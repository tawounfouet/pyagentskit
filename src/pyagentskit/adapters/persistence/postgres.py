"""Production-reference PostgreSQL adapters for PyAgentsKit V2 persistence."""

from __future__ import annotations

import asyncio
import re
from collections.abc import Awaitable, Callable
from contextlib import AbstractAsyncContextManager
from contextvars import ContextVar, Token
from importlib.resources import files
from types import TracebackType
from typing import TypeVar

from ...contracts.effects import EffectReservationResult
from ...contracts.persistence import InboxRecord, InboxStatus, OutboxRecord, OutboxStatus
from ...domain.effects import (
    Effect,
    IdempotencyKey,
    IdempotencyScope,
    ReconciliationCase,
    ReconciliationEvidence,
)
from ...domain.entities import (
    Approval,
    AuditEvent,
    Lease,
    MemoryEntry,
    Run,
    RuntimeBinding,
    RuntimeInvocation,
)
from ...domain.errors import (
    ConcurrencyConflictError,
    DuplicateAggregateError,
    IdempotencyConflictError,
    InboxDigestConflictError,
    PersistenceError,
)
from ...domain.events import IntegrationEvent
from ...domain.lifecycle import ApprovalStatus, RunStatus
from ...domain.shared import (
    AggregateVersion,
    ApprovalId,
    EffectId,
    FencingToken,
    MemoryEntryId,
    RunId,
    RuntimeBindingId,
    RuntimeInvocationId,
)
from ...postgres import AsyncPostgresConnection, AsyncPostgresPool
from ._codec import (
    approval_from_document,
    approval_to_document,
    audit_from_document,
    audit_to_document,
    dumps,
    effect_from_document,
    effect_to_document,
    integration_event_from_document,
    integration_event_to_document,
    lease_from_document,
    lease_to_document,
    loads,
    memory_from_document,
    memory_to_document,
    reconciliation_case_from_document,
    reconciliation_case_to_document,
    reconciliation_evidence_to_document,
    run_from_document,
    run_to_document,
    runtime_binding_from_document,
    runtime_binding_to_document,
    runtime_invocation_from_document,
    runtime_invocation_to_document,
)

ResultT = TypeVar("ResultT")
_SAFE_PREFIX = re.compile(r"^[a-z][a-z0-9_]{0,47}$")


def _safe_prefix(value: str) -> str:
    if _SAFE_PREFIX.fullmatch(value) is None:
        raise ValueError("PostgreSQL V2 table prefix must be a safe lowercase identifier")
    return value


def _text(value: object | None) -> str | None:
    return None if value is None else str(value)


class _PostgresV2Database:
    schema_version = 2

    def __init__(
        self,
        pool: AsyncPostgresPool,
        *,
        table_prefix: str = "pyagentskit",
    ) -> None:
        self.pool = pool
        self.table_prefix = _safe_prefix(table_prefix)
        self._initialized = False
        self._initialize_lock = asyncio.Lock()
        self._connection: ContextVar[AsyncPostgresConnection | None] = ContextVar(
            f"pyagentskit_postgres_v2_{id(self)}",
            default=None,
        )

    def table(self, suffix: str) -> str:
        if re.fullmatch(r"[a-z][a-z0-9_]*", suffix) is None:
            raise ValueError("invalid PostgreSQL V2 table suffix")
        return f"{self.table_prefix}_v2_{suffix}"

    async def initialize(self) -> None:
        async with self._initialize_lock:
            if self._initialized:
                return
            schema = self.table("schema_migrations")
            try:
                async with self.pool.acquire() as connection, connection.transaction():
                    await connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {schema} "
                        "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
                    )
                    row = await connection.fetchrow(
                        f"SELECT version FROM {schema} WHERE component=$1 FOR UPDATE",
                        "persistence_v2",
                    )
                    current = 0 if row is None else int(row["version"])
                    if current > self.schema_version:
                        raise PersistenceError("PostgreSQL V2 schema is newer than this package")
                    migrations = {
                        1: "0001_v2_core.sql",
                        2: "0002_v2_catalog.sql",
                    }
                    for version in range(current + 1, self.schema_version + 1):
                        migration = (
                            files("pyagentskit.adapters.persistence.migrations.postgres")
                            .joinpath(migrations[version])
                            .read_text(encoding="utf-8")
                            .replace("__PFX__", self.table_prefix)
                        )
                        await connection.execute(migration)
                self._initialized = True
            except PersistenceError:
                raise
            except Exception as exc:
                raise PersistenceError("cannot initialize PostgreSQL V2 persistence") from exc

    async def call(
        self,
        operation: Callable[[AsyncPostgresConnection], Awaitable[ResultT]],
    ) -> ResultT:
        await self.initialize()
        current = self._connection.get()
        if current is not None:
            return await operation(current)
        try:
            async with self.pool.acquire() as connection:
                return await operation(connection)
        except (
            ConcurrencyConflictError,
            DuplicateAggregateError,
            IdempotencyConflictError,
            InboxDigestConflictError,
            PersistenceError,
            KeyError,
            ValueError,
        ):
            raise
        except Exception as exc:
            raise PersistenceError("PostgreSQL V2 persistence operation failed") from exc

    async def atomic(
        self,
        operation: Callable[[AsyncPostgresConnection], Awaitable[ResultT]],
    ) -> ResultT:
        await self.initialize()
        current = self._connection.get()
        if current is not None:
            return await operation(current)
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                return await operation(connection)
        except (
            ConcurrencyConflictError,
            DuplicateAggregateError,
            IdempotencyConflictError,
            InboxDigestConflictError,
            PersistenceError,
            KeyError,
            ValueError,
        ):
            raise
        except Exception as exc:
            raise PersistenceError("PostgreSQL V2 transaction failed") from exc

    def bind(self, connection: AsyncPostgresConnection) -> Token[AsyncPostgresConnection | None]:
        return self._connection.set(connection)

    def reset(self, token: Token[AsyncPostgresConnection | None]) -> None:
        self._connection.reset(token)


