# Changelog

## [2.0.0a2] - 2026-10-22

### Added

- Added the provider-neutral `AgentRuntimeAdapter` contract for start, resume, cancel, status,
  events, checkpoint and close operations.
- Added runtime descriptors, opaque handles, normalized requests/events, qualification levels and
  explicit side-effect control levels.
- Added deterministic capability negotiation with hard required-capability, exact-runtime,
  version, platform and safety checks.
- Added process-local runtime registry with collision detection and stable descriptor ordering.
- Added the `NativeRuntimeEngine`/`NativeRuntimeAdapter` boundary over the V1 `Runner`.
- Added contract tests for native runtime behavior, capability mismatch, exact selection and
  durable binding/invocation separation.

### Changed

- Completed the A1 domain foundation with typed `OwnershipContext`, `ResourceIdentity`,
  `MessageRecipient` and an explicit reconciliation lifecycle.
- Removed Native-specific preference logic from runtime negotiation; operator preference is now
  expressed only through generic runtime IDs.
- Enforced fail-closed runtime-family continuity for durable `RuntimeBinding` snapshots.
- Classified the Native runtime as `BOUNDED` and stopped advertising `TOOL_INTERCEPTION`
  until the V2 protected-effect contract is demonstrated.
- Added property-based domain invariants, recursive architecture checks and a reusable runtime
  adapter contract harness executed by Native and external-fake adapters.
- Restored GitHub Actions qualification across Python 3.11, 3.12 and 3.13 with a true clean-wheel
  installation check.

### Not Included

- External runtime connectors, V2 persistence, complete recovery orchestration and plugin
  discovery remain future milestones.

## [2.0.0a1] - 2026-10-22

### Added

- Added the infrastructure-independent V2 domain boundary and package topology.
- Added typed domain identifiers, aggregate versions, fingerprints, external references and fencing tokens.
- Added P0 domain entities for runs, effects, approvals, leases, workers, conversations, runtimes, artifacts, audit and reconciliation.
- Added explicit V2 lifecycle transitions with terminality and stale fencing protection.
- Added V2 domain invariant and architecture tests without changing the frozen V1 exports.

### Not Included

- PostgreSQL V2 persistence, external runtime adapters, connectors and production qualification remain future milestones.

## [1.6.0] - 2026-09-11

### Added

- Added finite worker admission, health snapshots and non-cancelling graceful drain.
- Added payload-free distributed lifecycle events, metrics, JSONL audit and OpenTelemetry spans.
- Added real multi-process terminate, kill and suspension qualification.
- Added opt-in two-worker PostgreSQL durable takeover, load benchmark, runbook and Kubernetes template.

### Security

- Excluded prompts, tool payloads, credentials and exception messages from operational events.
- Kept observer failures isolated from durable effect truth.
- Preserved `UNKNOWN_EFFECT` and target-side fencing across crash and takeover.
- Preserved all frozen root API, core event, provider and store contracts.

## [1.5.0] - 2026-09-10

### Added

- Added `DistributedDurableRunner` composition over durable runs and fenced leases.
- Added finite periodic renewal, immediate stale-worker cancellation and explicit takeover.
- Added typed fencing-token propagation and a protected-operation store port.
- Added crash, pause, expiry, takeover and split-brain qualification.

### Security

- Refused every new effect after current-lease validation fails.
- Preserved ambiguous in-flight effects as `UNKNOWN_EFFECT` without implicit replay.
- Required target-side atomic fencing to close the lease-expiry race.
- Preserved all frozen V1 root/API/event/provider/store contracts.

## [1.4.0] - 2026-09-09

### Added

- Added PostgreSQL session, lexical-memory and approval stores.
- Added `BlobStore`, S3 and Azure Blob artifact adapters.
- Added versioned PostgreSQL v2/RLS scripts and SQLite migration CLI.
- Added common memory/SQLite/PostgreSQL contracts and PostgreSQL 16 CI qualification.

### Security

- Preserved structural tenant scoping, optimistic transitions and future-schema rejection.
- Kept credentials, SDK clients, pools and live services application-owned and opt-in.
- Migrated durable aggregates without model calls, tool execution or effect replay.
- Preserved all frozen V1 root/API/event/provider contracts.

