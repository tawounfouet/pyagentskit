# PyAgentsKit — post-V1 roadmap

Baseline: `1.0.0` stable. Current milestone: `1.6.0`.

## Delivered in 1.1.0

- Runner-integrated streaming with final response reconstruction;
- bounded parallel execution for explicitly safe tool batches;
- V1 compatibility, security and packaging qualification.

## Delivered in 1.2.0

- explicit Runner-owned model retry/backoff policy;
- typed retry categories and coordinated retry ownership;
- payload-safe attempt and streaming telemetry using the frozen V1 event vocabulary;
- proof that model retries never replay tool effects.

## Delivered in 1.3.0

- tenant-scoped lease port with monotonic fencing tokens;
- memory, SQLite and optional PostgreSQL lease implementations;
- optional transactional PostgreSQL implementation of the frozen durable `RunStore`;
- explicit production qualification boundary with no default network access.

## Delivered in 1.4.0

- PostgreSQL implementations of session, lexical-memory and approval contracts;
- provider-neutral blob port with S3 and Azure Blob artifact stores;
- versioned PostgreSQL migration/RLS assets and explicit SQLite import;
- common local/database contracts and an ephemeral PostgreSQL 16 CI job.

## Delivered in 1.5.0

- explicit `DistributedDurableRunner` and `LeaseStore` coordination;
- bounded renewal and stale-worker cancellation;
- fencing-token propagation to effectful tools and protected-store ports;
- takeover through existing durable reconciliation with no implicit business-effect replay.

## Delivered in 1.6.0

- finite worker admission, readiness and non-cancelling graceful drain;
- safe distributed metrics, audit events and optional OpenTelemetry spans;
- real process crash/suspension tests and two-worker PostgreSQL qualification;
- operational runbook, performance gate and Kubernetes integration template.

## Candidate next milestones

| Version | Candidate scope | Gate |
|---|---|---|
| 1.1.x | Defect fixes only | No behavior expansion |
| 1.4.x | Defect fixes and production-store hardening | No contract breakage |
| 1.5.x | Defect fixes and distributed-runtime hardening | No contract breakage |
| 1.6.x | Defect fixes and production-operations hardening | No contract breakage |
| 2.0.0 | Only changes requiring contract breakage | Migration guide and deprecation cycle |

Multi-agent orchestration, a workflow engine, arbitrary code execution and a hosted control plane
remain outside this roadmap unless a separate architectural decision changes the project boundary.
