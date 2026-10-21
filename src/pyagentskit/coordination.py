"""Tenant-scoped distributed coordination contracts and local lease stores.

Leases coordinate ownership; monotonically increasing fencing tokens let the
protected resource reject a stale owner.  The embedding application remains
responsible for carrying the token to every protected write.
"""

from __future__ import annotations

import asyncio
import math
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Protocol, runtime_checkable
from uuid import uuid4

from pydantic import Field, field_validator

from ._base import ContractModel
from .exceptions import PersistenceError
from .runs import utc_now
from .types import NonEmptyString

__all__ = [
    "Lease",
    "LeaseConflictError",
    "LeaseNotFoundError",
    "LeaseStore",
    "MemoryLeaseStore",
    "SQLiteLeaseStore",
]


class LeaseConflictError(PersistenceError):
    """A resource is owned by another worker or the supplied lease is stale."""


class LeaseNotFoundError(PersistenceError):
    """No current lease exists inside the requested tenant scope."""


class Lease(ContractModel):
    """One time-bounded ownership grant with a monotonic fencing token."""

    lease_id: NonEmptyString = Field(default_factory=lambda: NonEmptyString(uuid4().hex))
    resource_id: NonEmptyString
    owner_id: NonEmptyString
    tenant_id: NonEmptyString | None = None
    fencing_token: int = Field(ge=1)
    acquired_at: datetime
    expires_at: datetime
    revision: int = Field(default=0, ge=0)

    @field_validator("acquired_at", "expires_at")
    @classmethod
    def validate_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("lease timestamps must be timezone-aware")
        return value

    @field_validator("expires_at")
    @classmethod
    def validate_expiration(cls, value: datetime, info: object) -> datetime:
        data = getattr(info, "data", {})
        acquired_at = data.get("acquired_at")
        if isinstance(acquired_at, datetime) and value <= acquired_at:
            raise ValueError("lease expiration must follow acquisition")
        return value


@runtime_checkable
class LeaseStore(Protocol):
    """Port for mutually exclusive, tenant-scoped distributed leases."""

    async def acquire(
        self,
        resource_id: str,
        *,
        owner_id: str,
        ttl_seconds: float,
        tenant_id: str | None = None,
    ) -> Lease: ...

    async def get(self, resource_id: str, *, tenant_id: str | None = None) -> Lease: ...

    async def renew(self, lease: Lease, *, ttl_seconds: float) -> Lease: ...

    async def release(self, lease: Lease) -> None: ...

    async def assert_current(self, lease: Lease) -> None: ...

    async def purge_expired(self, *, now: datetime | None = None) -> int: ...


def _scope(tenant_id: str | None) -> str:
    return tenant_id or ""


