"""Explicit codecs for the remaining V2 persistence catalog aggregates."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ...domain.entities import (
    Artifact,
    Conversation,
    ConversationMessage,
    Session,
    Worker,
)
from ...domain.lifecycle import WorkerStatus
from ...domain.shared import (
    AggregateVersion,
    ArtifactChecksum,
    ArtifactId,
    ConversationId,
    ExternalReference,
    MessageId,
    SessionId,
    TenantId,
    WorkerId,
)


def _external_reference(value: Mapping[str, Any] | None) -> ExternalReference | None:
    if value is None:
        return None
    return ExternalReference(system=str(value["system"]), key=str(value["key"]))


def session_to_document(session: Session) -> dict[str, object]:
    return {
        "id": str(session.id),
        "tenant_id": str(session.tenant_id),
        "version": session.version.value,
        "created_at": session.created_at.isoformat(),
    }


def session_from_document(document: Mapping[str, Any]) -> Session:
    return Session(
        id=SessionId(str(document["id"])),
        tenant_id=TenantId(str(document["tenant_id"])),
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
    )


def message_to_document(message: ConversationMessage) -> dict[str, object]:
    return {
        "id": str(message.id),
        "actor": message.actor,
        "content": message.content,
        "created_at": message.created_at.isoformat(),
    }


def message_from_document(document: Mapping[str, Any]) -> ConversationMessage:
    return ConversationMessage(
        id=MessageId(str(document["id"])),
        actor=str(document["actor"]),
        content=str(document["content"]),
        created_at=datetime.fromisoformat(str(document["created_at"])),
    )


def conversation_to_document(conversation: Conversation) -> dict[str, object]:
    return {
        "id": str(conversation.id),
        "session_id": str(conversation.session_id),
        "messages": [message_to_document(item) for item in conversation.messages],
        "version": conversation.version.value,
        "created_at": conversation.created_at.isoformat(),
    }


def conversation_from_document(document: Mapping[str, Any]) -> Conversation:
    messages = document.get("messages", [])
    if not isinstance(messages, list):
        from ...domain.errors import PersistenceCorruptionError

        raise PersistenceCorruptionError("conversation messages must be a JSON array")
    return Conversation(
        id=ConversationId(str(document["id"])),
        session_id=SessionId(str(document["session_id"])),
        messages=tuple(message_from_document(item) for item in messages),
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
    )


def worker_to_document(worker: Worker) -> dict[str, object]:
    return {
        "id": str(worker.id),
        "tenant_id": str(worker.tenant_id),
        "status": worker.status.value,
        "version": worker.version.value,
        "created_at": worker.created_at.isoformat(),
    }


def worker_from_document(document: Mapping[str, Any]) -> Worker:
    return Worker(
        id=WorkerId(str(document["id"])),
        tenant_id=TenantId(str(document["tenant_id"])),
        status=WorkerStatus(str(document["status"])),
        version=AggregateVersion(int(document["version"])),
        created_at=datetime.fromisoformat(str(document["created_at"])),
    )


def artifact_to_document(artifact: Artifact) -> dict[str, object]:
    return {
        "id": str(artifact.id),
        "name": artifact.name,
        "checksum": (
            None
            if artifact.checksum is None
            else {
                "algorithm": artifact.checksum.algorithm,
                "value": artifact.checksum.value,
            }
        ),
        "external_reference": (
            None
            if artifact.external_reference is None
            else {
                "system": artifact.external_reference.system,
                "key": artifact.external_reference.key,
            }
        ),
    }


def artifact_from_document(document: Mapping[str, Any]) -> Artifact:
    checksum_document = document.get("checksum")
    checksum = (
        None
        if checksum_document is None
        else ArtifactChecksum(
            algorithm=str(checksum_document["algorithm"]),
            value=str(checksum_document["value"]),
        )
    )
    return Artifact(
        id=ArtifactId(str(document["id"])),
        name=str(document["name"]),
        checksum=checksum,
        external_reference=_external_reference(document.get("external_reference")),
    )


__all__ = [
    "artifact_from_document",
    "artifact_to_document",
    "conversation_from_document",
    "conversation_to_document",
    "message_from_document",
    "message_to_document",
    "session_from_document",
    "session_to_document",
    "worker_from_document",
    "worker_to_document",
]
