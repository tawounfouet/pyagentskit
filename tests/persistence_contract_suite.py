from __future__ import annotations

from pyagentskit.contracts import InboxRecord, OutboxStatus
from pyagentskit.domain import (
    ConcurrencyConflictError,
    Effect,
    IdempotencyConflictError,
    IdempotencyKey,
    InboxDigestConflictError,
    InputFingerprint,
    IntegrationEvent,
    Run,
    RunStatus,
)


class PersistenceContractSuiteMixin:
    """Reusable P0 persistence contracts shared by every qualified backend."""

    async def make_run_repository(self):
        raise NotImplementedError

    async def make_effect_repository(self):
        raise NotImplementedError

    async def make_outbox_store(self):
        raise NotImplementedError

    async def make_inbox_store(self):
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
