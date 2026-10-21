from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from pyagentskit import (
    AgentDefinition,
    ApprovalDecision,
    EffectStatus,
    FinishReason,
    MemoryApprovalStore,
    MemoryRunStore,
    MemorySessionStore,
    ModelRef,
    ModelResponse,
    RunContext,
    RunStatus,
    Session,
    TextContent,
    ToolCall,
    ToolRegistry,
    ToolRisk,
    tool,
)
from pyagentskit.coordination import LeaseConflictError, LeaseNotFoundError, MemoryLeaseStore
from pyagentskit.distributed import (
    DistributedAdmissionError,
    DistributedDurableRunner,
    DistributedEventType,
    DistributedExecutionPolicy,
    DistributedMetricsSink,
    DistributedWorkerController,
    DistributedWorkerState,
    FencedOperationStore,
    FencingToken,
    JsonLinesDistributedEventSink,
    LeaseLostError,
    LeaseRenewalLimitError,
    MemoryDistributedEventSink,
    OpenTelemetryDistributedEventSink,
    fencing_token_from_context,
    resource_id_for_run,
)
from pyagentskit.durability import DurableRunner
from pyagentskit.exceptions import PersistenceError
from pyagentskit.models import ModelCapabilities, ModelRequest
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel

NOW = datetime(2026, 9, 9, 12, tzinfo=UTC)


class MutableClock:
    def __init__(self) -> None:
        self.now = NOW

    def __call__(self) -> datetime:
        return self.now


class GateModel:
    def __init__(self, response: ModelResponse) -> None:
        self.response = response
        self.entered = asyncio.Event()
        self.proceed = asyncio.Event()
        self.requests: list[ModelRequest] = []

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(tool_calling=True, structured_output=True)

    async def generate(self, request: ModelRequest, *, context: RunContext[Any]) -> ModelResponse:
        del context
        self.requests.append(request)
        self.entered.set()
        await self.proceed.wait()
        return self.response


class ProtectedStore:
    def __init__(self) -> None:
        self.highest: dict[tuple[str | None, str], int] = {}
        self.applied: list[tuple[str, Any, int]] = []

    async def apply_fenced(
        self,
        operation_id: str,
        payload: Any,
        *,
        fencing_token: FencingToken,
    ) -> Any:
        key = (fencing_token.tenant_id, fencing_token.resource_id)
        highest = self.highest.get(key, 0)
        if fencing_token.value < highest:
            raise LeaseConflictError("Protected store rejected a stale fencing token")
        self.highest[key] = fencing_token.value
        if not any(item[0] == operation_id for item in self.applied):
            self.applied.append((operation_id, payload, fencing_token.value))
        return payload


class FailingRenewLeaseStore(MemoryLeaseStore):
    async def renew(self, lease: Any, *, ttl_seconds: float) -> Any:
        del lease, ttl_seconds
        raise PersistenceError("simulated coordination outage")


class FailingReleaseLeaseStore(MemoryLeaseStore):
    async def release(self, lease: Any) -> None:
        del lease
        raise PersistenceError("simulated release outage")


class FakeSpan:
    def __init__(self) -> None:
        self.events: list[str] = []
        self.attributes: dict[str, Any] = {}
        self.ended = False

    def add_event(self, name: str, attributes: dict[str, Any] | None = None) -> None:
        self.events.append(name)
        self.attributes.update(attributes or {})

    def set_attribute(self, name: str, value: Any) -> None:
        self.attributes[name] = value

    def end(self) -> None:
        self.ended = True


class FakeTracer:
    def __init__(self) -> None:
        self.spans: list[FakeSpan] = []

    def start_span(self, name: str, *, attributes: dict[str, Any] | None = None) -> FakeSpan:
        self.name = name
        span = FakeSpan()
        span.attributes.update(attributes or {})
        self.spans.append(span)
        return span


def definition(*, approval: bool = False) -> AgentDefinition:
    return AgentDefinition(
        id="distributed.agent",
        version="1.0.0",
        instructions="Perform one durable operation",
        model=ModelRef(provider="fake", name="test"),
        tools=("write_record",) if not approval else ("approved_write",),
    )


def tool_response(name: str = "write_record", call_id: str = "call-1") -> ModelResponse:
    return ModelResponse(
        id="tool-response",
        model="test",
        tool_calls=(ToolCall(id=call_id, name=name, arguments={"value": 7}),),
        finish_reason=FinishReason.TOOL_CALLS,
    )


def final_response() -> ModelResponse:
    return ModelResponse(
        id="final-response",
        model="test",
        content=(TextContent(text="done"),),
        finish_reason=FinishReason.STOP,
    )


