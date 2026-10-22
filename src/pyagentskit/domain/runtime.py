"""Provider-neutral runtime integration contracts.

The objects in this module are intentionally opaque about runtime internals. They
describe the guarantees exposed at the PyAgentsKit boundary, not how a runtime
implements them.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from enum import IntEnum, StrEnum
from typing import Any
from uuid import uuid4

from .lifecycle import RuntimeCapability
from .shared import OwnershipContext, RunId, utc_now


class SideEffectControlLevel(IntEnum):
    """How completely PyAgentsKit can control externally visible actions."""

    OPAQUE = 0
    BOUNDED = 1
    FULL = 2


class RuntimeQualificationLevel(IntEnum):
    """Evidence level attached to an adapter descriptor."""

    L0 = 0
    L1 = 1
    L2 = 2
    L3 = 3
    L4 = 4


@dataclass(frozen=True, slots=True)
class RuntimeIdentity:
    """Stable identity independent from a concrete adapter instance."""

    namespace: str
    name: str
    contract_major: int = 1
    variant: str | None = None

    def __post_init__(self) -> None:
        if not self.namespace or not self.name or self.contract_major < 1:
            raise ValueError("runtime identity namespace, name and contract_major are required")

    @property
    def canonical(self) -> str:
        suffix = f"/{self.variant}" if self.variant else ""
        return f"{self.namespace}/{self.name}{suffix}@{self.contract_major}"


class RuntimeStatus(StrEnum):
    CREATED = "created"
    STARTING = "starting"
    RUNNING = "running"
    WAITING = "waiting"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    UNKNOWN = "unknown"

    @property
    def is_terminal(self) -> bool:
        return self in {
            RuntimeStatus.COMPLETED,
            RuntimeStatus.FAILED,
            RuntimeStatus.CANCELLED,
            RuntimeStatus.UNKNOWN,
        }


class RuntimeCancelStatus(StrEnum):
    CANCELLED = "cancelled"
    CANCELLATION_REQUESTED = "cancellation_requested"
    NOT_SUPPORTED = "not_supported"
    ALREADY_TERMINAL = "already_terminal"
    FAILED = "failed"


class RuntimeEventType(StrEnum):
    RUNTIME_STARTED = "runtime.started"
    RUNTIME_WAITING = "runtime.waiting"
    RUNTIME_RESUMED = "runtime.resumed"
    RUNTIME_COMPLETED = "runtime.completed"
    RUNTIME_FAILED = "runtime.failed"
    RUNTIME_CANCELLED = "runtime.cancelled"
    MESSAGE_EMITTED = "message.emitted"
    TOOL_REQUESTED = "tool.requested"
    TOOL_STARTED = "tool.started"
    TOOL_COMPLETED = "tool.completed"
    TOOL_FAILED = "tool.failed"
    CHECKPOINT_AVAILABLE = "checkpoint.available"
    APPROVAL_REQUESTED = "approval.requested"
    DIAGNOSTIC = "diagnostic"


@dataclass(frozen=True, slots=True)
class RuntimeHandle:
    """Serializable opaque reference to one runtime execution."""

    adapter_name: str
    external_id: str
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.adapter_name or not self.external_id:
            raise ValueError("runtime handle adapter_name and external_id are required")


@dataclass(frozen=True, slots=True)
class RuntimeDescriptor:
    """Side-effect-free description of an available runtime adapter."""

    runtime_id: str
    display_name: str
    runtime_family: str
    adapter_version: str
    contract_version: str
    capabilities: frozenset[RuntimeCapability] = frozenset()
    runtime_version: str | None = None
    side_effect_control_level: SideEffectControlLevel = SideEffectControlLevel.OPAQUE
    qualification_level: RuntimeQualificationLevel = RuntimeQualificationLevel.L0
    supported_platforms: tuple[str, ...] = ()
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.runtime_id or any(character.isspace() for character in self.runtime_id):
            raise ValueError("runtime_id must be a non-empty opaque identifier")
        if not self.display_name or not self.runtime_family:
            raise ValueError("runtime display_name and runtime_family are required")
        if not self.adapter_version or not self.contract_version:
            raise ValueError("runtime adapter and contract versions are required")

    @property
    def adapter_name(self) -> str:
        """Compatibility alias for the adapter-facing name."""

        return self.runtime_id


@dataclass(frozen=True, slots=True)
class RuntimeRequirements:
    """Required, preferred and forbidden guarantees for one Run."""

    required_capabilities: frozenset[RuntimeCapability] = frozenset()
    preferred_capabilities: frozenset[RuntimeCapability] = frozenset()
    forbidden_capabilities: frozenset[RuntimeCapability] = frozenset()
    minimum_qualification_level: RuntimeQualificationLevel = RuntimeQualificationLevel.L0
    minimum_side_effect_control: SideEffectControlLevel = SideEffectControlLevel.OPAQUE
    runtime_family: str | None = None
    runtime_id: str | None = None
    runtime_version: str | None = None
    platform: str | None = None

    def __post_init__(self) -> None:
        if self.required_capabilities & self.forbidden_capabilities:
            raise ValueError("a capability cannot be both required and forbidden")
        if self.runtime_id is not None and not self.runtime_id:
            raise ValueError("runtime_id cannot be empty")


@dataclass(frozen=True, slots=True)
class RuntimeSelectionPolicy:
    """Deterministic policy applied after hard requirements are satisfied."""

    preferred_runtime_ids: tuple[str, ...] = ()
    prefer_highest_qualification: bool = True
    prefer_full_control: bool = True
    policy_version: str = "1"


class RejectionReason(StrEnum):
    MISSING_REQUIRED_CAPABILITY = "missing_required_capability"
    FORBIDDEN_CAPABILITY = "forbidden_capability"
    QUALIFICATION_TOO_LOW = "qualification_too_low"
    SIDE_EFFECT_CONTROL_TOO_WEAK = "side_effect_control_too_weak"
    VERSION_INCOMPATIBLE = "version_incompatible"
    PLATFORM_INCOMPATIBLE = "platform_incompatible"
    RUNTIME_FAMILY_MISMATCH = "runtime_family_mismatch"
    RUNTIME_NOT_FOUND = "runtime_not_found"


@dataclass(frozen=True, slots=True)
class RejectedCandidate:
    runtime_id: str
    reasons: tuple[RejectionReason, ...]


@dataclass(frozen=True, slots=True)
class RuntimeCompatibility:
    """Explain why one descriptor satisfies a requirements object."""

    runtime_id: str
    matched_capabilities: frozenset[RuntimeCapability]
    missing_preferred_capabilities: frozenset[RuntimeCapability]


@dataclass(frozen=True, slots=True)
class RuntimeStartRequest:
    run_id: RunId = field(default_factory=lambda: RunId.new("run"))
    input: str = ""
    session_id: str | None = None
    conversation_id: str | None = None
    runtime_config_reference: str | None = None
    correlation_context: Mapping[str, str] = field(default_factory=dict)
    ownership_context: OwnershipContext | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.input:
            raise ValueError("runtime start input is required")


@dataclass(frozen=True, slots=True)
class RuntimeResumeRequest:
    run_id: RunId
    runtime_handle: RuntimeHandle
    checkpoint_reference: str | None = None
    runtime_checkpoint: RuntimeCheckpoint | None = None
    resume_input: str | None = None
    correlation_context: Mapping[str, str] = field(default_factory=dict)
    ownership_context: OwnershipContext | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class RuntimeCancelRequest:
    run_id: RunId
    runtime_handle: RuntimeHandle
    reason: str
    requested_by: str
    deadline: datetime | None = None

    def __post_init__(self) -> None:
        if not self.reason or not self.requested_by:
            raise ValueError("runtime cancellation reason and requested_by are required")


@dataclass(frozen=True, slots=True)
class RuntimeCancelResult:
    status: RuntimeCancelStatus
    runtime_handle: RuntimeHandle
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class RuntimeCheckpoint:
    runtime_checkpoint_id: str
    runtime_handle: RuntimeHandle
    payload_reference: str | None = None
    created_at: datetime = field(default_factory=utc_now)
    metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class NormalizedRuntimeEvent:
    event_id: str = field(default_factory=lambda: str(uuid4()))
    event_type: RuntimeEventType = RuntimeEventType.DIAGNOSTIC
    runtime_handle: RuntimeHandle | None = None
    timestamp: datetime = field(default_factory=utc_now)
    correlation_context: Mapping[str, str] = field(default_factory=dict)
    payload: Mapping[str, Any] = field(default_factory=dict)
    raw_reference: str | None = None
