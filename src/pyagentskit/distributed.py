"""Lease-coordinated durable execution with explicit fencing propagation.

This module is intentionally additive: the stable package-root API remains
unchanged.  Import distributed execution contracts from ``pyagentskit.distributed``.
"""

from __future__ import annotations

import asyncio
import importlib
import math
from collections.abc import Awaitable, Callable, Iterable
from contextlib import suppress
from contextvars import ContextVar, Token
from dataclasses import replace
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, ClassVar, Protocol, TypeVar, cast, runtime_checkable
from uuid import UUID

from pydantic import Field, field_validator, model_validator

from ._base import ContractModel
from ._tool_execution import ToolExecutor
from .agents import AgentDefinition
from .coordination import (
    Lease,
    LeaseConflictError,
    LeaseNotFoundError,
    LeaseStore,
)
from .durability import DurableRunner
from .exceptions import PersistenceError
from .runs import RunContext, RunLimits, RunResult, utc_now
from .tools import ToolCall, ToolDefinition, ToolExecutionPolicy, ToolRegistry, ToolResult
from .types import NonEmptyString

__all__ = [
    "DistributedAdmissionError",
    "DistributedDurableRunner",
    "DistributedEventSink",
    "DistributedEventType",
    "DistributedExecutionPolicy",
    "DistributedMetrics",
    "DistributedMetricsSink",
    "DistributedOperationEvent",
    "DistributedWorkerController",
    "DistributedWorkerHealth",
    "DistributedWorkerState",
    "FencedOperationStore",
    "FencingToken",
    "JsonLinesDistributedEventSink",
    "LeaseLostError",
    "LeaseRenewalLimitError",
    "MemoryDistributedEventSink",
    "OpenTelemetryDistributedEventSink",
    "fencing_token_from_context",
    "resource_id_for_run",
]

ResultT = TypeVar("ResultT")


class LeaseLostError(LeaseConflictError):
    """The worker must stop because its durable-run lease is no longer current."""


class LeaseRenewalLimitError(LeaseLostError):
    """The configured finite renewal budget was exhausted."""


class DistributedAdmissionError(LeaseConflictError):
    """The worker is draining, stopped or at its explicit admission limit."""


class DistributedEventType(StrEnum):
    """Payload-free lifecycle vocabulary for distributed operations."""

    LEASE_ACQUIRE_STARTED = "lease.acquire.started"
    LEASE_ACQUIRED = "lease.acquired"
    LEASE_CONFLICT = "lease.conflict"
    LEASE_RENEWED = "lease.renewed"
    LEASE_LOST = "lease.lost"
    LEASE_RELEASED = "lease.released"
    TAKEOVER = "lease.takeover"
    ADMISSION_REJECTED = "worker.admission.rejected"
    DRAIN_STARTED = "worker.drain.started"
    DRAIN_COMPLETED = "worker.drain.completed"
    DRAIN_TIMED_OUT = "worker.drain.timed_out"


