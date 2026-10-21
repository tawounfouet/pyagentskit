"""Function-backed implementation of the Tool protocol."""

from __future__ import annotations

import asyncio
import inspect
from collections.abc import Callable
from typing import Any
from uuid import uuid4

from ._tool_schema import CallableSchema, compile_callable_schema
from .exceptions import ToolError, ToolExecutionError, ToolValidationError
from .runs import RunContext
from .tools import ToolDefinition, ToolResult, ToolResultStatus, ToolRisk


class FunctionTool:
    """A typed Python callable exposed through the provider-neutral Tool port."""

    def __init__(
        self,
        function: Callable[..., Any],
        definition: ToolDefinition,
        schema: CallableSchema,
    ) -> None:
        self._function = function
        self._definition = definition
        self._schema = schema

    @property
    def definition(self) -> ToolDefinition:
        """Return immutable schema and governance metadata."""

        return self._definition

    @property
    def wrapped(self) -> Callable[..., Any]:
        """Return the original callable for introspection and testing."""

        return self._function

    async def invoke(
        self,
        arguments: dict[str, Any],
        *,
        context: RunContext[Any],
    ) -> ToolResult:
        """Validate and invoke the wrapped callable."""

        return await self._invoke(arguments, context=context, call_id=str(uuid4()))

    async def _invoke(
        self,
        arguments: dict[str, Any],
        *,
        context: RunContext[Any],
        call_id: str,
    ) -> ToolResult:
        values = self._schema.validate_arguments(arguments)
        if self._schema.context_parameter is not None:
            values[self._schema.context_parameter] = context

        try:
            if inspect.iscoroutinefunction(self._function):
                raw_result = await self._function(**values)
            else:
                raw_result = await asyncio.to_thread(self._function, **values)
            content = self._schema.validate_result(raw_result)
        except ToolError:
            raise
        except Exception as error:
            raise ToolExecutionError(f"Tool '{self.definition.name}' execution failed") from error

        return ToolResult(
            call_id=call_id,
            tool_name=self.definition.name,
            status=ToolResultStatus.SUCCEEDED,
            content=content,
        )


def create_function_tool(
    function: Callable[..., Any],
    *,
    name: str | None,
    version: str,
    description: str | None,
    risk: ToolRisk | str,
    idempotent: bool,
    requires_approval: bool,
    timeout_seconds: float,
    concurrency_limit: int | None,
    tags: tuple[str, ...],
    metadata: dict[str, Any] | None,
) -> FunctionTool:
    """Build a validated FunctionTool from decorator options."""

    schema = compile_callable_schema(function)
    resolved_description = description or inspect.getdoc(function)
    if not resolved_description:
        raise ToolValidationError("Tool functions require a description or docstring")

    definition = ToolDefinition(
        name=name or function.__name__,
        version=version,
        description=resolved_description,
        input_schema=schema.input_schema,
        output_schema=schema.output_schema,
        risk=ToolRisk(risk),
        idempotent=idempotent,
        requires_approval=requires_approval,
        timeout_seconds=timeout_seconds,
        concurrency_limit=concurrency_limit,
        tags=tags,
        metadata={} if metadata is None else metadata,
    )
    return FunctionTool(function, definition, schema)
