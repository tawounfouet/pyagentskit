"""Durable checkpoints, effect journal and controlled run recovery."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
from collections.abc import Callable
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Protocol, runtime_checkable
from uuid import UUID, uuid4

from pydantic import Field, field_validator

from ._base import ContractModel
from .agents import AgentDefinition
from .exceptions import PersistenceError, RunConflictError, RunNotFoundError
from .messages import Message, MessageRole
from .privacy import Redactor
from .runs import RunContext, RunError, RunLimits, RunResult, RunStatus, utc_now
from .sessions import SessionStore
from .tools import (
    ToolCall,
    ToolDefinition,
    ToolExecutionPolicy,
    ToolExecutor,
    ToolRegistry,
    ToolResult,
)
from .usage import Usage

__all__ = [
    "CheckpointKind",
    "DurableRunner",
    "EffectRecord",
    "EffectResolution",
    "EffectStatus",
    "JournalEntry",
    "MemoryRunStore",
    "RecoveryPlan",
    "RunCheckpoint",
    "RunStore",
    "SQLiteRunStore",
    "effect_fingerprint",
    "migrate_checkpoint_document",
]


class CheckpointKind(StrEnum):
    """Stable transition names persisted by :class:`DurableRunner`."""

    RUN_STARTED = "run_started"
    TOOL_STARTED = "tool_started"
    TOOL_COMPLETED = "tool_completed"
    WAITING_APPROVAL = "waiting_approval"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_LIMIT_EXCEEDED = "run_limit_exceeded"
    RUN_INTERRUPTED = "run_interrupted"
    UNKNOWN_EFFECT = "unknown_effect"
    RUN_RECOVERED = "run_recovered"


class EffectStatus(StrEnum):
    """Lifecycle of an externally observable tool effect."""

    PLANNED = "planned"
    STARTED = "started"
    COMPLETED = "completed"
    FAILED = "failed"
    UNKNOWN = "unknown"


class EffectResolution(StrEnum):
    """Operator conclusions for an ambiguous effect."""

    NOT_APPLIED = "not_applied"
    COMMITTED = "committed"


class RunCheckpoint(ContractModel):
    """One immutable versioned run transition."""

    checkpoint_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    schema_version: int = Field(default=1, ge=1)
    run_id: UUID
    trace_id: UUID
    agent_id: str = Field(min_length=1)
    agent_version: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    tenant_id: str | None = None
    sequence: int = Field(ge=0)
    kind: CheckpointKind
    status: RunStatus
    created_at: datetime
    result: RunResult[Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def validate_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("checkpoint timestamps must be timezone-aware")
        return value


class EffectRecord(ContractModel):
    """Durable evidence for one tool call and its external-effect boundary."""

    effect_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    schema_version: int = Field(default=1, ge=1)
    run_id: UUID
    trace_id: UUID
    agent_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    tenant_id: str | None = None
    idempotency_key: str = Field(min_length=1)
    fingerprint: str = Field(min_length=64, max_length=64)
    call: ToolCall
    tool_version: str = Field(min_length=1)
    idempotent: bool
    status: EffectStatus = EffectStatus.PLANNED
    revision: int = Field(default=0, ge=0)
    planned_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None
    result: ToolResult | None = None
    recovery_count: int = Field(default=0, ge=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("planned_at", "started_at", "completed_at")
    @classmethod
    def validate_aware_time(cls, value: datetime | None) -> datetime | None:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("effect timestamps must be timezone-aware")
        return value


class JournalEntry(ContractModel):
    """Append-only decision or transition record, excluding tool payloads."""

    entry_id: str = Field(default_factory=lambda: str(uuid4()), min_length=1)
    run_id: UUID
    tenant_id: str | None = None
    sequence: int = Field(ge=0)
    kind: str = Field(min_length=1)
    created_at: datetime
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def validate_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("journal timestamps must be timezone-aware")
        return value


class RecoveryPlan(ContractModel):
    """Explain whether a run can resume without guessing an external effect."""

    run_id: UUID
    resumable: bool
    unknown_effect_ids: tuple[str, ...] = ()
    recovered_effect_ids: tuple[str, ...] = ()
    reason: str = Field(min_length=1)


def migrate_checkpoint_document(document: dict[str, Any]) -> RunCheckpoint:
    """Migrate the synthetic pre-release v0 checkpoint shape to schema v1.

    There was no public durable schema before 0.5.0. Supporting this v0 fixture
    establishes and tests the forward-migration contract without claiming a
    historical production format.
    """

    migrated = dict(document)
    version = migrated.get("schema_version", 0)
    if version == 0:
        if "timestamp" in migrated and "created_at" not in migrated:
            migrated["created_at"] = migrated.pop("timestamp")
        migrated["schema_version"] = 1
        migrated.setdefault("metadata", {})
    elif version != 1:
        raise PersistenceError(f"Unsupported checkpoint schema version: {version}")
    return RunCheckpoint.model_validate_json(json.dumps(migrated))


@runtime_checkable
class RunStore(Protocol):
    """Replaceable durable store with optimistic transitions."""

    async def append_checkpoint(
        self, checkpoint: RunCheckpoint, *, expected_previous_sequence: int | None = None
    ) -> RunCheckpoint: ...

    async def latest_checkpoint(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> RunCheckpoint: ...

    async def list_checkpoints(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[RunCheckpoint, ...]: ...

    async def plan_effect(self, effect: EffectRecord) -> EffectRecord: ...

    async def get_effect(self, effect_id: str, *, tenant_id: str | None = None) -> EffectRecord: ...

    async def get_effect_by_key(
        self, run_id: UUID, idempotency_key: str, *, tenant_id: str | None = None
    ) -> EffectRecord | None: ...

    async def list_effects(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[EffectRecord, ...]: ...

    async def transition_effect(
        self,
        effect_id: str,
        status: EffectStatus,
        *,
        tenant_id: str | None = None,
        expected_revision: int,
        result: ToolResult | None = None,
    ) -> EffectRecord: ...

    async def resolve_effect(
        self,
        effect_id: str,
        resolution: EffectResolution,
        *,
        tenant_id: str | None = None,
        expected_revision: int,
        result: ToolResult | None = None,
    ) -> EffectRecord: ...

    async def list_journal(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[JournalEntry, ...]: ...


def _scope(tenant_id: str | None) -> str:
    return tenant_id or ""


def effect_fingerprint(call: ToolCall, definition: ToolDefinition) -> str:
    """Return a deterministic digest without putting arguments in journal entries."""

    payload = {
        "call": call.model_dump(mode="json"),
        "tool_version": definition.version,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(canonical).hexdigest()


class _Aggregate(ContractModel):
    checkpoints: tuple[RunCheckpoint, ...] = ()
    effects: tuple[EffectRecord, ...] = ()
    journal: tuple[JournalEntry, ...] = ()


class _StoreLogic:
    """Pure aggregate transitions shared by memory and SQLite implementations."""

    @staticmethod
    def journal(
        aggregate: _Aggregate, run_id: UUID, tenant_id: str | None, kind: str, **metadata: Any
    ) -> _Aggregate:
        entry = JournalEntry(
            run_id=run_id,
            tenant_id=tenant_id,
            sequence=len(aggregate.journal),
            kind=kind,
            created_at=utc_now(),
            metadata=metadata,
        )
        return aggregate.model_copy(update={"journal": (*aggregate.journal, entry)})

    @classmethod
    def checkpoint(
        cls, aggregate: _Aggregate, item: RunCheckpoint, expected: int | None
    ) -> _Aggregate:
        previous = len(aggregate.checkpoints) - 1
        if expected is not None and previous != expected:
            raise RunConflictError("Checkpoint sequence changed")
        if item.sequence != previous + 1:
            raise RunConflictError("Checkpoint sequence is not contiguous")
        updated = aggregate.model_copy(update={"checkpoints": (*aggregate.checkpoints, item)})
        return cls.journal(
            updated,
            item.run_id,
            item.tenant_id,
            f"checkpoint.{item.kind.value}",
            checkpoint_id=item.checkpoint_id,
            status=item.status.value,
        )

    @classmethod
    def plan(cls, aggregate: _Aggregate, item: EffectRecord) -> tuple[_Aggregate, EffectRecord]:
        for existing in aggregate.effects:
            if existing.idempotency_key == item.idempotency_key:
                if existing.fingerprint != item.fingerprint:
                    raise RunConflictError("Effect idempotency key payload conflict")
                return aggregate, existing
        updated = aggregate.model_copy(update={"effects": (*aggregate.effects, item)})
        updated = cls.journal(
            updated,
            item.run_id,
            item.tenant_id,
            "effect.planned",
            effect_id=item.effect_id,
            call_id=item.call.id,
            tool_name=item.call.name,
            fingerprint=item.fingerprint,
        )
        return updated, item

    @classmethod
    def transition(
        cls,
        aggregate: _Aggregate,
        effect_id: str,
        status: EffectStatus,
        expected_revision: int,
        result: ToolResult | None,
    ) -> tuple[_Aggregate, EffectRecord]:
        selected = next((item for item in aggregate.effects if item.effect_id == effect_id), None)
        if selected is None:
            raise RunNotFoundError("Effect not found")
        if selected.revision != expected_revision:
            raise RunConflictError("Effect revision conflict")
        allowed = {
            EffectStatus.PLANNED: {EffectStatus.STARTED, EffectStatus.FAILED},
            EffectStatus.STARTED: {
                EffectStatus.COMPLETED,
                EffectStatus.FAILED,
                EffectStatus.UNKNOWN,
            },
        }
        if status not in allowed.get(selected.status, set()):
            raise RunConflictError(f"Invalid effect transition {selected.status} -> {status}")
        now = utc_now()
        changes: dict[str, Any] = {"status": status, "revision": selected.revision + 1}
        if status is EffectStatus.STARTED:
            changes["started_at"] = now
        if status in {EffectStatus.COMPLETED, EffectStatus.FAILED, EffectStatus.UNKNOWN}:
            changes["completed_at"] = now
        if status is EffectStatus.COMPLETED:
            if result is None:
                raise RunConflictError("Completed effects require a ToolResult")
            changes["result"] = result
        updated_effect = selected.model_copy(update=changes)
        effects = tuple(
            updated_effect if item.effect_id == effect_id else item for item in aggregate.effects
        )
        updated = aggregate.model_copy(update={"effects": effects})
        updated = cls.journal(
            updated,
            selected.run_id,
            selected.tenant_id,
            f"effect.{status.value}",
            effect_id=effect_id,
            call_id=selected.call.id,
            tool_name=selected.call.name,
        )
        return updated, updated_effect

    @classmethod
    def resolve(
        cls,
        aggregate: _Aggregate,
        effect_id: str,
        resolution: EffectResolution,
        expected_revision: int,
        result: ToolResult | None,
    ) -> tuple[_Aggregate, EffectRecord]:
        selected = next((item for item in aggregate.effects if item.effect_id == effect_id), None)
        if selected is None:
            raise RunNotFoundError("Effect not found")
        if selected.revision != expected_revision or selected.status is not EffectStatus.UNKNOWN:
            raise RunConflictError("Only the current unknown effect can be reconciled")
        if resolution is EffectResolution.COMMITTED and result is None:
            raise RunConflictError("Committed resolution requires the observed ToolResult")
        status = (
            EffectStatus.COMPLETED
            if resolution is EffectResolution.COMMITTED
            else EffectStatus.PLANNED
        )
        changes: dict[str, Any] = {
            "status": status,
            "revision": selected.revision + 1,
            "recovery_count": selected.recovery_count + 1,
            "completed_at": utc_now() if status is EffectStatus.COMPLETED else None,
            "started_at": None if status is EffectStatus.PLANNED else selected.started_at,
        }
        if result is not None:
            changes["result"] = result
        updated_effect = selected.model_copy(update=changes)
        effects = tuple(
            updated_effect if item.effect_id == effect_id else item for item in aggregate.effects
        )
        updated = aggregate.model_copy(update={"effects": effects})
        updated = cls.journal(
            updated,
            selected.run_id,
            selected.tenant_id,
            "effect.reconciled",
            effect_id=effect_id,
            resolution=resolution.value,
        )
        return updated, updated_effect


class MemoryRunStore:
    """Process-local reference implementation of :class:`RunStore`."""

    def __init__(self) -> None:
        self._runs: dict[tuple[str, UUID], _Aggregate] = {}
        self._lock = asyncio.Lock()

    def _get(self, run_id: UUID, tenant_id: str | None) -> _Aggregate:
        try:
            return self._runs[(_scope(tenant_id), run_id)]
        except KeyError as exc:
            raise RunNotFoundError("Durable run not found") from exc

    async def append_checkpoint(
        self, checkpoint: RunCheckpoint, *, expected_previous_sequence: int | None = None
    ) -> RunCheckpoint:
        key = (_scope(checkpoint.tenant_id), checkpoint.run_id)
        async with self._lock:
            aggregate = self._runs.get(key, _Aggregate())
            self._runs[key] = _StoreLogic.checkpoint(
                aggregate, checkpoint, expected_previous_sequence
            )
        return checkpoint

    async def latest_checkpoint(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> RunCheckpoint:
        checkpoints = self._get(run_id, tenant_id).checkpoints
        if not checkpoints:
            raise RunNotFoundError("Durable run has no checkpoint")
        return checkpoints[-1]

    async def list_checkpoints(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[RunCheckpoint, ...]:
        return self._get(run_id, tenant_id).checkpoints

    async def plan_effect(self, effect: EffectRecord) -> EffectRecord:
        key = (_scope(effect.tenant_id), effect.run_id)
        async with self._lock:
            aggregate = self._runs.get(key, _Aggregate())
            updated, selected = _StoreLogic.plan(aggregate, effect)
            self._runs[key] = updated
            return selected

    async def get_effect(self, effect_id: str, *, tenant_id: str | None = None) -> EffectRecord:
        scope = _scope(tenant_id)
        for (stored_scope, _), aggregate in self._runs.items():
            if stored_scope == scope:
                for effect in aggregate.effects:
                    if effect.effect_id == effect_id:
                        return effect
        raise RunNotFoundError("Effect not found")

    async def get_effect_by_key(
        self, run_id: UUID, idempotency_key: str, *, tenant_id: str | None = None
    ) -> EffectRecord | None:
        aggregate = self._runs.get((_scope(tenant_id), run_id))
        if aggregate is None:
            return None
        return next((e for e in aggregate.effects if e.idempotency_key == idempotency_key), None)

    async def list_effects(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[EffectRecord, ...]:
        return self._get(run_id, tenant_id).effects

    async def transition_effect(
        self,
        effect_id: str,
        status: EffectStatus,
        *,
        tenant_id: str | None = None,
        expected_revision: int,
        result: ToolResult | None = None,
    ) -> EffectRecord:
        current = await self.get_effect(effect_id, tenant_id=tenant_id)
        key = (_scope(tenant_id), current.run_id)
        async with self._lock:
            updated, selected = _StoreLogic.transition(
                self._runs[key], effect_id, status, expected_revision, result
            )
            self._runs[key] = updated
            return selected

    async def resolve_effect(
        self,
        effect_id: str,
        resolution: EffectResolution,
        *,
        tenant_id: str | None = None,
        expected_revision: int,
        result: ToolResult | None = None,
    ) -> EffectRecord:
        current = await self.get_effect(effect_id, tenant_id=tenant_id)
        key = (_scope(tenant_id), current.run_id)
        async with self._lock:
            updated, selected = _StoreLogic.resolve(
                self._runs[key], effect_id, resolution, expected_revision, result
            )
            self._runs[key] = updated
            return selected

    async def list_journal(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[JournalEntry, ...]:
        return self._get(run_id, tenant_id).journal


class SQLiteRunStore(MemoryRunStore):
    """SQLite aggregate store with schema migration v1 and atomic replacement."""

    schema_version = 1

    def __init__(self, path: str | Path) -> None:
        super().__init__()
        self.path = Path(path)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(self.path, check_same_thread=False, isolation_level=None)
            self._db.execute("PRAGMA journal_mode=WAL")
            self._migrate()
            self._load()
        except (OSError, sqlite3.Error) as exc:
            raise PersistenceError("Cannot initialize SQLite run store") from exc

    def _migrate(self) -> None:
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS schema_migrations "
            "(component TEXT PRIMARY KEY, version INTEGER NOT NULL)"
        )
        row = self._db.execute(
            "SELECT version FROM schema_migrations WHERE component='durable_runs'"
        ).fetchone()
        version = 0 if row is None else int(row[0])
        if version > self.schema_version:
            raise PersistenceError("Run database schema is newer than this package")
        if version == 0:
            self._db.executescript(
                """
                BEGIN IMMEDIATE;
                CREATE TABLE durable_runs (
                    tenant_scope TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    PRIMARY KEY (tenant_scope, run_id)
                );
                INSERT INTO schema_migrations(component, version)
                VALUES ('durable_runs', 1);
                COMMIT;
                """
            )

    def _load(self) -> None:
        for tenant_scope, run_id, payload in self._db.execute(
            "SELECT tenant_scope, run_id, payload_json FROM durable_runs"
        ):
            document = json.loads(payload)
            document["checkpoints"] = [
                migrate_checkpoint_document(item).model_dump(mode="json")
                for item in document.get("checkpoints", [])
            ]
            self._runs[(str(tenant_scope), UUID(str(run_id)))] = _Aggregate.model_validate_json(
                json.dumps(document)
            )

    def _flush(self, key: tuple[str, UUID]) -> None:
        aggregate = self._runs[key]
        try:
            self._db.execute("BEGIN IMMEDIATE")
            self._db.execute(
                "INSERT INTO durable_runs(tenant_scope, run_id, payload_json) VALUES (?, ?, ?) "
                "ON CONFLICT(tenant_scope, run_id) DO UPDATE SET "
                "payload_json=excluded.payload_json",
                (key[0], str(key[1]), aggregate.model_dump_json()),
            )
            self._db.execute("COMMIT")
        except sqlite3.Error as exc:
            self._db.execute("ROLLBACK")
            raise PersistenceError("Cannot persist durable run") from exc

    async def append_checkpoint(
        self, checkpoint: RunCheckpoint, *, expected_previous_sequence: int | None = None
    ) -> RunCheckpoint:
        result = await super().append_checkpoint(
            checkpoint, expected_previous_sequence=expected_previous_sequence
        )
        self._flush((_scope(checkpoint.tenant_id), checkpoint.run_id))
        return result

    async def plan_effect(self, effect: EffectRecord) -> EffectRecord:
        result = await super().plan_effect(effect)
        self._flush((_scope(effect.tenant_id), effect.run_id))
        return result

    async def transition_effect(
        self,
        effect_id: str,
        status: EffectStatus,
        *,
        tenant_id: str | None = None,
        expected_revision: int,
        result: ToolResult | None = None,
    ) -> EffectRecord:
        updated = await super().transition_effect(
            effect_id,
            status,
            tenant_id=tenant_id,
            expected_revision=expected_revision,
            result=result,
        )
        self._flush((_scope(updated.tenant_id), updated.run_id))
        return updated

    async def resolve_effect(
        self,
        effect_id: str,
        resolution: EffectResolution,
        *,
        tenant_id: str | None = None,
        expected_revision: int,
        result: ToolResult | None = None,
    ) -> EffectRecord:
        updated = await super().resolve_effect(
            effect_id,
            resolution,
            tenant_id=tenant_id,
            expected_revision=expected_revision,
            result=result,
        )
        self._flush((_scope(updated.tenant_id), updated.run_id))
        return updated

    def close(self) -> None:
        """Close the SQLite connection."""

        self._db.close()


class _DurableToolPolicy(ToolExecutionPolicy):
    def __init__(self, store: RunStore, checkpoint: Callable[..., Any], redactor: Redactor) -> None:
        self.store = store
        self.checkpoint = checkpoint
        self.redactor = redactor

    async def before_execute(
        self, call: ToolCall, definition: ToolDefinition, *, context: RunContext[Any]
    ) -> None:
        tenant_id = context.metadata.get("tenant_id")
        fingerprint = effect_fingerprint(call, definition)
        key = f"{context.run_id}:{call.id}:{fingerprint}"
        call_document = call.model_dump(mode="json")
        safe_call_document = self.redactor.redact(call_document)
        safe_call = ToolCall.model_validate_json(json.dumps(safe_call_document))
        arguments_redacted = safe_call_document != call_document
        effect = EffectRecord(
            run_id=context.run_id,
            trace_id=context.trace_id,
            agent_id=context.agent_id,
            session_id=context.session_id or "",
            tenant_id=tenant_id,
            idempotency_key=key,
            fingerprint=fingerprint,
            call=safe_call,
            tool_version=definition.version,
            idempotent=definition.idempotent and not arguments_redacted,
            planned_at=utc_now(),
            metadata={"arguments_redacted": arguments_redacted},
        )
        effect = await self.store.plan_effect(effect)
        if effect.status is not EffectStatus.PLANNED:
            raise RunConflictError(f"Effect cannot execute from {effect.status.value}")
        effect = await self.store.transition_effect(
            effect.effect_id,
            EffectStatus.STARTED,
            tenant_id=tenant_id,
            expected_revision=effect.revision,
        )
        await self.checkpoint(context, CheckpointKind.TOOL_STARTED, effect_id=effect.effect_id)

    async def after_execute(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        result: ToolResult,
        *,
        context: RunContext[Any],
    ) -> ToolResult:
        tenant_id = context.metadata.get("tenant_id")
        fingerprint = effect_fingerprint(call, definition)
        key = f"{context.run_id}:{call.id}:{fingerprint}"
        effect = await self.store.get_effect_by_key(context.run_id, key, tenant_id=tenant_id)
        if effect is None:
            raise RunNotFoundError("Planned effect disappeared")
        completed = await self.store.transition_effect(
            effect.effect_id,
            EffectStatus.COMPLETED,
            tenant_id=tenant_id,
            expected_revision=effect.revision,
            result=ToolResult.model_validate_json(
                json.dumps(self.redactor.redact(result.model_dump(mode="json")))
            ),
        )
        await self.checkpoint(context, CheckpointKind.TOOL_COMPLETED, effect_id=completed.effect_id)
        return result


class DurableRunner:
    """Checkpointed wrapper around a Runner, requiring a persistent session."""

    def __init__(
        self, runner: Any, run_store: RunStore, *, redactor: Redactor | None = None
    ) -> None:
        from .runtime import Runner

        if not isinstance(runner, Runner):
            raise TypeError("DurableRunner requires a Runner")
        if runner.session_store is None:
            raise ValueError("DurableRunner requires Runner.session_store")
        self.runner: Runner = runner
        self.run_store = run_store
        self.redactor = redactor or Redactor()
        policy = _DurableToolPolicy(run_store, self._tool_checkpoint, self.redactor)
        original = runner.tools
        executor = original.executor
        durable_executor = ToolExecutor(
            policies=(*executor.policies, policy), event_sinks=executor.event_sinks
        )
        runner.tools = ToolRegistry(
            (original.get(name) for name in original.names()), executor=durable_executor
        )
        self._agents: dict[UUID, AgentDefinition] = {}

    @property
    def session_store(self) -> SessionStore:
        store = self.runner.session_store
        assert store is not None
        return store

    async def _append_checkpoint(
        self,
        agent: AgentDefinition,
        context: RunContext[Any],
        kind: CheckpointKind,
        status: RunStatus,
        *,
        result: RunResult[Any] | None = None,
        **metadata: Any,
    ) -> RunCheckpoint:
        tenant_id = context.metadata.get("tenant_id")
        try:
            latest = await self.run_store.latest_checkpoint(context.run_id, tenant_id=tenant_id)
            previous = latest.sequence
        except RunNotFoundError:
            previous = -1
        checkpoint = RunCheckpoint(
            run_id=context.run_id,
            trace_id=context.trace_id,
            agent_id=agent.id,
            agent_version=agent.version,
            session_id=context.session_id or "",
            tenant_id=tenant_id,
            sequence=previous + 1,
            kind=kind,
            status=status,
            created_at=self.runner.clock(),
            result=(
                None
                if result is None
                else RunResult[Any].model_validate_json(
                    json.dumps(self.redactor.redact(result.model_dump(mode="json")))
                )
            ),
            metadata=self.redactor.redact(metadata),
        )
        return await self.run_store.append_checkpoint(
            checkpoint, expected_previous_sequence=previous
        )

    async def _tool_checkpoint(
        self, context: RunContext[Any], kind: CheckpointKind, **metadata: Any
    ) -> RunCheckpoint:
        agent = self._agents.get(context.run_id)
        if agent is None:
            latest = await self.run_store.latest_checkpoint(
                context.run_id, tenant_id=context.metadata.get("tenant_id")
            )
            checkpoint = RunCheckpoint(
                run_id=context.run_id,
                trace_id=context.trace_id,
                agent_id=latest.agent_id,
                agent_version=latest.agent_version,
                session_id=context.session_id or "",
                tenant_id=context.metadata.get("tenant_id"),
                sequence=latest.sequence + 1,
                kind=kind,
                status=RunStatus.RUNNING,
                created_at=self.runner.clock(),
                metadata=metadata,
            )
            return await self.run_store.append_checkpoint(
                checkpoint, expected_previous_sequence=latest.sequence
            )
        return await self._append_checkpoint(agent, context, kind, RunStatus.RUNNING, **metadata)

    async def run(
        self,
        agent: AgentDefinition,
        input: str,
        *,
        context: RunContext[Any],
        limits: RunLimits | None = None,
        output_type: Any = None,
        recover_tool_errors: bool = False,
        context_budget: Any = None,
    ) -> RunResult[Any]:
        """Run with transition checkpoints and effect ambiguity detection."""

        if context.session_id is None:
            raise ValueError("Durable runs require RunContext.session_id")
        self._agents[context.run_id] = agent
        await self._append_checkpoint(agent, context, CheckpointKind.RUN_STARTED, RunStatus.RUNNING)
        try:
            result = await self.runner.run(
                agent,
                input,
                context=context,
                limits=limits,
                output_type=output_type,
                recover_tool_errors=recover_tool_errors,
                context_budget=context_budget,
            )
        except asyncio.CancelledError:
            await self._mark_started_unknown(context)
            await self._append_checkpoint(
                agent, context, CheckpointKind.RUN_INTERRUPTED, RunStatus.CANCELLED
            )
            raise
        result = await self._finalize_result(agent, context, result)
        return result

    async def _mark_started_unknown(self, context: RunContext[Any]) -> tuple[str, ...]:
        tenant_id = context.metadata.get("tenant_id")
        effects = await self.run_store.list_effects(context.run_id, tenant_id=tenant_id)
        changed: list[str] = []
        for effect in effects:
            if effect.status is EffectStatus.STARTED:
                await self.run_store.transition_effect(
                    effect.effect_id,
                    EffectStatus.UNKNOWN,
                    tenant_id=tenant_id,
                    expected_revision=effect.revision,
                )
                changed.append(effect.effect_id)
        return tuple(changed)

    async def _finalize_result(
        self, agent: AgentDefinition, context: RunContext[Any], result: RunResult[Any]
    ) -> RunResult[Any]:
        unknown = await self._mark_started_unknown(context)
        if unknown:
            result = result.model_copy(
                update={
                    "status": RunStatus.UNKNOWN_EFFECT,
                    "output": None,
                    "error": RunError(
                        type="run.unknown_effect",
                        message="External effect requires operator reconciliation",
                        details={"effect_ids": list(unknown)},
                    ),
                    "metadata": {**result.metadata, "unknown_effect_ids": list(unknown)},
                }
            )
        mapping = {
            RunStatus.COMPLETED: CheckpointKind.RUN_COMPLETED,
            RunStatus.FAILED: CheckpointKind.RUN_FAILED,
            RunStatus.LIMIT_EXCEEDED: CheckpointKind.RUN_LIMIT_EXCEEDED,
            RunStatus.WAITING_APPROVAL: CheckpointKind.WAITING_APPROVAL,
            RunStatus.UNKNOWN_EFFECT: CheckpointKind.UNKNOWN_EFFECT,
        }
        kind = mapping.get(result.status, CheckpointKind.RUN_FAILED)
        await self._append_checkpoint(agent, context, kind, result.status, result=result)
        self._agents.pop(context.run_id, None)
        return result

    async def recovery_plan(self, run_id: UUID, *, tenant_id: str | None = None) -> RecoveryPlan:
        effects = await self.run_store.list_effects(run_id, tenant_id=tenant_id)
        unknown = tuple(item.effect_id for item in effects if item.status is EffectStatus.UNKNOWN)
        if unknown:
            return RecoveryPlan(
                run_id=run_id,
                resumable=False,
                unknown_effect_ids=unknown,
                reason="Reconcile every unknown effect before resuming",
            )
        return RecoveryPlan(run_id=run_id, resumable=True, reason="No ambiguous effect remains")

    async def resume_approval(
        self,
        agent: AgentDefinition,
        approval_id: str,
        *,
        context: RunContext[Any],
        limits: RunLimits | None = None,
        output_type: Any = None,
        recover_tool_errors: bool = False,
        context_budget: Any = None,
    ) -> RunResult[Any]:
        """Resume an approved call while preserving the durable effect journal."""

        if context.session_id is None:
            raise ValueError("Durable approval resume requires RunContext.session_id")
        self._agents[context.run_id] = agent
        result = await self.runner.resume_approval(
            agent,
            approval_id,
            context=context,
            limits=limits,
            output_type=output_type,
            recover_tool_errors=recover_tool_errors,
            context_budget=context_budget,
        )
        return await self._finalize_result(agent, context, result)

    async def resume(
        self,
        agent: AgentDefinition,
        run_id: UUID,
        *,
        deps: Any = None,
        tenant_id: str | None = None,
        limits: RunLimits | None = None,
        output_type: Any = None,
    ) -> RunResult[Any]:
        """Resume from persisted session state after explicit effect reconciliation."""

        latest = await self.run_store.latest_checkpoint(run_id, tenant_id=tenant_id)
        if latest.agent_id != agent.id or latest.agent_version != agent.version:
            raise RunConflictError("Agent identity or version changed since checkpoint")
        if latest.status is RunStatus.COMPLETED:
            raise RunConflictError("A completed durable run cannot be resumed")
        if latest.status is RunStatus.WAITING_APPROVAL:
            raise RunConflictError("Use resume_approval for a waiting durable run")
        plan = await self.recovery_plan(run_id, tenant_id=tenant_id)
        if not plan.resumable:
            return RunResult(
                run_id=run_id,
                trace_id=latest.trace_id,
                agent_id=agent.id,
                status=RunStatus.UNKNOWN_EFFECT,
                error=RunError(
                    type="run.unknown_effect",
                    message=plan.reason,
                    details={"effect_ids": list(plan.unknown_effect_ids)},
                ),
                usage=Usage(),
                started_at=latest.created_at,
                completed_at=self.runner.clock(),
                metadata={"unknown_effect_ids": list(plan.unknown_effect_ids)},
            )
        context = RunContext(
            agent_id=agent.id,
            deps=deps,
            run_id=run_id,
            trace_id=latest.trace_id,
            session_id=latest.session_id,
            started_at=latest.created_at,
            metadata={} if tenant_id is None else {"tenant_id": tenant_id},
        )
        recovered = await self._recover_pending_tools(agent, context)
        self._agents[run_id] = agent
        await self._append_checkpoint(
            agent,
            context,
            CheckpointKind.RUN_RECOVERED,
            RunStatus.RUNNING,
            recovered_effect_ids=list(recovered),
        )
        result = await self.runner.run(
            agent,
            "durable-resume",
            context=context,
            limits=limits,
            output_type=output_type,
            _resume_session=True,
        )
        return await self._finalize_result(agent, context, result)

    async def _recover_pending_tools(
        self, agent: AgentDefinition, context: RunContext[Any]
    ) -> tuple[str, ...]:
        tenant_id = context.metadata.get("tenant_id")
        entries = await self.session_store.list_entries(
            context.session_id or "", tenant_id=tenant_id
        )
        effects = await self.run_store.list_effects(context.run_id, tenant_id=tenant_id)
        observed = {
            entry.message.tool_call_id
            for entry in entries
            if entry.message.role is MessageRole.TOOL
        }
        announced = {
            call.id
            for entry in entries
            if entry.message.role is MessageRole.ASSISTANT
            for call in entry.message.tool_calls
        }
        for effect in effects:
            if (
                effect.call.id not in observed
                and effect.call.id not in announced
                and effect.status in {EffectStatus.PLANNED, EffectStatus.COMPLETED}
            ):
                assistant_message = Message(
                    role=MessageRole.ASSISTANT,
                    tool_calls=(effect.call,),
                    metadata={"recovered_from_effect_id": effect.effect_id},
                )
                await self.session_store.append(
                    context.session_id or "",
                    (assistant_message,),
                    turn_id=str(context.run_id),
                    tenant_id=tenant_id,
                    run_id=context.run_id,
                    idempotency_key=f"{context.run_id}:recovery:assistant:{effect.call.id}",
                )
        entries = await self.session_store.list_entries(
            context.session_id or "", tenant_id=tenant_id
        )
        pending = [
            call
            for entry in entries
            if entry.message.role is MessageRole.ASSISTANT
            for call in entry.message.tool_calls
            if call.id not in observed
        ]
        by_call = {effect.call.id: effect for effect in effects}
        recovered: list[str] = []
        for call in pending:
            current_effect = by_call.get(call.id)
            if current_effect is None:
                raise RunConflictError("Pending tool call has no durable effect record")
            if current_effect.status is EffectStatus.PLANNED:
                if current_effect.metadata.get("arguments_redacted") is True:
                    raise RunConflictError(
                        "Redacted tool arguments cannot be replayed; start a new run"
                    )
                if call.name not in agent.tools:
                    raise RunConflictError("Pending tool is no longer allowed")
                await self.runner.tools.execute_call(call, context=context)
                fingerprint = effect_fingerprint(call, self.runner.tools.get(call.name).definition)
                key = f"{context.run_id}:{call.id}:{fingerprint}"
                current_effect = await self.run_store.get_effect_by_key(
                    context.run_id, key, tenant_id=tenant_id
                )
                if current_effect is None or current_effect.result is None:
                    raise RunConflictError("Recovered tool result was not committed")
            if current_effect.status is not EffectStatus.COMPLETED or current_effect.result is None:
                raise RunConflictError("Pending tool effect is not recoverable")
            tool_message = Message.from_text(
                MessageRole.TOOL,
                current_effect.result.model_dump_json(),
                name=call.name,
                tool_call_id=call.id,
            )
            await self.session_store.append(
                context.session_id or "",
                (tool_message,),
                turn_id=str(context.run_id),
                tenant_id=tenant_id,
                run_id=context.run_id,
                idempotency_key=f"{context.run_id}:recovery:{call.id}",
            )
            recovered.append(current_effect.effect_id)
        return tuple(recovered)

    async def replay(
        self, run_id: UUID, *, tenant_id: str | None = None
    ) -> tuple[JournalEntry, ...]:
        """Return analytical history only; never invoke a model or tool."""

        return await self.run_store.list_journal(run_id, tenant_id=tenant_id)
