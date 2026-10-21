"""Optional PostgreSQL stores using an asyncpg-compatible connection pool.

The core package does not import asyncpg.  Applications may pass an asyncpg
pool or any object satisfying :class:`AsyncPostgresPool`.  Schema creation is
lazy and idempotent; call :meth:`initialize` during application startup when a
fail-fast readiness check is preferred.
"""

from __future__ import annotations

import asyncio
import json
import re
from collections.abc import Callable, Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import datetime, timedelta
from typing import Any, Protocol, TypeVar, cast, runtime_checkable
from uuid import UUID

from .coordination import (
    Lease,
    LeaseConflictError,
    LeaseNotFoundError,
    MemoryLeaseStore,
    _key,
    _scope,
    _ttl,
)
from .durability import (
    EffectRecord,
    EffectResolution,
    EffectStatus,
    JournalEntry,
    RunCheckpoint,
    _Aggregate,
    _StoreLogic,
    migrate_checkpoint_document,
)
from .exceptions import PersistenceError, PyAgentsKitError, RunNotFoundError
from .tools import ToolResult

__all__ = [
    "AsyncPostgresConnection",
    "AsyncPostgresPool",
    "PostgresLeaseStore",
    "PostgresRunStore",
    "create_asyncpg_pool",
]

_SAFE_PREFIX = re.compile(r"^[a-z][a-z0-9_]{0,47}$")
_T = TypeVar("_T")


@runtime_checkable
class AsyncPostgresConnection(Protocol):
    """Small asyncpg-compatible connection surface used by the stores."""

    async def execute(self, query: str, *args: object) -> str: ...

    async def fetchrow(self, query: str, *args: object) -> Mapping[str, Any] | None: ...

    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, Any]]: ...

    def transaction(self) -> AbstractAsyncContextManager[Any]: ...


@runtime_checkable
class AsyncPostgresPool(Protocol):
    """Connection-pool port compatible with ``asyncpg.Pool``."""

    def acquire(self) -> AbstractAsyncContextManager[AsyncPostgresConnection]: ...


def _prefix(value: str) -> str:
    if not _SAFE_PREFIX.fullmatch(value):
        raise ValueError("PostgreSQL table prefix must be a safe lowercase identifier")
    return value


def _json_payload(value: object) -> str:
    if isinstance(value, bytes):
        return value.decode("utf-8")
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


async def create_asyncpg_pool(
    dsn: str,
    *,
    min_size: int = 1,
    max_size: int = 10,
    command_timeout: float = 30.0,
) -> AsyncPostgresPool:
    """Create an application-owned asyncpg pool without retaining the DSN.

    This explicit helper requires the ``postgres`` extra.  Importing
    :mod:`pyagentskit.postgres` never imports asyncpg and never opens a socket.
    """

    if not dsn.strip():
        raise ValueError("PostgreSQL DSN cannot be blank")
    if min_size < 0 or max_size < 1 or min_size > max_size:
        raise ValueError("PostgreSQL pool size bounds are invalid")
    if command_timeout <= 0:
        raise ValueError("PostgreSQL command timeout must be positive")
    try:
        import asyncpg  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PersistenceError(
            'PostgreSQL support requires pip install "pyagentskit[postgres]"'
        ) from exc
    pool = await asyncpg.create_pool(
        dsn=dsn,
        min_size=min_size,
        max_size=max_size,
        command_timeout=command_timeout,
    )
    if pool is None:
        raise PersistenceError("asyncpg did not create a PostgreSQL pool")
    return cast(AsyncPostgresPool, pool)


class _PostgresStore:
    schema_version = 1

    def __init__(self, pool: AsyncPostgresPool, *, table_prefix: str = "pyagentskit") -> None:
        self.pool = pool
        self.table_prefix = _prefix(table_prefix)
        self._initialized = False
        self._initialize_lock = asyncio.Lock()

    async def _ensure_initialized(self) -> None:
        if not self._initialized:
            await self.initialize()

    async def initialize(self) -> None:
        raise NotImplementedError


