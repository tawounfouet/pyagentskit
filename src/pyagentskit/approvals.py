"""Persistent, tenant-scoped human approval contracts and stores."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime, timedelta
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from ._base import ContractModel
from .exceptions import ApprovalConflictError, ApprovalNotFoundError, PersistenceError
from .runs import utc_now
from .tools import ToolCall
from .types import Identifier, NonEmptyString

__all__ = [
    "ApprovalDecision",
    "ApprovalRequest",
    "ApprovalStatus",
    "ApprovalStore",
    "MemoryApprovalStore",
    "SQLiteApprovalStore",
    "tool_call_fingerprint",
]


class ApprovalDecision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"
    CANCEL = "cancel"


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    CLAIMED = "claimed"
    EXECUTED = "executed"
    EXPIRED = "expired"


def tool_call_fingerprint(call: ToolCall) -> str:
    """Bind an approval to the exact normalized tool name and arguments."""

    canonical = json.dumps(
        call.model_dump(mode="json", exclude={"metadata"}),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


class ApprovalRequest(ContractModel):
    approval_id: NonEmptyString = Field(default_factory=lambda: str(uuid4()))
    run_id: UUID
    trace_id: UUID
    agent_id: Identifier
    session_id: NonEmptyString
    tenant_id: str | None = None
    tool_call: ToolCall
    tool_fingerprint: NonEmptyString
    status: ApprovalStatus = ApprovalStatus.PENDING
    revision: int = Field(default=0, ge=0)
    requested_at: datetime = Field(default_factory=utc_now)
    expires_at: datetime | None = None
    resolved_at: datetime | None = None
    actor_id: str | None = None
    decision: ApprovalDecision | None = None
    reason: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_state(self) -> ApprovalRequest:
        for value in (self.requested_at, self.expires_at, self.resolved_at):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError("Approval timestamps must be timezone-aware")
        if self.expires_at is not None and self.expires_at <= self.requested_at:
            raise ValueError("Approval expiry must follow its request time")
        if self.tool_fingerprint != tool_call_fingerprint(self.tool_call):
            raise ValueError("Approval fingerprint does not match its tool call")
        terminal = self.status in {
            ApprovalStatus.APPROVED,
            ApprovalStatus.REJECTED,
            ApprovalStatus.CANCELLED,
            ApprovalStatus.CLAIMED,
            ApprovalStatus.EXECUTED,
        }
        if terminal and (self.decision is None or self.resolved_at is None or not self.actor_id):
            raise ValueError("Resolved approvals require decision, actor and timestamp")
        return self

    @classmethod
    def for_tool_call(
        cls,
        call: ToolCall,
        *,
        run_id: UUID,
        trace_id: UUID,
        agent_id: str,
        session_id: str,
        tenant_id: str | None = None,
        ttl_seconds: float | None = 3600,
        metadata: dict[str, Any] | None = None,
        clock: Callable[[], datetime] = utc_now,
    ) -> ApprovalRequest:
        now = clock()
        expires = None if ttl_seconds is None else now + timedelta(seconds=ttl_seconds)
        return cls(
            run_id=run_id,
            trace_id=trace_id,
            agent_id=agent_id,
            session_id=session_id,
            tenant_id=tenant_id,
            tool_call=call,
            tool_fingerprint=tool_call_fingerprint(call),
            requested_at=now,
            expires_at=expires,
            metadata={} if metadata is None else metadata,
        )


@runtime_checkable
class ApprovalStore(Protocol):
    async def create(self, request: ApprovalRequest) -> ApprovalRequest: ...

    async def get(self, approval_id: str, *, tenant_id: str | None = None) -> ApprovalRequest: ...

    async def list_pending(
        self, *, tenant_id: str | None = None, session_id: str | None = None
    ) -> tuple[ApprovalRequest, ...]: ...

    async def resolve(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        actor_id: str,
        reason: str | None = None,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest: ...

    async def claim(
        self,
        approval_id: str,
        *,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest: ...

    async def complete(
        self,
        approval_id: str,
        *,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest: ...


def _scope(tenant_id: str | None) -> str:
    return tenant_id or ""


def _effective(request: ApprovalRequest, now: datetime) -> ApprovalRequest:
    if (
        request.status is ApprovalStatus.PENDING
        and request.expires_at is not None
        and request.expires_at <= now
    ):
        return request.model_copy(
            update={"status": ApprovalStatus.EXPIRED, "revision": request.revision + 1}
        )
    return request


def _resolved(
    request: ApprovalRequest,
    decision: ApprovalDecision,
    actor_id: str,
    reason: str | None,
    now: datetime,
) -> ApprovalRequest:
    status = {
        ApprovalDecision.APPROVE: ApprovalStatus.APPROVED,
        ApprovalDecision.REJECT: ApprovalStatus.REJECTED,
        ApprovalDecision.CANCEL: ApprovalStatus.CANCELLED,
    }[decision]
    return request.model_copy(
        update={
            "status": status,
            "decision": decision,
            "actor_id": actor_id,
            "reason": reason,
            "resolved_at": now,
            "revision": request.revision + 1,
        }
    )


class MemoryApprovalStore:
    def __init__(self, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._items: dict[tuple[str, str], ApprovalRequest] = {}
        self._lock = asyncio.Lock()

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        key = (_scope(request.tenant_id), request.approval_id)
        async with self._lock:
            existing = self._items.get(key)
            if existing is not None:
                if existing.model_dump() != request.model_dump():
                    raise ApprovalConflictError("Approval ID already exists with different content")
                return existing
            self._items[key] = request
            return request

    async def get(self, approval_id: str, *, tenant_id: str | None = None) -> ApprovalRequest:
        key = (_scope(tenant_id), approval_id)
        async with self._lock:
            try:
                item = _effective(self._items[key], self._clock())
            except KeyError as exc:
                raise ApprovalNotFoundError("Approval not found") from exc
            self._items[key] = item
            return item

    async def list_pending(
        self, *, tenant_id: str | None = None, session_id: str | None = None
    ) -> tuple[ApprovalRequest, ...]:
        async with self._lock:
            now = self._clock()
            result = []
            for key, item in tuple(self._items.items()):
                current = _effective(item, now)
                self._items[key] = current
                if (
                    key[0] == _scope(tenant_id)
                    and current.status is ApprovalStatus.PENDING
                    and (session_id is None or current.session_id == session_id)
                ):
                    result.append(current)
            return tuple(sorted(result, key=lambda item: item.requested_at))

    async def resolve(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        actor_id: str,
        reason: str | None = None,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest:
        async with self._lock:
            key = (_scope(tenant_id), approval_id)
            if key not in self._items:
                raise ApprovalNotFoundError("Approval not found")
            current = _effective(self._items[key], self._clock())
            if current.status is not ApprovalStatus.PENDING:
                if current.decision is decision and current.actor_id == actor_id:
                    return current
                raise ApprovalConflictError("Approval is no longer pending")
            if expected_revision is not None and current.revision != expected_revision:
                raise ApprovalConflictError("Approval revision conflict")
            if not actor_id.strip():
                raise ApprovalConflictError("Approval actor cannot be blank")
            updated = _resolved(current, decision, actor_id, reason, self._clock())
            self._items[key] = updated
            return updated

    async def claim(
        self,
        approval_id: str,
        *,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest:
        async with self._lock:
            key = (_scope(tenant_id), approval_id)
            if key not in self._items:
                raise ApprovalNotFoundError("Approval not found")
            current = _effective(self._items[key], self._clock())
            if current.status not in {
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.CANCELLED,
            }:
                raise ApprovalConflictError("Approval decision cannot be claimed")
            if expected_revision is not None and current.revision != expected_revision:
                raise ApprovalConflictError("Approval revision conflict")
            updated = current.model_copy(
                update={"status": ApprovalStatus.CLAIMED, "revision": current.revision + 1}
            )
            self._items[key] = updated
            return updated

    async def complete(
        self,
        approval_id: str,
        *,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest:
        return await self._transition(
            approval_id,
            ApprovalStatus.CLAIMED,
            ApprovalStatus.EXECUTED,
            tenant_id,
            expected_revision,
        )

    async def _transition(
        self,
        approval_id: str,
        source: ApprovalStatus,
        target: ApprovalStatus,
        tenant_id: str | None,
        expected_revision: int | None,
    ) -> ApprovalRequest:
        async with self._lock:
            key = (_scope(tenant_id), approval_id)
            if key not in self._items:
                raise ApprovalNotFoundError("Approval not found")
            current = self._items[key]
            if current.status is not source:
                raise ApprovalConflictError(f"Approval must be {source.value}")
            if expected_revision is not None and current.revision != expected_revision:
                raise ApprovalConflictError("Approval revision conflict")
            updated = current.model_copy(
                update={"status": target, "revision": current.revision + 1}
            )
            self._items[key] = updated
            return updated


class SQLiteApprovalStore(MemoryApprovalStore):
    """SQLite-backed approval store with transactional state transitions."""

    schema_version = 1

    def __init__(self, path: str | Path, *, clock: Callable[[], datetime] = utc_now) -> None:
        self.path = Path(path)
        self._clock = clock
        self._lock = asyncio.Lock()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._migrate()
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError("Cannot initialize SQLite approval store") from exc

    def _migrate(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
        )
        row = self._db.execute(
            "SELECT version FROM schema_migrations WHERE component='approvals'"
        ).fetchone()
        version = 0 if row is None else int(row[0])
        if version > self.schema_version:
            raise PersistenceError("Approval database schema is newer than this package")
        if version == 0:
            self._db.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE approvals (
                    tenant_scope TEXT NOT NULL,
                    approval_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_scope, approval_id)
                );
                INSERT INTO schema_migrations(component, version) VALUES ('approvals', 1);
                COMMIT;
                """
            )

    async def aclose(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._db.close)

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        async with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                key = (_scope(request.tenant_id), request.approval_id)
                row = self._db.execute(
                    "SELECT payload_json FROM approvals WHERE tenant_scope=? AND approval_id=?",
                    key,
                ).fetchone()
                if row is not None:
                    existing = ApprovalRequest.model_validate_json(row[0])
                    if existing.model_dump() != request.model_dump():
                        raise ApprovalConflictError(
                            "Approval ID already exists with different content"
                        )
                    self._db.execute("COMMIT")
                    return existing
                self._db.execute(
                    "INSERT INTO approvals(tenant_scope, approval_id, payload_json) "
                    "VALUES (?, ?, ?)",
                    (*key, request.model_dump_json()),
                )
                self._db.execute("COMMIT")
                return request
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    async def get(self, approval_id: str, *, tenant_id: str | None = None) -> ApprovalRequest:
        async with self._lock:
            return self._load_locked(approval_id, tenant_id, expire=True)

    async def list_pending(
        self, *, tenant_id: str | None = None, session_id: str | None = None
    ) -> tuple[ApprovalRequest, ...]:
        async with self._lock:
            rows = self._db.execute(
                "SELECT approval_id FROM approvals WHERE tenant_scope=?",
                (_scope(tenant_id),),
            ).fetchall()
            items = [self._load_locked(str(row[0]), tenant_id, expire=True) for row in rows]
            return tuple(
                sorted(
                    (
                        item
                        for item in items
                        if item.status is ApprovalStatus.PENDING
                        and (session_id is None or item.session_id == session_id)
                    ),
                    key=lambda item: item.requested_at,
                )
            )

    async def resolve(
        self,
        approval_id: str,
        decision: ApprovalDecision,
        *,
        actor_id: str,
        reason: str | None = None,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest:
        async with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                current = self._load_locked(approval_id, tenant_id, expire=True)
                if current.status is not ApprovalStatus.PENDING:
                    if current.decision is decision and current.actor_id == actor_id:
                        self._db.execute("COMMIT")
                        return current
                    raise ApprovalConflictError("Approval is no longer pending")
                if expected_revision is not None and current.revision != expected_revision:
                    raise ApprovalConflictError("Approval revision conflict")
                if not actor_id.strip():
                    raise ApprovalConflictError("Approval actor cannot be blank")
                updated = self._save_locked(
                    _resolved(current, decision, actor_id, reason, self._clock())
                )
                self._db.execute("COMMIT")
                return updated
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    async def claim(
        self,
        approval_id: str,
        *,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest:
        async with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                current = self._load_locked(approval_id, tenant_id, expire=True)
                if current.status not in {
                    ApprovalStatus.APPROVED,
                    ApprovalStatus.REJECTED,
                    ApprovalStatus.CANCELLED,
                }:
                    raise ApprovalConflictError("Approval decision cannot be claimed")
                if expected_revision is not None and current.revision != expected_revision:
                    raise ApprovalConflictError("Approval revision conflict")
                updated = self._save_locked(
                    current.model_copy(
                        update={
                            "status": ApprovalStatus.CLAIMED,
                            "revision": current.revision + 1,
                        }
                    )
                )
                self._db.execute("COMMIT")
                return updated
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    async def complete(
        self,
        approval_id: str,
        *,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest:
        return await self._transition_sql(
            approval_id,
            ApprovalStatus.CLAIMED,
            ApprovalStatus.EXECUTED,
            tenant_id,
            expected_revision,
        )

    async def _transition_sql(
        self,
        approval_id: str,
        source: ApprovalStatus,
        target: ApprovalStatus,
        tenant_id: str | None,
        expected_revision: int | None,
    ) -> ApprovalRequest:
        async with self._lock:
            self._db.execute("BEGIN IMMEDIATE")
            try:
                current = self._load_locked(approval_id, tenant_id, expire=True)
                if current.status is not source:
                    raise ApprovalConflictError(f"Approval must be {source.value}")
                if expected_revision is not None and current.revision != expected_revision:
                    raise ApprovalConflictError("Approval revision conflict")
                updated = self._save_locked(
                    current.model_copy(update={"status": target, "revision": current.revision + 1})
                )
                self._db.execute("COMMIT")
                return updated
            except Exception:
                if self._db.in_transaction:
                    self._db.execute("ROLLBACK")
                raise

    def _load_locked(
        self, approval_id: str, tenant_id: str | None, *, expire: bool
    ) -> ApprovalRequest:
        row = self._db.execute(
            "SELECT payload_json FROM approvals WHERE tenant_scope=? AND approval_id=?",
            (_scope(tenant_id), approval_id),
        ).fetchone()
        if row is None:
            raise ApprovalNotFoundError("Approval not found")
        current = ApprovalRequest.model_validate_json(row[0])
        effective = _effective(current, self._clock()) if expire else current
        if effective is not current:
            return self._save_locked(effective)
        return current

    def _save_locked(self, request: ApprovalRequest) -> ApprovalRequest:
        self._db.execute(
            "UPDATE approvals SET payload_json=? WHERE tenant_scope=? AND approval_id=?",
            (request.model_dump_json(), _scope(request.tenant_id), request.approval_id),
        )
        return request
