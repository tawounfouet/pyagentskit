"""Advanced OpenRouter routing, catalog and capability contract tests."""

import asyncio
import json
import tempfile
import unittest
from pathlib import Path

import httpx
from pydantic import ValidationError

from pyagentskit import (
    AgentDefinition,
    CapabilityError,
    ConfigurationError,
    EventType,
    Message,
    MessageRole,
    Modality,
    ModelRef,
    ModelRequest,
    ModelResponseError,
    RunContext,
)
from pyagentskit.observability import EventBus, MemoryEventSink
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.providers.openrouter_catalog import (
    ModelCapabilityRequirements,
    OpenRouterCatalog,
    OpenRouterModelDescriptor,
    common_capabilities,
    require_capabilities,
)
from pyagentskit.providers.openrouter_routing import (
    OpenRouterDataPolicy,
    OpenRouterProfile,
    OpenRouterRoutingPolicy,
)
from pyagentskit.runtime import Runner


def catalog_payload() -> dict[str, object]:
    return {
        "data": [
            {
                "id": "anthropic/claude-test",
                "name": "Claude Test",
                "canonical_slug": "anthropic/claude-test-20260901",
                "context_length": 200_000,
                "architecture": {
                    "input_modalities": ["text", "image", "unknown-future-type"],
                    "output_modalities": ["text"],
                },
                "supported_parameters": [
                    "tools",
                    "response_format",
                    "parallel_tool_calls",
                    "temperature",
                ],
                "top_provider": {"max_completion_tokens": 8_192},
            }
        ]
    }


def fallback_catalog_payload() -> dict[str, object]:
    payload = catalog_payload()
    models = list(payload["data"])  # type: ignore[arg-type]
    models.append(
        {
            "id": "openai/fallback-test",
            "name": "Fallback Test",
            "context_length": 100_000,
            "architecture": {
                "input_modalities": ["text"],
                "output_modalities": ["text"],
            },
            "supported_parameters": ["tools", "temperature"],
            "top_provider": {"max_completion_tokens": 4_096},
        }
    )
    return {"data": models}


def sse(*chunks: dict[str, object]) -> str:
    return "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks) + ("data: [DONE]\n\n")


class RoutingPolicyTests(unittest.TestCase):
    def test_wire_policy_and_profiles(self):
        policy = OpenRouterRoutingPolicy(
            provider_order=("anthropic", "amazon-bedrock"),
            ignored_providers=("google-vertex",),
            allow_fallbacks=True,
            model_fallbacks=("openai/gpt-test",),
            data=OpenRouterDataPolicy(
                require_zdr=True,
                allow_training=False,
                allowed_providers=("anthropic", "amazon-bedrock"),
            ),
        )
        self.assertEqual(
            policy.to_provider(),
            {
                "zdr": True,
                "data_collection": "deny",
                "only": ["anthropic", "amazon-bedrock"],
                "allow_fallbacks": True,
                "require_parameters": True,
                "order": ["anthropic", "amazon-bedrock"],
                "ignore": ["google-vertex"],
            },
        )
        evaluation = OpenRouterRoutingPolicy.for_profile(OpenRouterProfile.EVALUATION)
        self.assertFalse(evaluation.allow_fallbacks)
        pinned_evaluation = OpenRouterRoutingPolicy.for_profile(
            OpenRouterProfile.EVALUATION,
            allowed_providers=("anthropic",),
        )
        self.assertEqual(pinned_evaluation.data.allowed_providers, ("anthropic",))
        compliance = OpenRouterRoutingPolicy.for_profile(
            OpenRouterProfile.COMPLIANCE, allowed_providers=("anthropic",)
        )
        self.assertTrue(compliance.data.require_zdr)
        self.assertEqual(compliance.data.allowed_providers, ("anthropic",))

    def test_invalid_policy_combinations_fail_closed(self):
        invalid = [
            {"provider_order": ("anthropic", "anthropic")},
            {
                "provider_order": ("anthropic",),
                "ignored_providers": ("anthropic",),
            },
            {"model_fallbacks": ("openai/test",)},
            {"model_fallbacks": ("unqualified",), "allow_fallbacks": True},
            {
                "provider_order": ("google",),
                "data": OpenRouterDataPolicy(allowed_providers=("anthropic",)),
            },
        ]
        for values in invalid:
            with self.subTest(values=values), self.assertRaises(ValidationError):
                OpenRouterRoutingPolicy(**values)
        with self.assertRaises(ConfigurationError):
            OpenRouterRoutingPolicy.for_profile(OpenRouterProfile.COMPLIANCE)
        with self.assertRaises(ConfigurationError):
            OpenRouterRoutingPolicy.for_profile("evaluation")  # type: ignore[arg-type]

    def test_retry_coordination_and_legacy_compatibility(self):
        routing = OpenRouterRoutingPolicy(allow_fallbacks=True)
        with self.assertRaises(ConfigurationError):
            OpenRouterModel("anthropic/test", api_key="fake", retries=1, routing=routing)
        with self.assertRaises(ConfigurationError):
            OpenRouterModel("anthropic/test", api_key="fake", routing=routing, allow_fallbacks=True)


