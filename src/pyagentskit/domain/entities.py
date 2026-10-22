"""P0 V2 aggregates and entities.

These objects contain no persistence, provider or framework dependencies. State
changes return a new value so callers cannot mutate an aggregate behind the
back of an optimistic-concurrency boundary.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import datetime
from typing import TypeVar

from .errors import InvalidTransitionError, StaleFencingTokenError
from .lifecycle import (
    EFFECT_TRANSITIONS,
    RUN_TRANSITIONS,
    WORKER_TRANSITIONS,
    ApprovalScope,
    ApprovalStatus,
    EffectStatus,
    LeaseStatus,
    RunStatus,
    RuntimeCapability,
    WorkerStatus,
)
from .runtime import (
    RuntimeHandle,
    RuntimeQualificationLevel,
    RuntimeStatus,
    SideEffectControlLevel,
)
from .shared import (
    ActorId,
    AggregateVersion,
    ApprovalId,
    ArtifactChecksum,
    ArtifactId,
    AuditEventId,
    ConversationId,
    EffectId,
    ExternalReference,
    FencingToken,
    Fingerprint,
    LeaseId,
    MessageId,
    ParticipantId,
    ReconciliationCaseId,
    RunId,
    RuntimeBindingId,
    RuntimeInvocationId,
    SessionId,
    TenantId,
    WorkerId,
    utc_now,
)

TransitionState = TypeVar("TransitionState")


def _versioned_transition(
    current: TransitionState,
    target: TransitionState,
    transitions: Mapping[TransitionState, set[TransitionState]],
) -> None:
    allowed = transitions[current]
    if target not in allowed:
        raise InvalidTransitionError(f"cannot transition {current!s} to {target!s}")


@dataclass(frozen=True, slots=True)
class Run:
    id: RunId = field(default_factory=lambda: RunId.new("run"))
    tenant_id: TenantId = field(default_factory=lambda: TenantId.new("tenant"))
    status: RunStatus = RunStatus.CREATED
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)

    def transition(self, status: RunStatus) -> Run:
        _versioned_transition(self.status, status, RUN_TRANSITIONS)
        return replace(self, status=status, version=self.version.next())


@dataclass(frozen=True, slots=True)
class Effect:
    id: EffectId = field(default_factory=lambda: EffectId.new("effect"))
    run_id: RunId = field(default_factory=lambda: RunId.new("run"))
    fingerprint: Fingerprint = field(
        default_factory=lambda: Fingerprint.from_text(str(EffectId.new()))
    )
    status: EffectStatus = EffectStatus.NOT_STARTED
    external_reference: ExternalReference | None = None
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)

    def transition(self, status: EffectStatus) -> Effect:
        _versioned_transition(self.status, status, EFFECT_TRANSITIONS)
        return replace(self, status=status, version=self.version.next())


@dataclass(frozen=True, slots=True)
class Approval:
    id: ApprovalId = field(default_factory=lambda: ApprovalId.new("approval"))
    scope: ApprovalScope = ApprovalScope.EFFECT
    subject: str = ""
    status: ApprovalStatus = ApprovalStatus.PENDING
    expires_at: datetime | None = None
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.subject:
            raise ValueError("approval subject is required")

    def transition(self, status: ApprovalStatus) -> Approval:
        if self.status is not ApprovalStatus.PENDING:
            raise InvalidTransitionError("a terminal approval cannot transition")
        if status is ApprovalStatus.PENDING:
            raise InvalidTransitionError("approval must transition to a terminal status")
        return replace(self, status=status, version=self.version.next())


@dataclass(frozen=True, slots=True)
class Lease:
    id: LeaseId = field(default_factory=lambda: LeaseId.new("lease"))
    resource: str = ""
    status: LeaseStatus = LeaseStatus.AVAILABLE
    worker_id: WorkerId | None = None
    fencing_token: FencingToken = field(default_factory=lambda: FencingToken(0))
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.resource:
            raise ValueError("lease resource is required")

    def acquire(self, worker_id: WorkerId, fencing_token: FencingToken) -> Lease:
        if self.status not in {LeaseStatus.AVAILABLE, LeaseStatus.RELEASED, LeaseStatus.EXPIRED}:
            raise InvalidTransitionError("held lease cannot be acquired")
        if fencing_token <= self.fencing_token:
            raise StaleFencingTokenError("fencing token must increase on acquisition")
        return replace(
            self,
            status=LeaseStatus.HELD,
            worker_id=worker_id,
            fencing_token=fencing_token,
            version=self.version.next(),
        )

    def release(self) -> Lease:
        if self.status is not LeaseStatus.HELD:
            raise InvalidTransitionError("only a held lease can be released")
        return replace(
            self,
            status=LeaseStatus.RELEASED,
            worker_id=None,
            version=self.version.next(),
        )

    def expire(self) -> Lease:
        if self.status is not LeaseStatus.HELD:
            raise InvalidTransitionError("only a held lease can expire")
        return replace(
            self,
            status=LeaseStatus.EXPIRED,
            worker_id=None,
            version=self.version.next(),
        )


@dataclass(frozen=True, slots=True)
class Session:
    id: SessionId = field(default_factory=lambda: SessionId.new("session"))
    tenant_id: TenantId = field(default_factory=lambda: TenantId.new("tenant"))
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)


@dataclass(frozen=True, slots=True)
class Actor:
    id: ActorId = field(default_factory=lambda: ActorId.new("actor"))
    kind: str = ""
    label: str = ""

    def __post_init__(self) -> None:
        if not self.kind or not self.label:
            raise ValueError("actor kind and label are required")


@dataclass(frozen=True, slots=True)
class Participant:
    id: ParticipantId = field(default_factory=lambda: ParticipantId.new("participant"))
    actor_id: ActorId = field(default_factory=lambda: ActorId.new("actor"))
    role: str = ""

    def __post_init__(self) -> None:
        if not self.role:
            raise ValueError("participant role is required")


@dataclass(frozen=True, slots=True)
class Worker:
    id: WorkerId = field(default_factory=lambda: WorkerId.new("worker"))
    tenant_id: TenantId = field(default_factory=lambda: TenantId.new("tenant"))
    status: WorkerStatus = WorkerStatus.ADMITTED
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)

    def transition(self, status: WorkerStatus) -> Worker:
        _versioned_transition(self.status, status, WORKER_TRANSITIONS)
        return replace(self, status=status, version=self.version.next())


@dataclass(frozen=True, slots=True)
class ConversationMessage:
    id: MessageId = field(default_factory=lambda: MessageId.new("message"))
    actor: str = ""
    content: str = ""
    created_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.actor or not self.content:
            raise ValueError("message actor and content are required")


@dataclass(frozen=True, slots=True)
class Conversation:
    id: ConversationId = field(default_factory=lambda: ConversationId.new("conversation"))
    session_id: SessionId = field(default_factory=lambda: SessionId.new("session"))
    messages: tuple[ConversationMessage, ...] = ()
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)

    def append(self, message: ConversationMessage) -> Conversation:
        return replace(self, messages=(*self.messages, message), version=self.version.next())


@dataclass(frozen=True, slots=True)
class RuntimeBinding:
    id: RuntimeBindingId = field(default_factory=lambda: RuntimeBindingId.new("binding"))
    runtime_name: str = ""
    capabilities: frozenset[RuntimeCapability] = frozenset()
    run_id: RunId | None = None
    runtime_id: str | None = None
    runtime_family: str | None = None
    adapter_version: str | None = None
    runtime_version: str | None = None
    contract_version: str | None = None
    required_capabilities: frozenset[RuntimeCapability] = frozenset()
    selected_capabilities: frozenset[RuntimeCapability] | None = None
    side_effect_control_level: SideEffectControlLevel = SideEffectControlLevel.OPAQUE
    qualification_level: RuntimeQualificationLevel = RuntimeQualificationLevel.L0
    configuration_ref: str | None = None
    selection_reason: str = ""
    bound_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.runtime_name and not self.runtime_id:
            raise ValueError("runtime name or runtime id is required")

    @property
    def resolved_runtime_id(self) -> str:
        """Return the canonical id when available, otherwise the legacy name."""

        return self.runtime_id or self.runtime_name

    @property
    def resolved_capabilities(self) -> frozenset[RuntimeCapability]:
        """Return the negotiated capability snapshot."""

        return (
            self.capabilities if self.selected_capabilities is None else self.selected_capabilities
        )


@dataclass(frozen=True, slots=True)
class RuntimeInvocation:
    id: RuntimeInvocationId = field(default_factory=lambda: RuntimeInvocationId.new("invocation"))
    run_id: RunId = field(default_factory=lambda: RunId.new("run"))
    binding_id: RuntimeBindingId = field(default_factory=lambda: RuntimeBindingId.new("binding"))
    input: str = ""
    runtime_id: str | None = None
    status: RuntimeStatus = RuntimeStatus.CREATED
    handle: RuntimeHandle | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    parent_invocation_id: RuntimeInvocationId | None = None
    restart_reason: str | None = None
    checkpoint_origin: str | None = None
    version: AggregateVersion = field(default_factory=AggregateVersion)

    def __post_init__(self) -> None:
        if not self.input:
            raise ValueError("runtime invocation input is required")


@dataclass(frozen=True, slots=True)
class Artifact:
    id: ArtifactId = field(default_factory=lambda: ArtifactId.new("artifact"))
    name: str = ""
    checksum: ArtifactChecksum | None = None
    external_reference: ExternalReference | None = None

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("artifact name is required")


@dataclass(frozen=True, slots=True)
class AuditEvent:
    id: AuditEventId = field(default_factory=lambda: AuditEventId.new("audit"))
    event_type: str = ""
    subject: str = ""
    metadata: tuple[tuple[str, str], ...] = ()
    occurred_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.event_type or not self.subject:
            raise ValueError("audit event type and subject are required")


@dataclass(frozen=True, slots=True)
class ReconciliationCase:
    id: ReconciliationCaseId = field(
        default_factory=lambda: ReconciliationCaseId.new("reconciliation")
    )
    effect_id: EffectId = field(default_factory=lambda: EffectId.new("effect"))
    reason: str = ""
    resolved: bool = False
    resolution: str | None = None

    def __post_init__(self) -> None:
        if not self.reason:
            raise ValueError("reconciliation reason is required")

    def resolve(self, resolution: str) -> ReconciliationCase:
        if self.resolved:
            raise InvalidTransitionError("reconciliation case is already resolved")
        if not resolution:
            raise ValueError("reconciliation resolution is required")
        return replace(self, resolved=True, resolution=resolution)
