from __future__ import annotations

import unittest
from dataclasses import replace

from pyagentskit.adapters.persistence import (
    InMemoryMemoryRepository,
    MemoryApprovalRepository,
    MemoryArtifactRepository,
    MemoryAuditStore,
    MemoryBlobStore,
    MemoryConversationRepository,
    MemoryEffectRepository,
    MemoryInboxStore,
    MemoryLeaseRepository,
    MemoryMessageRepository,
    MemoryOutboxStore,
    MemoryRunRepository,
    MemoryRuntimeRepository,
    MemorySessionRepository,
    MemoryUnitOfWork,
    MemoryWorkerRepository,
)
from pyagentskit.contracts import (
    InboxRecord,
    InboxStatus,
    OutboxStatus,
    RunRepository,
)
from pyagentskit.domain import (
    Approval,
    ApprovalStatus,
    Artifact,
    AuditEvent,
    ConcurrencyConflictError,
    Conversation,
    ConversationMessage,
    DomainEvent,
    DuplicateAggregateError,
    Effect,
    FencingToken,
    IdempotencyConflictError,
    IdempotencyKey,
    InboxDigestConflictError,
    InputFingerprint,
    IntegrationEvent,
    Lease,
    ReconciliationCase,
    ReconciliationEvidence,
    MemoryEntry,
    MemoryScope,
    Run,
    RunStatus,
    RuntimeBinding,
    RuntimeInvocation,
    Session,
    Worker,
    WorkerId,
)


class RunRepositoryContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_run_repository_is_a_run_repository(self) -> None:
        repository = MemoryRunRepository()
        self.assertIsInstance(repository, RunRepository)

    async def test_compare_and_swap_rejects_stale_writer(self) -> None:
        repository = MemoryRunRepository()
        original = Run()
        await repository.add(original)

        writer_a = original.transition(RunStatus.RUNNING)
        writer_b = original.transition(RunStatus.RUNNING)

        await repository.save(writer_a, expected_version=original.version)

        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(writer_b, expected_version=original.version)

        stored = await repository.get(original.id)
        self.assertEqual(stored, writer_a)

    async def test_list_by_state_is_domain_oriented(self) -> None:
        repository = MemoryRunRepository()
        created = Run()
        running = Run().transition(RunStatus.RUNNING)
        await repository.add(created)
        await repository.add(running)

        self.assertEqual(await repository.list_by_state(RunStatus.RUNNING), (running,))


class EffectRepositoryContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_same_idempotency_identity_returns_existing_effect(self) -> None:
        repository = MemoryEffectRepository()
        key = IdempotencyKey("run", "effect-42")
        fingerprint = InputFingerprint.from_text("payload=42")
        first = Effect(idempotency_key=key, fingerprint=fingerprint)
        duplicate = Effect(idempotency_key=key, fingerprint=fingerprint)

        reserved = await repository.reserve(first)
        repeated = await repository.reserve(duplicate)

        self.assertTrue(reserved.created)
        self.assertFalse(repeated.created)
        self.assertEqual(repeated.effect.id, first.id)

    async def test_same_key_different_fingerprint_is_hard_conflict(self) -> None:
        repository = MemoryEffectRepository()
        key = IdempotencyKey("run", "effect-42")
        await repository.reserve(
            Effect(
                idempotency_key=key,
                fingerprint=InputFingerprint.from_text("payload=42"),
            )
        )

        with self.assertRaises(IdempotencyConflictError):
            await repository.reserve(
                Effect(
                    idempotency_key=key,
                    fingerprint=InputFingerprint.from_text("payload=43"),
                )
            )

    async def test_effect_save_uses_cas(self) -> None:
        repository = MemoryEffectRepository()
        effect = Effect()
        await repository.reserve(effect)
        started = effect.begin()
        await repository.save(started, expected_version=effect.version)

        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(
                effect.begin(),
                expected_version=effect.version,
            )


class MemoryRepositoryContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_entry_is_versioned_and_scoped(self) -> None:
        repository = InMemoryMemoryRepository()
        entry = MemoryEntry(
            scope=MemoryScope.SESSION,
            scope_id="session-42",
            key="customer",
            value={"tier": "gold"},
        )
        await repository.put(entry)

        updated = entry.revise({"tier": "platinum"})
        await repository.save(updated, expected_version=entry.version)

        listed = await repository.list_by_scope(
            tenant_id=str(entry.tenant_id),
            scope=MemoryScope.SESSION.value,
            scope_id="session-42",
        )
        self.assertEqual(listed, (updated,))

    async def test_memory_entry_rejects_stale_update(self) -> None:
        repository = InMemoryMemoryRepository()
        entry = MemoryEntry(
            scope=MemoryScope.CUSTOM,
            scope_id="accounting",
            key="policy",
            value={"version": 1},
        )
        await repository.put(entry)
        writer_a = entry.revise({"version": 2})
        writer_b = entry.revise({"version": 3})
        await repository.save(writer_a, expected_version=entry.version)

        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(writer_b, expected_version=entry.version)


class LeaseRepositoryContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_one_active_owner_and_monotonic_fencing(self) -> None:
        repository = MemoryLeaseRepository()
        resource = "run:42"
        worker_a = WorkerId("worker-a")
        worker_b = WorkerId("worker-b")

        token_1 = await repository.next_fencing_token(resource)
        self.assertEqual(token_1, FencingToken(1))
        lease_a = Lease(resource=resource).acquire(worker_a, token_1)
        await repository.add(lease_a)

        token_2 = await repository.next_fencing_token(resource)
        self.assertEqual(token_2, FencingToken(2))
        lease_b = Lease(resource=resource).acquire(worker_b, token_2)

        with self.assertRaises(ConcurrencyConflictError):
            await repository.add(lease_b)

        released = lease_a.release()
        await repository.save(released, expected_version=lease_a.version)
        await repository.add(lease_b)

        current = await repository.get_current(resource)
        self.assertEqual(current, lease_b)
        self.assertGreater(lease_b.fencing_token, lease_a.fencing_token)


class OutboxInboxContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_outbox_redelivery_after_crash_is_explicit(self) -> None:
        outbox = MemoryOutboxStore()
        event = IntegrationEvent(
            name="run.changed",
            aggregate_type="Run",
            aggregate_id="run-42",
            payload={"status": "waiting"},
        )
        await outbox.append(event)

        first_claim = await outbox.claim_batch(worker_id="worker-a")
        self.assertEqual(first_claim[0].status, OutboxStatus.CLAIMED)
        self.assertEqual(first_claim[0].attempt_count, 1)

        # Publisher may have sent the event and crashed before mark_published.
        await outbox.release_claim(event.event_id)
        second_claim = await outbox.claim_batch(worker_id="worker-b")
        self.assertEqual(second_claim[0].attempt_count, 2)

        await outbox.mark_published(event.event_id)
        self.assertEqual(await outbox.claim_batch(worker_id="worker-c"), ())

    async def test_inbox_same_digest_is_noop_but_digest_drift_is_conflict(self) -> None:
        inbox = MemoryInboxStore()
        record = InboxRecord(
            source="github",
            external_event_id="evt-42",
            digest="a" * 64,
        )

        self.assertTrue(await inbox.reserve(record))
        self.assertFalse(await inbox.reserve(record))

        with self.assertRaises(InboxDigestConflictError):
            await inbox.reserve(replace(record, digest="b" * 64))

        await inbox.mark_processed(record.source, record.external_event_id)
        stored = await inbox.get(record.source, record.external_event_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.status, InboxStatus.PROCESSED)


class UnitOfWorkContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_uncommitted_domain_state_and_outbox_roll_back_together(self) -> None:
        uow = MemoryUnitOfWork()
        run = Run()
        event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(run.id),
        )

        async with uow:
            await uow.runs.add(run)
            await uow.outbox.append(event)

        self.assertIsNone(await uow.runs.get(run.id))
        self.assertEqual(await uow.outbox.claim_batch(worker_id="worker"), ())

    async def test_commit_keeps_domain_state_and_outbox_together(self) -> None:
        uow = MemoryUnitOfWork()
        run = Run()
        event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(run.id),
        )

        async with uow:
            await uow.runs.add(run)
            await uow.outbox.append(event)
            await uow.commit()

        self.assertEqual(await uow.runs.get(run.id), run)
        claimed = await uow.outbox.claim_batch(worker_id="publisher")
        self.assertEqual(claimed[0].event.event_id, event.event_id)


class OtherRepositoryContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_session_conversation_and_message_roundtrip(self) -> None:
        sessions = MemorySessionRepository()
        conversations = MemoryConversationRepository()
        messages = MemoryMessageRepository()
        session = Session()
        conversation = Conversation(session_id=session.id)
        message = ConversationMessage(actor="agent", content="hello")

        await sessions.add(session)
        await conversations.add(conversation)
        await messages.append(conversation.id, message)

        self.assertEqual(await sessions.get(session.id), session)
        self.assertEqual(
            await conversations.list_for_session(session.id),
            (conversation,),
        )
        self.assertEqual(
            await messages.list_for_conversation(conversation.id),
            (message,),
        )

    async def test_approval_cas_preserves_terminality(self) -> None:
        approvals = MemoryApprovalRepository()
        approval = Approval(subject="effect-42")
        await approvals.add(approval)
        approved = approval.transition(ApprovalStatus.APPROVED)
        await approvals.save(approved, expected_version=approval.version)

        self.assertEqual(await approvals.get(approval.id), approved)
        with self.assertRaises(ConcurrencyConflictError):
            await approvals.save(
                approval.transition(ApprovalStatus.REJECTED),
                expected_version=approval.version,
            )

    async def test_runtime_binding_invocation_artifact_and_audit_roundtrip(self) -> None:
        runtimes = MemoryRuntimeRepository()
        artifacts = MemoryArtifactRepository()
        audit = MemoryAuditStore()

        binding = RuntimeBinding(runtime_id="test/runtime@1", runtime_family="test")
        invocation = RuntimeInvocation(
            binding_id=binding.id,
            runtime_id=binding.resolved_runtime_id,
            input="work",
        )
        artifact = Artifact(name="report.txt")
        audit_event = AuditEvent(event_type="run.started", subject="run-42")

        await runtimes.add_binding(binding)
        await runtimes.add_invocation(invocation)
        await artifacts.add(artifact)
        await audit.append(audit_event)

        self.assertEqual(await runtimes.get_binding(binding.id), binding)
        self.assertEqual(await runtimes.get_invocation(invocation.id), invocation)
        self.assertEqual(await artifacts.get(artifact.id), artifact)
        self.assertEqual(
            await audit.list_for_subject("run-42"),
            (audit_event,),
        )

    def test_domain_event_and_integration_event_are_distinct_contracts(self) -> None:
        domain_event = DomainEvent(
            name="RunWaiting",
            aggregate_type="Run",
            aggregate_id="run-42",
        )
        integration_event = IntegrationEvent(
            name="run.waiting",
            aggregate_type="Run",
            aggregate_id="run-42",
        )

        self.assertNotEqual(type(domain_event), type(integration_event))


