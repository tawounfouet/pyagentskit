from __future__ import annotations

import asyncio
import threading
import unittest
from enum import StrEnum
from typing import Any

from pydantic import ValidationError

from pyagentskit import (
    FunctionTool,
    RunContext,
    ToolExecutionError,
    ToolResultStatus,
    ToolRisk,
    ToolValidationError,
    tool,
)


class Unit(StrEnum):
    CELSIUS = "celsius"
    FAHRENHEIT = "fahrenheit"


def context() -> RunContext[dict[str, str]]:
    return RunContext(agent_id="test.agent", deps={"tenant": "acme"})


class ToolDecoratorTests(unittest.IsolatedAsyncioTestCase):
    async def test_async_function_is_declared_and_invoked(self) -> None:
        @tool(risk="read", idempotent=True, tags=("weather",))
        async def weather(
            city: str,
            unit: Unit = Unit.CELSIUS,
            run_context: RunContext[dict[str, str]] | None = None,
        ) -> str:
            """Return the current weather."""
            tenant = "none" if run_context is None else run_context.deps["tenant"]
            return f"{city}:{unit.value}:{tenant}"

        self.assertIsInstance(weather, FunctionTool)
        self.assertEqual(weather.definition.name, "weather")
        self.assertEqual(weather.definition.risk, ToolRisk.READ)
        self.assertTrue(weather.definition.idempotent)
        properties = weather.definition.input_schema["properties"]
        self.assertIn("city", properties)
        # Optional RunContext is not treated as injectable; explicit contexts must be exact.
        self.assertIn("run_context", properties)

        result = await weather.invoke({"city": "Paris", "run_context": None}, context=context())
        self.assertEqual(result.status, ToolResultStatus.SUCCEEDED)
        self.assertEqual(result.content, "Paris:celsius:none")

    async def test_exact_run_context_is_injected_and_hidden_from_schema(self) -> None:
        @tool
        def tenant_name(value: int, context: RunContext[dict[str, str]]) -> str:
            """Return a value scoped to the current tenant."""
            return f"{context.deps['tenant']}:{value}"

        self.assertNotIn("context", tenant_name.definition.input_schema["properties"])
        result = await tenant_name.invoke({"value": 3}, context=context())
        self.assertEqual(result.content, "acme:3")

    async def test_sync_function_runs_outside_event_loop_thread(self) -> None:
        event_loop_thread = threading.get_ident()

        @tool
        def thread_id() -> int:
            """Return the worker thread identifier."""
            return threading.get_ident()

        result = await thread_id.invoke({}, context=context())
        self.assertNotEqual(result.content, event_loop_thread)

    async def test_arguments_are_strict_and_extra_fields_are_forbidden(self) -> None:
        @tool
        def double(value: int) -> int:
            """Double an integer."""
            return value * 2

        with self.assertRaises(ToolValidationError):
            await double.invoke({"value": "2"}, context=context())
        with self.assertRaises(ToolValidationError):
            await double.invoke({"value": 2, "extra": True}, context=context())

    async def test_result_annotation_is_validated(self) -> None:
        @tool
        def broken() -> int:
            """Return an intentionally invalid result."""
            return "not-an-int"  # type: ignore[return-value]

        with self.assertRaises(ToolValidationError):
            await broken.invoke({}, context=context())

    async def test_user_exception_is_normalized_without_message_leak(self) -> None:
        @tool
        def explode() -> None:
            """Raise a private implementation error."""
            raise RuntimeError("secret implementation detail")

        with self.assertRaisesRegex(
            ToolExecutionError, "Tool 'explode' execution failed"
        ) as caught:
            await explode.invoke({}, context=context())
        self.assertNotIn("secret", str(caught.exception))

    def test_decorator_options_override_defaults(self) -> None:
        @tool(
            name="weather.current",
            version="2.1.0",
            description="Read the current weather.",
            risk=ToolRisk.READ,
            timeout_seconds=4.5,
            concurrency_limit=2,
            metadata={"owner": "platform"},
        )
        def weather(city: str) -> dict[str, Any]:
            return {"city": city}

        definition = weather.definition
        self.assertEqual(definition.name, "weather.current")
        self.assertEqual(definition.version, "2.1.0")
        self.assertEqual(definition.timeout_seconds, 4.5)
        self.assertEqual(definition.concurrency_limit, 2)
        self.assertEqual(definition.metadata, {"owner": "platform"})
        self.assertEqual(definition.output_schema["type"], "object")

    def test_untyped_parameter_is_rejected(self) -> None:
        with self.assertRaises(ToolValidationError):

            @tool
            def invalid(value):  # type: ignore[no-untyped-def]
                """Invalid untyped tool."""
                return value

    def test_variadic_and_positional_only_parameters_are_rejected(self) -> None:
        with self.assertRaises(ToolValidationError):

            @tool
            def variadic(*values: int) -> int:
                """Invalid variadic tool."""
                return sum(values)

        with self.assertRaises(ToolValidationError):

            @tool
            def positional(value: int, /) -> int:
                """Invalid positional-only tool."""
                return value

    def test_missing_description_is_rejected(self) -> None:
        def undocumented(value: int) -> int:
            return value

        with self.assertRaises(ToolValidationError):
            tool(undocumented)

    def test_unresolved_annotation_is_rejected(self) -> None:
        namespace: dict[str, Any] = {}
        exec("def unresolved(value: 'MissingType'):\n    'Doc.'\n    return value", namespace)
        with self.assertRaises(ToolValidationError):
            tool(namespace["unresolved"])

    def test_security_invariant_still_applies_to_decorator(self) -> None:
        with self.assertRaises(ValidationError):

            @tool(risk=ToolRisk.DESTRUCTIVE)
            def erase(identifier: str) -> None:
                """Erase a resource."""

    async def test_cancellation_is_not_wrapped(self) -> None:
        started = asyncio.Event()

        @tool
        async def wait_forever() -> None:
            """Wait until cancelled."""
            started.set()
            await asyncio.Event().wait()

        task = asyncio.create_task(wait_forever.invoke({}, context=context()))
        await started.wait()
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
