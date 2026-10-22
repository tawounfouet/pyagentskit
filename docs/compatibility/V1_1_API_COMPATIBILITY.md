# PyAgentsKit 1.1.0 API compatibility

## Frozen V1 surface

The V1 freeze suite remains authoritative. Version 1.1.0 retains:

| Contract | 1.0.0 | 1.1.0 |
|---|---:|---:|
| Root exports | 155 | 155 |
| Root export SHA-256 | `bfd66c240b638dca67178db2159c49b1df0181a78a405d72f6abb889252b08d9` | unchanged |
| Frozen structured field layouts | 10 | unchanged |
| Direct provider constructor parameter list | frozen | unchanged |
| OpenRouter constructor/routing surface | frozen | unchanged |

## Additive call parameters

`Runner.__init__` adds the keyword-only option `parallel_tool_calls: bool = False`.
`Runner.run` adds the keyword-only option `stream_handler = None`. Both defaults reproduce 1.0.0
behavior. Positional calling conventions are unaffected.

The stream callback is asynchronous and receives defensive copies of `ModelStreamEvent`. The final
`RunResult` remains the authoritative run outcome.

## Behavioral compatibility

| Existing use | Behavior in 1.1.0 |
|---|---|
| No stream callback | Calls `Model.generate()` as before |
| Parallel option omitted | Tools run sequentially as before |
| Parallel option enabled for a write | Entire batch remains sequential |
| Parallel option enabled for non-idempotent read | Entire batch remains sequential |
| Approval-required call | Suspends before effects as before |

