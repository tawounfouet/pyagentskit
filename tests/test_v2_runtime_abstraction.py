from __future__ import annotations

import unittest
from collections.abc import AsyncIterator

from pyagentskit import AgentDefinition, ModelRef, Runner
from pyagentskit.adapters import NativeRuntimeAdapter, NativeRuntimeEngine
from pyagentskit.application import (
    CapabilityNegotiator,
    InMemoryRuntimeRegistry,
    RuntimeCandidate,
)
from pyagentskit.domain import (
    CapabilityNegotiationError,
    Effect,
    RuntimeBinding,
    RuntimeCancelRequest,
    RuntimeCancelStatus,
    RuntimeCapability,
    RuntimeDescriptor,
    RuntimeEventType,
    RuntimeHandle,
    RuntimeIdentity,
    RuntimeInvocation,
    RuntimeQualificationLevel,
    RuntimeRequirements,
    RuntimeResumeRequest,
    RuntimeStartRequest,
    RuntimeStatus,
    SideEffectControlLevel,
)
from pyagentskit.domain.errors import (
    RuntimeAdapterError,
    RuntimeCapabilityError,
    RuntimeRegistrationError,
)
from pyagentskit.messages import TextContent
from pyagentskit.models import FinishReason, ModelResponse
from pyagentskit.testing import FakeModel


class StubRuntime:
    def __init__(self, descriptor: RuntimeDescriptor) -> None:
        self.descriptor = descriptor

    async def start(self, request: object) -> RuntimeHandle:
        return RuntimeHandle(self.descriptor.runtime_id, "stub")

    async def resume(self, request: object) -> RuntimeHandle:
        return RuntimeHandle(self.descriptor.runtime_id, "stub")

    async def cancel(self, request: object) -> object:
        return object()

    async def inspect(self, handle: RuntimeHandle) -> RuntimeStatus:
        return RuntimeStatus.COMPLETED

    async def events(self, handle: RuntimeHandle) -> AsyncIterator[object]:
        if False:
            yield object()

    async def checkpoint(self, handle: RuntimeHandle) -> None:
        return None

    async def close(self) -> None:
        return None


def descriptor(
    runtime_id: str,
    *,
    capabilities: frozenset[RuntimeCapability],
    control: SideEffectControlLevel = SideEffectControlLevel.BOUNDED,
    qualification: RuntimeQualificationLevel = RuntimeQualificationLevel.L1,
) -> RuntimeDescriptor:
    return RuntimeDescriptor(
        runtime_id=runtime_id,
        display_name=runtime_id,
        runtime_family="test",
        adapter_version="1.0.0",
        contract_version="2",
        capabilities=capabilities,
        side_effect_control_level=control,
        qualification_level=qualification,
    )


