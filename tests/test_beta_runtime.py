import asyncio
import io
import unittest

from pydantic import BaseModel

from pyagentskit import (
    AgentDefinition,
    EventType,
    FinishReason,
    Message,
    MessageRole,
    ModelRef,
    ModelRequest,
    ModelResponse,
    RunContext,
    RunLimits,
    RunStatus,
    TextContent,
    ToolCall,
    ToolRegistry,
    Usage,
    tool,
)
from pyagentskit.exceptions import ModelResponseError, PyAgentsKitError
from pyagentskit.observability import (
    ConsoleEventSink,
    EventBus,
    JsonLinesEventSink,
    MemoryEventSink,
)
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


def agent(**kwargs):
    return AgentDefinition(
        id="demo",
        version="1.0.0",
        instructions="Help",
        model=ModelRef(provider="fake", name="test"),
        **kwargs,
    )


def response(text="done", **kwargs):
    return ModelResponse(
        id="r1",
        model="test",
        content=(TextContent(text=text),),
        finish_reason=FinishReason.STOP,
        **kwargs,
    )


class Output(BaseModel):
    value: int


class RuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_tool_limits_and_recovery(self):
        @tool
        def broken() -> None:
            """Fail predictably."""
            raise ValueError("private")

        call = ModelResponse(
            id="r",
            model="test",
            finish_reason=FinishReason.TOOL_CALLS,
            tool_calls=(ToolCall(id="c", name="broken", arguments={}),),
        )
        registry = ToolRegistry([broken])
        for limits in [
            RunLimits(max_tool_calls=0),
            RunLimits(max_steps=1),
            RunLimits(max_model_calls=1),
        ]:
            result = await Runner(FakeModel([call]), tools=registry).run(
                agent(tools=("broken",)), "Hi", limits=limits, recover_tool_errors=True
            )
            self.assertEqual(result.status, RunStatus.LIMIT_EXCEEDED)
        result = await Runner(FakeModel([call, response()]), tools=registry).run(
            agent(tools=("broken",)), "Hi", recover_tool_errors=True
        )
        self.assertEqual(result.status, RunStatus.COMPLETED)
        result = await Runner(FakeModel([call]), tools=registry).run(agent(tools=("broken",)), "Hi")
        self.assertEqual(result.status, RunStatus.FAILED)
        result = await Runner(FakeModel([call])).run(agent(), "Hi")
        self.assertEqual(result.status, RunStatus.FAILED)

    async def test_approval_is_refused(self):
        @tool(requires_approval=True)
        def protected() -> None:
            """Must never execute."""
            raise AssertionError("not approved")

        call = ModelResponse(
            id="r",
            model="test",
            finish_reason=FinishReason.TOOL_CALLS,
            tool_calls=(ToolCall(id="c", name="protected", arguments={}),),
        )
        result = await Runner(FakeModel([call]), tools=ToolRegistry([protected])).run(
            agent(tools=("protected",)), "Hi"
        )
        self.assertEqual(result.status, RunStatus.FAILED)

    async def test_text_and_events(self):
        sink = MemoryEventSink()
        result = await Runner(FakeModel([response()]), events=EventBus([sink])).run(agent(), "Hi")
        self.assertEqual(result.output, "done")
        self.assertEqual(result.usage.model_calls, 1)
        self.assertEqual(sink.events[-1].event_type, EventType.RUN_COMPLETED)
        request_event = next(
            event for event in sink.events if event.event_type is EventType.MODEL_REQUEST_STARTED
        )
        response_event = next(
            event for event in sink.events if event.event_type is EventType.MODEL_RESPONSE_COMPLETED
        )
        self.assertEqual(request_event.payload["requested_model"], "test")
        self.assertEqual(response_event.payload["resolved_model"], "test")

    async def test_tool_cycle_and_context(self):
        @tool
        def add(value: int, context: RunContext[None]) -> int:
            """Add one."""
            return value + 1

        fake = FakeModel(
            [
                ModelResponse(
                    id="r",
                    model="test",
                    tool_calls=(ToolCall(id="c", name="add", arguments={"value": 2}),),
                    finish_reason=FinishReason.TOOL_CALLS,
                ),
                response(),
            ]
        )
        result = await Runner(fake, tools=ToolRegistry([add])).run(agent(tools=("add",)), "Hi")
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(result.usage.tool_calls, 1)
        self.assertEqual(fake.requests[-1].messages[-1].tool_call_id, "c")
        self.assertIn('"content":3', fake.requests[-1].messages[-1].content[0].text)

    async def test_budgets(self):
        for limits in [RunLimits(max_total_tokens=2), RunLimits(max_input_tokens=1)]:
            result = await Runner(
                FakeModel([response(usage=Usage(input_tokens=2, output_tokens=2))])
            ).run(agent(), "Hi", limits=limits)
            self.assertEqual(result.status, RunStatus.LIMIT_EXCEEDED)

        exact = await Runner(
            FakeModel([response(usage=Usage(input_tokens=2, output_tokens=2))])
        ).run(agent(), "Hi", limits=RunLimits(max_input_tokens=2, max_output_tokens=2))
        self.assertEqual(exact.status, RunStatus.COMPLETED)

    async def test_exhausted_output_budget_blocks_another_model_call(self):
        call = ModelResponse(
            id="r",
            model="test",
            finish_reason=FinishReason.TOOL_CALLS,
            tool_calls=(ToolCall(id="c", name="echo", arguments={}),),
            usage=Usage(output_tokens=2),
        )

        @tool
        def echo() -> str:
            """Return a value."""
            return "ok"

        fake = FakeModel([call, response()])
        result = await Runner(fake, tools=ToolRegistry([echo])).run(
            agent(tools=("echo",)), "Hi", limits=RunLimits(max_output_tokens=2)
        )
        self.assertEqual(result.status, RunStatus.LIMIT_EXCEEDED)
        self.assertEqual(len(fake.requests), 1)

    async def test_structured_output(self):
        result = await Runner(FakeModel([response('{"value":2}')])).run(
            agent(), "Hi", output_type=Output
        )
        self.assertEqual(result.output.value, 2)
        invalid = await Runner(FakeModel([response('{"value":"bad"}')])).run(
            agent(), "Hi", output_type=Output
        )
        self.assertEqual(invalid.status, RunStatus.FAILED)

    async def test_script_error_and_refusal(self):
        for item in [
            RuntimeError("SECRET"),
            ModelResponse(id="r", model="test", finish_reason=FinishReason.CONTENT_FILTER),
        ]:
            result = await Runner(FakeModel([item])).run(agent(), "Hi")
            self.assertEqual(result.status, RunStatus.FAILED)
            self.assertNotIn("SECRET", result.model_dump_json())

    async def test_length_limit(self):
        item = response().model_copy(update={"finish_reason": FinishReason.LENGTH})
        result = await Runner(FakeModel([item])).run(agent(), "Hi")
        self.assertEqual(result.status, RunStatus.LIMIT_EXCEEDED)

    async def test_active_loop_sync_rejected(self):
        with self.assertRaises(RuntimeError):
            Runner(FakeModel([])).run_sync(agent(), "Hi")

    async def test_deadline_and_cancellation(self):
        class Slow(FakeModel):
            async def generate(self, request, *, context):
                await asyncio.sleep(10)

        result = await Runner(Slow([])).run(agent(), "Hi", limits=RunLimits(timeout_seconds=0.01))
        self.assertEqual(result.status, RunStatus.LIMIT_EXCEEDED)
        sink = MemoryEventSink()
        task = asyncio.create_task(Runner(Slow([]), events=EventBus([sink])).run(agent(), "Hi"))
        await asyncio.sleep(0.01)
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(sink.events[-1].event_type, EventType.RUN_CANCELLED)

    async def test_nested_tool_model_preserved(self):
        @tool
        def nested(value: Output) -> int:
            """Read typed model."""
            return value.value

        result = await nested.invoke(
            {"value": {"value": 2}}, context=RunContext(agent_id="demo", deps=None)
        )
        self.assertEqual(result.content, 2)

    async def test_sinks_redaction_and_failures(self):
        memory = MemoryEventSink()
        stream = io.StringIO()
        console = io.StringIO()
        bus = EventBus(
            [memory, JsonLinesEventSink(stream), ConsoleEventSink(console, verbose=True)],
            secrets=["SECRET"],
        )
        await Runner(FakeModel([response()]), events=bus).run(agent(), "SECRET")
        self.assertNotIn("SECRET", stream.getvalue())
        self.assertIn("DEBUG", console.getvalue())

        def broken(event):
            raise RuntimeError("private")

        bus = EventBus([broken], fail_fast=False)
        await bus.emit(memory.events[0])
        self.assertEqual(bus.failures, 1)
        with self.assertRaises(PyAgentsKitError):
            await EventBus([broken]).emit(memory.events[0])

    async def test_stream_and_exhaustion(self):
        fake = FakeModel([response()])
        request = ModelRequest(messages=(Message.from_text(MessageRole.USER, "Hi"),))
        ctx = RunContext(agent_id="demo", deps=None)
        events = [event async for event in fake.stream(request, context=ctx)]
        self.assertEqual(events[-1].type.value, "completed")
        with self.assertRaises(ModelResponseError):
            await fake.generate(request, context=ctx)


class SyncTests(unittest.TestCase):
    def test_sync(self):
        self.assertEqual(Runner(FakeModel([response()])).run_sync(agent(), "Hi").output, "done")
