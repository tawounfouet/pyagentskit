# PyAgentsKit 1.1.0 — streaming and safe parallel tools

Release date: 2026-09-09

PyAgentsKit 1.1.0 is a backward-compatible post-V1 feature release. Existing applications keep
the complete-response, sequential-tool behavior unless they explicitly opt in.

## Added

- `Runner.run(..., stream_handler=...)` consumes `Model.stream()` inside the normal bounded loop.
- Text deltas, completed tool calls, usage and terminal provider metadata are forwarded while the
  runtime retains validation, guardrails, budgets, sessions, events and final output validation.
- `Runner(..., parallel_tool_calls=True)` may execute a model batch concurrently.
- Parallelism is capped by `RunLimits.max_parallel_tools` and results are appended to model history
  in original call order.

## Safety envelope

Parallel execution requires every call in the batch to reference a declared tool that is both:

- `idempotent=True`; and
- classified as `ToolRisk.PURE` or `ToolRisk.READ`.

If any call falls outside that envelope, the complete batch runs sequentially. Approval-gated calls
suspend before execution, exactly as in 1.0.0. A declaration is an application-owned assertion;
incorrect risk or idempotence metadata cannot be detected by the runtime.

Streaming fails closed when an event is malformed, the provider reports an error, the stream ends
without one terminal event, or multiple terminal events are received.

## Compatibility

- No root export was added or removed: the 155-symbol V1 manifest is unchanged.
- No frozen Pydantic field order, dataclass field order or provider constructor changed.
- Existing `Runner(model, ...)` and `Runner.run(agent, input, ...)` calls behave as before.
- No migration is required from 1.0.0.

## Explicit exclusions

- no multi-agent delegation or workflow scheduling;
- no parallel writes or automatic retry of side effects;
- no synchronous streaming callback;
- no token-level event persistence by default;
- no claim that concurrent tools are transactionally atomic.

