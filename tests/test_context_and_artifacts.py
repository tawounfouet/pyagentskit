"""Context budgeting, artifact integrity and runtime session integration tests."""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from pyagentskit import (
    AgentDefinition,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactRetentionPolicy,
    ContextAction,
    ContextBudget,
    ContextBudgetError,
    EventType,
    FileSystemArtifactStore,
    FinishReason,
    FullContextPolicy,
    InMemoryMemoryStore,
    MemoryArtifactStore,
    MemoryContextSource,
    MemoryRecord,
    MemorySessionStore,
    Message,
    MessageRole,
    ModelRef,
    ModelResponse,
    PersistenceError,
    RunContext,
    Session,
    SessionStateManager,
    SummarizingContextPolicy,
    TextContent,
    ToolCall,
    ToolRegistry,
    WindowContextPolicy,
    tool,
)
from pyagentskit.observability import EventBus, MemoryEventSink
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel

NOW = datetime(2026, 9, 5, 12, tzinfo=UTC)


def response(text: str) -> ModelResponse:
    return ModelResponse(
        id="response",
        model="test",
        content=(TextContent(text=text),),
        finish_reason=FinishReason.STOP,
    )


def agent(*, tools: tuple[str, ...] = ()) -> AgentDefinition:
    return AgentDefinition(
        id="assistant",
        version="1.0.0",
        instructions="Help safely",
        model=ModelRef(provider="fake", name="test"),
        tools=tools,
    )


class ContextPolicyTests(unittest.IsolatedAsyncioTestCase):
    async def test_full_context_enforces_known_budget(self) -> None:
        messages = (Message.from_text(MessageRole.USER, "x" * 100),)
        with self.assertRaises(ContextBudgetError):
            await FullContextPolicy().select(
                messages, budget=ContextBudget(max_tokens=2, chars_per_token=1)
            )

    async def test_window_is_explainable_and_keeps_tool_exchange_atomic(self) -> None:
        call = ToolCall(id="call-1", name="lookup", arguments={})
        messages = (
            Message.from_text(MessageRole.SYSTEM, "system"),
            Message.from_text(MessageRole.USER, "old"),
            Message(role=MessageRole.ASSISTANT, tool_calls=(call,)),
            Message.from_text(MessageRole.TOOL, "result", name="lookup", tool_call_id="call-1"),
            Message.from_text(MessageRole.USER, "current"),
        )
        selected = await WindowContextPolicy(max_messages=4).select(
            messages, budget=ContextBudget()
        )
        self.assertEqual(selected.removed_message_count, 1)
        self.assertIn(messages[2], selected.messages)
        self.assertIn(messages[3], selected.messages)
        self.assertEqual(selected.decisions[1].action, ContextAction.DROP)

    async def test_summary_validation_and_success(self) -> None:
        messages = tuple(
            Message.from_text(MessageRole.USER, f"message-{index}") for index in range(4)
        )

        async def valid(removed):
            self.assertTrue(removed)
            return "Earlier preferences"

        selected = await SummarizingContextPolicy(valid, max_messages=2).select(
            messages, budget=ContextBudget(max_tokens=1_000)
        )
        self.assertEqual(selected.summarized_message_count, 2)
        self.assertTrue(selected.messages[0].metadata["context_summary"])

        async def invalid(removed):
            return " "

        with self.assertRaises(ContextBudgetError):
            await SummarizingContextPolicy(invalid, max_messages=1).select(
                messages, budget=ContextBudget()
            )

        async def too_large(removed):
            return "x" * 1_000

        with self.assertRaises(ContextBudgetError):
            await SummarizingContextPolicy(too_large, max_messages=1, max_summary_tokens=2).select(
                messages, budget=ContextBudget()
            )


class ArtifactStoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_memory_and_filesystem_contract(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            stores = [
                MemoryArtifactStore(clock=lambda: NOW),
                FileSystemArtifactStore(Path(directory) / "artifacts", clock=lambda: NOW),
            ]
            for store in stores:
                with self.subTest(store=type(store).__name__):
                    record = await store.put(
                        b"payload",
                        name="report.json",
                        media_type="application/json",
                        tenant_id="tenant-a",
                        session_id="session-a",
                        provenance={"tool": "report"},
                        artifact_id="artifact-1",
                    )
                    self.assertEqual(record.ref.size_bytes, 7)
                    self.assertTrue(record.ref.checksum.startswith("sha256:"))  # type: ignore[union-attr]
                    self.assertEqual(
                        (await store.get("artifact-1", tenant_id="tenant-a"))[1], b"payload"
                    )
                    with self.assertRaises(ArtifactNotFoundError):
                        await store.get("artifact-1", tenant_id="tenant-b")
                    self.assertEqual(
                        await store.delete_session("session-a", tenant_id="tenant-a"), 1
                    )
                    self.assertFalse(await store.delete("artifact-1", tenant_id="tenant-a"))

    async def test_filesystem_detects_corruption_and_rejects_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "artifacts"
            store = FileSystemArtifactStore(root, clock=lambda: NOW)
            record = await store.put(
                b"original",
                name="data.bin",
                media_type="application/octet-stream",
                tenant_id="tenant-a",
                artifact_id="safe-id",
            )
            blob = next(root.glob("*/*.blob"))
            blob.write_bytes(b"tampered")
            with self.assertRaises(ArtifactIntegrityError):
                await store.get(record.ref.artifact_id, tenant_id="tenant-a")
            blob.write_bytes(b"original")
            next(root.glob("*/*.json")).write_text("not-json", encoding="utf-8")
            with self.assertRaises(ArtifactIntegrityError):
                await store.get(record.ref.artifact_id, tenant_id="tenant-a")
            with self.assertRaises(PersistenceError):
                await store.get("../escape", tenant_id="tenant-a")

    async def test_retention(self) -> None:
        moment = [NOW]
        store = MemoryArtifactStore(clock=lambda: moment[0])
        await store.put(
            b"expired",
            name="old.txt",
            media_type="text/plain",
            ttl_seconds=1,
            artifact_id="old",
        )
        moment[0] = NOW + timedelta(seconds=2)
        with self.assertRaises(ArtifactNotFoundError):
            await store.get("old", tenant_id=None)
        self.assertEqual(await store.purge_expired(), 1)


class SessionRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_runs_fail_one_writer_instead_of_mixing_turns(self) -> None:
        sessions = MemorySessionStore(clock=lambda: NOW)
        await sessions.create(
            Session(
                session_id="single-writer",
                agent_id="assistant",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        gate = asyncio.Event()

        class GatedStore(MemorySessionStore):
            async def get(self, session_id, *, tenant_id=None):
                value = await super().get(session_id, tenant_id=tenant_id)
                gate.set()
                await asyncio.sleep(0)
                return value

        gated = GatedStore(clock=lambda: NOW)
        await gated.create(await sessions.get("single-writer"))
        contexts = (
            RunContext(agent_id="assistant", deps=None, session_id="single-writer"),
            RunContext(agent_id="assistant", deps=None, session_id="single-writer"),
        )
        results = await asyncio.gather(
            Runner(FakeModel([response("one")]), session_store=gated).run(
                agent(), "one", context=contexts[0]
            ),
            Runner(FakeModel([response("two")]), session_store=gated).run(
                agent(), "two", context=contexts[1]
            ),
        )
        self.assertEqual(sorted(result.status.value for result in results), ["completed", "failed"])
        self.assertEqual(len(await gated.list_entries("single-writer")), 2)

    async def test_session_state_manager_applies_artifact_retention_policy(self) -> None:
        sessions = MemorySessionStore(clock=lambda: NOW)
        artifacts = MemoryArtifactStore(clock=lambda: NOW)
        await sessions.create(
            Session(
                session_id="cascade",
                agent_id="assistant",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await artifacts.put(
            b"payload",
            name="data.txt",
            media_type="text/plain",
            session_id="cascade",
            artifact_id="cascade-artifact",
        )
        manager = SessionStateManager(sessions, artifact_store=artifacts)
        self.assertTrue(await manager.delete("cascade"))
        with self.assertRaises(ArtifactNotFoundError):
            await artifacts.get("cascade-artifact", tenant_id=None)

        await sessions.create(
            Session(
                session_id="retain",
                agent_id="assistant",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        await artifacts.put(
            b"retained",
            name="keep.txt",
            media_type="text/plain",
            session_id="retain",
            artifact_id="retained-artifact",
        )
        keep = SessionStateManager(
            sessions,
            artifact_store=artifacts,
            artifact_policy=ArtifactRetentionPolicy(delete_with_session=False),
        )
        self.assertTrue(await keep.delete("retain"))
        self.assertEqual((await artifacts.get("retained-artifact", tenant_id=None))[1], b"retained")

    async def test_runner_uses_an_opt_in_memory_context_source(self) -> None:
        memories = InMemoryMemoryStore(clock=lambda: NOW)
        await memories.upsert(
            MemoryRecord(
                memory_id="preference-1",
                agent_id="assistant",
                content="technical answers should be concise",
                tenant_id="tenant-a",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        fake = FakeModel([response("done")])
        context = RunContext(agent_id="assistant", deps=None, metadata={"tenant_id": "tenant-a"})
        await Runner(
            fake,
            context_sources=(MemoryContextSource(memories),),
        ).run(agent(), "technical", context=context)
        self.assertTrue(fake.requests[0].messages[1].metadata["memory_source"])
        self.assertEqual(fake.requests[0].messages[-1].content[0].text, "technical")

    async def test_runner_resumes_session_without_duplicate_messages(self) -> None:
        sessions = MemorySessionStore(clock=lambda: NOW)
        await sessions.create(
            Session(
                session_id="conversation",
                agent_id="assistant",
                tenant_id="tenant-a",
                created_at=NOW,
                updated_at=NOW,
            )
        )
        first_context = RunContext(
            agent_id="assistant",
            deps=None,
            session_id="conversation",
            metadata={"tenant_id": "tenant-a"},
        )
        await Runner(FakeModel([response("first")]), session_store=sessions).run(
            agent(), "question one", context=first_context
        )
        second_model = FakeModel([response("second")])
        second_context = RunContext(
            agent_id="assistant",
            deps=None,
            session_id="conversation",
            metadata={"tenant_id": "tenant-a"},
        )
        result = await Runner(second_model, session_store=sessions).run(
            agent(), "question two", context=second_context
        )
        texts = [
            part.text
            for message in second_model.requests[0].messages
            for part in message.content
            if part.type == "text"
        ]
        self.assertEqual(texts, ["Help safely", "question one", "first", "question two"])
        self.assertEqual(result.metadata["session_id"], "conversation")
        entries = await sessions.list_entries("conversation", tenant_id="tenant-a")
        self.assertEqual(len(entries), 4)

        replay_model = FakeModel([response("different")])
        await Runner(replay_model, session_store=sessions).run(
            agent(), "question two", context=second_context
        )
        self.assertEqual(len(await sessions.list_entries("conversation", tenant_id="tenant-a")), 4)

    async def test_runner_externalizes_large_tool_result_and_emits_context(self) -> None:
        @tool
        def large() -> str:
            """Return a large payload."""
            return "x" * 200

        call = ModelResponse(
            id="tool-response",
            model="test",
            tool_calls=(ToolCall(id="call-1", name="large", arguments={}),),
            finish_reason=FinishReason.TOOL_CALLS,
        )
        artifacts = MemoryArtifactStore(clock=lambda: NOW)
        sink = MemoryEventSink()
        fake = FakeModel([call, response("done")])
        result = await Runner(
            fake,
            tools=ToolRegistry([large]),
            artifact_store=artifacts,
            artifact_policy=ArtifactRetentionPolicy(inline_threshold_bytes=1),
            events=EventBus([sink]),
        ).run(agent(tools=("large",)), "go")
        self.assertEqual(len(result.artifacts), 1)
        self.assertEqual(
            (await artifacts.get(result.artifacts[0].artifact_id, tenant_id=None))[1][0:1], b"{"
        )
        tool_message = fake.requests[1].messages[-1]
        payload = json.loads(tool_message.content[0].text)
        self.assertEqual(payload["status"], "externalized")
        self.assertIn(EventType.ARTIFACT_CREATED, [event.event_type for event in sink.events])
        self.assertIn(EventType.CONTEXT_SELECTED, [event.event_type for event in sink.events])