def _ttl(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise ValueError("lease TTL must be finite and positive")
    return value


def _key(resource_id: str, tenant_id: str | None) -> tuple[str, str]:
    if not resource_id.strip():
        raise ValueError("resource_id cannot be blank")
    return _scope(tenant_id), resource_id


class MemoryLeaseStore:
    """Process-local lease implementation for tests and local deployments."""

    def __init__(self, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._leases: dict[tuple[str, str], Lease] = {}
        self._tokens: dict[tuple[str, str], int] = {}
        self._lock = asyncio.Lock()

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
        key = _key(resource_id, tenant_id)
        async with self._lock:
            now = self._clock()
            current = self._leases.get(key)
            if current is not None and current.expires_at > now:
                if current.owner_id == owner_id:
                    return current
                raise LeaseConflictError("Resource lease is already held")
            token = self._tokens.get(key, 0) + 1
            lease = Lease(
                resource_id=resource_id,
                owner_id=owner_id,
                tenant_id=tenant_id,
                fencing_token=token,
                acquired_at=now,
                expires_at=now + timedelta(seconds=ttl),
            )
            self._tokens[key] = token
            self._leases[key] = lease
            return lease

    async def get(self, resource_id: str, *, tenant_id: str | None = None) -> Lease:
        key = _key(resource_id, tenant_id)
        async with self._lock:
            current = self._leases.get(key)
            if current is None or current.expires_at <= self._clock():
                raise LeaseNotFoundError("Lease not found")
            return current

    async def renew(self, lease: Lease, *, ttl_seconds: float) -> Lease:
        ttl = _ttl(ttl_seconds)
        key = _key(lease.resource_id, lease.tenant_id)
        async with self._lock:
            now = self._clock()
            current = self._leases.get(key)
            self._require_current(current, lease, now)
            renewed = lease.model_copy(
                update={"expires_at": now + timedelta(seconds=ttl), "revision": lease.revision + 1}
            )
            self._leases[key] = renewed
            return renewed

    async def release(self, lease: Lease) -> None:
        key = _key(lease.resource_id, lease.tenant_id)
        async with self._lock:
            self._require_current(self._leases.get(key), lease, self._clock())
            del self._leases[key]

    async def assert_current(self, lease: Lease) -> None:
        key = _key(lease.resource_id, lease.tenant_id)
        async with self._lock:
            self._require_current(self._leases.get(key), lease, self._clock())

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        async with self._lock:
            keys = [key for key, lease in self._leases.items() if lease.expires_at <= moment]
            for key in keys:
                del self._leases[key]
            return len(keys)

    @staticmethod
    def _require_current(current: Lease | None, supplied: Lease, now: datetime) -> None:
        if current is None:
            raise LeaseNotFoundError("Lease not found")
        if current.expires_at <= now:
            raise LeaseConflictError("Lease has expired")
        if (
            current.lease_id != supplied.lease_id
            or current.owner_id != supplied.owner_id
            or current.fencing_token != supplied.fencing_token
            or current.revision != supplied.revision
        ):
            raise LeaseConflictError("Lease is stale")


class SQLiteLeaseStore:
    """Multi-process local lease store with transactional fencing counters."""

    schema_version = 1

    def __init__(self, path: str | Path, *, clock: Callable[[], datetime] = utc_now) -> None:
        self.path = Path(path)
        self._clock = clock
        self._lock = asyncio.Lock()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._db.execute("PRAGMA busy_timeout=5000")
            self._migrate()
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError("Cannot initialize SQLite lease store") from exc

    def _migrate(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
        )
        row = self._db.execute(
            "SELECT version FROM schema_migrations WHERE component='leases'"
        ).fetchone()
        version = 0 if row is None else int(row[0])
        if version > self.schema_version:
            raise PersistenceError("Lease database schema is newer than this package")
        if version == 0:
            self._db.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE coordination_lease_tokens (
                    tenant_scope TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    last_token INTEGER NOT NULL,
                    PRIMARY KEY (tenant_scope, resource_id)
                );
                CREATE TABLE coordination_leases (
                    tenant_scope TEXT NOT NULL,
                    resource_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_scope, resource_id)
                );
                INSERT INTO schema_migrations(component, version) VALUES ('leases', 1);
                COMMIT;
                """
            )

    async def aclose(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._db.close)

    async def __aenter__(self) -> SQLiteLeaseStore:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

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
        key = _key(resource_id, tenant_id)
        async with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                now = self._clock()
                row = self._db.execute(
                    "SELECT payload_json FROM coordination_leases "
                    "WHERE tenant_scope=? AND resource_id=?",
                    key,
                ).fetchone()
                if row is not None:
                    current = Lease.model_validate_json(row[0])
                    if current.expires_at > now:
                        if current.owner_id == owner_id:
                            self._db.execute("COMMIT")
                            return current
                        raise LeaseConflictError("Resource lease is already held")
                token_row = self._db.execute(
                    "SELECT last_token FROM coordination_lease_tokens "
                    "WHERE tenant_scope=? AND resource_id=?",
                    key,
                ).fetchone()
                token = (0 if token_row is None else int(token_row[0])) + 1
                lease = Lease(
                    resource_id=resource_id,
                    owner_id=owner_id,
                    tenant_id=tenant_id,
                    fencing_token=token,
                    acquired_at=now,
                    expires_at=now + timedelta(seconds=ttl),
                )
                self._db.execute(
                    "INSERT INTO coordination_lease_tokens VALUES (?, ?, ?) "
                    "ON CONFLICT(tenant_scope, resource_id) DO UPDATE SET "
                    "last_token=excluded.last_token",
                    (*key, token),
                )
                self._db.execute(
                    "INSERT INTO coordination_leases VALUES (?, ?, ?) "
                    "ON CONFLICT(tenant_scope, resource_id) DO UPDATE SET "
                    "payload_json=excluded.payload_json",
                    (*key, lease.model_dump_json()),
                )
                self._db.execute("COMMIT")
                return lease
            except (LeaseConflictError, ValueError):
                self._rollback()
                raise
            except sqlite3.Error as exc:
                self._rollback()
                raise PersistenceError("Cannot acquire SQLite lease") from exc

    async def get(self, resource_id: str, *, tenant_id: str | None = None) -> Lease:
        key = _key(resource_id, tenant_id)
        async with self._lock:
            try:
                row = self._db.execute(
                    "SELECT payload_json FROM coordination_leases "
                    "WHERE tenant_scope=? AND resource_id=?",
                    key,
                ).fetchone()
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot read SQLite lease") from exc
            if row is None:
                raise LeaseNotFoundError("Lease not found")
            lease = Lease.model_validate_json(row[0])
            if lease.expires_at <= self._clock():
                raise LeaseNotFoundError("Lease not found")
            return lease

    async def renew(self, lease: Lease, *, ttl_seconds: float) -> Lease:
        ttl = _ttl(ttl_seconds)
        async with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                current = self._load_for_update(lease)
                now = self._clock()
                MemoryLeaseStore._require_current(current, lease, now)
                renewed = lease.model_copy(
                    update={
                        "expires_at": now + timedelta(seconds=ttl),
                        "revision": lease.revision + 1,
                    }
                )
                self._db.execute(
                    "UPDATE coordination_leases SET payload_json=? "
                    "WHERE tenant_scope=? AND resource_id=?",
                    (renewed.model_dump_json(), _scope(lease.tenant_id), lease.resource_id),
                )
                self._db.execute("COMMIT")
                return renewed
            except (LeaseConflictError, LeaseNotFoundError):
                self._rollback()
                raise
            except sqlite3.Error as exc:
                self._rollback()
                raise PersistenceError("Cannot renew SQLite lease") from exc

    async def release(self, lease: Lease) -> None:
        async with self._lock:
            try:
                self._db.execute("BEGIN IMMEDIATE")
                current = self._load_for_update(lease)
                MemoryLeaseStore._require_current(current, lease, self._clock())
                self._db.execute(
                    "DELETE FROM coordination_leases WHERE tenant_scope=? AND resource_id=?",
                    (_scope(lease.tenant_id), lease.resource_id),
                )
                self._db.execute("COMMIT")
            except (LeaseConflictError, LeaseNotFoundError):
                self._rollback()
                raise
            except sqlite3.Error as exc:
                self._rollback()
                raise PersistenceError("Cannot release SQLite lease") from exc

    async def assert_current(self, lease: Lease) -> None:
        current = await self.get(lease.resource_id, tenant_id=lease.tenant_id)
        MemoryLeaseStore._require_current(current, lease, self._clock())

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        async with self._lock:
            rows = self._db.execute(
                "SELECT tenant_scope, resource_id, payload_json FROM coordination_leases"
            ).fetchall()
            expired = [
                (row[0], row[1])
                for row in rows
                if Lease.model_validate_json(row[2]).expires_at <= moment
            ]
            try:
                self._db.execute("BEGIN IMMEDIATE")
                self._db.executemany(
                    "DELETE FROM coordination_leases WHERE tenant_scope=? AND resource_id=?",
                    expired,
                )
                self._db.execute("COMMIT")
            except sqlite3.Error as exc:
                self._rollback()
                raise PersistenceError("Cannot purge SQLite leases") from exc
            return len(expired)

    def _load_for_update(self, lease: Lease) -> Lease | None:
        row = self._db.execute(
            "SELECT payload_json FROM coordination_leases WHERE tenant_scope=? AND resource_id=?",
            (_scope(lease.tenant_id), lease.resource_id),
        ).fetchone()
        return None if row is None else Lease.model_validate_json(row[0])

    def _rollback(self) -> None:
        try:
            if self._db.in_transaction:
                self._db.execute("ROLLBACK")
        except sqlite3.Error:
            return
