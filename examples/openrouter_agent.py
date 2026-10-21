"""Minimal OpenRouter example; execution is explicit and potentially billable."""

import asyncio
import os

from pyagentskit import AgentDefinition, ModelRef
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.runtime import Runner


async def main() -> None:
    model_name = os.environ["PYAGENTSKIT_OPENROUTER_MODEL"]
    agent = AgentDefinition(
        id="openrouter-demo",
        version="1.0.0",
        instructions="Answer precisely and briefly.",
        model=ModelRef(provider="openrouter", name=model_name),
    )
    async with OpenRouterModel(model_name, app_title="PyAgentsKit example") as model:
        result = await Runner(model).run(agent, "Reply with one short greeting.")
        print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    if os.getenv("PYAGENTSKIT_OPENROUTER_LIVE") != "1":
        raise SystemExit("Set PYAGENTSKIT_OPENROUTER_LIVE=1 to allow a live request")
    asyncio.run(main())