## [1.3.0] - 2026-09-09

### Added

- Added tenant-scoped `LeaseStore` with memory and SQLite implementations.
- Added monotonic fencing tokens, optimistic renewal and explicit stale-owner rejection.
- Added optional asyncpg-compatible `PostgresLeaseStore` and `PostgresRunStore`.
- Added schema gates, offline pool qualification, a live opt-in test, guide and benchmark.

### Security

- Used database time for distributed lease expiry and tenant scope in every SQL predicate.
- Added safe table-prefix validation and per-run first-write serialization.
- Kept credentials, pools, scheduling and effect retries outside serializable runtime state.
- Preserved the frozen V1 root API, events, providers and core contract layouts.

## [1.2.0] - 2026-09-09

### Added

- Added strict `ModelRetryPolicy` and `ModelRetryReason` in `pyagentskit.retry`.
- Added bounded deterministic backoff for typed transient model failures.
- Added attempt, retry and safe streaming counters to the frozen model event vocabulary.
- Added retry and stream metrics, an offline example and a deterministic benchmark.

### Changed

- `Usage.model_calls` counts every Runner-level provider attempt when retries are enabled.
- `model.request.started` and `model.request.failed` describe actual attempts.

### Security

- Refused automatic retry after observable streaming payload.
- Refused stacked built-in HTTP and Runner retries.
- Kept all tools and durable effects outside the retry boundary.
- Preserved all 155 V1 root exports and the exact 28-value `EventType` enum.

## [1.1.0] - 2026-09-09

### Added

- Added an opt-in `stream_handler` to `Runner.run`, preserving the full bounded agent loop.
- Added opt-in parallel execution for batches containing only idempotent `PURE` or `READ` tools.
- Enforced `RunLimits.max_parallel_tools` while preserving tool-result message order.

### Changed

- Added normalized terminal route metadata to OpenAI-compatible streaming responses.
- Preserved the exact 155-symbol V1 root export surface and all frozen serialized contracts.

### Security

- Writes, non-idempotent tools and approval-gated calls always retain sequential execution.
- Truncated, duplicate-terminal and explicit-error streams fail closed.

## [1.0.0] - 2026-09-08

### Stable

- Froze the 155-symbol root public API and key serialized contract field order.
- Froze direct-provider and OpenRouter constructor parameter names.
- Qualified the complete lots 00–11 feature set as the V1 baseline.
- Added a tag-gated trusted-publishing workflow with no long-lived PyPI token.
- Added final compatibility, security, migration and release evidence.

### Security

- Confirmed fail-closed tools, guardrails, privacy policies, approvals and durable effects.
- Confirmed archive, secret, dependency-integrity and reproducible-build gates.
- Retained all live provider tests as explicit opt-in operations.

There is no functional migration from `0.9.0`; this release stabilizes its API candidate.

## [0.9.0] - 2026-09-08

### Added

- Deterministic evaluation datasets, assertions, reports and regression comparison.
- Advisory model-judge scores that cannot override release-gate results.
- Standard-library CLI for diagnostics, validation, safe offline runs and checkpoint inspection.
- Local runtime metrics and optional OpenTelemetry event bridge.
- Offline runtime benchmark, reproducible-build gate, V1 migration and deprecation policy.

### Changed

- Exported `Runner` intentionally from the package root as part of the V1 API candidate.
- Promoted lots 00–11 to the completed pre-V1 baseline.

### Security

- CLI execution never imports arbitrary application code or invokes a provider.
- OpenTelemetry attributes exclude prompts, tool arguments and arbitrary event payloads.

## [0.5.0] - 2026-09-07

### Added

- Versioned `RunCheckpoint` and provider-neutral `RunStore` contract.
- Memory and SQLite run stores with tenant scope, optimistic transitions and migration metadata.
- Append-only analytical journal and durable tool-effect records.
- `DurableRunner` recovery, `unknown_effect` status and explicit effect reconciliation.
- Redacted durable state, N-1 fixture migration, offline example and qualification evidence.

