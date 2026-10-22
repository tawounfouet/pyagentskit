"""First-party runtime adapter over the stable V1 Runner."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Mapping
from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from ..agents import AgentDefinition
from ..application.runtime import AgentRuntimeAdapter
from ..domain import (
    NormalizedRuntimeEvent,
    RuntimeCancelRequest,
    RuntimeCancelResult,
    RuntimeCancelStatus,
    RuntimeCapability,
    RuntimeCheckpoint,
    RuntimeDescriptor,
    RuntimeEventType,
    RuntimeHandle,
    RuntimeQualificationLevel,
    RuntimeResumeRequest,
    RuntimeStartRequest,
    RuntimeStatus,
    SideEffectControlLevel,
)
from ..domain.errors import RuntimeAdapterError, RuntimeCapabilityError
from ..runs import RunContext, RunResult, RunStatus
from ..runtime import Runner


class NativeRuntimeEngine:
    """Internal engine boundary retaining the V1 model/tool loop."""

    def __init__(self, runner: Runner, agent: AgentDefinition) -> None:
        self.runner = runner
        self.agent = agent

    async def start(self, request: RuntimeStartRequest) -> RunResult[Any]:
        metadata = dict(request.metadata)
        metadata["v2_run_id"] = str(request.run_id)
        if request.correlation_context:
            metadata["correlation_context"] = dict(request.correlation_context)
        context = RunContext(
            agent_id=str(self.agent.id),
            deps=None,
            session_id=request.session_id,
            metadata=metadata,
        )
        return await self.runner.run(self.agent, request.input, context=context)


@dataclass(slots=True)
class _NativeExecution:
    handle: RuntimeHandle
    correlation_context: Mapping[str, str]
    status: RuntimeStatus = RuntimeStatus.STARTING
    events: asyncio.Queue[NormalizedRuntimeEvent | None] = field(default_factory=asyncio.Queue)
    task: asyncio.Task[None] | None = None


class NativeRuntimeAdapter(AgentRuntimeAdapter):
    """Expose the V1 Runner through the same port as external runtimes."""

    def __init__(
        self,
        engine: NativeRuntimeEngine,
        *,
        adapter_version: str = "2.0.0a3",
        runtime_version: str | None = None,
        qualification_level: RuntimeQualificationLevel = RuntimeQualificationLevel.L1,
    ) -> None:
        self.engine = engine
        self._closed = False
        self._executions: dict[str, _NativeExecution] = {}
        self._descriptor = RuntimeDescriptor(
            runtime_id="pyagentskit/native@2",
            display_name="PyAgentsKit Native Runtime",
            runtime_family="native",
            adapter_version=adapter_version,
            runtime_version=runtime_version,
            contract_version="2",
            capabilities=frozenset(
                {
                    RuntimeCapability.START,
                    RuntimeCapability.STATUS,
                    RuntimeCapability.CANCEL,
                    RuntimeCapability.EVENT_STREAM,
                }
            ),
            side_effect_control_level=SideEffectControlLevel.BOUNDED,
            qualification_level=qualification_level,
        )

    @property
    def descriptor(self) -> RuntimeDescriptor:
        return self._descriptor

    async def start(self, request: RuntimeStartRequest) -> RuntimeHandle:
        if self._closed:
            raise RuntimeAdapterError("native runtime adapter is closed")
        execution_id = uuid4().hex
        handle = RuntimeHandle(
            adapter_name=self.descriptor.runtime_id,
            external_id=execution_id,
            metadata={"run_id": str(request.run_id)},
        )
        execution = _NativeExecution(handle, request.correlation_context)
        self._executions[execution_id] = execution
        execution.task = asyncio.create_task(self._execute(execution, request))
        return handle

    async def resume(self, request: RuntimeResumeRequest) -> RuntimeHandle:
        raise RuntimeCapabilityError(
            f"{self.descriptor.runtime_id} does not declare {RuntimeCapability.RESUME.value}"
        )

    async def cancel(self, request: RuntimeCancelRequest) -> RuntimeCancelResult:
        execution = self._get_execution(request.runtime_handle)
        if execution.status.is_terminal:
            return RuntimeCancelResult(RuntimeCancelStatus.ALREADY_TERMINAL, execution.handle)
        if execution.task is None:
            return RuntimeCancelResult(RuntimeCancelStatus.FAILED, execution.handle)
        execution.task.cancel()
        await execution.task
        return RuntimeCancelResult(RuntimeCancelStatus.CANCELLED, execution.handle)

    async def inspect(self, handle: RuntimeHandle) -> RuntimeStatus:
        return self._get_execution(handle).status

    async def events(self, handle: RuntimeHandle) -> AsyncIterator[NormalizedRuntimeEvent]:
        execution = self._get_execution(handle)
        while True:
            event = await execution.events.get()
            if event is None:
                return
            yield event

    async def checkpoint(self, handle: RuntimeHandle) -> RuntimeCheckpoint | None:
        self._get_execution(handle)
        return None

    async def close(self) -> None:
        self._closed = True
        tasks = [execution.task for execution in self._executions.values() if execution.task]
        for task in tasks:
            if task is not None and not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _execute(self, execution: _NativeExecution, request: RuntimeStartRequest) -> None:
        execution.status = RuntimeStatus.RUNNING
        await self._emit(
            execution, RuntimeEventType.RUNTIME_STARTED, {"run_id": str(request.run_id)}
        )
        try:
            result = await self.engine.start(request)
        except asyncio.CancelledError:
            execution.status = RuntimeStatus.CANCELLED
            await self._emit(execution, RuntimeEventType.RUNTIME_CANCELLED, {})
        except Exception as exc:
            execution.status = RuntimeStatus.FAILED
            await self._emit(
                execution,
                RuntimeEventType.RUNTIME_FAILED,
                {"error_type": type(exc).__name__},
            )
        else:
            execution.status = self._status_from_result(result)
            event_type = {
                RuntimeStatus.COMPLETED: RuntimeEventType.RUNTIME_COMPLETED,
                RuntimeStatus.WAITING: RuntimeEventType.RUNTIME_WAITING,
            }.get(execution.status, RuntimeEventType.RUNTIME_FAILED)
            await self._emit(execution, event_type, {"status": execution.status.value})
        finally:
            await execution.events.put(None)

    async def _emit(
        self,
        execution: _NativeExecution,
        event_type: RuntimeEventType,
        payload: Mapping[str, Any],
    ) -> None:
        await execution.events.put(
            NormalizedRuntimeEvent(
                event_type=event_type,
                runtime_handle=execution.handle,
                correlation_context=execution.correlation_context,
                payload=payload,
            )
        )

    def _get_execution(self, handle: RuntimeHandle) -> _NativeExecution:
        if handle.adapter_name != self.descriptor.runtime_id:
            raise RuntimeAdapterError("runtime handle belongs to another adapter")
        try:
            return self._executions[handle.external_id]
        except KeyError as exc:
            raise RuntimeAdapterError("runtime handle is unknown") from exc

    @staticmethod
    def _status_from_result(result: RunResult[Any]) -> RuntimeStatus:
        if result.status is RunStatus.COMPLETED:
            return RuntimeStatus.COMPLETED
        if result.status is RunStatus.WAITING_APPROVAL:
            return RuntimeStatus.WAITING
        if result.status is RunStatus.CANCELLED:
            return RuntimeStatus.CANCELLED
        return RuntimeStatus.FAILED


__all__ = ["NativeRuntimeAdapter", "NativeRuntimeEngine"]
