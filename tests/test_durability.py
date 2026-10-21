from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime
from pathlib import Path

from pyagentskit import (
    AgentDefinition,
    ApprovalDecision,
    CheckpointKind,
    DurableRunner,
    EffectResolution,
    EffectStatus,
    FinishReason,
    MemoryApprovalStore,
    MemoryRunStore,
    MemorySessionStore,
    ModelRef,
    ModelResponse,
    PersistenceError,
    RunConflictError,
    RunContext,
    RunNotFoundError,
    RunStatus,
    Session,
    SQLiteRunStore,
    TextContent,
    ToolCall,
    ToolRegistry,
    ToolResult,
    ToolResultStatus,
    ToolRisk,
    migrate_checkpoint_document,
    tool,
)
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


def agent() -> AgentDefinition:
    return AgentDefinition(
        id="durable.agent",
        version="1.0.0",
        instructions="Complete the durable operation",
        model=ModelRef(provider="fake", name="test"),
        tools=("write_record",),
    )


def tool_response(call_id: str = "call-1") -> ModelResponse:
    return ModelResponse(
        id="tool-response",
        model="test",
        tool_calls=(ToolCall(id=call_id, name="write_record", arguments={"value": 7}),),
        finish_reason=FinishReason.TOOL_CALLS,
    )


def final_response() -> ModelResponse:
    return ModelResponse(
        id="final-response",
        model="test",
        content=(TextContent(text="done"),),
        finish_reason=FinishReason.STOP,
    )


async def session_store(
    session_id: str = "session", *, tenant_id: str | None = None
) -> MemorySessionStore:
    store = MemorySessionStore()
    now = datetime.now(UTC)
    await store.create(
        Session(
            session_id=session_id,
            agent_id="durable.agent",
            tenant_id=tenant_id,
            created_at=now,
            updated_at=now,
        )
    )
    return store


class DurableRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_completed_run_has_checkpoints_effect_and_replay(self) -> None:
        calls: list[int] = []

        @tool(risk=ToolRisk.EXTERNAL_WRITE, idempotent=True)
        def write_record(value: int) -> int:
            """Write one record."""

            calls.append(value)
            return value

        sessions = await session_store()
        model = FakeModel([tool_response(), final_response()])
        store = MemoryRunStore()
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry([write_record]), session_store=sessions), store
        )
        context = RunContext(agent_id="durable.agent", deps=None, session_id="session")

        result = await durable.run(agent(), "write seven", context=context)

        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(calls, [7])
        checkpoints = await store.list_checkpoints(context.run_id)
        self.assertEqual(
            [item.kind for item in checkpoints],
            [
                CheckpointKind.RUN_STARTED,
                CheckpointKind.TOOL_STARTED,
                CheckpointKind.TOOL_COMPLETED,
                CheckpointKind.RUN_COMPLETED,
            ],
        )
        effects = await store.list_effects(context.run_id)
        self.assertEqual(len(effects), 1)
        self.assertEqual(effects[0].status, EffectStatus.COMPLETED)
        journal = await durable.replay(context.run_id)
        self.assertGreaterEqual(len(journal), 7)
        self.assertEqual(calls, [7], "analytical replay must not invoke the tool")
        with self.assertRaises(RunConflictError):
            await durable.resume(agent(), context.run_id)

    async def test_unknown_effect_requires_explicit_committed_resolution(self) -> None:
        calls: list[int] = []

        @tool(risk=ToolRisk.EXTERNAL_WRITE)
        def write_record(value: int) -> int:
            """Write and lose the acknowledgement."""

            calls.append(value)
            raise RuntimeError("acknowledgement lost")

        sessions = await session_store()
        model = FakeModel([tool_response(), final_response()])
        store = MemoryRunStore()
        durable = DurableRunner(
            Runner(model, tools=ToolRegistry([write_record]), session_store=sessions), store
        )
        context = RunContext(agent_id="durable.agent", deps=None, session_id="session")

        result = await durable.run(agent(), "write seven", context=context)
        self.assertEqual(result.status, RunStatus.UNKNOWN_EFFECT)
        self.assertEqual(calls, [7])
        effect = (await store.list_effects(context.run_id))[0]
        blocked = await durable.resume(agent(), context.run_id)
        self.assertEqual(blocked.status, RunStatus.UNKNOWN_EFFECT)
        self.assertEqual(calls, [7])

        observed = ToolResult(
            call_id=effect.call.id,
            tool_name=effect.call.name,
            status=ToolResultStatus.SUCCEEDED,
            content={"value": 7, "reconciled": True},
        )
        await store.resolve_effect(
            effect.effect_id,
            EffectResolution.COMMITTED,
            expected_revision=effect.revision,
            result=observed,
        )
        resumed = await durable.resume(agent(), context.run_id)
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(resumed.output, "done")
        self.assertEqual(calls, [7], "committed effects must not be replayed")

    async def test_not_applied_resolution_allows_one_controlled_retry(self) -> None:
        attempts = 0

        @tool(risk=ToolRisk.EXTERNAL_WRITE, idempotent=True)
        def write_record(value: int) -> int:
            """Fail before commit once."""

            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise RuntimeError("failed before commit")
            return value

        sessions = await session_store()
        store = MemoryRunStore()
        durable = DurableRunner(
            Runner(
                FakeModel([tool_response(), final_response()]),
                tools=ToolRegistry([write_record]),
                session_store=sessions,
            ),
            store,
        )
        context = RunContext(agent_id="durable.agent", deps=None, session_id="session")
        first = await durable.run(agent(), "write", context=context)
        self.assertEqual(first.status, RunStatus.UNKNOWN_EFFECT)
        effect = (await store.list_effects(context.run_id))[0]
        await store.resolve_effect(
            effect.effect_id,
            EffectResolution.NOT_APPLIED,
            expected_revision=effect.revision,
        )

        resumed = await durable.resume(agent(), context.run_id)

        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(attempts, 2)
        current = await store.get_effect(effect.effect_id)
        self.assertEqual(current.status, EffectStatus.COMPLETED)
        self.assertEqual(current.recovery_count, 1)

    async def test_agent_version_change_is_rejected(self) -> None:
        @tool
        def write_record(value: int) -> int:
            """Return the input."""

            raise RuntimeError(value)

        sessions = await session_store()
        store = MemoryRunStore()
        durable = DurableRunner(
            Runner(
                FakeModel([tool_response()]),
                tools=ToolRegistry([write_record]),
                session_store=sessions,
            ),
            store,
        )
        context = RunContext(agent_id="durable.agent", deps=None, session_id="session")
        await durable.run(agent(), "write", context=context)
        changed = agent().model_copy(update={"version": "2.0.0"})
        with self.assertRaises(RunConflictError):
            await durable.resume(changed, context.run_id)

    async def test_secret_patterns_are_redacted_from_effect_state(self) -> None:
        secret = "sk-example-secret-123456789"

        @tool
        def write_record(value: str) -> str:
            """Echo a value."""

            return value

        response = ModelResponse(
            id="tool-response",
            model="test",
            tool_calls=(
                ToolCall(id="secret-call", name="write_record", arguments={"value": secret}),
            ),
            finish_reason=FinishReason.TOOL_CALLS,
        )
        sessions = await session_store()
        store = MemoryRunStore()
        durable = DurableRunner(
            Runner(
                FakeModel([response, final_response()]),
                tools=ToolRegistry([write_record]),
                session_store=sessions,
            ),
            store,
        )
        context = RunContext(agent_id="durable.agent", deps=None, session_id="session")
        result = await durable.run(agent(), "process credential", context=context)
        self.assertEqual(result.status, RunStatus.COMPLETED)
        serialized = json.dumps(
            [item.model_dump(mode="json") for item in await store.list_effects(context.run_id)]
        )
        self.assertNotIn(secret, serialized)
        self.assertIn("[REDACTED]", serialized)

    async def test_pending_approval_keeps_durable_effect_boundary(self) -> None:
        calls: list[int] = []

        @tool(risk=ToolRisk.EXTERNAL_WRITE, requires_approval=True)
        def write_record(value: int) -> int:
            """Write after approval."""

            calls.append(value)
            return value

        sessions = await session_store()
        approvals = MemoryApprovalStore()
        store = MemoryRunStore()
        durable = DurableRunner(
            Runner(
                FakeModel([tool_response(), final_response()]),
                tools=ToolRegistry([write_record]),
                session_store=sessions,
                approval_store=approvals,
            ),
            store,
        )
        context = RunContext(agent_id="durable.agent", deps=None, session_id="session")
        waiting = await durable.run(agent(), "write", context=context)
        self.assertEqual(waiting.status, RunStatus.WAITING_APPROVAL)
        approval_id = waiting.metadata["approval_id"]
        approval = await approvals.resolve(
            approval_id,
            ApprovalDecision.APPROVE,
            actor_id="reviewer",
            expected_revision=0,
        )
        resumed = await durable.resume_approval(agent(), approval.approval_id, context=context)
        self.assertEqual(resumed.status, RunStatus.COMPLETED)
        self.assertEqual(calls, [7])
        self.assertEqual(
            (await store.list_effects(context.run_id))[0].status,
            EffectStatus.COMPLETED,
        )


