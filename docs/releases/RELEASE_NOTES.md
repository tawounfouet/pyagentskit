# PyAgentsKit 1.6.0 — Distributed Operations & Production Qualification

PyAgentsKit 1.6.0 adds bounded worker admission, readiness, non-cancelling graceful drain,
payload-free operational metrics/audit/traces, real process crash qualification and an opt-in
two-worker PostgreSQL takeover test. The mono-agent, no-scheduler and no-effect-replay boundaries
remain unchanged.

See `V1_6_RELEASE_NOTES.md`, `../qualification/V1_6_QUALIFICATION.md`, `../compatibility/V1_6_API_COMPATIBILITY.md`,
`../compatibility/V1_6_OPERATIONS_MATRIX.md` and `../audits/AUDIT_V1_6.md`.

## Historical 1.5.0 notes

# PyAgentsKit 1.5.0 — Distributed Durable Execution

PyAgentsKit 1.5.0 composes `DurableRunner` and `LeaseStore` into an explicit distributed execution
boundary with finite renewal, immediate stale-worker shutdown, typed fencing-token propagation
and takeover through the existing recovery plan. No effect is replayed implicitly and the V1 API
freeze remains unchanged.

See `V1_5_RELEASE_NOTES.md`, `../qualification/V1_5_QUALIFICATION.md`, `../compatibility/V1_5_API_COMPATIBILITY.md`,
`../compatibility/V1_5_DISTRIBUTED_EXECUTION_MATRIX.md` and `../audits/AUDIT_V1_5.md`.

## Historical 1.4.0 notes

# PyAgentsKit 1.4.0 — Production State Stores

PyAgentsKit 1.4.0 completes the production persistence path with PostgreSQL session, memory and
approval stores, provider-neutral blob storage, S3/Azure artifacts, versioned migrations, RLS SQL
and an explicit SQLite-to-PostgreSQL command. The V1 API freeze remains unchanged.

See `V1_4_RELEASE_NOTES.md`, `../qualification/V1_4_QUALIFICATION.md`, `../compatibility/V1_4_API_COMPATIBILITY.md`,
`../compatibility/V1_4_STORE_COMPATIBILITY.md` and `../audits/AUDIT_V1_4.md`.

## Historical 1.3.0 notes

# PyAgentsKit 1.3.0 — production stores and distributed coordination

PyAgentsKit 1.3.0 adds optional transactional PostgreSQL durable runs and a tenant-scoped lease
port with monotonic fencing tokens. Memory and SQLite implementations remain supported, and the
V1 public API freeze is unchanged.

See `V1_3_RELEASE_NOTES.md`, `../qualification/V1_3_QUALIFICATION.md`, `../compatibility/V1_3_API_COMPATIBILITY.md`,
`../compatibility/V1_3_STORE_COMPATIBILITY.md` and `../audits/AUDIT_V1_3.md`.

## Historical 1.2.0 notes

## PyAgentsKit 1.2.0 - explicit model retries and stream observability

PyAgentsKit 1.2.0 adds disabled-by-default, Runner-owned retry/backoff policies for transient model
failures. Every attempt consumes run limits, streams stop retrying after observable payload, and
tool execution remains outside the retry boundary. Existing model events gain safe attempt and
stream counters without changing the frozen `EventType` vocabulary.

See `V1_2_RELEASE_NOTES.md`, `../qualification/V1_2_QUALIFICATION.md`, `../compatibility/V1_2_API_COMPATIBILITY.md` and
`../audits/AUDIT_V1_2.md`.

## Historical 1.1.0 notes

PyAgentsKit 1.1.0 is an additive stable release. It integrates provider-neutral streaming into
`Runner.run` and adds opt-in, bounded parallel execution for batches made exclusively of
idempotent `PURE`/`READ` tools. All other tools remain sequential, and the V1 public API freeze is
unchanged.

See `V1_1_RELEASE_NOTES.md`, `../qualification/V1_1_QUALIFICATION.md`, `../compatibility/V1_1_API_COMPATIBILITY.md` and
`../audits/AUDIT_V1_1.md`.