### Changed

- `ToolExecutor` and `ToolRegistry` expose read-only composition properties for safe wrappers.
- `Runner` has an internal session-resume path used by `DurableRunner`.

### Excluded

- PyWorkflowKit integration and all scheduler/worker/DAG behavior.

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the
project follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.0] - 2026-09-06

### Added

- Added five-stage fail-closed guardrails and normalized policy decisions.
- Added data classification, provider/model egress allowlists and privacy guarantees.
- Added environment secret lookup and recursive redaction helpers.
- Added tenant-scoped memory/SQLite approval stores with expiry and optimistic revisions.
- Added Runner suspension and approval/rejection resume from durable session history.

### Security

- Bound approvals to canonical tool arguments by SHA-256.
- Added atomic claim and single-consumption protection against approval replay.
- Removed detailed guardrail reasons from runtime events and result metadata.
- Required adapter-owned evidence for ZDR and training-exclusion enforcement.

## [0.3.0] - 2026-09-05

### Added

- Added tenant-scoped memory and SQLite session stores with idempotent optimistic appends.
- Added memory and SQLite lexical memory stores plus an opt-in context-source bridge.
- Added full, window and injected-summary context policies with explainable token budgeting.
- Added memory and filesystem artifact stores with SHA-256 verification and retention.
- Added optional Runner session reconstruction and large tool-result externalization.
- Added state lifecycle coordination, API-freeze tests, documentation and offline example.

### Fixed

- Separated UUID-compatible technical IDs from normalized business identifiers.
- Prevented concurrent stale session writers from mixing turns before model execution.
- Rejected idempotency-key reuse when the append payload differs.
- Distinguished missing artifacts from corrupted bytes or metadata.

### Security

- Enforced tenant scope on all session, memory and artifact reads/writes.
- Kept retrieval and summarization explicit; no hidden network or embedding calls are introduced.

## [0.2.0] - 2026-09-05

### Added

- Added a frozen OpenRouter `0.2.x` API contract with explicit module exports and golden tests.
- Added the final RC audit and compatibility matrix separating adapter support from live model
  certification.

### Changed

- Promoted the OpenRouter adapter from release candidate to stable without application migration.
- Declared schema-v1 snapshot reads and schema-v2 reads/writes as patch-line compatibility
  guarantees.

### Security

- Retained the credential-free release boundary and explicit billable live-test gates.
- Documented dynamic catalog, ZDR, cost and upstream-provider boundaries as accepted residual risks.

## [0.2.0rc1] - 2026-09-05

### Added

- Added terminal streaming route metadata and three independently gated live qualification paths.
- Added snapshot schema v2 with model-count and SHA-256 integrity checks.
- Added true network-free catalog construction through `OpenRouterCatalog.from_snapshot(...)`.
- Added safe routing details to normalized model-failure events.

### Changed

- Capability preflight now checks every model in the fallback chain and exposes only their
  intersection to the runtime.
- Evaluation profiles may pin an upstream-provider allowlist.
- Empty catalogs and invalid routing/profile objects now fail closed.

### Fixed

- OpenRouter guardrail and invalid-prompt HTTP 403 responses are no longer misclassified as
  authentication failures.
- Choice-level errors retain sanitized top-level route context.

### Security

- Snapshot integrity detects accidental or untrusted-file modification but is not represented as
  an authenticity signature.
- Raw router summaries, pipelines, prompts and attempt arrays remain excluded from traces.

## [0.2.0b1] - 2026-09-05

### Added

- Added serializable OpenRouter routing/data policies and four explicit profiles.
- Added provider order, allow/ignore lists, ZDR, data-collection constraints and model fallbacks.
- Added dynamic model catalog descriptors, coalesced TTL cache and explicit offline snapshots.
- Added conservative preflight capability negotiation and catalog-based model construction.
- Added sanitized router decision metadata to model results, failures and runtime events.

### Changed

- Opted into the stable `X-OpenRouter-Metadata` response extension by default.
- Refused local HTTP retries whenever server-side OpenRouter fallback is active.

