from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyagentskit.adapters.persistence import (
    InMemoryMemoryRepository,
    MemoryApprovalRepository,
    MemoryArtifactRepository,
    MemoryAuditStore,
    MemoryConversationRepository,
    MemoryEffectRepository,
    MemoryInboxStore,
    MemoryLeaseRepository,
    MemoryMessageRepository,
    MemoryOutboxStore,
    MemoryReconciliationRepository,
    MemoryRunRepository,
    MemoryRuntimeRepository,
    MemorySessionRepository,
    MemoryWorkerRepository,
    SQLiteApprovalRepository,
    SQLiteArtifactRepository,
    SQLiteAuditStore,
    SQLiteConversationRepository,
    SQLiteEffectRepository,
    SQLiteInboxStore,
    SQLiteLeaseRepository,
    SQLiteMemoryRepository,
    SQLiteMessageRepository,
    SQLiteOutboxStore,
    SQLiteReconciliationRepository,
    SQLiteRunRepository,
    SQLiteRuntimeRepository,
    SQLiteSessionRepository,
    SQLiteWorkerRepository,
)
from tests.persistence_contract_suite import PersistenceContractSuiteMixin


class MemoryPersistenceCommonContracts(
    PersistenceContractSuiteMixin,
    unittest.IsolatedAsyncioTestCase,
):
    async def make_run_repository(self):
        return MemoryRunRepository()

    async def make_session_repository(self):
        return MemorySessionRepository()

    async def make_conversation_repository(self):
        return MemoryConversationRepository()

    async def make_message_repository(self):
        return MemoryMessageRepository()

    async def make_memory_repository(self):
        return InMemoryMemoryRepository()

    async def make_effect_repository(self):
        return MemoryEffectRepository()

    async def make_reconciliation_repository(self):
        return MemoryReconciliationRepository()

    async def make_approval_repository(self):
        return MemoryApprovalRepository()

    async def make_lease_repository(self):
        return MemoryLeaseRepository()

    async def make_worker_repository(self):
        return MemoryWorkerRepository()

    async def make_artifact_repository(self):
        return MemoryArtifactRepository()

    async def make_runtime_repository(self):
        return MemoryRuntimeRepository()

    async def make_audit_store(self):
        return MemoryAuditStore()

    async def make_outbox_store(self):
        return MemoryOutboxStore()

    async def make_inbox_store(self):
        return MemoryInboxStore()


class SQLitePersistenceCommonContracts(
    PersistenceContractSuiteMixin,
    unittest.IsolatedAsyncioTestCase,
):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "contracts.sqlite3"
        self._stores: list[object] = []

    async def asyncTearDown(self) -> None:
        for store in reversed(self._stores):
            close = getattr(store, "close", None)
            if close is not None:
                await close()
        self._tmp.cleanup()

    def _track(self, store):
        self._stores.append(store)
        return store

    async def make_run_repository(self):
        return self._track(SQLiteRunRepository(self.path))

    async def make_session_repository(self):
        return self._track(SQLiteSessionRepository(self.path))

    async def make_conversation_repository(self):
        return self._track(SQLiteConversationRepository(self.path))

    async def make_message_repository(self):
        return self._track(SQLiteMessageRepository(self.path))

    async def make_memory_repository(self):
        return self._track(SQLiteMemoryRepository(self.path))

    async def make_effect_repository(self):
        return self._track(SQLiteEffectRepository(self.path))

    async def make_reconciliation_repository(self):
        return self._track(SQLiteReconciliationRepository(self.path))

    async def make_approval_repository(self):
        return self._track(SQLiteApprovalRepository(self.path))

    async def make_lease_repository(self):
        return self._track(SQLiteLeaseRepository(self.path))

    async def make_worker_repository(self):
        return self._track(SQLiteWorkerRepository(self.path))

    async def make_artifact_repository(self):
        return self._track(SQLiteArtifactRepository(self.path))

    async def make_runtime_repository(self):
        return self._track(SQLiteRuntimeRepository(self.path))

    async def make_audit_store(self):
        return self._track(SQLiteAuditStore(self.path))

    async def make_outbox_store(self):
        return self._track(SQLiteOutboxStore(self.path))

    async def make_inbox_store(self):
        return self._track(SQLiteInboxStore(self.path))


if __name__ == "__main__":
    unittest.main()