## Historical 1.0.0 notes

PyAgentsKit 1.0.0 promotes the complete `0.9.0` API candidate without functional breakage. The
root API, central serialized contracts and provider constructor surfaces are protected by exact
freeze tests. The stable package is release-ready through a reproducible build and trusted
publishing workflow.

The authoritative V1 evidence is in `V1_RELEASE_NOTES.md`, `../qualification/V1_QUALIFICATION.md`,
`../compatibility/V1_API_STABILITY.md`, `../compatibility/V1_COMPATIBILITY_MATRIX.md`, `../audits/V1_SECURITY_AUDIT.md` and `../audits/AUDIT_V1.md`.

## Historical 0.9.0 notes

PyAgentsKit 0.9.0 completes Lot 11 with deterministic evaluations, a dependency-free CLI,
runtime metrics, optional OpenTelemetry integration, reproducible-build enforcement and the final
pre-V1 documentation set. It is compatible with the 0.5.0 runtime and durability baseline.

The authoritative details are in `LOT_11_RELEASE_NOTES.md`, `../qualification/LOT_11_QUALIFICATION.md`,
`../compatibility/LOT_11_API_STABILITY.md`, `../audits/AUDIT_LOT_11.md` and `../planning/MIGRATION_TO_V1.md`.

## Historical 0.5.0 notes

Date: 2026-09-07. Baseline: `0.4.0`.

Lot 10 adds opt-in `DurableRunner`, memory/SQLite `RunStore` implementations, versioned
checkpoints, an append-only analytical journal and fail-closed reconciliation of ambiguous tool
effects. PyWorkflowKit integration is explicitly not included.

See `LOT_10_RELEASE_NOTES.md`, `../qualification/LOT_10_QUALIFICATION.md`, `../compatibility/LOT_10_API_STABILITY.md`,
`../audits/AUDIT_LOT_10.md` and `../verification/CHECK_RESULTS.md`.

## Previous stable milestone

## PyAgentsKit 0.4.0 — guardrails, privacy and Human-in-the-Loop

Date: 2026-09-06. Baseline: `0.3.0`.

Lot 09 adds five fail-closed guardrail boundaries, explicit data egress policy, secret/redaction
helpers, persistent tenant-scoped approvals and single-consumption suspension/resume for sensitive
tool calls. General crash recovery remains deliberately assigned to Lot 10.

See `LOT_09_RELEASE_NOTES.md`, `../qualification/LOT_09_QUALIFICATION.md`, `../compatibility/LOT_09_API_STABILITY.md`,
`../audits/AUDIT_LOT_09.md` and `../verification/CHECK_RESULTS.md`.

## Previous stable milestone

## PyAgentsKit 0.3.0 — sessions, context, memory and artifacts

Date: 2026-09-05. Baseline: `0.2.0`.

Lot 08 adds opt-in tenant-scoped conversation state, memory/SQLite stores, explainable context
selection, external retrieval hooks and integrity-checked artifacts. Stateless Runner behavior and
all six provider adapters remain compatible.

See `LOT_08_RELEASE_NOTES.md`, `../qualification/LOT_08_QUALIFICATION.md`, `../compatibility/LOT_08_API_STABILITY.md`,
`../audits/AUDIT_LOT_08.md` and `../verification/CHECK_RESULTS.md`.

## Previous stable milestone

## PyAgentsKit 0.2.0 — stable OpenRouter adapter

Date: 2026-09-05. Baseline: `0.2.0rc1`.

This stable release freezes the OpenRouter public API for the `0.2.x` line, closes the final RC
audit and publishes an explicit compatibility matrix. No application migration from RC1 is
required. Deterministic protocol, API, runtime and packaging qualification is complete; live
account/model/compliance/fallback tests remain opt-in and were not run.

See `OPENROUTER_STABLE_RELEASE_NOTES.md`, `../audits/AUDIT_OPENROUTER_RC1.md`,
`../compatibility/OPENROUTER_API_STABILITY.md`, `../compatibility/OPENROUTER_COMPATIBILITY_MATRIX.md` and `../verification/CHECK_RESULTS.md`.

