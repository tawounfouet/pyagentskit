from __future__ import annotations

import asyncio
import unittest
from typing import Any

from pyagentskit import (
    AgentEvent,
    EventType,
    RunContext,
    ToolAlreadyRegisteredError,
    ToolCall,
    ToolExecutionError,
    ToolExecutor,
    ToolNotFoundError,
    ToolPermissionError,
    ToolRegistry,
    ToolResult,
    ToolResultStatus,
    ToolTimeoutError,
    tool,
)


def context() -> RunContext[None]:
    return RunContext(agent_id="test.agent", deps=None)


class MemorySink:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []

    async def emit(self, event: AgentEvent) -> None:
        self.events.append(event)


class RecordingPolicy:
    def __init__(self, *, deny: bool = False) -> None:
        self.deny = deny
        self.calls: list[str] = []

    async def before_execute(self, call, definition, *, context) -> None:  # type: ignore[no-untyped-def]
        self.calls.append(f"before:{call.id}:{definition.name}:{context.agent_id}")
        if self.deny:
            raise ToolPermissionError("denied by test policy")

    async def after_execute(self, call, definition, result, *, context):  # type: ignore[no-untyped-def]
        self.calls.append(f"after:{call.id}:{definition.name}:{context.agent_id}")
        return result.model_copy(update={"metadata": {"reviewed": True}})


class ToolRegistryTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self) -> None:
        @tool
        async def echo(value: str) -> str:
            """Echo a string."""
            return value

        self.echo = echo

    async def test_register_list_get_execute_and_unregister(self) -> None:
        registry = ToolRegistry([self.echo])
        self.assertEqual(len(registry), 1)
        self.assertIn("echo", registry)
        self.assertEqual(registry.names(), ("echo",))
        self.assertEqual(registry.definitions(), (self.echo.definition,))
        self.assertIs(registry.get("echo"), self.echo)

        result = await registry.execute(
            "echo", {"value": "hello"}, context=context(), call_id="call-1"
        )
        self.assertEqual(result.call_id, "call-1")
        self.assertEqual(result.tool_name, "echo")
        self.assertEqual(result.content, "hello")
        self.assertIs(registry.unregister("echo"), self.echo)
        self.assertEqual(len(registry), 0)

    async def test_execute_existing_call(self) -> None:
        registry = ToolRegistry([self.echo])
        result = await registry.execute_call(
            ToolCall(id="call-existing", name="echo", arguments={"value": "yes"}),
            context=context(),
        )
        self.assertEqual(result.call_id, "call-existing")

    def test_duplicate_requires_explicit_replace(self) -> None:
        registry = ToolRegistry([self.echo])
        with self.assertRaises(ToolAlreadyRegisteredError):
            registry.register(self.echo)
        registry.register(self.echo, replace=True)
        self.assertEqual(len(registry), 1)

    def test_unknown_tool_operations_raise_normalized_error(self) -> None:
        registry = ToolRegistry()
        with self.assertRaises(ToolNotFoundError):
            registry.get("unknown")
        with self.assertRaises(ToolNotFoundError):
            registry.unregister("unknown")


