from __future__ import annotations

import inspect
import unittest

import pyagentskit
from pyagentskit import (
    ApprovalRequest,
    ApprovalStore,
    DataPolicy,
    GuardrailDecision,
    GuardrailPipeline,
    MemoryApprovalStore,
)
from pyagentskit.runtime import Runner


class GuardrailsPublicApiTests(unittest.TestCase):
    def test_root_exports_and_protocols(self) -> None:
        expected = {
            "ApprovalDecision",
            "ApprovalRequest",
            "ApprovalStatus",
            "ApprovalStore",
            "CallableGuardrail",
            "DataClassification",
            "DataPolicy",
            "EnvironmentSecretProvider",
            "Guardrail",
            "GuardrailAction",
            "GuardrailDecision",
            "GuardrailPipeline",
            "GuardrailStage",
            "MemoryApprovalStore",
            "Redactor",
            "SQLiteApprovalStore",
        }
        self.assertTrue(expected.issubset(pyagentskit.__all__))
        self.assertIsInstance(MemoryApprovalStore(), ApprovalStore)

    def test_serialized_fields_are_frozen_for_0_4_x(self) -> None:
        self.assertEqual(
            tuple(GuardrailDecision.model_fields),
            (
                "action",
                "reason",
                "transformed_value",
                "feedback",
                "policy_id",
                "metadata",
            ),
        )
        self.assertEqual(
            tuple(ApprovalRequest.model_fields),
            (
                "approval_id",
                "run_id",
                "trace_id",
                "agent_id",
                "session_id",
                "tenant_id",
                "tool_call",
                "tool_fingerprint",
                "status",
                "revision",
                "requested_at",
                "expires_at",
                "resolved_at",
                "actor_id",
                "decision",
                "reason",
                "metadata",
            ),
        )
        self.assertEqual(
            tuple(DataPolicy.model_fields),
            (
                "max_classification",
                "allowed_providers",
                "allowed_models",
                "require_zdr",
                "allow_training",
            ),
        )

    def test_runner_extensions_are_additive(self) -> None:
        init_parameters = inspect.signature(Runner.__init__).parameters
        for name in ("guardrails", "data_policy", "approval_store", "approval_ttl_seconds"):
            self.assertIn(name, init_parameters)
        self.assertTrue(inspect.iscoroutinefunction(Runner.resume_approval))
        self.assertEqual(GuardrailPipeline().guardrails, ())


if __name__ == "__main__":
    unittest.main()
