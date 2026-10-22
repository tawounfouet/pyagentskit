from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta

from pyagentskit import AgentDefinition, ModelRef, Runner
from pyagentskit.adapters import NativeRuntimeAdapter, NativeRuntimeEngine
from pyagentskit.application import (
    EffectExecutionGate,
    PlanRecovery,
    ReconcileEffect,
    RuntimeRecoveryExecutor,
)
from pyagentskit.contracts import EffectReservationResult
from pyagentskit.domain import (
    Approval,
    Effect,
    EffectKind,
    EffectRiskLevel,
    EffectStatus,
    EvidenceConfidence,
    EvidenceKind,
    EvidenceSource,
    ExternalReference,
    FencingToken,
    IdempotencyConflictError,
    IdempotencyKey,
    InputFingerprint,
    InvalidTransitionError,
    LeaseId,
    NextAction,
    OwnershipContext,
    ReconciliationCase,
    ReconciliationError,
    ReconciliationEvidence,
    ReconciliationObservation,
    ReconciliationResolution,
    ReconciliationStatus,
    ReconciliationStrategy,
    RecoveryContext,
    RecoveryPlanner,
    ResourceIdentity,
    Run,
    RunStatus,
    RuntimeBinding,
    RuntimeBindingError,
    RuntimeCapability,
    RuntimeHandle,
    RuntimeInvocation,
    RuntimeRecoverySnapshot,
    RuntimeStartRequest,
    RuntimeStatus,
    SecuritySnapshot,
    StaleRecoveryPlanError,
    WorkerId,
)
from pyagentskit.messages import TextContent
from pyagentskit.models import FinishReason, ModelResponse
from pyagentskit.testing import FakeModel


class MemoryEffectRepository:
    def __init__(self, *effects: Effect) -> None:
        self.items = {effect.id: effect for effect in effects}
        self.save_history = []

    async def get(self, effect_id):
        return self.items[effect_id]

    async def reserve(self, effect):
        if effect.idempotency_key is not None:
            existing = await self.find_by_idempotency_key(
                effect.idempotency_scope,
                effect.idempotency_key,
            )
            if existing is not None:
                return EffectReservationResult(effect=existing, created=False)
        existing = self.items.get(effect.id)
        if existing is not None:
            return EffectReservationResult(effect=existing, created=False)
        self.items[effect.id] = effect
        return EffectReservationResult(effect=effect, created=True)

    async def find_by_idempotency_key(self, scope, key):
        for effect in self.items.values():
            if effect.idempotency_scope == scope and effect.idempotency_key == key:
                return effect
        return None

    async def save(self, effect, *, expected_version):
        current = self.items[effect.id]
        if current.version != expected_version:
            raise RuntimeError("effect concurrency conflict")
        self.items[effect.id] = effect
        self.save_history.append(effect.status)


class MemoryReconciliationRepository:
    def __init__(self) -> None:
        self.cases = {}
        self.evidence = []

    async def get_active(self, effect_id):
        for case in self.cases.values():
            if case.effect_id == effect_id and not case.resolved:
                return case
        return None

    async def save(self, case, *, expected_version):
        current = self.cases.get(case.id)
        if expected_version is None:
            if current is not None:
                raise RuntimeError("reconciliation already exists")
        elif current is None or current.version != expected_version:
            raise RuntimeError("reconciliation concurrency conflict")
        self.cases[case.id] = case

    async def append_evidence(self, evidence):
        self.evidence.append(evidence)


class MemoryAuditSink:
    def __init__(self) -> None:
        self.events = []

    async def append(self, event):
        self.events.append(event)


class StaticReconciliationPort:
    def __init__(self, observation: ReconciliationObservation) -> None:
        self.observation = observation
        self.calls = 0

    async def reconcile(self, effect, case):
        self.calls += 1
        return self.observation


def running_run() -> Run:
    return Run().transition(RunStatus.RUNNING)


