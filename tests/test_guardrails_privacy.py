from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from pyagentskit import (
    AgentDefinition,
    CallableGuardrail,
    ConfigurationError,
    DataClassification,
    DataPolicy,
    EnvironmentSecretProvider,
    FinishReason,
    GuardrailAction,
    GuardrailDecision,
    GuardrailError,
    GuardrailPipeline,
    GuardrailStage,
    ModelRef,
    ModelResponse,
    PrivacyPolicyError,
    Redactor,
    RunContext,
    RunStatus,
    TextContent,
)
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


def agent(*, metadata=None):  # type: ignore[no-untyped-def]
    return AgentDefinition(
        id="guarded",
        version="1.0.0",
        instructions="Help safely",
        model=ModelRef(provider="fake", name="test"),
        metadata={} if metadata is None else metadata,
    )


def response(text: str) -> ModelResponse:
    return ModelResponse(
        id="response",
        model="test",
        content=(TextContent(text=text),),
        finish_reason=FinishReason.STOP,
    )


class GuardrailTests(unittest.IsolatedAsyncioTestCase):
    def test_decision_and_pipeline_contract_validation(self) -> None:
        with self.assertRaises(ValueError):
            GuardrailDecision(action=GuardrailAction.TRANSFORM, reason="missing value")
        with self.assertRaises(ValueError):
            GuardrailDecision(action=GuardrailAction.RETRY_WITH_FEEDBACK, reason="missing feedback")

        async def allow(value, stage, context):  # type: ignore[no-untyped-def]
            return GuardrailDecision(action=GuardrailAction.ALLOW, reason="ok")

        with self.assertRaises(GuardrailError):
            CallableGuardrail("empty", [], allow)
        guardrail = CallableGuardrail("input", [GuardrailStage.INPUT], allow)
        pipeline = GuardrailPipeline([guardrail])
        self.assertEqual(pipeline.stages()[GuardrailStage.INPUT], 1)
        self.assertEqual(pipeline.stages()[GuardrailStage.OUTPUT], 0)

    async def test_callable_guardrail_rejects_wrong_stage_and_return_type(self) -> None:
        async def invalid(value, stage, context):  # type: ignore[no-untyped-def]
            return "not-a-decision"

        guardrail = CallableGuardrail("invalid", [GuardrailStage.INPUT], invalid)
        context = RunContext(agent_id="guarded", deps=None)
        with self.assertRaises(GuardrailError):
            await guardrail.evaluate("x", stage=GuardrailStage.OUTPUT, context=context)
        with self.assertRaises(GuardrailError):
            await guardrail.evaluate("x", stage=GuardrailStage.INPUT, context=context)

    async def test_input_transform_is_applied_before_provider_access(self) -> None:
        async def transform(value, stage, context):  # type: ignore[no-untyped-def]
            self.assertEqual(stage, GuardrailStage.INPUT)
            self.assertEqual(context.agent_id, "guarded")
            return GuardrailDecision(
                action=GuardrailAction.TRANSFORM,
                reason="remove sensitive marker",
                transformed_value=value.replace("SECRET", "[REDACTED]"),
            )

        fake = FakeModel([response("ok")])
        pipeline = GuardrailPipeline(
            [CallableGuardrail("input.redact", [GuardrailStage.INPUT], transform)]
        )
        result = await Runner(fake, guardrails=pipeline).run(agent(), "hello SECRET")
        self.assertEqual(result.status, RunStatus.COMPLETED)
        self.assertEqual(fake.requests[0].messages[-1].content[0].text, "hello [REDACTED]")
        self.assertEqual(result.metadata["guardrails"][0]["action"], "transform")

    async def test_rejection_fails_closed_without_leaking_reason_to_result(self) -> None:
        async def reject(value, stage, context):  # type: ignore[no-untyped-def]
            return GuardrailDecision(
                action=GuardrailAction.REJECT,
                reason="contains private evaluation detail",
                policy_id="ignored",
            )

        fake = FakeModel([response("unused")])
        result = await Runner(
            fake,
            guardrails=GuardrailPipeline(
                [CallableGuardrail("request.block", [GuardrailStage.MODEL_REQUEST], reject)]
            ),
        ).run(agent(), "hello")
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(fake.requests, [])
        self.assertNotIn("private evaluation detail", result.model_dump_json())

    async def test_output_can_retry_once_with_policy_feedback(self) -> None:
        async def retry_bad(value, stage, context):  # type: ignore[no-untyped-def]
            if value == "bad":
                return GuardrailDecision(
                    action=GuardrailAction.RETRY_WITH_FEEDBACK,
                    reason="output incomplete",
                    feedback="provide a complete answer",
                )
            return GuardrailDecision(action=GuardrailAction.ALLOW, reason="output accepted")

        fake = FakeModel([response("bad"), response("good")])
        result = await Runner(
            fake,
            guardrails=GuardrailPipeline(
                [CallableGuardrail("output.quality", [GuardrailStage.OUTPUT], retry_bad)]
            ),
        ).run(agent(), "hello")
        self.assertEqual(result.output, "good")
        self.assertEqual(len(fake.requests), 2)
        self.assertIn("rejected by policy", fake.requests[1].messages[-1].content[0].text)

    async def test_policy_failure_is_normalized_and_fail_closed(self) -> None:
        async def broken(value, stage, context):  # type: ignore[no-untyped-def]
            raise RuntimeError("SECRET implementation detail")

        result = await Runner(
            FakeModel([response("unused")]),
            guardrails=GuardrailPipeline(
                [CallableGuardrail("broken", [GuardrailStage.INPUT], broken)]
            ),
        ).run(agent(), "hello")
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertNotIn("SECRET", result.model_dump_json())