class _PostgresRepository:
    def __init__(
        self,
        database: _PostgresV2Database | AsyncPostgresPool,
        *,
        table_prefix: str = "pyagentskit",
    ) -> None:
        self._db = (
            database
            if isinstance(database, _PostgresV2Database)
            else _PostgresV2Database(database, table_prefix=table_prefix)
        )

    async def initialize(self) -> None:
        await self._db.initialize()


class PostgresV2RunRepository(_PostgresRepository):
    async def get(self, run_id: RunId) -> Run | None:
        table = self._db.table("runs")

        async def operation(connection: AsyncPostgresConnection) -> Run | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(run_id),
            )
            return None if row is None else run_from_document(loads(str(row["payload_json"])))

        return await self._db.call(operation)

    async def add(self, run: Run) -> None:
        table = self._db.table("runs")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}(id, tenant_id, status, version, created_at, payload_json) "
                "VALUES ($1,$2,$3,$4,$5,$6::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(run.id),
                str(run.tenant_id),
                run.status.value,
                run.version.value,
                run.created_at,
                dumps(run_to_document(run)),
            )
            if row is None:
                raise DuplicateAggregateError(f"run {run.id} already exists")

        await self._db.call(operation)

    async def save(self, run: Run, *, expected_version: AggregateVersion) -> None:
        if run.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")
        table = self._db.table("runs")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET tenant_id=$2, status=$3, version=$4, payload_json=$5::jsonb "
                "WHERE id=$1 AND version=$6 RETURNING id",
                str(run.id),
                str(run.tenant_id),
                run.status.value,
                run.version.value,
                dumps(run_to_document(run)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(f"stale or missing run {run.id}")

        await self._db.call(operation)

    async def list_by_state(self, status: RunStatus) -> tuple[Run, ...]:
        table = self._db.table("runs")

        async def operation(connection: AsyncPostgresConnection) -> tuple[Run, ...]:
            rows = await connection.fetch(
                f"SELECT payload_json FROM {table} WHERE status=$1 ORDER BY id",
                status.value,
            )
            return tuple(run_from_document(loads(str(row["payload_json"]))) for row in rows)

        return await self._db.call(operation)


class PostgresV2EffectRepository(_PostgresRepository):
    async def get(self, effect_id: EffectId) -> Effect:
        table = self._db.table("effects")

        async def operation(connection: AsyncPostgresConnection) -> Effect:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(effect_id),
            )
            if row is None:
                raise KeyError(str(effect_id))
            return effect_from_document(loads(str(row["payload_json"])))

        return await self._db.call(operation)

    async def reserve(self, effect: Effect) -> EffectReservationResult:
        table = self._db.table("effects")
        key = effect.idempotency_key

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> EffectReservationResult:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,run_id,effect_kind,status,risk_level,idempotency_scope,"
                "idempotency_namespace,idempotency_key,fingerprint,fencing_token,"
                "version,created_at,started_at,completed_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15::jsonb) "
                "ON CONFLICT DO NOTHING RETURNING id",
                str(effect.id),
                str(effect.run_id),
                str(effect.kind),
                effect.status.value,
                effect.risk_level.value,
                effect.idempotency_scope.value,
                None if key is None else key.namespace,
                None if key is None else key.key,
                effect.fingerprint.value,
                None if effect.fencing_token is None else effect.fencing_token.value,
                effect.version.value,
                effect.created_at,
                effect.started_at,
                effect.completed_at,
                dumps(effect_to_document(effect)),
            )
            if row is not None:
                return EffectReservationResult(effect=effect, created=True)

            existing_row = None
            if key is not None:
                existing_row = await connection.fetchrow(
                    f"SELECT payload_json FROM {table} "
                    "WHERE idempotency_scope=$1 AND idempotency_namespace=$2 "
                    "AND idempotency_key=$3",
                    effect.idempotency_scope.value,
                    key.namespace,
                    key.key,
                )
            if existing_row is None:
                existing_row = await connection.fetchrow(
                    f"SELECT payload_json FROM {table} WHERE id=$1",
                    str(effect.id),
                )
            if existing_row is None:
                raise PersistenceError("Effect insert conflicted without an existing row")
            existing = effect_from_document(loads(str(existing_row["payload_json"])))
            existing.assert_same_intent(effect.idempotency_key, effect.fingerprint)
            return EffectReservationResult(effect=existing, created=False)

        return await self._db.call(operation)

    async def find_by_idempotency_key(
        self,
        scope: IdempotencyScope,
        key: IdempotencyKey,
    ) -> Effect | None:
        table = self._db.table("effects")

        async def operation(connection: AsyncPostgresConnection) -> Effect | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} "
                "WHERE idempotency_scope=$1 AND idempotency_namespace=$2 "
                "AND idempotency_key=$3",
                scope.value,
                key.namespace,
                key.key,
            )
            return None if row is None else effect_from_document(loads(str(row["payload_json"])))

        return await self._db.call(operation)

    async def save(
        self,
        effect: Effect,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if effect.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")
        table = self._db.table("effects")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$2, fingerprint=$3, fencing_token=$4, "
                "version=$5, started_at=$6, completed_at=$7, payload_json=$8::jsonb "
                "WHERE id=$1 AND version=$9 RETURNING id",
                str(effect.id),
                effect.status.value,
                effect.fingerprint.value,
                None if effect.fencing_token is None else effect.fencing_token.value,
                effect.version.value,
                effect.started_at,
                effect.completed_at,
                dumps(effect_to_document(effect)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(f"stale or missing effect {effect.id}")

        await self._db.call(operation)


class PostgresV2MemoryRepository(_PostgresRepository):
    async def get(self, memory_id: MemoryEntryId) -> MemoryEntry | None:
        table = self._db.table("memory_entries")

        async def operation(connection: AsyncPostgresConnection) -> MemoryEntry | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(memory_id),
            )
            return None if row is None else memory_from_document(loads(str(row["payload_json"])))

        return await self._db.call(operation)

    async def put(self, entry: MemoryEntry) -> None:
        table = self._db.table("memory_entries")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,tenant_id,scope,scope_id,memory_key,version,created_at,updated_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb) "
                "ON CONFLICT DO NOTHING RETURNING id",
                str(entry.id),
                str(entry.tenant_id),
                entry.scope.value,
                entry.scope_id,
                entry.key,
                entry.version.value,
                entry.created_at,
                entry.updated_at,
                dumps(memory_to_document(entry)),
            )
            if row is None:
                raise DuplicateAggregateError(
                    f"memory entry {entry.id} or logical key already exists"
                )

        await self._db.call(operation)

    async def save(
        self,
        entry: MemoryEntry,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if entry.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")
        table = self._db.table("memory_entries")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET tenant_id=$2, scope=$3, scope_id=$4, memory_key=$5, "
                "version=$6, updated_at=$7, payload_json=$8::jsonb "
                "WHERE id=$1 AND version=$9 RETURNING id",
                str(entry.id),
                str(entry.tenant_id),
                entry.scope.value,
                entry.scope_id,
                entry.key,
                entry.version.value,
                entry.updated_at,
                dumps(memory_to_document(entry)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(f"stale or missing memory entry {entry.id}")

        await self._db.call(operation)

    async def list_by_scope(
        self,
        *,
        tenant_id: str,
        scope: str,
        scope_id: str | None,
    ) -> tuple[MemoryEntry, ...]:
        table = self._db.table("memory_entries")

        async def operation(connection: AsyncPostgresConnection) -> tuple[MemoryEntry, ...]:
            rows = await connection.fetch(
                f"SELECT payload_json FROM {table} "
                "WHERE tenant_id=$1 AND scope=$2 AND scope_id IS NOT DISTINCT FROM $3 "
                "ORDER BY id",
                tenant_id,
                scope,
                scope_id,
            )
            return tuple(memory_from_document(loads(str(row["payload_json"]))) for row in rows)

        return await self._db.call(operation)


class PostgresV2ReconciliationRepository(_PostgresRepository):
    async def get_active(self, effect_id: EffectId) -> ReconciliationCase | None:
        table = self._db.table("reconciliation_cases")

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> ReconciliationCase | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE effect_id=$1 "
                "AND status NOT IN ('resolved_success','resolved_failure') "
                "ORDER BY created_at DESC LIMIT 1",
                str(effect_id),
            )
            return (
                None
                if row is None
                else reconciliation_case_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def save(
        self,
        case: ReconciliationCase,
        *,
        expected_version: AggregateVersion | None,
    ) -> None:
        table = self._db.table("reconciliation_cases")
        if expected_version is None:

            async def insert(connection: AsyncPostgresConnection) -> None:
                row = await connection.fetchrow(
                    f"INSERT INTO {table}("
                    "id,effect_id,status,attempt_count,max_attempts,version,created_at,"
                    "resolved_at,payload_json"
                    ") VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb) "
                    "ON CONFLICT(id) DO NOTHING RETURNING id",
                    str(case.id),
                    str(case.effect_id),
                    case.status.value,
                    case.attempt_count,
                    case.max_attempts,
                    case.version.value,
                    case.created_at,
                    case.resolved_at,
                    dumps(reconciliation_case_to_document(case)),
                )
                if row is None:
                    raise DuplicateAggregateError(f"reconciliation case {case.id} already exists")

            await self._db.call(insert)
            return

        if case.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")

        async def update(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$2, attempt_count=$3, max_attempts=$4, "
                "version=$5, resolved_at=$6, payload_json=$7::jsonb "
                "WHERE id=$1 AND version=$8 RETURNING id",
                str(case.id),
                case.status.value,
                case.attempt_count,
                case.max_attempts,
                case.version.value,
                case.resolved_at,
                dumps(reconciliation_case_to_document(case)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(f"stale or missing reconciliation case {case.id}")

        await self._db.call(update)

    async def append_evidence(self, evidence: ReconciliationEvidence) -> None:
        table = self._db.table("reconciliation_evidence")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}(id,case_id,observed_at,payload_json) "
                "VALUES ($1,$2,$3,$4::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(evidence.id),
                str(evidence.case_id),
                evidence.observed_at,
                dumps(reconciliation_evidence_to_document(evidence)),
            )
            if row is None:
                raise DuplicateAggregateError(
                    f"reconciliation evidence {evidence.id} already exists"
                )

        await self._db.call(operation)


class PostgresV2ApprovalRepository(_PostgresRepository):
    async def get(self, approval_id: ApprovalId) -> Approval | None:
        table = self._db.table("approvals")

        async def operation(connection: AsyncPostgresConnection) -> Approval | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(approval_id),
            )
            return None if row is None else approval_from_document(loads(str(row["payload_json"])))

        return await self._db.call(operation)

    async def add(self, approval: Approval) -> None:
        table = self._db.table("approvals")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,subject,scope,status,expires_at,version,created_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(approval.id),
                approval.subject,
                approval.scope.value,
                approval.status.value,
                approval.expires_at,
                approval.version.value,
                approval.created_at,
                dumps(approval_to_document(approval)),
            )
            if row is None:
                raise DuplicateAggregateError(f"approval {approval.id} already exists")

        await self._db.call(operation)

    async def save(
        self,
        approval: Approval,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if approval.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")
        table = self._db.table("approvals")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$2, expires_at=$3, version=$4, payload_json=$5::jsonb "
                "WHERE id=$1 AND version=$6 RETURNING id",
                str(approval.id),
                approval.status.value,
                approval.expires_at,
                approval.version.value,
                dumps(approval_to_document(approval)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(f"stale or missing approval {approval.id}")

        await self._db.call(operation)

    async def list_pending(self) -> tuple[Approval, ...]:
        table = self._db.table("approvals")

        async def operation(connection: AsyncPostgresConnection) -> tuple[Approval, ...]:
            rows = await connection.fetch(
                f"SELECT payload_json FROM {table} WHERE status=$1 ORDER BY created_at,id",
                ApprovalStatus.PENDING.value,
            )
            return tuple(approval_from_document(loads(str(row["payload_json"]))) for row in rows)

        return await self._db.call(operation)


class PostgresV2LeaseRepository(_PostgresRepository):
    async def get_current(self, resource: str) -> Lease | None:
        table = self._db.table("leases")

        async def operation(connection: AsyncPostgresConnection) -> Lease | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE resource=$1 "
                "ORDER BY fencing_token DESC LIMIT 1",
                resource,
            )
            return None if row is None else lease_from_document(loads(str(row["payload_json"])))

        return await self._db.call(operation)

    async def add(self, lease: Lease) -> None:
        table = self._db.table("leases")
        resources = self._db.table("lease_resources")

        async def operation(connection: AsyncPostgresConnection) -> None:
            counter = await connection.fetchrow(
                f"SELECT current_fencing_token FROM {resources} WHERE resource=$1 FOR UPDATE",
                lease.resource,
            )
            if (
                counter is None
                or int(counter["current_fencing_token"]) != lease.fencing_token.value
            ):
                raise ConcurrencyConflictError(f"stale fencing token for resource {lease.resource}")
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,resource,status,worker_id,fencing_token,version,created_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6,$7,$8::jsonb) "
                "ON CONFLICT DO NOTHING RETURNING id",
                str(lease.id),
                lease.resource,
                lease.status.value,
                None if lease.worker_id is None else str(lease.worker_id),
                lease.fencing_token.value,
                lease.version.value,
                lease.created_at,
                dumps(lease_to_document(lease)),
            )
            if row is not None:
                return
            duplicate = await connection.fetchrow(
                f"SELECT id FROM {table} WHERE id=$1",
                str(lease.id),
            )
            if duplicate is not None:
                raise DuplicateAggregateError(f"lease {lease.id} already exists")
            raise ConcurrencyConflictError(f"resource {lease.resource} already has an active lease")

        await self._db.atomic(operation)

    async def save(
        self,
        lease: Lease,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if lease.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")
        table = self._db.table("leases")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$2, worker_id=$3, fencing_token=$4, "
                "version=$5, payload_json=$6::jsonb "
                "WHERE id=$1 AND version=$7 RETURNING id",
                str(lease.id),
                lease.status.value,
                None if lease.worker_id is None else str(lease.worker_id),
                lease.fencing_token.value,
                lease.version.value,
                dumps(lease_to_document(lease)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(f"stale or missing lease {lease.id}")

        await self._db.call(operation)

    async def next_fencing_token(self, resource: str) -> FencingToken:
        resources = self._db.table("lease_resources")

        async def operation(connection: AsyncPostgresConnection) -> FencingToken:
            row = await connection.fetchrow(
                f"INSERT INTO {resources}(resource,current_fencing_token,version) "
                "VALUES ($1,1,0) "
                "ON CONFLICT(resource) DO UPDATE SET "
                f"current_fencing_token={resources}.current_fencing_token+1, "
                f"version={resources}.version+1 "
                "RETURNING current_fencing_token",
                resource,
            )
            if row is None:
                raise PersistenceError("PostgreSQL fencing counter did not return a token")
            return FencingToken(int(row["current_fencing_token"]))

        return await self._db.atomic(operation)


class PostgresV2RuntimeRepository(_PostgresRepository):
    async def get_binding(
        self,
        binding_id: RuntimeBindingId,
    ) -> RuntimeBinding | None:
        table = self._db.table("runtime_bindings")

        async def operation(connection: AsyncPostgresConnection) -> RuntimeBinding | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(binding_id),
            )
            return (
                None
                if row is None
                else runtime_binding_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def add_binding(self, binding: RuntimeBinding) -> None:
        table = self._db.table("runtime_bindings")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,run_id,runtime_id,runtime_family,bound_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(binding.id),
                None if binding.run_id is None else str(binding.run_id),
                binding.resolved_runtime_id,
                binding.runtime_family,
                binding.bound_at,
                dumps(runtime_binding_to_document(binding)),
            )
            if row is None:
                raise DuplicateAggregateError(f"runtime binding {binding.id} already exists")

        await self._db.call(operation)

    async def get_invocation(
        self,
        invocation_id: RuntimeInvocationId,
    ) -> RuntimeInvocation | None:
        table = self._db.table("runtime_invocations")

        async def operation(connection: AsyncPostgresConnection) -> RuntimeInvocation | None:
            row = await connection.fetchrow(
                f"SELECT payload_json FROM {table} WHERE id=$1",
                str(invocation_id),
            )
            return (
                None
                if row is None
                else runtime_invocation_from_document(loads(str(row["payload_json"])))
            )

        return await self._db.call(operation)

    async def add_invocation(self, invocation: RuntimeInvocation) -> None:
        table = self._db.table("runtime_invocations")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "id,run_id,binding_id,runtime_id,status,version,started_at,"
                "completed_at,payload_json"
                ") VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(invocation.id),
                str(invocation.run_id),
                str(invocation.binding_id),
                invocation.runtime_id,
                invocation.status.value,
                invocation.version.value,
                invocation.started_at,
                invocation.completed_at,
                dumps(runtime_invocation_to_document(invocation)),
            )
            if row is None:
                raise DuplicateAggregateError(f"runtime invocation {invocation.id} already exists")

        await self._db.call(operation)

    async def save_invocation(
        self,
        invocation: RuntimeInvocation,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if invocation.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")
        table = self._db.table("runtime_invocations")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET runtime_id=$2,status=$3,version=$4,"
                "started_at=$5,completed_at=$6,payload_json=$7::jsonb "
                "WHERE id=$1 AND version=$8 RETURNING id",
                str(invocation.id),
                invocation.runtime_id,
                invocation.status.value,
                invocation.version.value,
                invocation.started_at,
                invocation.completed_at,
                dumps(runtime_invocation_to_document(invocation)),
                expected_version.value,
            )
            if row is None:
                raise ConcurrencyConflictError(
                    f"stale or missing runtime invocation {invocation.id}"
                )

        await self._db.call(operation)


