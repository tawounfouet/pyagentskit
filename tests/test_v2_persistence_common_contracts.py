from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from pyagentskit.adapters.persistence import (
    MemoryEffectRepository,
    MemoryInboxStore,
    MemoryOutboxStore,
    MemoryRunRepository,
    MemoryRuntimeRepository,
    SQLiteEffectRepository,
    SQLiteInboxStore,
    SQLiteOutboxStore,
    SQLiteRunRepository,
    SQLiteRuntimeRepository,
)
from tests.persistence_contract_suite import PersistenceContractSuiteMixin


class MemoryPersistenceCommonContracts(
    PersistenceContractSuiteMixin,
    unittest.IsolatedAsyncioTestCase,
):
    async def make_run_repository(self):
        return MemoryRunRepository()

    async def make_effect_repository(self):
        return MemoryEffectRepository()

    async def make_runtime_repository(self):
        return MemoryRuntimeRepository()

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

    async def make_effect_repository(self):
        return self._track(SQLiteEffectRepository(self.path))

    async def make_runtime_repository(self):
        return self._track(SQLiteRuntimeRepository(self.path))

    async def make_outbox_store(self):
        return self._track(SQLiteOutboxStore(self.path))

    async def make_inbox_store(self):
        return self._track(SQLiteInboxStore(self.path))


if __name__ == "__main__":
    unittest.main()
