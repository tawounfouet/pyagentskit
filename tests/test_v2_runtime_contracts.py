from __future__ import annotations

import unittest
from collections.abc import AsyncIterator
from uuid import uuid4

from pyagentskit import AgentDefinition, ModelRef, Runner
from pyagentskit.adapters import NativeRuntimeAdapter, NativeRuntimeEngine
from pyagentskit.domain import (
    NormalizedRuntimeEvent,
    RuntimeCancelRequest,
    RuntimeCancelResult,
    RuntimeCancelStatus,
    RuntimeCapability,
    RuntimeDescriptor,
    RuntimeEventType,
    RuntimeHandle,
    RuntimeQualificationLevel,
    RuntimeResumeRequest,
    RuntimeStartRequest,
    RuntimeStatus,
    SideEffectControlLevel,
)
from pyagentskit.domain.errors import RuntimeAdapterError, RuntimeCapabilityError
from pyagentskit.messages import TextContent
from pyagentskit.models import FinishReason, ModelResponse
from pyagentskit.testing import FakeModel
from tests.contracts.runtime_adapter import RuntimeAdapterContractMixin


class FakeExternalRuntimeAdapter:
    """Brand-neutral fake proving the common contract is reusable."""

    def __init__(self) -> None:
        self._closed = False
        self._correlations: dict[str, dict[str, str]] = {}
        self.descriptor = RuntimeDescriptor(
            runtime_id="external/fake@1",
            display_name="External Fake Runtime",
            runtime_family="external-fake",
            adapter_version="1.0.0",
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
            qualification_level=RuntimeQualificationLevel.L1,
        )

    async def start(self, request: RuntimeStartRequest) -> RuntimeHandle:
        if self._closed:
            raise RuntimeAdapterError("fake runtime adapter is closed")
        external_id = uuid4().hex
        self._correlations[external_id] = dict(request.correlation_context)
        return RuntimeHandle(self.descriptor.runtime_id, external_id)

    async def resume(self, request: RuntimeResumeRequest) -> RuntimeHandle:
        raise RuntimeCapabilityError("fake runtime does not declare resume")

    async def cancel(self, request: RuntimeCancelRequest) -> RuntimeCancelResult:
        self._require_known(request.runtime_handle)
        return RuntimeCancelResult(RuntimeCancelStatus.ALREADY_TERMINAL, request.runtime_handle)

    async def inspect(self, handle: RuntimeHandle) -> RuntimeStatus:
        self._require_known(handle)
        return RuntimeStatus.COMPLETED

    async def events(self, handle: RuntimeHandle) -> AsyncIterator[NormalizedRuntimeEvent]:
        self._require_known(handle)
        correlation = self._correlations[handle.external_id]
        yield NormalizedRuntimeEvent(
            event_type=RuntimeEventType.RUNTIME_STARTED,
            runtime_handle=handle,
            correlation_context=correlation,
        )
        yield NormalizedRuntimeEvent(
            event_type=RuntimeEventType.RUNTIME_COMPLETED,
            runtime_handle=handle,
            correlation_context=correlation,
        )

    async def checkpoint(self, handle: RuntimeHandle) -> None:
        self._require_known(handle)
        return None

    async def close(self) -> None:
        self._closed = True

    def _require_known(self, handle: RuntimeHandle) -> None:
        if handle.adapter_name != self.descriptor.runtime_id:
            raise RuntimeAdapterError("runtime handle belongs to another adapter")
        if handle.external_id not in self._correlations:
            raise RuntimeAdapterError("runtime handle is unknown")


class NativeRuntimeAdapterContractTests(
    RuntimeAdapterContractMixin,
    unittest.IsolatedAsyncioTestCase,
):
    def make_adapter(self) -> NativeRuntimeAdapter:
        response = ModelResponse(
            id="response-contract",
            model="fake",
            content=(TextContent(text="done"),),
            finish_reason=FinishReason.STOP,
        )
        agent = AgentDefinition(
            id="native.contract",
            version="1.0.0",
            instructions="Return a short answer.",
            model=ModelRef(provider="fake", name="fake"),
        )
        return NativeRuntimeAdapter(NativeRuntimeEngine(Runner(FakeModel([response])), agent))


class ExternalRuntimeAdapterContractTests(
    RuntimeAdapterContractMixin,
    unittest.IsolatedAsyncioTestCase,
):
    def make_adapter(self) -> FakeExternalRuntimeAdapter:
        return FakeExternalRuntimeAdapter()


if __name__ == "__main__":
    unittest.main()
