"""OpenRouter adapter contract tests over an HTTPX mock transport."""

import json
import os
import unittest
from decimal import Decimal
from unittest.mock import patch

import httpx

from pyagentskit import (
    AgentDefinition,
    Message,
    MessageRole,
    ModelRef,
    ModelRequest,
    ModelStreamEventType,
    RunContext,
    ToolDefinition,
)
from pyagentskit.exceptions import (
    ConfigurationError,
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from pyagentskit.providers._mapping import wire_name
from pyagentskit.providers.openrouter import OpenRouterModel
from pyagentskit.runtime import Runner

CTX = RunContext(agent_id="test", deps=None)
REQ = ModelRequest(messages=(Message.from_text(MessageRole.USER, "hello"),))
TOOL = ToolDefinition(name="math.add", description="Add", input_schema={"type": "object"})


def completion(**updates):
    value = {
        "id": "gen-1",
        "model": "anthropic/claude-test",
        "provider": "Anthropic",
        "choices": [{"message": {"content": "hello"}, "finish_reason": "stop"}],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 3,
            "prompt_tokens_details": {"cached_tokens": 2},
            "completion_tokens_details": {"reasoning_tokens": 1},
            "cost": 0.0012,
            "is_byok": False,
        },
    }
    value.update(updates)
    return value


def sse(*chunks):
    return "".join("data: " + json.dumps(chunk) + "\n\n" for chunk in chunks) + "data: [DONE]\n\n"


class OpenRouterProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_request_headers_policy_and_response_metadata(self):
        def handler(request):
            self.assertEqual(request.url.path, "/api/v1/chat/completions")
            self.assertEqual(request.headers["authorization"], "Bearer test-key")
            self.assertEqual(request.headers["http-referer"], "https://example.org")
            self.assertEqual(request.headers["x-openrouter-title"], "PyAgentsKit")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "anthropic/claude-test")
            self.assertEqual(
                body["provider"], {"allow_fallbacks": False, "require_parameters": True}
            )
            return httpx.Response(200, json=completion())

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model = OpenRouterModel(
                "anthropic/claude-test",
                api_key="test-key",
                app_url="https://example.org/",
                app_title=" PyAgentsKit ",
                client=client,
            )
            result = await model.generate(REQ, context=CTX)
            self.assertEqual(result.usage.estimated_cost_usd, Decimal("0.0012"))
            self.assertEqual(result.metadata["router"], "openrouter")
            self.assertEqual(result.metadata["generation_id"], "gen-1")
            self.assertEqual(result.metadata["requested_model"], "anthropic/claude-test")
            self.assertEqual(result.metadata["resolved_model"], "anthropic/claude-test")
            self.assertEqual(result.metadata["upstream_provider"], "Anthropic")
            self.assertFalse(result.metadata["fallback_used"])
            self.assertFalse(result.metadata["is_byok"])

    async def test_body_uses_openrouter_parameter_shapes(self):
        model = OpenRouterModel("openai/test", api_key="fake")
        try:
            request = REQ.model_copy(
                update={
                    "settings": {"max_output_tokens": 50},
                    "tools": (TOOL,),
                    "output_schema": {
                        "type": "object",
                        "properties": {"answer": {"type": "string"}},
                        "required": ["answer"],
                    },
                }
            )
            body = model._body(request, stream=True)
            self.assertEqual(body["max_tokens"], 50)
            self.assertNotIn("max_completion_tokens", body)
            self.assertNotIn("stream_options", body)
            self.assertNotIn("strict", body["tools"][0]["function"])
            self.assertTrue(body["response_format"]["json_schema"]["strict"])
        finally:
            await model.aclose()

    async def test_tool_call_and_stream_usage(self):
        tool_name = wire_name("math.add")
        body = completion(
            choices=[
                {
                    "message": {
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call-1",
                                "type": "function",
                                "function": {"name": tool_name, "arguments": '{"x": 2}'},
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=body))
        ) as client:
            model = OpenRouterModel("openai/test", api_key="fake", client=client)
            response = await model.generate(REQ.model_copy(update={"tools": (TOOL,)}), context=CTX)
            self.assertEqual(response.tool_calls[0].name, "math.add")

        stream = sse(
            {"choices": [{"delta": {"content": "Hi"}, "finish_reason": None}]},
            {
                "choices": [{"delta": {}, "finish_reason": "stop"}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1, "cost": 0.0001},
            },
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text=stream))
        ) as client:
            model = OpenRouterModel("openai/test", api_key="fake", client=client)
            events = [event async for event in model.stream(REQ, context=CTX)]
            usage = next(
                event.usage for event in events if event.type is ModelStreamEventType.USAGE
            )
            self.assertEqual(usage.estimated_cost_usd, Decimal("0.0001"))
            self.assertEqual(events[-1].type, ModelStreamEventType.COMPLETED)

    async def test_typed_errors_preserve_safe_metadata(self):
        cases = [
            (401, "authentication", ModelAuthenticationError),
            (429, "rate_limit_exceeded", ModelRateLimitError),
            (408, "timeout", ModelTimeoutError),
            (503, "provider_overloaded", ModelUnavailableError),
            (502, "provider_unavailable", ModelUnavailableError),
            (400, "invalid_request", ModelResponseError),
        ]
        for status, error_type, exception in cases:
            payload = {
                "error": {
                    "code": status,
                    "message": "PRIVATE PROMPT",
                    "metadata": {"error_type": error_type, "provider_code": "upstream"},
                },
                "openrouter_metadata": {
                    "strategy": "fallback",
                    "region": "iad",
                    "attempt": 2,
                    "summary": "PRIVATE ROUTER SUMMARY",
                },
            }
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request, status=status, payload=payload: httpx.Response(
                        status, json=payload
                    )
                )
            ) as client:
                model = OpenRouterModel("openai/test", api_key="fake", client=client)
                with self.assertRaises(exception) as caught:
                    await model.generate(REQ, context=CTX)
                self.assertEqual(caught.exception.metadata["error_type"], error_type)
                self.assertEqual(caught.exception.metadata["provider_code"], "upstream")
                self.assertEqual(caught.exception.metadata["route_attempt"], 2)
                self.assertTrue(caught.exception.metadata["fallback_used"])
                self.assertNotIn("PRIVATE", str(caught.exception))
                self.assertNotIn("message", caught.exception.metadata)

    async def test_errors_inside_success_and_stream_responses(self):
        payload = {
            "error": {
                "code": 429,
                "message": "limited",
                "metadata": {"error_type": "rate_limit_exceeded"},
            }
        }
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json=payload))
        ) as client:
            with self.assertRaises(ModelRateLimitError):
                await OpenRouterModel("openai/test", api_key="fake", client=client).generate(
                    REQ, context=CTX
                )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda request: httpx.Response(200, text=sse(payload)))
        ) as client:
            with self.assertRaises(ModelRateLimitError):
                _ = [
                    event
                    async for event in OpenRouterModel(
                        "openai/test", api_key="fake", client=client
                    ).stream(REQ, context=CTX)
                ]

    async def test_choice_error_and_malformed_cost(self):
        error = completion(
            choices=[
                {
                    "message": {"content": "partial"},
                    "finish_reason": "error",
                    "error": {
                        "code": 502,
                        "metadata": {"error_type": "provider_unavailable"},
                    },
                }
            ]
        )
        malformed = completion()
        malformed["usage"]["cost"] = "not-a-number"
        for payload, exception in [
            (error, ModelUnavailableError),
            (malformed, ModelResponseError),
        ]:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request, payload=payload: httpx.Response(200, json=payload)
                )
            ) as client:
                with self.assertRaises(exception):
                    await OpenRouterModel("openai/test", api_key="fake", client=client).generate(
                        REQ, context=CTX
                    )

    def test_configuration(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ConfigurationError):
            OpenRouterModel("openai/test")
        for model in ["", "unqualified", "/model", "provider/"]:
            with self.assertRaises(ConfigurationError):
                OpenRouterModel(model, api_key="fake")
        with self.assertRaises(ConfigurationError):
            OpenRouterModel("openai/test", api_key="   ")
        for app_url in ["http://example.org", "https://user@host", "https://host?q=secret"]:
            with self.assertRaises(ConfigurationError):
                OpenRouterModel("openai/test", api_key="fake", app_url=app_url)
        with self.assertRaises(ConfigurationError):
            OpenRouterModel("openai/test", api_key="fake", app_title="  ")
        with self.assertRaises(ConfigurationError):
            OpenRouterModel("openai/test", api_key="fake", allow_fallbacks="no")  # type: ignore[arg-type]

    async def test_runner_preflight_and_context_manager(self):
        async with (
            httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda request: httpx.Response(200, json=completion())
                )
            ) as client,
            OpenRouterModel("anthropic/claude-test", api_key="fake", client=client) as model,
        ):
            agent = AgentDefinition(
                id="router-test",
                version="1.0.0",
                instructions="Answer",
                model=ModelRef(provider="openrouter", name="anthropic/claude-test"),
            )
            result = await Runner(model).run(agent, "hello")
            self.assertEqual(result.output, "hello")


@unittest.skipUnless(os.getenv("PYAGENTSKIT_OPENROUTER_LIVE") == "1", "Live calls are opt-in")
class LiveOpenRouter(unittest.IsolatedAsyncioTestCase):
    async def test_text(self):
        async with OpenRouterModel(os.environ["PYAGENTSKIT_OPENROUTER_MODEL"]) as model:
            response = await model.generate(
                REQ.model_copy(update={"settings": {"max_output_tokens": 64}}), context=CTX
            )
            self.assertTrue(response.content)