class PostgresLeaseStore(_PostgresStore):
    """Distributed lease store with database-time expiry and fencing tokens."""

    def __init__(self, pool: AsyncPostgresPool, *, table_prefix: str = "pyagentskit") -> None:
        super().__init__(pool, table_prefix=table_prefix)
        self._leases = f"{self.table_prefix}_leases"
        self._tokens = f"{self.table_prefix}_lease_tokens"
        self._schema = f"{self.table_prefix}_schema_versions"

    async def initialize(self) -> None:
        async with self._initialize_lock:
            if self._initialized:
                return
            try:
                async with self.pool.acquire() as connection, connection.transaction():
                    await connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {self._schema} ("
                        "component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
                    )
                    row = await connection.fetchrow(
                        f"SELECT version FROM {self._schema} WHERE component=$1 FOR UPDATE",
                        "coordination_leases",
                    )
                    if row is not None and int(row["version"]) > self.schema_version:
                        raise PersistenceError("PostgreSQL lease schema is newer than this package")
                    await connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {self._tokens} ("
                        "tenant_scope TEXT NOT NULL, resource_id TEXT NOT NULL, "
                        "last_token BIGINT NOT NULL, "
                        "PRIMARY KEY (tenant_scope, resource_id))"
                    )
                    await connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {self._leases} ("
                        "tenant_scope TEXT NOT NULL, resource_id TEXT NOT NULL, "
                        "lease_id TEXT NOT NULL, owner_id TEXT NOT NULL, "
                        "fencing_token BIGINT NOT NULL, revision BIGINT NOT NULL, "
                        "acquired_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ NOT NULL, "
                        "PRIMARY KEY (tenant_scope, resource_id))"
                    )
                    await connection.execute(
                        f"CREATE INDEX IF NOT EXISTS {self._leases}_expiry_idx "
                        f"ON {self._leases}(expires_at)"
                    )
                    await connection.execute(
                        f"INSERT INTO {self._schema}(component, version) VALUES ($1, $2) "
                        "ON CONFLICT(component) DO NOTHING",
                        "coordination_leases",
                        self.schema_version,
                    )
                self._initialized = True
            except PersistenceError:
                raise
            except Exception as exc:
                raise PersistenceError("Cannot initialize PostgreSQL lease store") from exc

    async def acquire(
        self,
        resource_id: str,
        *,
        owner_id: str,
        ttl_seconds: float,
        tenant_id: str | None = None,
    ) -> Lease:
        ttl = _ttl(ttl_seconds)
        if not owner_id.strip():
            raise ValueError("owner_id cannot be blank")
        tenant_scope, resource = _key(resource_id, tenant_id)
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                await connection.execute(
                    f"INSERT INTO {self._tokens}(tenant_scope, resource_id, last_token) "
                    "VALUES ($1, $2, 0) ON CONFLICT(tenant_scope, resource_id) DO NOTHING",
                    tenant_scope,
                    resource,
                )
                token_row = await connection.fetchrow(
                    f"SELECT last_token, CURRENT_TIMESTAMP AS now FROM {self._tokens} "
                    "WHERE tenant_scope=$1 AND resource_id=$2 FOR UPDATE",
                    tenant_scope,
                    resource,
                )
                if token_row is None:
                    raise PersistenceError("Lease token row disappeared")
                now = token_row["now"]
                current_row = await connection.fetchrow(
                    f"SELECT * FROM {self._leases} "
                    "WHERE tenant_scope=$1 AND resource_id=$2 FOR UPDATE",
                    tenant_scope,
                    resource,
                )
                if current_row is not None:
                    current = self._lease(current_row, tenant_id)
                    if current.expires_at > now:
                        if current.owner_id == owner_id:
                            return current
                        raise LeaseConflictError("Resource lease is already held")
                token = int(token_row["last_token"]) + 1
                lease = Lease(
                    resource_id=resource_id,
                    owner_id=owner_id,
                    tenant_id=tenant_id,
                    fencing_token=token,
                    acquired_at=now,
                    expires_at=now + timedelta(seconds=ttl),
                )
                await connection.execute(
                    f"UPDATE {self._tokens} SET last_token=$3 "
                    "WHERE tenant_scope=$1 AND resource_id=$2",
                    tenant_scope,
                    resource,
                    token,
                )
                await connection.execute(
                    f"INSERT INTO {self._leases}(tenant_scope, resource_id, lease_id, "
                    "owner_id, fencing_token, revision, acquired_at, expires_at) "
                    "VALUES ($1,$2,$3,$4,$5,$6,$7,$8) "
                    "ON CONFLICT(tenant_scope, resource_id) DO UPDATE SET "
                    "lease_id=EXCLUDED.lease_id, owner_id=EXCLUDED.owner_id, "
                    "fencing_token=EXCLUDED.fencing_token, revision=EXCLUDED.revision, "
                    "acquired_at=EXCLUDED.acquired_at, expires_at=EXCLUDED.expires_at",
                    tenant_scope,
                    resource,
                    lease.lease_id,
                    lease.owner_id,
                    lease.fencing_token,
                    lease.revision,
                    lease.acquired_at,
                    lease.expires_at,
                )
                return lease
        except (LeaseConflictError, PersistenceError):
            raise
        except Exception as exc:
            raise PersistenceError("Cannot acquire PostgreSQL lease") from exc

    async def get(self, resource_id: str, *, tenant_id: str | None = None) -> Lease:
        tenant_scope, resource = _key(resource_id, tenant_id)
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    f"SELECT *, CURRENT_TIMESTAMP AS now FROM {self._leases} "
                    "WHERE tenant_scope=$1 AND resource_id=$2",
                    tenant_scope,
                    resource,
                )
            if row is None or row["expires_at"] <= row["now"]:
                raise LeaseNotFoundError("Lease not found")
            return self._lease(row, tenant_id)
        except LeaseNotFoundError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot read PostgreSQL lease") from exc

    async def renew(self, lease: Lease, *, ttl_seconds: float) -> Lease:
        ttl = _ttl(ttl_seconds)
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                row = await connection.fetchrow(
                    f"SELECT *, CURRENT_TIMESTAMP AS now FROM {self._leases} "
                    "WHERE tenant_scope=$1 AND resource_id=$2 FOR UPDATE",
                    _scope(lease.tenant_id),
                    lease.resource_id,
                )
                if row is None:
                    raise LeaseNotFoundError("Lease not found")
                now = row["now"]
                current = self._lease(row, lease.tenant_id)
                MemoryLeaseStore._require_current(current, lease, now)
                renewed = lease.model_copy(
                    update={
                        "expires_at": now + timedelta(seconds=ttl),
                        "revision": lease.revision + 1,
                    }
                )
                await connection.execute(
                    f"UPDATE {self._leases} SET expires_at=$3, revision=$4 "
                    "WHERE tenant_scope=$1 AND resource_id=$2",
                    _scope(lease.tenant_id),
                    lease.resource_id,
                    renewed.expires_at,
                    renewed.revision,
                )
                return renewed
        except (LeaseConflictError, LeaseNotFoundError):
            raise
        except Exception as exc:
            raise PersistenceError("Cannot renew PostgreSQL lease") from exc

    async def release(self, lease: Lease) -> None:
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                row = await connection.fetchrow(
                    f"SELECT *, CURRENT_TIMESTAMP AS now FROM {self._leases} "
                    "WHERE tenant_scope=$1 AND resource_id=$2 FOR UPDATE",
                    _scope(lease.tenant_id),
                    lease.resource_id,
                )
                if row is None:
                    raise LeaseNotFoundError("Lease not found")
                MemoryLeaseStore._require_current(
                    self._lease(row, lease.tenant_id), lease, row["now"]
                )
                await connection.execute(
                    f"DELETE FROM {self._leases} WHERE tenant_scope=$1 AND resource_id=$2",
                    _scope(lease.tenant_id),
                    lease.resource_id,
                )
        except (LeaseConflictError, LeaseNotFoundError):
            raise
        except Exception as exc:
            raise PersistenceError("Cannot release PostgreSQL lease") from exc

    async def assert_current(self, lease: Lease) -> None:
        current = await self.get(lease.resource_id, tenant_id=lease.tenant_id)
        if (
            current.lease_id != lease.lease_id
            or current.owner_id != lease.owner_id
            or current.fencing_token != lease.fencing_token
            or current.revision != lease.revision
        ):
            raise LeaseConflictError("Lease is stale")

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        if now is not None and (now.tzinfo is None or now.utcoffset() is None):
            raise ValueError("purge timestamp must be timezone-aware")
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection:
                status = await connection.execute(
                    f"DELETE FROM {self._leases} "
                    "WHERE expires_at <= COALESCE($1, CURRENT_TIMESTAMP)",
                    now,
                )
            return int(status.rsplit(" ", 1)[-1])
        except Exception as exc:
            raise PersistenceError("Cannot purge PostgreSQL leases") from exc

    @staticmethod
    def _lease(row: Mapping[str, Any], tenant_id: str | None) -> Lease:
        return Lease(
            lease_id=row["lease_id"],
            resource_id=row["resource_id"],
            owner_id=row["owner_id"],
            tenant_id=tenant_id,
            fencing_token=int(row["fencing_token"]),
            acquired_at=row["acquired_at"],
            expires_at=row["expires_at"],
            revision=int(row["revision"]),
        )