class DistributedOperationEvent(ContractModel):
    """Safe operational fact containing identifiers but no prompts or tool payloads."""

    type: DistributedEventType
    occurred_at: datetime = Field(default_factory=utc_now)
    owner_id: NonEmptyString
    run_id: UUID | None = None
    resource_id: NonEmptyString | None = None
    tenant_id: NonEmptyString | None = None
    fencing_token: int | None = Field(default=None, ge=1)
    lease_revision: int | None = Field(default=None, ge=0)
    active_runs: int | None = Field(default=None, ge=0)
    reason: NonEmptyString | None = None

    @field_validator("occurred_at")
    @classmethod
    def validate_aware_time(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("distributed event timestamp must be timezone-aware")
        return value


@runtime_checkable
class DistributedEventSink(Protocol):
    """Asynchronous sink for payload-safe distributed lifecycle facts."""

    def emit(self, event: DistributedOperationEvent) -> Awaitable[None]: ...


class MemoryDistributedEventSink:
    """In-process audit sink for tests and local diagnostics."""

    def __init__(self) -> None:
        self.events: list[DistributedOperationEvent] = []

    async def emit(self, event: DistributedOperationEvent) -> None:
        self.events.append(event)


class JsonLinesDistributedEventSink:
    """Append-only local audit sink containing only safe distributed events."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self._lock = asyncio.Lock()

    def _append(self, document: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(document)
            stream.write("\n")

    async def emit(self, event: DistributedOperationEvent) -> None:
        async with self._lock:
            try:
                await asyncio.to_thread(self._append, event.model_dump_json())
            except OSError as exc:
                raise PersistenceError("Cannot append distributed audit event") from exc

    def _read(self) -> tuple[DistributedOperationEvent, ...]:
        if not self.path.exists():
            return ()
        try:
            lines = self.path.read_text(encoding="utf-8").splitlines()
            return tuple(
                DistributedOperationEvent.model_validate_json(line)
                for line in lines
                if line.strip()
            )
        except (OSError, ValueError) as exc:
            raise PersistenceError("Cannot read distributed audit events") from exc

    async def read(self) -> tuple[DistributedOperationEvent, ...]:
        """Read and validate the local audit journal in append order."""

        async with self._lock:
            return await asyncio.to_thread(self._read)


class DistributedMetrics(ContractModel):
    """Immutable snapshot of distributed execution lifecycle counters."""

    acquisition_attempts: int = Field(default=0, ge=0)
    acquisitions: int = Field(default=0, ge=0)
    acquisition_conflicts: int = Field(default=0, ge=0)
    renewals: int = Field(default=0, ge=0)
    lease_losses: int = Field(default=0, ge=0)
    releases: int = Field(default=0, ge=0)
    takeovers: int = Field(default=0, ge=0)
    admissions_rejected: int = Field(default=0, ge=0)
    drains_started: int = Field(default=0, ge=0)
    drains_completed: int = Field(default=0, ge=0)
    drains_timed_out: int = Field(default=0, ge=0)


class DistributedMetricsSink:
    """Dependency-free distributed metrics sink."""

    _mapping: ClassVar[dict[DistributedEventType, str]] = {
        DistributedEventType.LEASE_ACQUIRE_STARTED: "acquisition_attempts",
        DistributedEventType.LEASE_ACQUIRED: "acquisitions",
        DistributedEventType.LEASE_CONFLICT: "acquisition_conflicts",
        DistributedEventType.LEASE_RENEWED: "renewals",
        DistributedEventType.LEASE_LOST: "lease_losses",
        DistributedEventType.LEASE_RELEASED: "releases",
        DistributedEventType.TAKEOVER: "takeovers",
        DistributedEventType.ADMISSION_REJECTED: "admissions_rejected",
        DistributedEventType.DRAIN_STARTED: "drains_started",
        DistributedEventType.DRAIN_COMPLETED: "drains_completed",
        DistributedEventType.DRAIN_TIMED_OUT: "drains_timed_out",
    }

    def __init__(self) -> None:
        self._counts = {name: 0 for name in DistributedMetrics.model_fields}

    async def emit(self, event: DistributedOperationEvent) -> None:
        key = self._mapping[event.type]
        self._counts[key] += 1

    def snapshot(self) -> DistributedMetrics:
        return DistributedMetrics.model_validate(self._counts)


class _Span(Protocol):
    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None: ...

    def set_attribute(self, name: str, value: Any) -> None: ...

    def end(self) -> None: ...


class _Tracer(Protocol):
    def start_span(self, name: str, *, attributes: dict[str, Any] | None = None) -> _Span: ...


class OpenTelemetryDistributedEventSink:
    """Map distributed lifecycle facts to optional OpenTelemetry spans."""

    def __init__(self, tracer: _Tracer | None = None) -> None:
        if tracer is None:
            try:
                trace = importlib.import_module("opentelemetry.trace")
            except ImportError as exc:
                raise RuntimeError("Install pyagentskit[opentelemetry] or inject a tracer") from exc
            tracer = trace.get_tracer("pyagentskit.distributed")
        self.tracer = tracer
        self._spans: dict[tuple[str, str], _Span] = {}

    @staticmethod
    def _attributes(event: DistributedOperationEvent) -> dict[str, Any]:
        attributes: dict[str, Any] = {
            "pyagentskit.distributed.event_type": event.type.value,
            "pyagentskit.worker.owner_id": event.owner_id,
        }
        for key, value in {
            "pyagentskit.run_id": event.run_id,
            "pyagentskit.lease.resource_id": event.resource_id,
            "pyagentskit.tenant_id": event.tenant_id,
            "pyagentskit.lease.fencing_token": event.fencing_token,
            "pyagentskit.lease.revision": event.lease_revision,
        }.items():
            if value is not None:
                attributes[key] = str(value) if isinstance(value, UUID) else value
        return attributes

    async def emit(self, event: DistributedOperationEvent) -> None:
        resource_id = event.resource_id or "worker"
        key = (event.owner_id, resource_id)
        attributes = self._attributes(event)
        if event.type is DistributedEventType.LEASE_ACQUIRED:
            self._spans[key] = self.tracer.start_span(
                "pyagentskit.distributed.run", attributes=attributes
            )
        span = self._spans.get(key)
        if span is None:
            return
        span.add_event(event.type.value, attributes=attributes)
        if event.type in {
            DistributedEventType.LEASE_LOST,
            DistributedEventType.LEASE_RELEASED,
        }:
            span.set_attribute("pyagentskit.distributed.terminal", event.type.value)
            span.end()
            self._spans.pop(key, None)


class DistributedWorkerState(StrEnum):
    """Admission lifecycle of one worker incarnation."""

    ACCEPTING = "accepting"
    DRAINING = "draining"
    STOPPED = "stopped"


class DistributedWorkerHealth(ContractModel):
    """Payload-safe readiness snapshot for an application health endpoint."""

    owner_id: NonEmptyString
    state: DistributedWorkerState
    ready: bool
    active_runs: int = Field(ge=0)
    max_active_runs: int = Field(gt=0)
    coordination_ready: bool
    reason: NonEmptyString | None = None


class FencingToken(ContractModel):
    """Typed authority passed to a tool and atomically checked by a protected store."""

    resource_id: NonEmptyString
    owner_id: NonEmptyString
    tenant_id: NonEmptyString | None = None
    value: int = Field(ge=1)
    lease_id: NonEmptyString


@runtime_checkable
class FencedOperationStore(Protocol):
    """Reference port for resources that atomically fence a business write.

    Implementations must compare ``fencing_token.value`` and apply the operation
    in one transaction.  A separate check followed by an unfenced write is unsafe.
    """

    def apply_fenced(
        self,
        operation_id: str,
        payload: Any,
        *,
        fencing_token: FencingToken,
    ) -> Awaitable[Any]: ...


class DistributedExecutionPolicy(ContractModel):
    """Finite lease and heartbeat bounds for one distributed durable operation."""

    lease_ttl_seconds: float = Field(default=30.0, gt=0)
    renewal_interval_seconds: float = Field(default=10.0, gt=0)
    max_renewals: int = Field(default=360, gt=0)
    resource_prefix: NonEmptyString = "durable-run"

    @model_validator(mode="after")
    def validate_heartbeat_bounds(self) -> DistributedExecutionPolicy:
        values = (self.lease_ttl_seconds, self.renewal_interval_seconds)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("lease timings must be finite")
        if self.renewal_interval_seconds >= self.lease_ttl_seconds:
            raise ValueError("renewal interval must be shorter than lease TTL")
        return self


def resource_id_for_run(run_id: UUID, *, prefix: str = "durable-run") -> str:
    """Return the stable coordination resource for a durable run."""

    if not prefix.strip():
        raise ValueError("resource prefix cannot be blank")
    return f"{prefix}:{run_id}"


def fencing_token_from_context(context: RunContext[Any]) -> FencingToken:
    """Read the current distributed authority injected into a tool context."""

    document = context.metadata.get("distributed_execution")
    if not isinstance(document, dict):
        raise LeaseLostError("No distributed execution authority is present")
    try:
        return FencingToken.model_validate(document)
    except (TypeError, ValueError) as exc:
        raise LeaseLostError("Distributed execution authority is invalid") from exc


class _LeaseGuard:
    def __init__(self, store: LeaseStore, lease: Lease) -> None:
        self.store = store
        self.lease = lease
        self.failure: LeaseLostError | None = None
        self.renewals = 0
        self._lock = asyncio.Lock()

    def token(self) -> FencingToken:
        lease = self.lease
        return FencingToken(
            resource_id=lease.resource_id,
            owner_id=lease.owner_id,
            tenant_id=lease.tenant_id,
            value=lease.fencing_token,
            lease_id=lease.lease_id,
        )

    def inject(self, context: RunContext[Any]) -> None:
        token = self.token()
        context.metadata["fencing_token"] = token.value
        context.metadata["distributed_execution"] = token.model_dump(mode="json")

    async def assert_current(self, context: RunContext[Any]) -> None:
        async with self._lock:
            if self.failure is not None:
                raise self.failure
            try:
                await self.store.assert_current(self.lease)
            except PersistenceError as exc:
                self.failure = LeaseLostError("Durable-run lease is no longer current")
                raise self.failure from exc
            self.inject(context)

    async def renew(self, policy: DistributedExecutionPolicy) -> Lease:
        async with self._lock:
            if self.failure is not None:
                raise self.failure
            if self.renewals >= policy.max_renewals:
                self.failure = LeaseRenewalLimitError(
                    "Finite durable-run lease renewal budget was exhausted"
                )
                raise self.failure
            try:
                self.lease = await self.store.renew(
                    self.lease, ttl_seconds=policy.lease_ttl_seconds
                )
            except PersistenceError as exc:
                self.failure = LeaseLostError("Durable-run lease renewal failed")
                raise self.failure from exc
            self.renewals += 1
            return self.lease


_ACTIVE_LEASE_GUARD: ContextVar[_LeaseGuard | None] = ContextVar(
    "pyagentskit_active_lease_guard", default=None
)


class _FencingToolPolicy(ToolExecutionPolicy):
    async def before_execute(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        *,
        context: RunContext[Any],
    ) -> None:
        del call, definition
        guard = _ACTIVE_LEASE_GUARD.get()
        if guard is not None:
            await guard.assert_current(context)

    async def after_execute(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        result: ToolResult,
        *,
        context: RunContext[Any],
    ) -> ToolResult:
        del call, definition
        guard = _ACTIVE_LEASE_GUARD.get()
        if guard is not None:
            await guard.assert_current(context)
        return result


class DistributedDurableRunner:
    """Coordinate a :class:`DurableRunner` with one renewable fenced lease.

    Lease acquisition is single-shot.  Provider, model, or business-effect retries
    are never inferred from lease loss.  Another worker may take over only after
    expiry/release and must follow the durable effect-reconciliation rules.
    """

    def __init__(
        self,
        durable_runner: DurableRunner,
        lease_store: LeaseStore,
        *,
        owner_id: str,
        policy: DistributedExecutionPolicy | None = None,
        event_sinks: Iterable[DistributedEventSink] = (),
    ) -> None:
        if not owner_id.strip():
            raise ValueError("owner_id cannot be blank")
        self.durable_runner = durable_runner
        self.lease_store = lease_store
        self.owner_id = owner_id
        self.policy = policy or DistributedExecutionPolicy()
        self.event_sinks = tuple(event_sinks)
        self._install_fencing_policy()

    async def _emit(
        self,
        event_type: DistributedEventType,
        *,
        run_id: UUID | None = None,
        resource_id: str | None = None,
        tenant_id: str | None = None,
        lease: Lease | None = None,
        active_runs: int | None = None,
        reason: str | None = None,
    ) -> None:
        if not self.event_sinks:
            return
        event = DistributedOperationEvent(
            type=event_type,
            owner_id=self.owner_id,
            run_id=run_id,
            resource_id=resource_id,
            tenant_id=tenant_id,
            fencing_token=None if lease is None else lease.fencing_token,
            lease_revision=None if lease is None else lease.revision,
            active_runs=active_runs,
            reason=reason,
        )
        for sink in self.event_sinks:
            with suppress(Exception):
                await sink.emit(event)

    def _install_fencing_policy(self) -> None:
        registry = self.durable_runner.runner.tools
        executor = registry.executor
        if any(isinstance(item, _FencingToolPolicy) for item in executor.policies):
            return
        fenced_executor = ToolExecutor(
            policies=(_FencingToolPolicy(), *executor.policies),
            event_sinks=executor.event_sinks,
        )
        self.durable_runner.runner.tools = ToolRegistry(
            (registry.get(name) for name in registry.names()), executor=fenced_executor
        )

    async def _heartbeat(
        self,
        guard: _LeaseGuard,
        stop: asyncio.Event,
        *,
        run_id: UUID,
    ) -> LeaseLostError | None:
        while not stop.is_set():
            try:
                await asyncio.wait_for(stop.wait(), timeout=self.policy.renewal_interval_seconds)
                return None
            except TimeoutError:
                try:
                    renewed = await guard.renew(self.policy)
                    await self._emit(
                        DistributedEventType.LEASE_RENEWED,
                        run_id=run_id,
                        resource_id=renewed.resource_id,
                        tenant_id=renewed.tenant_id,
                        lease=renewed,
                    )
                except LeaseLostError as exc:
                    return exc
        return None

    async def _run_under_lease(
        self,
        operation: Callable[[], Awaitable[ResultT]],
        *,
        run_id: UUID,
        tenant_id: str | None,
        context: RunContext[Any] | None = None,
    ) -> ResultT:
        resource_id = resource_id_for_run(run_id, prefix=self.policy.resource_prefix)
        await self._emit(
            DistributedEventType.LEASE_ACQUIRE_STARTED,
            run_id=run_id,
            resource_id=resource_id,
            tenant_id=tenant_id,
        )
        try:
            lease = await self.lease_store.acquire(
                resource_id,
                owner_id=self.owner_id,
                ttl_seconds=self.policy.lease_ttl_seconds,
                tenant_id=tenant_id,
            )
        except (LeaseConflictError, LeaseNotFoundError):
            await self._emit(
                DistributedEventType.LEASE_CONFLICT,
                run_id=run_id,
                resource_id=resource_id,
                tenant_id=tenant_id,
                reason="lease_conflict",
            )
            raise
        await self._emit(
            DistributedEventType.LEASE_ACQUIRED,
            run_id=run_id,
            resource_id=resource_id,
            tenant_id=tenant_id,
            lease=lease,
        )
        if lease.fencing_token > 1:
            await self._emit(
                DistributedEventType.TAKEOVER,
                run_id=run_id,
                resource_id=resource_id,
                tenant_id=tenant_id,
                lease=lease,
            )
        guard = _LeaseGuard(self.lease_store, lease)
        if context is not None:
            guard.inject(context)
        context_token: Token[_LeaseGuard | None] = _ACTIVE_LEASE_GUARD.set(guard)
        stop = asyncio.Event()
        operation_task: asyncio.Future[Any] = asyncio.ensure_future(operation())
        heartbeat_task: asyncio.Future[Any] = asyncio.create_task(
            self._heartbeat(guard, stop, run_id=run_id)
        )
        loss_emitted = False
        try:
            done, _ = await asyncio.wait(
                {operation_task, heartbeat_task}, return_when=asyncio.FIRST_COMPLETED
            )
            if heartbeat_task in done:
                heartbeat_failure = heartbeat_task.result()
                if heartbeat_failure is not None:
                    await self._emit(
                        DistributedEventType.LEASE_LOST,
                        run_id=run_id,
                        resource_id=resource_id,
                        tenant_id=tenant_id,
                        lease=guard.lease,
                        reason=type(heartbeat_failure).__name__,
                    )
                    loss_emitted = True
                    operation_task.cancel()
                    with suppress(asyncio.CancelledError):
                        await operation_task
                    raise heartbeat_failure
            result = cast(ResultT, await operation_task)
            if guard.failure is not None:
                await self._emit(
                    DistributedEventType.LEASE_LOST,
                    run_id=run_id,
                    resource_id=resource_id,
                    tenant_id=tenant_id,
                    lease=guard.lease,
                    reason=type(guard.failure).__name__,
                )
                loss_emitted = True
                raise guard.failure
            return result
        except asyncio.CancelledError:
            operation_task.cancel()
            with suppress(asyncio.CancelledError):
                await operation_task
            raise
        finally:
            stop.set()
            if not heartbeat_task.done():
                await heartbeat_task
            _ACTIVE_LEASE_GUARD.reset(context_token)
            if guard.failure is None:
                try:
                    await self.lease_store.release(guard.lease)
                    await self._emit(
                        DistributedEventType.LEASE_RELEASED,
                        run_id=run_id,
                        resource_id=resource_id,
                        tenant_id=tenant_id,
                        lease=guard.lease,
                    )
                except PersistenceError as exc:
                    await self._emit(
                        DistributedEventType.LEASE_LOST,
                        run_id=run_id,
                        resource_id=resource_id,
                        tenant_id=tenant_id,
                        lease=guard.lease,
                        reason=f"release_error:{type(exc).__name__}",
                    )
            elif not loss_emitted:
                await self._emit(
                    DistributedEventType.LEASE_LOST,
                    run_id=run_id,
                    resource_id=resource_id,
                    tenant_id=tenant_id,
                    lease=guard.lease,
                    reason=type(guard.failure).__name__,
                )

    @staticmethod
    def _distributed_context(context: RunContext[Any]) -> RunContext[Any]:
        return replace(context, metadata=dict(context.metadata))

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
        """Acquire ownership, run, renew within bounds, then release ownership."""

        distributed_context = self._distributed_context(context)
        tenant_id = distributed_context.metadata.get("tenant_id")
        return await self._run_under_lease(
            lambda: self.durable_runner.run(
                agent,
                input,
                context=distributed_context,
                limits=limits,
                output_type=output_type,
                recover_tool_errors=recover_tool_errors,
                context_budget=context_budget,
            ),
            run_id=distributed_context.run_id,
            tenant_id=tenant_id,
            context=distributed_context,
        )

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
        """Take ownership and resume only through DurableRunner recovery semantics."""

        return await self._run_under_lease(
            lambda: self.durable_runner.resume(
                agent,
                run_id,
                deps=deps,
                tenant_id=tenant_id,
                limits=limits,
                output_type=output_type,
            ),
            run_id=run_id,
            tenant_id=tenant_id,
        )

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
        """Acquire a fresh lease before resuming a previously paused approval."""

        distributed_context = self._distributed_context(context)
        tenant_id = distributed_context.metadata.get("tenant_id")
        return await self._run_under_lease(
            lambda: self.durable_runner.resume_approval(
                agent,
                approval_id,
                context=distributed_context,
                limits=limits,
                output_type=output_type,
                recover_tool_errors=recover_tool_errors,
                context_budget=context_budget,
            ),
            run_id=distributed_context.run_id,
            tenant_id=tenant_id,
            context=distributed_context,
        )


class DistributedWorkerController:
    """Bound admissions and drain one distributed worker without cancelling effects.

    A timed-out drain deliberately leaves the worker in ``DRAINING``.  The host may
    then keep waiting or terminate the process; this controller never converts a
    shutdown deadline into an implicit tool or run retry.
    """

    def __init__(
        self,
        runner: DistributedDurableRunner,
        *,
        max_active_runs: int = 32,
        readiness_probe: Callable[[], Awaitable[bool]] | None = None,
    ) -> None:
        if max_active_runs <= 0:
            raise ValueError("max_active_runs must be positive")
        self.runner = runner
        self.max_active_runs = max_active_runs
        self.readiness_probe = readiness_probe
        self._state = DistributedWorkerState.ACCEPTING
        self._active: set[UUID] = set()
        self._lock = asyncio.Lock()
        self._drained = asyncio.Event()
        self._drained.set()

    @property
    def state(self) -> DistributedWorkerState:
        return self._state

    async def _admit(self, run_id: UUID, tenant_id: str | None) -> None:
        reason: str | None = None
        async with self._lock:
            if self._state is not DistributedWorkerState.ACCEPTING:
                reason = f"worker_{self._state.value}"
            elif run_id in self._active:
                reason = "run_already_active"
            elif len(self._active) >= self.max_active_runs:
                reason = "capacity_exhausted"
            else:
                self._active.add(run_id)
                self._drained.clear()
        if reason is not None:
            await self.runner._emit(
                DistributedEventType.ADMISSION_REJECTED,
                run_id=run_id,
                resource_id=resource_id_for_run(run_id, prefix=self.runner.policy.resource_prefix),
                tenant_id=tenant_id,
                active_runs=len(self._active),
                reason=reason,
            )
            raise DistributedAdmissionError(f"Distributed admission rejected: {reason}")

    async def _complete(self, run_id: UUID) -> None:
        completed_drain = False
        async with self._lock:
            self._active.discard(run_id)
            if not self._active:
                self._drained.set()
                if self._state is DistributedWorkerState.DRAINING:
                    self._state = DistributedWorkerState.STOPPED
                    completed_drain = True
        if completed_drain:
            await self.runner._emit(
                DistributedEventType.DRAIN_COMPLETED,
                active_runs=0,
                reason="all_active_runs_completed",
            )

    async def _execute(
        self,
        operation: Callable[[], Awaitable[ResultT]],
        *,
        run_id: UUID,
        tenant_id: str | None,
    ) -> ResultT:
        await self._admit(run_id, tenant_id)
        try:
            return await operation()
        finally:
            await self._complete(run_id)

    async def health(self) -> DistributedWorkerHealth:
        """Return readiness without acquiring a lease or touching business state."""

        coordination_ready = True
        reason: str | None = None
        if self.readiness_probe is not None:
            try:
                coordination_ready = bool(await self.readiness_probe())
                if not coordination_ready:
                    reason = "coordination_probe_failed"
            except Exception as exc:
                coordination_ready = False
                reason = f"coordination_probe_error:{type(exc).__name__}"
        async with self._lock:
            state = self._state
            active_runs = len(self._active)
        ready = (
            state is DistributedWorkerState.ACCEPTING
            and coordination_ready
            and active_runs < self.max_active_runs
        )
        if reason is None and state is not DistributedWorkerState.ACCEPTING:
            reason = f"worker_{state.value}"
        elif reason is None and active_runs >= self.max_active_runs:
            reason = "capacity_exhausted"
        return DistributedWorkerHealth(
            owner_id=self.runner.owner_id,
            state=state,
            ready=ready,
            active_runs=active_runs,
            max_active_runs=self.max_active_runs,
            coordination_ready=coordination_ready,
            reason=reason,
        )

    async def drain(self, *, timeout_seconds: float) -> bool:
        """Stop admissions and wait within a bound; never cancel an active effect."""

        if not math.isfinite(timeout_seconds) or timeout_seconds <= 0:
            raise ValueError("drain timeout must be finite and positive")
        async with self._lock:
            if self._state is DistributedWorkerState.STOPPED:
                return True
            self._state = DistributedWorkerState.DRAINING
            active_runs = len(self._active)
            if active_runs == 0:
                self._state = DistributedWorkerState.STOPPED
                self._drained.set()
        await self.runner._emit(
            DistributedEventType.DRAIN_STARTED,
            active_runs=active_runs,
            reason="shutdown_requested",
        )
        if active_runs == 0:
            await self.runner._emit(
                DistributedEventType.DRAIN_COMPLETED,
                active_runs=0,
                reason="no_active_runs",
            )
            return True
        try:
            await asyncio.wait_for(self._drained.wait(), timeout=timeout_seconds)
        except TimeoutError:
            await self.runner._emit(
                DistributedEventType.DRAIN_TIMED_OUT,
                active_runs=len(self._active),
                reason="grace_period_exhausted",
            )
            return False
        return True

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
        tenant_id = context.metadata.get("tenant_id")
        return await self._execute(
            lambda: self.runner.run(
                agent,
                input,
                context=context,
                limits=limits,
                output_type=output_type,
                recover_tool_errors=recover_tool_errors,
                context_budget=context_budget,
            ),
            run_id=context.run_id,
            tenant_id=tenant_id,
        )

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
        return await self._execute(
            lambda: self.runner.resume(
                agent,
                run_id,
                deps=deps,
                tenant_id=tenant_id,
                limits=limits,
                output_type=output_type,
            ),
            run_id=run_id,
            tenant_id=tenant_id,
        )

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
        tenant_id = context.metadata.get("tenant_id")
        return await self._execute(
            lambda: self.runner.resume_approval(
                agent,
                approval_id,
                context=context,
                limits=limits,
                output_type=output_type,
                recover_tool_errors=recover_tool_errors,
                context_budget=context_budget,
            ),
            run_id=context.run_id,
            tenant_id=tenant_id,
        )
