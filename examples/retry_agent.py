"""Demonstrate an explicit, bounded model retry without network access."""

import asyncio

from pyagentskit import (
    AgentDefinition,
    FinishReason,
    ModelRef,
    ModelResponse,
    ModelUnavailableError,
    Runner,
    TextContent,
)
from pyagentskit.retry import ModelRetryPolicy
from pyagentskit.testing import FakeModel


async def main() -> None:
    model = FakeModel(
        (
            ModelUnavailableError("Scripted temporary failure"),
            ModelResponse(
                id="retry-success",
                model="demo",
                content=(TextContent(text="Recovered safely."),),
                finish_reason=FinishReason.STOP,
            ),
        )
    )
    agent = AgentDefinition(
        id="retry.demo",
        version="1.0.0",
        instructions="Return the scripted response.",
        model=ModelRef(provider="fake", name="demo"),
    )
    policy = ModelRetryPolicy(
        max_attempts=2,
        initial_delay_seconds=0,
        max_delay_seconds=0,
    )
    result = await Runner(model, retry_policy=policy).run(agent, "Hello")
    assert result.output == "Recovered safely."
    assert result.usage.model_calls == 2
    print(result.model_dump_json())


if __name__ == "__main__":
    asyncio.run(main())
