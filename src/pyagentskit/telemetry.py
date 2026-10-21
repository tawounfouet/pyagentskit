"""Local runtime metrics and optional OpenTelemetry event bridge."""

from __future__ import annotations

import importlib
from contextlib import suppress
from decimal import Decimal, InvalidOperation
from typing import Any, ClassVar, Protocol
from uuid import UUID

from pydantic import Field

from ._base import ContractModel
from .events import AgentEvent, EventType

__all__ = ["OpenTelemetryEventSink", "RuntimeMetrics", "RuntimeMetricsSink"]


class RuntimeMetrics(ContractModel):
    runs_started: int = Field(default=0, ge=0)
    runs_completed: int = Field(default=0, ge=0)
    runs_failed: int = Field(default=0, ge=0)
    runs_cancelled: int = Field(default=0, ge=0)
    runs_limited: int = Field(default=0, ge=0)
    approvals_waiting: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    model_attempts: int = Field(default=0, ge=0)
    model_retries: int = Field(default=0, ge=0)
    model_failures: int = Field(default=0, ge=0)
    streams_completed: int = Field(default=0, ge=0)
    stream_events: int = Field(default=0, ge=0)
    stream_failures: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    tool_failures: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    estimated_cost_usd: float = Field(default=0.0, ge=0)


class RuntimeMetricsSink:
    """Dependency-free event sink exposing an immutable metrics snapshot."""

    def __init__(self) -> None:
        self._counts: dict[str, int | float] = {
            name: field.default
            for name, field in RuntimeMetrics.model_fields.items()
            if field.default is not None
        }

    async def emit(self, event: AgentEvent) -> None:
        increments = {
            EventType.RUN_STARTED: "runs_started",
            EventType.RUN_COMPLETED: "runs_completed",
            EventType.RUN_FAILED: "runs_failed",
            EventType.RUN_CANCELLED: "runs_cancelled",
            EventType.RUN_LIMIT_EXCEEDED: "runs_limited",
            EventType.RUN_WAITING_APPROVAL: "approvals_waiting",
            EventType.MODEL_RESPONSE_COMPLETED: "model_calls",
            EventType.MODEL_REQUEST_FAILED: "model_failures",
            EventType.TOOL_CALL_COMPLETED: "tool_calls",
            EventType.TOOL_CALL_FAILED: "tool_failures",
        }
        key = increments.get(event.event_type)
        if key is not None:
            self._counts[key] = int(self._counts[key]) + 1
        if event.event_type is EventType.MODEL_REQUEST_STARTED:
            self._counts["model_attempts"] = int(self._counts["model_attempts"]) + 1
            if event.payload.get("is_retry") is True:
                self._counts["model_retries"] = int(self._counts["model_retries"]) + 1
        if (
            event.event_type
            in {
                EventType.MODEL_RESPONSE_COMPLETED,
                EventType.MODEL_REQUEST_FAILED,
            }
            and event.payload.get("streaming") is True
        ):
            event_count = event.payload.get("stream_event_count", 0)
            if isinstance(event_count, int) and event_count >= 0:
                self._counts["stream_events"] = int(self._counts["stream_events"]) + event_count
            stream_key = (
                "streams_completed"
                if event.event_type is EventType.MODEL_RESPONSE_COMPLETED
                else "stream_failures"
            )
            self._counts[stream_key] = int(self._counts[stream_key]) + 1
        if event.event_type is EventType.USAGE_UPDATED:
            usage = event.payload.get("usage", {})
            if isinstance(usage, dict):
                self._counts["input_tokens"] = int(usage.get("input_tokens", 0))
                self._counts["output_tokens"] = int(usage.get("output_tokens", 0))
                cost = usage.get("estimated_cost_usd")
                if isinstance(cost, int | float | str | Decimal):
                    with suppress(InvalidOperation):
                        self._counts["estimated_cost_usd"] = float(Decimal(str(cost)))

    def snapshot(self) -> RuntimeMetrics:
        return RuntimeMetrics.model_validate(self._counts)


class _Span(Protocol):
    def set_attribute(self, name: str, value: Any) -> None: ...

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None: ...

    def end(self, end_time: int | None = None) -> None: ...


class _Tracer(Protocol):
    def start_span(self, name: str, *, attributes: dict[str, Any] | None = None) -> _Span: ...


class OpenTelemetryEventSink:
    """Map safe runtime events to spans without requiring an SDK/exporter."""

    _terminal: ClassVar[set[EventType]] = {
        EventType.RUN_COMPLETED,
        EventType.RUN_FAILED,
        EventType.RUN_CANCELLED,
        EventType.RUN_LIMIT_EXCEEDED,
        EventType.RUN_WAITING_APPROVAL,
    }

    def __init__(self, tracer: _Tracer | None = None) -> None:
        if tracer is None:
            try:
                trace = importlib.import_module("opentelemetry.trace")
            except ImportError as exc:
                raise RuntimeError("Install pyagentskit[opentelemetry] or inject a tracer") from exc
            tracer = trace.get_tracer("pyagentskit")
        self.tracer = tracer
        self._spans: dict[UUID, _Span] = {}

    async def emit(self, event: AgentEvent) -> None:
        attributes = {
            "pyagentskit.run_id": str(event.run_id),
            "pyagentskit.trace_id": str(event.trace_id),
            "pyagentskit.agent_id": event.agent_id,
            "pyagentskit.event_type": event.event_type.value,
        }
        if event.event_type is EventType.RUN_STARTED:
            self._spans[event.run_id] = self.tracer.start_span(
                "pyagentskit.run", attributes=attributes
            )
        span = self._spans.get(event.run_id)
        if span is None:
            return
        span.add_event(event.event_type.value, attributes=attributes)
        if event.event_type in self._terminal:
            span.set_attribute("pyagentskit.run.status", event.event_type.value)
            span.end()
            self._spans.pop(event.run_id, None)
