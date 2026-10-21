"""Contract tests over real HTTPX request/response objects, no network."""

import json
import os
import unittest
from unittest.mock import patch

import httpx

from pyagentskit import (
    AgentDefinition,
    AudioContent,
    ImageContent,
    Message,
    MessageRole,
    ModelCapabilities,
    ModelRef,
    ModelRequest,
    RunContext,
    ToolDefinition,
    ToolRegistry,
    tool,
)
from pyagentskit.exceptions import (
    CapabilityError,
    ConfigurationError,
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from pyagentskit.providers._http import HttpTransport
from pyagentskit.providers._mapping import strict_schema, wire_name
from pyagentskit.providers.openai import OpenAIModel
from pyagentskit.runtime import Runner

CTX = RunContext(agent_id="test", deps=None)
REQ = ModelRequest(messages=(Message.from_text(MessageRole.USER, "hello"),))
TOOL = ToolDefinition(name="math.add", description="Add", input_schema={"type": "object"})


def raw(text="hello", **kwargs):
    return {
        "id": "r1",
        "model": "resolved",
        "choices": [{"message": {"content": text}, "finish_reason": "stop"}],
        **kwargs,
    }


def sse(*chunks):
    return "".join("data: " + json.dumps(c) + "\n\n" for c in chunks) + "data: [DONE]\n\n"


class ProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_and_usage(self):
        def handler(request):
            self.assertEqual(request.headers["authorization"], "Bearer test-key")
            body = json.loads(request.content)
            self.assertEqual(body["model"], "configured")
            return httpx.Response(
                200,
                json=raw(
                    usage={
                        "prompt_tokens": 10,
                        "completion_tokens": 3,
                        "prompt_tokens_details": {"cached_tokens": 4},
                    }
                ),
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model = OpenAIModel("configured", api_key="test-key", client=client)
            result = await model.generate(REQ, context=CTX)
            self.assertEqual(result.usage.input_tokens, 10)
            self.assertEqual(result.usage.cached_input_tokens, 4)
            self.assertEqual(result.model, "resolved")
            await model.aclose()
            self.assertFalse(client.is_closed)

    async def test_runner_real_wire_tool_cycle(self):
        requests = []

        @tool(name="math.add")
        def add(value: int) -> int:
            """Increment."""
            return value + 1

        def handler(request):
            body = json.loads(request.content)
            requests.append(body)
            if len(requests) == 1:
                name = body["tools"][0]["function"]["name"]
                return httpx.Response(
                    200,
                    json={
                        "id": "r1",
                        "model": "m",
                        "choices": [
                            {
                                "finish_reason": "tool_calls",
                                "message": {
                                    "content": None,
                                    "tool_calls": [
                                        {
                                            "id": "c1",
                                            "function": {"name": name, "arguments": '{"value":2}'},
                                        }
                                    ],
                                },
                            }
                        ],
                    },
                )
            assistant = body["messages"][-2]
            self.assertIsNone(assistant["content"])
            self.assertEqual(assistant["tool_calls"][0]["id"], "c1")
            self.assertEqual(body["messages"][-1]["tool_call_id"], "c1")
            return httpx.Response(200, json=raw("3"))

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model = OpenAIModel("m", api_key="fake", client=client)
            agent = AgentDefinition(
                id="test",
                version="1.0.0",
                instructions="Help",
                model=ModelRef(provider="openai", name="m"),
                tools=("math.add",),
            )
            result = await Runner(model, tools=ToolRegistry([add])).run(agent, "add")
            self.assertEqual(result.output, "3")

    async def test_error_statuses(self):
        for status, kind in [
            (401, ModelAuthenticationError),
            (403, ModelAuthenticationError),
            (429, ModelRateLimitError),
            (408, ModelTimeoutError),
            (500, ModelUnavailableError),
            (400, ModelResponseError),
            (302, ModelResponseError),
        ]:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(
                    lambda req, status=status: httpx.Response(status, json={"secret": "PRIVATE"})
                )
            ) as client:
                model = OpenAIModel("m", api_key="fake", client=client)
                with self.assertRaises(kind) as caught:
                    await model.generate(REQ, context=CTX)
                self.assertNotIn("PRIVATE", str(caught.exception))

    async def test_network_errors(self):
        for exc, kind in [
            (httpx.ReadTimeout("private"), ModelTimeoutError),
            (httpx.ConnectError("private"), ModelUnavailableError),
        ]:

            def fail(req, exc=exc):
                raise exc

            async with httpx.AsyncClient(transport=httpx.MockTransport(fail)) as client:
                model = OpenAIModel("m", api_key="fake", client=client)
                with self.assertRaises(kind):
                    await model.generate(REQ, context=CTX)
                with self.assertRaises(kind):
                    _ = [e async for e in model.stream(REQ, context=CTX)]

    async def test_bounded_retry(self):
        for header in ["0", "invalid"]:
            count = 0

            def handler(req, header=header):
                nonlocal count
                count += 1
                if count == 1:
                    return httpx.Response(429, headers={"retry-after": header})
                return httpx.Response(200, json=raw())

            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                model = OpenAIModel("m", api_key="fake", retries=1, client=client)
                await model.generate(REQ, context=CTX)
                self.assertEqual(count, 2)

    async def test_malformed_response(self):
        for body in [[], {}, {"error": {}}, {"choices": []}, raw(usage={"prompt_tokens": -1})]:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda req, body=body: httpx.Response(200, json=body))
            ) as client:
                with self.assertRaises(ModelResponseError):
                    await OpenAIModel("m", api_key="fake", client=client).generate(REQ, context=CTX)
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, text="not-json"))
        ) as client:
            with self.assertRaises(ModelResponseError):
                await OpenAIModel("m", api_key="fake", client=client).generate(REQ, context=CTX)

    async def test_stream_text_tool_usage(self):
        chunks = sse(
            {"choices": [{"delta": {"content": "Hi"}}]},
            {
                "choices": [
                    {
                        "delta": {
                            "tool_calls": [
                                {
                                    "index": 0,
                                    "id": "c1",
                                    "function": {
                                        "name": wire_name("math.add"),
                                        "arguments": '{"x":',
                                    },
                                }
                            ]
                        }
                    }
                ]
            },
            {
                "choices": [
                    {
                        "delta": {"tool_calls": [{"index": 0, "function": {"arguments": "2}"}}]},
                        "finish_reason": "tool_calls",
                    }
                ]
            },
            {"choices": [], "usage": {"prompt_tokens": 2, "completion_tokens": 1}},
        )
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, text=chunks))
        ) as client:
            model = OpenAIModel("m", api_key="fake", client=client)
            request = REQ.model_copy(update={"tools": (TOOL,)})
            events = [e async for e in model.stream(request, context=CTX)]
            self.assertEqual(events[-2].tool_call.name, "math.add")
            self.assertEqual(events[-2].tool_call.arguments, {"x": 2})
            self.assertEqual(events[-1].type.value, "completed")

    async def test_stream_errors_and_ndjson(self):
        for text in [
            "data: invalid\n\n",
            'data: {"error":{}}\n\n',
            sse({"choices": [{"delta": {}, "finish_reason": "length"}]}),
            sse({"choices": []}),
            "data: []\n\n",
        ]:
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda req, text=text: httpx.Response(200, text=text))
            ) as client:
                with self.assertRaises(ModelResponseError):
                    _ = [
                        e
                        async for e in OpenAIModel("m", api_key="fake", client=client).stream(
                            REQ, context=CTX
                        )
                    ]
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, text='\n{"done":true}\n'))
        ) as client:
            transport = HttpTransport("http://localhost:11434", {}, client=client)
            self.assertEqual(
                [x async for x in transport.stream("/chat", {}, ndjson=True)], [{"done": True}]
            )

    async def test_refusal(self):
        body = raw()
        body["choices"][0]["message"] = {"refusal": "No", "content": None}
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, json=body))
        ) as client:
            result = await OpenAIModel("m", api_key="fake", client=client).generate(
                REQ, context=CTX
            )
            self.assertEqual(result.finish_reason.value, "content_filter")

    async def test_schema_settings_and_modalities(self):
        model = OpenAIModel("m", api_key="fake")
        try:
            req = REQ.model_copy(
                update={
                    "output_schema": {
                        "type": "object",
                        "properties": {"answer": {"type": "integer"}},
                        "required": ["answer"],
                    },
                    "settings": {"max_output_tokens": 20, "temperature": 0.1},
                }
            )
            body = model._body(req)
            self.assertEqual(body["max_completion_tokens"], 20)
            self.assertFalse(
                body["response_format"]["json_schema"]["schema"]["additionalProperties"]
            )
            image = Message(
                role=MessageRole.USER, content=(ImageContent(uri="https://example.org/i"),)
            )
            self.assertEqual(
                model._body(ModelRequest(messages=(image,)))["messages"][0]["content"][0]["type"],
                "image_url",
            )
            audio = Message(role=MessageRole.USER, content=(AudioContent(uri="x"),))
            with self.assertRaises(CapabilityError):
                model._body(ModelRequest(messages=(audio,)))
            with self.assertRaises(CapabilityError):
                model._body(REQ.model_copy(update={"settings": {"messages": []}}))
        finally:
            await model.aclose()
        limited = OpenAIModel("m", api_key="fake", capabilities=ModelCapabilities())
        try:
            for req in [
                REQ.model_copy(update={"tools": (TOOL,)}),
                REQ.model_copy(update={"output_schema": {"type": "string"}}),
            ]:
                with self.assertRaises(CapabilityError):
                    limited._body(req)
            with self.assertRaises(CapabilityError):
                limited._body(REQ, stream=True)
        finally:
            await limited.aclose()

    def test_configuration_and_strict_schema(self):
        with patch.dict(os.environ, {}, clear=True), self.assertRaises(ConfigurationError):
            OpenAIModel("m")
        with self.assertRaises(ConfigurationError):
            OpenAIModel("", api_key="fake")
        with self.assertRaises(ConfigurationError):
            OpenAIModel("m", api_key="   ")
        for url in [
            "http://external.org",
            "https://user:pass@host",
            "https://host?key=secret",
            "bad",
        ]:
            with self.assertRaises(ConfigurationError):
                HttpTransport(url, {})
        with self.assertRaises(ConfigurationError):
            HttpTransport("https://host", {}, timeout=0)
        for schema in [
            {"type": "object", "properties": {"x": {"type": "string"}}},
            {"type": "object", "additionalProperties": {"type": "string"}},
        ]:
            with self.assertRaises(CapabilityError):
                strict_schema(schema)

    async def test_async_context_manager_and_normalized_model_name(self):
        model = OpenAIModel("  configured  ", api_key="fake")
        client = model._http.client
        async with model as entered:
            self.assertIs(entered, model)
            self.assertEqual(model.model, "configured")
        self.assertTrue(client.is_closed)


@unittest.skipUnless(
    os.getenv("PYAGENTSKIT_OPENAI_LIVE") == "1" or os.getenv("PYAGENTSKIT_LIVE_OPENAI") == "1",
    "Live calls are opt-in",
)
class LiveOpenAI(unittest.IsolatedAsyncioTestCase):
    async def test_text(self):
        model = OpenAIModel(os.environ["PYAGENTSKIT_OPENAI_MODEL"])
        try:
            result = await model.generate(
                REQ.model_copy(update={"settings": {"max_output_tokens": 64}}), context=CTX
            )
            self.assertTrue(result.content)
        finally:
            await model.aclose()
