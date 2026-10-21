# Streaming and parallel tools

Both features are opt-in. Existing sequential, complete-response applications require no changes.

## Integrated streaming

```python
from pyagentskit import ModelStreamEvent, Runner


async def on_stream(event: ModelStreamEvent) -> None:
    if event.delta:
        print(event.delta, end="", flush=True)


result = await Runner(model, tools=registry).run(
    agent,
    "Question",
    stream_handler=on_stream,
)
```

The callback sees provider-neutral events. It can display partial text, but must treat the final
`RunResult` as authoritative: validation, a later tool, a guardrail or the provider stream can still
fail after partial output was observed. Keep the callback asynchronous, bounded and free of secrets.

## Safe parallel reads

```python
from pyagentskit import RunLimits, Runner, ToolRisk, tool


@tool(risk=ToolRisk.READ, idempotent=True)
async def get_customer(customer_id: str) -> dict[str, str]:
    """Read one customer."""
    ...


runner = Runner(model, tools=registry, parallel_tool_calls=True)
result = await runner.run(
    agent,
    "Compare these customers",
    limits=RunLimits(max_parallel_tools=4),
)
```

Parallel execution occurs only when the model adapter declares parallel tool support and every call
in the response is an idempotent `PURE` or `READ` tool. One unsafe call makes the whole batch
sequential. Completion order never changes the order of tool-result messages.

Do not mark an operation idempotent or read-only merely to gain concurrency. State changes,
payments, messages, file writes and uncertain effects must retain a stricter risk classification.

