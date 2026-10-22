from __future__ import annotations

import unittest
from dataclasses import replace

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
    MemoryRunRepository,
    MemoryRuntimeRepository,
    MemorySessionRepository,
    MemoryUnitOfWork,
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
    Run,
    RunStatus,
    RuntimeBinding,
    RuntimeInvocation,
    Session,
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


if __name__ == "__main__":
    unittest.main()
