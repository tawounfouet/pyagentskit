from __future__ import annotations

import unittest
from datetime import UTC, datetime

from pyagentskit import (
    AgentDefinition,
    ApprovalDecision,
    ApprovalError,
    ApprovalStatus,
    EventType,
    FinishReason,
    MemoryApprovalStore,
    MemorySessionStore,
    ModelRef,
    ModelResponse,
    RunContext,
    RunStatus,
    Session,
    TextContent,
    ToolCall,
    ToolRegistry,
    ToolRisk,
    tool,
)
from pyagentskit.observability import EventBus, MemoryEventSink
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


def definition() -> AgentDefinition:
    return AgentDefinition(
        id="operator",
        version="1.0.0",
        instructions="Operate safely",
        model=ModelRef(provider="fake", name="test"),
        tools=("write_record",),
    )


def final(text: str = "completed") -> ModelResponse:
    return ModelResponse(
        id="final",
        model="test",
        content=(TextContent(text=text),),
        finish_reason=FinishReason.STOP,
    )


class HitlRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        self.calls: list[int] = []

        @tool(risk=ToolRisk.EXTERNAL_WRITE, requires_approval=True)
        def write_record(value: int) -> int:
            """Write one externally visible value."""

            self.calls.append(value)
            return value

        self.sessions = MemorySessionStore()
        now = datetime.now(UTC)
        await self.sessions.create(
            Session(
                session_id="session",
                agent_id="operator",
                created_at=now,
                updated_at=now,
            )
        )
        self.approvals = MemoryApprovalStore()
        self.sink = MemoryEventSink()
        self.model = FakeModel(
            [
                ModelResponse(
                    id="tool",
                    model="test",
                    tool_calls=(
                        ToolCall(id="call-1", name="write_record", arguments={"value": 7}),
                    ),
                    finish_reason=FinishReason.TOOL_CALLS,
                ),
                final(),
            ]
        )
        self.runner = Runner(
            self.model,
            tools=ToolRegistry([write_record]),
            session_store=self.sessions,
            approval_store=self.approvals,
            events=EventBus([self.sink]),
        )

    async def test_approved_call_suspends_then_resumes_once(self) -> None:
        context = RunContext(agent_id="operator", deps=None, session_id="session")
        waiting = await self.runner.run(definition(), "write seven", context=context)
        self.assertEqual(waiting.status, RunStatus.WAITING_APPROVAL)
        self.assertEqual(self.calls, [])
        approval_id = waiting.metadata["approval_id"]
        approval = await self.approvals.get(approval_id)
        self.assertEqual(approval.status, ApprovalStatus.PENDING)
        await self.approvals.resolve(
            approval_id,
            ApprovalDecision.APPROVE,
            actor_id="human.reviewer",
            reason="checked",
            expected_revision=0,
        )
        resumed = await self.runner.resume_approval(definition(), approval_id, context=context)
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(resumed.output, "completed")
        self.assertEqual(self.calls, [7])
        self.assertEqual((await self.approvals.get(approval_id)).status, ApprovalStatus.EXECUTED)
        self.assertEqual(self.model.requests[-1].messages[-1].role.value, "tool")
        event_types = [event.event_type for event in self.sink.events]
        self.assertIn(EventType.APPROVAL_REQUESTED, event_types)
        self.assertIn(EventType.APPROVAL_CLAIMED, event_types)
        self.assertIn(EventType.APPROVAL_EXECUTED, event_types)
        with self.assertRaises(ApprovalError):
            await self.runner.resume_approval(definition(), approval_id, context=context)

    async def test_rejection_is_observed_without_tool_execution(self) -> None:
        context = RunContext(agent_id="operator", deps=None, session_id="session")
        waiting = await self.runner.run(definition(), "write seven", context=context)
        approval_id = waiting.metadata["approval_id"]
        await self.approvals.resolve(
            approval_id,
            ApprovalDecision.REJECT,
            actor_id="human.reviewer",
            reason="not authorized",
        )
        result = await self.runner.resume_approval(definition(), approval_id, context=context)
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(self.calls, [])
        self.assertIn("denied", self.model.requests[-1].messages[-1].content[0].text)
        self.assertEqual((await self.approvals.get(approval_id)).status, ApprovalStatus.EXECUTED)
        with self.assertRaises(ApprovalError):
            await self.runner.resume_approval(definition(), approval_id, context=context)

    async def test_missing_state_fails_before_action(self) -> None:
        model = FakeModel(
            [
                ModelResponse(
                    id="tool",
                    model="test",
                    tool_calls=(
                        ToolCall(id="call-1", name="write_record", arguments={"value": 7}),
                    ),
                    finish_reason=FinishReason.TOOL_CALLS,
                )
            ]
        )
        runner = Runner(model, tools=self.runner.tools)
        result = await runner.run(definition(), "write")
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(self.calls, [])


if __name__ == "__main__":
    unittest.main()
