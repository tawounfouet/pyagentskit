"""Run two explicitly safe tool calls concurrently without network access."""

import asyncio

from pyagentskit import (
    AgentDefinition,
    FinishReason,
    ModelRef,
    ModelResponse,
    RunLimits,
    Runner,
    TextContent,
    ToolCall,
    ToolRegistry,
    ToolRisk,
    tool,
)
from pyagentskit.testing import FakeModel


@tool(risk=ToolRisk.READ, idempotent=True)
async def read_value(value: int) -> int:
    """Read one value."""
    await asyncio.sleep(0)
    return value


async def main() -> None:
    model = FakeModel(
        (
            ModelResponse(
                id="tools",
                model="demo",
                tool_calls=(
                    ToolCall(id="call-1", name="read_value", arguments={"value": 1}),
                    ToolCall(id="call-2", name="read_value", arguments={"value": 2}),
                ),
                finish_reason=FinishReason.TOOL_CALLS,
            ),
            ModelResponse(
                id="final",
                model="demo",
                content=(TextContent(text="Read complete."),),
                finish_reason=FinishReason.STOP,
            ),
        )
    )
    agent = AgentDefinition(
        id="parallel.demo",
        version="1.0.0",
        instructions="Use both reads.",
        model=ModelRef(provider="fake", name="demo"),
        tools=("read_value",),
    )
    runner = Runner(
        model,
        tools=ToolRegistry((read_value,)),
        parallel_tool_calls=True,
    )
    result = await runner.run(agent, "Read two values", limits=RunLimits(max_parallel_tools=2))
    assert result.output == "Read complete."
    print(result.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())
