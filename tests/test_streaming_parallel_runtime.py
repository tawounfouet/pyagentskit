from __future__ import annotations

import asyncio
import unittest
from collections.abc import AsyncIterator
from typing import Any

from pyagentskit import (
    AgentDefinition,
    CapabilityError,
    FinishReason,
    MessageRole,
    ModelCapabilities,
    ModelRef,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
    RunContext,
    RunLimits,
    Runner,
    RunStatus,
    TextContent,
    ToolCall,
    ToolRegistry,
    ToolRisk,
    tool,
)
from pyagentskit.testing import FakeModel


def agent(*tools: str) -> AgentDefinition:
    return AgentDefinition(
        id="stream.agent",
        version="1.0.0",
        instructions="Help",
        model=ModelRef(provider="fake", name="stream-model"),
        tools=tools,
    )


def final(text: str = "done") -> ModelResponse:
    return ModelResponse(
        id="final",
        model="stream-model",
        content=(TextContent(text=text),),
        finish_reason=FinishReason.STOP,
    )


def calls(*items: ToolCall) -> ModelResponse:
    return ModelResponse(
        id="calls",
        model="stream-model",
        tool_calls=items,
        finish_reason=FinishReason.TOOL_CALLS,
    )


class StreamingRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_handler_receives_text_and_completion(self) -> None:
        events: list[ModelStreamEvent] = []

        async def handle(event: ModelStreamEvent) -> None:
            events.append(event)

        result = await Runner(FakeModel((final("streamed"),))).run(
            agent(), "hello", stream_handler=handle
        )
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(result.output, "streamed")
        self.assertEqual(result.usage.model_calls, 1)
        self.assertEqual(events[0].type, ModelStreamEventType.STARTED)
        self.assertEqual(events[-1].type, ModelStreamEventType.COMPLETED)
        self.assertEqual(
            "".join(event.delta or "" for event in events),
            "streamed",
        )

    async def test_streaming_preserves_complete_tool_cycle(self) -> None:
        @tool(idempotent=True, risk=ToolRisk.READ)
        async def lookup(value: int) -> int:
            """Return one value."""
            return value

        model = FakeModel(
            (
                calls(ToolCall(id="call-1", name="lookup", arguments={"value": 3})),
                final("complete"),
            )
        )
        events: list[ModelStreamEventType] = []

        async def handle(event: ModelStreamEvent) -> None:
            events.append(event.type)

        result = await Runner(model, tools=ToolRegistry((lookup,))).run(
            agent("lookup"), "hello", stream_handler=handle
        )
        self.assertEqual(result.output, "complete")
        self.assertEqual(result.usage.model_calls, 2)
        self.assertEqual(result.usage.tool_calls, 1)
        self.assertIn(ModelStreamEventType.TOOL_CALL_COMPLETED, events)

    async def test_streaming_requires_capability(self) -> None:
        class NonStreamingModel:
            capabilities = ModelCapabilities()

            async def generate(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> ModelResponse:
                raise AssertionError("must fail during preflight")

            async def stream(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> AsyncIterator[ModelStreamEvent]:
                if False:
                    yield ModelStreamEvent(type=ModelStreamEventType.STARTED)

        async def handle(event: ModelStreamEvent) -> None:
            return None

        with self.assertRaises(CapabilityError):
            await Runner(NonStreamingModel()).run(agent(), "hello", stream_handler=handle)

    async def test_truncated_stream_fails_closed(self) -> None:
        class TruncatedModel:
            capabilities = ModelCapabilities(streaming=True)

            async def generate(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> ModelResponse:
                raise AssertionError("stream path expected")

            async def stream(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> AsyncIterator[ModelStreamEvent]:
                yield ModelStreamEvent(type=ModelStreamEventType.STARTED)
                yield ModelStreamEvent(type=ModelStreamEventType.TEXT_DELTA, delta="partial")

        async def handle(event: ModelStreamEvent) -> None:
            return None

        result = await Runner(TruncatedModel()).run(agent(), "hello", stream_handler=handle)
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertIsNone(result.output)

    async def test_error_and_duplicate_terminal_streams_fail_closed(self) -> None:
        class InvalidStreamModel:
            capabilities = ModelCapabilities(streaming=True)

            def __init__(self, *, error: bool) -> None:
                self.error = error

            async def generate(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> ModelResponse:
                raise AssertionError("stream path expected")

            async def stream(
                self, request: ModelRequest, *, context: RunContext[Any]
            ) -> AsyncIterator[ModelStreamEvent]:
                if self.error:
                    yield ModelStreamEvent(type=ModelStreamEventType.ERROR)
                    return
                yield ModelStreamEvent(type=ModelStreamEventType.TEXT_DELTA, delta="done")
                yield ModelStreamEvent(type=ModelStreamEventType.COMPLETED)
                yield ModelStreamEvent(type=ModelStreamEventType.COMPLETED)

        async def handle(event: ModelStreamEvent) -> None:
            return None

        for error in (True, False):
            with self.subTest(error=error):
                result = await Runner(InvalidStreamModel(error=error)).run(
                    agent(), "hello", stream_handler=handle
                )
                self.assertEqual(result.status, RunStatus.FAILED)
                self.assertIsNone(result.output)


class ParallelToolRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_safe_idempotent_tools_run_in_parallel_with_ordered_messages(self) -> None:
        active = 0
        peak = 0
        both_started = asyncio.Event()

        @tool(idempotent=True, risk=ToolRisk.READ)
        async def lookup(value: int) -> int:
            """Read a value."""
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            if active == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=0.2)
            active -= 1
            return value

        model = FakeModel(
            (
                calls(
                    ToolCall(id="call-1", name="lookup", arguments={"value": 1}),
                    ToolCall(id="call-2", name="lookup", arguments={"value": 2}),
                ),
                final(),
            )
        )
        result = await Runner(
            model,
            tools=ToolRegistry((lookup,)),
            parallel_tool_calls=True,
        ).run(agent("lookup"), "hello", limits=RunLimits(max_parallel_tools=2))
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(peak, 2)
        tool_messages = [
            message for message in model.requests[-1].messages if message.role is MessageRole.TOOL
        ]
        self.assertEqual([message.tool_call_id for message in tool_messages], ["call-1", "call-2"])

    async def test_external_writes_remain_sequential(self) -> None:
        active = 0
        peak = 0

        @tool(idempotent=True, risk=ToolRisk.EXTERNAL_WRITE)
        async def publish(value: int) -> int:
            """Represent a governed external write."""
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return value

        model = FakeModel(
            (
                calls(
                    ToolCall(id="call-1", name="publish", arguments={"value": 1}),
                    ToolCall(id="call-2", name="publish", arguments={"value": 2}),
                ),
                final(),
            )
        )
        result = await Runner(
            model,
            tools=ToolRegistry((publish,)),
            parallel_tool_calls=True,
        ).run(agent("publish"), "hello")
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(peak, 1)

    async def test_parallel_execution_obeys_run_limit(self) -> None:
        active = 0
        peak = 0

        @tool(idempotent=True, risk=ToolRisk.PURE)
        async def calculate(value: int) -> int:
            """Return one calculated value."""
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return value

        model = FakeModel(
            (
                calls(
                    ToolCall(id="call-1", name="calculate", arguments={"value": 1}),
                    ToolCall(id="call-2", name="calculate", arguments={"value": 2}),
                    ToolCall(id="call-3", name="calculate", arguments={"value": 3}),
                ),
                final(),
            )
        )
        result = await Runner(
            model,
            tools=ToolRegistry((calculate,)),
            parallel_tool_calls=True,
        ).run(agent("calculate"), "hello", limits=RunLimits(max_parallel_tools=2))
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(peak, 2)


if __name__ == "__main__":
    unittest.main()