def ownership_for(run: Run, *, token: int = 1, worker: str = "worker-a") -> OwnershipContext:
    return OwnershipContext(
        worker_id=WorkerId(worker),
        lease_id=LeaseId("lease-a"),
        resource_identity=ResourceIdentity("run", str(run.id)),
        fencing_token=FencingToken(token),
        expires_at=datetime.now(UTC) + timedelta(minutes=5),
    )


def recovery_context(
    *,
    run: Run | None = None,
    effects: tuple[Effect, ...] = (),
    approvals: tuple[Approval, ...] = (),
    cases: tuple[ReconciliationCase, ...] = (),
    snapshot: RuntimeRecoverySnapshot | None = None,
    security: SecuritySnapshot | None = None,
    runtime_binding: RuntimeBinding | None = None,
    completion_ready: bool = False,
    known_failure: bool = False,
    authority_required: bool = True,
) -> RecoveryContext:
    current = run or running_run()
    ownership = ownership_for(current)
    binding = runtime_binding or RuntimeBinding(
        run_id=current.id,
        runtime_id="test/runtime@1",
        runtime_family="test",
    )
    invocation = RuntimeInvocation(
        run_id=current.id,
        binding_id=binding.id,
        input="recover",
        runtime_id=binding.resolved_runtime_id,
        status=RuntimeStatus.WAITING,
    )
    return RecoveryContext(
        run=current,
        effects=effects,
        approvals=approvals,
        reconciliation_cases=cases,
        runtime_binding=binding,
        latest_runtime_invocation=invocation,
        runtime_snapshot=snapshot,
        ownership=ownership,
        current_worker_id=ownership.worker_id,
        security=security or SecuritySnapshot(valid=True, policy_version="policy-1"),
        authority_required=authority_required,
        completion_ready=completion_ready,
        known_irrecoverable_failure=known_failure,
        now=datetime.now(UTC),
    )


class EffectDomainTests(unittest.TestCase):
    def test_effect_idempotency_identity_detects_payload_conflict(self) -> None:
        key = IdempotencyKey("tenant-a", "send-invoice-42")
        effect = Effect(
            kind=EffectKind("erp.create_invoice"),
            idempotency_key=key,
            fingerprint=InputFingerprint.from_text("invoice=42"),
            risk_level=EffectRiskLevel.HIGH,
        )
        effect.assert_same_intent(key, InputFingerprint.from_text("invoice=42"))

        with self.assertRaises(IdempotencyConflictError):
            effect.assert_same_intent(key, InputFingerprint.from_text("invoice=43"))

    def test_protected_effect_requires_ownership_and_captures_fencing(self) -> None:
        run = running_run()
        effect = Effect(run_id=run.id)
        with self.assertRaises(InvalidTransitionError):
            effect.begin(protected=True)

        owned = effect.begin(ownership=ownership_for(run), protected=True)
        self.assertEqual(owned.status, EffectStatus.STARTED)
        self.assertEqual(owned.fencing_token, FencingToken(1))

    def test_unknown_requires_reconciliation_before_terminal_resolution(self) -> None:
        effect = Effect().begin().mark_unknown()
        self.assertFalse(effect.status.is_terminal)
        self.assertTrue(effect.requires_reconciliation)
        with self.assertRaises(InvalidTransitionError):
            effect.transition(EffectStatus.FAILED)

        pending = effect.open_reconciliation()
        succeeded = pending.reconcile_success(
            external_reference=ExternalReference("provider", "external-1")
        )
        self.assertEqual(succeeded.status, EffectStatus.SUCCEEDED)
        self.assertFalse(succeeded.safe_to_replay)
        self.assertTrue(succeeded.status.is_terminal)

    def test_succeeded_effect_never_replays(self) -> None:
        effect = Effect().begin().mark_succeeded()
        self.assertFalse(effect.safe_to_replay)
        with self.assertRaises(InvalidTransitionError):
            effect.transition(EffectStatus.STARTED)


