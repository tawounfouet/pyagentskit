# Public contract reference

## Stability

PyAgentsKit `1.0.0` established the stable public API. Version `1.5.0` preserves the names exported by
`pyagentskit.__all__`, the documented provider constructors and the serialized fields frozen by
the V1 contract tests follow semantic versioning. Incompatible changes require a major release.

## Agent definition

`AgentDefinition` is serializable configuration. It references a model through `ModelRef`; it
does not own a provider client or application dependency.

## Messages and content

Messages contain a role and typed content parts. Text, image, audio and document references are
represented without importing provider-specific message classes. Binary content is referenced
by URI instead of being embedded in persisted domain events.

## Model

`Model` is the async provider port. A conforming implementation exposes capabilities and maps a
normalized `ModelRequest` to a normalized `ModelResponse`. Provider metadata may be retained in
the response metadata, but must not alter core types.

`ModelCapabilities` is an explicit declaration. Adapter defaults describe the implemented
protocol envelope and carry `model_verified=false`; they are not proof that every model ID exposed
by a provider supports every feature. Deployments should supply capabilities for their selected
model and fail before networking when agent requirements are incompatible.

## Tools

`ToolDefinition` describes a governed capability. `Tool` is its async execution protocol.
Arguments and results remain untrusted until `ToolExecutor` validates them against the declared
schemas. Tools marked as requiring approval fail closed until an approval workflow is configured.

## Runs

`Runner` is a stable root export. `RunContext` contains identifiers and application dependencies
that are not sent to the model by
default. `RunLimits` makes finite execution the default. `RunResult` represents completion,
failure, cancellation or limit exhaustion without requiring exceptions for normal terminal
states.

`Runner.run(..., stream_handler=...)` is an additive 1.1 option that consumes the same `Model`
stream port inside the bounded loop. `Runner(..., parallel_tool_calls=True)` is also additive and
only permits bounded concurrency for wholly idempotent `PURE`/`READ` batches. The defaults retain
the 1.0 execution behavior.

Version 1.2 adds the keyword-only `retry_policy` composition point. The policy repeats only a model
request, never a tool or complete agent step. It is public from `pyagentskit.retry` so the exact V1
root namespace remains frozen. Existing model event types carry additive attempt and stream-summary
payloads; the 28-value `EventType` enum is unchanged.

## Events

`AgentEvent` is the stable envelope for runtime facts. Events use timezone-aware timestamps and
full UUIDs. Human-readable logs may abbreviate identifiers but persisted events may not.

## Durable runs

`RunStore` persists semantic checkpoints, effect state and a metadata-only analytical journal.
`DurableRunner` composes a session-aware `Runner`; it never changes provider contracts. A started
effect without a committed result becomes `RunStatus.UNKNOWN_EFFECT` and cannot continue until an
authorized application reconciles it. The `1.0.x` contract contains no workflow-engine adapter.

Version 1.3 adds `PostgresRunStore` as an implementation of the unchanged `RunStore` protocol. It
uses tenant-scoped row serialization and the existing optimistic transition logic. Memory and
SQLite implementations remain first-class local options.

Version 1.4 adds PostgreSQL implementations of the unchanged `SessionStore`, `MemoryStore` and
`ApprovalStore` protocols. `BlobStore` is an additive submodule port used by S3 and Azure Blob
implementations of the existing `ArtifactStore`. SQLite migration copies validated state and never
executes durable effects.

## Distributed coordination

`LeaseStore` grants time-bounded tenant-scoped ownership. Every new ownership generation receives
a monotonically increasing fencing token. Memory and SQLite implementations are local references;
`PostgresLeaseStore` uses an asyncpg-compatible pool and database time.

The lease does not execute work or schedule a run. The application must enforce the fencing token
inside every protected external write; `assert_current()` alone cannot close the expiry race.

Version 1.5 adds `DistributedDurableRunner` in `pyagentskit.distributed`. It composes the existing
ports, injects a typed fencing token into tool context, renews ownership within finite bounds and
uses the unchanged durable recovery plan for takeover. The wrapper never infers a business-effect
retry from lease acquisition, expiration, renewal loss or cancellation.

Version 1.6 adds submodule-scoped operational events, metrics, audit/trace sinks and
`DistributedWorkerController`. Admission and drain operate around the unchanged distributed
runner methods. The core `EventType`, root exports and serialized agent/run/store contracts remain
frozen. Operational control does not claim queue delivery, scheduling or autoscaling ownership.

## Security boundary

Model output, tool arguments, tool results and provider metadata are untrusted. Secrets belong to
the host application and must never be included in serializable definitions or event payloads.
