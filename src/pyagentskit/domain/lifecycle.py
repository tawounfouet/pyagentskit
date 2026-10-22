"""Explicit state machines for the V2 P0 aggregates."""

from enum import StrEnum


class RunStatus(StrEnum):
    CREATED = "created"
    RUNNING = "running"
    WAITING = "waiting"
    PAUSED = "paused"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in {self.SUCCEEDED, self.FAILED, self.CANCELLED}


class EffectStatus(StrEnum):
    NOT_STARTED = "not_started"
    STARTED = "started"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    UNKNOWN = "unknown"

    @property
    def is_terminal(self) -> bool:
        return self in {self.SUCCEEDED, self.FAILED, self.UNKNOWN}


class ApprovalStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self is not ApprovalStatus.PENDING


class ApprovalScope(StrEnum):
    EFFECT = "effect"
    RUN = "run"
    SESSION = "session"


class LeaseStatus(StrEnum):
    AVAILABLE = "available"
    HELD = "held"
    RELEASED = "released"
    EXPIRED = "expired"


class RuntimeCapability(StrEnum):
    INVOKE = "invoke"
    STREAM = "stream"
    TOOLS = "tools"
    STRUCTURED_OUTPUT = "structured_output"
    PAUSE = "pause"
    RESUME = "resume"


RUN_TRANSITIONS = {
    RunStatus.CREATED: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.RUNNING: {
        RunStatus.WAITING,
        RunStatus.PAUSED,
        RunStatus.SUCCEEDED,
        RunStatus.FAILED,
        RunStatus.CANCELLED,
    },
    RunStatus.WAITING: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.PAUSED: {RunStatus.RUNNING, RunStatus.CANCELLED},
    RunStatus.SUCCEEDED: set(),
    RunStatus.FAILED: set(),
    RunStatus.CANCELLED: set(),
}

EFFECT_TRANSITIONS = {
    EffectStatus.NOT_STARTED: {EffectStatus.STARTED},
    EffectStatus.STARTED: {
        EffectStatus.SUCCEEDED,
        EffectStatus.FAILED,
        EffectStatus.UNKNOWN,
    },
    EffectStatus.SUCCEEDED: set(),
    EffectStatus.FAILED: set(),
    EffectStatus.UNKNOWN: set(),
}