class ReconciliationDomainTests(unittest.TestCase):
    def test_still_unknown_escalates_to_manual_when_budget_is_exhausted(self) -> None:
        case = ReconciliationCase(
            reason="timeout after send",
            strategy=ReconciliationStrategy.BY_EXTERNAL_ID,
            max_attempts=1,
        ).start()
        case = case.record_result(ReconciliationResolution.STILL_UNKNOWN)

        self.assertEqual(case.status, ReconciliationStatus.MANUAL_REVIEW)
        self.assertFalse(case.resolved)

        resolved = case.record_result(
            ReconciliationResolution.CONFIRMED_SUCCESS,
            detail="operator supplied provider evidence",
        )
        self.assertEqual(resolved.status, ReconciliationStatus.RESOLVED_SUCCESS)
        self.assertTrue(resolved.resolved)

    def test_evidence_is_explicit_and_typed(self) -> None:
        case = ReconciliationCase(reason="ambiguous")
        evidence = ReconciliationEvidence(
            case_id=case.id,
            source=EvidenceSource.PROVIDER_API,
            kind=EvidenceKind.OBJECT_EXISTS,
            summary="provider returned the exact operation id",
            confidence=EvidenceConfidence.AUTHORITATIVE,
        )
        self.assertEqual(evidence.case_id, case.id)
        self.assertEqual(evidence.confidence, EvidenceConfidence.AUTHORITATIVE)


class RecoveryPlannerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RecoveryPlanner()

    def test_all_p0_next_actions_are_reachable(self) -> None:
        no_lease = recovery_context()
        no_lease = RecoveryContext(
            **{
                **{field: getattr(no_lease, field) for field in no_lease.__dataclass_fields__},
                "ownership": None,
            }
        )
        self.assertEqual(self.planner.plan(no_lease).next_action, NextAction.ACQUIRE_LEASE)

        pending = Approval(subject="future-effect")
        self.assertEqual(
            self.planner.plan(recovery_context(approvals=(pending,))).next_action,
            NextAction.WAIT_FOR_APPROVAL,
        )

        ambiguous = Effect().begin().mark_unknown().open_reconciliation()
        self.assertEqual(
            self.planner.plan(recovery_context(effects=(ambiguous,))).next_action,
            NextAction.RECONCILE_EFFECT,
        )

        resumable = RuntimeRecoverySnapshot(
            status=RuntimeStatus.WAITING,
            handle_valid=True,
            capabilities=frozenset({RuntimeCapability.RESUME}),
        )
        self.assertEqual(
            self.planner.plan(recovery_context(snapshot=resumable)).next_action,
            NextAction.RESUME_RUNTIME,
        )

        restartable = RuntimeRecoverySnapshot(
            status=RuntimeStatus.FAILED,
            handle_valid=False,
            capabilities=frozenset({RuntimeCapability.START}),
            restart_safe=True,
        )
        self.assertEqual(
            self.planner.plan(recovery_context(snapshot=restartable)).next_action,
            NextAction.RESTART_RUNTIME,
        )

        self.assertEqual(
            self.planner.plan(recovery_context(completion_ready=True)).next_action,
            NextAction.COMPLETE_RUN,
        )
        self.assertEqual(
            self.planner.plan(recovery_context(known_failure=True)).next_action,
            NextAction.FAIL_RUN,
        )
        self.assertEqual(
            self.planner.plan(
                recovery_context(security=SecuritySnapshot(valid=False, reason="revoked"))
            ).next_action,
            NextAction.MANUAL_INTERVENTION,
        )

    def test_terminal_run_never_resumes(self) -> None:
        terminal = running_run().transition(RunStatus.SUCCEEDED)
        snapshot = RuntimeRecoverySnapshot(
            status=RuntimeStatus.WAITING,
            handle_valid=True,
            capabilities=frozenset({RuntimeCapability.RESUME}),
        )
        plan = self.planner.plan(recovery_context(run=terminal, snapshot=snapshot))
        self.assertEqual(plan.next_action, NextAction.NO_ACTION)

    def test_checkpoint_never_overrides_ambiguous_effect_truth(self) -> None:
        unknown = Effect().begin().mark_unknown().open_reconciliation()
        snapshot = RuntimeRecoverySnapshot(
            status=RuntimeStatus.WAITING,
            handle_valid=True,
            capabilities=frozenset({RuntimeCapability.RESUME}),
            checkpoint_available=True,
        )

        plan = self.planner.plan(
            recovery_context(effects=(unknown,), snapshot=snapshot)
        )

        self.assertEqual(plan.next_action, NextAction.RECONCILE_EFFECT)

    def test_manual_reconciliation_blocks_runtime_progress(self) -> None:
        effect = Effect().begin().mark_unknown().open_reconciliation()
        case = ReconciliationCase(
            effect_id=effect.id,
            reason="ambiguous",
            max_attempts=1,
        ).start()
        case = case.record_result(ReconciliationResolution.STILL_UNKNOWN)
        snapshot = RuntimeRecoverySnapshot(
            status=RuntimeStatus.WAITING,
            handle_valid=True,
            capabilities=frozenset({RuntimeCapability.RESUME}),
        )

        plan = self.planner.plan(
            recovery_context(effects=(effect,), cases=(case,), snapshot=snapshot)
        )
        self.assertEqual(plan.next_action, NextAction.MANUAL_INTERVENTION)

    def test_stale_plan_is_rejected_after_takeover(self) -> None:
        context = recovery_context(
            snapshot=RuntimeRecoverySnapshot(
                status=RuntimeStatus.FAILED,
                handle_valid=False,
                capabilities=frozenset({RuntimeCapability.START}),
                restart_safe=True,
            )
        )
        plan = self.planner.plan(context)
        replacement = OwnershipContext(
            worker_id=WorkerId("worker-b"),
            lease_id=context.ownership.lease_id,
            resource_identity=context.ownership.resource_identity,
            fencing_token=FencingToken(context.ownership.fencing_token.value + 1),
            expires_at=context.ownership.expires_at,
        )

        with self.assertRaises(StaleRecoveryPlanError):
            plan.assert_current_ownership(replacement, now=context.now)


class CrashWindowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.planner = RecoveryPlanner()
        self.restartable = RuntimeRecoverySnapshot(
            status=RuntimeStatus.FAILED,
            handle_valid=False,
            capabilities=frozenset({RuntimeCapability.START}),
            restart_safe=True,
        )

    def test_w1_before_durable_intent_can_restart_pure_work(self) -> None:
        plan = self.planner.plan(recovery_context(snapshot=self.restartable))
        self.assertEqual(plan.next_action, NextAction.RESTART_RUNTIME)

    def test_w2_durable_intent_before_send_can_restart_without_replay(self) -> None:
        intent = Effect()
        plan = self.planner.plan(recovery_context(effects=(intent,), snapshot=self.restartable))
        self.assertEqual(intent.status, EffectStatus.NOT_STARTED)
        self.assertEqual(plan.next_action, NextAction.RESTART_RUNTIME)

    def test_w3_after_send_before_response_requires_reconciliation(self) -> None:
        started = Effect().begin()
        plan = self.planner.plan(recovery_context(effects=(started,), snapshot=self.restartable))
        self.assertEqual(plan.next_action, NextAction.RECONCILE_EFFECT)

    def test_w4_response_before_durable_outcome_requires_reconciliation(self) -> None:
        durable_state_still_started = Effect().begin()
        plan = self.planner.plan(
            recovery_context(effects=(durable_state_still_started,), snapshot=self.restartable)
        )
        self.assertEqual(plan.next_action, NextAction.RECONCILE_EFFECT)

    def test_w5_durable_success_continues_without_replay(self) -> None:
        succeeded = Effect().begin().mark_succeeded()
        resumable = RuntimeRecoverySnapshot(
            status=RuntimeStatus.WAITING,
            handle_valid=True,
            capabilities=frozenset({RuntimeCapability.RESUME}),
        )
        plan = self.planner.plan(recovery_context(effects=(succeeded,), snapshot=resumable))
        self.assertEqual(plan.next_action, NextAction.RESUME_RUNTIME)
        self.assertFalse(succeeded.safe_to_replay)


