"""Run the reusable P0 persistence contracts against a real PostgreSQL service."""

from __future__ import annotations

import os
import unittest
from importlib.resources import files
from uuid import uuid4

from pyagentskit.adapters.persistence import (
    PostgresV2ApprovalRepository,
    PostgresV2ArtifactRepository,
    PostgresV2AuditStore,
    PostgresV2ConversationRepository,
    PostgresV2EffectRepository,
    PostgresV2InboxStore,
    PostgresV2LeaseRepository,
    PostgresV2MemoryRepository,
    PostgresV2MessageRepository,
    PostgresV2OutboxStore,
    PostgresV2ReconciliationRepository,
    PostgresV2RunRepository,
    PostgresV2RuntimeRepository,
    PostgresV2SessionRepository,
    PostgresV2UnitOfWork,
    PostgresV2WorkerRepository,
)
from pyagentskit.domain import Session
from pyagentskit.postgres import create_asyncpg_pool
from tests.persistence_contract_suite import PersistenceContractSuiteMixin

_ENABLED = os.getenv("PYAGENTSKIT_LIVE_POSTGRES") == "I_ACCEPT_DATABASE_WRITES" and bool(
    os.getenv("PYAGENTSKIT_POSTGRES_DSN")
)

_SUFFIXES = (
    "runtime_invocations",
    "runtime_bindings",
    "messages",
    "conversations",
    "sessions",
    "workers",
    "artifacts",
    "reconciliation_evidence",
    "reconciliation_cases",
    "effects",
    "approvals",
    "leases",
    "lease_resources",
    "audit_events",
    "outbox_events",
    "inbox_events",
    "memory_entries",
    "runs",
    "schema_migrations",
)


@unittest.skipUnless(_ENABLED, "PostgreSQL V2 common contracts are opt-in")
class PostgresPersistenceCommonContracts(
    PersistenceContractSuiteMixin,
    unittest.IsolatedAsyncioTestCase,
):
    async def asyncSetUp(self) -> None:
        self.dsn = os.environ["PYAGENTSKIT_POSTGRES_DSN"]
        self.prefix = "pakv2contract_" + uuid4().hex[:8]
        self.pool = await create_asyncpg_pool(self.dsn, min_size=1, max_size=8)

    async def asyncTearDown(self) -> None:
        async with self.pool.acquire() as connection:
            for suffix in _SUFFIXES:
                await connection.execute(f"DROP TABLE IF EXISTS {self.prefix}_v2_{suffix} CASCADE")
        await self.pool.close()

    async def test_postgres_schema_migrates_incrementally_from_v1_to_v2(self) -> None:
        migration_v1 = (
            files("pyagentskit.adapters.persistence.migrations.postgres")
            .joinpath("0001_v2_core.sql")
            .read_text(encoding="utf-8")
            .replace("__PFX__", self.prefix)
        )
        async with self.pool.acquire() as connection:
            await connection.execute(migration_v1)
            before = await connection.fetchval(
                f"SELECT version FROM {self.prefix}_v2_schema_migrations "
                "WHERE component='persistence_v2'"
            )
            self.assertEqual(before, 1)

        sessions = PostgresV2SessionRepository(
            self.pool,
            table_prefix=self.prefix,
        )
        session = Session()
        await sessions.add(session)

        async with self.pool.acquire() as connection:
            after = await connection.fetchval(
                f"SELECT version FROM {self.prefix}_v2_schema_migrations "
                "WHERE component='persistence_v2'"
            )
            self.assertEqual(after, 2)
            table_name = await connection.fetchval(
                "SELECT to_regclass($1)::text",
                f"{self.prefix}_v2_runtime_invocations",
            )
            self.assertEqual(
                table_name,
                f"{self.prefix}_v2_runtime_invocations",
            )

    async def make_run_repository(self):
        return PostgresV2RunRepository(self.pool, table_prefix=self.prefix)

    async def make_session_repository(self):
        return PostgresV2SessionRepository(self.pool, table_prefix=self.prefix)

    async def make_conversation_repository(self):
        return PostgresV2ConversationRepository(self.pool, table_prefix=self.prefix)

    async def make_message_repository(self):
        return PostgresV2MessageRepository(self.pool, table_prefix=self.prefix)

    async def make_memory_repository(self):
        return PostgresV2MemoryRepository(self.pool, table_prefix=self.prefix)

    async def make_effect_repository(self):
        return PostgresV2EffectRepository(self.pool, table_prefix=self.prefix)

    async def make_reconciliation_repository(self):
        return PostgresV2ReconciliationRepository(
            self.pool,
            table_prefix=self.prefix,
        )

    async def make_approval_repository(self):
        return PostgresV2ApprovalRepository(self.pool, table_prefix=self.prefix)

    async def make_lease_repository(self):
        return PostgresV2LeaseRepository(self.pool, table_prefix=self.prefix)

    async def make_worker_repository(self):
        return PostgresV2WorkerRepository(self.pool, table_prefix=self.prefix)

    async def make_artifact_repository(self):
        return PostgresV2ArtifactRepository(self.pool, table_prefix=self.prefix)

    async def make_runtime_repository(self):
        return PostgresV2RuntimeRepository(self.pool, table_prefix=self.prefix)

    async def make_audit_store(self):
        return PostgresV2AuditStore(self.pool, table_prefix=self.prefix)

    async def make_outbox_store(self):
        return PostgresV2OutboxStore(self.pool, table_prefix=self.prefix)

    async def make_inbox_store(self):
        return PostgresV2InboxStore(self.pool, table_prefix=self.prefix)

    async def make_unit_of_work(self):
        return PostgresV2UnitOfWork(self.pool, table_prefix=self.prefix)


if __name__ == "__main__":
    unittest.main()
