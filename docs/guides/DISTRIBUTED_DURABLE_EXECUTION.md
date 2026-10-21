# Distributed durable execution

PyAgentsKit 1.5.0 composes durable effect journaling and fenced ownership without introducing a
workflow scheduler. Use a shared `PostgresLeaseStore` and `PostgresRunStore` in production; memory
and SQLite remain local implementations for tests and single-host deployments.

```python
from pyagentskit.distributed import DistributedDurableRunner, DistributedExecutionPolicy

worker = DistributedDurableRunner(
    durable_runner,
    lease_store,
    owner_id=worker_incarnation_id,
    policy=DistributedExecutionPolicy(
        lease_ttl_seconds=30,
        renewal_interval_seconds=10,
        max_renewals=360,
    ),
)

result = await worker.run(agent, user_input, context=context)
```

`owner_id` identifies one worker incarnation, not a stable service name. A run resource is
tenant-scoped and deterministic: `durable-run:<run UUID>`.

## Lifecycle guarantees

| Transition | Runtime behavior | Effect behavior |
|---|---|---|
| Acquire conflict | Fail immediately | Nothing starts |
| Healthy heartbeat | Renew before TTL | Run continues |
| Renewal limit | Cancel active run | Started effect becomes unknown |
| Lease loss before tool | Reject before durable plan | No effect record or business write |
| Lease loss during tool | Cancel/fail and stop | Effect is `UNKNOWN_EFFECT` |
| Pause for approval | Return and release lease | No tool effect yet |
| Takeover | New owner gets a larger token | Resume obeys durable recovery plan |

The interval must be finite, positive and shorter than the TTL. `max_renewals` is mandatory and
finite, making the total unattended ownership period bounded by configuration.

## Fencing a protected write

Every effectful tool can recover its typed authority:

```python
from pyagentskit import RunContext, tool
from pyagentskit.distributed import fencing_token_from_context


@tool(risk="external_write")
async def charge(order_id: str, context: RunContext[None]) -> str:
    token = fencing_token_from_context(context)
    return await ledger.apply_fenced(
        operation_id=order_id,
        payload={"state": "charged"},
        fencing_token=token,
    )
```

The protected store must compare `fencing_token.value` against the highest token accepted for the
same tenant/resource and apply the operation in the **same transaction**. Checking first and then
performing an unfenced write has a time-of-check/time-of-use race and is not safe.

The integer is also present as `context.metadata["fencing_token"]`; prefer
`fencing_token_from_context()` because it validates the complete authority document.

## Crash and takeover

After a crash, the lease remains unavailable until expiry. The next worker receives a higher
fencing token and calls `resume()`. If the old worker might have committed an external effect, the
effect journal blocks the resumed run with `UNKNOWN_EFFECT`. An authorized operator must attest
`COMMITTED` or `NOT_APPLIED`; only the latter permits the already-defined controlled recovery path.

There is no automatic retry of acquisition, renewal, model calls, tool calls or complete runs.
Queueing, worker discovery, backpressure and scheduling remain deployment responsibilities.