class EffectExecutionGateTests(unittest.IsolatedAsyncioTestCase):
    async def test_prepare_persists_started_before_external_send(self) -> None:
        run = running_run()
        repo = MemoryEffectRepository()
        audit = MemoryAuditSink()
        gate = EffectExecutionGate(effects=repo, audit=audit)
        effect = Effect(
            run_id=run.id,
            kind=EffectKind("github.git_push"),
            idempotency_key=IdempotencyKey("run", "push-main"),
            fingerprint=InputFingerprint.from_text("sha=abc;ref=main"),
            risk_level=EffectRiskLevel.HIGH,
        )

        prepared = await gate.prepare(
            effect,
            ownership=ownership_for(run),
            protected=True,
        )

        self.assertTrue(prepared.execute)
        self.assertFalse(prepared.reused)
        self.assertEqual(prepared.effect.status, EffectStatus.STARTED)
        self.assertEqual(repo.save_history, [EffectStatus.STARTED])
        self.assertEqual(audit.events[-1].event_type, "effect.started")

    async def test_expired_ownership_cannot_cross_protected_effect_gate(self) -> None:
        run = running_run()
        repo = MemoryEffectRepository()
        gate = EffectExecutionGate(effects=repo, audit=MemoryAuditSink())
        expired = OwnershipContext(
            worker_id=WorkerId("worker-a"),
            lease_id=LeaseId("lease-expired"),
            resource_identity=ResourceIdentity("run", str(run.id)),
            fencing_token=FencingToken(1),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )

        with self.assertRaises(InvalidTransitionError):
            await gate.prepare(
                Effect(run_id=run.id),
                ownership=expired,
                protected=True,
            )

    async def test_existing_succeeded_effect_is_reused_without_replay(self) -> None:
        key = IdempotencyKey("run", "publish-package")
        fingerprint = InputFingerprint.from_text("pkg=pyagentskit;version=2.0.0a3")
        succeeded = (
            Effect(
                idempotency_key=key,
                fingerprint=fingerprint,
            )
            .begin()
            .mark_succeeded()
        )
        repo = MemoryEffectRepository(succeeded)
        gate = EffectExecutionGate(effects=repo, audit=MemoryAuditSink())
        duplicate_intent = Effect(
            idempotency_key=key,
            fingerprint=fingerprint,
        )

        prepared = await gate.prepare(duplicate_intent)

        self.assertFalse(prepared.execute)
        self.assertTrue(prepared.reused)
        self.assertEqual(prepared.effect.id, succeeded.id)
        self.assertEqual(repo.save_history, [])

    async def test_started_effect_is_never_replayed_by_prepare(self) -> None:
        key = IdempotencyKey("run", "send-email")
        fingerprint = InputFingerprint.from_text("recipient=a@example.test")
        started = Effect(idempotency_key=key, fingerprint=fingerprint).begin()
        repo = MemoryEffectRepository(started)
        gate = EffectExecutionGate(effects=repo, audit=MemoryAuditSink())

        with self.assertRaises(ReconciliationError):
            await gate.prepare(Effect(idempotency_key=key, fingerprint=fingerprint))

    async def test_missing_response_is_persisted_as_unknown_not_failed(self) -> None:
        repo = MemoryEffectRepository()
        audit = MemoryAuditSink()
        gate = EffectExecutionGate(effects=repo, audit=audit)
        prepared = await gate.prepare(Effect())

        unknown = await gate.mark_unknown(
            prepared.effect,
            reason="timeout after external send",
        )

        self.assertEqual(unknown.status, EffectStatus.UNKNOWN)
        self.assertNotEqual(unknown.status, EffectStatus.FAILED)
        self.assertEqual(repo.save_history[-1], EffectStatus.UNKNOWN)
        self.assertEqual(audit.events[-1].event_type, "effect.outcome_unknown")


class ReconciliationApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_confirmed_success_updates_effect_without_resend_and_audits(self) -> None:
        effect = Effect().begin().mark_unknown()
        effects = MemoryEffectRepository(effect)
        reconciliations = MemoryReconciliationRepository()
        audit = MemoryAuditSink()
        port = StaticReconciliationPort(
            ReconciliationObservation(
                resolution=ReconciliationResolution.CONFIRMED_SUCCESS,
                evidence=(
                    ReconciliationEvidence(
                        source=EvidenceSource.PROVIDER_API,
                        kind=EvidenceKind.OBJECT_EXISTS,
                        summary="exact provider operation found",
                        confidence=EvidenceConfidence.AUTHORITATIVE,
                    ),
                ),
                external_reference=ExternalReference("provider", "op-123"),
            )
        )
        service = ReconcileEffect(
            effects=effects,
            reconciliations=reconciliations,
            port=port,
            audit=audit,
        )

        result = await service.execute(
            effect.id,
            strategy=ReconciliationStrategy.BY_EXTERNAL_ID,
        )

        self.assertEqual(result.effect.status, EffectStatus.SUCCEEDED)
        self.assertEqual(result.case.status, ReconciliationStatus.RESOLVED_SUCCESS)
        self.assertEqual(port.calls, 1)
        self.assertEqual(len(reconciliations.evidence), 1)
        self.assertEqual(audit.events[-1].event_type, "effect.reconciliation_decided")

    async def test_still_unknown_never_becomes_failed_and_escalates_manual(self) -> None:
        effect = Effect().begin().mark_unknown()
        effects = MemoryEffectRepository(effect)
        reconciliations = MemoryReconciliationRepository()
        audit = MemoryAuditSink()
        service = ReconcileEffect(
            effects=effects,
            reconciliations=reconciliations,
            port=StaticReconciliationPort(
                ReconciliationObservation(
                    resolution=ReconciliationResolution.STILL_UNKNOWN,
                    detail="provider unavailable",
                )
            ),
            audit=audit,
        )

        result = await service.execute(effect.id, max_attempts=1)

        self.assertEqual(result.effect.status, EffectStatus.RECONCILIATION_REQUIRED)
        self.assertNotEqual(result.effect.status, EffectStatus.FAILED)
        self.assertEqual(result.case.status, ReconciliationStatus.MANUAL_REVIEW)


