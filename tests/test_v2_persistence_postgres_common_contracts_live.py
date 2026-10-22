"""Run the reusable P0 persistence contracts against a real PostgreSQL service."""

from __future__ import annotations

import os
import unittest
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
