"""Run limits, context and result contracts."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Generic, TypeVar
from uuid import UUID, uuid4

from pydantic import Field, model_validator

from ._base import ContractModel
from .artifacts import ArtifactRef
from .types import Identifier, NonEmptyString
from .usage import Usage

DependenciesT = TypeVar("DependenciesT")
OutputT = TypeVar("OutputT")


def utc_now() -> datetime:
    """Return an aware UTC timestamp."""

    return datetime.now(UTC)


class RunLimits(ContractModel):
    """Finite safety and resource limits for one agent run."""

    max_steps: int = Field(default=8, gt=0)
    max_model_calls: int = Field(default=8, gt=0)
    max_tool_calls: int = Field(default=16, ge=0)
    max_parallel_tools: int = Field(default=4, gt=0)
    timeout_seconds: float = Field(default=120.0, gt=0)
    max_input_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    max_total_tokens: int | None = Field(default=None, gt=0)
    max_cost_usd: float | None = Field(default=None, gt=0)


class RunStatus(StrEnum):
    """Lifecycle states shared by runtime implementations and stores."""

    CREATED = "created"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    LIMIT_EXCEEDED = "limit_exceeded"
    UNKNOWN_EFFECT = "unknown_effect"

    @property
    def is_terminal(self) -> bool:
        """Return whether the state may be represented by a final RunResult."""

        return self in {
            RunStatus.COMPLETED,
            RunStatus.FAILED,
            RunStatus.CANCELLED,
            RunStatus.LIMIT_EXCEEDED,
            RunStatus.WAITING_APPROVAL,
            RunStatus.UNKNOWN_EFFECT,
        }


@dataclass(frozen=True, slots=True)
class RunContext(Generic[DependenciesT]):
    """Non-prompt application context available during one run."""

    agent_id: str
    deps: DependenciesT
    run_id: UUID = field(default_factory=uuid4)
    trace_id: UUID = field(default_factory=uuid4)
    session_id: str | None = None
    started_at: datetime = field(default_factory=utc_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.agent_id:
            msg = "agent_id cannot be empty"
            raise ValueError(msg)
        if self.started_at.tzinfo is None or self.started_at.utcoffset() is None:
            msg = "started_at must be timezone-aware"
            raise ValueError(msg)


class RunError(ContractModel):
    """Serializable error attached to a terminal run."""

    type: Identifier
    message: NonEmptyString
    retryable: bool = False
    details: dict[str, Any] = Field(default_factory=dict)


class RunResult(ContractModel, Generic[OutputT]):
    """Final, serializable outcome of an agent run."""

    run_id: UUID
    trace_id: UUID
    agent_id: Identifier
    status: RunStatus
    output: OutputT | None = None
    error: RunError | None = None
    usage: Usage = Field(default_factory=Usage)
    artifacts: tuple[ArtifactRef, ...] = ()
    started_at: datetime
    completed_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_terminal_result(self) -> "RunResult[OutputT]":
        if not self.status.is_terminal:
            msg = "RunResult requires a terminal status"
            raise ValueError(msg)
        for field_name, value in {
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }.items():
            if value.tzinfo is None or value.utcoffset() is None:
                msg = f"{field_name} must be timezone-aware"
                raise ValueError(msg)
        if self.completed_at < self.started_at:
            msg = "completed_at cannot precede started_at"
            raise ValueError(msg)
        if self.status is RunStatus.COMPLETED and self.error is not None:
            msg = "a completed run cannot contain an error"
            raise ValueError(msg)
        if self.status is RunStatus.FAILED and self.error is None:
            msg = "a failed run requires an error"
            raise ValueError(msg)
        if self.status is RunStatus.WAITING_APPROVAL and self.output is not None:
            msg = "a waiting run cannot contain final output"
            raise ValueError(msg)
        return self