### Security

- Do not retain router summaries, attempt arrays, pipeline data or arbitrary endpoint metadata.
- Compliance profile requires both ZDR and an explicit upstream-provider allowlist.

## [0.2.0a1] - 2026-09-05

### Added

- Added the optional deterministic `OpenRouterModel` adapter.
- Added OpenRouter tool, structured-output, streaming, usage/cost and error normalization.
- Added sanitized provider metadata on `ModelError`.
- Added OpenRouter contract tests, live opt-in smoke test, guide, ADR and qualification report.

### Changed

- Extended the shared HTTP transport with provider-specific error normalization hooks.
- Disabled OpenRouter provider fallback and required parameter support by default.

### Security

- OpenRouter raw error messages and arbitrary upstream metadata are not exposed.
- Live OpenRouter calls remain disabled unless an exact opt-in gate is set.

## [0.1.0] - 2026-09-05

### Added

- Added a reproducible full release-check and stable provider qualification report.
- Added requested/resolved provider and model identity to runtime model events.
- Added async context manager support to every HTTP provider adapter.

### Changed

- Stabilized the bounded mono-agent runtime and all five provider adapters.
- Declared adapter-default capability provenance without claiming model-level verification.
- Standardized live-test opt-in variables while retaining the legacy OpenAI gate.

### Fixed

- Accept exact configured token budgets and reject only actual overruns.
- Prevent a second provider request after the output-token budget is exhausted.
- Reject provider/model configuration mismatches before network access.
- Normalize HTTP 408 as a retryable timeout and reject whitespace-only credentials.
- Preserve resolved model identity and tool-call finish reasons across adapters.

### Security

- Keep provider live tests disabled by default and document the credential-free release boundary.
- Fail closed for unknown tool names, unsupported capabilities and approval-required tools.

## [0.1.0rc2] - 2026-09-05

- Added native Anthropic Messages, Google Gemini and Ollama chat adapters.
- Added explicit xAI Chat Completions adapter and per-provider optional extras.
- Added native streaming, opaque signature/history preservation and protocol regression tests.
- Added streamed refusal detection and defensive malformed-response normalization.
- Live provider tests remain opt-in; no real provider calls executed for this delivery.

## [0.1.0rc1] - 2026-09-05

- Consolidated typed tool history, timeout validation, queue deadlines and approval refusal.
- Added optional OpenAI HTTP adapter, native SSE streaming and mocked protocol regression tests.
- Live tests opt-in; no real provider invocation performed during delivery.

## [0.1.0b1] - 2026-09-05

### Added

- Offline bounded mono-agent Runner, FakeModel, EventBus and local sinks.
- Strict structured output validation, sanitized failures and approval-required tool rejection.
- Beta regression tests and complete offline example.

### Fixed

- Preserve nested Pydantic argument instances passed to function tools.

### Planned

- Mono-agent runtime and deterministic fake model.
- OpenAI reference provider.

## [0.1.0a2] - 2026-09-04

### Added

- Typed `@tool` decorator for synchronous and asynchronous functions.
- Strict Pydantic-derived input schemas and return-value validation.
- Hidden `RunContext` injection for application dependencies.
- `ToolRegistry` with deterministic lookup and explicit replacement.
- `ToolExecutor` with timeouts, cancellation, concurrency limits and normalized errors.
- Before/after policy hooks for future guardrails and approval orchestration.
- Structured start, completion and failure events without argument payload leakage.
- Offline tests and user guide for the complete tool lifecycle.

### Changed

- Package version advanced from `0.1.0a1` to `0.1.0a2`.

### Security

- Synchronous tools execute outside the event-loop thread.
- Untrusted arguments are validated strictly before user code runs.
- Internal exception messages and tool arguments are excluded from public errors and events.

## [0.1.0a1] - 2026-09-04

### Added

- Phase 0 project foundation and quality configuration.
- Provider-neutral model, message, tool, run and event contracts.
- Normalized exception hierarchy.
- Initial architecture decision records.
- Unit and protocol conformance tests.
- Reproducible package metadata compatible with the release-check toolchain.
