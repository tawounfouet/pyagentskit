from __future__ import annotations

import shutil
import sqlite3
import tempfile
import unittest
from importlib.resources import files
from pathlib import Path

from pyagentskit.adapters.persistence import (
    SQLiteApprovalRepository,
    SQLiteEffectRepository,
    SQLiteInboxStore,
    SQLiteLeaseRepository,
    SQLiteMemoryRepository,
    SQLiteOutboxStore,
    SQLiteReconciliationRepository,
    SQLiteRunRepository,
    SQLiteUnitOfWork,
)
from pyagentskit.contracts import InboxRecord, InboxStatus, OutboxStatus
from pyagentskit.domain import (
    Approval,
    ApprovalStatus,
    AuditEvent,
    ConcurrencyConflictError,
    DuplicateAggregateError,
    Effect,
    FencingToken,
    IdempotencyConflictError,
    IdempotencyKey,
    InboxDigestConflictError,
    InputFingerprint,
    IntegrationEvent,
    Lease,
    MemoryEntry,
    MemoryScope,
    ReconciliationCase,
    ReconciliationEvidence,
    Run,
    RunStatus,
    WorkerId,
)


class SQLitePersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "pyagentskit-v2.sqlite3"

    async def asyncTearDown(self) -> None:
        self._tmp.cleanup()

    async def test_schema_migration_is_versioned_and_contains_safety_constraints(self) -> None:
        repository = SQLiteRunRepository(self.path)
        await repository.close()

        connection = sqlite3.connect(self.path)
        try:
            version = connection.execute(
                "SELECT version FROM v2_schema_migrations WHERE component='persistence_v2'"
            ).fetchone()
            self.assertEqual(version, (2,))
            indexes = {
                row[0]
                for row in connection.execute("SELECT name FROM sqlite_master WHERE type='index'")
            }
            self.assertIn("ux_v2_effect_idempotency", indexes)
            self.assertIn("ux_v2_active_lease_resource", indexes)
        finally:
            connection.close()

    async def test_schema_migrates_incrementally_from_v1_to_v2(self) -> None:
        migration_v1 = (
            files("pyagentskit.adapters.persistence.migrations.sqlite")
            .joinpath("0001_v2_core.sql")
            .read_text(encoding="utf-8")
        )
        connection = sqlite3.connect(self.path)
        try:
            connection.executescript(migration_v1)
            before = connection.execute(
                "SELECT version FROM v2_schema_migrations "
                "WHERE component='persistence_v2'"
            ).fetchone()
            self.assertEqual(before, (1,))
        finally:
            connection.close()

        repository = SQLiteRunRepository(self.path)
        await repository.close()

        connection = sqlite3.connect(self.path)
        try:
            after = connection.execute(
                "SELECT version FROM v2_schema_migrations "
                "WHERE component='persistence_v2'"
            ).fetchone()
            self.assertEqual(after, (2,))
            tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
            }
            self.assertIn("v2_sessions", tables)
            self.assertIn("v2_runtime_invocations", tables)
        finally:
            connection.close()

    async def test_run_roundtrip_restart_and_cas(self) -> None:
        repository = SQLiteRunRepository(self.path)
        run = Run()
        await repository.add(run)
        running = run.transition(RunStatus.RUNNING)
        await repository.save(running, expected_version=run.version)
        await repository.close()

        reopened = SQLiteRunRepository(self.path)
        self.assertEqual(await reopened.get(run.id), running)
        self.assertEqual(
            await reopened.list_by_state(RunStatus.RUNNING),
            (running,),
        )
        with self.assertRaises(ConcurrencyConflictError):
            await reopened.save(
                run.transition(RunStatus.RUNNING),
                expected_version=run.version,
            )
        with self.assertRaises(DuplicateAggregateError):
            await reopened.add(running)
        await reopened.close()

    async def test_effect_idempotency_survives_restart(self) -> None:
        key = IdempotencyKey("run", "payment-42")
        fingerprint = InputFingerprint.from_text("amount=42")
        effect = Effect(idempotency_key=key, fingerprint=fingerprint)

        repository = SQLiteEffectRepository(self.path)
        first = await repository.reserve(effect)
        self.assertTrue(first.created)
        await repository.close()

        reopened = SQLiteEffectRepository(self.path)
        duplicate = await reopened.reserve(Effect(idempotency_key=key, fingerprint=fingerprint))
        self.assertFalse(duplicate.created)
        self.assertEqual(duplicate.effect.id, effect.id)

        with self.assertRaises(IdempotencyConflictError):
            await reopened.reserve(
                Effect(
                    idempotency_key=key,
                    fingerprint=InputFingerprint.from_text("amount=43"),
                )
            )

        started = effect.begin()
        await reopened.save(started, expected_version=effect.version)
        self.assertEqual(await reopened.get(effect.id), started)
        await reopened.close()

    async def test_memory_roundtrip_and_scope_query(self) -> None:
        repository = SQLiteMemoryRepository(self.path)
        entry = MemoryEntry(
            scope=MemoryScope.SESSION,
            scope_id="session-42",
            key="profile",
            value={"tier": "gold"},
        )
        await repository.put(entry)
        revised = entry.revise({"tier": "platinum"})
        await repository.save(revised, expected_version=entry.version)

        listed = await repository.list_by_scope(
            tenant_id=str(entry.tenant_id),
            scope=MemoryScope.SESSION.value,
            scope_id="session-42",
        )
        self.assertEqual(listed, (revised,))
        await repository.close()

    async def test_reconciliation_and_approval_cas(self) -> None:
        reconciliations = SQLiteReconciliationRepository(self.path)
        effect = Effect()
        case = ReconciliationCase(effect_id=effect.id, reason="timeout")
        await reconciliations.save(case, expected_version=None)
        running = case.start()
        await reconciliations.save(running, expected_version=case.version)
        evidence = ReconciliationEvidence(
            case_id=case.id,
            summary="provider confirms lookup",
        )
        await reconciliations.append_evidence(evidence)
        self.assertEqual(await reconciliations.get_active(effect.id), running)

        with self.assertRaises(DuplicateAggregateError):
            await reconciliations.append_evidence(evidence)
        await reconciliations.close()

        approvals = SQLiteApprovalRepository(self.path)
        approval = Approval(subject=str(effect.id))
        await approvals.add(approval)
        approved = approval.transition(ApprovalStatus.APPROVED)
        await approvals.save(approved, expected_version=approval.version)
        self.assertEqual(await approvals.get(approval.id), approved)
        self.assertEqual(await approvals.list_pending(), ())
        await approvals.close()

    async def test_fencing_is_monotonic_across_reopen_and_active_owner_is_unique(self) -> None:
        repository = SQLiteLeaseRepository(self.path)
        token_1 = await repository.next_fencing_token("run:42")
        lease_a = Lease(resource="run:42").acquire(WorkerId("worker-a"), token_1)
        await repository.add(lease_a)
        await repository.close()

        reopened = SQLiteLeaseRepository(self.path)
        token_2 = await reopened.next_fencing_token("run:42")
        self.assertEqual(token_1, FencingToken(1))
        self.assertEqual(token_2, FencingToken(2))

        lease_b = Lease(resource="run:42").acquire(WorkerId("worker-b"), token_2)
        with self.assertRaises(ConcurrencyConflictError):
            await reopened.add(lease_b)

        released = lease_a.release()
        await reopened.save(released, expected_version=lease_a.version)
        await reopened.add(lease_b)
        self.assertEqual(await reopened.get_current("run:42"), lease_b)
        await reopened.close()

    async def test_outbox_and_inbox_survive_restart(self) -> None:
        outbox = SQLiteOutboxStore(self.path)
        event = IntegrationEvent(
            name="run.changed",
            aggregate_type="Run",
            aggregate_id="run-42",
        )
        await outbox.append(event)
        first = await outbox.claim_batch(worker_id="publisher-a")
        self.assertEqual(first[0].status, OutboxStatus.CLAIMED)
        await outbox.release_claim(event.event_id)
        await outbox.close()

        reopened = SQLiteOutboxStore(self.path)
        second = await reopened.claim_batch(worker_id="publisher-b")
        self.assertEqual(second[0].attempt_count, 2)
        await reopened.mark_published(event.event_id)
        self.assertEqual(await reopened.claim_batch(worker_id="publisher-c"), ())
        await reopened.close()

        inbox = SQLiteInboxStore(self.path)
        record = InboxRecord(
            source="github",
            external_event_id="delivery-42",
            digest="a" * 64,
        )
        self.assertTrue(await inbox.reserve(record))
        self.assertFalse(await inbox.reserve(record))
        await inbox.mark_processed(record.source, record.external_event_id)
        await inbox.close()

        inbox_reopened = SQLiteInboxStore(self.path)
        stored = await inbox_reopened.get(record.source, record.external_event_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.status, InboxStatus.PROCESSED)
        with self.assertRaises(InboxDigestConflictError):
            await inbox_reopened.reserve(
                InboxRecord(
                    source=record.source,
                    external_event_id=record.external_event_id,
                    digest="b" * 64,
                )
            )
        await inbox_reopened.close()

    async def test_outbox_claim_is_reclaimed_after_publisher_crash(self) -> None:
        outbox = SQLiteOutboxStore(self.path)
        event = IntegrationEvent(name="effect.changed")
        await outbox.append(event)

        first = await outbox.claim_batch(worker_id="publisher-a")
        self.assertEqual(first[0].attempt_count, 1)
        await outbox.close()

        reopened = SQLiteOutboxStore(self.path)
        second = await reopened.claim_batch(
            worker_id="publisher-b",
            claim_timeout_seconds=0,
        )
        self.assertEqual(second[0].attempt_count, 2)
        self.assertEqual(second[0].claimed_by, "publisher-b")
        await reopened.close()

    async def test_restored_started_effect_requires_reconciliation_before_reentry(self) -> None:
        repository = SQLiteEffectRepository(self.path)
        effect = Effect()
        await repository.reserve(effect)
        started = effect.begin()
        await repository.save(started, expected_version=effect.version)
        await repository.close()

        restored_snapshot = Path(self._tmp.name) / "restored.sqlite3"
        shutil.copy2(self.path, restored_snapshot)

        live = SQLiteEffectRepository(self.path)
        succeeded = started.mark_succeeded()
        await live.save(succeeded, expected_version=started.version)
        await live.close()

        shutil.copy2(restored_snapshot, self.path)
        restored = SQLiteEffectRepository(self.path)
        recovered_effect = await restored.get(effect.id)
        self.assertEqual(recovered_effect.status.value, "started")
        self.assertTrue(recovered_effect.requires_reconciliation)
        self.assertFalse(recovered_effect.safe_to_replay)
        await restored.close()

    async def test_unit_of_work_rolls_back_domain_and_outbox_together(self) -> None:
        run = Run()
        event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(run.id),
        )
        uow = SQLiteUnitOfWork(self.path)
        async with uow:
            await uow.runs.add(run)
            await uow.outbox.append(event)

        self.assertIsNone(await uow.runs.get(run.id))
        self.assertEqual(await uow.outbox.claim_batch(worker_id="publisher"), ())
        await uow.close()

    async def test_unit_of_work_commits_domain_audit_and_outbox_together(self) -> None:
        run = Run()
        event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(run.id),
        )
        uow = SQLiteUnitOfWork(self.path)
        async with uow:
            await uow.runs.add(run)
            await uow.audit.append(
                AuditEvent(
                    event_type="run.created",
                    subject=str(run.id),
                )
            )
            await uow.outbox.append(event)
            await uow.commit()

        self.assertEqual(await uow.runs.get(run.id), run)
        self.assertEqual(len(await uow.audit.list_for_subject(str(run.id))), 1)
        self.assertEqual(
            (await uow.outbox.claim_batch(worker_id="publisher"))[0].event.event_id,
            event.event_id,
        )
        await uow.close()


if __name__ == "__main__":
    unittest.main()
