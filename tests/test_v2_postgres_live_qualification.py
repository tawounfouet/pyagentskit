"""Real PostgreSQL qualification for the V2 persistence contracts.

This suite is opt-in locally and mandatory in the dedicated CI PostgreSQL job.
It uses a unique table prefix and drops every created V2 table afterwards.
"""

from __future__ import annotations

import asyncio
import os
import unittest
from multiprocessing import get_context
from uuid import uuid4

from pyagentskit.adapters.persistence import (
    PostgresV2AuditStore,
    PostgresV2EffectRepository,
    PostgresV2InboxStore,
    PostgresV2LeaseRepository,
    PostgresV2OutboxStore,
    PostgresV2RunRepository,
    PostgresV2UnitOfWork,
)
from pyagentskit.contracts import InboxRecord
from pyagentskit.domain import (
    AuditEvent,
    ConcurrencyConflictError,
    Effect,
    FencingToken,
    IdempotencyConflictError,
    IdempotencyKey,
    InboxDigestConflictError,
    InputFingerprint,
    IntegrationEvent,
    Lease,
    Run,
    RunStatus,
    WorkerId,
)
from pyagentskit.postgres import AsyncPostgresPool, create_asyncpg_pool

_ENABLED = os.getenv("PYAGENTSKIT_LIVE_POSTGRES") == "I_ACCEPT_DATABASE_WRITES" and bool(
    os.getenv("PYAGENTSKIT_POSTGRES_DSN")
)


async def _drop_v2_tables(pool: AsyncPostgresPool, prefix: str) -> None:
    suffixes = (
        "runtime_invocations",
        "runtime_bindings",
        "messages",
        "conversations",
        "sessions",
        "workers",
        "artifacts",
        "reconciliation_evidence",
        "reconciliation_cases",
        "effects",
        "runs",
        "approvals",
        "leases",
        "lease_resources",
        "audit_events",
        "outbox_events",
        "inbox_events",
        "memory_entries",
        "schema_migrations",
    )
    async with pool.acquire() as connection:
        for suffix in suffixes:
            await connection.execute(f"DROP TABLE IF EXISTS {prefix}_v2_{suffix} CASCADE")


def _lease_process_worker(
    dsn: str,
    prefix: str,
    resource: str,
    token_value: int,
    worker_id: str,
    result_queue: object,
) -> None:
    async def run() -> str:
        pool = await create_asyncpg_pool(dsn, min_size=1, max_size=2)
        try:
            repository = PostgresV2LeaseRepository(pool, table_prefix=prefix)
            lease = Lease(resource=resource).acquire(
                WorkerId(worker_id),
                FencingToken(token_value),
            )
            try:
                await repository.add(lease)
                return "success"
            except ConcurrencyConflictError:
                return "conflict"
        finally:
            close = getattr(pool, "close", None)
            if close is not None:
                await close()

    try:
        outcome = asyncio.run(run())
    except Exception as exc:  # pragma: no cover - surfaced to parent assertion
        outcome = f"error:{type(exc).__name__}:{exc}"
    result_queue.put(outcome)


