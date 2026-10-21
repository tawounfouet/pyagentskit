"""Real multi-process lease crash and suspension qualification."""

from __future__ import annotations

import asyncio
import multiprocessing
import os
import signal
import tempfile
import unittest
from pathlib import Path
from typing import Any

from pyagentskit.coordination import LeaseConflictError, SQLiteLeaseStore


def _hold_lease(path: str, connection: Any, ttl_seconds: float) -> None:
    async def acquire() -> None:
        store = SQLiteLeaseStore(path)
        lease = await store.acquire(
            "durable-run:process-qualification",
            owner_id=f"worker-{os.getpid()}",
            tenant_id="tenant-a",
            ttl_seconds=ttl_seconds,
        )
        connection.send((lease.fencing_token, lease.owner_id))
        while True:
            await asyncio.sleep(60)

    asyncio.run(acquire())


class DistributedMultiprocessQualification(unittest.IsolatedAsyncioTestCase):
    async def _start_holder(
        self, path: Path, ttl_seconds: float
    ) -> tuple[multiprocessing.Process, int, str]:
        process_context = multiprocessing.get_context("spawn")
        parent, child = process_context.Pipe(duplex=False)
        process = process_context.Process(
            target=_hold_lease,
            args=(str(path), child, ttl_seconds),
            name="pyagentskit-crash-fixture",
        )
        process.start()
        child.close()
        token, owner_id = await asyncio.wait_for(asyncio.to_thread(parent.recv), timeout=10)
        parent.close()
        return process, int(token), str(owner_id)

    async def _assert_takeover_after_process_death(self, *, hard_kill: bool) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "coordination.sqlite"
            process, first_token, owner_id = await self._start_holder(path, 0.25)
            contender = SQLiteLeaseStore(path)
            try:
                with self.assertRaises(LeaseConflictError):
                    await contender.acquire(
                        "durable-run:process-qualification",
                        owner_id="worker-contender",
                        tenant_id="tenant-a",
                        ttl_seconds=1,
                    )
                if hard_kill:
                    process.kill()
                else:
                    process.terminate()
                await asyncio.to_thread(process.join, 5)
                self.assertFalse(process.is_alive())
                await asyncio.sleep(0.35)
                replacement = await contender.acquire(
                    "durable-run:process-qualification",
                    owner_id="worker-takeover",
                    tenant_id="tenant-a",
                    ttl_seconds=1,
                )
                self.assertEqual(first_token, 1)
                self.assertNotEqual(owner_id, replacement.owner_id)
                self.assertEqual(replacement.fencing_token, 2)
            finally:
                if process.is_alive():
                    process.kill()
                    await asyncio.to_thread(process.join, 5)
                await contender.aclose()

    async def test_sigterm_crash_releases_os_locks_but_not_the_lease(self) -> None:
        await self._assert_takeover_after_process_death(hard_kill=False)

    async def test_sigkill_crash_allows_takeover_only_after_expiry(self) -> None:
        await self._assert_takeover_after_process_death(hard_kill=True)

    @unittest.skipUnless(hasattr(signal, "SIGSTOP"), "SIGSTOP is unavailable")
    async def test_suspended_worker_becomes_fenced_after_expiry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "coordination.sqlite"
            process, first_token, _ = await self._start_holder(path, 0.25)
            contender = SQLiteLeaseStore(path)
            try:
                os.kill(process.pid, signal.SIGSTOP)
                await asyncio.sleep(0.35)
                replacement = await contender.acquire(
                    "durable-run:process-qualification",
                    owner_id="worker-after-pause",
                    tenant_id="tenant-a",
                    ttl_seconds=1,
                )
                self.assertEqual(first_token, 1)
                self.assertEqual(replacement.fencing_token, 2)
            finally:
                if process.is_alive():
                    os.kill(process.pid, signal.SIGCONT)
                    process.kill()
                    await asyncio.to_thread(process.join, 5)
                await contender.aclose()


if __name__ == "__main__":
    unittest.main()