class RuntimeNegotiationTests(unittest.TestCase):
    def test_runtime_value_objects_validate_contract_metadata(self) -> None:
        identity = RuntimeIdentity("pyagentskit", "native", contract_major=2)
        self.assertEqual(identity.canonical, "pyagentskit/native@2")

        with self.assertRaises(ValueError):
            RuntimeIdentity("", "native")
        with self.assertRaises(ValueError):
            RuntimeDescriptor(
                runtime_id="bad id",
                display_name="Bad",
                runtime_family="test",
                adapter_version="1",
                contract_version="2",
            )
        with self.assertRaises(ValueError):
            RuntimeRequirements(
                required_capabilities=frozenset({RuntimeCapability.START}),
                forbidden_capabilities=frozenset({RuntimeCapability.START}),
            )

    def test_required_capabilities_and_control_level_are_hard_constraints(self) -> None:
        bounded = StubRuntime(
            descriptor(
                "test/bounded@1",
                capabilities=frozenset({RuntimeCapability.START, RuntimeCapability.STATUS}),
                control=SideEffectControlLevel.BOUNDED,
            )
        )
        full = StubRuntime(
            descriptor(
                "test/full@1",
                capabilities=frozenset({RuntimeCapability.START, RuntimeCapability.STATUS}),
                control=SideEffectControlLevel.FULL,
            )
        )
        result = CapabilityNegotiator().negotiate(
            RuntimeRequirements(
                required_capabilities=frozenset({RuntimeCapability.START}),
                minimum_side_effect_control=SideEffectControlLevel.FULL,
            ),
            (
                RuntimeCandidate(bounded.descriptor, bounded),
                RuntimeCandidate(full.descriptor, full),
            ),
        )

        self.assertEqual(result.selected_runtime_id, "test/full@1")
        self.assertEqual(result.rejected[0].runtime_id, "test/bounded@1")
        self.assertIn(
            "side_effect_control_too_weak",
            {reason.value for reason in result.rejected[0].reasons},
        )

    def test_no_compatible_candidate_fails_without_fallback(self) -> None:
        runtime = StubRuntime(
            descriptor(
                "test/bounded@1",
                capabilities=frozenset({RuntimeCapability.START}),
            )
        )

        with self.assertRaises(CapabilityNegotiationError):
            CapabilityNegotiator().negotiate(
                RuntimeRequirements(
                    required_capabilities=frozenset({RuntimeCapability.START}),
                    minimum_side_effect_control=SideEffectControlLevel.FULL,
                ),
                (RuntimeCandidate(runtime.descriptor, runtime),),
            )

    def test_exact_runtime_request_does_not_fallback(self) -> None:
        native = StubRuntime(
            descriptor(
                "test/native@1",
                capabilities=frozenset({RuntimeCapability.START}),
                control=SideEffectControlLevel.FULL,
            )
        )
        alternative = StubRuntime(
            descriptor(
                "test/alternative@1",
                capabilities=frozenset({RuntimeCapability.START}),
                control=SideEffectControlLevel.FULL,
            )
        )

        with self.assertRaises(CapabilityNegotiationError):
            CapabilityNegotiator().negotiate(
                RuntimeRequirements(runtime_id="test/missing@1"),
                (
                    RuntimeCandidate(native.descriptor, native),
                    RuntimeCandidate(alternative.descriptor, alternative),
                ),
            )

    def test_selection_is_deterministic_and_explainable(self) -> None:
        candidates = tuple(
            RuntimeCandidate(
                runtime.descriptor,
                runtime,
            )
            for runtime in (
                StubRuntime(
                    descriptor(
                        "test/z@1",
                        capabilities=frozenset({RuntimeCapability.START}),
                    )
                ),
                StubRuntime(
                    descriptor(
                        "test/a@1",
                        capabilities=frozenset({RuntimeCapability.START}),
                    )
                ),
            )
        )
        requirements = RuntimeRequirements(
            required_capabilities=frozenset({RuntimeCapability.START})
        )
        first = CapabilityNegotiator().negotiate(requirements, candidates)
        second = CapabilityNegotiator().negotiate(requirements, tuple(reversed(candidates)))

        self.assertEqual(first.selected_runtime_id, second.selected_runtime_id)
        self.assertIn(first.selected_runtime_id or "", first.reason)

    def test_registry_rejects_collisions_and_lists_canonically(self) -> None:
        registry = InMemoryRuntimeRegistry()
        first = StubRuntime(
            descriptor("test/z@1", capabilities=frozenset({RuntimeCapability.START}))
        )
        second = StubRuntime(
            descriptor("test/a@1", capabilities=frozenset({RuntimeCapability.START}))
        )
        registry.register(first)
        with self.assertRaises(RuntimeRegistrationError):
            registry.register(first)
        registry.register(second)

        self.assertEqual([item.runtime_id for item in registry.list()], ["test/a@1", "test/z@1"])
        self.assertEqual(len(registry.find(RuntimeRequirements())), 2)
        self.assertIs(registry.get("test/a@1"), second)
        self.assertIs(registry.unregister("test/z@1"), first)
        with self.assertRaises(RuntimeRegistrationError):
            registry.get("test/z@1")