@unittest.skipUnless(_ENABLED, "PostgreSQL V2 live qualification is opt-in")
class PostgresV2LiveQualification(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        dsn = os.environ["PYAGENTSKIT_POSTGRES_DSN"]
        self.prefix = "pakv2_" + uuid4().hex[:10]
        self.pool = await create_asyncpg_pool(dsn, min_size=1, max_size=8)

    async def asyncTearDown(self) -> None:
        await _drop_v2_tables(self.pool, self.prefix)
        close = getattr(self.pool, "close", None)
        if close is not None:
            await close()

    async def test_run_cas_and_effect_idempotency_are_physical(self) -> None:
        runs_a = PostgresV2RunRepository(self.pool, table_prefix=self.prefix)
        runs_b = PostgresV2RunRepository(self.pool, table_prefix=self.prefix)
        run = Run()
        await runs_a.add(run)

        writer_a = run.transition(RunStatus.RUNNING)
        writer_b = run.transition(RunStatus.RUNNING)
        outcomes = await asyncio.gather(
            runs_a.save(writer_a, expected_version=run.version),
            runs_b.save(writer_b, expected_version=run.version),
            return_exceptions=True,
        )
        conflicts = [item for item in outcomes if isinstance(item, ConcurrencyConflictError)]
        self.assertEqual(len(conflicts), 1)

        effects = PostgresV2EffectRepository(self.pool, table_prefix=self.prefix)
        key = IdempotencyKey("run", "live-effect")
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

    async def test_lease_owner_uniqueness_and_fencing_are_database_serialized(self) -> None:
        leases_a = PostgresV2LeaseRepository(self.pool, table_prefix=self.prefix)
        leases_b = PostgresV2LeaseRepository(self.pool, table_prefix=self.prefix)

        token_1 = await leases_a.next_fencing_token("run:live")
        lease_a = Lease(resource="run:live").acquire(
            WorkerId("worker-a"),
            token_1,
        )
        await leases_a.add(lease_a)

        token_2 = await leases_b.next_fencing_token("run:live")
        self.assertEqual(token_1, FencingToken(1))
        self.assertEqual(token_2, FencingToken(2))
        lease_b = Lease(resource="run:live").acquire(
            WorkerId("worker-b"),
            token_2,
        )
        with self.assertRaises(ConcurrencyConflictError):
            await leases_b.add(lease_b)

        released = lease_a.release()
        await leases_a.save(released, expected_version=lease_a.version)
        await leases_b.add(lease_b)
        self.assertEqual(await leases_a.get_current("run:live"), lease_b)

        tokens = await asyncio.gather(
            leases_a.next_fencing_token("run:counter"),
            leases_b.next_fencing_token("run:counter"),
        )
        self.assertEqual({item.value for item in tokens}, {1, 2})

    async def test_multi_process_lease_has_one_owner_then_monotonic_takeover(self) -> None:
        resource = "run:multiprocess"
        leases = PostgresV2LeaseRepository(self.pool, table_prefix=self.prefix)
        token = await leases.next_fencing_token(resource)

        context = get_context("spawn")
        result_queue = context.Queue()
        dsn = os.environ["PYAGENTSKIT_POSTGRES_DSN"]
        processes = [
            context.Process(
                target=_lease_process_worker,
                args=(
                    dsn,
                    self.prefix,
                    resource,
                    token.value,
                    f"worker-{index}",
                    result_queue,
                ),
            )
            for index in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            await asyncio.to_thread(process.join, 20)
            if process.is_alive():
                process.terminate()
                process.join()
                self.fail("multiprocess lease worker did not terminate")
            self.assertEqual(process.exitcode, 0)

        outcomes = [await asyncio.to_thread(result_queue.get, True, 5) for _ in processes]
        self.assertCountEqual(outcomes, ["success", "conflict"])

        current = await leases.get_current(resource)
        self.assertIsNotNone(current)
        assert current is not None
        released = current.release()
        await leases.save(released, expected_version=current.version)

        takeover_token = await leases.next_fencing_token(resource)
        self.assertGreater(takeover_token, token)
        takeover = Lease(resource=resource).acquire(
            WorkerId("worker-takeover"),
            takeover_token,
        )
        await leases.add(takeover)
        self.assertEqual(await leases.get_current(resource), takeover)

    async def test_parallel_outbox_claims_are_disjoint_and_inbox_deduplicates(self) -> None:
        outbox_a = PostgresV2OutboxStore(self.pool, table_prefix=self.prefix)
        outbox_b = PostgresV2OutboxStore(self.pool, table_prefix=self.prefix)
        events = tuple(IntegrationEvent(name=f"event.{index}") for index in range(6))
        for event in events:
            await outbox_a.append(event)

        first, second = await asyncio.gather(
            outbox_a.claim_batch(worker_id="publisher-a", limit=3),
            outbox_b.claim_batch(worker_id="publisher-b", limit=3),
        )
        first_ids = {item.event.event_id for item in first}
        second_ids = {item.event.event_id for item in second}
        self.assertEqual(len(first), 3)
        self.assertEqual(len(second), 3)
        self.assertTrue(first_ids.isdisjoint(second_ids))
        self.assertEqual(first_ids | second_ids, {event.event_id for event in events})

        inbox = PostgresV2InboxStore(self.pool, table_prefix=self.prefix)
        record = InboxRecord(
            source="ci",
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

    async def test_unit_of_work_commits_and_rolls_back_state_audit_outbox_atomically(self) -> None:
        committed_run = Run()
        committed_event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(committed_run.id),
        )
        committed_audit = AuditEvent(
            event_type="run.created",
            subject=str(committed_run.id),
        )
        uow = PostgresV2UnitOfWork(self.pool, table_prefix=self.prefix)
        async with uow:
            await uow.runs.add(committed_run)
            await uow.audit.append(committed_audit)
            await uow.outbox.append(committed_event)
            await uow.commit()

        runs = PostgresV2RunRepository(self.pool, table_prefix=self.prefix)
        audit = PostgresV2AuditStore(self.pool, table_prefix=self.prefix)
        outbox = PostgresV2OutboxStore(self.pool, table_prefix=self.prefix)
        self.assertEqual(await runs.get(committed_run.id), committed_run)
        self.assertEqual(
            await audit.list_for_subject(str(committed_run.id)),
            (committed_audit,),
        )
        claimed = await outbox.claim_batch(worker_id="publisher", limit=10)
        self.assertIn(
            committed_event.event_id,
            {item.event.event_id for item in claimed},
        )

        rolled_back_run = Run()
        rolled_back_event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(rolled_back_run.id),
        )
        rollback_uow = PostgresV2UnitOfWork(self.pool, table_prefix=self.prefix)
        with self.assertRaisesRegex(RuntimeError, "rollback"):
            async with rollback_uow:
                await rollback_uow.runs.add(rolled_back_run)
                await rollback_uow.outbox.append(rolled_back_event)
                raise RuntimeError("rollback")

        self.assertIsNone(await runs.get(rolled_back_run.id))
        remaining = await outbox.claim_batch(
            worker_id="publisher-after-rollback",
            limit=20,
        )
        self.assertNotIn(
            rolled_back_event.event_id,
            {item.event.event_id for item in remaining},
        )


if __name__ == "__main__":
    unittest.main()
