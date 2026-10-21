"""Offline Lot 02 example: declare, register and execute one typed tool."""

import asyncio

from pyagentskit import RunContext, ToolRegistry, tool


@tool(risk="read", idempotent=True, timeout_seconds=5)
async def weather(city: str, context: RunContext[dict[str, str]]) -> str:
    """Return deterministic demo weather for a city."""

    return f"Sunny in {city} for tenant {context.deps['tenant']}"


async def main() -> None:
    registry = ToolRegistry([weather])
    result = await registry.execute(
        "weather",
        {"city": "Paris"},
        context=RunContext(agent_id="example.weather", deps={"tenant": "demo"}),
        call_id="example-call-1",
    )
    print(result.content)


if __name__ == "__main__":
    asyncio.run(main())
