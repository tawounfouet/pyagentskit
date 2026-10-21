"""Explicitly gated PostgreSQL integration qualification.

This module never connects unless both the exact gate and a DSN are supplied.
It creates only uniquely prefixed PyAgentsKit tables in the selected database.
"""

from __future__ import annotations

import os
import unittest
from datetime import UTC, datetime
from uuid import uuid4

from pyagentskit import (
    AgentDefinition,
    DurableRunner,
    FinishReason,
    ModelRef,
    ModelResponse,
    RunContext,
    RunStatus,
    TextContent,
    ToolRegistry,
)
from pyagentskit.coordination import LeaseConflictError
from pyagentskit.distributed import (
    DistributedDurableRunner,
    DistributedEventType,
    MemoryDistributedEventSink,
)
from pyagentskit.memory import MemoryRecord
from pyagentskit.postgres import PostgresLeaseStore, PostgresRunStore, create_asyncpg_pool
from pyagentskit.postgres_state import (
    PostgresApprovalStore,
    PostgresMemoryStore,
    PostgresSessionStore,
)
from pyagentskit.runtime import Runner
from pyagentskit.sessions import Session
from pyagentskit.testing import FakeModel


class PostgresLiveQualification(unittest.IsolatedAsyncioTestCase):
    @unittest.skipUnless(
        os.getenv("PYAGENTSKIT_LIVE_POSTGRES") == "I_ACCEPT_DATABASE_WRITES"
        and bool(os.getenv("PYAGENTSKIT_POSTGRES_DSN")),
        "PostgreSQL live qualification is opt-in",
    )
    async def test_distributed_lease_round_trip(self) -> None:
        dsn = os.environ["PYAGENTSKIT_POSTGRES_DSN"]
        prefix = "paktest_" + uuid4().hex[:12]
        pool = await create_asyncpg_pool(dsn, min_size=1, max_size=2)
        store = PostgresLeaseStore(pool, table_prefix=prefix)
        try:
            await store.initialize()
            first = await store.acquire(
                "run:qualification",
                owner_id="worker-a",
                tenant_id="tenant-a",
                ttl_seconds=10,
            )
            with self.assertRaises(LeaseConflictError):
                await store.acquire(
                    "run:qualification",
                    owner_id="worker-b",
                    tenant_id="tenant-a",
                    ttl_seconds=10,
                )
            renewed = await store.renew(first, ttl_seconds=20)
            await store.assert_current(renewed)
            await store.release(renewed)
        finally:
            async with pool.acquire() as connection:
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_leases")
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_lease_tokens")
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_schema_versions")
            close = getattr(pool, "close", None)
            if close is not None:
                await close()

    @unittest.skipUnless(
        os.getenv("PYAGENTSKIT_LIVE_POSTGRES") == "I_ACCEPT_DATABASE_WRITES"
        and bool(os.getenv("PYAGENTSKIT_POSTGRES_DSN")),
        "PostgreSQL live qualification is opt-in",
    )
    async def test_production_state_round_trip(self) -> None:
        dsn = os.environ["PYAGENTSKIT_POSTGRES_DSN"]
        prefix = "paktest_" + uuid4().hex[:12]
        pool = await create_asyncpg_pool(dsn, min_size=1, max_size=3)
        session_store = PostgresSessionStore(pool, table_prefix=prefix)
        memory_store = PostgresMemoryStore(pool, table_prefix=prefix)
        approval_store = PostgresApprovalStore(pool, table_prefix=prefix)
        now = datetime.now(UTC)
        try:
            await session_store.create(
                Session(
                    session_id="live-session",
                    agent_id="agent",
                    tenant_id="tenant-a",
                    created_at=now,
                    updated_at=now,
                )
            )
            await memory_store.upsert(
                MemoryRecord(
                    memory_id="live-memory",
                    agent_id="agent",
                    tenant_id="tenant-a",
                    content="PostgreSQL qualification",
                    created_at=now,
                    updated_at=now,
                )
            )
            self.assertEqual(
                len(
                    await memory_store.search(
                        "qualification", tenant_id="tenant-a", agent_id="agent"
                    )
                ),
                1,
            )
            self.assertEqual(await approval_store.list_pending(tenant_id="tenant-a"), ())
        finally:
            async with pool.acquire() as connection:
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_state")
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_schema_versions")
            close = getattr(pool, "close", None)
            if close is not None:
                await close()

    @unittest.skipUnless(
        os.getenv("PYAGENTSKIT_LIVE_POSTGRES") == "I_ACCEPT_DATABASE_WRITES"
        and bool(os.getenv("PYAGENTSKIT_POSTGRES_DSN")),
        "PostgreSQL live qualification is opt-in",
    )
    async def test_two_worker_distributed_durable_takeover(self) -> None:
        dsn = os.environ["PYAGENTSKIT_POSTGRES_DSN"]
        prefix = "paktest_" + uuid4().hex[:12]
        pool = await create_asyncpg_pool(dsn, min_size=1, max_size=4)
        leases = PostgresLeaseStore(pool, table_prefix=prefix)
        runs = PostgresRunStore(pool, table_prefix=prefix)
        sessions = PostgresSessionStore(pool, table_prefix=prefix)
        session_id = "live-distributed-session"
        now = datetime.now(UTC)
        audit = MemoryDistributedEventSink()
        try:
            await sessions.create(
                Session(
                    session_id=session_id,
                    agent_id="distributed.live",
                    tenant_id="tenant-a",
                    created_at=now,
                    updated_at=now,
                )
            )
            model = FakeModel(
                [
                    RuntimeError("worker stopped before any effect"),
                    ModelResponse(
                        id="live-final",
                        model="fake",
                        content=(TextContent(text="resumed"),),
                        finish_reason=FinishReason.STOP,
                    ),
                ]
            )
            durable = DurableRunner(
                Runner(model, tools=ToolRegistry(), session_store=sessions), runs
            )
            agent = AgentDefinition(
                id="distributed.live",
                version="1.0.0",
                instructions="Qualify PostgreSQL takeover",
                model=ModelRef(provider="fake", name="fake"),
            )
            context = RunContext(
                agent_id=agent.id,
                deps=None,
                session_id=session_id,
                metadata={"tenant_id": "tenant-a"},
            )
            worker_a = DistributedDurableRunner(
                durable, leases, owner_id="postgres-worker-a", event_sinks=(audit,)
            )
            failed = await worker_a.run(agent, "start", context=context)
            self.assertEqual(failed.status, RunStatus.FAILED)

            worker_b = DistributedDurableRunner(
                durable, leases, owner_id="postgres-worker-b", event_sinks=(audit,)
            )
            resumed = await worker_b.resume(agent, context.run_id, tenant_id="tenant-a")
            self.assertEqual(resumed.status, RunStatus.COMPLETED)
            self.assertEqual(resumed.output, "resumed")
            takeovers = [
                event for event in audit.events if event.type is DistributedEventType.TAKEOVER
            ]
            self.assertEqual(len(takeovers), 1)
            self.assertEqual(takeovers[0].fencing_token, 2)
        finally:
            async with pool.acquire() as connection:
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_runs")
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_run_locks")
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_leases")
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_lease_tokens")
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_state")
                await connection.execute(f"DROP TABLE IF EXISTS {prefix}_schema_versions")
            close = getattr(pool, "close", None)
            if close is not None:
                await close()


if __name__ == "__main__":
    unittest.main()
