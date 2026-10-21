"""Governed execution of registered tools."""

from __future__ import annotations

import asyncio
import math
from collections.abc import Iterable
from datetime import UTC, datetime
from time import monotonic
from typing import Any, Protocol

from .events import AgentEvent, EventType
from .exceptions import ToolError, ToolExecutionError, ToolPermissionError, ToolTimeoutError
from .runs import RunContext
from .tools import ToolCall, ToolExecutionPolicy, ToolResult


class _ToolLike(Protocol):
    @property
    def definition(self) -> Any: ...

    async def invoke(
        self,
        arguments: dict[str, Any],
        *,
        context: RunContext[Any],
    ) -> ToolResult: ...


class _EventSinkLike(Protocol):
    async def emit(self, event: AgentEvent) -> None: ...


class ToolExecutor:
    """Apply policy, timeout, concurrency and event boundaries to a tool call."""

    def __init__(
        self,
        *,
        policies: Iterable[ToolExecutionPolicy] = (),
        event_sinks: Iterable[_EventSinkLike] = (),
    ) -> None:
        self._policies = tuple(policies)
        self._event_sinks = tuple(event_sinks)
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    @property
    def policies(self) -> tuple[ToolExecutionPolicy, ...]:
        """Return the immutable policy chain used by this executor."""

        return self._policies

    @property
    def event_sinks(self) -> tuple[_EventSinkLike, ...]:
        """Return the immutable tool-level event sinks."""

        return self._event_sinks

    async def execute(
        self,
        tool: _ToolLike,
        call: ToolCall,
        *,
        context: RunContext[Any],
        timeout_seconds: float | None = None,
        approved: bool = False,
    ) -> ToolResult:
        """Execute one call and either return a normalized result or raise ToolError."""

        if call.name != tool.definition.name:
            raise ToolExecutionError("Tool call name does not match the selected tool")

        limit = tool.definition.timeout_seconds if timeout_seconds is None else timeout_seconds
        if not math.isfinite(limit) or limit <= 0:
            raise ToolExecutionError("Tool timeout must be finite and positive")
        if tool.definition.requires_approval and not approved:
            raise ToolPermissionError("Tool execution requires a verified approval")

        for policy in self._policies:
            try:
                await policy.before_execute(call, tool.definition, context=context)
            except ToolPermissionError:
                raise
            except Exception as error:
                raise ToolPermissionError("Tool execution policy failed") from error

        await self._emit(EventType.TOOL_CALL_STARTED, call, context)
        started = monotonic()
        semaphore = self._semaphore_for(tool)
        try:
            async with asyncio.timeout(limit):
                async with semaphore:
                    result = await self._invoke(tool, call, context)
        except TimeoutError as error:
            await self._emit(
                EventType.TOOL_CALL_FAILED,
                call,
                context,
                status="timeout",
                duration_seconds=monotonic() - started,
            )
            raise ToolTimeoutError(f"Tool '{call.name}' exceeded its {limit:g}s timeout") from error
        except asyncio.CancelledError:
            await self._emit(
                EventType.TOOL_CALL_FAILED,
                call,
                context,
                status="cancelled",
                duration_seconds=monotonic() - started,
            )
            raise
        except ToolError:
            await self._emit(
                EventType.TOOL_CALL_FAILED,
                call,
                context,
                status="failed",
                duration_seconds=monotonic() - started,
            )
            raise
        except Exception as error:
            await self._emit(
                EventType.TOOL_CALL_FAILED,
                call,
                context,
                status="failed",
                duration_seconds=monotonic() - started,
            )
            raise ToolExecutionError(f"Tool '{call.name}' execution failed") from error

        for policy in self._policies:
            try:
                result = await policy.after_execute(call, tool.definition, result, context=context)
            except ToolError:
                raise
            except Exception as error:
                raise ToolExecutionError("Tool result policy failed") from error

        await self._emit(
            EventType.TOOL_CALL_COMPLETED,
            call,
            context,
            status=result.status.value,
            duration_seconds=monotonic() - started,
        )
        return result

    async def _invoke(
        self,
        tool: _ToolLike,
        call: ToolCall,
        context: RunContext[Any],
    ) -> ToolResult:
        from ._tool_function import FunctionTool

        if isinstance(tool, FunctionTool):
            return await tool._invoke(call.arguments, context=context, call_id=call.id)
        result = await tool.invoke(call.arguments, context=context)
        return result.model_copy(update={"call_id": call.id, "tool_name": call.name})

    def _semaphore_for(self, tool: _ToolLike) -> asyncio.Semaphore:
        limit = tool.definition.concurrency_limit
        if limit is None:
            return asyncio.Semaphore(1_000_000)
        semaphore = self._semaphores.get(tool.definition.name)
        if semaphore is None:
            semaphore = asyncio.Semaphore(limit)
            self._semaphores[tool.definition.name] = semaphore
        return semaphore

    async def _emit(
        self,
        event_type: EventType,
        call: ToolCall,
        context: RunContext[Any],
        **payload: Any,
    ) -> None:
        if not self._event_sinks:
            return
        event = AgentEvent(
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            run_id=context.run_id,
            trace_id=context.trace_id,
            agent_id=context.agent_id,
            session_id=context.session_id,
            payload={"call_id": call.id, "tool_name": call.name, **payload},
        )
        for sink in self._event_sinks:
            await sink.emit(event)
