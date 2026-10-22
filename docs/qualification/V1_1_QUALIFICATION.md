# PyAgentsKit 1.1.0 qualification

Qualification is deterministic and network-free. The full evidence is recorded in
`../verification/CHECK_RESULTS.md` after the release-check.

## Feature matrix

| Area | Required evidence |
|---|---|
| Streaming text | Ordered deltas and terminal event produce the final result |
| Streaming tools | A streamed tool call completes a full model-tool-model cycle |
| Streaming capability | Unsupported models are rejected before a request |
| Stream integrity | Truncation, provider error and duplicate completion fail closed |
| Safe parallelism | Idempotent `PURE`/`READ` calls overlap when explicitly enabled |
| Concurrency bound | Peak active calls never exceeds `max_parallel_tools` |
| Determinism | Tool-result messages retain model call order |
| Side effects | Writes and non-idempotent tools remain sequential |
| Compatibility | Frozen V1 root exports and serialized contracts remain unchanged |
| Packaging | Wheel/sdist, reproducible rebuild and installed-wheel smoke tests pass |

## Provider behavior

The Runner consumes the existing provider-neutral `Model.stream` protocol. Native adapters embed
their normalized final response in the terminal event. OpenAI-compatible adapters supply sanitized
provider/model/generation metadata for Runner reconstruction. No provider key or network call is
required by the qualification suite.

Concrete deployed model revisions still require application-owned live qualification. Adapter
streaming support does not promise support by every named provider model.

