from __future__ import annotations

import asyncio
import json
import sys
import tempfile
import unittest
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch
from uuid import UUID, uuid4

from pyagentskit.coordination import (
    Lease,
    LeaseConflictError,
    LeaseNotFoundError,
    LeaseStore,
    MemoryLeaseStore,
    SQLiteLeaseStore,
)
from pyagentskit.durability import (
    CheckpointKind,
    EffectRecord,
    EffectResolution,
    EffectStatus,
    RunCheckpoint,
    RunStore,
)
from pyagentskit.exceptions import PersistenceError, RunConflictError, RunNotFoundError
from pyagentskit.postgres import (
    AsyncPostgresConnection,
    AsyncPostgresPool,
    PostgresLeaseStore,
    PostgresRunStore,
    create_asyncpg_pool,
)
from pyagentskit.runs import RunStatus
from pyagentskit.tools import ToolCall, ToolResult, ToolResultStatus

NOW = datetime(2026, 9, 9, 12, tzinfo=UTC)


class MutableClock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


class LeaseContract:
    store: LeaseStore
    clock: MutableClock

    async def test_lifecycle_tenant_isolation_and_fencing(self) -> None:
        first = await self.store.acquire(
            "run:one", owner_id="worker-a", tenant_id="tenant-a", ttl_seconds=30
        )
        self.assertEqual(first.fencing_token, 1)
        self.assertEqual(
            await self.store.acquire(
                "run:one", owner_id="worker-a", tenant_id="tenant-a", ttl_seconds=30
            ),
            first,
        )
        with self.assertRaises(LeaseConflictError):
            await self.store.acquire(
                "run:one", owner_id="worker-b", tenant_id="tenant-a", ttl_seconds=30
            )
        isolated = await self.store.acquire(
            "run:one", owner_id="worker-b", tenant_id="tenant-b", ttl_seconds=30
        )
        self.assertEqual(isolated.fencing_token, 1)
        renewed = await self.store.renew(first, ttl_seconds=60)
        self.assertEqual(renewed.revision, 1)
        with self.assertRaises(LeaseConflictError):
            await self.store.assert_current(first)
        await self.store.assert_current(renewed)
        await self.store.release(renewed)
        with self.assertRaises(LeaseNotFoundError):
            await self.store.get("run:one", tenant_id="tenant-a")
        next_lease = await self.store.acquire(
            "run:one", owner_id="worker-c", tenant_id="tenant-a", ttl_seconds=30
        )
        self.assertEqual(next_lease.fencing_token, 2)

    async def test_expiry_purge_and_validation(self) -> None:
        lease = await self.store.acquire(
            "run:two", owner_id="worker-a", tenant_id="tenant-a", ttl_seconds=5
        )
        self.clock.now += timedelta(seconds=6)
        with self.assertRaises(LeaseNotFoundError):
            await self.store.get("run:two", tenant_id="tenant-a")
        with self.assertRaises(LeaseConflictError):
            await self.store.renew(lease, ttl_seconds=5)
        replacement = await self.store.acquire(
            "run:two", owner_id="worker-b", tenant_id="tenant-a", ttl_seconds=5
        )
        self.assertEqual(replacement.fencing_token, 2)
        self.clock.now += timedelta(seconds=6)
        self.assertEqual(await self.store.purge_expired(), 1)
        for invalid in (0.0, -1.0, float("inf")):
            with self.assertRaises(ValueError):
                await self.store.acquire("run:x", owner_id="worker", ttl_seconds=invalid)
        with self.assertRaises(ValueError):
            await self.store.acquire(" ", owner_id="worker", ttl_seconds=1)
        with self.assertRaises(ValueError):
            await self.store.acquire("run:x", owner_id=" ", ttl_seconds=1)


