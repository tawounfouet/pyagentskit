"""Tenant-scoped session contracts plus memory and SQLite stores."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import UUID

from pydantic import Field, field_validator

from ._base import ContractModel
from .exceptions import PersistenceError, SessionConflictError, SessionError, SessionNotFoundError
from .messages import Message
from .runs import utc_now
from .types import Identifier, NonEmptyString

__all__ = [
    "MemorySessionStore",
    "SQLiteSessionStore",
    "Session",
    "SessionEntry",
    "SessionStore",
]


class Session(ContractModel):
    """Conversation identity and optimistic revision metadata."""

    session_id: NonEmptyString
    agent_id: Identifier
    tenant_id: NonEmptyString | None = None
    revision: int = Field(default=0, ge=0)
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at", "updated_at", "expires_at")
    @classmethod
    def validate_aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("session timestamps must be timezone-aware")
        return value


class SessionEntry(ContractModel):
    """One ordered immutable message persisted in a session."""

    session_id: NonEmptyString
    tenant_id: NonEmptyString | None = None
    sequence: int = Field(ge=0)
    turn_id: NonEmptyString
    message: Message
    created_at: datetime
    run_id: UUID | None = None

    @field_validator("created_at")
    @classmethod
    def validate_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("session entry timestamp must be timezone-aware")
        return value


@runtime_checkable
class SessionStore(Protocol):
    """Replaceable ordered conversation store."""

    async def create(self, session: Session) -> Session: ...

    async def get(self, session_id: str, *, tenant_id: str | None = None) -> Session: ...

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
    ) -> tuple[SessionEntry, ...]: ...

    async def list_entries(
        self, session_id: str, *, tenant_id: str | None = None
    ) -> tuple[SessionEntry, ...]: ...

    async def delete(self, session_id: str, *, tenant_id: str | None = None) -> bool: ...

    async def purge_expired(self, *, now: datetime | None = None) -> int: ...


def _scope(tenant_id: str | None) -> str:
    return tenant_id or ""


def _expired(session: Session, now: datetime) -> bool:
    return session.expires_at is not None and session.expires_at <= now


def _append_fingerprint(messages: tuple[Message, ...], turn_id: str, run_id: UUID | None) -> str:
    payload = {
        "messages": [message.model_dump(mode="json") for message in messages],
        "turn_id": turn_id,
        "run_id": str(run_id) if run_id is not None else None,
    }
    canonical = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(canonical).hexdigest()


class MemorySessionStore:
    """Process-local deterministic implementation of :class:`SessionStore`."""

    def __init__(self, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._sessions: dict[tuple[str, str], Session] = {}
        self._entries: dict[tuple[str, str], list[SessionEntry]] = {}
        self._appends: dict[tuple[str, str, str], tuple[str, tuple[SessionEntry, ...]]] = {}
        self._lock = asyncio.Lock()

    async def create(self, session: Session) -> Session:
        key = (_scope(session.tenant_id), session.session_id)
        async with self._lock:
            if key in self._sessions:
                raise SessionConflictError("Session already exists")
            self._sessions[key] = session
            self._entries[key] = []
            return session

    async def get(self, session_id: str, *, tenant_id: str | None = None) -> Session:
        async with self._lock:
            return self._get_unlocked(session_id, tenant_id)

    def _get_unlocked(self, session_id: str, tenant_id: str | None) -> Session:
        session = self._sessions.get((_scope(tenant_id), session_id))
        if session is None or _expired(session, self._clock()):
            raise SessionNotFoundError("Session not found")
        return session

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
        key = (_scope(tenant_id), session_id)
        append_key = (*key, idempotency_key)
        async with self._lock:
            fingerprint = _append_fingerprint(messages, turn_id, run_id)
            previous = self._appends.get(append_key)
            if previous is not None:
                if previous[0] != fingerprint:
                    raise SessionConflictError("Idempotency key payload conflict")
                return previous[1]
            session = self._get_unlocked(session_id, tenant_id)
            if expected_revision is not None and session.revision != expected_revision:
                raise SessionConflictError("Session revision conflict")
            now = self._clock()
            start = len(self._entries[key])
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
            self._entries[key].extend(entries)
            self._sessions[key] = session.model_copy(
                update={"revision": session.revision + 1, "updated_at": now}
            )
            self._appends[append_key] = (fingerprint, entries)
            return entries

    async def list_entries(
        self, session_id: str, *, tenant_id: str | None = None
    ) -> tuple[SessionEntry, ...]:
        async with self._lock:
            self._get_unlocked(session_id, tenant_id)
            return tuple(self._entries[(_scope(tenant_id), session_id)])

    async def delete(self, session_id: str, *, tenant_id: str | None = None) -> bool:
        key = (_scope(tenant_id), session_id)
        async with self._lock:
            if key not in self._sessions:
                return False
            del self._sessions[key]
            del self._entries[key]
            for append_key in [item for item in self._appends if item[:2] == key]:
                del self._appends[append_key]
            return True

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        async with self._lock:
            keys = [key for key, value in self._sessions.items() if _expired(value, moment)]
            for key in keys:
                del self._sessions[key]
                self._entries.pop(key, None)
                for append_key in [item for item in self._appends if item[:2] == key]:
                    del self._appends[append_key]
            return len(keys)


class SQLiteSessionStore:
    """SQLite session store with schema migration v1 and transactional appends."""

    schema_version = 1

    def __init__(self, path: str | Path, *, clock: Callable[[], datetime] = utc_now) -> None:
        self.path = Path(path)
        self._clock = clock
        self._lock = asyncio.Lock()
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
            self._db.execute("PRAGMA foreign_keys=ON")
            self._db.execute("PRAGMA journal_mode=WAL")
            self._migrate()
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError("Cannot initialize SQLite session store") from exc

    def _migrate(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
        )
        row = self._db.execute(
            "SELECT version FROM schema_migrations WHERE component='sessions'"
        ).fetchone()
        version = 0 if row is None else int(row[0])
        if version > self.schema_version:
            raise PersistenceError("Session database schema is newer than this package")
        if version == 0:
            self._db.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE sessions (
                    tenant_scope TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_scope, session_id)
                );
                CREATE TABLE session_appends (
                    tenant_scope TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    idempotency_key TEXT NOT NULL,
                    fingerprint TEXT NOT NULL,
                    PRIMARY KEY (tenant_scope, session_id, idempotency_key),
                    FOREIGN KEY (tenant_scope, session_id)
                        REFERENCES sessions(tenant_scope, session_id) ON DELETE CASCADE
                );
                CREATE TABLE session_entries (
                    tenant_scope TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    sequence INTEGER NOT NULL,
                    append_key TEXT NOT NULL,
                    append_index INTEGER NOT NULL,
                    turn_id TEXT NOT NULL,
                    message_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    run_id TEXT,
                    PRIMARY KEY (tenant_scope, session_id, sequence),
                    UNIQUE (tenant_scope, session_id, append_key, append_index),
                    FOREIGN KEY (tenant_scope, session_id)
                        REFERENCES sessions(tenant_scope, session_id) ON DELETE CASCADE
                );
                INSERT INTO schema_migrations(component, version) VALUES ('sessions', 1);
                COMMIT;
                """
            )

    async def aclose(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._db.close)

    async def __aenter__(self) -> SQLiteSessionStore:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def create(self, session: Session) -> Session:
        async with self._lock:
            try:
                await asyncio.to_thread(self._create, session)
            except sqlite3.IntegrityError:
                raise SessionConflictError("Session already exists") from None
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot create session") from exc
        return session

    def _create(self, session: Session) -> None:
        self._db.execute(
            "INSERT INTO sessions VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                _scope(session.tenant_id),
                session.session_id,
                session.agent_id,
                session.revision,
                session.created_at.isoformat(),
                session.updated_at.isoformat(),
                session.expires_at.isoformat() if session.expires_at else None,
                json.dumps(session.metadata, separators=(",", ":"), sort_keys=True),
            ),
        )

    def _session_from_row(self, row: tuple[Any, ...], tenant_id: str | None) -> Session:
        return Session(
            session_id=row[0],
            agent_id=row[1],
            tenant_id=tenant_id,
            revision=row[2],
            created_at=datetime.fromisoformat(row[3]),
            updated_at=datetime.fromisoformat(row[4]),
            expires_at=datetime.fromisoformat(row[5]) if row[5] else None,
            metadata=json.loads(row[6]),
        )

    def _get(self, session_id: str, tenant_id: str | None) -> Session:
        row = self._db.execute(
            "SELECT session_id, agent_id, revision, created_at, updated_at, expires_at, "
            "metadata_json FROM sessions WHERE tenant_scope=? AND session_id=?",
            (_scope(tenant_id), session_id),
        ).fetchone()
        if row is None:
            raise SessionNotFoundError("Session not found")
        session = self._session_from_row(row, tenant_id)
        if _expired(session, self._clock()):
            raise SessionNotFoundError("Session not found")
        return session

    async def get(self, session_id: str, *, tenant_id: str | None = None) -> Session:
        async with self._lock:
            try:
                return await asyncio.to_thread(self._get, session_id, tenant_id)
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot load session") from exc

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
        async with self._lock:
            try:
                return await asyncio.to_thread(
                    self._append,
                    session_id,
                    messages,
                    turn_id,
                    tenant_id,
                    run_id,
                    idempotency_key,
                    expected_revision,
                )
            except (SessionError, SessionConflictError, SessionNotFoundError):
                raise
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot append session messages") from exc

    def _append(
        self,
        session_id: str,
        messages: tuple[Message, ...],
        turn_id: str,
        tenant_id: str | None,
        run_id: UUID | None,
        idempotency_key: str,
        expected_revision: int | None,
    ) -> tuple[SessionEntry, ...]:
        scope = _scope(tenant_id)
        try:
            self._db.execute("BEGIN IMMEDIATE")
            fingerprint = _append_fingerprint(messages, turn_id, run_id)
            existing = self._db.execute(
                "SELECT fingerprint FROM session_appends WHERE tenant_scope=? AND session_id=? "
                "AND idempotency_key=?",
                (scope, session_id, idempotency_key),
            ).fetchone()
            if existing:
                if existing[0] != fingerprint:
                    raise SessionConflictError("Idempotency key payload conflict")
                entries = self._list_entries(session_id, tenant_id, idempotency_key)
                self._db.execute("COMMIT")
                return entries
            session = self._get(session_id, tenant_id)
            if expected_revision is not None and session.revision != expected_revision:
                raise SessionConflictError("Session revision conflict")
            row = self._db.execute(
                "SELECT COALESCE(MAX(sequence), -1) FROM session_entries "
                "WHERE tenant_scope=? AND session_id=?",
                (scope, session_id),
            ).fetchone()
            start = int(row[0]) + 1
            now = self._clock()
            self._db.execute(
                "INSERT INTO session_appends VALUES (?, ?, ?, ?)",
                (scope, session_id, idempotency_key, fingerprint),
            )
            for index, message in enumerate(messages):
                self._db.execute(
                    "INSERT INTO session_entries VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        scope,
                        session_id,
                        start + index,
                        idempotency_key,
                        index,
                        turn_id,
                        message.model_dump_json(),
                        now.isoformat(),
                        str(run_id) if run_id else None,
                    ),
                )
            self._db.execute(
                "UPDATE sessions SET revision=revision+1, updated_at=? "
                "WHERE tenant_scope=? AND session_id=?",
                (now.isoformat(), scope, session_id),
            )
            entries = self._list_entries(session_id, tenant_id, idempotency_key)
            self._db.execute("COMMIT")
            return entries
        except Exception:
            self._db.execute("ROLLBACK")
            raise

    def _list_entries(
        self, session_id: str, tenant_id: str | None, append_key: str | None = None
    ) -> tuple[SessionEntry, ...]:
        query = (
            "SELECT sequence, turn_id, message_json, created_at, run_id FROM session_entries "
            "WHERE tenant_scope=? AND session_id=?"
        )
        parameters: list[Any] = [_scope(tenant_id), session_id]
        if append_key is not None:
            query += " AND append_key=?"
            parameters.append(append_key)
        query += " ORDER BY sequence"
        return tuple(
            SessionEntry(
                session_id=session_id,
                tenant_id=tenant_id,
                sequence=row[0],
                turn_id=row[1],
                message=Message.model_validate_json(row[2]),
                created_at=datetime.fromisoformat(row[3]),
                run_id=UUID(row[4]) if row[4] else None,
            )
            for row in self._db.execute(query, parameters).fetchall()
        )

    async def list_entries(
        self, session_id: str, *, tenant_id: str | None = None
    ) -> tuple[SessionEntry, ...]:
        async with self._lock:
            try:
                await asyncio.to_thread(self._get, session_id, tenant_id)
                return await asyncio.to_thread(self._list_entries, session_id, tenant_id)
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot list session messages") from exc

    async def delete(self, session_id: str, *, tenant_id: str | None = None) -> bool:
        async with self._lock:
            try:
                cursor = await asyncio.to_thread(
                    self._db.execute,
                    "DELETE FROM sessions WHERE tenant_scope=? AND session_id=?",
                    (_scope(tenant_id), session_id),
                )
                return cursor.rowcount > 0
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot delete session") from exc

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        async with self._lock:
            try:
                cursor = await asyncio.to_thread(
                    self._db.execute,
                    "DELETE FROM sessions WHERE expires_at IS NOT NULL AND expires_at<=?",
                    (moment.isoformat(),),
                )
                return cursor.rowcount
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot purge expired sessions") from exc