class CheckpointMigrationTests(unittest.TestCase):
    def test_synthetic_v0_checkpoint_migrates_to_v1(self) -> None:
        now = datetime.now(UTC)
        context = RunContext(agent_id="durable.agent", deps=None, session_id="session")
        document = {
            "checkpoint_id": "legacy-checkpoint",
            "run_id": str(context.run_id),
            "trace_id": str(context.trace_id),
            "agent_id": "durable.agent",
            "agent_version": "1.0.0",
            "session_id": "session",
            "sequence": 0,
            "kind": "run_started",
            "status": "running",
            "timestamp": now.isoformat(),
        }
        migrated = migrate_checkpoint_document(document)
        self.assertEqual(migrated.schema_version, 1)
        self.assertEqual(migrated.created_at, now)

    def test_future_checkpoint_schema_is_rejected(self) -> None:
        with self.assertRaises(PersistenceError):
            migrate_checkpoint_document({"schema_version": 99})


class SQLiteRunStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_state_survives_reopen_and_tenant_scope(self) -> None:
        calls: list[int] = []

        @tool(idempotent=True)
        def write_record(value: int) -> int:
            """Write one record."""

            calls.append(value)
            return value

        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "runs.db"
            sessions = await session_store(tenant_id="tenant-a")
            first_store = SQLiteRunStore(path)
            durable = DurableRunner(
                Runner(
                    FakeModel([tool_response(), final_response()]),
                    tools=ToolRegistry([write_record]),
                    session_store=sessions,
                ),
                first_store,
            )
            context = RunContext(
                agent_id="durable.agent",
                deps=None,
                session_id="session",
                metadata={"tenant_id": "tenant-a"},
            )
            result = await durable.run(agent(), "write", context=context)
            self.assertEqual(result.status, RunStatus.COMPLETED)
            first_store.close()

            reopened = SQLiteRunStore(path)
            latest = await reopened.latest_checkpoint(context.run_id, tenant_id="tenant-a")
            self.assertEqual(latest.kind, CheckpointKind.RUN_COMPLETED)
            self.assertEqual(
                (await reopened.list_effects(context.run_id, tenant_id="tenant-a"))[0].status,
                EffectStatus.COMPLETED,
            )
            with self.assertRaises(RunNotFoundError):
                await reopened.latest_checkpoint(context.run_id, tenant_id="tenant-b")
            reopened.close()


if __name__ == "__main__":
    unittest.main()
