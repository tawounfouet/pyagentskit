"""Contract tests shared by memory and SQLite session/memory stores."""

from __future__ import annotations

import asyncio
import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pyagentskit import (
    InMemoryMemoryStore,
    MemoryContextSource,
    MemoryRecord,
    MemorySessionStore,
    Message,
    MessageRole,
    RunContext,
    Session,
    SessionConflictError,
    SessionNotFoundError,
    SQLiteMemoryStore,
    SQLiteSessionStore,
)
from pyagentskit.exceptions import PersistenceError

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)


def session(session_id: str = "s-1", *, tenant_id: str | None = "tenant-a") -> Session:
    return Session(
        session_id=session_id,
        agent_id="assistant",
        tenant_id=tenant_id,
        created_at=NOW,
        updated_at=NOW,
    )


def memory(memory_id: str = "m-1", *, tenant_id: str | None = "tenant-a") -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        agent_id="assistant",
        tenant_id=tenant_id,
        session_id="s-1",
        content="Thomas prefers concise technical reports",
        tags=("preference", "writing"),
        created_at=NOW,
        updated_at=NOW,
    )


class SessionStoreContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_and_sqlite_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stores = [
                MemorySessionStore(clock=lambda: NOW),
                SQLiteSessionStore(Path(directory) / "sessions.sqlite", clock=lambda: NOW),
            ]
            for store in stores:
                with self.subTest(store=type(store).__name__):
                    created = await store.create(session())
                    self.assertEqual(created.revision, 0)
                    first = await store.append(
                        "s-1",
                        (Message.from_text(MessageRole.USER, "Hello"),),
                        tenant_id="tenant-a",
                        turn_id="turn-1",
                        idempotency_key="append-1",
                        expected_revision=0,
                    )
                    replay = await store.append(
                        "s-1",
                        (Message.from_text(MessageRole.USER, "Hello"),),
                        tenant_id="tenant-a",
                        turn_id="turn-1",
                        idempotency_key="append-1",
                    )
                    self.assertEqual(first, replay)
                    with self.assertRaises(SessionConflictError):
                        await store.append(
                            "s-1",
                            (Message.from_text(MessageRole.USER, "DIFFERENT"),),
                            tenant_id="tenant-a",
                            turn_id="turn-1",
                            idempotency_key="append-1",
                        )
                    self.assertEqual((await store.get("s-1", tenant_id="tenant-a")).revision, 1)
                    with self.assertRaises(SessionConflictError):
                        await store.append(
                            "s-1",
                            (Message.from_text(MessageRole.ASSISTANT, "Hi"),),
                            tenant_id="tenant-a",
                            turn_id="turn-1",
                            idempotency_key="append-2",
                            expected_revision=0,
                        )
                    with self.assertRaises(SessionNotFoundError):
                        await store.get("s-1", tenant_id="tenant-b")
                    self.assertEqual(
                        (await store.list_entries("s-1", tenant_id="tenant-a"))[0], first[0]
                    )
                    self.assertTrue(await store.delete("s-1", tenant_id="tenant-a"))
                    self.assertFalse(await store.delete("s-1", tenant_id="tenant-a"))
                close = getattr(store, "aclose", None)
                if close is not None:
                    await close()

    async def test_sqlite_concurrent_appends_have_unique_stable_sequences(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SQLiteSessionStore(Path(directory) / "sessions.sqlite", clock=lambda: NOW)
            await store.create(session())
            await asyncio.gather(
                *(
                    store.append(
                        "s-1",
                        (Message.from_text(MessageRole.USER, f"message-{index}"),),
                        tenant_id="tenant-a",
                        turn_id=f"turn-{index}",
                        idempotency_key=f"append-{index}",
                    )
                    for index in range(20)
                )
            )
            entries = await store.list_entries("s-1", tenant_id="tenant-a")
            self.assertEqual(tuple(item.sequence for item in entries), tuple(range(20)))
            self.assertEqual((await store.get("s-1", tenant_id="tenant-a")).revision, 20)
            await store.aclose()

    async def test_session_and_memory_migrations_share_one_database(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.sqlite"
            sessions = SQLiteSessionStore(path, clock=lambda: NOW)
            memories = SQLiteMemoryStore(path, clock=lambda: NOW)
            await sessions.create(session())
            await memories.upsert(memory())
            self.assertEqual(
                (await sessions.get("s-1", tenant_id="tenant-a")).agent_id, "assistant"
            )
            self.assertIsNotNone(
                await memories.get("m-1", tenant_id="tenant-a", agent_id="assistant")
            )
            await memories.aclose()
            await sessions.aclose()

    async def test_expiration_purge_and_newer_schema_rejection(self) -> None:
        expired = session().model_copy(update={"expires_at": NOW - timedelta(seconds=1)})
        store = MemorySessionStore(clock=lambda: NOW)
        await store.create(expired)
        with self.assertRaises(SessionNotFoundError):
            await store.get("s-1", tenant_id="tenant-a")
        self.assertEqual(await store.purge_expired(), 1)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "newer.sqlite"
            db = sqlite3.connect(path)
            db.execute(
                "CREATE TABLE schema_migrations "
                "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
            )
            db.execute("INSERT INTO schema_migrations VALUES ('sessions', 99)")
            db.commit()
            db.close()
            with self.assertRaises(PersistenceError):
                SQLiteSessionStore(path)


class MemoryStoreContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_and_sqlite_search_isolation_and_lifecycle(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stores = [
                InMemoryMemoryStore(clock=lambda: NOW),
                SQLiteMemoryStore(Path(directory) / "memory.sqlite", clock=lambda: NOW),
            ]
            for store in stores:
                with self.subTest(store=type(store).__name__):
                    item = memory()
                    await store.upsert(item)
                    self.assertEqual(
                        await store.get("m-1", tenant_id="tenant-a", agent_id="assistant"),
                        item,
                    )
                    self.assertIsNone(
                        await store.get("m-1", tenant_id="tenant-b", agent_id="assistant")
                    )
                    results = await store.search(
                        "TECHNICAL",
                        tenant_id="tenant-a",
                        agent_id="assistant",
                        session_id="s-1",
                        tags=("preference",),
                    )
                    self.assertEqual(results, (item,))
                    self.assertEqual(
                        await store.search("missing", tenant_id="tenant-a", agent_id="assistant"),
                        (),
                    )
                    updated = item.model_copy(
                        update={
                            "content": "Updated preference",
                            "updated_at": NOW + timedelta(seconds=1),
                        }
                    )
                    await store.upsert(updated)
                    self.assertEqual(
                        (
                            await store.get("m-1", tenant_id="tenant-a", agent_id="assistant")
                        ).content,  # type: ignore[union-attr]
                        "Updated preference",
                    )
                    with self.assertRaises(PersistenceError):
                        await store.upsert(
                            updated.model_copy(update={"created_at": NOW + timedelta(seconds=2)})
                        )
                    self.assertTrue(
                        await store.delete("m-1", tenant_id="tenant-a", agent_id="assistant")
                    )
                close = getattr(store, "aclose", None)
                if close is not None:
                    await close()

    async def test_memory_retention(self) -> None:
        store = InMemoryMemoryStore(clock=lambda: NOW)
        await store.upsert(memory().model_copy(update={"expires_at": NOW - timedelta(seconds=1)}))
        self.assertEqual(await store.search("", tenant_id="tenant-a", agent_id="assistant"), ())
        self.assertEqual(await store.purge_expired(), 1)
        with self.assertRaises(ValueError):
            await store.search("", tenant_id="tenant-a", agent_id="assistant", limit=0)

    async def test_memory_context_source_is_explicit_and_scoped(self) -> None:
        store = InMemoryMemoryStore(clock=lambda: NOW)
        await store.upsert(memory())
        source = MemoryContextSource(store, tags=("preference",), limit=2)
        context = RunContext(
            agent_id="assistant",
            deps=None,
            session_id="s-1",
            metadata={"tenant_id": "tenant-a"},
        )
        messages = await source.retrieve("technical", context=context)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0].metadata["memory_id"], "m-1")
