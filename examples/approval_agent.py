"""Offline approval suspension and resume example."""

import asyncio
from datetime import UTC, datetime

from pyagentskit import (
    AgentDefinition,
    ApprovalDecision,
    FinishReason,
    MemoryApprovalStore,
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
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


async def main() -> None:
    effects: list[str] = []

    @tool(risk=ToolRisk.EXTERNAL_WRITE, requires_approval=True)
    def publish(value: str) -> str:
        """Publish an externally visible value."""

        effects.append(value)
        return value

    agent = AgentDefinition(
        id="approval.demo",
        version="1.0.0",
        instructions="Publish only after approval.",
        model=ModelRef(provider="fake", name="scripted"),
        tools=("publish",),
    )
    model = FakeModel(
        [
            ModelResponse(
                id="request",
                model="scripted",
                tool_calls=(ToolCall(id="call-1", name="publish", arguments={"value": "ok"}),),
                finish_reason=FinishReason.TOOL_CALLS,
            ),
            ModelResponse(
                id="complete",
                model="scripted",
                content=(TextContent(text="Published after approval."),),
                finish_reason=FinishReason.STOP,
            ),
        ]
    )
    sessions = MemorySessionStore()
    now = datetime.now(UTC)
    await sessions.create(
        Session(
            session_id="demo-session",
            agent_id=agent.id,
            created_at=now,
            updated_at=now,
        )
    )
    approvals = MemoryApprovalStore()
    runner = Runner(
        model,
        tools=ToolRegistry([publish]),
        session_store=sessions,
        approval_store=approvals,
    )
    context = RunContext(agent_id=agent.id, deps=None, session_id="demo-session")
    waiting = await runner.run(agent, "Publish ok", context=context)
    approval_id = waiting.metadata["approval_id"]
    request = await approvals.get(approval_id)
    await approvals.resolve(
        approval_id,
        ApprovalDecision.APPROVE,
        actor_id="human.reviewer",
        expected_revision=request.revision,
    )
    completed = await runner.resume_approval(agent, approval_id, context=context)
    print(waiting.status.value)
    print(completed.output)
    print(f"effects={effects!r}")


if __name__ == "__main__":
    asyncio.run(main())
