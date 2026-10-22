"""In-memory reference implementations of the V2 persistence contracts."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from types import TracebackType

from ...contracts.effects import EffectReservationResult
from ...contracts.persistence import (
    InboxRecord,
    InboxStatus,
    OutboxRecord,
    OutboxStatus,
)
from ...domain.effects import (
    Effect,
    IdempotencyKey,
    IdempotencyScope,
    ReconciliationCase,
    ReconciliationEvidence,
)
from ...domain.entities import (
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
from ...domain.errors import (
    ConcurrencyConflictError,
    DuplicateAggregateError,
    InboxDigestConflictError,
)
from ...domain.events import IntegrationEvent
from ...domain.lifecycle import ApprovalStatus, LeaseStatus, RunStatus
from ...domain.shared import (
    AggregateVersion,
    ApprovalId,
    ArtifactId,
    ConversationId,
    EffectId,
    FencingToken,
    LeaseId,
    MemoryEntryId,
    MessageId,
    ReconciliationCaseId,
    ReconciliationEvidenceId,
    RunId,
    RuntimeBindingId,
    RuntimeInvocationId,
    SessionId,
    WorkerId,
    utc_now,
)


def _require_cas(
    *,
    current: AggregateVersion,
    expected: AggregateVersion,
    new: AggregateVersion,
) -> None:
    if current != expected:
        raise ConcurrencyConflictError(
            f"expected aggregate version {expected.value}, found {current.value}"
        )
    if new != expected.next():
        raise ConcurrencyConflictError("saved aggregate version must advance by exactly one")


class MemoryRunRepository:
    def __init__(self) -> None:
        self._items: dict[RunId, Run] = {}

    async def get(self, run_id: RunId) -> Run | None:
        return self._items.get(run_id)

    async def add(self, run: Run) -> None:
        if run.id in self._items:
            raise DuplicateAggregateError(f"run {run.id} already exists")
        self._items[run.id] = run

    async def save(self, run: Run, *, expected_version: AggregateVersion) -> None:
        current = self._items.get(run.id)
        if current is None:
            raise ConcurrencyConflictError(f"run {run.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=run.version,
        )
        self._items[run.id] = run

    async def list_by_state(self, status: RunStatus) -> tuple[Run, ...]:
        return tuple(item for item in self._items.values() if item.status is status)


class MemorySessionRepository:
    def __init__(self) -> None:
        self._items: dict[SessionId, Session] = {}

    async def get(self, session_id: SessionId) -> Session | None:
        return self._items.get(session_id)

    async def add(self, session: Session) -> None:
        if session.id in self._items:
            raise DuplicateAggregateError(f"session {session.id} already exists")
        self._items[session.id] = session

    async def save(
        self,
        session: Session,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        current = self._items.get(session.id)
        if current is None:
            raise ConcurrencyConflictError(f"session {session.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=session.version,
        )
        self._items[session.id] = session


class InMemoryMemoryRepository:
    def __init__(self) -> None:
        self._items: dict[MemoryEntryId, MemoryEntry] = {}

    async def get(self, memory_id: MemoryEntryId) -> MemoryEntry | None:
        return self._items.get(memory_id)

    async def put(self, entry: MemoryEntry) -> None:
        if entry.id in self._items:
            raise DuplicateAggregateError(f"memory entry {entry.id} already exists")
        self._items[entry.id] = entry

    async def save(
        self,
        entry: MemoryEntry,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        current = self._items.get(entry.id)
        if current is None:
            raise ConcurrencyConflictError(f"memory entry {entry.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=entry.version,
        )
        self._items[entry.id] = entry

    async def list_by_scope(
        self,
        *,
        tenant_id: str,
        scope: str,
        scope_id: str | None,
    ) -> tuple[MemoryEntry, ...]:
        return tuple(
            item
            for item in self._items.values()
            if str(item.tenant_id) == tenant_id
            and item.scope.value == scope
            and item.scope_id == scope_id
        )


class MemoryConversationRepository:
    def __init__(self) -> None:
        self._items: dict[ConversationId, Conversation] = {}

    async def get(self, conversation_id: ConversationId) -> Conversation | None:
        return self._items.get(conversation_id)

    async def add(self, conversation: Conversation) -> None:
        if conversation.id in self._items:
            raise DuplicateAggregateError(f"conversation {conversation.id} already exists")
        self._items[conversation.id] = conversation

    async def save(
        self,
        conversation: Conversation,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        current = self._items.get(conversation.id)
        if current is None:
            raise ConcurrencyConflictError(f"conversation {conversation.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=conversation.version,
        )
        self._items[conversation.id] = conversation

    async def list_for_session(
        self,
        session_id: SessionId,
    ) -> tuple[Conversation, ...]:
        return tuple(item for item in self._items.values() if item.session_id == session_id)


class MemoryMessageRepository:
    def __init__(self) -> None:
        self._items: dict[MessageId, ConversationMessage] = {}
        self._conversation_ids: dict[MessageId, ConversationId] = {}

    async def append(
        self,
        conversation_id: ConversationId,
        message: ConversationMessage,
    ) -> None:
        if message.id in self._items:
            raise DuplicateAggregateError(f"message {message.id} already exists")
        self._items[message.id] = message
        self._conversation_ids[message.id] = conversation_id

    async def get(self, message_id: MessageId) -> ConversationMessage | None:
        return self._items.get(message_id)

    async def list_for_conversation(
        self,
        conversation_id: ConversationId,
    ) -> tuple[ConversationMessage, ...]:
        items = [
            message
            for message_id, message in self._items.items()
            if self._conversation_ids[message_id] == conversation_id
        ]
        return tuple(sorted(items, key=lambda item: (item.created_at, str(item.id))))


class MemoryEffectRepository:
    def __init__(self) -> None:
        self._items: dict[EffectId, Effect] = {}
        self._idempotency: dict[tuple[IdempotencyScope, str], EffectId] = {}

    async def get(self, effect_id: EffectId) -> Effect:
        return self._items[effect_id]

    async def reserve(self, effect: Effect) -> EffectReservationResult:
        if effect.idempotency_key is not None:
            identity = (
                effect.idempotency_scope,
                effect.idempotency_key.canonical,
            )
            existing_id = self._idempotency.get(identity)
            if existing_id is not None:
                existing_by_key = self._items[existing_id]
                existing_by_key.assert_same_intent(
                    effect.idempotency_key,
                    effect.fingerprint,
                )
                return EffectReservationResult(effect=existing_by_key, created=False)

        existing_by_id = self._items.get(effect.id)
        if existing_by_id is not None:
            existing_by_id.assert_same_intent(
                effect.idempotency_key,
                effect.fingerprint,
            )
            return EffectReservationResult(effect=existing_by_id, created=False)

        self._items[effect.id] = effect
        if effect.idempotency_key is not None:
            self._idempotency[(effect.idempotency_scope, effect.idempotency_key.canonical)] = (
                effect.id
            )
        return EffectReservationResult(effect=effect, created=True)

    async def find_by_idempotency_key(
        self,
        scope: IdempotencyScope,
        key: IdempotencyKey,
    ) -> Effect | None:
        effect_id = self._idempotency.get((scope, key.canonical))
        return None if effect_id is None else self._items[effect_id]

    async def save(
        self,
        effect: Effect,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        current = self._items.get(effect.id)
        if current is None:
            raise ConcurrencyConflictError(f"effect {effect.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=effect.version,
        )
        self._items[effect.id] = effect


class MemoryReconciliationRepository:
    def __init__(self) -> None:
        self._cases: dict[ReconciliationCaseId, ReconciliationCase] = {}
        self._evidence: dict[ReconciliationEvidenceId, ReconciliationEvidence] = {}

    async def get_active(self, effect_id: EffectId) -> ReconciliationCase | None:
        candidates = [
            item
            for item in self._cases.values()
            if item.effect_id == effect_id and not item.resolved
        ]
        if not candidates:
            return None
        return max(candidates, key=lambda item: item.created_at)

    async def save(
        self,
        case: ReconciliationCase,
        *,
        expected_version: AggregateVersion | None,
    ) -> None:
        current = self._cases.get(case.id)
        if expected_version is None:
            if current is not None:
                raise DuplicateAggregateError(f"reconciliation case {case.id} already exists")
            self._cases[case.id] = case
            return
        if current is None:
            raise ConcurrencyConflictError(f"reconciliation case {case.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=case.version,
        )
        self._cases[case.id] = case

    async def append_evidence(self, evidence: ReconciliationEvidence) -> None:
        if evidence.id in self._evidence:
            raise DuplicateAggregateError(f"reconciliation evidence {evidence.id} already exists")
        self._evidence[evidence.id] = evidence


class MemoryApprovalRepository:
    def __init__(self) -> None:
        self._items: dict[ApprovalId, Approval] = {}

    async def get(self, approval_id: ApprovalId) -> Approval | None:
        return self._items.get(approval_id)

    async def add(self, approval: Approval) -> None:
        if approval.id in self._items:
            raise DuplicateAggregateError(f"approval {approval.id} already exists")
        self._items[approval.id] = approval

    async def save(
        self,
        approval: Approval,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        current = self._items.get(approval.id)
        if current is None:
            raise ConcurrencyConflictError(f"approval {approval.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=approval.version,
        )
        self._items[approval.id] = approval

    async def list_pending(self) -> tuple[Approval, ...]:
        return tuple(item for item in self._items.values() if item.status is ApprovalStatus.PENDING)


class MemoryLeaseRepository:
    def __init__(self) -> None:
        self._items: dict[LeaseId, Lease] = {}
        self._current_by_resource: dict[str, LeaseId] = {}
        self._fencing: dict[str, int] = {}

    async def get_current(self, resource: str) -> Lease | None:
        lease_id = self._current_by_resource.get(resource)
        return None if lease_id is None else self._items[lease_id]

    async def add(self, lease: Lease) -> None:
        if lease.id in self._items:
            raise DuplicateAggregateError(f"lease {lease.id} already exists")
        current = await self.get_current(lease.resource)
        if (
            current is not None
            and current.id != lease.id
            and current.status is LeaseStatus.HELD
            and lease.status is LeaseStatus.HELD
        ):
            raise ConcurrencyConflictError(f"resource {lease.resource} already has an active lease")
        self._items[lease.id] = lease
        self._current_by_resource[lease.resource] = lease.id
        self._fencing[lease.resource] = max(
            self._fencing.get(lease.resource, 0),
            lease.fencing_token.value,
        )

    async def save(
        self,
        lease: Lease,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        current = self._items.get(lease.id)
        if current is None:
            raise ConcurrencyConflictError(f"lease {lease.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=lease.version,
        )
        self._items[lease.id] = lease
        self._current_by_resource[lease.resource] = lease.id
        self._fencing[lease.resource] = max(
            self._fencing.get(lease.resource, 0),
            lease.fencing_token.value,
        )

    async def next_fencing_token(self, resource: str) -> FencingToken:
        token = self._fencing.get(resource, 0) + 1
        self._fencing[resource] = token
        return FencingToken(token)


class MemoryWorkerRepository:
    def __init__(self) -> None:
        self._items: dict[WorkerId, Worker] = {}

    async def get(self, worker_id: WorkerId) -> Worker | None:
        return self._items.get(worker_id)

    async def add(self, worker: Worker) -> None:
        if worker.id in self._items:
            raise DuplicateAggregateError(f"worker {worker.id} already exists")
        self._items[worker.id] = worker

    async def save(
        self,
        worker: Worker,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        current = self._items.get(worker.id)
        if current is None:
            raise ConcurrencyConflictError(f"worker {worker.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=worker.version,
        )
        self._items[worker.id] = worker


class MemoryRuntimeRepository:
    def __init__(self) -> None:
        self._bindings: dict[RuntimeBindingId, RuntimeBinding] = {}
        self._invocations: dict[RuntimeInvocationId, RuntimeInvocation] = {}

    async def get_binding(
        self,
        binding_id: RuntimeBindingId,
    ) -> RuntimeBinding | None:
        return self._bindings.get(binding_id)

    async def add_binding(self, binding: RuntimeBinding) -> None:
        if binding.id in self._bindings:
            raise DuplicateAggregateError(f"runtime binding {binding.id} already exists")
        self._bindings[binding.id] = binding

    async def get_invocation(
        self,
        invocation_id: RuntimeInvocationId,
    ) -> RuntimeInvocation | None:
        return self._invocations.get(invocation_id)

    async def add_invocation(self, invocation: RuntimeInvocation) -> None:
        if invocation.id in self._invocations:
            raise DuplicateAggregateError(f"runtime invocation {invocation.id} already exists")
        self._invocations[invocation.id] = invocation

    async def save_invocation(
        self,
        invocation: RuntimeInvocation,
        *,
        expected_version: AggregateVersion,
    ) -> None:
        current = self._invocations.get(invocation.id)
        if current is None:
            raise ConcurrencyConflictError(f"runtime invocation {invocation.id} does not exist")
        _require_cas(
            current=current.version,
            expected=expected_version,
            new=invocation.version,
        )
        self._invocations[invocation.id] = invocation


class MemoryArtifactRepository:
    def __init__(self) -> None:
        self._items: dict[ArtifactId, Artifact] = {}

    async def get(self, artifact_id: ArtifactId) -> Artifact | None:
        return self._items.get(artifact_id)

    async def add(self, artifact: Artifact) -> None:
        if artifact.id in self._items:
            raise DuplicateAggregateError(f"artifact {artifact.id} already exists")
        self._items[artifact.id] = artifact


class MemoryAuditStore:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    async def append(self, event: AuditEvent) -> None:
        self._events.append(event)

    async def list_for_subject(self, subject: str) -> tuple[AuditEvent, ...]:
        return tuple(event for event in self._events if event.subject == subject)


class MemoryOutboxStore:
    def __init__(self) -> None:
        self._records: dict[str, OutboxRecord] = {}

    async def append(self, event: IntegrationEvent) -> None:
        if event.event_id in self._records:
            raise DuplicateAggregateError(f"outbox event {event.event_id} already exists")
        self._records[event.event_id] = OutboxRecord(event=event)

    async def claim_batch(
        self,
        *,
        worker_id: str,
        limit: int = 100,
        claim_timeout_seconds: float = 60.0,
    ) -> tuple[OutboxRecord, ...]:
        if limit < 1:
            raise ValueError("outbox claim limit must be positive")
        if claim_timeout_seconds < 0:
            raise ValueError("outbox claim timeout cannot be negative")
        now = datetime.now(UTC)
        stale_before = now - timedelta(seconds=claim_timeout_seconds)
        selected: list[OutboxRecord] = []
        for event_id, record in sorted(
            self._records.items(),
            key=lambda item: item[1].event.occurred_at,
        ):
            if len(selected) >= limit:
                break
            reclaimable = (
                record.status is OutboxStatus.CLAIMED
                and record.claimed_at is not None
                and record.claimed_at <= stale_before
            )
            if record.status not in {OutboxStatus.PENDING, OutboxStatus.FAILED} and not reclaimable:
                continue
            if record.next_attempt_at is not None and record.next_attempt_at > now:
                continue
            claimed = replace(
                record,
                status=OutboxStatus.CLAIMED,
                claimed_by=worker_id,
                claimed_at=now,
                attempt_count=record.attempt_count + 1,
            )
            self._records[event_id] = claimed
            selected.append(claimed)
        return tuple(selected)

    async def mark_published(self, event_id: str) -> None:
        record = self._records[event_id]
        self._records[event_id] = replace(
            record,
            status=OutboxStatus.PUBLISHED,
            claimed_by=None,
            claimed_at=None,
            published_at=utc_now(),
            last_error=None,
        )

    async def mark_failed(self, event_id: str, *, error: str) -> None:
        record = self._records[event_id]
        self._records[event_id] = replace(
            record,
            status=OutboxStatus.FAILED,
            claimed_by=None,
            claimed_at=None,
            last_error=error,
        )

    async def release_claim(self, event_id: str) -> None:
        record = self._records[event_id]
        self._records[event_id] = replace(
            record,
            status=OutboxStatus.PENDING,
            claimed_by=None,
            claimed_at=None,
        )


class MemoryInboxStore:
    def __init__(self) -> None:
        self._records: dict[tuple[str, str], InboxRecord] = {}

    async def reserve(self, record: InboxRecord) -> bool:
        key = (record.source, record.external_event_id)
        existing = self._records.get(key)
        if existing is None:
            self._records[key] = record
            return True
        if existing.digest != record.digest:
            raise InboxDigestConflictError("external event id was reused with a different digest")
        return False

    async def get(
        self,
        source: str,
        external_event_id: str,
    ) -> InboxRecord | None:
        return self._records.get((source, external_event_id))

    async def mark_processed(
        self,
        source: str,
        external_event_id: str,
    ) -> None:
        key = (source, external_event_id)
        record = self._records[key]
        self._records[key] = replace(
            record,
            status=InboxStatus.PROCESSED,
            processed_at=utc_now(),
            last_error=None,
        )

    async def mark_failed(
        self,
        source: str,
        external_event_id: str,
        *,
        error: str,
    ) -> None:
        key = (source, external_event_id)
        record = self._records[key]
        self._records[key] = replace(
            record,
            status=InboxStatus.FAILED,
            last_error=error,
        )


class MemoryBlobStore:
    def __init__(self) -> None:
        self._items: dict[str, bytes] = {}

    async def put(self, key: str, content: bytes) -> str:
        self._items[key] = bytes(content)
        return key

    async def get(self, key: str) -> bytes:
        return self._items[key]

    async def delete(self, key: str) -> None:
        self._items.pop(key, None)


@dataclass(slots=True)
class _MemoryUnitOfWorkSnapshot:
    runs: dict[RunId, Run]
    sessions: dict[SessionId, Session]
    conversations: dict[ConversationId, Conversation]
    messages: dict[MessageId, ConversationMessage]
    message_conversation_ids: dict[MessageId, ConversationId]
    effects: dict[EffectId, Effect]
    effect_idempotency: dict[tuple[IdempotencyScope, str], EffectId]
    memories: dict[MemoryEntryId, MemoryEntry]
    reconciliation_cases: dict[ReconciliationCaseId, ReconciliationCase]
    reconciliation_evidence: dict[ReconciliationEvidenceId, ReconciliationEvidence]
    approvals: dict[ApprovalId, Approval]
    workers: dict[WorkerId, Worker]
    artifacts: dict[ArtifactId, Artifact]
    runtime_bindings: dict[RuntimeBindingId, RuntimeBinding]
    runtime_invocations: dict[RuntimeInvocationId, RuntimeInvocation]
    outbox: dict[str, OutboxRecord]
    audit: list[AuditEvent]


class MemoryUnitOfWork:
    """Reference local transaction boundary with rollback snapshots."""

    def __init__(self) -> None:
        self.runs = MemoryRunRepository()
        self.sessions = MemorySessionRepository()
        self.conversations = MemoryConversationRepository()
        self.messages = MemoryMessageRepository()
        self.effects = MemoryEffectRepository()
        self.memories = InMemoryMemoryRepository()
        self.reconciliations = MemoryReconciliationRepository()
        self.approvals = MemoryApprovalRepository()
        self.workers = MemoryWorkerRepository()
        self.artifacts = MemoryArtifactRepository()
        self.runtimes = MemoryRuntimeRepository()
        self.outbox = MemoryOutboxStore()
        self.audit = MemoryAuditStore()
        self._committed = False
        self._snapshot: _MemoryUnitOfWorkSnapshot | None = None

    async def __aenter__(self) -> MemoryUnitOfWork:
        self._committed = False
        self._snapshot = _MemoryUnitOfWorkSnapshot(
            runs=deepcopy(self.runs._items),
            sessions=deepcopy(self.sessions._items),
            conversations=deepcopy(self.conversations._items),
            messages=deepcopy(self.messages._items),
            message_conversation_ids=deepcopy(self.messages._conversation_ids),
            effects=deepcopy(self.effects._items),
            effect_idempotency=deepcopy(self.effects._idempotency),
            memories=deepcopy(self.memories._items),
            reconciliation_cases=deepcopy(self.reconciliations._cases),
            reconciliation_evidence=deepcopy(self.reconciliations._evidence),
            approvals=deepcopy(self.approvals._items),
            workers=deepcopy(self.workers._items),
            artifacts=deepcopy(self.artifacts._items),
            runtime_bindings=deepcopy(self.runtimes._bindings),
            runtime_invocations=deepcopy(self.runtimes._invocations),
            outbox=deepcopy(self.outbox._records),
            audit=deepcopy(self.audit._events),
        )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if exc_type is not None or not self._committed:
            await self.rollback()

    async def commit(self) -> None:
        self._committed = True
        self._snapshot = None

    async def rollback(self) -> None:
        if self._snapshot is None:
            return
        snapshot = self._snapshot
        self.runs._items = deepcopy(snapshot.runs)
        self.sessions._items = deepcopy(snapshot.sessions)
        self.conversations._items = deepcopy(snapshot.conversations)
        self.messages._items = deepcopy(snapshot.messages)
        self.messages._conversation_ids = deepcopy(snapshot.message_conversation_ids)
        self.effects._items = deepcopy(snapshot.effects)
        self.effects._idempotency = deepcopy(snapshot.effect_idempotency)
        self.memories._items = deepcopy(snapshot.memories)
        self.reconciliations._cases = deepcopy(snapshot.reconciliation_cases)
        self.reconciliations._evidence = deepcopy(snapshot.reconciliation_evidence)
        self.approvals._items = deepcopy(snapshot.approvals)
        self.workers._items = deepcopy(snapshot.workers)
        self.artifacts._items = deepcopy(snapshot.artifacts)
        self.runtimes._bindings = deepcopy(snapshot.runtime_bindings)
        self.runtimes._invocations = deepcopy(snapshot.runtime_invocations)
        self.outbox._records = deepcopy(snapshot.outbox)
        self.audit._events = deepcopy(snapshot.audit)
        self._snapshot = None


__all__ = [
    "InMemoryMemoryRepository",
    "MemoryApprovalRepository",
    "MemoryArtifactRepository",
    "MemoryAuditStore",
    "MemoryBlobStore",
    "MemoryConversationRepository",
    "MemoryEffectRepository",
    "MemoryInboxStore",
    "MemoryLeaseRepository",
    "MemoryMessageRepository",
    "MemoryOutboxStore",
    "MemoryReconciliationRepository",
    "MemoryRunRepository",
    "MemoryRuntimeRepository",
    "MemorySessionRepository",
    "MemoryUnitOfWork",
    "MemoryWorkerRepository",
]