class PostgresV2AuditStore(_PostgresRepository):
    async def append(self, event: AuditEvent) -> None:
        table = self._db.table("audit_events")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}(id,subject,event_type,occurred_at,payload_json) "
                "VALUES ($1,$2,$3,$4,$5::jsonb) "
                "ON CONFLICT(id) DO NOTHING RETURNING id",
                str(event.id),
                event.subject,
                event.event_type,
                event.occurred_at,
                dumps(audit_to_document(event)),
            )
            if row is None:
                raise DuplicateAggregateError(f"audit event {event.id} already exists")

        await self._db.call(operation)

    async def list_for_subject(self, subject: str) -> tuple[AuditEvent, ...]:
        table = self._db.table("audit_events")

        async def operation(connection: AsyncPostgresConnection) -> tuple[AuditEvent, ...]:
            rows = await connection.fetch(
                f"SELECT payload_json FROM {table} WHERE subject=$1 ORDER BY occurred_at,id",
                subject,
            )
            return tuple(audit_from_document(loads(str(row["payload_json"]))) for row in rows)

        return await self._db.call(operation)


class PostgresV2OutboxStore(_PostgresRepository):
    async def append(self, event: IntegrationEvent) -> None:
        table = self._db.table("outbox_events")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "event_id,event_name,aggregate_type,aggregate_id,status,attempt_count,"
                "occurred_at,event_json"
                ") VALUES ($1,$2,$3,$4,$5,0,$6,$7::jsonb) "
                "ON CONFLICT(event_id) DO NOTHING RETURNING event_id",
                event.event_id,
                event.name,
                event.aggregate_type,
                event.aggregate_id,
                OutboxStatus.PENDING.value,
                event.occurred_at,
                dumps(integration_event_to_document(event)),
            )
            if row is None:
                raise DuplicateAggregateError(f"outbox event {event.event_id} already exists")

        await self._db.call(operation)

    async def claim_batch(
        self,
        *,
        worker_id: str,
        limit: int = 100,
        claim_timeout_seconds: float = 60.0,
    ) -> tuple[OutboxRecord, ...]:
        if limit < 1:
            raise ValueError("outbox claim limit must be positive")
        if claim_timeout_seconds < 0:
            raise ValueError("outbox claim timeout cannot be negative")
        table = self._db.table("outbox_events")

        async def operation(
            connection: AsyncPostgresConnection,
        ) -> tuple[OutboxRecord, ...]:
            rows = await connection.fetch(
                f"SELECT event_id,event_json,attempt_count,next_attempt_at,published_at,"
                f"last_error FROM {table} "
                "WHERE (status IN ($1,$2) OR "
                "(status=$3 AND claimed_at IS NOT NULL "
                "AND claimed_at <= CURRENT_TIMESTAMP - ($4 * INTERVAL '1 second'))) "
                "AND (next_attempt_at IS NULL OR next_attempt_at <= CURRENT_TIMESTAMP) "
                "ORDER BY occurred_at,event_id FOR UPDATE SKIP LOCKED LIMIT $5",
                OutboxStatus.PENDING.value,
                OutboxStatus.FAILED.value,
                OutboxStatus.CLAIMED.value,
                claim_timeout_seconds,
                limit,
            )
            claimed: list[OutboxRecord] = []
            for row in rows:
                updated = await connection.fetchrow(
                    f"UPDATE {table} SET status=$2,claimed_by=$3,claimed_at=CURRENT_TIMESTAMP,"
                    "attempt_count=attempt_count+1 WHERE event_id=$1 "
                    "RETURNING attempt_count,claimed_at",
                    str(row["event_id"]),
                    OutboxStatus.CLAIMED.value,
                    worker_id,
                )
                if updated is None:
                    continue
                claimed.append(
                    OutboxRecord(
                        event=integration_event_from_document(loads(str(row["event_json"]))),
                        status=OutboxStatus.CLAIMED,
                        attempt_count=int(updated["attempt_count"]),
                        next_attempt_at=row["next_attempt_at"],
                        claimed_by=worker_id,
                        claimed_at=updated["claimed_at"],
                        published_at=row["published_at"],
                        last_error=_text(row["last_error"]),
                    )
                )
            return tuple(claimed)

        return await self._db.atomic(operation)

    async def mark_published(self, event_id: str) -> None:
        table = self._db.table("outbox_events")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$2,claimed_by=NULL,claimed_at=NULL,"
                "published_at=CURRENT_TIMESTAMP,last_error=NULL "
                "WHERE event_id=$1 RETURNING event_id",
                event_id,
                OutboxStatus.PUBLISHED.value,
            )
            if row is None:
                raise KeyError(event_id)

        await self._db.call(operation)

    async def mark_failed(self, event_id: str, *, error: str) -> None:
        table = self._db.table("outbox_events")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$2,claimed_by=NULL,claimed_at=NULL,"
                "last_error=$3 WHERE event_id=$1 RETURNING event_id",
                event_id,
                OutboxStatus.FAILED.value,
                error,
            )
            if row is None:
                raise KeyError(event_id)

        await self._db.call(operation)

    async def release_claim(self, event_id: str) -> None:
        table = self._db.table("outbox_events")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$2,claimed_by=NULL,claimed_at=NULL "
                "WHERE event_id=$1 RETURNING event_id",
                event_id,
                OutboxStatus.PENDING.value,
            )
            if row is None:
                raise KeyError(event_id)

        await self._db.call(operation)


