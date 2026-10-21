"""Golden public contract for the PyAgentsKit 0.3.x state layer."""

from __future__ import annotations

import inspect
import unittest

import pyagentskit
from pyagentskit import (
    ArtifactRecord,
    ArtifactRetentionPolicy,
    ArtifactStore,
    ContextBudget,
    ContextDecision,
    ContextSelection,
    InMemoryMemoryStore,
    MemoryRecord,
    MemorySessionStore,
    MemoryStore,
    Session,
    SessionEntry,
    SessionStateManager,
    SessionStore,
    artifact_store,
    context,
    memory,
    sessions,
)
from pyagentskit.runtime import Runner


class StatePublicApiTests(unittest.TestCase):
    def test_new_symbols_are_root_exports(self) -> None:
        expected = {
            "ArtifactRecord",
            "ArtifactRetentionPolicy",
            "ArtifactStore",
            "ContextBudget",
            "ContextPolicy",
            "ContextSelection",
            "ContextSource",
            "FileSystemArtifactStore",
            "InMemoryMemoryStore",
            "MemoryArtifactStore",
            "MemoryContextSource",
            "MemoryRecord",
            "MemorySessionStore",
            "MemoryStore",
            "SQLiteMemoryStore",
            "SQLiteSessionStore",
            "Session",
            "SessionEntry",
            "SessionStore",
            "SessionStateManager",
            "SummarizingContextPolicy",
            "WindowContextPolicy",
        }
        self.assertTrue(expected.issubset(pyagentskit.__all__))

    def test_module_exports_are_explicit(self) -> None:
        self.assertEqual(
            sessions.__all__,
            [
                "MemorySessionStore",
                "SQLiteSessionStore",
                "Session",
                "SessionEntry",
                "SessionStore",
            ],
        )
        self.assertEqual(
            memory.__all__,
            [
                "InMemoryMemoryStore",
                "MemoryContextSource",
                "MemoryRecord",
                "MemoryStore",
                "SQLiteMemoryStore",
            ],
        )
        self.assertEqual(
            artifact_store.__all__,
            [
                "ArtifactRecord",
                "ArtifactRetentionPolicy",
                "ArtifactStore",
                "FileSystemArtifactStore",
                "MemoryArtifactStore",
            ],
        )
        self.assertIn("ContextPolicy", context.__all__)
        self.assertIn("ContextSource", context.__all__)

    def test_serialized_fields_are_stable(self) -> None:
        self.assertEqual(
            tuple(Session.model_fields),
            (
                "session_id",
                "agent_id",
                "tenant_id",
                "revision",
                "created_at",
                "updated_at",
                "expires_at",
                "metadata",
            ),
        )
        self.assertEqual(
            tuple(SessionEntry.model_fields),
            (
                "session_id",
                "tenant_id",
                "sequence",
                "turn_id",
                "message",
                "created_at",
                "run_id",
            ),
        )
        self.assertEqual(
            tuple(MemoryRecord.model_fields),
            (
                "memory_id",
                "agent_id",
                "content",
                "tenant_id",
                "session_id",
                "tags",
                "created_at",
                "updated_at",
                "expires_at",
                "metadata",
            ),
        )
        self.assertEqual(
            tuple(ArtifactRecord.model_fields),
            ("ref", "tenant_id", "session_id", "created_at", "expires_at", "provenance"),
        )
        self.assertEqual(
            tuple(ContextBudget.model_fields),
            ("max_tokens", "reserve_output_tokens", "chars_per_token"),
        )
        self.assertEqual(
            tuple(ContextDecision.model_fields),
            ("action", "source_indexes", "reason", "estimated_tokens"),
        )
        self.assertEqual(
            tuple(ContextSelection.model_fields),
            (
                "messages",
                "estimated_tokens",
                "source_message_count",
                "removed_message_count",
                "summarized_message_count",
                "decisions",
            ),
        )

    def test_protocols_and_runner_extension_points(self) -> None:
        self.assertIsInstance(MemorySessionStore(), SessionStore)
        self.assertIsInstance(InMemoryMemoryStore(), MemoryStore)
        self.assertIsInstance(pyagentskit.MemoryArtifactStore(), ArtifactStore)
        self.assertTrue(inspect.iscoroutinefunction(SessionStateManager.delete))
        parameters = inspect.signature(Runner.__init__).parameters
        names = tuple(parameters)
        previous_extensions = (
            "session_store",
            "context_policy",
            "artifact_store",
            "artifact_policy",
            "context_sources",
        )
        self.assertTrue(all(name in names for name in previous_extensions))
        indexes = tuple(names.index(name) for name in previous_extensions)
        self.assertEqual(indexes, tuple(sorted(indexes)))
        run_parameters = inspect.signature(Runner.run).parameters
        self.assertIn("context_budget", run_parameters)

    def test_policy_defaults_are_bounded_and_explicit(self) -> None:
        policy = ArtifactRetentionPolicy()
        self.assertEqual(policy.inline_threshold_bytes, 65_536)
        self.assertIsNone(policy.default_ttl_seconds)
        self.assertTrue(policy.delete_with_session)
        budget = ContextBudget()
        self.assertIsNone(budget.max_tokens)
        self.assertEqual(budget.reserve_output_tokens, 0)
        self.assertEqual(budget.chars_per_token, 4.0)


if __name__ == "__main__":
    unittest.main()