class CatalogTests(unittest.IsolatedAsyncioTestCase):
    async def test_ttl_cache_invalidation_and_concurrent_coalescing(self):
        calls = 0
        now = [100.0]

        async def handler(request):
            nonlocal calls
            self.assertEqual(request.url.path, "/api/v1/models")
            self.assertEqual(request.headers["authorization"], "Bearer catalog-key")
            calls += 1
            await asyncio.sleep(0.01)
            return httpx.Response(200, json=catalog_payload())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            catalog = OpenRouterCatalog(
                api_key="catalog-key",
                client=client,
                ttl_seconds=10,
                clock=lambda: now[0],
            )
            first, second = await asyncio.gather(catalog.list_models(), catalog.list_models())
            self.assertIs(first, second)
            self.assertEqual(calls, 1)
            now[0] = 111
            await catalog.list_models()
            self.assertEqual(calls, 2)
            catalog.invalidate()
            await catalog.list_models()
            self.assertEqual(calls, 3)

    async def test_descriptor_capabilities_and_negotiation(self):
        descriptor = OpenRouterModelDescriptor.from_api(catalog_payload()["data"][0])  # type: ignore[index]
        self.assertTrue(descriptor.capabilities.tool_calling)
        self.assertTrue(descriptor.capabilities.structured_output)
        self.assertEqual(descriptor.capabilities.input_modalities, (Modality.TEXT, Modality.IMAGE))
        require_capabilities(
            descriptor.id,
            descriptor.capabilities,
            ModelCapabilityRequirements(
                tool_calling=True,
                structured_output=True,
                streaming=True,
                parallel_tool_calls=True,
                input_modalities=(Modality.IMAGE,),
                min_context_tokens=128_000,
                min_output_tokens=4_096,
            ),
        )
        with self.assertRaisesRegex(CapabilityError, "input_modalities"):
            require_capabilities(
                descriptor.id,
                descriptor.capabilities,
                ModelCapabilityRequirements(input_modalities=(Modality.AUDIO,)),
            )

    async def test_snapshot_roundtrip_and_invalid_documents(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=catalog_payload())
            )
        ) as client:
            catalog = OpenRouterCatalog(api_key="fake", client=client)
            await catalog.list_models()
            with tempfile.TemporaryDirectory() as directory:
                snapshot = Path(directory) / "catalog.json"
                catalog.save_snapshot(snapshot)
                saved = json.loads(snapshot.read_text(encoding="utf-8"))
                self.assertEqual(saved["schema_version"], 2)
                self.assertEqual(saved["model_count"], 1)
                loaded = OpenRouterCatalog(api_key="fake", client=client)
                self.assertEqual(loaded.load_snapshot(snapshot)[0].id, "anthropic/claude-test")
                saved["models"][0]["name"] = "tampered"
                snapshot.write_text(json.dumps(saved), encoding="utf-8")
                with self.assertRaises(ConfigurationError):
                    loaded.load_snapshot(snapshot)
                snapshot.write_text('{"schema_version":2}', encoding="utf-8")
                with self.assertRaises(ConfigurationError):
                    loaded.load_snapshot(snapshot)

    async def test_v1_snapshot_is_still_readable(self):
        descriptor = OpenRouterModelDescriptor.from_api(catalog_payload()["data"][0])  # type: ignore[index]
        with tempfile.TemporaryDirectory() as directory:
            snapshot = Path(directory) / "v1.json"
            snapshot.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "models": [descriptor.model_dump(mode="json")],
                    }
                ),
                encoding="utf-8",
            )
            catalog = OpenRouterCatalog(api_key="fake")
            try:
                self.assertEqual(catalog.load_snapshot(snapshot), (descriptor,))
            finally:
                await catalog.aclose()

    async def test_offline_snapshot_requires_no_secret_or_http_client(self):
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=catalog_payload())
            )
        ) as client:
            source = OpenRouterCatalog(api_key="fake", client=client)
            await source.list_models()
            with tempfile.TemporaryDirectory() as directory:
                snapshot = Path(directory) / "offline.json"
                source.save_snapshot(snapshot)
                offline = OpenRouterCatalog.from_snapshot(snapshot)
                self.assertEqual((await offline.list_models())[0].id, "anthropic/claude-test")
                with self.assertRaises(ConfigurationError):
                    await offline.list_models(force=True)
                await offline.aclose()
        with self.assertRaises(ConfigurationError):
            OpenRouterCatalog(offline=True, api_key="not-allowed")
        with self.assertRaises(ConfigurationError):
            OpenRouterCatalog()

    async def test_catalog_rejects_malformed_and_missing_models(self):
        cases = [
            {"wrong": []},
            {"data": []},
            {"data": ["not-an-object"]},
            {"data": [{"id": "invalid"}]},
            {"data": [{"id": "openai/a"}, {"id": "openai/a"}]},
        ]
        for payload in cases:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request, payload=payload: httpx.Response(200, json=payload)
                )
            ) as client:
                catalog = OpenRouterCatalog(api_key="fake", client=client)
                with self.assertRaises(ModelResponseError) as caught:
                    await catalog.list_models()
                self.assertEqual(type(caught.exception).__name__, "ModelResponseError")
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=catalog_payload())
            )
        ) as client:
            with self.assertRaises(CapabilityError):
                await OpenRouterCatalog(api_key="fake", client=client).get("openai/missing")

    async def test_construct_model_from_catalog_before_generation(self):
        requests: list[str] = []

        def handler(request):
            requests.append(request.url.path)
            if request.url.path.endswith("/models"):
                return httpx.Response(200, json=catalog_payload())
            return httpx.Response(
                200,
                json={
                    "id": "gen-2",
                    "model": "anthropic/claude-test",
                    "provider": "Anthropic",
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                },
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            catalog = OpenRouterCatalog(api_key="fake", client=client)
            model = await OpenRouterModel.from_catalog(
                "anthropic/claude-test",
                catalog=catalog,
                requirements=ModelCapabilityRequirements(tool_calling=True),
                api_key="fake",
                client=client,
            )
            self.assertTrue(model.capabilities.tool_calling)
            self.assertEqual(requests, ["/api/v1/models"])

    async def test_fallback_chain_uses_capability_intersection(self):
        routing = OpenRouterRoutingPolicy(
            allow_fallbacks=True,
            model_fallbacks=("openai/fallback-test",),
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json=fallback_catalog_payload())
            )
        ) as client:
            catalog = OpenRouterCatalog(api_key="fake", client=client)
            with self.assertRaisesRegex(CapabilityError, "openai/fallback-test"):
                await OpenRouterModel.from_catalog(
                    "anthropic/claude-test",
                    catalog=catalog,
                    requirements=ModelCapabilityRequirements(structured_output=True),
                    api_key="fake",
                    client=client,
                    routing=routing,
                )
            model = await OpenRouterModel.from_catalog(
                "anthropic/claude-test",
                catalog=catalog,
                api_key="fake",
                client=client,
                routing=routing,
            )
            self.assertTrue(model.capabilities.tool_calling)
            self.assertFalse(model.capabilities.structured_output)
            self.assertEqual(model.capabilities.input_modalities, (Modality.TEXT,))
            self.assertEqual(model.capabilities.max_context_tokens, 100_000)
            self.assertEqual(
                model.capabilities.metadata["routed_models"],
                ["anthropic/claude-test", "openai/fallback-test"],
            )
            with self.assertRaises(ConfigurationError):
                await OpenRouterModel.from_catalog(
                    "anthropic/claude-test",
                    catalog=catalog,
                    capabilities=model.capabilities,
                    api_key="fake",
                    client=client,
                )

    def test_empty_capability_chain_is_rejected(self):
        with self.assertRaises(ConfigurationError):
            common_capabilities(())


