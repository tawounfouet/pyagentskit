from __future__ import annotations

import dataclasses
import hashlib
import inspect
import unittest

import pyagentskit
from pyagentskit import (
    AgentDefinition,
    AgentEvent,
    EvalReport,
    EventType,
    ModelRequest,
    ModelResponse,
    RunCheckpoint,
    RunContext,
    RunLimits,
    RunResult,
    RunStatus,
    ToolDefinition,
)
from pyagentskit.providers.anthropic import AnthropicModel
from pyagentskit.providers.google import GoogleModel
from pyagentskit.providers.ollama import OllamaModel
from pyagentskit.providers.openai import OpenAIModel
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.providers.xai import XAIModel


class V1PublicApiFreezeTests(unittest.TestCase):
    def test_root_export_manifest_is_frozen(self) -> None:
        payload = "\n".join(sorted(pyagentskit.__all__)).encode()
        self.assertEqual(len(pyagentskit.__all__), 155)
        self.assertEqual(
            hashlib.sha256(payload).hexdigest(),
            "bfd66c240b638dca67178db2159c49b1df0181a78a405d72f6abb889252b08d9",
        )

    def test_structured_contract_field_order_is_frozen(self) -> None:
        expected = {
            AgentDefinition: (
                "id",
                "version",
                "instructions",
                "model",
                "description",
                "tools",
                "limits",
                "output_schema",
                "metadata",
            ),
            ModelRequest: ("messages", "tools", "output_schema", "settings", "metadata"),
            ModelResponse: (
                "id",
                "model",
                "content",
                "tool_calls",
                "finish_reason",
                "usage",
                "metadata",
            ),
            ToolDefinition: (
                "name",
                "version",
                "description",
                "input_schema",
                "output_schema",
                "risk",
                "idempotent",
                "requires_approval",
                "timeout_seconds",
                "concurrency_limit",
                "tags",
                "metadata",
            ),
            RunLimits: (
                "max_steps",
                "max_model_calls",
                "max_tool_calls",
                "max_parallel_tools",
                "timeout_seconds",
                "max_input_tokens",
                "max_output_tokens",
                "max_total_tokens",
                "max_cost_usd",
            ),
            RunResult: (
                "run_id",
                "trace_id",
                "agent_id",
                "status",
                "output",
                "error",
                "usage",
                "artifacts",
                "started_at",
                "completed_at",
                "metadata",
            ),
            AgentEvent: (
                "schema_version",
                "event_id",
                "event_type",
                "occurred_at",
                "run_id",
                "trace_id",
                "agent_id",
                "session_id",
                "step",
                "payload",
            ),
            RunCheckpoint: (
                "checkpoint_id",
                "schema_version",
                "run_id",
                "trace_id",
                "agent_id",
                "agent_version",
                "session_id",
                "tenant_id",
                "sequence",
                "kind",
                "status",
                "created_at",
                "result",
                "metadata",
            ),
            EvalReport: (
                "schema_version",
                "dataset_id",
                "dataset_version",
                "created_at",
                "duration_seconds",
                "results",
                "passed_cases",
                "failed_cases",
                "pass_rate",
                "metadata",
            ),
        }
        for contract, fields in expected.items():
            self.assertEqual(tuple(contract.model_fields), fields)
        self.assertEqual(
            tuple(field.name for field in dataclasses.fields(RunContext)),
            ("agent_id", "deps", "run_id", "trace_id", "session_id", "started_at", "metadata"),
        )

    def test_provider_constructor_parameters_are_frozen(self) -> None:
        common = (
            "model",
            "api_key",
            "client",
            "base_url",
            "timeout",
            "retries",
            "capabilities",
        )
        for adapter in (OpenAIModel, AnthropicModel, GoogleModel, XAIModel, OllamaModel):
            self.assertEqual(tuple(inspect.signature(adapter).parameters), common)
        self.assertEqual(
            tuple(inspect.signature(OpenRouterModel).parameters),
            (
                *common,
                "app_url",
                "app_title",
                "allow_fallbacks",
                "require_parameters",
                "routing",
                "include_router_metadata",
            ),
        )

    def test_serialized_enum_values_are_frozen(self) -> None:
        self.assertEqual(
            tuple(RunStatus),
            (
                RunStatus.CREATED,
                RunStatus.RUNNING,
                RunStatus.WAITING_APPROVAL,
                RunStatus.COMPLETED,
                RunStatus.FAILED,
                RunStatus.CANCELLED,
                RunStatus.LIMIT_EXCEEDED,
                RunStatus.UNKNOWN_EFFECT,
            ),
        )
        self.assertEqual(len(tuple(EventType)), 28)


if __name__ == "__main__":
    unittest.main()
