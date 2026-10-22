# PyAgentsKit 1.5.0 — Distributed Durable Execution

Release date: 2026-09-10

PyAgentsKit 1.5.0 connects the durable runner to the fenced lease port introduced in 1.3.0. The
release remains mono-agent and adds worker ownership, heartbeat and takeover semantics without
adding scheduling or implicit effect retries.

## Added

- `DistributedDurableRunner` composition over `DurableRunner` and `LeaseStore`;
- finite `DistributedExecutionPolicy` for TTL, interval and maximum renewal count;
- immediate stale-worker cancellation on renewal loss;
- current-lease checks before effect planning and before durable acknowledgement;
- typed `FencingToken` propagation through tool `RunContext`;
- `FencedOperationStore` reference port for atomic token-check-and-write implementations;
- explicit `resume()` and `resume_approval()` takeover paths;
- deterministic crash, pause, expiry, takeover and split-brain qualification;
- an offline end-to-end example and deployment guide.

## Safety and compatibility

- acquisition and renewal failures never retry a complete run;
- a stale worker cannot start a newly planned durable effect;
- a possibly applied effect becomes `UNKNOWN_EFFECT` and is never replayed implicitly;
- the protected resource must enforce the fencing token atomically;
- the exact 155-name root API and 28-value event vocabulary remain unchanged;
- all new contracts are imported from `pyagentskit.distributed`.