class RoutedResponseTests(unittest.IsolatedAsyncioTestCase):
    async def test_model_fallback_body_and_safe_router_metadata(self):
        routing = OpenRouterRoutingPolicy(
            allow_fallbacks=True,
            model_fallbacks=("openai/gpt-test",),
        )

        def handler(request):
            self.assertEqual(request.headers["x-openrouter-metadata"], "enabled")
            body = json.loads(request.content)
            self.assertNotIn("model", body)
            self.assertEqual(body["models"], ["anthropic/primary", "openai/gpt-test"])
            return httpx.Response(
                200,
                json={
                    "id": "gen-fallback",
                    "model": "openai/gpt-test",
                    "choices": [{"message": {"content": "ok"}, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                    "openrouter_metadata": {
                        "requested": "anthropic/primary",
                        "strategy": "fallback",
                        "region": "iad",
                        "summary": "PRIVATE ROUTER SUMMARY",
                        "attempt": 2,
                        "is_byok": True,
                        "endpoints": {
                            "available": [
                                {
                                    "provider": "OpenAI",
                                    "model": "openai/gpt-test",
                                    "selected": True,
                                }
                            ]
                        },
                        "pipeline": [{"data": {"secret": "PRIVATE"}}],
                    },
                },
            )

        request = ModelRequest(messages=(Message.from_text(MessageRole.USER, "hello"),))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model = OpenRouterModel(
                "anthropic/primary", api_key="fake", client=client, routing=routing
            )
            response = await model.generate(request, context=RunContext(agent_id="test", deps=None))
        self.assertTrue(response.metadata["fallback_used"])
        self.assertEqual(response.metadata["upstream_provider"], "OpenAI")
        self.assertEqual(response.metadata["route_attempt"], 2)
        self.assertEqual(response.metadata["route_strategy"], "fallback")
        serialized = json.dumps(response.metadata)
        self.assertNotIn("PRIVATE", serialized)
        self.assertNotIn("pipeline", serialized)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model = OpenRouterModel(
                "anthropic/primary", api_key="fake", client=client, routing=routing
            )
            sink = MemoryEventSink()
            definition = AgentDefinition(
                id="routing-trace",
                version="1.0.0",
                instructions="Answer",
                model=ModelRef(provider="openrouter", name="anthropic/primary"),
            )
            await Runner(model, events=EventBus([sink])).run(definition, "hello")
        completed = next(
            event for event in sink.events if event.event_type is EventType.MODEL_RESPONSE_COMPLETED
        )
        self.assertTrue(completed.payload["fallback_used"])
        self.assertEqual(completed.payload["upstream_provider"], "OpenAI")
        self.assertEqual(completed.payload["route_attempt"], 2)

    async def test_stream_terminal_event_contains_only_safe_route_metadata(self):
        stream = sse(
            {
                "id": "gen-stream",
                "model": "anthropic/primary",
                "choices": [{"delta": {"content": "ok"}, "finish_reason": None}],
            },
            {
                "id": "gen-stream",
                "model": "openai/fallback-test",
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                "openrouter_metadata": {
                    "strategy": "fallback",
                    "region": "fra",
                    "attempt": 2,
                    "is_byok": False,
                    "summary": "PRIVATE",
                    "pipeline": [{"data": {"prompt": "PRIVATE"}}],
                    "endpoints": {
                        "available": [
                            {
                                "provider": "OpenAI",
                                "model": "openai/fallback-test",
                                "selected": True,
                            }
                        ]
                    },
                },
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text=stream))
        ) as client:
            model = OpenRouterModel("anthropic/primary", api_key="fake", client=client)
            events = [
                event
                async for event in model.stream(
                    ModelRequest(messages=(Message.from_text(MessageRole.USER, "hello"),)),
                    context=RunContext(agent_id="stream", deps=None),
                )
            ]
        terminal = events[-1]
        self.assertEqual(terminal.metadata["resolved_model"], "openai/fallback-test")
        self.assertEqual(terminal.metadata["upstream_provider"], "OpenAI")
        self.assertTrue(terminal.metadata["fallback_used"])
        self.assertEqual(terminal.metadata["route_attempt"], 2)
        self.assertNotIn("PRIVATE", json.dumps(terminal.metadata))

    async def test_guardrail_403_is_not_misclassified_as_authentication(self):
        payload = {
            "error": {
                "code": 403,
                "message": "PRIVATE BLOCK DETAILS",
                "metadata": {"error_type": "invalid_prompt"},
            },
            "openrouter_metadata": {
                "strategy": "direct",
                "attempt": 1,
                "summary": "PRIVATE",
                "endpoints": {
                    "available": [
                        {
                            "provider": "Anthropic",
                            "model": "anthropic/primary",
                            "selected": True,
                        }
                    ]
                },
            },
        }
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(403, json=payload))
        ) as client:
            model = OpenRouterModel("anthropic/primary", api_key="fake", client=client)
            with self.assertRaises(ModelResponseError) as caught:
                await model.generate(
                    ModelRequest(messages=(Message.from_text(MessageRole.USER, "hello"),)),
                    context=RunContext(agent_id="error", deps=None),
                )
        self.assertEqual(caught.exception.metadata["error_type"], "invalid_prompt")
        self.assertEqual(caught.exception.metadata["upstream_provider"], "Anthropic")
        self.assertNotIn("PRIVATE", str(caught.exception))

        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(403, json=payload))
        ) as client:
            model = OpenRouterModel("anthropic/primary", api_key="fake", client=client)
            sink = MemoryEventSink()
            definition = AgentDefinition(
                id="routing-error",
                version="1.0.0",
                instructions="Answer",
                model=ModelRef(provider="openrouter", name="anthropic/primary"),
            )
            await Runner(model, events=EventBus([sink])).run(definition, "hello")
        failed = next(
            event for event in sink.events if event.event_type is EventType.MODEL_REQUEST_FAILED
        )
        self.assertEqual(failed.payload["error_type"], "ModelResponseError")
        self.assertEqual(failed.payload["provider_error_type"], "invalid_prompt")
        self.assertEqual(failed.payload["upstream_provider"], "Anthropic")
