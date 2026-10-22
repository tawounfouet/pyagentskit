"""Stable JSON codecs for V2 persistence adapters.

The codec is intentionally explicit: persistence adapters do not rely on
pickle, provider SDK serializers, or dataclass implementation details.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ...domain.effects import (
    Effect,
    EffectKind,
    EffectRiskLevel,
    EvidenceConfidence,
    EvidenceKind,
    EvidenceSource,
    IdempotencyKey,
    IdempotencyScope,
    InputFingerprint,
    ReconciliationCase,
    ReconciliationEvidence,
    ReconciliationResolution,
    ReconciliationStrategy,
)
from ...domain.entities import (
    Approval,
    AuditEvent,
    Lease,
    MemoryEntry,
    MemoryScope,
    Run,
)
from ...domain.events import IntegrationEvent
from ...domain.lifecycle import (
    ApprovalScope,
    ApprovalStatus,
    EffectStatus,
    LeaseStatus,
    ReconciliationStatus,
    RunStatus,
)
from ...domain.shared import (
    AggregateVersion,
    ApprovalId,
    ArtifactId,
    AuditEventId,
    EffectId,
    ExternalReference,
    FencingToken,
    Fingerprint,
    LeaseId,
    MemoryEntryId,
    ReconciliationCaseId,
    ReconciliationEvidenceId,
    RunId,
    TenantId,
    WorkerId,
)


def _datetime(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _external_reference(value: Mapping[str, Any] | None) -> ExternalReference | None:
    if value is None:
        return None
    return ExternalReference(system=str(value["system"]), key=str(value["key"]))


def _metadata(value: list[list[str]] | list[tuple[str, str]] | None) -> tuple[tuple[str, str], ...]:
    if value is None:
        return ()
    return tuple((str(key), str(item)) for key, item in value)


def dumps(document: Mapping[str, object]) -> str:
    try:
        return json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    except (TypeError, ValueError) as exc:
        from ...domain.errors import PersistenceError

        raise PersistenceError("V2 persistence payload is not JSON serializable") from exc


def loads(payload: str) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except json.JSONDecodeError as exc:
        from ...domain.errors import PersistenceCorruptionError

        raise PersistenceCorruptionError("invalid persisted JSON payload") from exc
    if not isinstance(value, dict):
        from ...domain.errors import PersistenceCorruptionError

        raise PersistenceCorruptionError("persisted payload must be a JSON object")
    return value


def run_to_document(run: Run) -> dict[str, object]:
    return {
        "id": str(run.id),
        "tenant_id": str(run.tenant_id),
        "status": run.status.value,
        "version": run.version.value,
        "created_at": run.created_at.isoformat(),
    }


def run_from_document(document: Mapping[str, Any]) -> Run:
    return Run(
        id=RunId(str(document["id"])),
        tenant_id=TenantId(str(document["tenant_id"])),
        status=RunStatus(str(document["status"])),
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
    )


def effect_to_document(effect: Effect) -> dict[str, object]:
    return {
        "id": str(effect.id),
        "run_id": str(effect.run_id),
        "kind": str(effect.kind),
        "status": effect.status.value,
        "idempotency_key": (
            None
            if effect.idempotency_key is None
            else {
                "namespace": effect.idempotency_key.namespace,
                "key": effect.idempotency_key.key,
            }
        ),
        "idempotency_scope": effect.idempotency_scope.value,
        "fingerprint": effect.fingerprint.value,
        "risk_level": effect.risk_level.value,
        "external_reference": (
            None
            if effect.external_reference is None
            else {
                "system": effect.external_reference.system,
                "key": effect.external_reference.key,
            }
        ),
        "fencing_token": (None if effect.fencing_token is None else effect.fencing_token.value),
        "version": effect.version.value,
        "created_at": effect.created_at.isoformat(),
        "started_at": (None if effect.started_at is None else effect.started_at.isoformat()),
        "completed_at": (None if effect.completed_at is None else effect.completed_at.isoformat()),
        "metadata": list(effect.metadata),
    }


def effect_from_document(document: Mapping[str, Any]) -> Effect:
    key_document = document.get("idempotency_key")
    key = (
        None
        if key_document is None
        else IdempotencyKey(
            namespace=str(key_document["namespace"]),
            key=str(key_document["key"]),
        )
    )
    fencing = document.get("fencing_token")
    return Effect(
        id=EffectId(str(document["id"])),
        run_id=RunId(str(document["run_id"])),
        kind=EffectKind(str(document["kind"])),
        status=EffectStatus(str(document["status"])),
        idempotency_key=key,
        idempotency_scope=IdempotencyScope(str(document["idempotency_scope"])),
        fingerprint=InputFingerprint(str(document["fingerprint"])),
        risk_level=EffectRiskLevel(str(document["risk_level"])),
        external_reference=_external_reference(document.get("external_reference")),
        fencing_token=None if fencing is None else FencingToken(int(fencing)),
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
        started_at=_datetime(document.get("started_at")),
        completed_at=_datetime(document.get("completed_at")),
        metadata=_metadata(document.get("metadata")),
    )


def memory_to_document(entry: MemoryEntry) -> dict[str, object]:
    return {
        "id": str(entry.id),
        "tenant_id": str(entry.tenant_id),
        "scope": entry.scope.value,
        "scope_id": entry.scope_id,
        "key": entry.key,
        "value": dict(entry.value),
        "version": entry.version.value,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
        "metadata": list(entry.metadata),
    }


def memory_from_document(document: Mapping[str, Any]) -> MemoryEntry:
    value = document.get("value")
    if not isinstance(value, dict):
        from ...domain.errors import PersistenceCorruptionError

        raise PersistenceCorruptionError("memory value must be a JSON object")
    return MemoryEntry(
        id=MemoryEntryId(str(document["id"])),
        tenant_id=TenantId(str(document["tenant_id"])),
        scope=MemoryScope(str(document["scope"])),
        scope_id=None if document.get("scope_id") is None else str(document["scope_id"]),
        key=str(document["key"]),
        value=value,
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
        updated_at=datetime.fromisoformat(str(document["updated_at"])),
        metadata=_metadata(document.get("metadata")),
    )


def approval_to_document(approval: Approval) -> dict[str, object]:
    return {
        "id": str(approval.id),
        "scope": approval.scope.value,
        "subject": approval.subject,
        "status": approval.status.value,
        "expires_at": (None if approval.expires_at is None else approval.expires_at.isoformat()),
        "version": approval.version.value,
        "created_at": approval.created_at.isoformat(),
    }


def approval_from_document(document: Mapping[str, Any]) -> Approval:
    return Approval(
        id=ApprovalId(str(document["id"])),
        scope=ApprovalScope(str(document["scope"])),
        subject=str(document["subject"]),
        status=ApprovalStatus(str(document["status"])),
        expires_at=_datetime(document.get("expires_at")),
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
    )


def lease_to_document(lease: Lease) -> dict[str, object]:
    return {
        "id": str(lease.id),
        "resource": lease.resource,
        "status": lease.status.value,
        "worker_id": None if lease.worker_id is None else str(lease.worker_id),
        "fencing_token": lease.fencing_token.value,
        "version": lease.version.value,
        "created_at": lease.created_at.isoformat(),
    }


def lease_from_document(document: Mapping[str, Any]) -> Lease:
    worker_id = document.get("worker_id")
    return Lease(
        id=LeaseId(str(document["id"])),
        resource=str(document["resource"]),
        status=LeaseStatus(str(document["status"])),
        worker_id=None if worker_id is None else WorkerId(str(worker_id)),
        fencing_token=FencingToken(int(document["fencing_token"])),
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
    )


def reconciliation_case_to_document(case: ReconciliationCase) -> dict[str, object]:
    resolution = case.resolution
    resolution_value = (
        resolution.value if isinstance(resolution, ReconciliationResolution) else resolution
    )
    return {
        "id": str(case.id),
        "effect_id": str(case.effect_id),
        "reason": case.reason,
        "status": case.status.value,
        "strategy": case.strategy.value,
        "attempt_count": case.attempt_count,
        "max_attempts": case.max_attempts,
        "blocking": case.blocking,
        "resolution": resolution_value,
        "resolution_detail": case.resolution_detail,
        "version": case.version.value,
        "created_at": case.created_at.isoformat(),
        "resolved_at": (None if case.resolved_at is None else case.resolved_at.isoformat()),
        "metadata": list(case.metadata),
    }


def reconciliation_case_from_document(
    document: Mapping[str, Any],
) -> ReconciliationCase:
    resolution_value = document.get("resolution")
    resolution: ReconciliationResolution | str | None = None
    if resolution_value is not None:
        try:
            resolution = ReconciliationResolution(str(resolution_value))
        except ValueError:
            resolution = str(resolution_value)
    return ReconciliationCase(
        id=ReconciliationCaseId(str(document["id"])),
        effect_id=EffectId(str(document["effect_id"])),
        reason=str(document["reason"]),
        status=ReconciliationStatus(str(document["status"])),
        strategy=ReconciliationStrategy(str(document["strategy"])),
        attempt_count=int(document["attempt_count"]),
        max_attempts=int(document["max_attempts"]),
        blocking=bool(document["blocking"]),
        resolution=resolution,
        resolution_detail=(
            None
            if document.get("resolution_detail") is None
            else str(document["resolution_detail"])
        ),
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
        resolved_at=_datetime(document.get("resolved_at")),
        metadata=_metadata(document.get("metadata")),
    )


def reconciliation_evidence_to_document(
    evidence: ReconciliationEvidence,
) -> dict[str, object]:
    return {
        "id": str(evidence.id),
        "case_id": str(evidence.case_id),
        "source": evidence.source.value,
        "kind": evidence.kind.value,
        "summary": evidence.summary,
        "confidence": int(evidence.confidence),
        "observed_at": evidence.observed_at.isoformat(),
        "provider_timestamp": (
            None if evidence.provider_timestamp is None else evidence.provider_timestamp.isoformat()
        ),
        "external_reference": (
            None
            if evidence.external_reference is None
            else {
                "system": evidence.external_reference.system,
                "key": evidence.external_reference.key,
            }
        ),
        "payload_digest": (
            None if evidence.payload_digest is None else evidence.payload_digest.value
        ),
        "raw_artifact_id": (
            None if evidence.raw_artifact_id is None else str(evidence.raw_artifact_id)
        ),
    }


def reconciliation_evidence_from_document(
    document: Mapping[str, Any],
) -> ReconciliationEvidence:
    digest = document.get("payload_digest")
    artifact = document.get("raw_artifact_id")
    return ReconciliationEvidence(
        id=ReconciliationEvidenceId(str(document["id"])),
        case_id=ReconciliationCaseId(str(document["case_id"])),
        source=EvidenceSource(str(document["source"])),
        kind=EvidenceKind(str(document["kind"])),
        summary=str(document["summary"]),
        confidence=EvidenceConfidence(int(document["confidence"])),
        observed_at=datetime.fromisoformat(str(document["observed_at"])),
        provider_timestamp=_datetime(document.get("provider_timestamp")),
        external_reference=_external_reference(document.get("external_reference")),
        payload_digest=None if digest is None else Fingerprint(str(digest)),
        raw_artifact_id=None if artifact is None else ArtifactId(str(artifact)),
    )


def audit_to_document(event: AuditEvent) -> dict[str, object]:
    return {
        "id": str(event.id),
        "event_type": event.event_type,
        "subject": event.subject,
        "metadata": list(event.metadata),
        "occurred_at": event.occurred_at.isoformat(),
    }


def audit_from_document(document: Mapping[str, Any]) -> AuditEvent:
    return AuditEvent(
        id=AuditEventId(str(document["id"])),
        event_type=str(document["event_type"]),
        subject=str(document["subject"]),
        metadata=_metadata(document.get("metadata")),
        occurred_at=datetime.fromisoformat(str(document["occurred_at"])),
    )


def integration_event_to_document(event: IntegrationEvent) -> dict[str, object]:
    return {
        "event_id": event.event_id,
        "name": event.name,
        "payload": dict(event.payload),
        "tenant_id": None if event.tenant_id is None else str(event.tenant_id),
        "aggregate_type": event.aggregate_type,
        "aggregate_id": event.aggregate_id,
        "occurred_at": event.occurred_at.isoformat(),
    }


def integration_event_from_document(
    document: Mapping[str, Any],
) -> IntegrationEvent:
    payload = document.get("payload")
    if not isinstance(payload, dict):
        from ...domain.errors import PersistenceCorruptionError

        raise PersistenceCorruptionError("integration event payload must be a JSON object")
    tenant = document.get("tenant_id")
    return IntegrationEvent(
        event_id=str(document["event_id"]),
        name=str(document["name"]),
        payload=payload,
        tenant_id=None if tenant is None else TenantId(str(tenant)),
        aggregate_type=(
            None if document.get("aggregate_type") is None else str(document["aggregate_type"])
        ),
        aggregate_id=(
            None if document.get("aggregate_id") is None else str(document["aggregate_id"])
        ),
        occurred_at=datetime.fromisoformat(str(document["occurred_at"])),
    )
