"""Live PostgreSQL qualification for the V2 persistence contracts."""

from __future__ import annotations

import asyncio
import multiprocessing as mp
import os
import queue
import unittest
from collections.abc import Iterable
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
from pyagentskit.contracts import InboxRecord, OutboxStatus
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
from tests.persistence_contract_suite import PersistenceContractSuiteMixin

_GATE = os.getenv("PYAGENTSKIT_LIVE_POSTGRES") == "I_ACCEPT_DATABASE_WRITES" and bool(
    os.getenv("PYAGENTSKIT_POSTGRES_DSN")
)

_SUFFIXES = (
    "reconciliation_evidence",
    "reconciliation_cases",
    "effects",
    "memory_entries",
    "approvals",
    "leases",
    "lease_resources",
    "audit_events",
    "outbox_events",
    "inbox_events",
    "runs",
    "schema_migrations",
)


async def _close_pool(pool: object) -> None:
    close = getattr(pool, "close", None)
    if close is not None:
        await close()


async def _drop_tables(
    pool: AsyncPostgresPool,
    prefix: str,
    suffixes: Iterable[str] = _SUFFIXES,
) -> None:
    async with pool.acquire() as connection:
        for suffix in suffixes:
            await connection.execute(f"DROP TABLE IF EXISTS {prefix}_v2_{suffix} CASCADE")


async def _lease_process_attempt(
    dsn: str,
    prefix: str,
    worker_id: str,
) -> tuple[str, str, int]:
    pool = await create_asyncpg_pool(dsn, min_size=1, max_size=1)
    repository = PostgresV2LeaseRepository(pool, table_prefix=prefix)
    try:
        token = await repository.next_fencing_token("run:multi-process")
        lease = Lease(resource="run:multi-process").acquire(
            WorkerId(worker_id),
            token,
        )
        try:
            await repository.add(lease)
        except ConcurrencyConflictError:
            return worker_id, "conflict", token.value
        return worker_id, "won", token.value
    finally:
        await _close_pool(pool)


def _lease_process_entry(
    dsn: str,
    prefix: str,
    worker_id: str,
    start: mp.synchronize.Event,
    results: mp.queues.Queue,
) -> None:
    start.wait(timeout=10)
    try:
        result = asyncio.run(_lease_process_attempt(dsn, prefix, worker_id))
    except Exception as exc:
        results.put((worker_id, "error", repr(exc)))
    else:
        results.put(result)


