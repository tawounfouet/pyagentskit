"""Ordered event dispatch and dependency-free local sinks."""

from __future__ import annotations

import inspect
from collections.abc import Callable, Iterable
from typing import Any, TextIO

from .events import AgentEvent
from .exceptions import PyAgentsKitError


class EventBus:
    """Dispatch isolated copies; explicitly raise or record consumer failures."""

    def __init__(
        self, sinks: Iterable[Any] = (), *, fail_fast: bool = True, secrets: Iterable[str] = ()
    ) -> None:
        self.sinks = tuple(sinks)
        self.fail_fast = fail_fast
        self.secrets = tuple(value for value in secrets if value)
        self.failures = 0

    async def emit(self, event: AgentEvent) -> None:
        payload = event.model_dump_json()
        # Redact JSON string values without corrupting JSON escape sequences.
        import json

        def clean(value: Any) -> Any:
            if isinstance(value, str):
                for secret in self.secrets:
                    value = value.replace(secret, "[REDACTED]")
            elif isinstance(value, dict):
                value = {key: clean(item) for key, item in value.items()}
            elif isinstance(value, list):
                value = [clean(item) for item in value]
            return value

        sanitized = AgentEvent.model_validate_json(json.dumps(clean(json.loads(payload))))
        for sink in self.sinks:
            try:
                consumer: Callable[..., Any] = (
                    getattr(sink, "emit", None) or getattr(sink, "handle", None) or sink
                )
                result = consumer(sanitized.model_copy(deep=True))
                if inspect.isawaitable(result):
                    await result
            except Exception:
                self.failures += 1
                if self.fail_fast:
                    raise PyAgentsKitError("Event consumer failed") from None


class MemoryEventSink:
    def __init__(self) -> None:
        self.events: list[AgentEvent] = []

    async def emit(self, event: AgentEvent) -> None:
        self.events.append(event.model_copy(deep=True))


class JsonLinesEventSink:
    """Write to an application-owned stream; caller owns closing and retention."""

    def __init__(self, stream: TextIO) -> None:
        self.stream = stream

    async def emit(self, event: AgentEvent) -> None:
        self.stream.write(event.model_dump_json() + "\n")
        self.stream.flush()


class ConsoleEventSink:
    def __init__(self, stream: TextIO, *, verbose: bool = False) -> None:
        self.stream = stream
        self.verbose = verbose

    async def emit(self, event: AgentEvent) -> None:
        timestamp = event.occurred_at.astimezone().strftime("%Y-%m-%d %H:%M:%S")
        scope = f"run={str(event.run_id)[:8]} agent={event.agent_id}"
        if "tool_name" in event.payload:
            scope += f" tool={event.payload['tool_name']}"
        self.stream.write(f"{timestamp}  INFO  [{scope}] {event.event_type.value}\n")
        if self.verbose:
            self.stream.write(f"{timestamp}  DEBUG  [{scope}] {event.model_dump_json()}\n")
        self.stream.flush()
