# Security policy

## Supported versions

The latest stable `1.x` minor line receives security fixes. Pre-releases are supported only until
the next pre-release or stable release is published. Older lines receive fixes only when announced.

## Reporting a vulnerability

Do not disclose vulnerabilities in public issues. Use the private security reporting feature of
the project repository when available, and include:

- the affected version;
- the vulnerable component;
- reproduction steps;
- the potential impact;
- any suggested mitigation.

Never include real provider credentials, customer prompts, personal data or production traces.

## Security principles

- provider credentials are application-owned secrets;
- model output is untrusted input;
- tool arguments must be validated before execution;
- destructive and external-write tools require explicit policies;
- sensitive data must be redacted before logging or tracing;
- arbitrary code execution is excluded from the V1 core.

## OpenRouter boundary

- ZDR and provider allowlists are explicit per-request routing constraints;
- ZDR governs inference endpoints, not third-party plugins or server tools;
- PyAgentsKit does not enable OpenRouter plugins or server-side tools in `0.2.0`;
- catalog snapshots contain no credentials and their checksum detects modification, not origin;
- router summaries, prompts, pipeline payloads and full attempt arrays are excluded from events.

## Session, memory and artifact boundary

- every multi-tenant store operation must carry the same tenant scope used at creation;
- SQLite files, filesystem artifact roots, backups and encryption remain deployment-owned;
- SHA-256 detects artifact modification but does not encrypt data or prove its origin;
- retrieved memory/RAG content is untrusted unless its provenance is application-controlled;
- summarizers and external context sources may have separate network, logging and cost policies;
- expirations require an application-owned `purge_expired()` maintenance schedule;
- cross-store cascade deletion is coordinated but not a distributed transaction.

## Guardrail and approval boundary

- guardrail code is application-owned and every evaluation failure denies progress;
- detailed guardrail reasons are not copied into runtime events or result metadata;
- provider privacy guarantees must come from adapter-owned configuration;
- approvals are tenant-scoped, revisioned, expiring and bound to canonical arguments;
- reviewer identities must be authenticated and authorized by the embedding application;
- a claimed approval cannot be replayed automatically;
- crashes after claim become `unknown_effect` under `DurableRunner` and require explicit
  reconciliation;
- SQLite encryption, backups, access controls and retention remain deployment-owned.

## Durable-run boundary

- effect arguments and results are protected state, not telemetry;
- credential patterns and configured exact secrets are redacted before durable persistence;
- a redacted call cannot be retried from stored arguments;
- `COMMITTED` and `NOT_APPLIED` are operator attestations and require application authorization;
- SQLite is a single-process reference backend, not a distributed lock or lease service;
- session and run-store backup/retention must be coordinated by the deployment;
- analytical replay reads journal entries and never invokes model or tool code.

## Streaming and parallel-tool boundary

- partial stream output is provisional; only the final `RunResult` confirms successful completion;
- stream callbacks are application code and must be non-blocking, bounded and payload-safe;
- malformed, errored, truncated or duplicate-terminal streams fail closed;
- parallel execution is opt-in and limited to batches declared idempotent and `PURE`/`READ`;
- writes, destructive operations, non-idempotent calls and approval-gated effects stay sequential;
- the application owns the accuracy of risk and idempotence declarations;
- `max_parallel_tools` limits task concurrency but does not impose an external service quota.

## Model retry boundary

- retries are disabled unless an application supplies an enabled `ModelRetryPolicy`;
- every model attempt consumes the run call budget and the overall run timeout;
- authentication and response-normalization failures never retry;
- stream transport failures retry only before text, tool or usage payload is observed;
- built-in provider HTTP retries cannot be stacked with Runner retries;
- OpenRouter fallbacks require explicit consent before Runner retries are allowed;
- exception messages, generated text and tool arguments are absent from retry telemetry;
- model retries never wrap or replay tools, approvals, persistence or durable effects.

## Production-store and coordination boundary

- every PostgreSQL key and query is scoped by tenant; deployments should add RLS for defense in depth;
- DSNs and pools are application-owned and never serialized by PyAgentsKit;
- table prefixes are validated before the only identifier interpolation in SQL;
- distributed expiry uses database time, while local stores use their configured process clock;
- lease counters persist after release/expiry so fencing tokens cannot be reused;
- `assert_current()` is advisory against an expiry race: the protected resource must atomically
  reject tokens below the highest value it has accepted;
- schema initialization rejects newer versions and requires deliberately granted DDL permissions;
- database TLS, credentials, statement/lock timeouts, backups, retention and RLS remain
  deployment-owned;
- database failures are not retried automatically and cannot trigger tool-effect replay.
- the SQLite migration command reads DSNs from a named environment variable, validates documents
  before writing and never invokes models or tools;
- RLS scripts are defense in depth and require live testing with the exact non-owner runtime role;
- S3/Azure IAM, encryption keys, retention, legal hold and lifecycle policies remain deployment-owned;
- object metadata and bytes are separate writes; failed metadata creation triggers best-effort byte
  cleanup and operators must monitor for orphan cleanup after process termination.

## Distributed durable execution boundary

- `DistributedDurableRunner` acquires once and never retries a complete run after lease failure;
- heartbeat timing and renewal count are finite; renewal loss cancels active work;
- the lease is checked before effect planning and before durable acknowledgement;
- cancellation cannot revoke an already executing tool or prove whether its remote effect committed;
- every protected resource must atomically compare the supplied fencing token and apply its write;
- a lower token is always stale, including after process suspension or network partition;
- in-flight ambiguity becomes `UNKNOWN_EFFECT` and cannot be resumed without explicit resolution;
- queueing, scheduling, worker discovery and retry policy remain deployment responsibilities.

## Distributed operations boundary

- per-worker admission rejects duplicate runs, saturation and every request after drain starts;
- drain timeout never cancels or resubmits an active effect;
- readiness probe failures expose only a reason code or exception type, never messages or DSNs;
- distributed events contain identifiers and fencing metadata but no model/tool/business payloads;
- observability sinks are best-effort and require independent exporter/audit-gap monitoring;
- JSON Lines audit is a local reference and is not a multi-host compliance store;
- Kubernetes termination, queue consumption and forced replacement remain application-owned;
- real process death and suspension tests do not remove the requirement for target-side fencing.
