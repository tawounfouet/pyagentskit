"""Offline DistributedDurableRunner and fencing-token example."""

import asyncio
from datetime import UTC, datetime
from typing import Any

from pyagentskit import (
    AgentDefinition,
    DurableRunner,
    FinishReason,
    MemoryRunStore,
    MemorySessionStore,
    ModelRef,
    ModelResponse,
    RunContext,
    Session,
    TextContent,
    ToolCall,
    ToolRegistry,
    ToolRisk,
    tool,
)
from pyagentskit.coordination import LeaseConflictError, MemoryLeaseStore
from pyagentskit.distributed import (
    DistributedDurableRunner,
    FencingToken,
    fencing_token_from_context,
)
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


class ProtectedLedger:
    def __init__(self) -> None:
        self.highest_token = 0
        self.values: dict[str, Any] = {}

    async def apply_fenced(
        self,
        operation_id: str,
        payload: Any,
        *,
        fencing_token: FencingToken,
    ) -> Any:
        if fencing_token.value < self.highest_token:
            raise LeaseConflictError("stale worker")
        self.highest_token = fencing_token.value
        self.values.setdefault(operation_id, payload)
        return payload


async def main() -> None:
    ledger = ProtectedLedger()

    @tool(risk=ToolRisk.EXTERNAL_WRITE)
    async def write_record(value: int, context: RunContext[None]) -> int:
        """Write once under the current fenced authority."""

        token = fencing_token_from_context(context)
        return await ledger.apply_fenced("record-7", value, fencing_token=token)

    sessions = MemorySessionStore()
    now = datetime.now(UTC)
    await sessions.create(
        Session(
            session_id="demo",
            agent_id="demo.agent",
            created_at=now,
            updated_at=now,
        )
    )
    model = FakeModel(
        [
            ModelResponse(
                id="tool",
                model="fake",
                tool_calls=(ToolCall(id="call-1", name="write_record", arguments={"value": 7}),),
                finish_reason=FinishReason.TOOL_CALLS,
            ),
            ModelResponse(
                id="final",
                model="fake",
                content=(TextContent(text="done"),),
                finish_reason=FinishReason.STOP,
            ),
        ]
    )
    durable = DurableRunner(
        Runner(model, tools=ToolRegistry([write_record]), session_store=sessions),
        MemoryRunStore(),
    )
    distributed = DistributedDurableRunner(durable, MemoryLeaseStore(), owner_id="demo-worker-1")
    agent = AgentDefinition(
        id="demo.agent",
        version="1.0.0",
        instructions="Write one record",
        model=ModelRef(provider="fake", name="fake"),
        tools=("write_record",),
    )
    context = RunContext(agent_id=agent.id, deps=None, session_id="demo")
    result = await distributed.run(agent, "write seven", context=context)
    print(f"status={result.status.value} values={ledger.values} token={ledger.highest_token}")


if __name__ == "__main__":
    asyncio.run(main())