class ToolExecutorTests(unittest.IsolatedAsyncioTestCase):
    async def test_policy_and_events_wrap_successful_execution(self) -> None:
        sink = MemorySink()
        policy = RecordingPolicy()
        executor = ToolExecutor(policies=[policy], event_sinks=[sink])

        @tool
        async def echo(value: str) -> str:
            """Echo a string."""
            return value

        call = ToolCall(id="call-1", name="echo", arguments={"value": "hello"})
        result = await executor.execute(echo, call, context=context())

        self.assertEqual(result.metadata, {"reviewed": True})
        self.assertEqual(
            policy.calls,
            ["before:call-1:echo:test.agent", "after:call-1:echo:test.agent"],
        )
        self.assertEqual(
            [event.event_type for event in sink.events],
            [EventType.TOOL_CALL_STARTED, EventType.TOOL_CALL_COMPLETED],
        )
        self.assertEqual(sink.events[0].payload["call_id"], "call-1")
        self.assertNotIn("arguments", sink.events[0].payload)

    async def test_policy_can_deny_before_user_code(self) -> None:
        called = False
        policy = RecordingPolicy(deny=True)

        @tool
        def dangerous() -> None:
            """Represent a protected action."""
            nonlocal called
            called = True

        executor = ToolExecutor(policies=[policy])
        with self.assertRaises(ToolPermissionError):
            await executor.execute(
                dangerous,
                ToolCall(id="call-1", name="dangerous", arguments={}),
                context=context(),
            )
        self.assertFalse(called)

    async def test_policy_failure_is_normalized(self) -> None:
        class BrokenPolicy(RecordingPolicy):
            async def before_execute(self, call, definition, *, context) -> None:  # type: ignore[no-untyped-def]
                raise RuntimeError("internal policy detail")

        @tool
        def safe() -> None:
            """Do nothing."""

        with self.assertRaisesRegex(ToolPermissionError, "policy failed"):
            await ToolExecutor(policies=[BrokenPolicy()]).execute(
                safe,
                ToolCall(id="call-1", name="safe", arguments={}),
                context=context(),
            )

    async def test_timeout_emits_failure_event(self) -> None:
        sink = MemorySink()

        @tool(timeout_seconds=0.01)
        async def slow() -> None:
            """Sleep beyond the configured timeout."""
            await asyncio.sleep(1)

        with self.assertRaises(ToolTimeoutError):
            await ToolExecutor(event_sinks=[sink]).execute(
                slow,
                ToolCall(id="call-1", name="slow", arguments={}),
                context=context(),
            )
        self.assertEqual(sink.events[-1].event_type, EventType.TOOL_CALL_FAILED)
        self.assertEqual(sink.events[-1].payload["status"], "timeout")

    async def test_call_name_must_match_selected_tool(self) -> None:
        @tool
        def first() -> None:
            """Do nothing."""

        with self.assertRaises(ToolExecutionError):
            await ToolExecutor().execute(
                first,
                ToolCall(id="call-1", name="second", arguments={}),
                context=context(),
            )

    async def test_custom_tool_result_is_correlated_to_call(self) -> None:
        class CustomTool:
            @property
            def definition(self):  # type: ignore[no-untyped-def]
                return self._definition

            def __init__(self) -> None:
                @tool(name="custom")
                def placeholder() -> None:
                    """Provide metadata."""

                self._definition = placeholder.definition

            async def invoke(self, arguments, *, context):  # type: ignore[no-untyped-def]
                return ToolResult(
                    call_id="internal",
                    tool_name="custom",
                    status=ToolResultStatus.SUCCEEDED,
                    content=arguments["value"],
                )

        result = await ToolExecutor().execute(
            CustomTool(),
            ToolCall(id="external", name="custom", arguments={"value": 4}),
            context=context(),
        )
        self.assertEqual(result.call_id, "external")
        self.assertEqual(result.content, 4)

    async def test_concurrency_limit_is_enforced(self) -> None:
        active = 0
        peak = 0

        @tool(concurrency_limit=1)
        async def guarded(value: int) -> int:
            """Track concurrent executions."""
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            await asyncio.sleep(0.01)
            active -= 1
            return value

        executor = ToolExecutor()
        await asyncio.gather(
            *[
                executor.execute(
                    guarded,
                    ToolCall(id=f"call-{index}", name="guarded", arguments={"value": index}),
                    context=context(),
                )
                for index in range(3)
            ]
        )
        self.assertEqual(peak, 1)

    async def test_cancellation_is_emitted_and_propagated(self) -> None:
        sink = MemorySink()
        started = asyncio.Event()

        @tool
        async def waiting() -> None:
            """Wait until cancelled."""
            started.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(
            ToolExecutor(event_sinks=[sink]).execute(
                waiting,
                ToolCall(id="call-1", name="waiting", arguments={}),
                context=context(),
            )
        )
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertEqual(sink.events[-1].payload["status"], "cancelled")

    async def test_generic_execution_failure_is_normalized(self) -> None:
        class BrokenTool:
            def __init__(self) -> None:
                @tool(name="broken")
                def placeholder() -> None:
                    """Provide metadata."""

                self._definition = placeholder.definition

            @property
            def definition(self):  # type: ignore[no-untyped-def]
                return self._definition

            async def invoke(self, arguments: dict[str, Any], *, context):  # type: ignore[no-untyped-def]
                raise RuntimeError("private")

        with self.assertRaisesRegex(ToolExecutionError, "Tool 'broken' execution failed"):
            await ToolExecutor().execute(
                BrokenTool(),
                ToolCall(id="call-1", name="broken", arguments={}),
                context=context(),
            )
