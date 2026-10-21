"""Offline durable model-tool-model cycle with analytical replay."""

import asyncio
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from pyagentskit import (
    AgentDefinition,
    DurableRunner,
    FinishReason,
    MemorySessionStore,
    ModelRef,
    ModelResponse,
    RunContext,
    Session,
    SQLiteRunStore,
    TextContent,
    ToolCall,
    ToolRegistry,
    tool,
)
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


@tool(idempotent=True)
def lookup_order(order_id: str) -> dict[str, str]:
    """Look up one order in the example application."""

    return {"order_id": order_id, "status": "ready"}


async def main() -> None:
    model = FakeModel(
        [
            ModelResponse(
                id="tool",
                model="test",
                tool_calls=(
                    ToolCall(
                        id="call-1",
                        name="lookup_order",
                        arguments={"order_id": "O-42"},
                    ),
                ),
                finish_reason=FinishReason.TOOL_CALLS,
            ),
            ModelResponse(
                id="final",
                model="test",
                content=(TextContent(text="Order O-42 is ready."),),
                finish_reason=FinishReason.STOP,
            ),
        ]
    )
    agent = AgentDefinition(
        id="orders.agent",
        version="1.0.0",
        instructions="Check the order",
        model=ModelRef(provider="fake", name="test"),
        tools=("lookup_order",),
    )
    sessions = MemorySessionStore()
    now = datetime.now(UTC)
    await sessions.create(
        Session(session_id="demo", agent_id=agent.id, created_at=now, updated_at=now)
    )
    context = RunContext(agent_id=agent.id, deps=None, session_id="demo")
    with tempfile.TemporaryDirectory() as temporary:
        store = SQLiteRunStore(Path(temporary) / "runs.db")
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry([lookup_order]), session_store=sessions), store
        )
        result = await durable.run(agent, "Check O-42", context=context)
        journal = await durable.replay(context.run_id)
        print(result.output)
        print(f"{len(journal)} durable journal entries")
        store.close()


if __name__ == "__main__":
    asyncio.run(main())
