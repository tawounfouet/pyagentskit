"""SQLite compatibility adapter for PyAgentsKit V2 persistence.

SQLite is a local/dev durability target. It intentionally implements the same
safety-critical contracts as production stores: optimistic concurrency,
physical Effect idempotency, monotonic fencing, Inbox deduplication and an
explicit local UnitOfWork.
"""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import Callable
from contextvars import ContextVar, Token
from datetime import UTC, datetime, timedelta
from importlib.resources import files
from pathlib import Path
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
from ...domain.entities import Approval, AuditEvent, Lease, MemoryEntry, Run
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
)
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
)

ResultT = TypeVar("ResultT")


def _iso(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _from_iso(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


class _SQLiteDatabase:
    schema_version = 2

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = asyncio.Lock()
        self._transaction: ContextVar[bool] = ContextVar(
            f"pyagentskit_sqlite_v2_{id(self)}",
            default=False,
        )
        try:
            self.connection = sqlite3.connect(
                self.path,
                check_same_thread=False,
                isolation_level=None,
            )
            self.connection.row_factory = sqlite3.Row
            self.connection.execute("PRAGMA journal_mode=WAL")
            self.connection.execute("PRAGMA foreign_keys=ON")
            self.connection.execute("PRAGMA busy_timeout=5000")
            self._migrate()
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError("cannot initialize SQLite V2 persistence") from exc

    def _migrate(self) -> None:
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS v2_schema_migrations "
            "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
        )
        row = self.connection.execute(
            "SELECT version FROM v2_schema_migrations WHERE component='persistence_v2'"
        ).fetchone()
        current = 0 if row is None else int(row["version"])
        if current > self.schema_version:
            raise PersistenceError("SQLite V2 schema is newer than this package")
        migrations = {
            1: "0001_v2_core.sql",
            2: "0002_v2_catalog.sql",
        }
        try:
            for version in range(current + 1, self.schema_version + 1):
                migration = (
                    files("pyagentskit.adapters.persistence.migrations.sqlite")
                    .joinpath(migrations[version])
                    .read_text(encoding="utf-8")
                )
                self.connection.executescript(migration)
        except sqlite3.Error as exc:
            raise PersistenceError("cannot migrate SQLite V2 persistence") from exc

    async def call(self, operation: Callable[[], ResultT]) -> ResultT:
        if self._transaction.get():
            return operation()
        async with self._lock:
            try:
                return await asyncio.to_thread(operation)
            except sqlite3.Error as exc:
                raise PersistenceError("SQLite V2 persistence operation failed") from exc

    async def atomic(self, operation: Callable[[], ResultT]) -> ResultT:
        if self._transaction.get():
            return operation()
        async with self._lock:
            try:
                await asyncio.to_thread(self.connection.execute, "BEGIN IMMEDIATE")
                result = await asyncio.to_thread(operation)
                await asyncio.to_thread(self.connection.execute, "COMMIT")
                return result
            except Exception:
                if self.connection.in_transaction:
                    await asyncio.to_thread(self.connection.execute, "ROLLBACK")
                raise

    async def begin(self) -> Token[bool]:
        await self._lock.acquire()
        token = self._transaction.set(True)
        try:
            await asyncio.to_thread(self.connection.execute, "BEGIN IMMEDIATE")
        except Exception:
            self._transaction.reset(token)
            self._lock.release()
            raise
        return token

    async def commit(self, token: Token[bool]) -> None:
        try:
            await asyncio.to_thread(self.connection.execute, "COMMIT")
        finally:
            self._transaction.reset(token)
            self._lock.release()

    async def rollback(self, token: Token[bool]) -> None:
        try:
            if self.connection.in_transaction:
                await asyncio.to_thread(self.connection.execute, "ROLLBACK")
        finally:
            self._transaction.reset(token)
            self._lock.release()

    async def close(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self.connection.close)


class _SQLiteRepository:
    def __init__(self, database: _SQLiteDatabase | str | Path) -> None:
        self._db = database if isinstance(database, _SQLiteDatabase) else _SQLiteDatabase(database)

    async def close(self) -> None:
        await self._db.close()


class SQLiteRunRepository(_SQLiteRepository):
    async def get(self, run_id: RunId) -> Run | None:
        def operation() -> Run | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_runs WHERE id=?",
                (str(run_id),),
            ).fetchone()
            return None if row is None else run_from_document(loads(row["payload_json"]))

        return await self._db.call(operation)

    async def add(self, run: Run) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_runs(id, tenant_id, status, version, payload_json) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (
                        str(run.id),
                        str(run.tenant_id),
                        run.status.value,
                        run.version.value,
                        dumps(run_to_document(run)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(f"run {run.id} already exists") from exc

        await self._db.call(operation)

    async def save(self, run: Run, *, expected_version: AggregateVersion) -> None:
        if run.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")

        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_runs SET tenant_id=?, status=?, version=?, payload_json=? "
                "WHERE id=? AND version=?",
                (
                    str(run.tenant_id),
                    run.status.value,
                    run.version.value,
                    dumps(run_to_document(run)),
                    str(run.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(f"stale or missing run {run.id}")

        await self._db.call(operation)

    async def list_by_state(self, status: RunStatus) -> tuple[Run, ...]:
        def operation() -> tuple[Run, ...]:
            rows = self._db.connection.execute(
                "SELECT payload_json FROM v2_runs WHERE status=? ORDER BY id",
                (status.value,),
            ).fetchall()
            return tuple(run_from_document(loads(row["payload_json"])) for row in rows)

        return await self._db.call(operation)


class SQLiteEffectRepository(_SQLiteRepository):
    async def get(self, effect_id: EffectId) -> Effect:
        def operation() -> Effect:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_effects WHERE id=?",
                (str(effect_id),),
            ).fetchone()
            if row is None:
                raise KeyError(str(effect_id))
            return effect_from_document(loads(row["payload_json"]))

        return await self._db.call(operation)

    async def reserve(self, effect: Effect) -> EffectReservationResult:
        def operation() -> EffectReservationResult:
            key = effect.idempotency_key
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_effects("
                    "id, run_id, status, idempotency_scope, idempotency_namespace, "
                    "idempotency_key, fingerprint, version, payload_json"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(effect.id),
                        str(effect.run_id),
                        effect.status.value,
                        effect.idempotency_scope.value,
                        None if key is None else key.namespace,
                        None if key is None else key.key,
                        effect.fingerprint.value,
                        effect.version.value,
                        dumps(effect_to_document(effect)),
                    ),
                )
                return EffectReservationResult(effect=effect, created=True)
            except sqlite3.IntegrityError:
                row = None
                if key is not None:
                    row = self._db.connection.execute(
                        "SELECT payload_json FROM v2_effects "
                        "WHERE idempotency_scope=? AND idempotency_namespace=? "
                        "AND idempotency_key=?",
                        (
                            effect.idempotency_scope.value,
                            key.namespace,
                            key.key,
                        ),
                    ).fetchone()
                if row is None:
                    row = self._db.connection.execute(
                        "SELECT payload_json FROM v2_effects WHERE id=?",
                        (str(effect.id),),
                    ).fetchone()
                if row is None:
                    raise
                existing = effect_from_document(loads(row["payload_json"]))
                existing.assert_same_intent(effect.idempotency_key, effect.fingerprint)
                return EffectReservationResult(effect=existing, created=False)

        try:
            return await self._db.call(operation)
        except IdempotencyConflictError:
            raise

    async def find_by_idempotency_key(
        self,
        scope: IdempotencyScope,
        key: IdempotencyKey,
    ) -> Effect | None:
        def operation() -> Effect | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_effects "
                "WHERE idempotency_scope=? AND idempotency_namespace=? "
                "AND idempotency_key=?",
                (scope.value, key.namespace, key.key),
            ).fetchone()
            return None if row is None else effect_from_document(loads(row["payload_json"]))

        return await self._db.call(operation)

    async def save(
        self,
        effect: Effect,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if effect.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")

        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_effects SET run_id=?, status=?, fingerprint=?, version=?, "
                "payload_json=? WHERE id=? AND version=?",
                (
                    str(effect.run_id),
                    effect.status.value,
                    effect.fingerprint.value,
                    effect.version.value,
                    dumps(effect_to_document(effect)),
                    str(effect.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(f"stale or missing effect {effect.id}")

        await self._db.call(operation)


class SQLiteMemoryRepository(_SQLiteRepository):
    async def get(self, memory_id: MemoryEntryId) -> MemoryEntry | None:
        def operation() -> MemoryEntry | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_memory_entries WHERE id=?",
                (str(memory_id),),
            ).fetchone()
            return None if row is None else memory_from_document(loads(row["payload_json"]))

        return await self._db.call(operation)

    async def put(self, entry: MemoryEntry) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_memory_entries("
                    "id, tenant_id, scope, scope_id, memory_key, version, payload_json"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(entry.id),
                        str(entry.tenant_id),
                        entry.scope.value,
                        entry.scope_id,
                        entry.key,
                        entry.version.value,
                        dumps(memory_to_document(entry)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(f"memory entry {entry.id} already exists") from exc

        await self._db.call(operation)

    async def save(
        self,
        entry: MemoryEntry,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if entry.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")

        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_memory_entries SET tenant_id=?, scope=?, scope_id=?, "
                "memory_key=?, version=?, payload_json=? WHERE id=? AND version=?",
                (
                    str(entry.tenant_id),
                    entry.scope.value,
                    entry.scope_id,
                    entry.key,
                    entry.version.value,
                    dumps(memory_to_document(entry)),
                    str(entry.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(f"stale or missing memory entry {entry.id}")

        await self._db.call(operation)

    async def list_by_scope(
        self,
        *,
        tenant_id: str,
        scope: str,
        scope_id: str | None,
    ) -> tuple[MemoryEntry, ...]:
        def operation() -> tuple[MemoryEntry, ...]:
            if scope_id is None:
                rows = self._db.connection.execute(
                    "SELECT payload_json FROM v2_memory_entries "
                    "WHERE tenant_id=? AND scope=? AND scope_id IS NULL ORDER BY id",
                    (tenant_id, scope),
                ).fetchall()
            else:
                rows = self._db.connection.execute(
                    "SELECT payload_json FROM v2_memory_entries "
                    "WHERE tenant_id=? AND scope=? AND scope_id=? ORDER BY id",
                    (tenant_id, scope, scope_id),
                ).fetchall()
            return tuple(memory_from_document(loads(row["payload_json"])) for row in rows)

        return await self._db.call(operation)


class SQLiteReconciliationRepository(_SQLiteRepository):
    async def get_active(self, effect_id: EffectId) -> ReconciliationCase | None:
        def operation() -> ReconciliationCase | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_reconciliation_cases "
                "WHERE effect_id=? AND status NOT IN ('resolved_success','resolved_failure') "
                "ORDER BY created_at DESC LIMIT 1",
                (str(effect_id),),
            ).fetchone()
            return (
                None
                if row is None
                else reconciliation_case_from_document(loads(row["payload_json"]))
            )

        return await self._db.call(operation)

    async def save(
        self,
        case: ReconciliationCase,
        *,
        expected_version: AggregateVersion | None,
    ) -> None:
        if expected_version is None:

            def insert() -> None:
                try:
                    self._db.connection.execute(
                        "INSERT INTO v2_reconciliation_cases("
                        "id, effect_id, status, version, created_at, payload_json"
                        ") VALUES (?, ?, ?, ?, ?, ?)",
                        (
                            str(case.id),
                            str(case.effect_id),
                            case.status.value,
                            case.version.value,
                            case.created_at.isoformat(),
                            dumps(reconciliation_case_to_document(case)),
                        ),
                    )
                except sqlite3.IntegrityError as exc:
                    raise DuplicateAggregateError(
                        f"reconciliation case {case.id} already exists"
                    ) from exc

            await self._db.call(insert)
            return

        if case.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")

        def update() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_reconciliation_cases SET effect_id=?, status=?, version=?, "
                "created_at=?, payload_json=? WHERE id=? AND version=?",
                (
                    str(case.effect_id),
                    case.status.value,
                    case.version.value,
                    case.created_at.isoformat(),
                    dumps(reconciliation_case_to_document(case)),
                    str(case.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(f"stale or missing reconciliation case {case.id}")

        await self._db.call(update)

    async def append_evidence(self, evidence: ReconciliationEvidence) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_reconciliation_evidence("
                    "id, case_id, observed_at, payload_json"
                    ") VALUES (?, ?, ?, ?)",
                    (
                        str(evidence.id),
                        str(evidence.case_id),
                        evidence.observed_at.isoformat(),
                        dumps(reconciliation_evidence_to_document(evidence)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(
                    f"reconciliation evidence {evidence.id} already exists"
                ) from exc

        await self._db.call(operation)


class SQLiteApprovalRepository(_SQLiteRepository):
    async def get(self, approval_id: ApprovalId) -> Approval | None:
        def operation() -> Approval | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_approvals WHERE id=?",
                (str(approval_id),),
            ).fetchone()
            return None if row is None else approval_from_document(loads(row["payload_json"]))

        return await self._db.call(operation)

    async def add(self, approval: Approval) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_approvals(id, status, version, payload_json) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        str(approval.id),
                        approval.status.value,
                        approval.version.value,
                        dumps(approval_to_document(approval)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(f"approval {approval.id} already exists") from exc

        await self._db.call(operation)

    async def save(
        self,
        approval: Approval,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if approval.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")

        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_approvals SET status=?, version=?, payload_json=? "
                "WHERE id=? AND version=?",
                (
                    approval.status.value,
                    approval.version.value,
                    dumps(approval_to_document(approval)),
                    str(approval.id),
                    expected_version.value,
                ),
            )
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(f"stale or missing approval {approval.id}")

        await self._db.call(operation)

    async def list_pending(self) -> tuple[Approval, ...]:
        def operation() -> tuple[Approval, ...]:
            rows = self._db.connection.execute(
                "SELECT payload_json FROM v2_approvals WHERE status=? ORDER BY id",
                (ApprovalStatus.PENDING.value,),
            ).fetchall()
            return tuple(approval_from_document(loads(row["payload_json"])) for row in rows)

        return await self._db.call(operation)


class SQLiteLeaseRepository(_SQLiteRepository):
    async def get_current(self, resource: str) -> Lease | None:
        def operation() -> Lease | None:
            row = self._db.connection.execute(
                "SELECT payload_json FROM v2_leases WHERE resource=? "
                "ORDER BY fencing_token DESC LIMIT 1",
                (resource,),
            ).fetchone()
            return None if row is None else lease_from_document(loads(row["payload_json"]))

        return await self._db.call(operation)

    async def add(self, lease: Lease) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_leases("
                    "id, resource, status, worker_id, fencing_token, version, payload_json"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        str(lease.id),
                        lease.resource,
                        lease.status.value,
                        None if lease.worker_id is None else str(lease.worker_id),
                        lease.fencing_token.value,
                        lease.version.value,
                        dumps(lease_to_document(lease)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                existing = self._db.connection.execute(
                    "SELECT id FROM v2_leases WHERE id=?",
                    (str(lease.id),),
                ).fetchone()
                if existing is not None:
                    raise DuplicateAggregateError(f"lease {lease.id} already exists") from exc
                raise ConcurrencyConflictError(
                    f"resource {lease.resource} already has an active lease"
                ) from exc

        await self._db.call(operation)

    async def save(
        self,
        lease: Lease,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        if lease.version != expected_version.next():
            raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")

        def operation() -> None:
            try:
                cursor = self._db.connection.execute(
                    "UPDATE v2_leases SET resource=?, status=?, worker_id=?, "
                    "fencing_token=?, version=?, payload_json=? "
                    "WHERE id=? AND version=?",
                    (
                        lease.resource,
                        lease.status.value,
                        None if lease.worker_id is None else str(lease.worker_id),
                        lease.fencing_token.value,
                        lease.version.value,
                        dumps(lease_to_document(lease)),
                        str(lease.id),
                        expected_version.value,
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise ConcurrencyConflictError(
                    f"resource {lease.resource} already has an active lease"
                ) from exc
            if cursor.rowcount != 1:
                raise ConcurrencyConflictError(f"stale or missing lease {lease.id}")

        await self._db.call(operation)

    async def next_fencing_token(self, resource: str) -> FencingToken:
        def operation() -> FencingToken:
            row = self._db.connection.execute(
                "INSERT INTO v2_fencing_counters(resource, last_token) VALUES (?, 1) "
                "ON CONFLICT(resource) DO UPDATE SET last_token=last_token+1 "
                "RETURNING last_token",
                (resource,),
            ).fetchone()
            if row is None:
                raise PersistenceError("SQLite fencing counter did not return a token")
            return FencingToken(int(row["last_token"]))

        return await self._db.atomic(operation)


class SQLiteAuditStore(_SQLiteRepository):
    async def append(self, event: AuditEvent) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_audit_events(id, subject, occurred_at, payload_json) "
                    "VALUES (?, ?, ?, ?)",
                    (
                        str(event.id),
                        event.subject,
                        event.occurred_at.isoformat(),
                        dumps(audit_to_document(event)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(f"audit event {event.id} already exists") from exc

        await self._db.call(operation)

    async def list_for_subject(self, subject: str) -> tuple[AuditEvent, ...]:
        def operation() -> tuple[AuditEvent, ...]:
            rows = self._db.connection.execute(
                "SELECT payload_json FROM v2_audit_events WHERE subject=? ORDER BY occurred_at, id",
                (subject,),
            ).fetchall()
            return tuple(audit_from_document(loads(row["payload_json"])) for row in rows)

        return await self._db.call(operation)


class SQLiteOutboxStore(_SQLiteRepository):
    async def append(self, event: IntegrationEvent) -> None:
        def operation() -> None:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_outbox_events("
                    "event_id, status, attempt_count, occurred_at, event_json"
                    ") VALUES (?, ?, 0, ?, ?)",
                    (
                        event.event_id,
                        OutboxStatus.PENDING.value,
                        event.occurred_at.isoformat(),
                        dumps(integration_event_to_document(event)),
                    ),
                )
            except sqlite3.IntegrityError as exc:
                raise DuplicateAggregateError(
                    f"outbox event {event.event_id} already exists"
                ) from exc

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

        def operation() -> tuple[OutboxRecord, ...]:
            now = datetime.now(UTC)
            stale_before = now - timedelta(seconds=claim_timeout_seconds)
            rows = self._db.connection.execute(
                "SELECT event_id, event_json, status, attempt_count, next_attempt_at, "
                "claimed_by, claimed_at, published_at, last_error FROM v2_outbox_events "
                "WHERE (status IN (?, ?) OR "
                "(status=? AND claimed_at IS NOT NULL AND claimed_at<=?)) "
                "AND (next_attempt_at IS NULL OR next_attempt_at<=?) "
                "ORDER BY occurred_at, event_id LIMIT ?",
                (
                    OutboxStatus.PENDING.value,
                    OutboxStatus.FAILED.value,
                    OutboxStatus.CLAIMED.value,
                    stale_before.isoformat(),
                    now.isoformat(),
                    limit,
                ),
            ).fetchall()
            records: list[OutboxRecord] = []
            for row in rows:
                attempts = int(row["attempt_count"]) + 1
                self._db.connection.execute(
                    "UPDATE v2_outbox_events SET status=?, claimed_by=?, claimed_at=?, "
                    "attempt_count=? WHERE event_id=?",
                    (
                        OutboxStatus.CLAIMED.value,
                        worker_id,
                        now.isoformat(),
                        attempts,
                        row["event_id"],
                    ),
                )
                records.append(
                    OutboxRecord(
                        event=integration_event_from_document(loads(row["event_json"])),
                        status=OutboxStatus.CLAIMED,
                        attempt_count=attempts,
                        next_attempt_at=_from_iso(row["next_attempt_at"]),
                        claimed_by=worker_id,
                        claimed_at=now,
                        published_at=_from_iso(row["published_at"]),
                        last_error=row["last_error"],
                    )
                )
            return tuple(records)

        return await self._db.atomic(operation)

    async def mark_published(self, event_id: str) -> None:
        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_outbox_events SET status=?, claimed_by=NULL, "
                "claimed_at=NULL, published_at=?, last_error=NULL WHERE event_id=?",
                (
                    OutboxStatus.PUBLISHED.value,
                    datetime.now(UTC).isoformat(),
                    event_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError(event_id)

        await self._db.call(operation)

    async def mark_failed(self, event_id: str, *, error: str) -> None:
        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_outbox_events SET status=?, claimed_by=NULL, "
                "claimed_at=NULL, last_error=? WHERE event_id=?",
                (OutboxStatus.FAILED.value, error, event_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(event_id)

        await self._db.call(operation)

    async def release_claim(self, event_id: str) -> None:
        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_outbox_events SET status=?, claimed_by=NULL, "
                "claimed_at=NULL WHERE event_id=?",
                (OutboxStatus.PENDING.value, event_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(event_id)

        await self._db.call(operation)


class SQLiteInboxStore(_SQLiteRepository):
    async def reserve(self, record: InboxRecord) -> bool:
        def operation() -> bool:
            try:
                self._db.connection.execute(
                    "INSERT INTO v2_inbox_events("
                    "source, external_event_id, digest, status, tenant_id, "
                    "processed_at, last_error"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        record.source,
                        record.external_event_id,
                        record.digest,
                        record.status.value,
                        record.tenant_id,
                        _iso(record.processed_at),
                        record.last_error,
                    ),
                )
                return True
            except sqlite3.IntegrityError:
                row = self._db.connection.execute(
                    "SELECT digest FROM v2_inbox_events WHERE source=? AND external_event_id=?",
                    (record.source, record.external_event_id),
                ).fetchone()
                if row is None:
                    raise
                if str(row["digest"]) != record.digest:
                    raise InboxDigestConflictError(
                        "external event id was reused with a different digest"
                    ) from None
                return False

        return await self._db.call(operation)

    async def get(
        self,
        source: str,
        external_event_id: str,
    ) -> InboxRecord | None:
        def operation() -> InboxRecord | None:
            row = self._db.connection.execute(
                "SELECT digest, status, tenant_id, processed_at, last_error "
                "FROM v2_inbox_events WHERE source=? AND external_event_id=?",
                (source, external_event_id),
            ).fetchone()
            if row is None:
                return None
            return InboxRecord(
                source=source,
                external_event_id=external_event_id,
                digest=str(row["digest"]),
                status=InboxStatus(str(row["status"])),
                tenant_id=row["tenant_id"],
                processed_at=_from_iso(row["processed_at"]),
                last_error=row["last_error"],
            )

        return await self._db.call(operation)

    async def mark_processed(self, source: str, external_event_id: str) -> None:
        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_inbox_events SET status=?, processed_at=?, last_error=NULL "
                "WHERE source=? AND external_event_id=?",
                (
                    InboxStatus.PROCESSED.value,
                    datetime.now(UTC).isoformat(),
                    source,
                    external_event_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError((source, external_event_id))

        await self._db.call(operation)

    async def mark_failed(
        self,
        source: str,
        external_event_id: str,
        *,
        error: str,
    ) -> None:
        def operation() -> None:
            cursor = self._db.connection.execute(
                "UPDATE v2_inbox_events SET status=?, last_error=? "
                "WHERE source=? AND external_event_id=?",
                (
                    InboxStatus.FAILED.value,
                    error,
                    source,
                    external_event_id,
                ),
            )
            if cursor.rowcount != 1:
                raise KeyError((source, external_event_id))

        await self._db.call(operation)


class SQLiteUnitOfWork:
    """One explicit local SQLite transaction for authoritative state + outbox."""

    def __init__(self, path: str | Path) -> None:
        self._db = _SQLiteDatabase(path)
        self.runs = SQLiteRunRepository(self._db)
        self.effects = SQLiteEffectRepository(self._db)
        self.memories = SQLiteMemoryRepository(self._db)
        self.reconciliations = SQLiteReconciliationRepository(self._db)
        self.approvals = SQLiteApprovalRepository(self._db)
        self.outbox = SQLiteOutboxStore(self._db)
        self.audit = SQLiteAuditStore(self._db)
        self._token: Token[bool] | None = None
        self._committed = False

    async def __aenter__(self) -> SQLiteUnitOfWork:
        if self._token is not None:
            raise RuntimeError("SQLiteUnitOfWork is already active")
        self._committed = False
        self._token = await self._db.begin()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if self._token is None:
            return
        token = self._token
        self._token = None
        if exc_type is not None or not self._committed:
            await self._db.rollback(token)
        else:
            await self._db.commit(token)

    async def commit(self) -> None:
        if self._token is None:
            raise RuntimeError("SQLiteUnitOfWork is not active")
        self._committed = True

    async def rollback(self) -> None:
        if self._token is None:
            return
        token = self._token
        self._token = None
        await self._db.rollback(token)

    async def close(self) -> None:
        if self._token is not None:
            await self.rollback()
        await self._db.close()


__all__ = [
    "SQLiteApprovalRepository",
    "SQLiteAuditStore",
    "SQLiteEffectRepository",
    "SQLiteInboxStore",
    "SQLiteLeaseRepository",
    "SQLiteMemoryRepository",
    "SQLiteOutboxStore",
    "SQLiteReconciliationRepository",
    "SQLiteRunRepository",
    "SQLiteUnitOfWork",
]
