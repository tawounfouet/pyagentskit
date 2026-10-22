"""Explicit codecs for the remaining V2 persistence catalog aggregates."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime
from typing import Any

from ...domain.entities import (
    Artifact,
    Conversation,
    ConversationMessage,
    RuntimeBinding,
    RuntimeInvocation,
    Session,
    Worker,
)
from ...domain.lifecycle import RuntimeCapability, WorkerStatus
from ...domain.runtime import (
    RuntimeHandle,
    RuntimeQualificationLevel,
    RuntimeStatus,
    SideEffectControlLevel,
)
from ...domain.shared import (
    AggregateVersion,
    ArtifactChecksum,
    ArtifactId,
    ConversationId,
    ExternalReference,
    MessageId,
    RunId,
    RuntimeBindingId,
    RuntimeInvocationId,
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


def runtime_binding_to_document(binding: RuntimeBinding) -> dict[str, object]:
    return {
        "id": str(binding.id),
        "runtime_name": binding.runtime_name,
        "capabilities": sorted(item.value for item in binding.capabilities),
        "run_id": None if binding.run_id is None else str(binding.run_id),
        "runtime_id": binding.runtime_id,
        "runtime_family": binding.runtime_family,
        "adapter_version": binding.adapter_version,
        "runtime_version": binding.runtime_version,
        "contract_version": binding.contract_version,
        "required_capabilities": sorted(
            item.value for item in binding.required_capabilities
        ),
        "selected_capabilities": (
            None
            if binding.selected_capabilities is None
            else sorted(item.value for item in binding.selected_capabilities)
        ),
        "side_effect_control_level": binding.side_effect_control_level.value,
        "qualification_level": binding.qualification_level.value,
        "configuration_ref": binding.configuration_ref,
        "selection_reason": binding.selection_reason,
        "bound_at": binding.bound_at.isoformat(),
    }


def runtime_binding_from_document(document: Mapping[str, Any]) -> RuntimeBinding:
    run_id = document.get("run_id")
    selected = document.get("selected_capabilities")
    selected_capabilities = (
        None
        if selected is None
        else frozenset(RuntimeCapability(str(item)) for item in selected)
    )
    return RuntimeBinding(
        id=RuntimeBindingId(str(document["id"])),
        runtime_name=str(document.get("runtime_name") or ""),
        capabilities=frozenset(
            RuntimeCapability(str(item)) for item in document.get("capabilities", [])
        ),
        run_id=None if run_id is None else RunId(str(run_id)),
        runtime_id=(
            None if document.get("runtime_id") is None else str(document["runtime_id"])
        ),
        runtime_family=(
            None
            if document.get("runtime_family") is None
            else str(document["runtime_family"])
        ),
        adapter_version=(
            None
            if document.get("adapter_version") is None
            else str(document["adapter_version"])
        ),
        runtime_version=(
            None
            if document.get("runtime_version") is None
            else str(document["runtime_version"])
        ),
        contract_version=(
            None
            if document.get("contract_version") is None
            else str(document["contract_version"])
        ),
        required_capabilities=frozenset(
            RuntimeCapability(str(item))
            for item in document.get("required_capabilities", [])
        ),
        selected_capabilities=selected_capabilities,
        side_effect_control_level=SideEffectControlLevel(
            str(document["side_effect_control_level"])
        ),
        qualification_level=RuntimeQualificationLevel(
            str(document["qualification_level"])
        ),
        configuration_ref=(
            None
            if document.get("configuration_ref") is None
            else str(document["configuration_ref"])
        ),
        selection_reason=str(document.get("selection_reason") or ""),
        bound_at=datetime.fromisoformat(str(document["bound_at"])),
    )


def runtime_invocation_to_document(invocation: RuntimeInvocation) -> dict[str, object]:
    return {
        "id": str(invocation.id),
        "run_id": str(invocation.run_id),
        "binding_id": str(invocation.binding_id),
        "input": invocation.input,
        "runtime_id": invocation.runtime_id,
        "status": invocation.status.value,
        "handle": (
            None
            if invocation.handle is None
            else {
                "adapter_name": invocation.handle.adapter_name,
                "external_id": invocation.handle.external_id,
                "metadata": dict(invocation.handle.metadata),
            }
        ),
        "started_at": (
            None
            if invocation.started_at is None
            else invocation.started_at.isoformat()
        ),
        "completed_at": (
            None
            if invocation.completed_at is None
            else invocation.completed_at.isoformat()
        ),
        "parent_invocation_id": (
            None
            if invocation.parent_invocation_id is None
            else str(invocation.parent_invocation_id)
        ),
        "restart_reason": invocation.restart_reason,
        "checkpoint_origin": invocation.checkpoint_origin,
        "version": invocation.version.value,
    }


def runtime_invocation_from_document(
    document: Mapping[str, Any],
) -> RuntimeInvocation:
    handle_document = document.get("handle")
    handle = None
    if handle_document is not None:
        metadata = handle_document.get("metadata", {})
        if not isinstance(metadata, dict):
            from ...domain.errors import PersistenceCorruptionError

            raise PersistenceCorruptionError("runtime handle metadata must be an object")
        handle = RuntimeHandle(
            adapter_name=str(handle_document["adapter_name"]),
            external_id=str(handle_document["external_id"]),
            metadata=metadata,
        )
    parent_id = document.get("parent_invocation_id")
    started_at = document.get("started_at")
    completed_at = document.get("completed_at")
    return RuntimeInvocation(
        id=RuntimeInvocationId(str(document["id"])),
        run_id=RunId(str(document["run_id"])),
        binding_id=RuntimeBindingId(str(document["binding_id"])),
        input=str(document["input"]),
        runtime_id=(
            None
            if document.get("runtime_id") is None
            else str(document["runtime_id"])
        ),
        status=RuntimeStatus(str(document["status"])),
        handle=handle,
        started_at=(
            None if started_at is None else datetime.fromisoformat(str(started_at))
        ),
        completed_at=(
            None
            if completed_at is None
            else datetime.fromisoformat(str(completed_at))
        ),
        parent_invocation_id=(
            None if parent_id is None else RuntimeInvocationId(str(parent_id))
        ),
        restart_reason=(
            None
            if document.get("restart_reason") is None
            else str(document["restart_reason"])
        ),
        checkpoint_origin=(
            None
            if document.get("checkpoint_origin") is None
            else str(document["checkpoint_origin"])
        ),
        version=AggregateVersion(int(document["version"])),
    )


__all__ = [
    "artifact_from_document",
    "artifact_to_document",
    "conversation_from_document",
    "conversation_to_document",
    "message_from_document",
    "message_to_document",
    "runtime_binding_from_document",
    "runtime_binding_to_document",
    "runtime_invocation_from_document",
    "runtime_invocation_to_document",
    "session_from_document",
    "session_to_document",
    "worker_from_document",
    "worker_to_document",
]
