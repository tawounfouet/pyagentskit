"""Minimal PyAgentsKit V2 Effect + Recovery example."""

from datetime import UTC, datetime, timedelta

from pyagentskit.domain import (
    Effect,
    EffectKind,
    FencingToken,
    LeaseId,
    NextAction,
    OwnershipContext,
    RecoveryContext,
    RecoveryPlanner,
    ResourceIdentity,
    Run,
    RunStatus,
    WorkerId,
)

run = Run().transition(RunStatus.RUNNING)
ownership = OwnershipContext(
    worker_id=WorkerId("worker-demo"),
    lease_id=LeaseId("lease-demo"),
    resource_identity=ResourceIdentity("run", str(run.id)),
    fencing_token=FencingToken(1),
    expires_at=datetime.now(UTC) + timedelta(minutes=1),
)

# Represents W3/W4: the external call may have happened, but local truth is ambiguous.
effect = Effect(
    run_id=run.id,
    kind=EffectKind("demo.external_write"),
).begin(ownership=ownership, protected=True).mark_unknown()

context = RecoveryContext(
    run=run,
    effects=(effect,),
    ownership=ownership,
    current_worker_id=ownership.worker_id,
    now=datetime.now(UTC),
)

plan = RecoveryPlanner().plan(context)

assert plan.next_action is NextAction.RECONCILE_EFFECT
print(plan.next_action.value)
