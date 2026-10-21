from __future__ import annotations

import asyncio
import tempfile
import unittest
from collections.abc import AsyncIterator, Mapping, Sequence
from contextlib import AbstractAsyncContextManager, redirect_stdout
from datetime import UTC, datetime, timedelta
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from uuid import uuid4

from pyagentskit.approvals import (
    ApprovalDecision,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStore,
    MemoryApprovalStore,
    SQLiteApprovalStore,
)
from pyagentskit.artifact_store import ArtifactStore
from pyagentskit.blobs import (
    AzureBlobArtifactStore,
    AzureBlobStore,
    BlobStore,
    ObjectArtifactStore,
    S3ArtifactStore,
    S3BlobStore,
    create_azure_container_client,
    create_s3_client,
)
from pyagentskit.cli import main as cli_main
from pyagentskit.durability import CheckpointKind, RunCheckpoint, SQLiteRunStore
from pyagentskit.exceptions import (
    ApprovalConflictError,
    ArtifactNotFoundError,
    PersistenceError,
    SessionConflictError,
    SessionNotFoundError,
)
from pyagentskit.memory import (
    InMemoryMemoryStore,
    MemoryRecord,
    MemoryStore,
    SQLiteMemoryStore,
)
from pyagentskit.messages import Message, MessageRole
from pyagentskit.postgres import AsyncPostgresConnection, AsyncPostgresPool, PostgresRunStore
from pyagentskit.postgres_state import (
    PostgresApprovalStore,
    PostgresMemoryStore,
    PostgresSessionStore,
)
from pyagentskit.runs import RunStatus
from pyagentskit.sessions import MemorySessionStore, Session, SessionStore, SQLiteSessionStore
from pyagentskit.state_migration import migrate_sqlite_to_postgres
from pyagentskit.tools import ToolCall

NOW = datetime(2026, 9, 9, 12, tzinfo=UTC)


class Clock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


class _Transaction(AbstractAsyncContextManager[Any]):
    def __init__(self, lock: asyncio.Lock) -> None:
        self.lock = lock

    async def __aenter__(self) -> _Transaction:
        await self.lock.acquire()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        self.lock.release()


