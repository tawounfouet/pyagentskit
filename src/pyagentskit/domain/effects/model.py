"""Effect safety domain model for PyAgentsKit V2."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import StrEnum

from ..errors import IdempotencyConflictError, InvalidTransitionError
from ..lifecycle import EFFECT_TRANSITIONS, EffectStatus
from ..shared import (
    AggregateVersion,
    EffectId,
    ExternalReference,
    FencingToken,
    Fingerprint,
    OwnershipContext,
    RunId,
    utc_now,
)


class IdempotencyScope(StrEnum):
    GLOBAL = "global"
    TENANT = "tenant"
    RUN = "run"
    TOOL = "tool"
    EXTERNAL_SYSTEM = "external_system"
    CUSTOM = "custom"


class EffectRiskLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EffectOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNKNOWN = "unknown"
    RECONCILED_SUCCESS = "reconciled_success"
    RECONCILED_FAILURE = "reconciled_failure"
    MANUAL_RESOLUTION = "manual_resolution"


@dataclass(frozen=True, slots=True)
class IdempotencyKey:
    namespace: str
    key: str

    def __post_init__(self) -> None:
        if not self.namespace or not self.key:
            raise ValueError("idempotency namespace and key are required")

    @property
    def canonical(self) -> str:
        return f"{self.namespace}:{self.key}"


@dataclass(frozen=True, slots=True)
class EffectKind:
    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 128:
            raise ValueError("effect kind must contain between 1 and 128 characters")

    def __str__(self) -> str:
        return self.value


class InputFingerprint(Fingerprint):
    """Canonical SHA-256 fingerprint of significant effect inputs."""


@dataclass(frozen=True, slots=True)
class Effect:
    """Durable logical intent for an externally observable side effect."""

    id: EffectId = field(default_factory=lambda: EffectId.new("effect"))
    run_id: RunId = field(default_factory=lambda: RunId.new("run"))
    kind: EffectKind = field(default_factory=lambda: EffectKind("generic"))
    status: EffectStatus = EffectStatus.NOT_STARTED
    idempotency_key: IdempotencyKey | None = None
    idempotency_scope: IdempotencyScope = IdempotencyScope.RUN
    fingerprint: InputFingerprint = field(
        default_factory=lambda: InputFingerprint.from_text(str(EffectId.new()))
    )
    risk_level: EffectRiskLevel = EffectRiskLevel.MEDIUM
    external_reference: ExternalReference | None = None
    fencing_token: FencingToken | None = None
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    @property
    def is_authoritative(self) -> bool:
        return self.status in {EffectStatus.SUCCEEDED, EffectStatus.FAILED}

    @property
    def requires_reconciliation(self) -> bool:
        return self.status in {
            EffectStatus.STARTED,
            EffectStatus.UNKNOWN,
            EffectStatus.RECONCILIATION_REQUIRED,
        }

    @property
    def safe_to_replay(self) -> bool:
        return self.status is EffectStatus.NOT_STARTED

    def assert_same_intent(
        self,
        idempotency_key: IdempotencyKey | None,
        fingerprint: Fingerprint,
    ) -> None:
        if self.idempotency_key != idempotency_key:
            return
        if self.fingerprint.value != fingerprint.value:
            raise IdempotencyConflictError(
                "same idempotency key cannot represent a different effect payload"
            )

    def transition(self, status: EffectStatus) -> Effect:
        allowed = EFFECT_TRANSITIONS[self.status]
        if status not in allowed:
            raise InvalidTransitionError(f"cannot transition {self.status!s} to {status!s}")
        now = utc_now()
        started_at = self.started_at
        completed_at = self.completed_at
        if status is EffectStatus.STARTED and started_at is None:
            started_at = now
        if status in {EffectStatus.SUCCEEDED, EffectStatus.FAILED}:
            completed_at = now
        return replace(
            self,
            status=status,
            started_at=started_at,
            completed_at=completed_at,
            version=self.version.next(),
        )

    def begin(
        self,
        *,
        ownership: OwnershipContext | None = None,
        protected: bool = False,
    ) -> Effect:
        if protected and ownership is None:
            raise InvalidTransitionError("protected effect requires an ownership context")
        started = self.transition(EffectStatus.STARTED)
        if ownership is None:
            return started
        return replace(started, fencing_token=ownership.fencing_token)

    def mark_succeeded(
        self,
        *,
        external_reference: ExternalReference | None = None,
    ) -> Effect:
        succeeded = self.transition(EffectStatus.SUCCEEDED)
        if external_reference is None:
            return succeeded
        return replace(succeeded, external_reference=external_reference)

    def mark_failed(self) -> Effect:
        return self.transition(EffectStatus.FAILED)

    def mark_unknown(self) -> Effect:
        return self.transition(EffectStatus.UNKNOWN)

    def open_reconciliation(self) -> Effect:
        return self.transition(EffectStatus.RECONCILIATION_REQUIRED)

    def reconcile_success(
        self,
        *,
        external_reference: ExternalReference | None = None,
    ) -> Effect:
        succeeded = self.transition(EffectStatus.SUCCEEDED)
        if external_reference is None:
            return succeeded
        return replace(succeeded, external_reference=external_reference)

    def reconcile_failure(self) -> Effect:
        return self.transition(EffectStatus.FAILED)
