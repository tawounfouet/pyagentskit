from __future__ import annotations

import unittest
from collections.abc import Mapping, Sequence
from contextlib import AbstractAsyncContextManager
from datetime import UTC, datetime
from typing import Any

from pyagentskit.adapters.persistence import (
    PostgresV2ApprovalRepository,
    PostgresV2AuditStore,
    PostgresV2EffectRepository,
    PostgresV2InboxStore,
    PostgresV2LeaseRepository,
    PostgresV2MemoryRepository,
    PostgresV2OutboxStore,
    PostgresV2ReconciliationRepository,
    PostgresV2RunRepository,
    PostgresV2UnitOfWork,
)
from pyagentskit.adapters.persistence._codec import (
    approval_to_document,
    audit_to_document,
    dumps,
    effect_to_document,
    integration_event_to_document,
    lease_to_document,
    memory_to_document,
    reconciliation_case_to_document,
    run_to_document,
)
from pyagentskit.contracts import InboxRecord, InboxStatus, OutboxStatus
from pyagentskit.domain import (
    Approval,
    ApprovalStatus,
    AuditEvent,
    ConcurrencyConflictError,
    Effect,
    FencingToken,
    IdempotencyKey,
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
from pyagentskit.domain.errors import PersistenceError
from pyagentskit.postgres import AsyncPostgresConnection, AsyncPostgresPool


class _Transaction(AbstractAsyncContextManager[None]):
    async def __aenter__(self) -> None:
        return None

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class _Acquire(AbstractAsyncContextManager[AsyncPostgresConnection]):
    def __init__(self, connection: ScriptedPostgresConnection) -> None:
        self.connection = connection

    async def __aenter__(self) -> AsyncPostgresConnection:
        return self.connection

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class ScriptedPostgresConnection:
    def __init__(self) -> None:
        self.schema_version = 1
        self.fetchrow_results: list[Mapping[str, Any] | None] = []
        self.fetch_results: list[Sequence[Mapping[str, Any]]] = []
        self.executed: list[tuple[str, tuple[object, ...]]] = []

    def transaction(self) -> AbstractAsyncContextManager[Any]:
        return _Transaction()

    async def execute(self, query: str, *args: object) -> str:
        self.executed.append((" ".join(query.split()), args))
        return "OK"

    async def fetchrow(self, query: str, *args: object) -> Mapping[str, Any] | None:
        normalized = " ".join(query.split())
        if "schema_migrations" in normalized and "SELECT version" in normalized:
            return {"version": self.schema_version}
        if not self.fetchrow_results:
            raise AssertionError(f"Unexpected fetchrow: {normalized} {args}")
        return self.fetchrow_results.pop(0)

    async def fetch(self, query: str, *args: object) -> Sequence[Mapping[str, Any]]:
        normalized = " ".join(query.split())
        if not self.fetch_results:
            raise AssertionError(f"Unexpected fetch: {normalized} {args}")
        return self.fetch_results.pop(0)


class ScriptedPostgresPool:
    def __init__(self) -> None:
        self.connection = ScriptedPostgresConnection()

    def acquire(self) -> AbstractAsyncContextManager[AsyncPostgresConnection]:
        return _Acquire(self.connection)


class PostgresV2PersistenceTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.pool = ScriptedPostgresPool()
        self.connection = self.pool.connection

    def _row(self, document: dict[str, object]) -> dict[str, object]:
        return {"payload_json": dumps(document)}

    async def test_pool_protocol_and_initialization_guards(self) -> None:
        self.assertIsInstance(self.pool, AsyncPostgresPool)
        self.assertIsInstance(self.connection, AsyncPostgresConnection)

        repository = PostgresV2RunRepository(self.pool, table_prefix="pakv2")
        await repository.initialize()
        await repository.initialize()
        self.assertTrue(
            any("CREATE TABLE IF NOT EXISTS pakv2_v2_schema_migrations" in q for q, _ in self.connection.executed)
        )

        with self.assertRaises(ValueError):
            PostgresV2RunRepository(self.pool, table_prefix="bad-prefix;drop")

        newer = ScriptedPostgresPool()
        newer.connection.schema_version = 99
        with self.assertRaises(PersistenceError):
            await PostgresV2RunRepository(newer, table_prefix="paknewer").initialize()

    async def test_run_repository_roundtrip_and_cas_paths(self) -> None:
        repository = PostgresV2RunRepository(self.pool, table_prefix="pakrun")
        run = Run()
        running = run.transition(RunStatus.RUNNING)

        self.connection.fetchrow_results.extend(
            [
                {"id": str(run.id)},
                {"id": str(run.id)},
                self._row(run_to_document(running)),
            ]
        )
        self.connection.fetch_results.append([self._row(run_to_document(running))])

        await repository.add(run)
        await repository.save(running, expected_version=run.version)
        self.assertEqual(await repository.get(run.id), running)
        self.assertEqual(
            await repository.list_by_state(RunStatus.RUNNING),
            (running,),
        )

        with self.assertRaises(ConcurrencyConflictError):
            await repository.save(run, expected_version=run.version)

    async def test_effect_repository_reservation_lookup_and_save(self) -> None:
        repository = PostgresV2EffectRepository(self.pool, table_prefix="pakeffect")
        run = Run()
        effect = Effect(
            run_id=run.id,
            idempotency_key=IdempotencyKey("run", "effect-42"),
            fingerprint=InputFingerprint.from_text("payload=42"),
        )
        started = effect.begin()
        payload = self._row(effect_to_document(effect))

        self.connection.fetchrow_results.extend(
            [
                {"id": str(effect.id)},
                {"id": str(effect.id)},
                self._row(effect_to_document(started)),
                payload,
            ]
        )
        created = await repository.reserve(effect)
        self.assertTrue(created.created)
        await repository.save(started, expected_version=effect.version)
        self.assertEqual(await repository.get(effect.id), started)
        self.assertEqual(
            await repository.find_by_idempotency_key(
                effect.idempotency_scope,
                effect.idempotency_key,
            ),
            effect,
        )

        duplicate = Effect(
            run_id=run.id,
            idempotency_key=effect.idempotency_key,
            fingerprint=effect.fingerprint,
        )
        self.connection.fetchrow_results.extend([None, payload])
        repeated = await repository.reserve(duplicate)
        self.assertFalse(repeated.created)
        self.assertEqual(repeated.effect.id, effect.id)

    async def test_memory_reconciliation_and_approval_repositories(self) -> None:
        memories = PostgresV2MemoryRepository(self.pool, table_prefix="pakstate")
        entry = MemoryEntry(
            scope=MemoryScope.SESSION,
            scope_id="session-42",
            key="profile",
            value={"tier": "gold"},
        )
        revised = entry.revise({"tier": "platinum"})
        self.connection.fetchrow_results.extend(
            [
                {"id": str(entry.id)},
                {"id": str(entry.id)},
                self._row(memory_to_document(revised)),
            ]
        )
        self.connection.fetch_results.append([self._row(memory_to_document(revised))])

        await memories.put(entry)
        await memories.save(revised, expected_version=entry.version)
        self.assertEqual(await memories.get(entry.id), revised)
        self.assertEqual(
            await memories.list_by_scope(
                tenant_id=str(entry.tenant_id),
                scope=entry.scope.value,
                scope_id=entry.scope_id,
            ),
            (revised,),
        )

        effect = Effect()
        case = ReconciliationCase(effect_id=effect.id, reason="timeout")
        running = case.start()
        evidence = ReconciliationEvidence(
            case_id=case.id,
            summary="provider lookup",
        )
        reconciliations = PostgresV2ReconciliationRepository(
            self.pool,
            table_prefix="pakstate",
        )
        self.connection.fetchrow_results.extend(
            [
                {"id": str(case.id)},
                {"id": str(case.id)},
                self._row(reconciliation_case_to_document(running)),
                {"id": str(evidence.id)},
            ]
        )
        await reconciliations.save(case, expected_version=None)
        await reconciliations.save(running, expected_version=case.version)
        self.assertEqual(await reconciliations.get_active(effect.id), running)
        await reconciliations.append_evidence(evidence)

        approval = Approval(subject=str(effect.id))
        approved = approval.transition(ApprovalStatus.APPROVED)
        approvals = PostgresV2ApprovalRepository(self.pool, table_prefix="pakstate")
        self.connection.fetchrow_results.extend(
            [
                {"id": str(approval.id)},
                {"id": str(approval.id)},
                self._row(approval_to_document(approved)),
            ]
        )
        self.connection.fetch_results.append([])
        await approvals.add(approval)
        await approvals.save(approved, expected_version=approval.version)
        self.assertEqual(await approvals.get(approval.id), approved)
        self.assertEqual(await approvals.list_pending(), ())

    async def test_lease_fencing_and_audit_paths(self) -> None:
        leases = PostgresV2LeaseRepository(self.pool, table_prefix="paklease")
        worker = WorkerId("worker-a")
        self.connection.fetchrow_results.append({"current_fencing_token": 1})
        token = await leases.next_fencing_token("run:42")
        self.assertEqual(token, FencingToken(1))

        held = Lease(resource="run:42").acquire(worker, token)
        released = held.release()
        self.connection.fetchrow_results.extend(
            [
                {"current_fencing_token": 1},
                {"id": str(held.id)},
                {"id": str(held.id)},
                self._row(lease_to_document(released)),
            ]
        )
        await leases.add(held)
        await leases.save(released, expected_version=held.version)
        self.assertEqual(await leases.get_current(held.resource), released)

        audit = PostgresV2AuditStore(self.pool, table_prefix="paklease")
        event = AuditEvent(event_type="lease.released", subject=held.resource)
        self.connection.fetchrow_results.append({"id": str(event.id)})
        self.connection.fetch_results.append([self._row(audit_to_document(event))])
        await audit.append(event)
        self.assertEqual(await audit.list_for_subject(held.resource), (event,))

    async def test_outbox_and_inbox_paths(self) -> None:
        outbox = PostgresV2OutboxStore(self.pool, table_prefix="pakmsg")
        event = IntegrationEvent(
            name="run.changed",
            aggregate_type="Run",
            aggregate_id="run-42",
        )
        now = datetime.now(UTC)
        self.connection.fetchrow_results.append({"event_id": event.event_id})
        await outbox.append(event)

        self.connection.fetch_results.append(
            [
                {
                    "event_id": event.event_id,
                    "event_json": dumps(integration_event_to_document(event)),
                    "attempt_count": 0,
                    "next_attempt_at": None,
                    "published_at": None,
                    "last_error": None,
                }
            ]
        )
        self.connection.fetchrow_results.append(
            {"attempt_count": 1, "claimed_at": now}
        )
        claimed = await outbox.claim_batch(worker_id="publisher")
        self.assertEqual(claimed[0].status, OutboxStatus.CLAIMED)
        self.assertEqual(claimed[0].attempt_count, 1)

        self.connection.fetchrow_results.extend(
            [
                {"event_id": event.event_id},
                {"event_id": event.event_id},
                {"event_id": event.event_id},
            ]
        )
        await outbox.mark_failed(event.event_id, error="broker unavailable")
        await outbox.release_claim(event.event_id)
        await outbox.mark_published(event.event_id)

        inbox = PostgresV2InboxStore(self.pool, table_prefix="pakmsg")
        record = InboxRecord(
            source="github",
            external_event_id="delivery-42",
            digest="a" * 64,
        )
        self.connection.fetchrow_results.append(
            {"external_event_id": record.external_event_id}
        )
        self.assertTrue(await inbox.reserve(record))

        self.connection.fetchrow_results.append(
            {
                "digest": record.digest,
                "status": InboxStatus.PROCESSED.value,
                "tenant_id": None,
                "processed_at": now,
                "last_error": None,
            }
        )
        stored = await inbox.get(record.source, record.external_event_id)
        self.assertIsNotNone(stored)
        assert stored is not None
        self.assertEqual(stored.status, InboxStatus.PROCESSED)

        self.connection.fetchrow_results.extend(
            [
                {"external_event_id": record.external_event_id},
                {"external_event_id": record.external_event_id},
            ]
        )
        await inbox.mark_processed(record.source, record.external_event_id)
        await inbox.mark_failed(
            record.source,
            record.external_event_id,
            error="handler failure",
        )

    async def test_unit_of_work_shares_connection_and_commits_or_rolls_back(self) -> None:
        run = Run()
        audit_event = AuditEvent(event_type="run.created", subject=str(run.id))
        outbox_event = IntegrationEvent(
            name="run.created",
            aggregate_type="Run",
            aggregate_id=str(run.id),
        )
        self.connection.fetchrow_results.extend(
            [
                {"id": str(run.id)},
                {"id": str(audit_event.id)},
                {"event_id": outbox_event.event_id},
            ]
        )
        uow = PostgresV2UnitOfWork(self.pool, table_prefix="pakuow")
        async with uow:
            await uow.runs.add(run)
            await uow.audit.append(audit_event)
            await uow.outbox.append(outbox_event)
            await uow.commit()

        commands = [query for query, _ in self.connection.executed]
        self.assertIn("BEGIN", commands)
        self.assertIn("COMMIT", commands)

        rollback_pool = ScriptedPostgresPool()
        rollback_uow = PostgresV2UnitOfWork(
            rollback_pool,
            table_prefix="pakrollback",
        )
        rollback_pool.connection.fetchrow_results.append({"id": str(run.id)})
        with self.assertRaisesRegex(RuntimeError, "boom"):
            async with rollback_uow:
                await rollback_uow.runs.add(run)
                raise RuntimeError("boom")
        rollback_commands = [query for query, _ in rollback_pool.connection.executed]
        self.assertIn("ROLLBACK", rollback_commands)


if __name__ == "__main__":
    unittest.main()
