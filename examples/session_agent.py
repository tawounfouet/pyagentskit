"""Run two deterministic turns through one persisted in-memory session."""

import asyncio

from pyagentskit import (
    AgentDefinition,
    FinishReason,
    MemorySessionStore,
    ModelRef,
    ModelResponse,
    RunContext,
    Session,
    TextContent,
)
from pyagentskit.runs import utc_now
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


async def main() -> None:
    store = MemorySessionStore()
    now = utc_now()
    await store.create(
        Session(
            session_id="demo-session",
            agent_id="demo",
            created_at=now,
            updated_at=now,
        )
    )
    definition = AgentDefinition(
        id="demo",
        version="1.0.0",
        instructions="Answer precisely.",
        model=ModelRef(provider="fake", name="test"),
    )
    responses = ("First answer.", "Second answer using history.")
    for index, answer in enumerate(responses, start=1):
        model = FakeModel(
            [
                ModelResponse(
                    id=f"response-{index}",
                    model="test",
                    content=(TextContent(text=answer),),
                    finish_reason=FinishReason.STOP,
                )
            ]
        )
        context = RunContext(agent_id="demo", deps=None, session_id="demo-session")
        result = await Runner(model, session_store=store).run(
            definition, f"Question {index}", context=context
        )
        print(result.output)

    entries = await store.list_entries("demo-session")
    print(f"Persisted messages: {len(entries)}")


if __name__ == "__main__":
    asyncio.run(main())
