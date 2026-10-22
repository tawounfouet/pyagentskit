from __future__ import annotations

from dataclasses import replace

from pyagentskit.contracts import InboxRecord, OutboxStatus
from pyagentskit.domain import (
    Approval,
    ApprovalStatus,
    Artifact,
    AuditEvent,
    ConcurrencyConflictError,
    Conversation,
    ConversationMessage,
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
    RuntimeBinding,
    RuntimeInvocation,
    Session,
    Worker,
    WorkerId,
    WorkerStatus,
)


class PersistenceContractSuiteMixin:
    """Reusable P0 persistence contracts shared by every qualified backend."""

    async def make_run_repository(self):
        raise NotImplementedError

    async def make_session_repository(self):
        raise NotImplementedError

    async def make_conversation_repository(self):
        raise NotImplementedError

    async def make_message_repository(self):
        raise NotImplementedError

    async def make_memory_repository(self):
        raise NotImplementedError

    async def make_effect_repository(self):
        raise NotImplementedError

    async def make_reconciliation_repository(self):
        raise NotImplementedError

    async def make_approval_repository(self):
        raise NotImplementedError

    async def make_lease_repository(self):
        raise NotImplementedError

    async def make_worker_repository(self):
        raise NotImplementedError

    async def make_artifact_repository(self):
        raise NotImplementedError

    async def make_runtime_repository(self):
        raise NotImplementedError

    async def make_audit_store(self):
        raise NotImplementedError

    async def make_outbox_store(self):
        raise NotImplementedError

    async def make_inbox_store(self):
        raise NotImplementedError

    async def make_unit_of_work(self):
        raise NotImplementedError

    async def test_contract_run_compare_and_swap_is_fail_closed(self) -> None:
        repository = await self.make_run_repository()
        run = Run()
        await repository.add(run)
        writer_a = run.transition(RunStatus.RUNNING)
        writer_b = run.transition(RunStatus.RUNNING)

        await repository.save(writer_a, expected_version=run.version)
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(writer_b, expected_version=run.version)

        self.assertEqual(await repository.get(run.id), writer_a)

    async def test_contract_session_compare_and_swap_is_fail_closed(self) -> None:
        repository = await self.make_session_repository()
        session = Session()
        await repository.add(session)
        writer_a = replace(session, version=session.version.next())
        writer_b = replace(session, version=session.version.next())

        await repository.save(writer_a, expected_version=session.version)
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(writer_b, expected_version=session.version)

        self.assertEqual(await repository.get(session.id), writer_a)

    async def test_contract_conversation_and_message_are_separate_durable_objects(self) -> None:
        sessions = await self.make_session_repository()
        conversations = await self.make_conversation_repository()
        messages = await self.make_message_repository()
        session = Session()
        await sessions.add(session)
        conversation = Conversation(session_id=session.id)
        await conversations.add(conversation)

        message = ConversationMessage(actor="agent", content="hello")
        await messages.append(conversation.id, message)
        self.assertEqual(await messages.get(message.id), message)
        self.assertEqual(
            await messages.list_for_conversation(conversation.id),
            (message,),
        )
        self.assertEqual(
            await conversations.list_for_session(session.id),
            (conversation,),
        )

        with self.assertRaises(DuplicateAggregateError):
            await messages.append(conversation.id, message)

        updated = conversation.append(message)
        await conversations.save(updated, expected_version=conversation.version)
        with self.assertRaises(ConcurrencyConflictError):
            await conversations.save(updated, expected_version=conversation.version)

    async def test_contract_memory_is_scoped_and_compare_and_swap_protected(self) -> None:
        repository = await self.make_memory_repository()
        entry = MemoryEntry(
            scope=MemoryScope.SESSION,
            scope_id="session-contract",
            key="profile",
            value={"tier": "gold"},
        )
        await repository.put(entry)
        revised = entry.revise({"tier": "platinum"})
        await repository.save(revised, expected_version=entry.version)

        self.assertEqual(await repository.get(entry.id), revised)
        self.assertEqual(
            await repository.list_by_scope(
                tenant_id=str(entry.tenant_id),
                scope=entry.scope.value,
                scope_id=entry.scope_id,
            ),
            (revised,),
        )
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(revised, expected_version=entry.version)

    async def test_contract_effect_idempotency_is_physical_and_intent_safe(self) -> None:
        runs = await self.make_run_repository()
        effects = await self.make_effect_repository()
        run = Run()
        await runs.add(run)

        key = IdempotencyKey("contract", "effect-42")
        fingerprint = InputFingerprint.from_text("payload=42")
        effect = Effect(
            run_id=run.id,
            idempotency_key=key,
            fingerprint=fingerprint,
        )

        first = await effects.reserve(effect)
        repeated = await effects.reserve(
            Effect(
                run_id=run.id,
                idempotency_key=key,
                fingerprint=fingerprint,
            )
        )

        self.assertTrue(first.created)
        self.assertFalse(repeated.created)
        self.assertEqual(repeated.effect.id, effect.id)

        with self.assertRaises(IdempotencyConflictError):
            await effects.reserve(
                Effect(
                    run_id=run.id,
                    idempotency_key=key,
                    fingerprint=InputFingerprint.from_text("payload=43"),
                )
            )

    async def test_contract_reconciliation_case_and_evidence_are_durable(self) -> None:
        runs = await self.make_run_repository()
        effects = await self.make_effect_repository()
        reconciliations = await self.make_reconciliation_repository()
        run = Run()
        await runs.add(run)
        effect = Effect(run_id=run.id)
        await effects.reserve(effect)

        case = ReconciliationCase(effect_id=effect.id, reason="ambiguous")
        await reconciliations.save(case, expected_version=None)
        running = case.start()
        await reconciliations.save(running, expected_version=case.version)
        self.assertEqual(await reconciliations.get_active(effect.id), running)

        evidence = ReconciliationEvidence(
            case_id=case.id,
            summary="provider observation",
        )
        await reconciliations.append_evidence(evidence)
        with self.assertRaises(DuplicateAggregateError):
            await reconciliations.append_evidence(evidence)

    async def test_contract_approval_is_terminal_and_compare_and_swap_protected(self) -> None:
        repository = await self.make_approval_repository()
        approval = Approval(subject="effect-contract")
        await repository.add(approval)
        self.assertEqual(await repository.list_pending(), (approval,))

        approved = approval.transition(ApprovalStatus.APPROVED)
        await repository.save(approved, expected_version=approval.version)
        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(approved, expected_version=approval.version)

    async def test_contract_lease_has_one_owner_and_monotonic_fencing(self) -> None:
        repository = await self.make_lease_repository()
        resource = "run:contract"
        token_1 = await repository.next_fencing_token(resource)
        lease_a = Lease(resource=resource).acquire(
            WorkerId("worker-contract-a"),
            token_1,
        )
        await repository.add(lease_a)

        token_2 = await repository.next_fencing_token(resource)
        self.assertGreater(token_2, token_1)
        self.assertEqual(token_1, FencingToken(1))
        lease_b = Lease(resource=resource).acquire(
            WorkerId("worker-contract-b"),
            token_2,
        )
        with self.assertRaises(ConcurrencyConflictError):
            await repository.add(lease_b)

        await repository.save(lease_a.release(), expected_version=lease_a.version)
        await repository.add(lease_b)
        self.assertEqual(await repository.get_current(resource), lease_b)

    async def test_contract_worker_compare_and_swap_is_fail_closed(self) -> None:
        repository = await self.make_worker_repository()
        worker = Worker()
        await repository.add(worker)
        ready = worker.transition(WorkerStatus.READY)
        await repository.save(ready, expected_version=worker.version)

        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(ready, expected_version=worker.version)
        self.assertEqual(await repository.get(worker.id), ready)

    async def test_contract_artifact_metadata_is_durable_and_identity_unique(self) -> None:
        repository = await self.make_artifact_repository()
        artifact = Artifact(name="contract.txt")
        await repository.add(artifact)
        self.assertEqual(await repository.get(artifact.id), artifact)

        with self.assertRaises(DuplicateAggregateError):
            await repository.add(artifact)

    async def test_contract_runtime_binding_is_immutable_and_invocation_uses_cas(self) -> None:
        runs = await self.make_run_repository()
        runtimes = await self.make_runtime_repository()
        run = Run()
        await runs.add(run)

        binding = RuntimeBinding(
            run_id=run.id,
            runtime_id="contract/runtime@1",
            runtime_family="contract",
        )
        await runtimes.add_binding(binding)
        self.assertEqual(await runtimes.get_binding(binding.id), binding)

        with self.assertRaises(DuplicateAggregateError):
            await runtimes.add_binding(binding)

        invocation = RuntimeInvocation(
            run_id=run.id,
            binding_id=binding.id,
            input="contract-work",
            runtime_id=binding.resolved_runtime_id,
        )
        await runtimes.add_invocation(invocation)
        self.assertEqual(await runtimes.get_invocation(invocation.id), invocation)

        updated = replace(
            invocation,
            version=invocation.version.next(),
        )
        await runtimes.save_invocation(
            updated,
            expected_version=invocation.version,
        )

        with self.assertRaises(ConcurrencyConflictError):
            await runtimes.save_invocation(
                updated,
                expected_version=invocation.version,
            )

    async def test_contract_audit_is_append_oriented_and_queryable(self) -> None:
        audit = await self.make_audit_store()
        event = AuditEvent(event_type="contract.checked", subject="run-contract")
        await audit.append(event)
        self.assertEqual(await audit.list_for_subject("run-contract"), (event,))

    async def test_contract_outbox_claim_can_be_recovered_after_publisher_crash(self) -> None:
        outbox = await self.make_outbox_store()
        event = IntegrationEvent(name="contract.event")
        await outbox.append(event)

        first = await outbox.claim_batch(worker_id="publisher-a")
        self.assertEqual(first[0].status, OutboxStatus.CLAIMED)
        self.assertEqual(first[0].attempt_count, 1)

        reclaimed = await outbox.claim_batch(
            worker_id="publisher-b",
            claim_timeout_seconds=0,
        )
        self.assertEqual(reclaimed[0].attempt_count, 2)
        self.assertEqual(reclaimed[0].claimed_by, "publisher-b")

        await outbox.mark_published(event.event_id)
        self.assertEqual(await outbox.claim_batch(worker_id="publisher-c"), ())

    async def test_contract_unit_of_work_rolls_back_catalog_and_outbox_together(self) -> None:
        uow = await self.make_unit_of_work()
        session = Session()
        conversation = Conversation(session_id=session.id)
        artifact = Artifact(name="transactional.txt")
        event = IntegrationEvent(
            name="conversation.created",
            aggregate_type="Conversation",
            aggregate_id=str(conversation.id),
        )

        async with uow:
            await uow.sessions.add(session)
            await uow.conversations.add(conversation)
            await uow.artifacts.add(artifact)
            await uow.outbox.append(event)

        self.assertIsNone(await uow.sessions.get(session.id))
        self.assertIsNone(await uow.artifacts.get(artifact.id))
        self.assertEqual(await uow.outbox.claim_batch(worker_id="publisher"), ())

    async def test_contract_unit_of_work_commits_catalog_and_outbox_together(self) -> None:
        uow = await self.make_unit_of_work()
        session = Session()
        conversation = Conversation(session_id=session.id)
        artifact = Artifact(name="committed.txt")
        event = IntegrationEvent(
            name="conversation.created",
            aggregate_type="Conversation",
            aggregate_id=str(conversation.id),
        )

        async with uow:
            await uow.sessions.add(session)
            await uow.conversations.add(conversation)
            await uow.artifacts.add(artifact)
            await uow.outbox.append(event)
            await uow.commit()

        self.assertEqual(await uow.sessions.get(session.id), session)
        self.assertEqual(await uow.artifacts.get(artifact.id), artifact)
        claimed = await uow.outbox.claim_batch(worker_id="publisher")
        self.assertEqual(claimed[0].event.event_id, event.event_id)

    async def test_contract_inbox_dedup_is_distinct_from_effect_idempotency(self) -> None:
        inbox = await self.make_inbox_store()
        record = InboxRecord(
            source="contract-consumer",
            external_event_id="message-42",
            digest="a" * 64,
        )

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
