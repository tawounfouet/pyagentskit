"""Explicitly gated, potentially billable OpenRouter RC qualification tests."""

import os
import unittest

from pyagentskit import Message, MessageRole, ModelRequest, RunContext
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.providers.openrouter_catalog import (
    ModelCapabilityRequirements,
    OpenRouterCatalog,
)
from pyagentskit.providers.openrouter_routing import (
    OpenRouterProfile,
    OpenRouterRoutingPolicy,
)

CTX = RunContext(agent_id="openrouter-live-qualification", deps=None)
REQUEST = ModelRequest(
    messages=(Message.from_text(MessageRole.USER, "Reply with exactly: OK"),),
    settings={"max_output_tokens": 16, "temperature": 0.0},
)


@unittest.skipUnless(
    os.getenv("PYAGENTSKIT_OPENROUTER_LIVE") == "1",
    "OpenRouter evaluation live qualification is opt-in",
)
class LiveEvaluationProfile(unittest.IsolatedAsyncioTestCase):
    async def test_catalog_preflight_and_generation(self):
        key = os.environ["OPENROUTER_API_KEY"]
        model_id = os.environ["PYAGENTSKIT_OPENROUTER_MODEL"]
        routing = OpenRouterRoutingPolicy.for_profile(OpenRouterProfile.EVALUATION)
        async with OpenRouterCatalog(api_key=key) as catalog:
            model = await OpenRouterModel.from_catalog(
                model_id,
                catalog=catalog,
                requirements=ModelCapabilityRequirements(streaming=True),
                routing=routing,
                api_key=key,
            )
            try:
                response = await model.generate(REQUEST, context=CTX)
            finally:
                await model.aclose()
        self.assertEqual(response.metadata["requested_model"], model_id)
        self.assertFalse(routing.allow_fallbacks)
        self.assertTrue(response.content)


@unittest.skipUnless(
    os.getenv("PYAGENTSKIT_OPENROUTER_COMPLIANCE_LIVE") == "1",
    "OpenRouter compliance live qualification is opt-in",
)
class LiveComplianceProfile(unittest.IsolatedAsyncioTestCase):
    async def test_zdr_allowlist_generation(self):
        providers = tuple(
            value.strip()
            for value in os.environ["PYAGENTSKIT_OPENROUTER_ALLOWED_PROVIDERS"].split(",")
            if value.strip()
        )
        routing = OpenRouterRoutingPolicy.for_profile(
            OpenRouterProfile.COMPLIANCE,
            allowed_providers=providers,
        )
        async with OpenRouterModel(
            os.environ["PYAGENTSKIT_OPENROUTER_MODEL"],
            routing=routing,
        ) as model:
            response = await model.generate(REQUEST, context=CTX)
        self.assertTrue(routing.data.require_zdr)
        self.assertTrue(response.content)


@unittest.skipUnless(
    os.getenv("PYAGENTSKIT_OPENROUTER_FALLBACK_LIVE") == "1",
    "OpenRouter model fallback live qualification is opt-in",
)
class LiveModelFallback(unittest.IsolatedAsyncioTestCase):
    async def test_expected_model_is_resolved(self):
        primary = os.environ["PYAGENTSKIT_OPENROUTER_PRIMARY_MODEL"]
        fallback = os.environ["PYAGENTSKIT_OPENROUTER_FALLBACK_MODEL"]
        expected = os.environ["PYAGENTSKIT_OPENROUTER_EXPECTED_RESOLVED_MODEL"]
        routing = OpenRouterRoutingPolicy(
            allow_fallbacks=True,
            model_fallbacks=(fallback,),
        )
        async with OpenRouterModel(primary, routing=routing) as model:
            response = await model.generate(REQUEST, context=CTX)
        self.assertEqual(response.metadata["resolved_model"], expected)
        self.assertEqual(response.metadata["fallback_used"], expected != primary)
