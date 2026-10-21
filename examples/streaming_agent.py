"""Run the complete Runner streaming path without credentials or network."""

import asyncio

from pyagentskit import (
    AgentDefinition,
    FinishReason,
    ModelRef,
    ModelResponse,
    ModelStreamEvent,
    Runner,
    TextContent,
)
from pyagentskit.testing import FakeModel


async def main() -> None:
    model = FakeModel(
        (
            ModelResponse(
                id="stream-1",
                model="demo",
                content=(TextContent(text="Stream complete."),),
                finish_reason=FinishReason.STOP,
            ),
        )
    )
    agent = AgentDefinition(
        id="stream.demo",
        version="1.0.0",
        instructions="Return the scripted response.",
        model=ModelRef(provider="fake", name="demo"),
    )
    deltas: list[str] = []

    async def on_stream(event: ModelStreamEvent) -> None:
        if event.delta is not None:
            deltas.append(event.delta)

    result = await Runner(model).run(agent, "Hello", stream_handler=on_stream)
    assert "".join(deltas) == "Stream complete."
    assert result.output == "Stream complete."
    print(result.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())
