"""Canonical recovery decision objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum

from ...effects import Effect, ReconciliationCase
from ...entities import Approval, Run, RuntimeBinding, RuntimeInvocation
from ...errors import StaleRecoveryPlanError
from ...lifecycle import ApprovalStatus, EffectStatus, RuntimeCapability
from ...runtime import RuntimeStatus
from ...shared import (
    EffectId,
    FencingToken,
    LeaseId,
    OwnershipContext,
    ReconciliationCaseId,
    RecoveryDecisionId,
    RunId,
    RuntimeInvocationId,
    WorkerId,
    utc_now,
)


class NextAction(StrEnum):
    NO_ACTION = "no_action"
    ACQUIRE_LEASE = "acquire_lease"
    WAIT_FOR_APPROVAL = "wait_for_approval"
    RECONCILE_EFFECT = "reconcile_effect"
    RESUME_RUNTIME = "resume_runtime"
    RESTART_RUNTIME = "restart_runtime"
    COMPLETE_RUN = "complete_run"
    FAIL_RUN = "fail_run"
    MANUAL_INTERVENTION = "manual_intervention"


class RecoveryBlockerType(StrEnum):
    NO_VALID_LEASE = "no_valid_lease"
    PENDING_APPROVAL = "pending_approval"
    EXPIRED_APPROVAL = "expired_approval"
    UNAUTHORIZED = "unauthorized"
    UNKNOWN_EFFECT = "unknown_effect"
    RECONCILIATION_PENDING = "reconciliation_pending"
    RUNTIME_NOT_RESUMABLE = "runtime_not_resumable"
    RUNTIME_STATE_UNKNOWN = "runtime_state_unknown"
    MISSING_CHECKPOINT = "missing_checkpoint"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"
    MANUAL_POLICY_BLOCK = "manual_policy_block"


class CrashWindow(StrEnum):
    W1_BEFORE_DURABLE_INTENT = "w1_before_durable_intent"
    W2_AFTER_INTENT_BEFORE_SEND = "w2_after_intent_before_send"
    W3_AFTER_SEND_BEFORE_RESPONSE = "w3_after_send_before_response"
    W4_AFTER_RESPONSE_BEFORE_DURABLE_OUTCOME = "w4_after_response_before_durable_outcome"
    W5_AFTER_DURABLE_OUTCOME_BEFORE_PROGRESS = "w5_after_durable_outcome_before_progress"


@dataclass(frozen=True, slots=True)
class RecoveryBlocker:
    type: RecoveryBlockerType
    reason: str
    subject_id: str | None = None

    def __post_init__(self) -> None:
        if not self.reason:
            raise ValueError("recovery blocker reason is required")


@dataclass(frozen=True, slots=True)
class SecuritySnapshot:
    valid: bool = True
    policy_version: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeRecoverySnapshot:
    status: RuntimeStatus
    handle_valid: bool
    capabilities: frozenset[RuntimeCapability] = frozenset()
    checkpoint_available: bool = False
    restart_safe: bool = False
    observed_at: datetime = field(default_factory=utc_now)

    @property
    def resumable(self) -> bool:
        return (
            self.handle_valid
            and RuntimeCapability.RESUME in self.capabilities
            and self.status in {RuntimeStatus.RUNNING, RuntimeStatus.WAITING}
        )


@dataclass(frozen=True, slots=True)
class RecoveryContext:
    run: Run
    effects: tuple[Effect, ...] = ()
    approvals: tuple[Approval, ...] = ()
    reconciliation_cases: tuple[ReconciliationCase, ...] = ()
    runtime_binding: RuntimeBinding | None = None
    latest_runtime_invocation: RuntimeInvocation | None = None
    runtime_snapshot: RuntimeRecoverySnapshot | None = None
    ownership: OwnershipContext | None = None
    current_worker_id: WorkerId | None = None
    security: SecuritySnapshot = field(default_factory=SecuritySnapshot)
    authority_required: bool = True
    completion_ready: bool = False
    known_irrecoverable_failure: bool = False
    now: datetime = field(default_factory=utc_now)

    def ownership_is_valid(self) -> bool:
        if self.ownership is None:
            return False
        if self.ownership.expires_at <= self.now:
            return False
        return not (
            self.current_worker_id is not None
            and self.ownership.worker_id != self.current_worker_id
        )

    def unresolved_effects(self) -> tuple[Effect, ...]:
        return tuple(
            effect
            for effect in self.effects
            if effect.status
            in {
                EffectStatus.STARTED,
                EffectStatus.UNKNOWN,
                EffectStatus.RECONCILIATION_REQUIRED,
            }
        )

    def pending_approvals(self) -> tuple[Approval, ...]:
        return tuple(
            approval for approval in self.approvals if approval.status is ApprovalStatus.PENDING
        )


@dataclass(frozen=True, slots=True)
class RecoveryPlan:
    run_id: RunId
    next_action: NextAction
    reason: str
    decision_id: RecoveryDecisionId = field(
        default_factory=lambda: RecoveryDecisionId.new("recovery")
    )
    blockers: tuple[RecoveryBlocker, ...] = ()
    required_capabilities: frozenset[RuntimeCapability] = frozenset()
    target_runtime_invocation_id: RuntimeInvocationId | None = None
    target_effect_id: EffectId | None = None
    target_reconciliation_case_id: ReconciliationCaseId | None = None
    generated_at: datetime = field(default_factory=utc_now)
    lease_id: LeaseId | None = None
    fencing_token: FencingToken | None = None
    security_policy_version: str | None = None

    def assert_current_ownership(
        self,
        ownership: OwnershipContext | None,
        *,
        now: datetime | None = None,
    ) -> None:
        if self.lease_id is None and self.fencing_token is None:
            return
        if ownership is None:
            raise StaleRecoveryPlanError(
                "recovery plan requires the ownership it was planned under"
            )
        effective_now = now or utc_now()
        if ownership.expires_at <= effective_now:
            raise StaleRecoveryPlanError("recovery plan ownership has expired")
        if ownership.lease_id != self.lease_id or ownership.fencing_token != self.fencing_token:
            raise StaleRecoveryPlanError("recovery plan ownership generation is stale")