class _Acquire(AbstractAsyncContextManager[AsyncPostgresConnection]):
    def __init__(self, connection: FakeStateConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakeStateConnection:
        return self.connection

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FakeStatePool:
    def __init__(self) -> None:
        self.lock = asyncio.Lock()
        self.schema: dict[str, int] = {}
        self.state: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        self.runs: dict[tuple[str, object], str] = {}

    def acquire(self) -> _Acquire:
        return _Acquire(FakeStateConnection(self))


class FakeStateConnection:
    def __init__(self, pool: FakeStatePool) -> None:
        self.pool = pool

    def transaction(self) -> _Transaction:
        return _Transaction(self.pool.lock)

    async def execute(self, query: str, *args: object) -> str:
        normalized = " ".join(query.split())
        if normalized.startswith("CREATE "):
            return "CREATE TABLE"
        if "schema_versions(component, version)" in normalized:
            self.pool.schema.setdefault(str(args[0]), int(args[1]))
            return "INSERT 0 1"
        if "_state(" in normalized and normalized.startswith("INSERT INTO"):
            key = tuple(str(item) for item in args[:4])
            assert len(key) == 4
            exists = key in self.pool.state
            if exists and "DO NOTHING" in normalized:
                return "INSERT 0 0"
            self.pool.state[key] = {
                "payload_json": str(args[4]),
                "search_text": str(args[5]),
                "session_id": args[6],
                "tags": tuple(args[7]),  # type: ignore[arg-type]
                "status": args[8],
                "created_at": args[9],
                "updated_at": args[10],
                "expires_at": args[11],
                "record_id": args[3],
            }
            return "INSERT 0 1"
        if normalized.startswith("DELETE FROM") and "_state" in normalized:
            if "record_id=$4" in normalized:
                key = tuple(str(item) for item in args[:4])
                return f"DELETE {int(self.pool.state.pop(key, None) is not None)}"
            collection, moment = str(args[0]), args[1]
            keys = [
                key
                for key, value in self.pool.state.items()
                if key[1] == collection
                and value["expires_at"] is not None
                and value["expires_at"] <= moment
            ]
            for key in keys:
                del self.pool.state[key]
            return f"DELETE {len(keys)}"
        if "_runs(tenant_scope, run_id, payload_json)" in normalized:
            key = (str(args[0]), args[1])
            if key in self.pool.runs and "DO NOTHING" in normalized:
                return "INSERT 0 0"
            self.pool.runs[key] = str(args[2])
            return "INSERT 0 1"
        raise AssertionError(f"Unhandled execute: {normalized}")

    async def fetchrow(self, query: str, *args: object) -> Mapping[str, Any] | None:
        normalized = " ".join(query.split())
        if "schema_versions WHERE component" in normalized:
            version = self.pool.schema.get(str(args[0]))
            return None if version is None else {"version": version}
        if "payload_json, expires_at" in normalized and "_state" in normalized:
            return self.pool.state.get(tuple(str(item) for item in args[:4]))
        if "payload_json FROM" in normalized and "_runs" in normalized:
            payload = self.pool.runs.get((str(args[0]), args[1]))
            return None if payload is None else {"payload_json": payload}
        raise AssertionError(f"Unhandled fetchrow: {normalized}")

    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, Any]]:
        normalized = " ".join(query.split())
        if "SELECT payload_json" in normalized:
            scope, collection, owner = map(str, args[:3])
            now, query_text, session_id, tags, limit = args[3:]
            records = [
                item
                for key, item in self.pool.state.items()
                if key[:3] == (scope, collection, owner)
                and (item["expires_at"] is None or item["expires_at"] > now)
                and (
                    not str(query_text)
                    or str(query_text).casefold() in item["search_text"].casefold()
                )
                and (session_id is None or item["session_id"] == session_id)
                and set(tags).issubset(item["tags"])
            ]
            records.sort(key=lambda item: (item["updated_at"], item["record_id"]), reverse=True)
            return records[: int(limit)]
        if "SELECT record_id" in normalized:
            scope, collection, status, session_id = args
            records = [
                item
                for key, item in self.pool.state.items()
                if key[:3] == (str(scope), str(collection), "")
                and item["status"] == status
                and (session_id is None or item["session_id"] == session_id)
            ]
            records.sort(key=lambda item: item["created_at"])
            return records
        raise AssertionError(f"Unhandled fetch: {normalized}")


class StateStoreContract:
    session_store: SessionStore
    memory_store: MemoryStore
    approval_store: ApprovalStore
    clock: Clock

    async def test_session_memory_and_approval_contracts(self) -> None:
        session = Session(
            session_id="session-1",
            agent_id="agent",
            tenant_id="tenant-a",
            created_at=NOW,
            updated_at=NOW,
        )
        self.assertIsInstance(self.session_store, SessionStore)  # type: ignore[attr-defined]
        await self.session_store.create(session)
        with self.assertRaises(SessionConflictError):  # type: ignore[attr-defined]
            await self.session_store.create(session)
        entries = await self.session_store.append(
            session.session_id,
            (Message.from_text(MessageRole.USER, "hello"),),
            turn_id="turn-1",
            tenant_id="tenant-a",
            idempotency_key="append-1",
            expected_revision=0,
        )
        self.assertEqual(
            entries,
            await self.session_store.append(  # type: ignore[attr-defined]
                session.session_id,
                (Message.from_text(MessageRole.USER, "hello"),),
                turn_id="turn-1",
                tenant_id="tenant-a",
                idempotency_key="append-1",
            ),
        )
        with self.assertRaises(SessionNotFoundError):  # type: ignore[attr-defined]
            await self.session_store.get(session.session_id, tenant_id="tenant-b")

        memory = MemoryRecord(
            memory_id="memory-1",
            agent_id="agent",
            tenant_id="tenant-a",
            session_id="session-1",
            content="Customer prefers French",
            tags=("preference",),
            created_at=NOW,
            updated_at=NOW,
        )
        self.assertIsInstance(self.memory_store, MemoryStore)  # type: ignore[attr-defined]
        await self.memory_store.upsert(memory)
        self.assertEqual(
            await self.memory_store.search(
                "french", tenant_id="tenant-a", agent_id="agent", tags=("preference",)
            ),
            (memory,),
        )
        self.assertIsNone(
            await self.memory_store.get("memory-1", tenant_id="tenant-b", agent_id="agent")
        )

        request = ApprovalRequest.for_tool_call(
            ToolCall(id="call-1", name="customer.write", arguments={"id": 1}),
            run_id=uuid4(),
            trace_id=uuid4(),
            agent_id="agent",
            session_id="session-1",
            tenant_id="tenant-a",
            clock=self.clock,
        )
        self.assertIsInstance(self.approval_store, ApprovalStore)  # type: ignore[attr-defined]
        await self.approval_store.create(request)
        resolved = await self.approval_store.resolve(
            request.approval_id,
            ApprovalDecision.APPROVE,
            actor_id="operator",
            tenant_id="tenant-a",
            expected_revision=0,
        )
        claimed = await self.approval_store.claim(
            request.approval_id,
            tenant_id="tenant-a",
            expected_revision=resolved.revision,
        )
        completed = await self.approval_store.complete(
            request.approval_id,
            tenant_id="tenant-a",
            expected_revision=claimed.revision,
        )
        self.assertEqual(completed.status, ApprovalStatus.EXECUTED)  # type: ignore[attr-defined]
        with self.assertRaises(ApprovalConflictError):  # type: ignore[attr-defined]
            await self.approval_store.complete(request.approval_id, tenant_id="tenant-a")


