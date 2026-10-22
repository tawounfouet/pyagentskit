from __future__ import annotations

from pyagentskit.application import AgentRuntimeAdapter
from pyagentskit.domain import (
    RuntimeCancelRequest,
    RuntimeCancelStatus,
    RuntimeCapability,
    RuntimeHandle,
    RuntimeResumeRequest,
    RuntimeStartRequest,
)
from pyagentskit.domain.errors import (
    RuntimeAdapterError,
    RuntimeCapabilityError,
)


class RuntimeAdapterContractMixin:
    """Common behavioral contract executed by every V2 runtime adapter."""

    def make_adapter(self) -> AgentRuntimeAdapter:
        raise NotImplementedError

    async def test_contract_start_status_and_events(self) -> None:
        adapter = self.make_adapter()
        request = RuntimeStartRequest(
            input="contract",
            correlation_context={"trace_id": "trace-1"},
        )
        handle = await adapter.start(request)
        events = [event async for event in adapter.events(handle)]

        self.assertEqual(handle.adapter_name, adapter.descriptor.runtime_id)
        self.assertTrue(events)
        self.assertEqual(events[0].correlation_context.get("trace_id"), "trace-1")
        self.assertTrue((await adapter.inspect(handle)).is_terminal)
        await adapter.close()

    async def test_contract_cancel_checkpoint_and_unsupported_resume(self) -> None:
        adapter = self.make_adapter()
        request = RuntimeStartRequest(input="contract")
        handle = await adapter.start(request)
        _ = [event async for event in adapter.events(handle)]

        cancelled = await adapter.cancel(
            RuntimeCancelRequest(
                run_id=request.run_id,
                runtime_handle=handle,
                reason="contract cleanup",
                requested_by="contract-suite",
            )
        )
        self.assertEqual(cancelled.status, RuntimeCancelStatus.ALREADY_TERMINAL)

        if RuntimeCapability.NATIVE_CHECKPOINT not in adapter.descriptor.capabilities:
            self.assertIsNone(await adapter.checkpoint(handle))

        if RuntimeCapability.RESUME not in adapter.descriptor.capabilities:
            with self.assertRaises(RuntimeCapabilityError):
                await adapter.resume(
                    RuntimeResumeRequest(
                        run_id=request.run_id,
                        runtime_handle=handle,
                    )
                )
        await adapter.close()

    async def test_contract_unknown_handle_fails_closed(self) -> None:
        adapter = self.make_adapter()
        unknown = RuntimeHandle(adapter.descriptor.runtime_id, "unknown")

        with self.assertRaises(RuntimeAdapterError):
            await adapter.inspect(unknown)
        await adapter.close()

    async def test_contract_close_rejects_new_execution(self) -> None:
        adapter = self.make_adapter()
        await adapter.close()

        with self.assertRaises(RuntimeAdapterError):
            await adapter.start(RuntimeStartRequest(input="closed"))