class MemoryLeaseStoreTests(LeaseContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.clock = MutableClock()
        self.store = MemoryLeaseStore(clock=self.clock)

    async def test_concurrent_acquisition_has_one_winner(self) -> None:
        outcomes = await asyncio.gather(
            *(
                self.store.acquire("shared", owner_id=f"worker-{index}", ttl_seconds=10)
                for index in range(12)
            ),
            return_exceptions=True,
        )
        self.assertEqual(sum(isinstance(item, Lease) for item in outcomes), 1)
        self.assertEqual(sum(isinstance(item, LeaseConflictError) for item in outcomes), 11)


class SQLiteLeaseStoreTests(LeaseContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.clock = MutableClock()
        self.store = SQLiteLeaseStore(
            Path(self.temporary.name) / "coordination.sqlite", clock=self.clock
        )

    async def asyncTearDown(self) -> None:
        await self.store.aclose()  # type: ignore[attr-defined]
        self.temporary.cleanup()

    async def test_two_instances_serialize_acquisition_and_keep_counter(self) -> None:
        second = SQLiteLeaseStore(self.store.path, clock=self.clock)  # type: ignore[attr-defined]
        try:
            outcomes = await asyncio.gather(
                self.store.acquire("shared", owner_id="a", ttl_seconds=10),
                second.acquire("shared", owner_id="b", ttl_seconds=10),
                return_exceptions=True,
            )
            self.assertEqual(sum(isinstance(item, Lease) for item in outcomes), 1)
            self.assertEqual(sum(isinstance(item, LeaseConflictError) for item in outcomes), 1)
        finally:
            await second.aclose()

    async def test_async_context_manager_closes_store(self) -> None:
        path = Path(self.temporary.name) / "context.sqlite"
        async with SQLiteLeaseStore(path, clock=self.clock) as scoped:
            await scoped.acquire("resource", owner_id="worker", ttl_seconds=1)
        with self.assertRaises(PersistenceError):
            await scoped.acquire("other", owner_id="worker", ttl_seconds=1)


class _Context(AbstractAsyncContextManager[Any]):
    def __init__(self, enter: Any, exit: Any | None = None) -> None:
        self._enter = enter
        self._exit = exit

    async def __aenter__(self) -> Any:
        if self._enter is not None:
            result = self._enter()
            if asyncio.iscoroutine(result):
                await result
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        if self._exit is not None:
            result = self._exit()
            if asyncio.iscoroutine(result):
                await result


class FakePostgresPool:
    """Small transactional asyncpg double; it never opens a socket."""

    def __init__(self, *, clock: MutableClock | None = None) -> None:
        self.clock = clock or MutableClock()
        self.lock = asyncio.Lock()
        self.schema: dict[str, int] = {}
        self.tokens: dict[tuple[str, str], int] = {}
        self.leases: dict[tuple[str, str], dict[str, Any]] = {}
        self.runs: dict[tuple[str, UUID], str] = {}
        self.init_statements = 0

    def acquire(self) -> _AcquireContext:
        return _AcquireContext(FakePostgresConnection(self))


class _AcquireContext(AbstractAsyncContextManager[AsyncPostgresConnection]):
    def __init__(self, connection: FakePostgresConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> FakePostgresConnection:
        return self.connection

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FakePostgresConnection:
    def __init__(self, pool: FakePostgresPool) -> None:
        self.pool = pool

    def transaction(self) -> _Context:
        return _Context(self.pool.lock.acquire, self.pool.lock.release)

    async def execute(self, query: str, *args: object) -> str:
        normalized = " ".join(query.split())
        if normalized.startswith("CREATE "):
            self.pool.init_statements += 1
            return "CREATE TABLE"
        if "schema_versions(component, version)" in normalized:
            self.pool.schema.setdefault(str(args[0]), int(args[1]))
            return "INSERT 0 1"
        if "lease_tokens(tenant_scope, resource_id, last_token)" in normalized:
            self.pool.tokens.setdefault((str(args[0]), str(args[1])), 0)
            return "INSERT 0 1"
        if "lease_tokens SET last_token" in normalized:
            self.pool.tokens[(str(args[0]), str(args[1]))] = int(args[2])
            return "UPDATE 1"
        if "_leases(tenant_scope, resource_id, lease_id" in normalized:
            key = (str(args[0]), str(args[1]))
            self.pool.leases[key] = {
                "tenant_scope": args[0],
                "resource_id": args[1],
                "lease_id": args[2],
                "owner_id": args[3],
                "fencing_token": args[4],
                "revision": args[5],
                "acquired_at": args[6],
                "expires_at": args[7],
            }
            return "INSERT 0 1"
        if "_leases SET expires_at" in normalized:
            item = self.pool.leases[(str(args[0]), str(args[1]))]
            item.update(expires_at=args[2], revision=args[3])
            return "UPDATE 1"
        if normalized.startswith("DELETE FROM") and "_leases WHERE" in normalized:
            if "COALESCE" in normalized:
                moment = args[0] or self.pool.clock()
                keys = [
                    key for key, item in self.pool.leases.items() if item["expires_at"] <= moment
                ]
                for key in keys:
                    del self.pool.leases[key]
                return f"DELETE {len(keys)}"
            existed = self.pool.leases.pop((str(args[0]), str(args[1])), None) is not None
            return f"DELETE {int(existed)}"
        if "_run_locks(tenant_scope, run_id)" in normalized:
            return "INSERT 0 1"
        if "_runs(tenant_scope, run_id, payload_json)" in normalized:
            self.pool.runs[(str(args[0]), args[1])] = str(args[2])  # type: ignore[index]
            return "INSERT 0 1"
        raise AssertionError(f"Unhandled execute: {normalized}")

    async def fetchrow(self, query: str, *args: object) -> dict[str, Any] | None:
        normalized = " ".join(query.split())
        if "schema_versions WHERE component" in normalized:
            value = self.pool.schema.get(str(args[0]))
            return None if value is None else {"version": value}
        if "last_token, CURRENT_TIMESTAMP" in normalized:
            value = self.pool.tokens.get((str(args[0]), str(args[1])))
            return None if value is None else {"last_token": value, "now": self.pool.clock()}
        if "SELECT *, CURRENT_TIMESTAMP" in normalized and "_leases" in normalized:
            value = self.pool.leases.get((str(args[0]), str(args[1])))
            return None if value is None else {**value, "now": self.pool.clock()}
        if "SELECT * FROM" in normalized and "_leases" in normalized:
            value = self.pool.leases.get((str(args[0]), str(args[1])))
            return None if value is None else dict(value)
        if "SELECT run_id FROM" in normalized and "_run_locks" in normalized:
            return {"run_id": args[1]}
        if "payload_json @>" in normalized:
            scope, needle = str(args[0]), json.loads(str(args[1]))
            effect_id = needle["effects"][0]["effect_id"]
            for (stored_scope, _), payload in self.pool.runs.items():
                if stored_scope == scope and any(
                    item["effect_id"] == effect_id for item in json.loads(payload)["effects"]
                ):
                    return {"payload_json": payload}
            return None
        if "SELECT payload_json FROM" in normalized and "_runs" in normalized:
            payload = self.pool.runs.get((str(args[0]), args[1]))  # type: ignore[index]
            return None if payload is None else {"payload_json": payload}
        raise AssertionError(f"Unhandled fetchrow: {normalized}")

    async def fetch(self, query: str, *args: object) -> list[dict[str, Any]]:
        raise AssertionError(f"Unhandled fetch: {query} {args}")


class PostgresLeaseStoreTests(LeaseContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.clock = MutableClock()
        self.pool = FakePostgresPool(clock=self.clock)
        self.store = PostgresLeaseStore(self.pool)

    async def test_ports_and_lazy_idempotent_initialization(self) -> None:
        self.assertIsInstance(self.pool, AsyncPostgresPool)
        self.assertIsInstance(FakePostgresConnection(self.pool), AsyncPostgresConnection)
        self.assertIsInstance(self.store, LeaseStore)
        await asyncio.gather(self.store.initialize(), self.store.initialize())
        first_count = self.pool.init_statements
        await self.store.initialize()
        self.assertEqual(self.pool.init_statements, first_count)

    async def test_unsafe_table_prefix_and_newer_schema_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            PostgresLeaseStore(self.pool, table_prefix="bad-prefix;drop")
        pool = FakePostgresPool()
        pool.schema["coordination_leases"] = 99
        with self.assertRaises(PersistenceError):
            await PostgresLeaseStore(pool).initialize()

    async def test_pool_helper_validates_before_optional_import(self) -> None:
        with self.assertRaises(ValueError):
            await create_asyncpg_pool(" ")
        with self.assertRaises(ValueError):
            await create_asyncpg_pool("postgresql://example", min_size=2, max_size=1)
        with self.assertRaises(ValueError):
            await create_asyncpg_pool("postgresql://example", command_timeout=0)
        with (
            patch.dict(sys.modules, {"asyncpg": None}),
            self.assertRaises(PersistenceError),
        ):
            await create_asyncpg_pool("postgresql://example")

        async def create_pool(**kwargs: object) -> FakePostgresPool:
            self.assertEqual(kwargs["min_size"], 2)
            return self.pool

        module = SimpleNamespace(create_pool=create_pool)
        with patch.dict(sys.modules, {"asyncpg": module}):
            created = await create_asyncpg_pool("postgresql://example", min_size=2, max_size=3)
        self.assertIs(created, self.pool)

        async def empty_pool(**kwargs: object) -> None:
            return None

        with (
            patch.dict(sys.modules, {"asyncpg": SimpleNamespace(create_pool=empty_pool)}),
            self.assertRaises(PersistenceError),
        ):
            await create_asyncpg_pool("postgresql://example")

    async def test_database_time_expiry_purge_and_stale_operations(self) -> None:
        lease = await self.store.acquire("expiring", owner_id="worker", ttl_seconds=1)
        self.clock.now += timedelta(seconds=2)
        with self.assertRaises(LeaseNotFoundError):
            await self.store.get("expiring")
        with self.assertRaises(LeaseConflictError):
            await self.store.renew(lease, ttl_seconds=1)
        self.assertEqual(await self.store.purge_expired(), 1)
        with self.assertRaises(LeaseNotFoundError):
            await self.store.release(lease)
        with self.assertRaises(ValueError):
            await self.store.purge_expired(now=datetime(2026, 1, 1))


def checkpoint(run_id: UUID, *, tenant_id: str = "tenant-a", sequence: int = 0) -> RunCheckpoint:
    return RunCheckpoint(
        run_id=run_id,
        trace_id=uuid4(),
        agent_id="agent",
        agent_version="1.0.0",
        session_id="session",
        tenant_id=tenant_id,
        sequence=sequence,
        kind=CheckpointKind.RUN_STARTED,
        status=RunStatus.RUNNING,
        created_at=NOW,
    )


def effect(run_id: UUID, *, tenant_id: str = "tenant-a") -> EffectRecord:
    return EffectRecord(
        run_id=run_id,
        trace_id=uuid4(),
        agent_id="agent",
        session_id="session",
        tenant_id=tenant_id,
        idempotency_key="effect-1",
        fingerprint="a" * 64,
        call=ToolCall(id="call-1", name="read", arguments={"id": 1}),
        tool_version="1.0.0",
        idempotent=True,
        planned_at=NOW,
    )


class PostgresRunStoreTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pool = FakePostgresPool()
        self.store = PostgresRunStore(self.pool)

    async def test_run_store_contract_and_tenant_isolation(self) -> None:
        self.assertIsInstance(self.store, RunStore)
        run_id = uuid4()
        first = checkpoint(run_id)
        await self.store.append_checkpoint(first, expected_previous_sequence=-1)
        self.assertEqual(await self.store.latest_checkpoint(run_id, tenant_id="tenant-a"), first)
        with self.assertRaises(RunNotFoundError):
            await self.store.latest_checkpoint(run_id, tenant_id="tenant-b")
        with self.assertRaises(RunConflictError):
            await self.store.append_checkpoint(
                checkpoint(run_id, sequence=1), expected_previous_sequence=-1
            )

    async def test_effect_lifecycle_and_jsonb_lookup(self) -> None:
        run_id = uuid4()
        item = await self.store.plan_effect(effect(run_id))
        self.assertEqual(await self.store.get_effect(item.effect_id, tenant_id="tenant-a"), item)
        self.assertIsNone(
            await self.store.get_effect_by_key(run_id, "missing", tenant_id="tenant-a")
        )
        self.assertIsNone(
            await self.store.get_effect_by_key(uuid4(), "missing", tenant_id="tenant-a")
        )
        started = await self.store.transition_effect(
            item.effect_id,
            EffectStatus.STARTED,
            tenant_id="tenant-a",
            expected_revision=0,
        )
        completed = await self.store.transition_effect(
            item.effect_id,
            EffectStatus.COMPLETED,
            tenant_id="tenant-a",
            expected_revision=started.revision,
            result=ToolResult(
                call_id="call-1",
                tool_name="read",
                status=ToolResultStatus.SUCCEEDED,
                content={"ok": True},
            ),
        )
        self.assertEqual(completed.status, EffectStatus.COMPLETED)
        self.assertEqual(
            await self.store.get_effect_by_key(run_id, "effect-1", tenant_id="tenant-a"),
            completed,
        )
        self.assertEqual(await self.store.list_effects(run_id, tenant_id="tenant-a"), (completed,))
        self.assertEqual(len(await self.store.list_journal(run_id, tenant_id="tenant-a")), 3)
        with self.assertRaises(RunNotFoundError):
            await self.store.get_effect(item.effect_id, tenant_id="tenant-b")

    async def test_initialization_rejects_newer_schema(self) -> None:
        pool = FakePostgresPool()
        pool.schema["durable_runs"] = 2
        with self.assertRaises(PersistenceError):
            await PostgresRunStore(pool).initialize()

    async def test_empty_aggregate_has_no_checkpoint_or_effect(self) -> None:
        run_id = uuid4()
        await self.store.plan_effect(effect(run_id))
        with self.assertRaises(RunNotFoundError):
            await self.store.latest_checkpoint(run_id, tenant_id="tenant-a")
        with self.assertRaises(RunNotFoundError):
            await self.store.get_effect("missing", tenant_id="tenant-a")
        self.assertEqual(await self.store.list_checkpoints(run_id, tenant_id="tenant-a"), ())

    async def test_unknown_effect_can_be_reconciled(self) -> None:
        run_id = uuid4()
        planned = await self.store.plan_effect(effect(run_id))
        started = await self.store.transition_effect(
            planned.effect_id,
            EffectStatus.STARTED,
            tenant_id="tenant-a",
            expected_revision=0,
        )
        unknown = await self.store.transition_effect(
            planned.effect_id,
            EffectStatus.UNKNOWN,
            tenant_id="tenant-a",
            expected_revision=started.revision,
        )
        reset = await self.store.resolve_effect(
            planned.effect_id,
            EffectResolution.NOT_APPLIED,
            tenant_id="tenant-a",
            expected_revision=unknown.revision,
        )
        self.assertEqual(reset.status, EffectStatus.PLANNED)


class LeaseContractValidationTests(unittest.TestCase):
    def test_lease_requires_aware_ordered_timestamps(self) -> None:
        with self.assertRaises(ValueError):
            Lease(
                resource_id="resource",
                owner_id="owner",
                fencing_token=1,
                acquired_at=datetime(2026, 1, 1),
                expires_at=datetime(2026, 1, 2),
            )
        with self.assertRaises(ValueError):
            Lease(
                resource_id="resource",
                owner_id="owner",
                fencing_token=1,
                acquired_at=NOW,
                expires_at=NOW,
            )


if __name__ == "__main__":
    unittest.main()