@unittest.skipUnless(_GATE, "PostgreSQL V2 live qualification is opt-in")
class PostgresV2LiveQualification(
    PersistenceContractSuiteMixin,
    unittest.IsolatedAsyncioTestCase,
):
    async def asyncSetUp(self) -> None:
        self.dsn = os.environ["PYAGENTSKIT_POSTGRES_DSN"]
        self.prefix = "pakv2live_" + uuid4().hex[:10]
        self.pool = await create_asyncpg_pool(self.dsn, min_size=1, max_size=6)

    async def asyncTearDown(self) -> None:
        try:
            await _drop_tables(self.pool, self.prefix)
        finally:
            await _close_pool(self.pool)

    async def make_run_repository(self):
        return PostgresV2RunRepository(self.pool, table_prefix=self.prefix)

    async def make_effect_repository(self):
        return PostgresV2EffectRepository(self.pool, table_prefix=self.prefix)

    async def make_outbox_store(self):
        return PostgresV2OutboxStore(self.pool, table_prefix=self.prefix)

    async def make_inbox_store(self):
        return PostgresV2InboxStore(self.pool, table_prefix=self.prefix)

    async def test_real_postgres_cas_idempotency_and_fencing(self) -> None:
        runs = PostgresV2RunRepository(self.pool, table_prefix=self.prefix)
        effects = PostgresV2EffectRepository(self.pool, table_prefix=self.prefix)
        leases = PostgresV2LeaseRepository(self.pool, table_prefix=self.prefix)

        run = Run()
        await runs.add(run)
        writer_a = run.transition(RunStatus.RUNNING)
        writer_b = run.transition(RunStatus.RUNNING)
        await runs.save(writer_a, expected_version=run.version)
        with self.assertRaises(ConcurrencyConflictError):
            await runs.save(writer_b, expected_version=run.version)

        key = IdempotencyKey("live", "charge-42")
        fingerprint = InputFingerprint.from_text("amount=42")
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
                    fingerprint=InputFingerprint.from_text("amount=43"),
                )
            )

        token_1 = await leases.next_fencing_token("run:42")
        lease_a = Lease(resource="run:42").acquire(WorkerId("worker-a"), token_1)
        await leases.add(lease_a)

        token_2 = await leases.next_fencing_token("run:42")
        self.assertEqual(token_1, FencingToken(1))
        self.assertEqual(token_2, FencingToken(2))
        lease_b = Lease(resource="run:42").acquire(WorkerId("worker-b"), token_2)
        with self.assertRaises(ConcurrencyConflictError):
            await leases.add(lease_b)

        await leases.save(lease_a.release(), expected_version=lease_a.version)
        await leases.add(lease_b)
        self.assertEqual(await leases.get_current("run:42"), lease_b)

    async def test_real_postgres_uow_outbox_reclaim_and_inbox_dedup(self) -> None:
        run = Run()
        audit_event = AuditEvent(event_type="run.created", subject=str(run.id))
        integration_event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(run.id),
        )

        uow = PostgresV2UnitOfWork(self.pool, table_prefix=self.prefix)
        async with uow:
            await uow.runs.add(run)
            await uow.audit.append(audit_event)
            await uow.outbox.append(integration_event)
            await uow.commit()

        runs = PostgresV2RunRepository(self.pool, table_prefix=self.prefix)
        audit = PostgresV2AuditStore(self.pool, table_prefix=self.prefix)
        outbox = PostgresV2OutboxStore(self.pool, table_prefix=self.prefix)
        inbox = PostgresV2InboxStore(self.pool, table_prefix=self.prefix)

        self.assertEqual(await runs.get(run.id), run)
        self.assertEqual(await audit.list_for_subject(str(run.id)), (audit_event,))

        first_claim = await outbox.claim_batch(worker_id="publisher-a")
        self.assertEqual(first_claim[0].status, OutboxStatus.CLAIMED)
        reclaimed = await outbox.claim_batch(
            worker_id="publisher-b",
            claim_timeout_seconds=0,
        )
        self.assertEqual(reclaimed[0].attempt_count, 2)
        self.assertEqual(reclaimed[0].claimed_by, "publisher-b")
        await outbox.mark_published(integration_event.event_id)

        record = InboxRecord(
            source="live-consumer",
            external_event_id=integration_event.event_id,
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
        await inbox.mark_processed(record.source, record.external_event_id)

    async def test_uncommitted_uow_rolls_back_state_and_outbox(self) -> None:
        run = Run()
        event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(run.id),
        )
        uow = PostgresV2UnitOfWork(self.pool, table_prefix=self.prefix)
        async with uow:
            await uow.runs.add(run)
            await uow.outbox.append(event)

        runs = PostgresV2RunRepository(self.pool, table_prefix=self.prefix)
        outbox = PostgresV2OutboxStore(self.pool, table_prefix=self.prefix)
        self.assertIsNone(await runs.get(run.id))
        self.assertEqual(await outbox.claim_batch(worker_id="publisher"), ())


@unittest.skipUnless(_GATE, "PostgreSQL V2 live qualification is opt-in")
class PostgresV2MultiProcessQualification(unittest.TestCase):
    def test_two_processes_cannot_be_active_owner_of_one_resource(self) -> None:
        dsn = os.environ["PYAGENTSKIT_POSTGRES_DSN"]
        prefix = "pakv2mp_" + uuid4().hex[:10]

        async def prepare() -> None:
            pool = await create_asyncpg_pool(dsn, min_size=1, max_size=2)
            try:
                repository = PostgresV2LeaseRepository(pool, table_prefix=prefix)
                await repository.initialize()
            finally:
                await _close_pool(pool)

        asyncio.run(prepare())

        context = mp.get_context("spawn")
        start = context.Event()
        results = context.Queue()
        processes = [
            context.Process(
                target=_lease_process_entry,
                args=(dsn, prefix, worker_id, start, results),
            )
            for worker_id in ("worker-a", "worker-b")
        ]
        for process in processes:
            process.start()
        start.set()

        observed: list[tuple[str, str, object]] = []
        try:
            for _ in processes:
                try:
                    observed.append(results.get(timeout=20))
                except queue.Empty as exc:
                    self.fail(f"timed out waiting for lease process: {exc}")
        finally:
            for process in processes:
                process.join(timeout=20)
                if process.is_alive():
                    process.terminate()
                    process.join(timeout=5)

        self.assertEqual(sum(status == "won" for _, status, _ in observed), 1)
        self.assertEqual(sum(status == "conflict" for _, status, _ in observed), 1)
        self.assertFalse(any(status == "error" for _, status, _ in observed))

        async def cleanup() -> None:
            pool = await create_asyncpg_pool(dsn, min_size=1, max_size=1)
            try:
                await _drop_tables(pool, prefix, ("leases", "lease_resources", "schema_migrations"))
            finally:
                await _close_pool(pool)

        asyncio.run(cleanup())


if __name__ == "__main__":
    unittest.main()