async def session_store() -> MemorySessionStore:
    store = MemorySessionStore()
    await store.create(
        Session(
            session_id="session",
            agent_id="distributed.agent",
            tenant_id="tenant-a",
            created_at=NOW,
            updated_at=NOW,
        )
    )
    return store


def policy(**updates: Any) -> DistributedExecutionPolicy:
    values = {
        "lease_ttl_seconds": 30.0,
        "renewal_interval_seconds": 20.0,
        "max_renewals": 3,
    }
    values.update(updates)
    return DistributedExecutionPolicy(**values)


class DistributedDurableExecutionTests(unittest.IsolatedAsyncioTestCase):
    async def test_propagates_fencing_token_and_releases_after_success(self) -> None:
        protected = ProtectedStore()
        observed: list[FencingToken] = []

        @tool(risk=ToolRisk.EXTERNAL_WRITE)
        async def write_record(value: int, context: RunContext[None]) -> int:
            """Apply a fenced external write."""

            token = fencing_token_from_context(context)
            observed.append(token)
            return await protected.apply_fenced("business-1", value, fencing_token=token)

        leases = MemoryLeaseStore()
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(
                FakeModel([tool_response(), final_response()]),
                tools=ToolRegistry([write_record]),
                session_store=await session_store(),
            ),
            MemoryRunStore(),
        )
        distributed = DistributedDurableRunner(
            durable, leases, owner_id="worker-a", policy=policy()
        )

        result = await distributed.run(definition(), "write", context=context)

        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0].owner_id, "worker-a")
        self.assertEqual(observed[0].tenant_id, "tenant-a")
        self.assertEqual(protected.applied, [("business-1", 7, 1)])
        self.assertNotIn("fencing_token", context.metadata, "caller context must not be mutated")
        with self.assertRaises(LeaseNotFoundError):
            await leases.get(resource_id_for_run(context.run_id), tenant_id="tenant-a")

    async def test_expired_worker_stops_before_planning_a_new_effect(self) -> None:
        calls: list[int] = []

        @tool(risk=ToolRisk.EXTERNAL_WRITE)
        def write_record(value: int) -> int:
            """Record a value only if the policy allows it."""

            calls.append(value)
            return value

        clock = MutableClock()
        leases = MemoryLeaseStore(clock=clock)
        model = GateModel(tool_response())
        run_store = MemoryRunStore()
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry([write_record]), session_store=await session_store()),
            run_store,
        )
        distributed = DistributedDurableRunner(
            durable, leases, owner_id="worker-a", policy=policy()
        )

        task = asyncio.create_task(distributed.run(definition(), "write", context=context))
        await model.entered.wait()
        clock.now += timedelta(seconds=31)
        replacement = await leases.acquire(
            resource_id_for_run(context.run_id),
            owner_id="worker-b",
            ttl_seconds=30,
            tenant_id="tenant-a",
        )
        model.proceed.set()

        with self.assertRaises(LeaseLostError):
            await task
        self.assertEqual(replacement.fencing_token, 2)
        self.assertEqual(calls, [])
        self.assertEqual(await run_store.list_effects(context.run_id, tenant_id="tenant-a"), ())

    async def test_renewal_budget_is_bounded_and_cancels_work(self) -> None:
        model = GateModel(final_response())
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry(), session_store=await session_store()),
            MemoryRunStore(),
        )
        distributed = DistributedDurableRunner(
            durable,
            MemoryLeaseStore(),
            owner_id="worker-a",
            policy=policy(
                lease_ttl_seconds=0.1,
                renewal_interval_seconds=0.01,
                max_renewals=1,
            ),
        )

        with self.assertRaises(LeaseRenewalLimitError):
            await distributed.run(
                definition().model_copy(update={"tools": ()}), "wait", context=context
            )

    async def test_crash_expiry_takeover_never_replays_ambiguous_effect(self) -> None:
        entered = asyncio.Event()
        proceed = asyncio.Event()
        calls: list[int] = []

        @tool(risk=ToolRisk.EXTERNAL_WRITE)
        async def write_record(value: int, context: RunContext[None]) -> int:
            """Simulate an externally committed effect before acknowledgement."""

            fencing_token_from_context(context)
            calls.append(value)
            entered.set()
            await proceed.wait()
            return value

        clock = MutableClock()
        leases = MemoryLeaseStore(clock=clock)
        run_store = MemoryRunStore()
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(
                FakeModel([tool_response(), final_response()]),
                tools=ToolRegistry([write_record]),
                session_store=await session_store(),
            ),
            run_store,
        )
        first = DistributedDurableRunner(durable, leases, owner_id="worker-a", policy=policy())
        task = asyncio.create_task(first.run(definition(), "write", context=context))
        await entered.wait()
        clock.now += timedelta(seconds=31)
        takeover_lease = await leases.acquire(
            resource_id_for_run(context.run_id),
            owner_id="worker-b",
            ttl_seconds=30,
            tenant_id="tenant-a",
        )
        proceed.set()

        with self.assertRaises(LeaseLostError):
            await task
        effects = await run_store.list_effects(context.run_id, tenant_id="tenant-a")
        self.assertEqual(effects[0].status, EffectStatus.UNKNOWN)
        second = DistributedDurableRunner(durable, leases, owner_id="worker-b", policy=policy())
        blocked = await second.resume(definition(), context.run_id, tenant_id="tenant-a")
        self.assertEqual(blocked.status, RunStatus.UNKNOWN_EFFECT)
        self.assertEqual(takeover_lease.fencing_token, 2)
        self.assertEqual(calls, [7], "ambiguous business effects must never replay implicitly")

    async def test_failed_run_can_be_taken_over_by_another_worker(self) -> None:
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        model = FakeModel([RuntimeError("worker crashed before an effect"), final_response()])
        leases = MemoryLeaseStore()
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry(), session_store=await session_store()),
            MemoryRunStore(),
        )
        worker_a = DistributedDurableRunner(durable, leases, owner_id="worker-a", policy=policy())
        no_tools = definition().model_copy(update={"tools": ()})
        failed = await worker_a.run(no_tools, "start", context=context)
        self.assertEqual(failed.status, RunStatus.FAILED)

        worker_b = DistributedDurableRunner(durable, leases, owner_id="worker-b", policy=policy())
        resumed = await worker_b.resume(no_tools, context.run_id, tenant_id="tenant-a")
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(resumed.output, "done")

    async def test_pause_releases_lease_and_approval_resumes_under_new_token(self) -> None:
        observed: list[FencingToken] = []

        @tool(risk=ToolRisk.EXTERNAL_WRITE, requires_approval=True)
        def approved_write(value: int, context: RunContext[None]) -> int:
            """Apply an approved write under distributed authority."""

            observed.append(fencing_token_from_context(context))
            return value

        approvals = MemoryApprovalStore()
        leases = MemoryLeaseStore()
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(
                FakeModel([tool_response("approved_write"), final_response()]),
                tools=ToolRegistry([approved_write]),
                session_store=await session_store(),
                approval_store=approvals,
            ),
            MemoryRunStore(),
        )
        worker_a = DistributedDurableRunner(durable, leases, owner_id="worker-a", policy=policy())
        waiting = await worker_a.run(definition(approval=True), "write", context=context)
        self.assertEqual(waiting.status, RunStatus.WAITING_APPROVAL)
        with self.assertRaises(LeaseNotFoundError):
            await leases.get(resource_id_for_run(context.run_id), tenant_id="tenant-a")
        approval_id = waiting.metadata["approval_id"]
        await approvals.resolve(
            approval_id,
            ApprovalDecision.APPROVE,
            actor_id="reviewer",
            tenant_id="tenant-a",
        )

        worker_b = DistributedDurableRunner(durable, leases, owner_id="worker-b", policy=policy())
        resumed = await worker_b.resume_approval(
            definition(approval=True), approval_id, context=context
        )
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(len(observed), 1)
        self.assertEqual(observed[0].owner_id, "worker-b")
        self.assertEqual(observed[0].value, 2)

    async def test_protected_store_rejects_split_brain_stale_token(self) -> None:
        protected = ProtectedStore()
        stale = FencingToken(
            resource_id="durable-run:one",
            owner_id="worker-a",
            tenant_id="tenant-a",
            value=1,
            lease_id="lease-a",
        )
        current = stale.model_copy(update={"owner_id": "worker-b", "value": 2, "lease_id": "b"})
        self.assertIsInstance(protected, FencedOperationStore)
        await protected.apply_fenced("operation-new", 2, fencing_token=current)
        with self.assertRaises(LeaseConflictError):
            await protected.apply_fenced("operation-stale", 1, fencing_token=stale)
        self.assertEqual(protected.applied, [("operation-new", 2, 2)])

    def test_policy_rejects_unbounded_or_unsafe_timings(self) -> None:
        for values in (
            {"lease_ttl_seconds": float("inf")},
            {"renewal_interval_seconds": float("inf")},
            {"lease_ttl_seconds": 10.0, "renewal_interval_seconds": 10.0},
        ):
            with self.assertRaises(ValueError):
                DistributedExecutionPolicy(**values)

    async def test_operational_events_metrics_and_telemetry_are_payload_free(self) -> None:
        audit = MemoryDistributedEventSink()
        metrics = DistributedMetricsSink()
        tracer = FakeTracer()
        telemetry = OpenTelemetryDistributedEventSink(tracer)
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a", "secret": "must-not-escape"},
        )
        durable = DurableRunner(
            Runner(
                FakeModel([final_response()]),
                tools=ToolRegistry(),
                session_store=await session_store(),
            ),
            MemoryRunStore(),
        )
        distributed = DistributedDurableRunner(
            durable,
            MemoryLeaseStore(),
            owner_id="worker-observed",
            policy=policy(),
            event_sinks=(audit, metrics, telemetry),
        )

        result = await distributed.run(
            definition().model_copy(update={"tools": ()}), "complete", context=context
        )

        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(
            [item.type for item in audit.events],
            [
                DistributedEventType.LEASE_ACQUIRE_STARTED,
                DistributedEventType.LEASE_ACQUIRED,
                DistributedEventType.LEASE_RELEASED,
            ],
        )
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.acquisition_attempts, 1)
        self.assertEqual(snapshot.acquisitions, 1)
        self.assertEqual(snapshot.releases, 1)
        serialized = "".join(item.model_dump_json() for item in audit.events)
        self.assertNotIn("must-not-escape", serialized)
        self.assertEqual(tracer.name, "pyagentskit.distributed.run")
        self.assertTrue(tracer.spans[0].ended)

    async def test_heartbeat_emits_renewal_and_database_outage_fails_closed(self) -> None:
        audit = MemoryDistributedEventSink()
        model = GateModel(final_response())
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry(), session_store=await session_store()),
            MemoryRunStore(),
        )
        distributed = DistributedDurableRunner(
            durable,
            FailingRenewLeaseStore(),
            owner_id="worker-outage",
            policy=policy(
                lease_ttl_seconds=0.1,
                renewal_interval_seconds=0.01,
                max_renewals=2,
            ),
            event_sinks=(audit,),
        )

        with self.assertRaises(LeaseLostError):
            await distributed.run(
                definition().model_copy(update={"tools": ()}), "wait", context=context
            )
        self.assertIn(DistributedEventType.LEASE_LOST, [item.type for item in audit.events])
        self.assertNotIn(DistributedEventType.LEASE_RELEASED, [item.type for item in audit.events])

    async def test_release_outage_never_turns_completed_effect_into_retry_signal(self) -> None:
        audit = MemoryDistributedEventSink()
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(
                FakeModel([final_response()]),
                tools=ToolRegistry(),
                session_store=await session_store(),
            ),
            MemoryRunStore(),
        )
        distributed = DistributedDurableRunner(
            durable,
            FailingReleaseLeaseStore(),
            owner_id="worker-release-outage",
            event_sinks=(audit,),
        )

        result = await distributed.run(
            definition().model_copy(update={"tools": ()}), "complete", context=context
        )

        self.assertEqual(result.status, RunStatus.COMPLETED)
        lost = [item for item in audit.events if item.type is DistributedEventType.LEASE_LOST]
        self.assertEqual(len(lost), 1)
        self.assertEqual(lost[0].reason, "release_error:PersistenceError")

    async def test_worker_drain_rejects_admission_and_waits_for_active_run(self) -> None:
        audit = MemoryDistributedEventSink()
        metrics = DistributedMetricsSink()
        model = GateModel(final_response())
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry(), session_store=await session_store()),
            MemoryRunStore(),
        )
        distributed = DistributedDurableRunner(
            durable,
            MemoryLeaseStore(),
            owner_id="worker-drain",
            policy=policy(),
            event_sinks=(audit, metrics),
        )
        controller = DistributedWorkerController(distributed, max_active_runs=1)
        no_tools = definition().model_copy(update={"tools": ()})
        active = asyncio.create_task(controller.run(no_tools, "wait", context=context))
        await model.entered.wait()
        health = await controller.health()
        self.assertFalse(health.ready)
        self.assertEqual(health.reason, "capacity_exhausted")
        drain = asyncio.create_task(controller.drain(timeout_seconds=1))
        await asyncio.sleep(0)
        rejected_context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="other-session",
            metadata={"tenant_id": "tenant-a"},
        )
        with self.assertRaises(DistributedAdmissionError):
            await controller.run(no_tools, "rejected", context=rejected_context)
        model.proceed.set()
        self.assertEqual((await active).status, RunStatus.COMPLETED)
        self.assertTrue(await drain)
        self.assertEqual(controller.state, DistributedWorkerState.STOPPED)
        stopped = await controller.health()
        self.assertFalse(stopped.ready)
        snapshot = metrics.snapshot()
        self.assertEqual(snapshot.admissions_rejected, 1)
        self.assertEqual(snapshot.drains_started, 1)
        self.assertEqual(snapshot.drains_completed, 1)

    async def test_drain_timeout_never_cancels_active_run(self) -> None:
        audit = MemoryDistributedEventSink()
        model = GateModel(final_response())
        context = RunContext(
            agent_id="distributed.agent",
            deps=None,
            session_id="session",
            metadata={"tenant_id": "tenant-a"},
        )
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry(), session_store=await session_store()),
            MemoryRunStore(),
        )
        controller = DistributedWorkerController(
            DistributedDurableRunner(
                durable,
                MemoryLeaseStore(),
                owner_id="worker-timeout",
                policy=policy(),
                event_sinks=(audit,),
            )
        )
        active = asyncio.create_task(
            controller.run(definition().model_copy(update={"tools": ()}), "wait", context=context)
        )
        await model.entered.wait()

        self.assertFalse(await controller.drain(timeout_seconds=0.01))
        self.assertFalse(active.done(), "drain timeout must not cancel an in-flight run")
        model.proceed.set()
        self.assertEqual((await active).status, RunStatus.COMPLETED)
        self.assertEqual(controller.state, DistributedWorkerState.STOPPED)
        self.assertIn(DistributedEventType.DRAIN_TIMED_OUT, [item.type for item in audit.events])

    async def test_readiness_probe_fails_closed_without_state_mutation(self) -> None:
        async def failed_probe() -> bool:
            raise PersistenceError("database unavailable")

        durable = DurableRunner(
            Runner(
                FakeModel([final_response()]),
                tools=ToolRegistry(),
                session_store=await session_store(),
            ),
            MemoryRunStore(),
        )
        controller = DistributedWorkerController(
            DistributedDurableRunner(durable, MemoryLeaseStore(), owner_id="worker-health"),
            readiness_probe=failed_probe,
        )

        health = await controller.health()

        self.assertFalse(health.ready)
        self.assertFalse(health.coordination_ready)
        self.assertEqual(health.reason, "coordination_probe_error:PersistenceError")
        self.assertEqual(controller.state, DistributedWorkerState.ACCEPTING)

    async def test_idle_worker_drains_immediately_and_validates_bound(self) -> None:
        audit = MemoryDistributedEventSink()
        durable = DurableRunner(
            Runner(
                FakeModel([final_response()]),
                tools=ToolRegistry(),
                session_store=await session_store(),
            ),
            MemoryRunStore(),
        )
        controller = DistributedWorkerController(
            DistributedDurableRunner(
                durable,
                MemoryLeaseStore(),
                owner_id="worker-idle",
                event_sinks=(audit,),
            )
        )
        self.assertTrue(await controller.drain(timeout_seconds=1))
        self.assertTrue(await controller.drain(timeout_seconds=1))
        self.assertEqual(controller.state, DistributedWorkerState.STOPPED)
        self.assertEqual(
            [event.type for event in audit.events],
            [DistributedEventType.DRAIN_STARTED, DistributedEventType.DRAIN_COMPLETED],
        )
        with self.assertRaises(ValueError):
            await DistributedWorkerController(
                DistributedDurableRunner(durable, MemoryLeaseStore(), owner_id="other")
            ).drain(timeout_seconds=float("inf"))

    async def test_json_lines_audit_is_append_only_and_validated(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            sink = JsonLinesDistributedEventSink(Path(temporary) / "audit" / "events.jsonl")
            durable = DurableRunner(
                Runner(
                    FakeModel([final_response()]),
                    tools=ToolRegistry(),
                    session_store=await session_store(),
                ),
                MemoryRunStore(),
            )
            context = RunContext(
                agent_id="distributed.agent",
                deps=None,
                session_id="session",
                metadata={"tenant_id": "tenant-a"},
            )
            runner = DistributedDurableRunner(
                durable,
                MemoryLeaseStore(),
                owner_id="worker-audit",
                event_sinks=(sink,),
            )

            await runner.run(
                definition().model_copy(update={"tools": ()}), "complete", context=context
            )

            events = await sink.read()
            self.assertEqual(len(events), 3)
            self.assertEqual(events[-1].type, DistributedEventType.LEASE_RELEASED)
            self.assertEqual(len(sink.path.read_text(encoding="utf-8").splitlines()), 3)


if __name__ == "__main__":
    unittest.main()