class MemoryStateStoreContractTests(StateStoreContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.clock = Clock()
        self.session_store = MemorySessionStore(clock=self.clock)
        self.memory_store = InMemoryMemoryStore(clock=self.clock)
        self.approval_store = MemoryApprovalStore(clock=self.clock)


class SQLiteStateStoreContractTests(StateStoreContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.clock = Clock()
        root = Path(self.temporary.name)
        self.session_store = SQLiteSessionStore(root / "session.db", clock=self.clock)
        self.memory_store = SQLiteMemoryStore(root / "memory.db", clock=self.clock)
        self.approval_store = SQLiteApprovalStore(root / "approval.db", clock=self.clock)

    async def asyncTearDown(self) -> None:
        await self.session_store.aclose()  # type: ignore[attr-defined]
        await self.memory_store.aclose()  # type: ignore[attr-defined]
        await self.approval_store.aclose()  # type: ignore[attr-defined]
        self.temporary.cleanup()


class PostgresStateStoreContractTests(StateStoreContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.clock = Clock()
        self.pool = FakeStatePool()
        self.assertIsInstance(self.pool, AsyncPostgresPool)
        self.session_store = PostgresSessionStore(self.pool, clock=self.clock)
        self.memory_store = PostgresMemoryStore(self.pool, clock=self.clock)
        self.approval_store = PostgresApprovalStore(self.pool, clock=self.clock)

    async def test_expiry_purge_and_schema_guard(self) -> None:
        record = MemoryRecord(
            memory_id="expired",
            agent_id="agent",
            content="old",
            created_at=NOW,
            updated_at=NOW,
            expires_at=NOW + timedelta(seconds=1),
        )
        await self.memory_store.upsert(record)
        self.clock.now += timedelta(seconds=2)
        self.assertIsNone(await self.memory_store.get("expired", tenant_id=None, agent_id="agent"))
        self.assertEqual(await self.memory_store.purge_expired(), 1)
        bad_pool = FakeStatePool()
        bad_pool.schema["production_state"] = 99
        with self.assertRaises(PersistenceError):
            await PostgresMemoryStore(bad_pool).initialize()

    async def test_session_conflicts_expiry_delete_and_import(self) -> None:
        session = Session(
            session_id="session-extra",
            agent_id="agent",
            created_at=NOW,
            updated_at=NOW,
        )
        await self.session_store.initialize()  # type: ignore[attr-defined]
        await self.session_store.initialize()  # type: ignore[attr-defined]
        await self.session_store.create(session)
        message = Message.from_text(MessageRole.USER, "one")
        await self.session_store.append(
            session.session_id,
            (message,),
            turn_id="turn",
            idempotency_key="same",
        )
        with self.assertRaises(SessionConflictError):
            await self.session_store.append(
                session.session_id,
                (Message.from_text(MessageRole.USER, "different"),),
                turn_id="turn",
                idempotency_key="same",
            )
        with self.assertRaises(SessionConflictError):
            await self.session_store.append(
                session.session_id,
                (message,),
                turn_id="next",
                idempotency_key="next",
                expected_revision=0,
            )
        with self.assertRaises(SessionNotFoundError):
            await self.session_store.append("missing", (message,), turn_id="x", idempotency_key="x")
        self.assertTrue(await self.session_store.delete(session.session_id))
        self.assertFalse(await self.session_store.delete(session.session_id))
        expired = session.model_copy(
            update={"session_id": "expired", "expires_at": NOW + timedelta(seconds=1)}
        )
        await self.session_store.create(expired)
        self.clock.now += timedelta(seconds=2)
        with self.assertRaises(SessionNotFoundError):
            await self.session_store.get("expired")
        self.assertEqual(await self.session_store.purge_expired(), 1)
        with self.assertRaises(ValueError):
            await self.session_store.purge_expired(now=datetime(2026, 1, 1))

    async def test_memory_mutation_filters_and_delete(self) -> None:
        record = MemoryRecord(
            memory_id="mutable",
            agent_id="agent",
            content="alpha beta",
            tags=("one", "two"),
            created_at=NOW,
            updated_at=NOW,
        )
        await self.memory_store.upsert(record)
        updated = record.model_copy(
            update={"content": "beta gamma", "updated_at": NOW + timedelta(seconds=1)}
        )
        await self.memory_store.upsert(updated)
        loaded = await self.memory_store.get("mutable", tenant_id=None, agent_id="agent")
        self.assertEqual(loaded, updated)
        self.assertEqual(
            await self.memory_store.search(
                "gamma", tenant_id=None, agent_id="agent", tags=("two",), limit=1
            ),
            (updated,),
        )
        with self.assertRaises(ValueError):
            await self.memory_store.search("", tenant_id=None, agent_id="agent", limit=0)
        with self.assertRaises(PersistenceError):
            await self.memory_store.upsert(
                updated.model_copy(update={"created_at": NOW + timedelta(seconds=1)})
            )
        self.assertTrue(await self.memory_store.delete("mutable", tenant_id=None, agent_id="agent"))
        deleted_again = await self.memory_store.delete("mutable", tenant_id=None, agent_id="agent")
        self.assertFalse(deleted_again)

    async def test_approval_pending_idempotency_and_conflicts(self) -> None:
        request = ApprovalRequest.for_tool_call(
            ToolCall(id="approval-call", name="write", arguments={}),
            run_id=uuid4(),
            trace_id=uuid4(),
            agent_id="agent",
            session_id="session-x",
            tenant_id="tenant",
            clock=self.clock,
        )
        self.assertEqual(await self.approval_store.create(request), request)
        self.assertEqual(await self.approval_store.create(request), request)
        self.assertEqual(await self.approval_store.list_pending(tenant_id="tenant"), (request,))
        self.assertEqual(
            await self.approval_store.list_pending(tenant_id="tenant", session_id="other"), ()
        )
        with self.assertRaises(ApprovalConflictError):
            await self.approval_store.create(request.model_copy(update={"metadata": {"x": 1}}))
        with self.assertRaises(ApprovalConflictError):
            await self.approval_store.resolve(
                request.approval_id, ApprovalDecision.APPROVE, actor_id=" ", tenant_id="tenant"
            )
        with self.assertRaises(ApprovalConflictError):
            await self.approval_store.claim(request.approval_id, tenant_id="tenant")
        with self.assertRaises(ApprovalConflictError):
            await self.approval_store.resolve(
                request.approval_id,
                ApprovalDecision.APPROVE,
                actor_id="actor",
                tenant_id="tenant",
                expected_revision=9,
            )
        resolved = await self.approval_store.resolve(
            request.approval_id, ApprovalDecision.REJECT, actor_id="actor", tenant_id="tenant"
        )
        self.assertEqual(
            await self.approval_store.resolve(
                request.approval_id, ApprovalDecision.REJECT, actor_id="actor", tenant_id="tenant"
            ),
            resolved,
        )
        with self.assertRaises(ApprovalConflictError):
            await self.approval_store.resolve(
                request.approval_id, ApprovalDecision.APPROVE, actor_id="actor", tenant_id="tenant"
            )


class FakeS3Client:
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}

    def put_object(self, **kwargs: Any) -> None:
        key = kwargs["Key"]
        if key in self.items and kwargs.get("IfNoneMatch") == "*":
            raise FakeCloudError("PreconditionFailed")
        self.items[key] = bytes(kwargs["Body"])

    def get_object(self, **kwargs: Any) -> dict[str, Any]:
        if kwargs["Key"] not in self.items:
            raise FakeCloudError("NoSuchKey")
        return {"Body": BytesIO(self.items[kwargs["Key"]])}

    def head_object(self, **kwargs: Any) -> None:
        if kwargs["Key"] not in self.items:
            raise FakeCloudError("NoSuchKey")

    def delete_object(self, **kwargs: Any) -> None:
        self.items.pop(kwargs["Key"], None)

    def list_objects_v2(self, **kwargs: Any) -> dict[str, Any]:
        return {
            "Contents": [
                {"Key": key} for key in self.items if key.startswith(kwargs.get("Prefix", ""))
            ],
            "IsTruncated": False,
        }


class FakeCloudError(Exception):
    def __init__(self, code: str) -> None:
        self.response = {"Error": {"Code": code}}


class FakeAzureClient:
    def __init__(self) -> None:
        self.items: dict[str, bytes] = {}

    async def upload_blob(self, *, name: str, data: bytes, overwrite: bool, **kwargs: Any) -> None:
        if name in self.items and not overwrite:
            raise FakeCloudError("BlobAlreadyExists")
        self.items[name] = data

    async def download_blob(self, name: str) -> Any:
        if name not in self.items:
            raise FakeCloudError("BlobNotFound")

        async def readall() -> bytes:
            return self.items[name]

        return SimpleNamespace(readall=readall)

    async def delete_blob(self, name: str) -> None:
        if name not in self.items:
            raise FakeCloudError("BlobNotFound")
        del self.items[name]

    async def list_blobs(self, *, name_starts_with: str) -> AsyncIterator[Any]:
        for name in tuple(self.items):
            if name.startswith(name_starts_with):
                yield SimpleNamespace(name=name)


class ObjectStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_s3_and_azure_artifact_contract(self) -> None:
        stores = (
            S3ArtifactStore(FakeS3Client(), bucket="bucket"),
            AzureBlobArtifactStore(FakeAzureClient()),
        )
        for store in stores:
            self.assertIsInstance(store, ArtifactStore)
            record = await store.put(
                b"payload",
                name="result.txt",
                media_type="text/plain",
                tenant_id="tenant-a",
                session_id="session-a",
                artifact_id="artifact-a",
            )
            loaded = await store.get(record.ref.artifact_id, tenant_id="tenant-a")
            self.assertEqual(loaded[1], b"payload")
            with self.assertRaises(ArtifactNotFoundError):
                await store.get(record.ref.artifact_id, tenant_id="tenant-b")
            self.assertEqual(await store.delete_session("session-a", tenant_id="tenant-a"), 1)

    async def test_blob_ports_errors_and_factories(self) -> None:
        s3 = S3BlobStore(FakeS3Client(), bucket="bucket", prefix="root")
        azure = AzureBlobStore(FakeAzureClient(), prefix="root")
        for store in (s3, azure):
            self.assertIsInstance(store, BlobStore)
            await store.put("one", b"1")
            with self.assertRaises(PersistenceError):
                await store.put("one", b"2")
            self.assertEqual([key async for key in store.list_keys()], ["one"])
            self.assertTrue(await store.delete("one"))
            self.assertFalse(await store.delete("one"))
        with (
            patch.dict("sys.modules", {"boto3": None}),
            self.assertRaises(PersistenceError),
        ):
            create_s3_client()
        with (
            patch.dict("sys.modules", {"azure.storage.blob.aio": None}),
            self.assertRaises(PersistenceError),
        ):
            create_azure_container_client(account_url="https://example", container_name="x")

    async def test_artifact_expiry_corruption_and_validation(self) -> None:
        clock = Clock()
        client = FakeS3Client()
        blobs = S3BlobStore(client, bucket="bucket")
        store = ObjectArtifactStore(blobs, clock=clock)
        await store.put(
            b"old",
            name="old.txt",
            media_type="text/plain",
            artifact_id="old",
            ttl_seconds=1,
        )
        clock.now += timedelta(seconds=2)
        with self.assertRaises(ArtifactNotFoundError):
            await store.get("old")
        self.assertEqual(await store.purge_expired(), 1)
        with self.assertRaises(ValueError):
            S3BlobStore(client, bucket=" ")
        with self.assertRaises(PersistenceError):
            await blobs.put("../unsafe", b"x")
        with self.assertRaises(ValueError):
            create_azure_container_client(account_url="", container_name="x")


class MigrationTests(unittest.IsolatedAsyncioTestCase):
    async def test_sqlite_to_postgres_dry_run_and_copy(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "state.db"
            clock = Clock()
            session_store = SQLiteSessionStore(path, clock=clock)
            memory_store = SQLiteMemoryStore(path, clock=clock)
            approval_store = SQLiteApprovalStore(path, clock=clock)
            run_store = SQLiteRunStore(path)
            session = Session(
                session_id="migrated",
                agent_id="agent",
                tenant_id="tenant",
                created_at=NOW,
                updated_at=NOW,
            )
            await session_store.create(session)
            await session_store.append(
                "migrated",
                (Message.from_text(MessageRole.USER, "hello"),),
                turn_id="turn",
                tenant_id="tenant",
                idempotency_key="append",
            )
            await memory_store.upsert(
                MemoryRecord(
                    memory_id="memory",
                    agent_id="agent",
                    tenant_id="tenant",
                    content="remember",
                    created_at=NOW,
                    updated_at=NOW,
                )
            )
            request = ApprovalRequest.for_tool_call(
                ToolCall(id="call", name="read", arguments={}),
                run_id=uuid4(),
                trace_id=uuid4(),
                agent_id="agent",
                session_id="migrated",
                tenant_id="tenant",
                clock=clock,
            )
            await approval_store.create(request)
            run_id = uuid4()
            await run_store.append_checkpoint(
                RunCheckpoint(
                    run_id=run_id,
                    trace_id=uuid4(),
                    agent_id="agent",
                    agent_version="1.0.0",
                    session_id="migrated",
                    tenant_id="tenant",
                    sequence=0,
                    kind=CheckpointKind.RUN_STARTED,
                    status=RunStatus.RUNNING,
                    created_at=NOW,
                )
            )
            await session_store.aclose()
            await memory_store.aclose()
            await approval_store.aclose()
            run_store.close()
            pool = FakeStatePool()
            dry = await migrate_sqlite_to_postgres((path,), pool, dry_run=True)
            self.assertEqual(
                dry.model_dump(exclude={"dry_run", "source_files"}),
                {
                    "sessions": 1,
                    "session_entries": 1,
                    "memories": 1,
                    "approvals": 1,
                    "durable_runs": 1,
                },
            )
            report = await migrate_sqlite_to_postgres((path,), pool)
            self.assertFalse(report.dry_run)
            repeated = await migrate_sqlite_to_postgres((path,), pool)
            self.assertEqual(repeated, report)
            self.assertEqual(
                len(await PostgresSessionStore(pool).list_entries("migrated", tenant_id="tenant")),
                1,
            )
            checkpoint = await PostgresRunStore(pool).latest_checkpoint(run_id, tenant_id="tenant")
            self.assertEqual(checkpoint.sequence, 0)

    async def test_migration_validation_and_cli_dry_run(self) -> None:
        pool = FakeStatePool()
        with self.assertRaises(ValueError):
            await migrate_sqlite_to_postgres((), pool)
        with self.assertRaises(PersistenceError):
            await migrate_sqlite_to_postgres(("missing.db",), pool)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "empty.db"
            connection = __import__("sqlite3").connect(path)
            connection.close()
            output = BytesIO()
            text_output = __import__("io").TextIOWrapper(output, encoding="utf-8")
            with redirect_stdout(text_output):
                result = await asyncio.to_thread(
                    cli_main, ["migrate-state", "--sqlite", str(path), "--dry-run"]
                )
            text_output.flush()
            self.assertEqual(result, 0)
            self.assertIn(b'"dry_run": true', output.getvalue())


if __name__ == "__main__":
    unittest.main()
