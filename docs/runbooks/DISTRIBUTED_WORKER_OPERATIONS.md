# Runbook — distributed PyAgentsKit workers

## Signals

| Signal | Meaning | Immediate action |
|---|---|---|
| Acquisition conflicts rising | Duplicate delivery or slow previous owner | Inspect assignment and lease TTL |
| Renewal latency above 50% interval | Ownership margin is shrinking | Check PostgreSQL and event-loop saturation |
| Lease loss | Worker can no longer start or acknowledge effects | Keep stale worker fenced; inspect run journal |
| `UNKNOWN_EFFECT` | External commit status is ambiguous | Stop automated resume and reconcile manually |
| Drain timeout | Active run exceeded shutdown grace | Keep pod alive if possible; never resubmit blindly |
| Readiness false | Draining, saturated or coordination unavailable | Stop new delivery to the worker |

## Lease loss procedure

1. Confirm that the protected resource rejects fencing tokens lower than its highest accepted token.
2. Identify the run, tenant, old owner, replacement owner and token generation from the audit sink.
3. Inspect the durable recovery plan and every `UNKNOWN` effect.
4. Verify the business system using its own transaction or idempotency identifier.
5. Resolve an effect as `COMMITTED` or `NOT_APPLIED` only with authorized evidence.
6. Resume under a new worker lease; never restart the whole request as a shortcut.

## PostgreSQL outage

- readiness must fail and queue consumption must stop;
- workers unable to renew must stop before new effects;
- do not lower TTL during the incident;
- restore database connectivity and verify monotonic lease counters before resuming admissions;
- investigate exporter and audit gaps separately from effect truth.

## Planned deployment

1. Mark the worker unready and stop external admissions.
2. Call `drain(timeout_seconds=...)` within the platform termination grace.
3. Verify `active_runs == 0` and `state == stopped`.
4. Terminate the process.
5. Start the new revision with a unique owner incarnation ID.

## Evidence to retain

- worker image/version and owner ID;
- run/trace/tenant/resource IDs;
- lease acquisition, renewal, loss, release and takeover events;
- fencing token and revision;
- durable checkpoints and effect resolutions;
- database and platform incident timeline.

Never retain prompt or tool payloads merely to satisfy operational troubleshooting.
