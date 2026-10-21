"""Versioned structured event contracts."""

from datetime import datetime
from enum import StrEnum
from typing import Any, Literal, Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from ._base import ContractModel
from .types import Identifier


class EventType(StrEnum):
    """Initial event vocabulary reserved by the runtime architecture."""

    RUN_CREATED = "run.created"
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    RUN_FAILED = "run.failed"
    RUN_CANCELLED = "run.cancelled"
    RUN_LIMIT_EXCEEDED = "run.limit_exceeded"
    RUN_WAITING_APPROVAL = "run.waiting_approval"
    STEP_STARTED = "step.started"
    STEP_COMPLETED = "step.completed"
    MODEL_REQUEST_STARTED = "model.request.started"
    MODEL_RESPONSE_COMPLETED = "model.response.completed"
    MODEL_REQUEST_FAILED = "model.request.failed"
    TOOL_CALL_REQUESTED = "tool.call.requested"
    TOOL_CALL_STARTED = "tool.call.started"
    TOOL_CALL_COMPLETED = "tool.call.completed"
    TOOL_CALL_FAILED = "tool.call.failed"
    GUARDRAIL_EVALUATED = "guardrail.evaluated"
    GUARDRAIL_REJECTED = "guardrail.rejected"
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_RESOLVED = "approval.resolved"
    APPROVAL_CLAIMED = "approval.claimed"
    APPROVAL_EXECUTED = "approval.executed"
    PRIVACY_POLICY_EVALUATED = "privacy.policy.evaluated"
    ARTIFACT_CREATED = "artifact.created"
    SESSION_LOADED = "session.loaded"
    SESSION_UPDATED = "session.updated"
    CONTEXT_SELECTED = "context.selected"
    USAGE_UPDATED = "usage.updated"


class AgentEvent(ContractModel):
    """Immutable envelope for an observable runtime fact."""

    schema_version: Literal["1.0"] = "1.0"
    event_id: UUID = Field(default_factory=uuid4)
    event_type: EventType
    occurred_at: datetime
    run_id: UUID
    trace_id: UUID
    agent_id: Identifier
    session_id: str | None = None
    step: int | None = Field(default=None, ge=0)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("occurred_at")
    @classmethod
    def validate_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            msg = "occurred_at must be timezone-aware"
            raise ValueError(msg)
        return value


@runtime_checkable
class EventHandler(Protocol):
    """Asynchronous consumer of immutable agent events."""

    async def handle(self, event: AgentEvent) -> None:
        """Process one event without mutating runtime state."""
        ...
