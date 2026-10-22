"""Technology-neutral V2 persistence contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from types import TracebackType
from typing import Protocol, runtime_checkable

from ..domain.entities import (
    Approval,
    Artifact,
    AuditEvent,
    Conversation,
    ConversationMessage,
    Lease,
    MemoryEntry,
    Run,
    RuntimeBinding,
    RuntimeInvocation,
    Session,
    Worker,
)
from ..domain.events import IntegrationEvent
from ..domain.lifecycle import RunStatus
from ..domain.shared import (
    AggregateVersion,
    ApprovalId,
    ArtifactId,
    ConversationId,
    FencingToken,
    MemoryEntryId,
    MessageId,
    RunId,
    RuntimeBindingId,
    RuntimeInvocationId,
    SessionId,
    WorkerId,
)
from .effects import EffectRepository, ReconciliationRepository


class OutboxStatus(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    PUBLISHED = "published"
    FAILED = "failed"


class InboxStatus(StrEnum):
    RESERVED = "reserved"
    PROCESSED = "processed"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class OutboxRecord:
    event: IntegrationEvent
    status: OutboxStatus = OutboxStatus.PENDING
    attempt_count: int = 0
    next_attempt_at: datetime | None = None
    claimed_by: str | None = None
    claimed_at: datetime | None = None
    published_at: datetime | None = None
    last_error: str | None = None


@dataclass(frozen=True, slots=True)
class InboxRecord:
    source: str
    external_event_id: str
    digest: str
    status: InboxStatus = InboxStatus.RESERVED
    tenant_id: str | None = None
    processed_at: datetime | None = None
    last_error: str | None = None

    def __post_init__(self) -> None:
        if not self.source or not self.external_event_id or not self.digest:
            raise ValueError("inbox source, external event id and digest are required")


@runtime_checkable
class RunRepository(Protocol):
    async def get(self, run_id: RunId) -> Run | None: ...
    async def add(self, run: Run) -> None: ...
    async def save(self, run: Run, *, expected_version: AggregateVersion) -> None: ...
    async def list_by_state(self, status: RunStatus) -> tuple[Run, ...]: ...


@runtime_checkable
class SessionRepository(Protocol):
    async def get(self, session_id: SessionId) -> Session | None: ...
    async def add(self, session: Session) -> None: ...
    async def save(self, session: Session, *, expected_version: AggregateVersion) -> None: ...


@runtime_checkable
class MemoryRepository(Protocol):
    async def get(self, memory_id: MemoryEntryId) -> MemoryEntry | None: ...
    async def put(self, entry: MemoryEntry) -> None: ...
    async def save(
        self,
        entry: MemoryEntry,
        *,
        expected_version: AggregateVersion,
    ) -> None: ...
    async def list_by_scope(
        self,
        *,
        tenant_id: str,
        scope: str,
        scope_id: str | None,
    ) -> tuple[MemoryEntry, ...]: ...


@runtime_checkable
class ConversationRepository(Protocol):
    async def get(self, conversation_id: ConversationId) -> Conversation | None: ...
    async def add(self, conversation: Conversation) -> None: ...
    async def save(
        self,
        conversation: Conversation,
        *,
        expected_version: AggregateVersion,
    ) -> None: ...
    async def list_for_session(self, session_id: SessionId) -> tuple[Conversation, ...]: ...


@runtime_checkable
class MessageRepository(Protocol):
    async def append(
        self,
        conversation_id: ConversationId,
        message: ConversationMessage,
    ) -> None: ...
    async def get(self, message_id: MessageId) -> ConversationMessage | None: ...
    async def list_for_conversation(
        self,
        conversation_id: ConversationId,
    ) -> tuple[ConversationMessage, ...]: ...


@runtime_checkable
class ApprovalRepository(Protocol):
    async def get(self, approval_id: ApprovalId) -> Approval | None: ...
    async def add(self, approval: Approval) -> None: ...
    async def save(
        self,
        approval: Approval,
        *,
        expected_version: AggregateVersion,
    ) -> None: ...
    async def list_pending(self) -> tuple[Approval, ...]: ...


@runtime_checkable
class LeaseRepository(Protocol):
    async def get_current(self, resource: str) -> Lease | None: ...
    async def add(self, lease: Lease) -> None: ...
    async def save(self, lease: Lease, *, expected_version: AggregateVersion) -> None: ...
    async def next_fencing_token(self, resource: str) -> FencingToken: ...


@runtime_checkable
class WorkerRepository(Protocol):
    async def get(self, worker_id: WorkerId) -> Worker | None: ...
    async def add(self, worker: Worker) -> None: ...
    async def save(self, worker: Worker, *, expected_version: AggregateVersion) -> None: ...


@runtime_checkable
class RuntimeRepository(Protocol):
    async def get_binding(self, binding_id: RuntimeBindingId) -> RuntimeBinding | None: ...
    async def add_binding(self, binding: RuntimeBinding) -> None: ...
    async def get_invocation(
        self,
        invocation_id: RuntimeInvocationId,
    ) -> RuntimeInvocation | None: ...
    async def add_invocation(self, invocation: RuntimeInvocation) -> None: ...
    async def save_invocation(
        self,
        invocation: RuntimeInvocation,
        *,
        expected_version: AggregateVersion,
    ) -> None: ...


@runtime_checkable
class ArtifactRepository(Protocol):
    async def get(self, artifact_id: ArtifactId) -> Artifact | None: ...
    async def add(self, artifact: Artifact) -> None: ...


@runtime_checkable
class AuditStore(Protocol):
    async def append(self, event: AuditEvent) -> None: ...
    async def list_for_subject(self, subject: str) -> tuple[AuditEvent, ...]: ...


@runtime_checkable
class OutboxStore(Protocol):
    async def append(self, event: IntegrationEvent) -> None: ...
    async def claim_batch(
        self,
        *,
        worker_id: str,
        limit: int = 100,
        claim_timeout_seconds: float = 60.0,
    ) -> tuple[OutboxRecord, ...]: ...
    async def mark_published(self, event_id: str) -> None: ...
    async def mark_failed(self, event_id: str, *, error: str) -> None: ...
    async def release_claim(self, event_id: str) -> None: ...


@runtime_checkable
class InboxStore(Protocol):
    async def reserve(self, record: InboxRecord) -> bool: ...
    async def get(self, source: str, external_event_id: str) -> InboxRecord | None: ...
    async def mark_processed(self, source: str, external_event_id: str) -> None: ...
    async def mark_failed(self, source: str, external_event_id: str, *, error: str) -> None: ...


@runtime_checkable
class UnitOfWork(Protocol):
    runs: RunRepository
    sessions: SessionRepository
    conversations: ConversationRepository
    messages: MessageRepository
    memories: MemoryRepository
    effects: EffectRepository
    reconciliations: ReconciliationRepository
    approvals: ApprovalRepository
    workers: WorkerRepository
    runtimes: RuntimeRepository
    artifacts: ArtifactRepository
    outbox: OutboxStore
    audit: AuditStore

    async def __aenter__(self) -> UnitOfWork: ...
    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...


@runtime_checkable
class BlobStore(Protocol):
    async def put(self, key: str, content: bytes) -> str: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


__all__ = [
    "ApprovalRepository",
    "ArtifactRepository",
    "AuditStore",
    "BlobStore",
    "ConversationRepository",
    "EffectRepository",
    "InboxRecord",
    "InboxStatus",
    "InboxStore",
    "LeaseRepository",
    "MemoryRepository",
    "MessageRepository",
    "OutboxRecord",
    "OutboxStatus",
    "OutboxStore",
    "ReconciliationRepository",
    "RunRepository",
    "RuntimeRepository",
    "SessionRepository",
    "UnitOfWork",
    "WorkerRepository",
]