## Release candidate history

## PyAgentsKit 0.2.0rc1 — OpenRouter resilience and qualification closure

Date: 2026-09-05. Baseline: `0.2.0b1`.

This release candidate closes the remaining advanced-routing gaps: complete fallback-chain
capability negotiation, terminal SSE route metadata, safe route context on failures, correct typed
HTTP 403 handling, integrity-checked snapshots and a true network-free catalog mode.

All live qualification paths remain explicit opt-ins and were not executed in the release
environment. See `../audits/AUDIT_OPENROUTER_BETA1.md`, `OPENROUTER_RC1_RELEASE_NOTES.md`,
`../qualification/OPENROUTER_RC1_QUALIFICATION.md` and `../verification/CHECK_RESULTS.md`.

## Previous OpenRouter beta

## PyAgentsKit 0.2.0b1 — OpenRouter routing and capabilities

Date: 2026-09-05. Baseline: `0.2.0a1`.

This beta adds explicit routing/data policies, four profiles, provider and model fallback controls,
a TTL-cached `/models` catalog with offline snapshots, conservative capability negotiation and a
safe subset of stable router metadata. It refuses local HTTP retries when OpenRouter fallback is
active.

All qualification is offline with HTTP fixtures. No authenticated or billable call was made. See
`OPENROUTER_BETA1_RELEASE_NOTES.md`, `../qualification/OPENROUTER_ADVANCED_QUALIFICATION.md` and
`../verification/CHECK_RESULTS.md`.

## Previous OpenRouter milestone

## PyAgentsKit 0.2.0a1 — OpenRouter minimal

Date: 2026-09-05. Baseline: stable `0.1.0`.

This alpha adds a distinct deterministic `OpenRouterModel` with text/image messages, client tools,
strict structured output, SSE streaming, normalized usage/cost, requested/resolved model identity,
upstream provider metadata and stable typed-error preservation. Provider endpoint fallbacks are
disabled and required-parameter enforcement is enabled by default.

No model fallback list, provider ordering, remote catalog, plugin or ZDR policy is exposed yet.
Those are deliberately deferred to `0.2.0b1` and `0.2.0rc1`.

The contract suite is offline. The live OpenRouter smoke test remained skipped because no
`OPENROUTER_API_KEY` was configured, so no authenticated or billable request was made. See
`OPENROUTER_ALPHA1_RELEASE_NOTES.md`, `../qualification/OPENROUTER_QUALIFICATION.md` and `../verification/CHECK_RESULTS.md`.

## Stable baseline history

## PyAgentsKit 0.1.0 — Stable mono-agent provider foundation

Date: 2026-09-05. Baseline: cumulative `0.1.0rc2`.

The first stable pre-1.0 release completes the bounded mono-agent runtime, typed tools,
structured events, deterministic `FakeModel`, and the OpenAI, Anthropic, Google Gemini, xAI and
Ollama adapters. The RC2 audit corrected provider/model preflight checks, exact budget semantics,
exhausted-budget handling, model identity traces, HTTP 408 normalization and resource lifecycle.

All offline tests, strict typing, formatting, linting, package checks and isolated wheel smoke tests
must pass through `python scripts/release_check.py`. The five provider adapters are contract-qualified
against mocked HTTP transports. Live provider execution was unavailable for this build and is not
claimed. See `../qualification/PROVIDER_QUALIFICATION.md`, `../audits/AUDIT_RC2.md` and `../verification/CHECK_RESULTS.md`.

## Release candidate history

## PyAgentsKit 0.1.0rc2 — Five explicit provider adapters

Date: 2026-09-05. Cumulative release based on 0.1.0rc1.

Added AnthropicModel (native Messages), GoogleModel (native Gemini generateContent),
XAIModel (Chat Completions compatible) and OllamaModel (native /api/chat).
See [provider guide and capability matrix](../guides/PROVIDERS.md) and ../verification/CHECK_RESULTS.md.
HTTPX remains optional; install a single provider extra or `.[providers]`.

