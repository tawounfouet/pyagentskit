import asyncio
import unittest

from pyagentskit import (
    AgentDefinition,
    FinishReason,
    Message,
    MessageRole,
    ModelRef,
    ModelResponse,
    RunContext,
    TextContent,
    ToolCall,
    ToolExecutor,
    tool,
)
from pyagentskit.exceptions import ToolExecutionError, ToolPermissionError, ToolTimeoutError
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


class ConsolidationTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_runs_do_not_share_history(self):
        class Echo(FakeModel):
            async def generate(self, request, *, context):
                await asyncio.sleep(0)
                self.assertion = len(request.messages)
                return ModelResponse(
                    id=str(context.run_id),
                    model="m",
                    finish_reason=FinishReason.STOP,
                    content=request.messages[-1].content,
                )

        model = Echo([])
        agent = AgentDefinition(
            id="a", version="1.0.0", instructions="Help", model=ModelRef(provider="fake", name="m")
        )
        runner = Runner(model)
        results = await asyncio.gather(*(runner.run(agent, str(i)) for i in range(8)))
        self.assertEqual([r.output for r in results], list(map(str, range(8))))
        self.assertEqual(len({r.run_id for r in results}), 8)
        self.assertEqual(model.assertion, 2)

    async def test_executor_preflight(self):
        @tool(requires_approval=True)
        def protected() -> None:
            """Not executable."""
            raise AssertionError("unsafe")

        executor = ToolExecutor()
        call = ToolCall(id="c", name="protected", arguments={})
        ctx = RunContext(agent_id="a", deps=None)
        with self.assertRaises(ToolPermissionError):
            await executor.execute(protected, call, context=ctx)
        for timeout in [0, -1, float("inf"), float("nan")]:
            with self.assertRaises(ToolExecutionError):
                await executor.execute(protected, call, context=ctx, timeout_seconds=timeout)

    async def test_timeout_includes_queue_wait(self):
        started = asyncio.Event()

        @tool(concurrency_limit=1)
        async def wait() -> None:
            """Wait for cancellation."""
            started.set()
            await asyncio.Event().wait()

        executor = ToolExecutor()
        call = ToolCall(id="c", name="wait", arguments={})
        ctx = RunContext(agent_id="a", deps=None)
        first = asyncio.create_task(executor.execute(wait, call, context=ctx))
        await started.wait()
        try:
            with self.assertRaises(ToolTimeoutError):
                await executor.execute(wait, call, context=ctx, timeout_seconds=0.01)
        finally:
            first.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await first

    def test_typed_tool_messages(self):
        call = ToolCall(id="c", name="tool", arguments={})
        message = Message(role=MessageRole.ASSISTANT, tool_calls=(call,))
        self.assertEqual(Message.model_validate_json(message.model_dump_json()), message)
        with self.assertRaises(ValueError):
            Message(role=MessageRole.USER, content=(TextContent(text="bad"),), tool_calls=(call,))
