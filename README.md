# PyAgentsKit

[![Release](https://img.shields.io/badge/release-1.6.0-blue)](#release-status)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)

PyAgentsKit is a typed, observable and provider-neutral Python runtime for bounded
mono-agent execution.

> The probabilistic model chooses an action inside an explicit boundary; the runtime
> validates, limits, observes and governs its execution.

## Release status

Version `1.6.0` preserves the stable V1 public API and operationalizes distributed durable
execution with bounded admission, graceful drain, health, audit, metrics and production failure
qualification. The V1 baseline includes:

- immutable Pydantic contracts for agents, messages, models, runs, usage and events;
- typed `@tool` functions with strict arguments, results, policies and timeouts;
- a bounded async mono-agent `Runner` and a safe synchronous facade;
- an opt-in stream callback integrated into the complete model-tool loop;
- opt-in parallel calls limited to idempotent `PURE`/`READ` tools and `max_parallel_tools`;
- disabled-by-default model retries with deterministic bounded exponential backoff;
- attempt-aware model telemetry and payload-safe streaming summaries;
- deterministic offline tests through `FakeModel`;
- structured events with correlation, redaction and local sinks;
- OpenAI, Anthropic, Google Gemini, xAI, Ollama and OpenRouter adapters;
- explicit OpenRouter provider/data policies, model fallbacks and compliance/evaluation profiles;
- cached OpenRouter catalog, offline snapshots and preflight capability negotiation;
- full fallback-chain capability intersection and terminal streaming route metadata;
- normalized tool calls, structured output, streaming, usage and provider errors.
- tenant-scoped memory and SQLite session stores with idempotent optimistic appends;
- explainable full, window and injected-summary context policies;
- lexical memory stores plus an opt-in external retrieval/RAG hook;
- integrity-checked memory and filesystem artifact stores with retention policies;
- optional Runner session reconstruction and large tool-result externalization.
- five guardrail boundaries with normalized allow/transform/retry/approval/reject/abort decisions;
- data classification, provider/model allowlists, ZDR/training guarantees and redaction helpers;
- tenant-scoped memory/SQLite approval stores with fingerprint, expiry and optimistic revisions;
- `WAITING_APPROVAL` suspension and single-consumption approval/rejection resume.
- versioned run checkpoints and append-only analytical journals;
- memory/SQLite `RunStore` implementations and schema migration contract;
- durable tool-effect states with idempotency fingerprints and optimistic revisions;
- explicit `unknown_effect` reconciliation with no silent tool replay;
- restart recovery through `DurableRunner`, including pending approvals.
- deterministic eval datasets, reports and regression gates with advisory model judges;
- dependency-free CLI diagnostics, validation, safe offline runs and checkpoint inspection;
- local runtime metrics and an optional payload-safe OpenTelemetry bridge;
- reproducible distribution checks and a bounded offline runtime benchmark.
- memory/SQLite lease stores and an optional PostgreSQL lease store;
- monotonic fencing tokens, database-time expiry and stale-owner rejection;
- an optional transactional PostgreSQL implementation of the frozen `RunStore` contract.
- PostgreSQL session, lexical-memory and approval stores with common contract tests;
- provider-neutral blob storage with S3 and Azure Blob artifact implementations;
- versioned SQL, opt-in RLS and explicit SQLite-to-PostgreSQL migration.
- `DistributedDurableRunner` coordination with bounded lease renewal and stale-worker shutdown;
- typed fencing tokens for atomic protected-store writes and takeover without implicit effect replay.
- worker admission/readiness/drain controls with no scheduler or queue ownership;
- payload-safe distributed metrics, JSONL audit and optional OpenTelemetry lease spans.

All adapters are contract-qualified with HTTPX request/response objects and official wire
formats. Governance qualification is entirely local and deterministic. See the
[V1 qualification](V1_QUALIFICATION.md),
[evaluation guide](docs/guides/EVALUATIONS.md) and
[V1 API stability contract](V1_API_STABILITY.md).

## Install

```bash
pip install pyagentskit
pip install "pyagentskit[openai]"
pip install "pyagentskit[openrouter]"
pip install "pyagentskit[providers]"
pip install "pyagentskit[postgres]"
pip install "pyagentskit[s3]"
pip install "pyagentskit[azure]"
pip install "pyagentskit[production-stores]"
```

Python 3.11 or newer is required. The core depends only on Pydantic; HTTPX is installed
only by provider extras. Database and object-store SDKs are optional extras.

## Offline quick start

```bash
python examples/offline_agent.py
python examples/session_agent.py
python examples/approval_agent.py
python examples/durable_agent.py
python examples/evaluate_agent.py
python examples/streaming_agent.py
python examples/parallel_tools.py
python examples/retry_agent.py
python examples/distributed_coordination.py
python examples/distributed_durable_agent.py
```

The example runs a complete model-tool-model cycle through `FakeModel`, with no network
connection or API key.

See the [streaming and parallel tools guide](docs/guides/STREAMING_AND_PARALLEL_TOOLS.md)
for the opt-in 1.1.0 features and their safety envelope.
See the [retry and stream observability guide](docs/guides/RETRIES_AND_STREAM_OBSERVABILITY.md)
for the explicit 1.2.0 retry boundary.
See the
[production stores and coordination guide](docs/guides/PRODUCTION_STORES_AND_COORDINATION.md)
for PostgreSQL setup, tenant scoping and mandatory fencing enforcement.
See the
[distributed durable execution guide](docs/guides/DISTRIBUTED_DURABLE_EXECUTION.md)
for bounded heartbeats, stale-worker shutdown and takeover semantics.
See the [distributed operations guide](docs/guides/DISTRIBUTED_OPERATIONS.md) and
[worker runbook](docs/runbooks/DISTRIBUTED_WORKER_OPERATIONS.md) for health, drain and incidents.
See the [production state guide](docs/guides/PRODUCTION_STATE_STORES.md) for PostgreSQL sessions,
memory, approvals, object artifacts, RLS and SQLite migration.

## Provider usage

```python
from pyagentskit.providers.anthropic import AnthropicModel
from pyagentskit.runtime import Runner

async with AnthropicModel(model="YOUR_MODEL_ID") as model:
    result = await Runner(model, tools=registry).run(agent_definition, "Question")
```

Model IDs are supplied by the application. The provider and model declared by
`AgentDefinition.model` must match the injected adapter. Capability declarations describe
an adapter envelope; applications must select and declare capabilities for the concrete
model they deploy.

## Provider matrix

| Adapter | Endpoint family | Tools | Structured output | Streaming |
|---|---|---:|---:|---:|
| OpenAI | Chat Completions | Yes | Yes | SSE |
| Anthropic | Messages | Yes | Yes | SSE |
| Google | Gemini `generateContent` | Yes | Yes | SSE |
| xAI | Chat Completions | Yes | Yes | SSE |
| Ollama | Native `/api/chat` | Yes | Yes | NDJSON |
| OpenRouter | Routed Chat Completions | Yes | Yes | SSE |

These are adapter features, not universal promises for every provider model. Consult the
[provider guide](docs/guides/PROVIDERS.md) before deployment.

## Stable constraints

- Mono-agent execution only.
- Streaming and parallel tools are opt-in; the default execution path remains unchanged.
- Writes, non-idempotent tools and approval-gated calls remain sequential.
- Model retries are opt-in, consume `max_model_calls` and never wrap tool execution.
- Streams never retry after text, tool or usage payload becomes observable.
- Durable runs require a session and are opt-in through `DurableRunner`.
- One approval-gated model response contains one tool call; ambiguous effects require explicit
  `COMMITTED` or `NOT_APPLIED` reconciliation.
- SQLite run durability and lease coordination are local to one host/file; PostgreSQL is required
  for cross-host coordination.
- Bare lease stores only coordinate ownership; the opt-in distributed durable wrapper renews
  within explicit finite bounds and still never schedules work.
- Worker admission and drain remain local controls; queues, assignment and autoscaling are external.
- A protected external resource must atomically reject stale fencing tokens; a lease check alone is
  insufficient.
- PostgreSQL pools, credentials, TLS, RLS, backups and retention remain application-owned.
- S3/Azure clients, credentials, encryption, IAM and lifecycle remain application-owned.
- OpenRouter routing remains explicit; evaluation and legacy defaults disable fallbacks.
- Dynamic catalog data is advisory; integrity-checked offline snapshots are not authenticity
  proofs and never replace deployment-specific live qualification.
- Usage budgets apply to provider-reported usage and are not a guaranteed billing ceiling.
- Remote calls, logs and credentials remain under the embedding application's policy.
- Model judges are advisory; deterministic assertions alone gate a release.
- CLI `run` is an offline smoke path and never loads application tools or provider credentials.

## Quality and release verification

```bash
python scripts/release_check.py
```

The check runs formatting, linting, strict typing, tests with coverage, byte compilation, the
runtime benchmark, reproducible package builds, metadata validation, wheel installation and
offline smoke scenarios. See
[release evidence](CHECK_RESULTS.md),
[1.6 qualification](V1_6_QUALIFICATION.md),
[1.6 audit](AUDIT_V1_6.md) and
[release notes](V1_6_RELEASE_NOTES.md).

## Architecture boundaries

| PyAgentsKit owns | Later or external systems own |
|---|---|
| Agent decisions, checkpoints and effect semantics | Workflow scheduling and workers |
| Typed tools and provider adapters | Business service implementation |
| Validation, events and local limits | Global observability backend |
| Provider-neutral contracts | Secrets, tenant policy and data governance |

See [architecture decisions](docs/adr/README.md),
[public contracts](docs/architecture/CONTRACTS.md), [security policy](SECURITY.md) and
[roadmap](docs/ROADMAP.md).

## License

Apache-2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
