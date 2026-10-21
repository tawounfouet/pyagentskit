"""Production PostgreSQL stores for sessions, memories and approvals.

The adapters depend only on the small asyncpg-compatible ports declared in
``pyagentskit.postgres``. Importing this module never imports a database driver
and never opens a connection.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import datetime
from typing import Any, TypeVar
from uuid import UUID

from pydantic import Field

from ._base import ContractModel
from .approvals import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    _effective,
    _resolved,
)
from .exceptions import (
    ApprovalConflictError,
    ApprovalNotFoundError,
    PersistenceError,
    PyAgentsKitError,
    SessionConflictError,
    SessionError,
    SessionNotFoundError,
)
from .memory import MemoryRecord, _matches, _visible
from .messages import Message
from .postgres import AsyncPostgresConnection, AsyncPostgresPool, _json_payload, _PostgresStore
from .runs import utc_now
from .sessions import Session, SessionEntry, _append_fingerprint, _expired

__all__ = [
    "PostgresApprovalStore",
    "PostgresMemoryStore",
    "PostgresSessionStore",
]

_T = TypeVar("_T")


def _scope(tenant_id: str | None) -> str:
    return tenant_id or ""


def _count(status: str) -> int:
    try:
        return int(status.rsplit(" ", 1)[-1])
    except (ValueError, IndexError) as exc:
        raise PersistenceError("PostgreSQL returned an invalid command status") from exc


class _SessionDocument(ContractModel):
    session: Session
    entries: tuple[SessionEntry, ...] = ()
    appends: dict[str, tuple[str, tuple[int, ...]]] = Field(default_factory=dict)


class _StateStore(_PostgresStore):
    """Shared versioned JSONB table and query helpers."""

    schema_version = 2

    def __init__(
        self,
        pool: AsyncPostgresPool,
        *,
        table_prefix: str = "pyagentskit",
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        super().__init__(pool, table_prefix=table_prefix)
        self._clock = clock
        self._state = f"{self.table_prefix}_state"
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
                        "production_state",
                    )
                    if row is not None and int(row["version"]) > self.schema_version:
                        raise PersistenceError("PostgreSQL state schema is newer than this package")
                    await connection.execute(
                        f"CREATE TABLE IF NOT EXISTS {self._state} ("
                        "tenant_scope TEXT NOT NULL, collection TEXT NOT NULL, "
                        "owner_id TEXT NOT NULL, record_id TEXT NOT NULL, "
                        "payload_json JSONB NOT NULL, search_text TEXT NOT NULL DEFAULT '', "
                        "session_id TEXT, tags TEXT[] NOT NULL DEFAULT '{}', "
                        "status TEXT, created_at TIMESTAMPTZ NOT NULL, "
                        "updated_at TIMESTAMPTZ NOT NULL, expires_at TIMESTAMPTZ, "
                        "PRIMARY KEY (tenant_scope, collection, owner_id, record_id))"
                    )
                    await connection.execute(
                        f"CREATE INDEX IF NOT EXISTS {self._state}_lookup_idx ON {self._state} "
                        "(tenant_scope, collection, owner_id, updated_at DESC)"
                    )
                    await connection.execute(
                        f"CREATE INDEX IF NOT EXISTS {self._state}_expiry_idx "
                        f"ON {self._state}(expires_at) WHERE expires_at IS NOT NULL"
                    )
                    await connection.execute(
                        f"CREATE INDEX IF NOT EXISTS {self._state}_tags_gin_idx "
                        f"ON {self._state} USING GIN(tags)"
                    )
                    await connection.execute(
                        f"INSERT INTO {self._schema}(component, version) VALUES ($1, $2) "
                        "ON CONFLICT(component) DO NOTHING",
                        "production_state",
                        self.schema_version,
                    )
                self._initialized = True
            except PersistenceError:
                raise
            except Exception as exc:
                raise PersistenceError("Cannot initialize PostgreSQL state stores") from exc

    async def _load(
        self,
        collection: str,
        owner_id: str,
        record_id: str,
        tenant_id: str | None,
        *,
        connection: AsyncPostgresConnection | None = None,
        for_update: bool = False,
    ) -> Mapping[str, Any] | None:
        await self._ensure_initialized()
        query = (
            f"SELECT payload_json, expires_at FROM {self._state} "
            "WHERE tenant_scope=$1 AND collection=$2 AND owner_id=$3 AND record_id=$4"
        )
        if for_update:
            query += " FOR UPDATE"
        if connection is not None:
            return await connection.fetchrow(
                query, _scope(tenant_id), collection, owner_id, record_id
            )
        async with self.pool.acquire() as acquired:
            return await acquired.fetchrow(
                query, _scope(tenant_id), collection, owner_id, record_id
            )

    async def _save(
        self,
        connection: AsyncPostgresConnection,
        *,
        tenant_id: str | None,
        collection: str,
        owner_id: str,
        record_id: str,
        payload: str,
        search_text: str = "",
        session_id: str | None = None,
        tags: tuple[str, ...] = (),
        status: str | None = None,
        created_at: datetime,
        updated_at: datetime,
        expires_at: datetime | None,
        overwrite: bool = True,
    ) -> int:
        conflict = (
            "DO UPDATE SET payload_json=EXCLUDED.payload_json, "
            "search_text=EXCLUDED.search_text, session_id=EXCLUDED.session_id, "
            "tags=EXCLUDED.tags, status=EXCLUDED.status, "
            "updated_at=EXCLUDED.updated_at, expires_at=EXCLUDED.expires_at"
            if overwrite
            else "DO NOTHING"
        )
        command = await connection.execute(
            f"INSERT INTO {self._state}(tenant_scope, collection, owner_id, record_id, "
            "payload_json, search_text, session_id, tags, status, created_at, updated_at, "
            "expires_at) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7, $8::text[], $9, "
            f"$10, $11, $12) ON CONFLICT(tenant_scope, collection, owner_id, record_id) {conflict}",
            _scope(tenant_id),
            collection,
            owner_id,
            record_id,
            payload,
            search_text,
            session_id,
            list(tags),
            status,
            created_at,
            updated_at,
            expires_at,
        )
        return _count(command)

    async def _delete(
        self, collection: str, owner_id: str, record_id: str, tenant_id: str | None
    ) -> bool:
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection:
                status = await connection.execute(
                    f"DELETE FROM {self._state} WHERE tenant_scope=$1 AND collection=$2 "
                    "AND owner_id=$3 AND record_id=$4",
                    _scope(tenant_id),
                    collection,
                    owner_id,
                    record_id,
                )
            return _count(status) > 0
        except Exception as exc:
            raise PersistenceError("Cannot delete PostgreSQL state") from exc

    async def _purge(self, collection: str, now: datetime) -> int:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("purge timestamp must be timezone-aware")
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection:
                status = await connection.execute(
                    f"DELETE FROM {self._state} WHERE collection=$1 "
                    "AND expires_at IS NOT NULL AND expires_at <= $2",
                    collection,
                    now,
                )
            return _count(status)
        except Exception as exc:
            raise PersistenceError("Cannot purge PostgreSQL state") from exc


class PostgresSessionStore(_StateStore):
    """Transactional PostgreSQL implementation of :class:`SessionStore`."""

    _collection = "sessions"

    async def create(self, session: Session) -> Session:
        await self._ensure_initialized()
        document = _SessionDocument(session=session)
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                inserted = await self._save(
                    connection,
                    tenant_id=session.tenant_id,
                    collection=self._collection,
                    owner_id="",
                    record_id=session.session_id,
                    payload=document.model_dump_json(),
                    session_id=session.session_id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    expires_at=session.expires_at,
                    overwrite=False,
                )
                if inserted == 0:
                    raise SessionConflictError("Session already exists")
            return session
        except SessionConflictError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot create PostgreSQL session") from exc

    async def import_document(
        self,
        session: Session,
        entries: tuple[SessionEntry, ...],
        appends: Mapping[str, tuple[str, tuple[int, ...]]],
        *,
        overwrite: bool = False,
    ) -> None:
        """Import one validated aggregate for an explicit migration operation."""

        if any(item.session_id != session.session_id for item in entries):
            raise PersistenceError("Session migration entries do not match their session")
        await self._ensure_initialized()
        document = _SessionDocument(session=session, entries=entries, appends=dict(appends))
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                changed = await self._save(
                    connection,
                    tenant_id=session.tenant_id,
                    collection=self._collection,
                    owner_id="",
                    record_id=session.session_id,
                    payload=document.model_dump_json(),
                    session_id=session.session_id,
                    created_at=session.created_at,
                    updated_at=session.updated_at,
                    expires_at=session.expires_at,
                    overwrite=overwrite,
                )
                if changed == 0:
                    row = await self._load(
                        self._collection,
                        "",
                        session.session_id,
                        session.tenant_id,
                        connection=connection,
                        for_update=True,
                    )
                    if row is None or self._document(row) != document:
                        raise SessionConflictError("Session migration target conflict")
        except (PersistenceError, SessionConflictError):
            raise
        except Exception as exc:
            raise PersistenceError("Cannot import PostgreSQL session") from exc

    async def get(self, session_id: str, *, tenant_id: str | None = None) -> Session:
        try:
            row = await self._load(self._collection, "", session_id, tenant_id)
            if row is None:
                raise SessionNotFoundError("Session not found")
            session = self._document(row).session
            if _expired(session, self._clock()):
                raise SessionNotFoundError("Session not found")
            return session
        except SessionNotFoundError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot load PostgreSQL session") from exc

    async def append(
        self,
        session_id: str,
        messages: tuple[Message, ...],
        *,
        turn_id: str,
        tenant_id: str | None = None,
        run_id: UUID | None = None,
        idempotency_key: str,
        expected_revision: int | None = None,
    ) -> tuple[SessionEntry, ...]:
        if not messages or not idempotency_key.strip() or not turn_id.strip():
            raise SessionError("Session append requires messages, turn_id and idempotency_key")
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                row = await self._load(
                    self._collection,
                    "",
                    session_id,
                    tenant_id,
                    connection=connection,
                    for_update=True,
                )
                if row is None:
                    raise SessionNotFoundError("Session not found")
                document = self._document(row)
                if _expired(document.session, self._clock()):
                    raise SessionNotFoundError("Session not found")
                fingerprint = _append_fingerprint(messages, turn_id, run_id)
                prior = document.appends.get(idempotency_key)
                if prior is not None:
                    if prior[0] != fingerprint:
                        raise SessionConflictError("Idempotency key payload conflict")
                    indexes = set(prior[1])
                    return tuple(item for item in document.entries if item.sequence in indexes)
                if expected_revision is not None and document.session.revision != expected_revision:
                    raise SessionConflictError("Session revision conflict")
                now = self._clock()
                start = len(document.entries)
                entries = tuple(
                    SessionEntry(
                        session_id=session_id,
                        tenant_id=tenant_id,
                        sequence=start + index,
                        turn_id=turn_id,
                        message=message,
                        created_at=now,
                        run_id=run_id,
                    )
                    for index, message in enumerate(messages)
                )
                updated_session = document.session.model_copy(
                    update={"revision": document.session.revision + 1, "updated_at": now}
                )
                updated = _SessionDocument(
                    session=updated_session,
                    entries=(*document.entries, *entries),
                    appends={
                        **document.appends,
                        idempotency_key: (fingerprint, tuple(item.sequence for item in entries)),
                    },
                )
                await self._save(
                    connection,
                    tenant_id=tenant_id,
                    collection=self._collection,
                    owner_id="",
                    record_id=session_id,
                    payload=updated.model_dump_json(),
                    session_id=session_id,
                    created_at=updated_session.created_at,
                    updated_at=now,
                    expires_at=updated_session.expires_at,
                )
                return entries
        except (SessionError, SessionConflictError, SessionNotFoundError):
            raise
        except Exception as exc:
            raise PersistenceError("Cannot append PostgreSQL session") from exc

    async def list_entries(
        self, session_id: str, *, tenant_id: str | None = None
    ) -> tuple[SessionEntry, ...]:
        row = await self._load(self._collection, "", session_id, tenant_id)
        if row is None:
            raise SessionNotFoundError("Session not found")
        document = self._document(row)
        if _expired(document.session, self._clock()):
            raise SessionNotFoundError("Session not found")
        return document.entries

    async def delete(self, session_id: str, *, tenant_id: str | None = None) -> bool:
        return await self._delete(self._collection, "", session_id, tenant_id)

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        return await self._purge(self._collection, now or self._clock())

    @staticmethod
    def _document(row: Mapping[str, Any]) -> _SessionDocument:
        return _SessionDocument.model_validate_json(_json_payload(row["payload_json"]))


class PostgresMemoryStore(_StateStore):
    """Indexed lexical PostgreSQL implementation of :class:`MemoryStore`."""

    _collection = "memories"

    async def upsert(self, record: MemoryRecord) -> MemoryRecord:
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                row = await self._load(
                    self._collection,
                    record.agent_id,
                    record.memory_id,
                    record.tenant_id,
                    connection=connection,
                    for_update=True,
                )
                if row is not None:
                    current = MemoryRecord.model_validate_json(_json_payload(row["payload_json"]))
                    if current.created_at != record.created_at:
                        raise PersistenceError("Memory created_at is immutable")
                await self._save(
                    connection,
                    tenant_id=record.tenant_id,
                    collection=self._collection,
                    owner_id=record.agent_id,
                    record_id=record.memory_id,
                    payload=record.model_dump_json(),
                    search_text=record.content,
                    session_id=record.session_id,
                    tags=record.tags,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                    expires_at=record.expires_at,
                )
            return record
        except PersistenceError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot persist PostgreSQL memory") from exc

    async def get(
        self, memory_id: str, *, tenant_id: str | None, agent_id: str
    ) -> MemoryRecord | None:
        try:
            row = await self._load(self._collection, agent_id, memory_id, tenant_id)
            if row is None:
                return None
            record = MemoryRecord.model_validate_json(_json_payload(row["payload_json"]))
            return record if _visible(record, self._clock()) else None
        except Exception as exc:
            raise PersistenceError("Cannot load PostgreSQL memory") from exc

    async def search(
        self,
        query: str,
        *,
        tenant_id: str | None,
        agent_id: str,
        session_id: str | None = None,
        tags: tuple[str, ...] = (),
        limit: int = 10,
    ) -> tuple[MemoryRecord, ...]:
        if limit <= 0:
            raise ValueError("Memory search limit must be positive")
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(
                    f"SELECT payload_json FROM {self._state} WHERE tenant_scope=$1 "
                    "AND collection=$2 AND owner_id=$3 "
                    "AND (expires_at IS NULL OR expires_at > $4) "
                    "AND ($5 = '' OR POSITION(LOWER($5) IN LOWER(search_text)) > 0) "
                    "AND ($6::text IS NULL OR session_id=$6) AND tags @> $7::text[] "
                    "ORDER BY updated_at DESC, record_id DESC LIMIT $8",
                    _scope(tenant_id),
                    self._collection,
                    agent_id,
                    self._clock(),
                    query.strip(),
                    session_id,
                    list(tags),
                    limit,
                )
            records = tuple(
                MemoryRecord.model_validate_json(_json_payload(row["payload_json"])) for row in rows
            )
            return tuple(
                item
                for item in records
                if _matches(item, query=query, session_id=session_id, tags=tags)
            )
        except Exception as exc:
            raise PersistenceError("Cannot search PostgreSQL memories") from exc

    async def delete(self, memory_id: str, *, tenant_id: str | None, agent_id: str) -> bool:
        return await self._delete(self._collection, agent_id, memory_id, tenant_id)

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        return await self._purge(self._collection, now or self._clock())


class PostgresApprovalStore(_StateStore):
    """Transactional PostgreSQL implementation of :class:`ApprovalStore`."""

    _collection = "approvals"

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                row = await self._load(
                    self._collection,
                    "",
                    request.approval_id,
                    request.tenant_id,
                    connection=connection,
                    for_update=True,
                )
                if row is not None:
                    current = self._request(row)
                    if current.model_dump() != request.model_dump():
                        raise ApprovalConflictError(
                            "Approval ID already exists with different content"
                        )
                    return current
                await self._persist(connection, request, overwrite=False)
                return request
        except ApprovalConflictError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot create PostgreSQL approval") from exc

    async def get(self, approval_id: str, *, tenant_id: str | None = None) -> ApprovalRequest:
        return await self._mutate(
            approval_id, tenant_id, lambda item: _effective(item, self._clock())
        )

    async def list_pending(
        self, *, tenant_id: str | None = None, session_id: str | None = None
    ) -> tuple[ApprovalRequest, ...]:
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection:
                rows = await connection.fetch(
                    f"SELECT record_id FROM {self._state} WHERE tenant_scope=$1 "
                    "AND collection=$2 AND owner_id='' AND status=$3 "
                    "AND ($4::text IS NULL OR session_id=$4) ORDER BY created_at",
                    _scope(tenant_id),
                    self._collection,
                    ApprovalStatus.PENDING.value,
                    session_id,
                )
            result: list[ApprovalRequest] = []
            for row in rows:
                current = await self.get(str(row["record_id"]), tenant_id=tenant_id)
                if current.status is ApprovalStatus.PENDING:
                    result.append(current)
            return tuple(result)
        except PyAgentsKitError:
            raise
        except Exception as exc:
            raise PersistenceError("Cannot list PostgreSQL approvals") from exc

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
        if not actor_id.strip():
            raise ApprovalConflictError("Approval actor cannot be blank")

        def transition(current: ApprovalRequest) -> ApprovalRequest:
            current = _effective(current, self._clock())
            if current.status is not ApprovalStatus.PENDING:
                if current.decision is decision and current.actor_id == actor_id:
                    return current
                raise ApprovalConflictError("Approval is no longer pending")
            self._revision(current, expected_revision)
            return _resolved(current, decision, actor_id, reason, self._clock())

        return await self._mutate(approval_id, tenant_id, transition)

    async def claim(
        self,
        approval_id: str,
        *,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest:
        def transition(current: ApprovalRequest) -> ApprovalRequest:
            current = _effective(current, self._clock())
            if current.status not in {
                ApprovalStatus.APPROVED,
                ApprovalStatus.REJECTED,
                ApprovalStatus.CANCELLED,
            }:
                raise ApprovalConflictError("Approval decision cannot be claimed")
            self._revision(current, expected_revision)
            return current.model_copy(
                update={"status": ApprovalStatus.CLAIMED, "revision": current.revision + 1}
            )

        return await self._mutate(approval_id, tenant_id, transition)

    async def complete(
        self,
        approval_id: str,
        *,
        tenant_id: str | None = None,
        expected_revision: int | None = None,
    ) -> ApprovalRequest:
        def transition(current: ApprovalRequest) -> ApprovalRequest:
            if current.status is not ApprovalStatus.CLAIMED:
                raise ApprovalConflictError("Approval must be claimed")
            self._revision(current, expected_revision)
            return current.model_copy(
                update={"status": ApprovalStatus.EXECUTED, "revision": current.revision + 1}
            )

        return await self._mutate(approval_id, tenant_id, transition)

    async def _mutate(
        self,
        approval_id: str,
        tenant_id: str | None,
        transform: Callable[[ApprovalRequest], ApprovalRequest],
    ) -> ApprovalRequest:
        await self._ensure_initialized()
        try:
            async with self.pool.acquire() as connection, connection.transaction():
                row = await self._load(
                    self._collection,
                    "",
                    approval_id,
                    tenant_id,
                    connection=connection,
                    for_update=True,
                )
                if row is None:
                    raise ApprovalNotFoundError("Approval not found")
                current = self._request(row)
                updated = transform(current)
                if updated != current:
                    await self._persist(connection, updated)
                return updated
        except (ApprovalConflictError, ApprovalNotFoundError):
            raise
        except Exception as exc:
            raise PersistenceError("Cannot mutate PostgreSQL approval") from exc

    async def _persist(
        self,
        connection: AsyncPostgresConnection,
        request: ApprovalRequest,
        *,
        overwrite: bool = True,
    ) -> None:
        await self._save(
            connection,
            tenant_id=request.tenant_id,
            collection=self._collection,
            owner_id="",
            record_id=request.approval_id,
            payload=request.model_dump_json(),
            session_id=request.session_id,
            status=request.status.value,
            created_at=request.requested_at,
            updated_at=request.resolved_at or request.requested_at,
            expires_at=request.expires_at,
            overwrite=overwrite,
        )

    @staticmethod
    def _request(row: Mapping[str, Any]) -> ApprovalRequest:
        return ApprovalRequest.model_validate_json(_json_payload(row["payload_json"]))

    @staticmethod
    def _revision(current: ApprovalRequest, expected: int | None) -> None:
        if expected is not None and current.revision != expected:
            raise ApprovalConflictError("Approval revision conflict")
