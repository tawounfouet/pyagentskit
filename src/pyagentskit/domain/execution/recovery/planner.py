"""Pure deterministic RecoveryPlanner."""

from __future__ import annotations

from ...lifecycle import ApprovalStatus, RuntimeCapability
from ...shared import EffectId, ReconciliationCaseId, RuntimeInvocationId
from .model import (
    NextAction,
    RecoveryBlocker,
    RecoveryBlockerType,
    RecoveryContext,
    RecoveryPlan,
)


class RecoveryPlanner:
    """Map authoritative canonical state to exactly one safe next action."""

    def plan(self, context: RecoveryContext) -> RecoveryPlan:
        if context.run.status.is_terminal:
            return self._plan(context, NextAction.NO_ACTION, "run is already terminal")

        if context.authority_required and not context.ownership_is_valid():
            return self._plan(
                context,
                NextAction.ACQUIRE_LEASE,
                "authoritative execution requires a valid ownership generation",
                blockers=(
                    RecoveryBlocker(
                        RecoveryBlockerType.NO_VALID_LEASE,
                        "no valid lease is held by the current worker",
                    ),
                ),
            )

        if not context.security.valid:
            return self._plan(
                context,
                NextAction.MANUAL_INTERVENTION,
                context.security.reason or "security authority is not valid",
                blockers=(
                    RecoveryBlocker(
                        RecoveryBlockerType.UNAUTHORIZED,
                        context.security.reason or "security revalidation failed",
                    ),
                ),
            )

        unresolved = sorted(context.unresolved_effects(), key=lambda item: str(item.id))
        if unresolved:
            effect = unresolved[0]
            case = next(
                (
                    item
                    for item in context.reconciliation_cases
                    if item.effect_id == effect.id and not item.resolved
                ),
                None,
            )
            if case is not None and case.status.value == "manual_review":
                return self._plan(
                    context,
                    NextAction.MANUAL_INTERVENTION,
                    "effect reconciliation requires operator evidence",
                    blockers=(
                        RecoveryBlocker(
                            RecoveryBlockerType.UNKNOWN_EFFECT,
                            "external effect outcome is unresolved",
                            str(effect.id),
                        ),
                        RecoveryBlocker(
                            RecoveryBlockerType.MANUAL_POLICY_BLOCK,
                            "reconciliation entered manual review",
                            str(case.id),
                        ),
                    ),
                    target_effect_id=effect.id,
                    target_reconciliation_case_id=case.id,
                )
            return self._plan(
                context,
                NextAction.RECONCILE_EFFECT,
                "external effect outcome must be established before runtime progress",
                blockers=(
                    RecoveryBlocker(
                        RecoveryBlockerType.UNKNOWN_EFFECT,
                        "effect is started/unknown or awaiting reconciliation",
                        str(effect.id),
                    ),
                ),
                target_effect_id=effect.id,
                target_reconciliation_case_id=None if case is None else case.id,
            )

        pending = sorted(context.pending_approvals(), key=lambda item: str(item.id))
        if pending:
            approval = pending[0]
            return self._plan(
                context,
                NextAction.WAIT_FOR_APPROVAL,
                "a protected future action is waiting for approval",
                blockers=(
                    RecoveryBlocker(
                        RecoveryBlockerType.PENDING_APPROVAL,
                        "approval is still pending",
                        str(approval.id),
                    ),
                ),
            )

        invalid_approval = next(
            (
                item
                for item in context.approvals
                if item.status
                in {
                    ApprovalStatus.REJECTED,
                    ApprovalStatus.EXPIRED,
                    ApprovalStatus.CANCELLED,
                }
            ),
            None,
        )
        if invalid_approval is not None:
            blocker_type = (
                RecoveryBlockerType.EXPIRED_APPROVAL
                if invalid_approval.status is ApprovalStatus.EXPIRED
                else RecoveryBlockerType.MANUAL_POLICY_BLOCK
            )
            return self._plan(
                context,
                NextAction.MANUAL_INTERVENTION,
                "required approval is no longer valid",
                blockers=(
                    RecoveryBlocker(
                        blocker_type,
                        f"approval is {invalid_approval.status.value}",
                        str(invalid_approval.id),
                    ),
                ),
            )

        snapshot = context.runtime_snapshot
        if snapshot is not None and snapshot.resumable:
            invocation_id = (
                None
                if context.latest_runtime_invocation is None
                else context.latest_runtime_invocation.id
            )
            return self._plan(
                context,
                NextAction.RESUME_RUNTIME,
                "runtime invocation is resumable and external effects are authoritative",
                required_capabilities=frozenset({RuntimeCapability.RESUME}),
                target_runtime_invocation_id=invocation_id,
            )

        if snapshot is not None and snapshot.restart_safe:
            return self._plan(
                context,
                NextAction.RESTART_RUNTIME,
                "runtime cannot resume but restart is safe from durable effect state",
                required_capabilities=frozenset({RuntimeCapability.START}),
            )

        if context.completion_ready:
            return self._plan(
                context,
                NextAction.COMPLETE_RUN,
                "all durable completion conditions are satisfied",
            )

        if context.known_irrecoverable_failure:
            return self._plan(
                context,
                NextAction.FAIL_RUN,
                "authoritative state proves an irrecoverable failure",
            )

        blocker = RecoveryBlocker(
            RecoveryBlockerType.RUNTIME_NOT_RESUMABLE,
            "no safe automatic runtime recovery path is available",
        )
        if snapshot is not None and snapshot.status.value == "unknown":
            blocker = RecoveryBlocker(
                RecoveryBlockerType.RUNTIME_STATE_UNKNOWN,
                "runtime state is unknown",
            )
        return self._plan(
            context,
            NextAction.MANUAL_INTERVENTION,
            "automation cannot establish a safe next step",
            blockers=(blocker,),
        )

    @staticmethod
    def _plan(
        context: RecoveryContext,
        next_action: NextAction,
        reason: str,
        *,
        blockers: tuple[RecoveryBlocker, ...] = (),
        required_capabilities: frozenset[RuntimeCapability] = frozenset(),
        target_runtime_invocation_id: RuntimeInvocationId | None = None,
        target_effect_id: EffectId | None = None,
        target_reconciliation_case_id: ReconciliationCaseId | None = None,
    ) -> RecoveryPlan:
        ownership = context.ownership if context.ownership_is_valid() else None
        return RecoveryPlan(
            run_id=context.run.id,
            next_action=next_action,
            reason=reason,
            blockers=blockers,
            required_capabilities=required_capabilities,
            target_runtime_invocation_id=target_runtime_invocation_id,
            target_effect_id=target_effect_id,
            target_reconciliation_case_id=target_reconciliation_case_id,
            lease_id=None if ownership is None else ownership.lease_id,
            fencing_token=None if ownership is None else ownership.fencing_token,
            security_policy_version=context.security.policy_version,
        )