class FlagshipRecoveryScenarioTests(unittest.IsolatedAsyncioTestCase):
    async def test_timeout_crash_takeover_reconcile_then_resume_without_resend(self) -> None:
        run = running_run()
        worker_a = ownership_for(run, token=1, worker="worker-a")
        repo = MemoryEffectRepository()
        audit = MemoryAuditSink()
        gate = EffectExecutionGate(effects=repo, audit=audit)
        effect = Effect(
            run_id=run.id,
            kind=EffectKind("provider.create_resource"),
            idempotency_key=IdempotencyKey("run", "create-resource-42"),
            fingerprint=InputFingerprint.from_text("resource=42"),
            risk_level=EffectRiskLevel.HIGH,
        )

        prepared = await gate.prepare(effect, ownership=worker_a, protected=True)
        unknown = await gate.mark_unknown(
            prepared.effect,
            reason="timeout after external send",
        )

        worker_b = OwnershipContext(
            worker_id=WorkerId("worker-b"),
            lease_id=LeaseId("lease-b"),
            resource_identity=worker_a.resource_identity,
            fencing_token=FencingToken(2),
            expires_at=datetime.now(UTC) + timedelta(minutes=5),
        )
        planner = RecoveryPlanner()
        after_takeover = RecoveryContext(
            run=run,
            effects=(unknown,),
            ownership=worker_b,
            current_worker_id=worker_b.worker_id,
            security=SecuritySnapshot(valid=True, policy_version="policy-1"),
            now=datetime.now(UTC),
        )
        reconcile_plan = planner.plan(after_takeover)
        self.assertEqual(reconcile_plan.next_action, NextAction.RECONCILE_EFFECT)

        reconciliations = MemoryReconciliationRepository()

        class FlagshipPort:
            calls = 0

            async def reconcile(self, observed_effect, case):
                self.calls += 1
                self.assertions(observed_effect, case)
                return ReconciliationObservation(
                    resolution=ReconciliationResolution.CONFIRMED_SUCCESS,
                    external_reference=ExternalReference("provider", "resource-42"),
                    evidence=(
                        ReconciliationEvidence(
                            case_id=case.id,
                            source=EvidenceSource.PROVIDER_API,
                            kind=EvidenceKind.OBJECT_EXISTS,
                            summary="provider confirms resource-42 exists",
                            confidence=EvidenceConfidence.AUTHORITATIVE,
                        ),
                    ),
                )

            @staticmethod
            def assertions(observed_effect, case):
                if observed_effect.status is not EffectStatus.RECONCILIATION_REQUIRED:
                    raise AssertionError("Effect must be durably marked for reconciliation")
                persisted = reconciliations.cases.get(case.id)
                if persisted is None or persisted.status is not ReconciliationStatus.RUNNING:
                    raise AssertionError(
                        "ReconciliationCase must be durable before provider lookup"
                    )

        port = FlagshipPort()
        reconciler = ReconcileEffect(
            effects=repo,
            reconciliations=reconciliations,
            port=port,
            audit=audit,
        )
        result = await reconciler.execute(
            unknown.id,
            strategy=ReconciliationStrategy.BY_EXTERNAL_ID,
        )

        self.assertEqual(result.effect.status, EffectStatus.SUCCEEDED)
        self.assertEqual(port.calls, 1)
        self.assertEqual(repo.save_history.count(EffectStatus.STARTED), 1)

        resumable = RuntimeRecoverySnapshot(
            status=RuntimeStatus.WAITING,
            handle_valid=True,
            capabilities=frozenset({RuntimeCapability.RESUME}),
        )
        after_reconciliation = RecoveryContext(
            run=run,
            effects=(result.effect,),
            reconciliation_cases=(result.case,),
            runtime_snapshot=resumable,
            ownership=worker_b,
            current_worker_id=worker_b.worker_id,
            security=SecuritySnapshot(valid=True, policy_version="policy-1"),
            now=datetime.now(UTC),
        )
        resume_plan = planner.plan(after_reconciliation)

        self.assertEqual(resume_plan.next_action, NextAction.RESUME_RUNTIME)
        self.assertFalse(result.effect.safe_to_replay)
        self.assertEqual(repo.save_history.count(EffectStatus.STARTED), 1)


