from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from pyagentskit import (
    ApprovalConflictError,
    ApprovalDecision,
    ApprovalNotFoundError,
    ApprovalRequest,
    ApprovalStatus,
    ApprovalStore,
    MemoryApprovalStore,
    SQLiteApprovalStore,
    ToolCall,
)


def request(*, tenant_id: str | None = "tenant-a", now=None):  # type: ignore[no-untyped-def]
    moment = now or datetime.now(UTC)
    return ApprovalRequest.for_tool_call(
        ToolCall(id="call-1", name="write", arguments={"value": 2}),
        run_id=uuid4(),
        trace_id=uuid4(),
        agent_id="agent",
        session_id="session",
        tenant_id=tenant_id,
        clock=lambda: moment,
    )


class ApprovalStoreContract:
    store: ApprovalStore

    async def test_lifecycle_is_revisioned_and_single_claim(self) -> None:
        item = request()
        self.assertEqual(await self.store.create(item), item)
        self.assertEqual(await self.store.create(item), item)
        approved = await self.store.resolve(
            item.approval_id,
            ApprovalDecision.APPROVE,
            actor_id="reviewer",
            reason="verified",
            tenant_id="tenant-a",
            expected_revision=0,
        )
        self.assertEqual(approved.status, ApprovalStatus.APPROVED)
        self.assertEqual(approved.revision, 1)
        claimed = await self.store.claim(
            item.approval_id, tenant_id="tenant-a", expected_revision=1
        )
        self.assertEqual(claimed.status, ApprovalStatus.CLAIMED)
        with self.assertRaises(ApprovalConflictError):
            await self.store.claim(item.approval_id, tenant_id="tenant-a")
        completed = await self.store.complete(
            item.approval_id, tenant_id="tenant-a", expected_revision=2
        )
        self.assertEqual(completed.status, ApprovalStatus.EXECUTED)

    async def test_tenant_isolation_pending_and_conflicts(self) -> None:
        item = request()
        await self.store.create(item)
        with self.assertRaises(ApprovalNotFoundError):
            await self.store.get(item.approval_id, tenant_id="tenant-b")
        self.assertEqual(await self.store.list_pending(tenant_id="tenant-a"), (item,))
        with self.assertRaises(ApprovalConflictError):
            await self.store.resolve(
                item.approval_id,
                ApprovalDecision.REJECT,
                actor_id="reviewer",
                tenant_id="tenant-a",
                expected_revision=2,
            )


class MemoryApprovalStoreTests(ApprovalStoreContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.store = MemoryApprovalStore()

    async def test_expiry_fails_closed(self) -> None:
        now = datetime.now(UTC)
        store = MemoryApprovalStore(clock=lambda: now + timedelta(hours=2))
        item = request(now=now)
        await store.create(item)
        self.assertEqual(
            (await store.get(item.approval_id, tenant_id="tenant-a")).status,
            ApprovalStatus.EXPIRED,
        )
        self.assertEqual(await store.list_pending(tenant_id="tenant-a"), ())

    async def test_conflicting_create_and_idempotent_resolution(self) -> None:
        item = request()
        await self.store.create(item)
        changed = item.model_copy(update={"metadata": {"different": True}})
        with self.assertRaises(ApprovalConflictError):
            await self.store.create(changed)
        first = await self.store.resolve(
            item.approval_id,
            ApprovalDecision.REJECT,
            actor_id="reviewer",
            tenant_id="tenant-a",
        )
        repeated = await self.store.resolve(
            item.approval_id,
            ApprovalDecision.REJECT,
            actor_id="reviewer",
            tenant_id="tenant-a",
        )
        self.assertEqual(first, repeated)
        claimed = await self.store.claim(
            item.approval_id,
            tenant_id="tenant-a",
            expected_revision=first.revision,
        )
        self.assertEqual(claimed.status, ApprovalStatus.CLAIMED)

    async def test_session_filter_and_missing_transition(self) -> None:
        item = request()
        await self.store.create(item)
        self.assertEqual(
            await self.store.list_pending(tenant_id="tenant-a", session_id="other"), ()
        )
        with self.assertRaises(ApprovalNotFoundError):
            await self.store.claim("missing", tenant_id="tenant-a")


class SQLiteApprovalStoreTests(ApprovalStoreContract, unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.store = SQLiteApprovalStore(Path(self.temporary.name) / "state.sqlite3")

    async def asyncTearDown(self) -> None:
        await self.store.aclose()  # type: ignore[attr-defined]
        self.temporary.cleanup()

    async def test_two_store_instances_cannot_claim_the_same_decision(self) -> None:
        item = request()
        await self.store.create(item)
        approved = await self.store.resolve(
            item.approval_id,
            ApprovalDecision.APPROVE,
            actor_id="reviewer",
            tenant_id="tenant-a",
        )
        second = SQLiteApprovalStore(self.store.path)  # type: ignore[attr-defined]
        try:
            outcomes = await asyncio.gather(
                self.store.claim(
                    item.approval_id,
                    tenant_id="tenant-a",
                    expected_revision=approved.revision,
                ),
                second.claim(
                    item.approval_id,
                    tenant_id="tenant-a",
                    expected_revision=approved.revision,
                ),
                return_exceptions=True,
            )
            self.assertEqual(sum(isinstance(item, ApprovalRequest) for item in outcomes), 1)
            self.assertEqual(sum(isinstance(item, ApprovalConflictError) for item in outcomes), 1)
        finally:
            await second.aclose()


if __name__ == "__main__":
    unittest.main()
