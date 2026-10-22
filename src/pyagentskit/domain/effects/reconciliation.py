"""Reconciliation domain objects for ambiguous Effects."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime
from enum import IntEnum, StrEnum

from ..errors import InvalidTransitionError
from ..lifecycle import ReconciliationStatus
from ..shared import (
    AggregateVersion,
    ArtifactId,
    EffectId,
    ExternalReference,
    Fingerprint,
    ReconciliationCaseId,
    ReconciliationEvidenceId,
    utc_now,
)


class ReconciliationResolution(StrEnum):
    CONFIRMED_SUCCESS = "confirmed_success"
    CONFIRMED_FAILURE = "confirmed_failure"
    STILL_UNKNOWN = "still_unknown"
    NOT_FOUND = "not_found"
    MANUAL_REQUIRED = "manual_required"


class ReconciliationStrategy(StrEnum):
    BY_EXTERNAL_ID = "by_external_id"
    BY_IDEMPOTENCY_KEY = "by_idempotency_key"
    BY_BUSINESS_KEY = "by_business_key"
    BY_REMOTE_STATE = "by_remote_state"
    BY_PROVIDER_EVENT = "by_provider_event"
    BY_COMPOSITE_EVIDENCE = "by_composite_evidence"
    MANUAL_ONLY = "manual_only"


class EvidenceSource(StrEnum):
    PROVIDER_API = "provider_api"
    WEBHOOK = "webhook"
    AUDIT_LOG = "audit_log"
    REMOTE_REF = "remote_ref"
    BUSINESS_KEY_LOOKUP = "business_key_lookup"
    OPERATOR = "operator"
    SECONDARY_SYSTEM = "secondary_system"


class EvidenceKind(StrEnum):
    OBJECT_EXISTS = "object_exists"
    OBJECT_ABSENT = "object_absent"
    STATUS_MATCH = "status_match"
    STATUS_CONFLICT = "status_conflict"
    SHA_MATCH = "sha_match"
    IDEMPOTENCY_MATCH = "idempotency_match"
    PROVIDER_EVENT = "provider_event"
    MANUAL_DOCUMENT = "manual_document"


class EvidenceConfidence(IntEnum):
    WEAK = 1
    MEDIUM = 2
    STRONG = 3
    AUTHORITATIVE = 4


@dataclass(frozen=True, slots=True)
class ReconciliationEvidence:
    id: ReconciliationEvidenceId = field(
        default_factory=lambda: ReconciliationEvidenceId.new("evidence")
    )
    case_id: ReconciliationCaseId = field(
        default_factory=lambda: ReconciliationCaseId.new("reconciliation")
    )
    source: EvidenceSource = EvidenceSource.PROVIDER_API
    kind: EvidenceKind = EvidenceKind.STATUS_MATCH
    summary: str = ""
    confidence: EvidenceConfidence = EvidenceConfidence.WEAK
    observed_at: datetime = field(default_factory=utc_now)
    provider_timestamp: datetime | None = None
    external_reference: ExternalReference | None = None
    payload_digest: Fingerprint | None = None
    raw_artifact_id: ArtifactId | None = None

    def __post_init__(self) -> None:
        if not self.summary:
            raise ValueError("reconciliation evidence summary is required")


@dataclass(frozen=True, slots=True)
class ReconciliationObservation:
    resolution: ReconciliationResolution
    evidence: tuple[ReconciliationEvidence, ...] = ()
    external_reference: ExternalReference | None = None
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class ReconciliationCase:
    id: ReconciliationCaseId = field(
        default_factory=lambda: ReconciliationCaseId.new("reconciliation")
    )
    effect_id: EffectId = field(default_factory=lambda: EffectId.new("effect"))
    reason: str = ""
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    strategy: ReconciliationStrategy = ReconciliationStrategy.MANUAL_ONLY
    attempt_count: int = 0
    max_attempts: int = 3
    blocking: bool = True
    resolution: ReconciliationResolution | str | None = None
    resolution_detail: str | None = None
    version: AggregateVersion = field(default_factory=AggregateVersion)
    created_at: datetime = field(default_factory=utc_now)
    resolved_at: datetime | None = None
    metadata: tuple[tuple[str, str], ...] = ()

    def __post_init__(self) -> None:
        if not self.reason:
            raise ValueError("reconciliation reason is required")
        if self.attempt_count < 0 or self.max_attempts < 1:
            raise ValueError("reconciliation attempt counters are invalid")
        if self.status.is_terminal and self.resolution is None:
            raise ValueError("terminal reconciliation requires a resolution")

    @property
    def resolved(self) -> bool:
        return self.status.is_terminal

    def start(self) -> ReconciliationCase:
        if self.status not in {ReconciliationStatus.PENDING, ReconciliationStatus.FAILED}:
            raise InvalidTransitionError("reconciliation cannot start from its current state")
        return replace(
            self,
            status=ReconciliationStatus.RUNNING,
            attempt_count=self.attempt_count + 1,
            version=self.version.next(),
        )

    def record_result(
        self,
        resolution: ReconciliationResolution,
        *,
        detail: str | None = None,
    ) -> ReconciliationCase:
        if self.status not in {
            ReconciliationStatus.RUNNING,
            ReconciliationStatus.MANUAL_REVIEW,
        }:
            raise InvalidTransitionError("reconciliation result requires running/manual state")
        now = utc_now()
        if resolution is ReconciliationResolution.CONFIRMED_SUCCESS:
            return replace(
                self,
                status=ReconciliationStatus.RESOLVED_SUCCESS,
                resolution=resolution,
                resolution_detail=detail,
                resolved_at=now,
                version=self.version.next(),
            )
        if resolution is ReconciliationResolution.CONFIRMED_FAILURE:
            return replace(
                self,
                status=ReconciliationStatus.RESOLVED_FAILURE,
                resolution=resolution,
                resolution_detail=detail,
                resolved_at=now,
                version=self.version.next(),
            )
        if (
            resolution is ReconciliationResolution.MANUAL_REQUIRED
            or self.attempt_count >= self.max_attempts
        ):
            return replace(
                self,
                status=ReconciliationStatus.MANUAL_REVIEW,
                resolution=resolution,
                resolution_detail=detail,
                version=self.version.next(),
            )
        return replace(
            self,
            status=ReconciliationStatus.RUNNING,
            resolution=resolution,
            resolution_detail=detail,
            version=self.version.next(),
        )

    def resolve(
        self,
        resolution: str,
        *,
        status: ReconciliationStatus = ReconciliationStatus.RESOLVED_SUCCESS,
    ) -> ReconciliationCase:
        """Compatibility helper retained for the A1 public surface."""

        if self.status.is_terminal:
            raise InvalidTransitionError("reconciliation case is already resolved")
        if not resolution:
            raise ValueError("reconciliation resolution is required")
        if status not in {
            ReconciliationStatus.RESOLVED_SUCCESS,
            ReconciliationStatus.RESOLVED_FAILURE,
        }:
            raise InvalidTransitionError("compatibility resolution must be terminal")
        canonical = (
            ReconciliationResolution.CONFIRMED_SUCCESS
            if status is ReconciliationStatus.RESOLVED_SUCCESS
            else ReconciliationResolution.CONFIRMED_FAILURE
        )
        return replace(
            self,
            status=status,
            resolution=canonical,
            resolution_detail=resolution,
            resolved_at=utc_now(),
            version=self.version.next(),
        )