class PersistenceConflictAndStoreCoverageTests(unittest.IsolatedAsyncioTestCase):
    async def test_run_repository_rejects_duplicate_missing_and_non_incrementing_save(self) -> None:
        repository = MemoryRunRepository()
        run = Run()
        await repository.add(run)

        with self.assertRaises(DuplicateAggregateError):
            await repository.add(run)
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(run, expected_version=run.version)
        with self.assertRaises(ConcurrencyConflictError):
            await MemoryRunRepository().save(
                run.transition(RunStatus.RUNNING),
                expected_version=run.version,
            )

    async def test_session_repository_save_and_conflicts(self) -> None:
        repository = MemorySessionRepository()
        session = Session()
        await repository.add(session)
        updated = replace(session, version=session.version.next())
        await repository.save(updated, expected_version=session.version)
        self.assertEqual(await repository.get(session.id), updated)

        with self.assertRaises(DuplicateAggregateError):
            await repository.add(updated)
        with self.assertRaises(ConcurrencyConflictError):
            await MemorySessionRepository().save(
                updated,
                expected_version=session.version,
            )

    async def test_conversation_repository_save_and_conflicts(self) -> None:
        repository = MemoryConversationRepository()
        conversation = Conversation()
        await repository.add(conversation)
        message = ConversationMessage(actor="agent", content="step")
        updated = conversation.append(message)
        await repository.save(updated, expected_version=conversation.version)

        self.assertEqual(await repository.get(conversation.id), updated)
        with self.assertRaises(DuplicateAggregateError):
            await repository.add(updated)
        with self.assertRaises(ConcurrencyConflictError):
            await MemoryConversationRepository().save(
                updated,
                expected_version=conversation.version,
            )

    async def test_message_repository_get_and_duplicate(self) -> None:
        repository = MemoryMessageRepository()
        conversation = Conversation()
        message = ConversationMessage(actor="human", content="hello")
        await repository.append(conversation.id, message)

        self.assertEqual(await repository.get(message.id), message)
        with self.assertRaises(DuplicateAggregateError):
            await repository.append(conversation.id, message)

    async def test_effect_lookup_same_id_and_missing_save_paths(self) -> None:
        repository = MemoryEffectRepository()
        key = IdempotencyKey("run", "lookup")
        effect = Effect(
            idempotency_key=key,
            fingerprint=InputFingerprint.from_text("payload"),
        )
        first = await repository.reserve(effect)
        by_id = await repository.reserve(effect)
        by_key = await repository.find_by_idempotency_key(
            effect.idempotency_scope,
            key,
        )

        self.assertTrue(first.created)
        self.assertFalse(by_id.created)
        self.assertEqual(by_key, effect)
        self.assertIsNone(
            await repository.find_by_idempotency_key(
                effect.idempotency_scope,
                IdempotencyKey("run", "missing"),
            )
        )

        with self.assertRaises(ConcurrencyConflictError):
            await MemoryEffectRepository().save(
                effect.begin(),
                expected_version=effect.version,
            )

    async def test_reconciliation_repository_create_update_and_evidence_conflicts(self) -> None:
        repository = MemoryReconciliationRepository()
        effect = Effect()
        self.assertIsNone(await repository.get_active(effect.id))
        case = ReconciliationCase(effect_id=effect.id, reason="ambiguous")
        await repository.save(case, expected_version=None)

        with self.assertRaises(DuplicateAggregateError):
            await repository.save(case, expected_version=None)

        running = case.start()
        await repository.save(running, expected_version=case.version)
        self.assertEqual(await repository.get_active(effect.id), running)

        evidence = ReconciliationEvidence(
            case_id=case.id,
            summary="provider observation",
        )
        await repository.append_evidence(evidence)
        with self.assertRaises(DuplicateAggregateError):
            await repository.append_evidence(evidence)

        with self.assertRaises(ConcurrencyConflictError):
            await MemoryReconciliationRepository().save(
                running,
                expected_version=case.version,
            )

    async def test_approval_repository_duplicate_missing_and_pending_listing(self) -> None:
        repository = MemoryApprovalRepository()
        approval = Approval(subject="effect-x")
        await repository.add(approval)
        self.assertEqual(await repository.list_pending(), (approval,))

        with self.assertRaises(DuplicateAggregateError):
            await repository.add(approval)
        with self.assertRaises(ConcurrencyConflictError):
            await MemoryApprovalRepository().save(
                approval.transition(ApprovalStatus.APPROVED),
                expected_version=approval.version,
            )

    async def test_lease_duplicate_missing_and_release_paths(self) -> None:
        repository = MemoryLeaseRepository()
        token = await repository.next_fencing_token("run:x")
        held = Lease(resource="run:x").acquire(WorkerId("worker-x"), token)
        await repository.add(held)

        with self.assertRaises(DuplicateAggregateError):
            await repository.add(held)

        released = held.release()
        await repository.save(released, expected_version=held.version)
        self.assertEqual(await repository.get_current("run:x"), released)

        with self.assertRaises(ConcurrencyConflictError):
            await MemoryLeaseRepository().save(
                released,
                expected_version=held.version,
            )

    async def test_worker_repository_roundtrip_cas_and_conflicts(self) -> None:
        repository = MemoryWorkerRepository()
        worker = Worker()
        await repository.add(worker)
        updated = replace(worker, version=worker.version.next())
        await repository.save(updated, expected_version=worker.version)

        self.assertEqual(await repository.get(worker.id), updated)
        with self.assertRaises(DuplicateAggregateError):
            await repository.add(updated)
        with self.assertRaises(ConcurrencyConflictError):
            await MemoryWorkerRepository().save(
                updated,
                expected_version=worker.version,
            )

    async def test_runtime_invocation_save_and_conflicts(self) -> None:
        repository = MemoryRuntimeRepository()
        binding = RuntimeBinding(runtime_id="runtime/test@1", runtime_family="test")
        invocation = RuntimeInvocation(
            binding_id=binding.id,
            runtime_id=binding.resolved_runtime_id,
            input="persist",
        )
        await repository.add_binding(binding)
        await repository.add_invocation(invocation)
        updated = replace(invocation, version=invocation.version.next())
        await repository.save_invocation(
            updated,
            expected_version=invocation.version,
        )

        self.assertEqual(await repository.get_invocation(invocation.id), updated)
        with self.assertRaises(DuplicateAggregateError):
            await repository.add_binding(binding)
        with self.assertRaises(DuplicateAggregateError):
            await repository.add_invocation(updated)
        with self.assertRaises(ConcurrencyConflictError):
            await MemoryRuntimeRepository().save_invocation(
                updated,
                expected_version=invocation.version,
            )

    async def test_artifact_audit_and_blob_conflict_free_paths(self) -> None:
        artifacts = MemoryArtifactRepository()
        artifact = Artifact(name="payload.bin")
        await artifacts.add(artifact)
        with self.assertRaises(DuplicateAggregateError):
            await artifacts.add(artifact)

        audit = MemoryAuditStore()
        self.assertEqual(await audit.list_for_subject("missing"), ())
        event = AuditEvent(event_type="artifact.created", subject=str(artifact.id))
        await audit.append(event)
        self.assertEqual(await audit.list_for_subject(str(artifact.id)), (event,))

        blobs = MemoryBlobStore()
        self.assertEqual(await blobs.put("artifact/1", b"payload"), "artifact/1")
        self.assertEqual(await blobs.get("artifact/1"), b"payload")
        await blobs.delete("artifact/1")
        with self.assertRaises(KeyError):
            await blobs.get("artifact/1")

    async def test_outbox_failure_duplicate_and_release_paths(self) -> None:
        outbox = MemoryOutboxStore()
        event = IntegrationEvent(name="effect.changed")
        await outbox.append(event)
        with self.assertRaises(DuplicateAggregateError):
            await outbox.append(event)

        claim = (await outbox.claim_batch(worker_id="publisher"))[0]
        self.assertEqual(claim.status, OutboxStatus.CLAIMED)
        await outbox.mark_failed(event.event_id, error="broker unavailable")

        retry = (await outbox.claim_batch(worker_id="retry"))[0]
        self.assertEqual(retry.status, OutboxStatus.CLAIMED)
        await outbox.release_claim(event.event_id)
        third = (await outbox.claim_batch(worker_id="third"))[0]
        self.assertEqual(third.attempt_count, 3)

    async def test_inbox_failed_path_and_missing_lookup(self) -> None:
        inbox = MemoryInboxStore()
        self.assertIsNone(await inbox.get("source", "missing"))
        record = InboxRecord(
            source="source",
            external_event_id="evt",
            digest="a" * 64,
        )
        await inbox.reserve(record)
        await inbox.mark_failed("source", "evt", error="handler failed")
        failed = await inbox.get("source", "evt")
        self.assertIsNotNone(failed)
        assert failed is not None
        self.assertEqual(failed.status, InboxStatus.FAILED)
        self.assertEqual(failed.last_error, "handler failed")

    async def test_uow_exception_rolls_back_and_explicit_rollback_is_idempotent(self) -> None:
        uow = MemoryUnitOfWork()
        run = Run()

        with self.assertRaisesRegex(RuntimeError, "boom"):
            async with uow:
                await uow.runs.add(run)
                raise RuntimeError("boom")

        self.assertIsNone(await uow.runs.get(run.id))
        await uow.rollback()
        await uow.rollback()

    def test_event_validation_and_memory_scope_validation(self) -> None:
        with self.assertRaises(ValueError):
            DomainEvent(name="", aggregate_type="Run", aggregate_id="run")
        with self.assertRaises(ValueError):
            IntegrationEvent(name="")
        with self.assertRaises(ValueError):
            MemoryEntry(scope=MemoryScope.SESSION, key="missing-scope")


if __name__ == "__main__":
    unittest.main()
