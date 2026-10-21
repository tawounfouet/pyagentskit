"""Explicit non-vector memory records with memory and SQLite stores."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from pydantic import Field, field_validator

from ._base import ContractModel
from .exceptions import PersistenceError
from .messages import Message, MessageRole
from .runs import RunContext, utc_now
from .types import Identifier, NonEmptyString

__all__ = [
    "InMemoryMemoryStore",
    "MemoryContextSource",
    "MemoryRecord",
    "MemoryStore",
    "SQLiteMemoryStore",
]


class MemoryRecord(ContractModel):
    """Application-authored text memory with explicit ownership and retention."""

    memory_id: NonEmptyString
    agent_id: Identifier
    content: NonEmptyString
    tenant_id: NonEmptyString | None = None
    session_id: NonEmptyString | None = None
    tags: tuple[Identifier, ...] = ()
    created_at: datetime
    updated_at: datetime
    expires_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at", "updated_at", "expires_at")
    @classmethod
    def validate_aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("memory timestamps must be timezone-aware")
        return value


@runtime_checkable
class MemoryStore(Protocol):
    """Replaceable lexical memory store; vector retrieval remains external."""

    async def upsert(self, record: MemoryRecord) -> MemoryRecord: ...

    async def get(
        self, memory_id: str, *, tenant_id: str | None, agent_id: str
    ) -> MemoryRecord | None: ...

    async def search(
        self,
        query: str,
        *,
        tenant_id: str | None,
        agent_id: str,
        session_id: str | None = None,
        tags: tuple[str, ...] = (),
        limit: int = 10,
    ) -> tuple[MemoryRecord, ...]: ...

    async def delete(self, memory_id: str, *, tenant_id: str | None, agent_id: str) -> bool: ...

    async def purge_expired(self, *, now: datetime | None = None) -> int: ...


def _scope(tenant_id: str | None) -> str:
    return tenant_id or ""


def _visible(record: MemoryRecord, now: datetime) -> bool:
    return record.expires_at is None or record.expires_at > now


def _matches(
    record: MemoryRecord,
    *,
    query: str,
    session_id: str | None,
    tags: tuple[str, ...],
) -> bool:
    normalized = query.casefold().strip()
    return (
        (not normalized or normalized in record.content.casefold())
        and (session_id is None or record.session_id == session_id)
        and set(tags).issubset(record.tags)
    )


class InMemoryMemoryStore:
    """Deterministic lexical memory store for local applications and tests."""

    def __init__(self, *, clock: Callable[[], datetime] = utc_now) -> None:
        self._clock = clock
        self._items: dict[tuple[str, str, str], MemoryRecord] = {}
        self._lock = asyncio.Lock()

    async def upsert(self, record: MemoryRecord) -> MemoryRecord:
        key = (_scope(record.tenant_id), record.agent_id, record.memory_id)
        async with self._lock:
            current = self._items.get(key)
            if current is not None and current.created_at != record.created_at:
                raise PersistenceError("Memory created_at is immutable")
            self._items[key] = record
            return record

    async def get(
        self, memory_id: str, *, tenant_id: str | None, agent_id: str
    ) -> MemoryRecord | None:
        async with self._lock:
            record = self._items.get((_scope(tenant_id), agent_id, memory_id))
            return record if record is not None and _visible(record, self._clock()) else None

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
        async with self._lock:
            now = self._clock()
            records = [
                record
                for (scope, owner, _), record in self._items.items()
                if scope == _scope(tenant_id)
                and owner == agent_id
                and _visible(record, now)
                and _matches(record, query=query, session_id=session_id, tags=tags)
            ]
            records.sort(key=lambda item: (item.updated_at, item.memory_id), reverse=True)
            return tuple(records[:limit])

    async def delete(self, memory_id: str, *, tenant_id: str | None, agent_id: str) -> bool:
        async with self._lock:
            return self._items.pop((_scope(tenant_id), agent_id, memory_id), None) is not None

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        async with self._lock:
            keys = [key for key, value in self._items.items() if not _visible(value, moment)]
            for key in keys:
                del self._items[key]
            return len(keys)


class MemoryContextSource:
    """Opt-in adapter exposing lexical memories as explicit system context."""

    def __init__(
        self,
        store: MemoryStore,
        *,
        tags: tuple[str, ...] = (),
        limit: int = 5,
    ) -> None:
        if limit <= 0:
            raise ValueError("Memory context limit must be positive")
        self.store = store
        self.tags = tags
        self.limit = limit

    async def retrieve(self, query: str, *, context: RunContext[Any]) -> tuple[Message, ...]:
        tenant_id = context.metadata.get("tenant_id")
        if tenant_id is not None and not isinstance(tenant_id, str):
            raise ValueError("RunContext metadata tenant_id must be a string")
        records = await self.store.search(
            query,
            tenant_id=tenant_id,
            agent_id=context.agent_id,
            session_id=context.session_id,
            tags=self.tags,
            limit=self.limit,
        )
        return tuple(
            Message.from_text(
                MessageRole.SYSTEM,
                f"Relevant memory [{record.memory_id}]: {record.content}",
                metadata={"memory_id": record.memory_id, "memory_source": "lexical"},
            )
            for record in records
        )


class SQLiteMemoryStore:
    """SQLite lexical memory store with tenant/agent composite ownership."""

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
            raise PersistenceError("Cannot initialize SQLite memory store") from exc

    def _migrate(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
        )
        row = self._db.execute(
            "SELECT version FROM schema_migrations WHERE component='memory'"
        ).fetchone()
        version = 0 if row is None else int(row[0])
        if version > self.schema_version:
            raise PersistenceError("Memory database schema is newer than this package")
        if version == 0:
            self._db.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE memories (
                    tenant_scope TEXT NOT NULL,
                    agent_id TEXT NOT NULL,
                    memory_id TEXT NOT NULL,
                    session_id TEXT,
                    content TEXT NOT NULL,
                    tags_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    expires_at TEXT,
                    metadata_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_scope, agent_id, memory_id)
                );
                CREATE INDEX memories_search_scope
                    ON memories(tenant_scope, agent_id, session_id, updated_at);
                INSERT INTO schema_migrations(component, version) VALUES ('memory', 1);
                COMMIT;
                """
            )

    async def aclose(self) -> None:
        async with self._lock:
            await asyncio.to_thread(self._db.close)

    async def __aenter__(self) -> SQLiteMemoryStore:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    async def upsert(self, record: MemoryRecord) -> MemoryRecord:
        async with self._lock:
            try:
                existing = await asyncio.to_thread(
                    self._db.execute,
                    "SELECT created_at FROM memories WHERE tenant_scope=? AND agent_id=? "
                    "AND memory_id=?",
                    (_scope(record.tenant_id), record.agent_id, record.memory_id),
                )
                row = existing.fetchone()
                if row is not None and datetime.fromisoformat(row[0]) != record.created_at:
                    raise PersistenceError("Memory created_at is immutable")
                await asyncio.to_thread(self._upsert, record)
                return record
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot persist memory") from exc

    def _upsert(self, record: MemoryRecord) -> None:
        self._db.execute(
            "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(tenant_scope, agent_id, memory_id) DO UPDATE SET "
            "session_id=excluded.session_id, content=excluded.content, "
            "tags_json=excluded.tags_json, updated_at=excluded.updated_at, "
            "expires_at=excluded.expires_at, metadata_json=excluded.metadata_json",
            (
                _scope(record.tenant_id),
                record.agent_id,
                record.memory_id,
                record.session_id,
                record.content,
                json.dumps(record.tags),
                record.created_at.isoformat(),
                record.updated_at.isoformat(),
                record.expires_at.isoformat() if record.expires_at else None,
                json.dumps(record.metadata, separators=(",", ":"), sort_keys=True),
            ),
        )

    @staticmethod
    def _from_row(row: tuple[Any, ...], tenant_id: str | None) -> MemoryRecord:
        return MemoryRecord(
            memory_id=row[0],
            agent_id=row[1],
            content=row[2],
            tenant_id=tenant_id,
            session_id=row[3],
            tags=tuple(json.loads(row[4])),
            created_at=datetime.fromisoformat(row[5]),
            updated_at=datetime.fromisoformat(row[6]),
            expires_at=datetime.fromisoformat(row[7]) if row[7] else None,
            metadata=json.loads(row[8]),
        )

    async def get(
        self, memory_id: str, *, tenant_id: str | None, agent_id: str
    ) -> MemoryRecord | None:
        async with self._lock:
            try:
                cursor = await asyncio.to_thread(
                    self._db.execute,
                    "SELECT memory_id, agent_id, content, session_id, tags_json, created_at, "
                    "updated_at, expires_at, metadata_json FROM memories "
                    "WHERE tenant_scope=? AND agent_id=? AND memory_id=?",
                    (_scope(tenant_id), agent_id, memory_id),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                record = self._from_row(row, tenant_id)
                return record if _visible(record, self._clock()) else None
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot load memory") from exc

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
        async with self._lock:
            try:
                return await asyncio.to_thread(
                    self._search, query, tenant_id, agent_id, session_id, tags, limit
                )
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot search memory") from exc

    def _search(
        self,
        query: str,
        tenant_id: str | None,
        agent_id: str,
        session_id: str | None,
        tags: tuple[str, ...],
        limit: int,
    ) -> tuple[MemoryRecord, ...]:
        sql = (
            "SELECT memory_id, agent_id, content, session_id, tags_json, created_at, "
            "updated_at, expires_at, metadata_json FROM memories "
            "WHERE tenant_scope=? AND agent_id=?"
        )
        parameters: list[Any] = [_scope(tenant_id), agent_id]
        if session_id is not None:
            sql += " AND session_id=?"
            parameters.append(session_id)
        sql += " ORDER BY updated_at DESC, memory_id DESC"
        now = self._clock()
        records = [
            self._from_row(row, tenant_id) for row in self._db.execute(sql, parameters).fetchall()
        ]
        matched = [
            record
            for record in records
            if _visible(record, now)
            and _matches(record, query=query, session_id=session_id, tags=tags)
        ]
        return tuple(matched[:limit])

    async def delete(self, memory_id: str, *, tenant_id: str | None, agent_id: str) -> bool:
        async with self._lock:
            try:
                cursor = await asyncio.to_thread(
                    self._db.execute,
                    "DELETE FROM memories WHERE tenant_scope=? AND agent_id=? AND memory_id=?",
                    (_scope(tenant_id), agent_id, memory_id),
                )
                return cursor.rowcount > 0
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot delete memory") from exc

    async def purge_expired(self, *, now: datetime | None = None) -> int:
        moment = now or self._clock()
        async with self._lock:
            try:
                cursor = await asyncio.to_thread(
                    self._db.execute,
                    "DELETE FROM memories WHERE expires_at IS NOT NULL AND expires_at<=?",
                    (moment.isoformat(),),
                )
                return cursor.rowcount
            except sqlite3.Error as exc:
                raise PersistenceError("Cannot purge memories") from exc
