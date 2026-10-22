"""Application services around the pure RecoveryPlanner."""

from __future__ import annotations

from ...contracts.audit import AuditSink
from ...domain.entities import AuditEvent
from ...domain.errors import RuntimeCapabilityError, StaleRecoveryPlanError
from ...domain.execution import NextAction, RecoveryContext, RecoveryPlan, RecoveryPlanner
from ...domain.runtime import RuntimeHandle, RuntimeResumeRequest, RuntimeStartRequest
from ..runtime import AgentRuntimeAdapter


class PlanRecovery:
    def __init__(self, *, planner: RecoveryPlanner, audit: AuditSink) -> None:
        self._planner = planner
        self._audit = audit

    async def execute(self, context: RecoveryContext) -> RecoveryPlan:
        plan = self._planner.plan(context)
        await self._audit.append(
            AuditEvent(
                event_type="recovery.planned",
                subject=str(context.run.id),
                metadata=(
                    ("decision_id", str(plan.decision_id)),
                    ("next_action", plan.next_action.value),
                    ("reason", plan.reason),
                ),
            )
        )
        return plan


class RuntimeRecoveryExecutor:
    """Execute one runtime recovery step after revalidating the deterministic plan."""

    def __init__(self, *, planner: RecoveryPlanner, audit: AuditSink) -> None:
        self._planner = planner
        self._audit = audit

    async def execute(
        self,
        plan: RecoveryPlan,
        context: RecoveryContext,
        adapter: AgentRuntimeAdapter,
        *,
        start_request: RuntimeStartRequest | None = None,
        resume_request: RuntimeResumeRequest | None = None,
    ) -> RuntimeHandle:
        current = self._planner.plan(context)
        if (
            current.next_action != plan.next_action
            or current.target_effect_id != plan.target_effect_id
            or current.target_runtime_invocation_id != plan.target_runtime_invocation_id
        ):
            raise StaleRecoveryPlanError("recovery state changed; discard plan and replan")

        plan.assert_current_ownership(context.ownership, now=context.now)
        missing = plan.required_capabilities - adapter.descriptor.capabilities
        if missing:
            missing_names = sorted(item.value for item in missing)
            raise RuntimeCapabilityError(
                f"runtime is missing recovery capabilities: {missing_names}"
            )

        if plan.next_action is NextAction.RESUME_RUNTIME:
            if resume_request is None:
                raise ValueError("resume request is required for RESUME_RUNTIME")
            handle = await adapter.resume(resume_request)
        elif plan.next_action is NextAction.RESTART_RUNTIME:
            if start_request is None:
                raise ValueError("start request is required for RESTART_RUNTIME")
            handle = await adapter.start(start_request)
        else:
            raise ValueError(f"{plan.next_action.value} is not a runtime execution action")

        await self._audit.append(
            AuditEvent(
                event_type="recovery.runtime_step_executed",
                subject=str(plan.run_id),
                metadata=(
                    ("decision_id", str(plan.decision_id)),
                    ("next_action", plan.next_action.value),
                    ("runtime_id", adapter.descriptor.runtime_id),
                ),
            )
        )
        return handle
