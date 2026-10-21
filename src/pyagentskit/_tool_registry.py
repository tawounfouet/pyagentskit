"""Registration and lookup for governed tools."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any
from uuid import uuid4

from ._tool_execution import ToolExecutor
from .exceptions import ToolAlreadyRegisteredError, ToolNotFoundError
from .runs import RunContext
from .tools import ToolCall, ToolDefinition, ToolResult


class ToolRegistry:
    """Mutable registry with explicit duplicate and replacement semantics."""

    def __init__(
        self,
        tools: Iterable[Any] = (),
        *,
        executor: ToolExecutor | None = None,
    ) -> None:
        self._tools: dict[str, Any] = {}
        self._executor = executor or ToolExecutor()
        for item in tools:
            self.register(item)

    def register(self, tool: Any, *, replace: bool = False) -> None:
        """Register a Tool implementation by its declared name."""

        name = tool.definition.name
        if name in self._tools and not replace:
            raise ToolAlreadyRegisteredError(f"Tool '{name}' is already registered")
        self._tools[name] = tool

    def unregister(self, name: str) -> Any:
        """Remove and return a tool, raising when it is unknown."""

        try:
            return self._tools.pop(name)
        except KeyError as error:
            raise ToolNotFoundError(f"Tool '{name}' is not registered") from error

    def get(self, name: str) -> Any:
        """Return a registered tool by name."""

        try:
            return self._tools[name]
        except KeyError as error:
            raise ToolNotFoundError(f"Tool '{name}' is not registered") from error

    def names(self) -> tuple[str, ...]:
        """Return registered names in deterministic lexical order."""

        return tuple(sorted(self._tools))

    def definitions(self) -> tuple[ToolDefinition, ...]:
        """Return definitions in deterministic lexical order."""

        return tuple(self._tools[name].definition for name in self.names())

    @property
    def executor(self) -> ToolExecutor:
        """Return the executor so wrappers can preserve its policies and sinks."""

        return self._executor

    def __contains__(self, name: object) -> bool:
        return name in self._tools

    def __len__(self) -> int:
        return len(self._tools)

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        *,
        context: RunContext[Any],
        call_id: str | None = None,
        timeout_seconds: float | None = None,
        approved: bool = False,
    ) -> ToolResult:
        """Build and execute a normalized call against a registered tool."""

        call = ToolCall(
            id=call_id or str(uuid4()),
            name=name,
            arguments=arguments,
        )
        return await self.execute_call(
            call,
            context=context,
            timeout_seconds=timeout_seconds,
            approved=approved,
        )

    async def execute_call(
        self,
        call: ToolCall,
        *,
        context: RunContext[Any],
        timeout_seconds: float | None = None,
        approved: bool = False,
    ) -> ToolResult:
        """Execute an existing normalized call."""

        selected = self.get(call.name)
        return await self._executor.execute(
            selected,
            call,
            context=context,
            timeout_seconds=timeout_seconds,
            approved=approved,
        )