class PostgresV2InboxStore(_PostgresRepository):
    async def reserve(self, record: InboxRecord) -> bool:
        table = self._db.table("inbox_events")

        async def operation(connection: AsyncPostgresConnection) -> bool:
            row = await connection.fetchrow(
                f"INSERT INTO {table}("
                "source,external_event_id,digest,status,tenant_id,processed_at,last_error"
                ") VALUES ($1,$2,$3,$4,$5,$6,$7) "
                "ON CONFLICT(source,external_event_id) DO NOTHING "
                "RETURNING external_event_id",
                record.source,
                record.external_event_id,
                record.digest,
                record.status.value,
                record.tenant_id,
                record.processed_at,
                record.last_error,
            )
            if row is not None:
                return True
            existing = await connection.fetchrow(
                f"SELECT digest FROM {table} WHERE source=$1 AND external_event_id=$2",
                record.source,
                record.external_event_id,
            )
            if existing is None:
                raise PersistenceError("Inbox conflict occurred without an existing row")
            if str(existing["digest"]) != record.digest:
                raise InboxDigestConflictError(
                    "external event id was reused with a different digest"
                )
            return False

        return await self._db.call(operation)

    async def get(
        self,
        source: str,
        external_event_id: str,
    ) -> InboxRecord | None:
        table = self._db.table("inbox_events")

        async def operation(connection: AsyncPostgresConnection) -> InboxRecord | None:
            row = await connection.fetchrow(
                f"SELECT digest,status,tenant_id,processed_at,last_error FROM {table} "
                "WHERE source=$1 AND external_event_id=$2",
                source,
                external_event_id,
            )
            if row is None:
                return None
            return InboxRecord(
                source=source,
                external_event_id=external_event_id,
                digest=str(row["digest"]),
                status=InboxStatus(str(row["status"])),
                tenant_id=_text(row["tenant_id"]),
                processed_at=row["processed_at"],
                last_error=_text(row["last_error"]),
            )

        return await self._db.call(operation)

    async def mark_processed(self, source: str, external_event_id: str) -> None:
        table = self._db.table("inbox_events")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$3,processed_at=CURRENT_TIMESTAMP,"
                "last_error=NULL WHERE source=$1 AND external_event_id=$2 "
                "RETURNING external_event_id",
                source,
                external_event_id,
                InboxStatus.PROCESSED.value,
            )
            if row is None:
                raise KeyError((source, external_event_id))

        await self._db.call(operation)

    async def mark_failed(
        self,
        source: str,
        external_event_id: str,
        *,
        error: str,
    ) -> None:
        table = self._db.table("inbox_events")

        async def operation(connection: AsyncPostgresConnection) -> None:
            row = await connection.fetchrow(
                f"UPDATE {table} SET status=$3,last_error=$4 "
                "WHERE source=$1 AND external_event_id=$2 RETURNING external_event_id",
                source,
                external_event_id,
                InboxStatus.FAILED.value,
                error,
            )
            if row is None:
                raise KeyError((source, external_event_id))

        await self._db.call(operation)