class PrivacyTests(unittest.IsolatedAsyncioTestCase):
    async def test_classification_and_allowlists_block_before_network(self) -> None:
        fake = FakeModel([response("unused")])
        policy = DataPolicy(
            max_classification=DataClassification.CONFIDENTIAL,
            allowed_providers=("fake",),
            allowed_models=("test",),
        )
        context = RunContext(
            agent_id="guarded",
            deps=None,
            metadata={"data_classification": "restricted"},
        )
        result = await Runner(fake, data_policy=policy).run(agent(), "hello", context=context)
        self.assertEqual(result.status, RunStatus.FAILED)
        self.assertEqual(fake.requests, [])

    async def test_zdr_and_training_guarantees_are_explicit(self) -> None:
        policy = DataPolicy(require_zdr=True, allow_training=False)
        with self.assertRaises(PrivacyPolicyError):
            policy.authorize(
                provider="fake",
                model="test",
                classification=DataClassification.INTERNAL,
            )
        policy.authorize(
            provider="fake",
            model="test",
            classification=DataClassification.INTERNAL,
            provider_policy={"zdr": True, "allow_training": False},
        )
        with self.assertRaises(PrivacyPolicyError):
            DataPolicy(allowed_providers=("allowed",)).authorize(
                provider="denied",
                model="test",
                classification=DataClassification.PUBLIC,
                provider_policy={"allow_training": False},
            )
        with self.assertRaises(PrivacyPolicyError):
            DataPolicy(allowed_models=("allowed",)).authorize(
                provider="fake",
                model="denied",
                classification=DataClassification.PUBLIC,
                provider_policy={"allow_training": False},
            )
        with self.assertRaises(PrivacyPolicyError):
            DataPolicy().authorize(
                provider="fake",
                model="test",
                classification=DataClassification.PUBLIC,
                provider_policy={"allow_training": True},
            )

    def test_data_policy_and_secret_provider_configuration_validation(self) -> None:
        with self.assertRaises(ValueError):
            DataPolicy(allowed_providers=("same", "same"))
        with self.assertRaises(ConfigurationError):
            EnvironmentSecretProvider([])
        with self.assertRaises(ConfigurationError):
            EnvironmentSecretProvider(["A", "A"])

    async def test_allowlisted_environment_secret_provider_has_no_cache(self) -> None:
        provider = EnvironmentSecretProvider(["SAFE_TEST_KEY"])
        with patch.dict(os.environ, {"SAFE_TEST_KEY": "value"}):
            self.assertEqual(await provider.get_secret("SAFE_TEST_KEY"), "value")
        with self.assertRaisesRegex(ConfigurationError, "allowlist"):
            await provider.get_secret("OTHER_KEY")
        self.assertNotIn("value", repr(provider.__dict__))

    def test_recursive_redaction(self) -> None:
        redactor = Redactor(["exact-secret"])
        value = {
            "a": "exact-secret",
            "nested": ["Bearer abcdefghijklmnop", "sk-abcdefghijklmnop"],
        }
        cleaned = redactor.redact(value)
        self.assertEqual(cleaned["a"], "[REDACTED]")
        self.assertNotIn("Bearer", cleaned["nested"][0])
        self.assertNotIn("sk-", cleaned["nested"][1])
        self.assertEqual(redactor.redact(("safe", 3)), ("safe", 3))


if __name__ == "__main__":
    unittest.main()