class RecoveryApplicationTests(unittest.IsolatedAsyncioTestCase):
    async def test_plan_recovery_emits_audit_decision(self) -> None:
        audit = MemoryAuditSink()
        service = PlanRecovery(planner=RecoveryPlanner(), audit=audit)
        context = recovery_context(
            snapshot=RuntimeRecoverySnapshot(
                status=RuntimeStatus.FAILED,
                handle_valid=False,
                capabilities=frozenset({RuntimeCapability.START}),
                restart_safe=True,
            )
        )

        plan = await service.execute(context)

        self.assertEqual(plan.next_action, NextAction.RESTART_RUNTIME)
        self.assertEqual(audit.events[-1].event_type, "recovery.planned")

    async def test_native_runtime_restart_is_guarded_by_recovery_plan(self) -> None:
        response = ModelResponse(
            id="response-a3",
            model="fake",
            content=(TextContent(text="recovered"),),
            finish_reason=FinishReason.STOP,
        )
        agent = AgentDefinition(
            id="native.recovery",
            version="1.0.0",
            instructions="Return a short answer.",
            model=ModelRef(provider="fake", name="fake"),
        )
        adapter = NativeRuntimeAdapter(NativeRuntimeEngine(Runner(FakeModel([response])), agent))
        audit = MemoryAuditSink()
        planner = RecoveryPlanner()
        executor = RuntimeRecoveryExecutor(planner=planner, audit=audit)
        context = recovery_context(
            snapshot=RuntimeRecoverySnapshot(
                status=RuntimeStatus.FAILED,
                handle_valid=False,
                capabilities=adapter.descriptor.capabilities,
                restart_safe=True,
            ),
            runtime_binding=RuntimeBinding(
                runtime_id=adapter.descriptor.runtime_id,
                runtime_family=adapter.descriptor.runtime_family,
            ),
        )
        plan = planner.plan(context)

        handle = await executor.execute(
            plan,
            context,
            adapter,
            start_request=RuntimeStartRequest(run_id=context.run.id, input="recover"),
        )
        events = [event async for event in adapter.events(handle)]

        self.assertEqual(plan.next_action, NextAction.RESTART_RUNTIME)
        self.assertEqual(events[-1].event_type.value, "runtime.completed")
        self.assertEqual(audit.events[-1].event_type, "recovery.runtime_step_executed")
        await adapter.close()

    async def test_executor_refuses_runtime_different_from_durable_binding(self) -> None:
        class WrongRuntimeAdapter:
            def __init__(self) -> None:
                from pyagentskit.domain import RuntimeDescriptor

                self.descriptor = RuntimeDescriptor(
                    runtime_id="other/runtime@1",
                    display_name="Other",
                    runtime_family="test",
                    adapter_version="1",
                    contract_version="2",
                    capabilities=frozenset({RuntimeCapability.START}),
                )

            async def start(self, request):
                raise AssertionError("mismatched runtime must not start")

            async def resume(self, request):
                raise AssertionError("mismatched runtime must not resume")

        planner = RecoveryPlanner()
        executor = RuntimeRecoveryExecutor(planner=planner, audit=MemoryAuditSink())
        context = recovery_context(
            snapshot=RuntimeRecoverySnapshot(
                status=RuntimeStatus.FAILED,
                handle_valid=False,
                capabilities=frozenset({RuntimeCapability.START}),
                restart_safe=True,
            )
        )
        plan = planner.plan(context)

        with self.assertRaises(RuntimeBindingError):
            await executor.execute(
                plan,
                context,
                WrongRuntimeAdapter(),
                start_request=RuntimeStartRequest(run_id=context.run.id, input="recover"),
            )

    async def test_executor_discards_plan_after_ownership_change(self) -> None:
        class FakeAdapter:
            def __init__(self) -> None:
                from pyagentskit.domain import RuntimeDescriptor

                self.descriptor = RuntimeDescriptor(
                    runtime_id="fake/runtime@1",
                    display_name="Fake",
                    runtime_family="fake",
                    adapter_version="1",
                    contract_version="2",
                    capabilities=frozenset({RuntimeCapability.START}),
                )

            async def start(self, request):
                return RuntimeHandle(self.descriptor.runtime_id, "handle")

            async def resume(self, request):
                return RuntimeHandle(self.descriptor.runtime_id, "handle")

        audit = MemoryAuditSink()
        planner = RecoveryPlanner()
        executor = RuntimeRecoveryExecutor(planner=planner, audit=audit)
        context = recovery_context(
            snapshot=RuntimeRecoverySnapshot(
                status=RuntimeStatus.FAILED,
                handle_valid=False,
                capabilities=frozenset({RuntimeCapability.START}),
                restart_safe=True,
            )
        )
        plan = planner.plan(context)
        stale_context = RecoveryContext(
            run=context.run,
            effects=context.effects,
            approvals=context.approvals,
            reconciliation_cases=context.reconciliation_cases,
            runtime_binding=context.runtime_binding,
            latest_runtime_invocation=context.latest_runtime_invocation,
            runtime_snapshot=context.runtime_snapshot,
            ownership=OwnershipContext(
                worker_id=WorkerId("worker-b"),
                lease_id=context.ownership.lease_id,
                resource_identity=context.ownership.resource_identity,
                fencing_token=FencingToken(context.ownership.fencing_token.value + 1),
                expires_at=context.ownership.expires_at,
            ),
            current_worker_id=WorkerId("worker-b"),
            security=context.security,
            now=context.now,
        )

        with self.assertRaises(StaleRecoveryPlanError):
            await executor.execute(
                plan,
                stale_context,
                FakeAdapter(),
                start_request=RuntimeStartRequest(run_id=context.run.id, input="recover"),
            )


if __name__ == "__main__":
    unittest.main()