class RuntimeContractTests(unittest.IsolatedAsyncioTestCase):
    async def test_native_adapter_uses_the_common_contract(self) -> None:
        response = ModelResponse(
            id="response-1",
            model="fake",
            content=(TextContent(text="done"),),
            finish_reason=FinishReason.STOP,
        )
        agent = AgentDefinition(
            id="native.test",
            version="1.0.0",
            instructions="Return a short answer.",
            model=ModelRef(provider="fake", name="fake"),
        )
        adapter = NativeRuntimeAdapter(NativeRuntimeEngine(Runner(FakeModel([response])), agent))

        self.assertIsInstance(adapter.descriptor.capabilities, frozenset)
        self.assertNotIn(RuntimeCapability.RESUME, adapter.descriptor.capabilities)
        self.assertNotIn(RuntimeCapability.NATIVE_CHECKPOINT, adapter.descriptor.capabilities)
        self.assertEqual(adapter.descriptor.side_effect_control_level, SideEffectControlLevel.FULL)

        request = RuntimeStartRequest(input="hello")
        handle = await adapter.start(request)
        events = [event async for event in adapter.events(handle)]

        self.assertEqual(await adapter.inspect(handle), RuntimeStatus.COMPLETED)
        self.assertEqual(events[0].event_type, RuntimeEventType.RUNTIME_STARTED)
        self.assertEqual(events[-1].event_type, RuntimeEventType.RUNTIME_COMPLETED)
        self.assertIsNone(await adapter.checkpoint(handle))
        cancelled = await adapter.cancel(
            RuntimeCancelRequest(
                run_id=request.run_id,
                runtime_handle=handle,
                reason="test cleanup",
                requested_by="test",
            )
        )
        self.assertEqual(cancelled.status, RuntimeCancelStatus.ALREADY_TERMINAL)
        with self.assertRaises(RuntimeCapabilityError):
            await adapter.resume(
                # The adapter must reject unsupported resume instead of restarting silently.
                RuntimeResumeRequest(
                    run_id=RuntimeStartRequest(input="resume").run_id,
                    runtime_handle=handle,
                )
            )
        await adapter.close()
        with self.assertRaises(RuntimeAdapterError):
            await adapter.start(RuntimeStartRequest(input="closed"))

    async def test_native_adapter_normalizes_engine_failures(self) -> None:
        agent = AgentDefinition(
            id="native.failure",
            version="1.0.0",
            instructions="Return a short answer.",
            model=ModelRef(provider="fake", name="fake"),
        )
        adapter = NativeRuntimeAdapter(
            NativeRuntimeEngine(Runner(FakeModel([RuntimeError("boom")])), agent)
        )
        handle = await adapter.start(RuntimeStartRequest(input="fail"))
        events = [event async for event in adapter.events(handle)]

        self.assertEqual(await adapter.inspect(handle), RuntimeStatus.FAILED)
        self.assertEqual(events[-1].event_type, RuntimeEventType.RUNTIME_FAILED)
        with self.assertRaises(RuntimeAdapterError):
            await adapter.inspect(RuntimeHandle(adapter.descriptor.runtime_id, "unknown"))
        await adapter.close()

    async def test_binding_snapshot_remains_distinct_from_invocation(self) -> None:
        effect = Effect()
        binding = RuntimeBinding(
            runtime_id="pyagentskit/native@2",
            runtime_family="native",
            selected_capabilities=frozenset({RuntimeCapability.START}),
            side_effect_control_level=SideEffectControlLevel.FULL,
            qualification_level=RuntimeQualificationLevel.L1,
            selection_reason="required capabilities satisfied",
        )
        invocation = RuntimeInvocation(
            run_id=effect.run_id,
            binding_id=binding.id,
            input="hello",
            runtime_id=binding.resolved_runtime_id,
        )

        self.assertEqual(binding.resolved_runtime_id, "pyagentskit/native@2")
        self.assertEqual(binding.resolved_capabilities, frozenset({RuntimeCapability.START}))
        self.assertEqual(invocation.status, RuntimeStatus.CREATED)
        self.assertNotEqual(binding.id, invocation.id)


if __name__ == "__main__":
    unittest.main()