class PostgresV2UnitOfWork:
    """One PostgreSQL connection/transaction shared by state, audit and outbox."""

    def __init__(
        self,
        pool: AsyncPostgresPool,
        *,
        table_prefix: str = "pyagentskit",
    ) -> None:
        from .postgres_catalog import (
            PostgresV2ArtifactRepository,
            PostgresV2ConversationRepository,
            PostgresV2MessageRepository,
            PostgresV2SessionRepository,
            PostgresV2WorkerRepository,
        )

        self._db = _PostgresV2Database(pool, table_prefix=table_prefix)
        self.runs = PostgresV2RunRepository(self._db)
        self.sessions = PostgresV2SessionRepository(self._db)
        self.conversations = PostgresV2ConversationRepository(self._db)
        self.messages = PostgresV2MessageRepository(self._db)
        self.effects = PostgresV2EffectRepository(self._db)
        self.memories = PostgresV2MemoryRepository(self._db)
        self.reconciliations = PostgresV2ReconciliationRepository(self._db)
        self.approvals = PostgresV2ApprovalRepository(self._db)
        self.workers = PostgresV2WorkerRepository(self._db)
        self.artifacts = PostgresV2ArtifactRepository(self._db)
        self.runtimes = PostgresV2RuntimeRepository(self._db)
        self.outbox = PostgresV2OutboxStore(self._db)
        self.audit = PostgresV2AuditStore(self._db)
        self._acquire: AbstractAsyncContextManager[AsyncPostgresConnection] | None = None
        self._connection: AsyncPostgresConnection | None = None
        self._token: Token[AsyncPostgresConnection | None] | None = None
        self._committed = False

    async def __aenter__(self) -> PostgresV2UnitOfWork:
        if self._connection is not None:
            raise RuntimeError("PostgresV2UnitOfWork is already active")
        await self._db.initialize()
        self._committed = False
        self._acquire = self._db.pool.acquire()
        self._connection = await self._acquire.__aenter__()
        await self._connection.execute("BEGIN")
        self._token = self._db.bind(self._connection)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._connection is None or self._acquire is None or self._token is None:
            return
        connection = self._connection
        acquire = self._acquire
        token = self._token
        self._connection = None
        self._acquire = None
        self._token = None
        try:
            if exc_type is None and self._committed:
                await connection.execute("COMMIT")
            else:
                await connection.execute("ROLLBACK")
        finally:
            self._db.reset(token)
            await acquire.__aexit__(exc_type, exc, tb)

    async def commit(self) -> None:
        if self._connection is None:
            raise RuntimeError("PostgresV2UnitOfWork is not active")
        self._committed = True

    async def rollback(self) -> None:
        if self._connection is None or self._acquire is None or self._token is None:
            return
        connection = self._connection
        acquire = self._acquire
        token = self._token
        self._connection = None
        self._acquire = None
        self._token = None
        try:
            await connection.execute("ROLLBACK")
        finally:
            self._db.reset(token)
            await acquire.__aexit__(None, None, None)


__all__ = [
    "PostgresV2ApprovalRepository",
    "PostgresV2AuditStore",
    "PostgresV2EffectRepository",
    "PostgresV2InboxStore",
    "PostgresV2LeaseRepository",
    "PostgresV2MemoryRepository",
    "PostgresV2OutboxStore",
    "PostgresV2ReconciliationRepository",
    "PostgresV2RunRepository",
    "PostgresV2RuntimeRepository",
    "PostgresV2UnitOfWork",
]
