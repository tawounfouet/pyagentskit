# Audit — PyAgentsKit 1.5.0 Distributed Durable Execution

Audit date: 2026-09-10

## Conclusion

The release safely composes leases and durable effects. Ownership is tenant-scoped, renewal is
finite, stale detection cancels the active operation, and the tool policy checks authority before
the durable effect is planned. The second check prevents a stale worker from acknowledging a
completed effect. Ambiguity remains explicit and blocks takeover replay.

## Controls reviewed

- deterministic run-resource derivation and unique worker-incarnation owner IDs;
- single-shot acquisition with no hidden wait/retry loop;
- positive finite TTL/interval and interval strictly below TTL;
- mandatory finite maximum renewal count;
- stale renewal converted to a typed lease-loss failure;
- fencing policy ordered before durable plan/start transitions;
- copied caller metadata and validated typed token extraction;
- tenant/resource/owner/lease identity retained in the token document;
- normal completion and HITL pause release ownership;
- takeover cannot bypass `DurableRunner.recovery_plan()`;
- stale tokens rejected by the protected-store qualification fixture;
- no root API, provider contract, event enum or durable schema expansion.

## Residual deployment risks

- event-loop starvation may consume the heartbeat margin; operators must size TTL from measured
  worst-case pauses and database latency;
- process suspension cannot be detected until execution resumes, so target-side fencing remains
  mandatory;
- external APIs that cannot atomically fence require an application gateway or manual ambiguity
  reconciliation;
- lease/database unavailability is fail-closed and requires orchestration outside PyAgentsKit;
- queue delivery, worker health, assignment, autoscaling and backpressure remain external;
- fencing-token retention and disaster recovery of the lease counter must match the run journal;
- cancellation cannot prove whether in-flight third-party code committed an effect.