class PostgresRunStore(_PostgresStore):
    """Transactional PostgreSQL implementation of the frozen V1 ``RunStore``."""

    def __init__(self, pool: AsyncPostgresPool, *, table_prefix: str = "pyagentskit") -> None:
        super().__init__(pool, table_prefix=table_prefix)
        self._runs = f"{self.table_prefix}_runs"
        self._locks = f"{self.table_prefix}_run_locks"
        self._schema = f"{self.table_prefix}_schema_versions"

    async def initialize(self) -> None:
        async with self._initialize_lock:
            if self._initialized:
                return
            try:
                async with self.pool.acquire() as connection, connection.transaction():
                    await connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {self._schema} ("
                        "component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
                    )
                    row = await connection.fetchrow(
                        f"SELECT version FROM {self._schema} WHERE component=$1 FOR UPDATE",
                        "durable_runs",
                    )
                    if row is not None and int(row["version"]) > self.schema_version:
                        raise PersistenceError("PostgreSQL run schema is newer than this package")
                    await connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {self._locks} ("
                        "tenant_scope TEXT NOT NULL, run_id UUID NOT NULL, "
                        "PRIMARY KEY (tenant_scope, run_id))"
                    )
                    await connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {self._runs} ("
                        "tenant_scope TEXT NOT NULL, run_id UUID NOT NULL, "
                        "payload_json JSONB NOT NULL, updated_at TIMESTAMPTZ NOT NULL "
                        "DEFAULT CURRENT_TIMESTAMP, PRIMARY KEY (tenant_scope, run_id))"
                    )
                    await connection.execute(
                        f"CREATE INDEX IF NOT EXISTS {self._runs}_payload_gin_idx "
                        f"ON {self._runs} USING GIN(payload_json)"
                    )
                    await connection.execute(
                        f"INSERT INTO {self._schema}(component, version) VALUES ($1, $2) "
                        "ON CONFLICT(component) DO NOTHING",
                        "durable_runs",
                        self.schema_version,
                    )
                self._initialized = True
            except PersistenceError:
                raise
            except Exception as exc:
                raise PersistenceError("Cannot initialize PostgreSQL run store") from exc

    async def _read(self, run_id: UUID, tenant_id: str | None) -> _Aggregate:
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    f"SELECT payload_json FROM {self._runs} WHERE tenant_scope=$1 AND run_id=$2",
                    _scope(tenant_id),
                    run_id,
                )
            if row is None:
                raise RunNotFoundError("Durable run not found")
            return self._aggregate(row["payload_json"])
        except RunNotFoundError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot read PostgreSQL run") from exc

    async def import_document(
        self,
        run_id: UUID,
        payload_json: str,
        *,
        tenant_id: str | None = None,
        overwrite: bool = False,
    ) -> None:
        """Import one validated SQLite aggregate without replaying its effects."""

        aggregate = self._aggregate(payload_json)
        canonical = aggregate.model_dump_json()
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                command = await connection.execute(
                    f"INSERT INTO {self._runs}(tenant_scope, run_id, payload_json) "
                    "VALUES ($1, $2, $3::jsonb) ON CONFLICT(tenant_scope, run_id) "
                    + (
                        "DO UPDATE SET payload_json=EXCLUDED.payload_json, "
                        "updated_at=CURRENT_TIMESTAMP"
                        if overwrite
                        else "DO NOTHING"
                    ),
                    _scope(tenant_id),
                    run_id,
                    canonical,
                )
                if not overwrite and command.endswith(" 0"):
                    row = await connection.fetchrow(
                        f"SELECT payload_json FROM {self._runs} "
                        "WHERE tenant_scope=$1 AND run_id=$2 FOR UPDATE",
                        _scope(tenant_id),
                        run_id,
                    )
                    if row is None or self._aggregate(row["payload_json"]) != aggregate:
                        raise PersistenceError("Durable run migration target conflict")
        except PersistenceError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot import PostgreSQL run") from exc

    async def _mutate(
        self,
        run_id: UUID,
        tenant_id: str | None,
        transform: Callable[[_Aggregate], tuple[_Aggregate, _T]],
    ) -> tuple[_Aggregate, _T]:
        await self._ensure_initialized()
        scope = _scope(tenant_id)
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                await connection.execute(
                    f"INSERT INTO {self._locks}(tenant_scope, run_id) VALUES ($1, $2) "
                    "ON CONFLICT(tenant_scope, run_id) DO NOTHING",
                    scope,
                    run_id,
                )
                await connection.fetchrow(
                    f"SELECT run_id FROM {self._locks} "
                    "WHERE tenant_scope=$1 AND run_id=$2 FOR UPDATE",
                    scope,
                    run_id,
                )
                row = await connection.fetchrow(
                    f"SELECT payload_json FROM {self._runs} "
                    "WHERE tenant_scope=$1 AND run_id=$2 FOR UPDATE",
                    scope,
                    run_id,
                )
                aggregate = _Aggregate() if row is None else self._aggregate(row["payload_json"])
                updated, selected = transform(aggregate)
                await connection.execute(
                    f"INSERT INTO {self._runs}(tenant_scope, run_id, payload_json) "
                    "VALUES ($1, $2, $3::jsonb) "
                    "ON CONFLICT(tenant_scope, run_id) DO UPDATE SET "
                    "payload_json=EXCLUDED.payload_json, updated_at=CURRENT_TIMESTAMP",
                    scope,
                    run_id,
                    updated.model_dump_json(),
                )
                return updated, selected
        except PyAgentsKitError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot mutate PostgreSQL run") from exc

    async def append_checkpoint(
        self, checkpoint: RunCheckpoint, *, expected_previous_sequence: int | None = None
    ) -> RunCheckpoint:
        await self._mutate(
            checkpoint.run_id,
            checkpoint.tenant_id,
            lambda aggregate: (
                _StoreLogic.checkpoint(aggregate, checkpoint, expected_previous_sequence),
                checkpoint,
            ),
        )
        return checkpoint

    async def latest_checkpoint(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> RunCheckpoint:
        checkpoints = (await self._read(run_id, tenant_id)).checkpoints
        if not checkpoints:
            raise RunNotFoundError("Durable run has no checkpoint")
        return checkpoints[-1]

    async def list_checkpoints(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[RunCheckpoint, ...]:
        return (await self._read(run_id, tenant_id)).checkpoints

    async def plan_effect(self, effect: EffectRecord) -> EffectRecord:
        _, selected = await self._mutate(
            effect.run_id,
            effect.tenant_id,
            lambda aggregate: _StoreLogic.plan(aggregate, effect),
        )
        return selected

    async def get_effect(self, effect_id: str, *, tenant_id: str | None = None) -> EffectRecord:
        await self._ensure_initialized()
        needle = json.dumps({"effects": [{"effect_id": effect_id}]}, separators=(",", ":"))
        try:
            async with self.pool.acquire() as connection:
                row = await connection.fetchrow(
                    f"SELECT payload_json FROM {self._runs} "
                    "WHERE tenant_scope=$1 AND payload_json @> $2::jsonb LIMIT 1",
                    _scope(tenant_id),
                    needle,
                )
            if row is None:
                raise RunNotFoundError("Effect not found")
            aggregate = self._aggregate(row["payload_json"])
            return next(item for item in aggregate.effects if item.effect_id == effect_id)
        except RunNotFoundError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot read PostgreSQL effect") from exc

    async def get_effect_by_key(
        self, run_id: UUID, idempotency_key: str, *, tenant_id: str | None = None
    ) -> EffectRecord | None:
        try:
            aggregate = await self._read(run_id, tenant_id)
        except RunNotFoundError:
            return None
        return next(
            (item for item in aggregate.effects if item.idempotency_key == idempotency_key), None
        )

    async def list_effects(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[EffectRecord, ...]:
        return (await self._read(run_id, tenant_id)).effects

    async def transition_effect(
        self,
        effect_id: str,
        status: EffectStatus,
        *,
        tenant_id: str | None = None,
        expected_revision: int,
        result: ToolResult | None = None,
    ) -> EffectRecord:
        current = await self.get_effect(effect_id, tenant_id=tenant_id)
        _, selected = await self._mutate(
            current.run_id,
            tenant_id,
            lambda aggregate: _StoreLogic.transition(
                aggregate, effect_id, status, expected_revision, result
            ),
        )
        return selected

    async def resolve_effect(
        self,
        effect_id: str,
        resolution: EffectResolution,
        *,
        tenant_id: str | None = None,
        expected_revision: int,
        result: ToolResult | None = None,
    ) -> EffectRecord:
        current = await self.get_effect(effect_id, tenant_id=tenant_id)
        _, selected = await self._mutate(
            current.run_id,
            tenant_id,
            lambda aggregate: _StoreLogic.resolve(
                aggregate, effect_id, resolution, expected_revision, result
            ),
        )
        return selected

    async def list_journal(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[JournalEntry, ...]:
        return (await self._read(run_id, tenant_id)).journal

    @staticmethod
    def _aggregate(payload: object) -> _Aggregate:
        document = json.loads(_json_payload(payload))
        document["checkpoints"] = tuple(
            migrate_checkpoint_document(item).model_dump(mode="json")
            for item in document.get("checkpoints", [])
        )
        document["effects"] = tuple(document.get("effects", []))
        document["journal"] = tuple(document.get("journal", []))
        return _Aggregate.model_validate_json(json.dumps(document))
