"""Golden compatibility contract for the public OpenRouter 0.2.x API."""

from __future__ import annotations

import inspect
import unittest

from pyagentskit.providers import openrouter, openrouter_catalog, openrouter_routing
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.providers.openrouter_catalog import (
    ModelCapabilityRequirements,
    OpenRouterCatalog,
    OpenRouterModelDescriptor,
)
from pyagentskit.providers.openrouter_routing import (
    OpenRouterDataPolicy,
    OpenRouterProfile,
    OpenRouterRoutingPolicy,
)


class OpenRouterStableApiTests(unittest.TestCase):
    def test_frozen_module_exports(self) -> None:
        self.assertEqual(openrouter.__all__, ["OpenRouterModel"])
        self.assertEqual(
            openrouter_catalog.__all__,
            [
                "ModelCapabilityRequirements",
                "OpenRouterCatalog",
                "OpenRouterModelDescriptor",
                "common_capabilities",
                "require_capabilities",
            ],
        )
        self.assertEqual(
            openrouter_routing.__all__,
            ["OpenRouterDataPolicy", "OpenRouterProfile", "OpenRouterRoutingPolicy"],
        )

    def test_frozen_constructor_parameters(self) -> None:
        self.assertEqual(
            tuple(inspect.signature(OpenRouterModel.__init__).parameters),
            (
                "self",
                "model",
                "api_key",
                "client",
                "base_url",
                "timeout",
                "retries",
                "capabilities",
                "app_url",
                "app_title",
                "allow_fallbacks",
                "require_parameters",
                "routing",
                "include_router_metadata",
            ),
        )
        defaults = {
            name: parameter.default
            for name, parameter in inspect.signature(OpenRouterModel.__init__).parameters.items()
            if parameter.default is not inspect.Parameter.empty
        }
        self.assertEqual(
            defaults,
            {
                "api_key": None,
                "client": None,
                "base_url": None,
                "timeout": 60,
                "retries": 0,
                "capabilities": None,
                "app_url": None,
                "app_title": None,
                "allow_fallbacks": False,
                "require_parameters": True,
                "routing": None,
                "include_router_metadata": True,
            },
        )
        self.assertEqual(
            tuple(inspect.signature(OpenRouterCatalog.__init__).parameters),
            (
                "self",
                "api_key",
                "client",
                "base_url",
                "timeout",
                "retries",
                "ttl_seconds",
                "clock",
                "offline",
            ),
        )

    def test_frozen_method_parameters(self) -> None:
        expected = {
            OpenRouterModel.from_catalog: ("model", "catalog", "requirements", "kwargs"),
            OpenRouterCatalog.from_snapshot: ("path", "clock"),
            OpenRouterCatalog.list_models: ("self", "force"),
            OpenRouterCatalog.get: ("self", "model_id", "force"),
            OpenRouterCatalog.save_snapshot: ("self", "path"),
            OpenRouterCatalog.load_snapshot: ("self", "path"),
            OpenRouterRoutingPolicy.for_profile: (
                "profile",
                "allowed_providers",
            ),
        }
        for method, names in expected.items():
            with self.subTest(method=method.__qualname__):
                self.assertEqual(tuple(inspect.signature(method).parameters), names)

    def test_frozen_serialized_fields_and_profiles(self) -> None:
        self.assertEqual(
            tuple(ModelCapabilityRequirements.model_fields),
            (
                "tool_calling",
                "structured_output",
                "streaming",
                "parallel_tool_calls",
                "input_modalities",
                "output_modalities",
                "min_context_tokens",
                "min_output_tokens",
            ),
        )
        self.assertEqual(
            tuple(OpenRouterModelDescriptor.model_fields),
            (
                "id",
                "name",
                "canonical_slug",
                "supported_parameters",
                "input_modalities",
                "output_modalities",
                "max_context_tokens",
                "max_output_tokens",
            ),
        )
        self.assertEqual(
            tuple(OpenRouterDataPolicy.model_fields),
            ("require_zdr", "allow_training", "allowed_providers"),
        )
        self.assertEqual(
            tuple(OpenRouterRoutingPolicy.model_fields),
            (
                "provider_order",
                "ignored_providers",
                "model_fallbacks",
                "allow_fallbacks",
                "require_parameters",
                "data",
            ),
        )
        self.assertEqual(
            tuple((profile.name, profile.value) for profile in OpenRouterProfile),
            (
                ("DEVELOPMENT", "development"),
                ("PRODUCTION", "production"),
                ("COMPLIANCE", "compliance"),
                ("EVALUATION", "evaluation"),
            ),
        )


if __name__ == "__main__":
    unittest.main()