All five expose generate and real incremental streaming (SSE or NDJSON), tools, normalized usage
and errors. Google and Anthropic opaque history is preserved for tool continuation.
Native providers are text-only in this RC; unsupported modalities fail before networking.
Gemini tools plus output_schema in the same request is explicitly rejected in this RC.
Gemini uses generateContent, not the newer Interactions API. Anthropic cloud-hosted variants
(Bedrock/Vertex) are not implemented. Ollama targets a user-managed loopback service by default;
model installation/server startup are not performed. No automatic capability discovery.

Regressions fixed in rc2: streamed OpenAI refusals, malformed native response normalization,
Google native call IDs, and preservation of identical distinct Ollama tool calls.

Real provider tests were NOT run. Included tests use hand-authored documented protocol fixtures,
not captured production responses. They validate mapping and transport behavior, not account access
or actual model quality/capability. Production acceptance still requires the opt-in smoke tests.

## Earlier milestone retained below

## PyAgentsKit 0.1.0rc1 — Consolidation and OpenAI

Date: 2026-09-05. Baseline: 0.1.0b1. Deliverable: source + wheel + sdist + tests.

## Implemented

- Typed Message.tool_calls, assistant tool-only messages, preservation through Runner history.
- Model-request failure events and sanitized exception classification on failed runs.
- Output-token remainder forwarded to adapters; existing reported-usage checks remain active.
- Executor refuses approval-required tools, validates timeouts and includes concurrency queue wait.
- OpenAIModel: text/image inputs, tool calls, strict structured output, SSE text/tool/usage events.
- Normalized HTTP/authentication/rate-limit/timeout/response errors and optional bounded retries.
- Stable wire aliases for tool names, including qualified names with dots.
- HTTPX MockTransport tests and separate explicitly opted-in live smoke test.

## Installation and use

```bash
pip install '.[openai]'
pip install -e '.[dev]'
python examples/offline_agent.py
```

```python
from pyagentskit.providers.openai import OpenAIModel

# Select the deployment/model explicitly. OPENAI_API_KEY is read only at construction.
model = OpenAIModel(model="YOUR_MODEL_ID")
# await Runner(model, tools=registry).run(definition, 'Question')
# await model.aclose() when finished; injected HTTP clients stay caller-owned.
```

Live tests are skipped by default. Explicit execution may incur charges:
`PYAGENTSKIT_LIVE_OPENAI=1 PYAGENTSKIT_OPENAI_MODEL=<model> pytest tests/test_openai_provider.py`.
The API key must already be configured. No live test was executed for this delivery.

## Compatibility and limits

- Migrate beta message metadata tool_calls to the typed Message.tool_calls field.
- No provider imports from core; HTTPX is required only when constructing a real adapter.
- Local output validation still requires output_type. For strict provider JSON output, fields
  must be required (nullable where needed). Open dictionaries/optional properties are rejected.
- Provider schemas have supported subsets; unsupported remote schemas yield normalized errors.
- Tool execution remains sequential; cancellation cannot kill an already-running sync thread.
- Runner consumes full responses. Native SSE streaming is exposed separately by model.stream.
- Unknown usage has zero legacy token counters plus usage_reported=false; cost remains unknown.
  Reported budgets are not a hard billing guarantee. No rates/prices are hardcoded.
- No automatic model catalog, fallback, live billing checks, persistence or HITL workflow.
- Core FakeModel concurrency is script order, not per-run branching; concurrent tests use independent
  models or explicitly concurrency-safe adapters. Caller must close owned HTTP resources.

## Validation

Run Ruff, format check, strict Mypy, pytest (coverage gate 90%), build and Twine. The archive contains
../verification/CHECK_RESULTS.md with measured results and SHA256SUMS covering the complete source and dist tree.
Tests are locally executed on Python 3.12; other versions remain CI validation targets.

## Official references consulted

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs)

Next requested release: 0.1.0rc2 adds Anthropic, Google Gemini, xAI and Ollama; OpenRouter remains
planned for 0.2.0. The two RC archives are independent cumulative snapshots.
