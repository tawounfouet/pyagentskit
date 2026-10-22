from __future__ import annotations

import sqlite3
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from pyagentskit.adapters.persistence import (
    SQLiteApprovalRepository,
    SQLiteAuditStore,
    SQLiteEffectRepository,
    SQLiteInboxStore,
    SQLiteLeaseRepository,
    SQLiteMemoryRepository,
    SQLiteOutboxStore,
    SQLiteReconciliationRepository,
    SQLiteRunRepository,
    SQLiteUnitOfWork,
)
from pyagentskit.adapters.persistence._codec import (
    dumps,
    effect_from_document,
    effect_to_document,
    integration_event_from_document,
    integration_event_to_document,
    loads,
    memory_from_document,
    reconciliation_case_from_document,
    reconciliation_case_to_document,
    reconciliation_evidence_from_document,
    reconciliation_evidence_to_document,
)
from pyagentskit.contracts import InboxRecord, InboxStatus, OutboxStatus
from pyagentskit.domain import (
    AggregateVersion,
    Approval,
    ApprovalStatus,
    ArtifactId,
    AuditEvent,
    ConcurrencyConflictError,
    DuplicateAggregateError,
    Effect,
    ExternalReference,
    FencingToken,
    Fingerprint,
    IdempotencyKey,
    InboxDigestConflictError,
    InputFingerprint,
    IntegrationEvent,
    Lease,
    MemoryEntry,
    MemoryScope,
    PersistenceCorruptionError,
    PersistenceError,
    ReconciliationCase,
    ReconciliationEvidence,
    ReconciliationStatus,
    Run,
    TenantId,
    WorkerId,
)


class PersistenceCodecFailurePathTests(unittest.TestCase):
    def test_json_codec_fails_closed_for_invalid_payloads(self) -> None:
        with self.assertRaises(PersistenceError):
            dumps({"bad": {1, 2, 3}})

        with self.assertRaises(PersistenceCorruptionError):
            loads("{not-json")

        with self.assertRaises(PersistenceCorruptionError):
            loads("[1,2,3]")

        with self.assertRaises(PersistenceCorruptionError):
            integration_event_from_document(
                {
                    "event_id": "event-bad",
                    "name": "bad.event",
                    "payload": "not-an-object",
                    "occurred_at": datetime.now(UTC).isoformat(),
                }
            )

        with self.assertRaises(PersistenceCorruptionError):
            memory_from_document(
                {
                    "id": "memory_bad",
                    "tenant_id": "tenant_bad",
                    "scope": MemoryScope.TENANT.value,
                    "scope_id": None,
                    "key": "bad",
                    "value": "not-an-object",
                    "version": 0,
                    "created_at": datetime.now(UTC).isoformat(),
                    "updated_at": datetime.now(UTC).isoformat(),
                }
            )

    def test_effect_codec_preserves_optional_safety_evidence(self) -> None:
        effect = Effect(
            idempotency_key=IdempotencyKey("billing", "payment-42"),
            fingerprint=InputFingerprint.from_text("amount=42"),
            external_reference=ExternalReference("stripe", "pi_42"),
            fencing_token=FencingToken(7),
            metadata=(("correlation_id", "corr-42"),),
        ).begin()
        restored = effect_from_document(effect_to_document(effect))

        self.assertEqual(restored, effect)
        self.assertEqual(restored.external_reference, ExternalReference("stripe", "pi_42"))
        self.assertEqual(restored.fencing_token, FencingToken(7))
        self.assertEqual(restored.metadata, (("correlation_id", "corr-42"),))

    def test_reconciliation_codecs_preserve_custom_resolution_and_full_evidence(self) -> None:
        effect = Effect()
        case = ReconciliationCase(
            effect_id=effect.id,
            reason="provider ambiguity",
            status=ReconciliationStatus.MANUAL_REVIEW,
            resolution="operator_pending",
            resolution_detail="waiting for finance",
            metadata=(("ticket", "INC-42"),),
        )
        restored_case = reconciliation_case_from_document(reconciliation_case_to_document(case))
        self.assertEqual(restored_case, case)
        self.assertEqual(restored_case.resolution, "operator_pending")

        now = datetime.now(UTC)
        evidence = ReconciliationEvidence(
            case_id=case.id,
            summary="provider evidence",
            provider_timestamp=now,
            external_reference=ExternalReference("provider", "remote-42"),
            payload_digest=Fingerprint.from_text("provider-payload"),
            raw_artifact_id=ArtifactId("artifact_42"),
        )
        restored_evidence = reconciliation_evidence_from_document(
            reconciliation_evidence_to_document(evidence)
        )
        self.assertEqual(restored_evidence, evidence)

    def test_integration_event_codec_preserves_tenant_and_aggregate_identity(self) -> None:
        event = IntegrationEvent(
            name="effect.changed",
            payload={"status": "unknown"},
            tenant_id=TenantId("tenant_42"),
            aggregate_type="Effect",
            aggregate_id="effect_42",
        )
        restored = integration_event_from_document(integration_event_to_document(event))
        self.assertEqual(restored, event)


class SQLitePersistenceFailurePathTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "pyagentskit-v2.sqlite3"

    async def asyncTearDown(self) -> None:
        self._tmp.cleanup()

    async def test_newer_schema_is_rejected(self) -> None:
        connection = sqlite3.connect(self.path)
        try:
            connection.execute(
                "CREATE TABLE v2_schema_migrations "
                "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
            )
            connection.execute(
                "INSERT INTO v2_schema_migrations(component, version) VALUES (?, ?)",
                ("persistence_v2", 99),
            )
            connection.commit()
        finally:
            connection.close()

        with self.assertRaises(PersistenceError):
            SQLiteRunRepository(self.path)

    async def test_missing_and_duplicate_effect_paths_fail_closed(self) -> None:
        repository = SQLiteEffectRepository(self.path)
        effect = Effect(
            idempotency_key=IdempotencyKey("run", "same-id"),
            fingerprint=InputFingerprint.from_text("payload"),
        )

        with self.assertRaises(KeyError):
            await repository.get(effect.id)

        self.assertIsNone(
            await repository.find_by_idempotency_key(
                effect.idempotency_scope,
                effect.idempotency_key,
            )
        )

        first = await repository.reserve(effect)
        second = await repository.reserve(effect)
        self.assertTrue(first.created)
        self.assertFalse(second.created)

        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(effect, expected_version=effect.version)

        await repository.close()

    async def test_memory_duplicate_missing_and_tenant_scope_paths(self) -> None:
        repository = SQLiteMemoryRepository(self.path)
        entry = MemoryEntry(
            scope=MemoryScope.TENANT,
            key="policy",
            value={"enabled": True},
        )
        await repository.put(entry)

        with self.assertRaises(DuplicateAggregateError):
            await repository.put(entry)

        listed = await repository.list_by_scope(
            tenant_id=str(entry.tenant_id),
            scope=entry.scope.value,
            scope_id=None,
        )
        self.assertEqual(listed, (entry,))

        revised = entry.revise({"enabled": False})
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(revised, expected_version=entry.version.next())

        missing = MemoryEntry(
            scope=MemoryScope.CUSTOM,
            scope_id="missing",
            key="missing",
            value={"v": 1},
        ).revise({"v": 2})
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(
                missing,
                expected_version=AggregateVersion(),
            )

        await repository.close()

    async def test_reconciliation_approval_and_audit_duplicates(self) -> None:
        effect = Effect()
        reconciliations = SQLiteReconciliationRepository(self.path)
        case = ReconciliationCase(effect_id=effect.id, reason="ambiguous")
        await reconciliations.save(case, expected_version=None)

        with self.assertRaises(DuplicateAggregateError):
            await reconciliations.save(case, expected_version=None)

        running = case.start()
        with self.assertRaises(ConcurrencyConflictError):
            await reconciliations.save(
                running,
                expected_version=case.version.next(),
            )

        evidence = ReconciliationEvidence(case_id=case.id, summary="evidence")
        await reconciliations.append_evidence(evidence)
        with self.assertRaises(DuplicateAggregateError):
            await reconciliations.append_evidence(evidence)
        await reconciliations.close()

        approvals = SQLiteApprovalRepository(self.path)
        approval = Approval(subject=str(effect.id))
        await approvals.add(approval)
        self.assertEqual(await approvals.list_pending(), (approval,))

        with self.assertRaises(DuplicateAggregateError):
            await approvals.add(approval)

        approved = approval.transition(ApprovalStatus.APPROVED)
        with self.assertRaises(ConcurrencyConflictError):
            await approvals.save(
                approved,
                expected_version=approval.version.next(),
            )
        await approvals.close()

        audit = SQLiteAuditStore(self.path)
        event = AuditEvent(event_type="effect.checked", subject=str(effect.id))
        await audit.append(event)
        with self.assertRaises(DuplicateAggregateError):
            await audit.append(event)
        self.assertEqual(await audit.list_for_subject("missing"), ())
        await audit.close()

    async def test_lease_duplicate_and_stale_save_paths(self) -> None:
        repository = SQLiteLeaseRepository(self.path)
        token = await repository.next_fencing_token("run:42")
        held = Lease(resource="run:42").acquire(WorkerId("worker-a"), token)
        await repository.add(held)

        with self.assertRaises(DuplicateAggregateError):
            await repository.add(held)

        released = held.release()
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(
                released,
                expected_version=held.version.next(),
            )

        missing = Lease(resource="run:missing").acquire(
            WorkerId("worker-x"),
            FencingToken(1),
        )
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(
                missing.release(),
                expected_version=missing.version,
            )

        await repository.close()

    async def test_outbox_stale_claim_duplicate_and_missing_paths(self) -> None:
        outbox = SQLiteOutboxStore(self.path)
        event = IntegrationEvent(name="run.changed")
        await outbox.append(event)

        with self.assertRaises(DuplicateAggregateError):
            await outbox.append(event)
        with self.assertRaises(ValueError):
            await outbox.claim_batch(worker_id="publisher", limit=0)
        with self.assertRaises(ValueError):
            await outbox.claim_batch(
                worker_id="publisher",
                claim_timeout_seconds=-1,
            )

        first = await outbox.claim_batch(worker_id="publisher-a")
        self.assertEqual(first[0].status, OutboxStatus.CLAIMED)

        reclaimed = await outbox.claim_batch(
            worker_id="publisher-b",
            claim_timeout_seconds=0,
        )
        self.assertEqual(reclaimed[0].attempt_count, 2)
        self.assertEqual(reclaimed[0].claimed_by, "publisher-b")

        for operation in (
            lambda: outbox.mark_published("missing"),
            lambda: outbox.mark_failed("missing", error="x"),
            lambda: outbox.release_claim("missing"),
        ):
            with self.assertRaises(KeyError):
                await operation()

        await outbox.close()

    async def test_inbox_failure_and_missing_paths(self) -> None:
        inbox = SQLiteInboxStore(self.path)
        record = InboxRecord(
            source="consumer",
            external_event_id="event-42",
            digest="a" * 64,
        )
        self.assertIsNone(await inbox.get("consumer", "missing"))
        self.assertTrue(await inbox.reserve(record))
        self.assertFalse(await inbox.reserve(record))

        with self.assertRaises(InboxDigestConflictError):
            await inbox.reserve(
                InboxRecord(
                    source=record.source,
                    external_event_id=record.external_event_id,
                    digest="b" * 64,
                )
            )

        await inbox.mark_failed(
            record.source,
            record.external_event_id,
            error="handler failed",
        )
        failed = await inbox.get(record.source, record.external_event_id)
        self.assertIsNotNone(failed)
        assert failed is not None
        self.assertEqual(failed.status, InboxStatus.FAILED)

        with self.assertRaises(KeyError):
            await inbox.mark_processed("consumer", "missing")
        with self.assertRaises(KeyError):
            await inbox.mark_failed("consumer", "missing", error="x")

        await inbox.close()

    async def test_unit_of_work_misuse_and_explicit_rollback(self) -> None:
        uow = SQLiteUnitOfWork(self.path)

        with self.assertRaises(RuntimeError):
            await uow.commit()
        await uow.rollback()

        await uow.__aenter__()
        with self.assertRaises(RuntimeError):
            await uow.__aenter__()

        run = Run()
        await uow.runs.add(run)
        await uow.rollback()
        self.assertIsNone(await uow.runs.get(run.id))

        await uow.close()


if __name__ == "__main__":
    unittest.main()
