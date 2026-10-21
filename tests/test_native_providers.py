"""Native wire contracts tested with real HTTPX MockTransport, never network."""

import json
import os
import unittest
from unittest.mock import patch

import httpx

from pyagentskit import (
    AgentDefinition,
    ImageContent,
    Message,
    MessageRole,
    ModelCapabilities,
    ModelRef,
    ModelRequest,
    RunContext,
    ToolRegistry,
    tool,
)
from pyagentskit.exceptions import CapabilityError, ConfigurationError, ModelResponseError
from pyagentskit.providers._mapping import wire_name
from pyagentskit.providers.anthropic import AnthropicModel
from pyagentskit.providers.google import GoogleModel
from pyagentskit.providers.ollama import OllamaModel
from pyagentskit.providers.xai import XAIModel
from pyagentskit.runtime import Runner

CTX = RunContext(agent_id="test", deps=None)
REQ = ModelRequest(
    messages=(
        Message.from_text(MessageRole.SYSTEM, "Help"),
        Message.from_text(MessageRole.USER, "Hi"),
    )
)
SCHEMA = {"type": "object", "properties": {"value": {"type": "integer"}}, "required": ["value"]}


@tool(name="math.add")
def add(value: int) -> int:
    """Increment the number."""
    return value + 1


def response(provider, *, calls=False):
    if provider == "anthropic":
        blocks = (
            [{"type": "tool_use", "id": "c1", "name": wire_name("math.add"), "input": {"value": 2}}]
            if calls
            else [{"type": "text", "text": "3"}]
        )
        return {
            "id": "r1",
            "model": "resolved",
            "content": blocks,
            "stop_reason": "tool_use" if calls else "end_turn",
            "usage": {
                "input_tokens": 4,
                "output_tokens": 2,
                "cache_read_input_tokens": 1,
                "cache_creation_input_tokens": 3,
            },
        }
    if provider == "google":
        parts = (
            [
                {
                    "functionCall": {"name": wire_name("math.add"), "args": {"value": 2}},
                    "thoughtSignature": "OPAQUE_SIGNATURE",
                }
            ]
            if calls
            else [{"text": "3"}]
        )
        return {
            "responseId": "r1",
            "modelVersion": "resolved",
            "candidates": [{"content": {"parts": parts}, "finishReason": "STOP"}],
            "usageMetadata": {
                "promptTokenCount": 4,
                "candidatesTokenCount": 2,
                "thoughtsTokenCount": 1,
            },
        }
    if provider == "ollama":
        return {
            "model": "resolved",
            "message": {
                "content": "" if calls else "3",
                "tool_calls": [
                    {"function": {"name": wire_name("math.add"), "arguments": {"value": 2}}}
                ]
                if calls
                else [],
            },
            "done": True,
            "done_reason": "stop",
            "eval_count": 2,
            "prompt_eval_count": 4,
        }
    return {
        "id": "r1",
        "model": "resolved",
        "choices": [{"finish_reason": "stop", "message": {"content": "3"}}],
    }


def sse(items):
    return "".join("data: " + json.dumps(x) + "\n\n" for x in items)


def chunks(provider, *, calls=False):
    if provider == "anthropic":
        data = response(provider, calls=calls)
        block = data["content"][0]
        return sse(
            [
                {
                    "type": "message_start",
                    "message": {"id": "r", "model": "resolved", "usage": {"input_tokens": 4}},
                },
                {
                    "type": "content_block_start",
                    "index": 0,
                    "content_block": {**block, **({"input": {}} if calls else {"text": ""})},
                },
                {
                    "type": "content_block_delta",
                    "index": 0,
                    "delta": {"type": "input_json_delta", "partial_json": '{"value":2}'}
                    if calls
                    else {"type": "text_delta", "text": "3"},
                },
                {
                    "type": "message_delta",
                    "delta": {"stop_reason": data["stop_reason"]},
                    "usage": {"output_tokens": 2},
                },
                {"type": "message_stop"},
            ]
        )
    if provider == "google":
        return sse([response(provider, calls=calls)])
    return json.dumps(response(provider, calls=calls)) + "\n"


class NativeProviderTests(unittest.IsolatedAsyncioTestCase):
    async def test_text_wire_and_usage(self):
        for cls in (AnthropicModel, GoogleModel, OllamaModel, XAIModel):
            requests = []

            def handler(req, cls=cls, requests=requests):
                requests.append(req)
                return httpx.Response(200, json=response(cls.provider))

            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                model = cls("test-model", api_key="fake", client=client)
                result = await model.generate(REQ, context=CTX)
                self.assertEqual(result.content[0].text, "3")
                self.assertEqual(result.metadata["provider"], cls.provider)
                self.assertEqual(result.metadata["resolved_model"], "resolved")
                self.assertEqual(result.model, "resolved")
                request = requests[0]
                if cls is AnthropicModel:
                    self.assertEqual(request.url.path, "/v1/messages")
                    self.assertEqual(request.headers["anthropic-version"], "2023-06-01")
                    self.assertEqual(result.usage.input_tokens, 8)
                elif cls is GoogleModel:
                    self.assertIn(":generateContent", request.url.path)
                    self.assertNotIn("key=", str(request.url))
                    self.assertEqual(request.headers["x-goog-api-key"], "fake")
                    self.assertEqual(result.usage.output_tokens, 3)
                elif cls is OllamaModel:
                    self.assertEqual(request.url.path, "/api/chat")
                else:
                    self.assertEqual(request.url.host, "api.x.ai")
                await model.aclose()
                self.assertFalse(client.is_closed)

    async def test_full_native_tool_cycles_and_opaque_replay(self):
        for cls in (AnthropicModel, GoogleModel, OllamaModel):
            seen = []

            def handler(req, cls=cls, seen=seen):
                body = json.loads(req.content)
                seen.append(body)
                if len(seen) == 1:
                    return httpx.Response(200, json=response(cls.provider, calls=True))
                if cls is AnthropicModel:
                    self.assertEqual(body["messages"][-1]["content"][0]["tool_use_id"], "c1")
                    self.assertEqual(body["messages"][-2]["content"][0]["type"], "tool_use")
                elif cls is GoogleModel:
                    self.assertEqual(
                        body["contents"][-2]["parts"][0]["thoughtSignature"], "OPAQUE_SIGNATURE"
                    )
                    self.assertIn("functionResponse", body["contents"][-1]["parts"][0])
                else:
                    self.assertEqual(body["messages"][-1]["tool_name"], wire_name("math.add"))
                return httpx.Response(200, json=response(cls.provider))

            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                model = cls("test-model", api_key="fake", client=client)
                agent = AgentDefinition(
                    id="test",
                    version="1.0.0",
                    instructions="Help",
                    model=ModelRef(provider=cls.provider, name="test-model"),
                    tools=("math.add",),
                )
                result = await Runner(model, tools=ToolRegistry([add])).run(agent, "Add")
                self.assertEqual(result.output, "3", result)
                self.assertEqual(len(seen), 2)

    async def test_structured_output_and_settings(self):
        for cls in (AnthropicModel, GoogleModel, OllamaModel):
            model = cls("m", api_key="fake")
            try:
                req = REQ.model_copy(
                    update={
                        "output_schema": SCHEMA,
                        "settings": {"max_output_tokens": 100, "temperature": 0.1, "top_p": 0.9},
                    }
                )
                body = model._body(req)
                field = {
                    AnthropicModel: "output_config",
                    GoogleModel: "generationConfig",
                    OllamaModel: "format",
                }[cls]
                self.assertIn(field, body)
                self.assertNotIn("fake", json.dumps(body))
                image = ModelRequest(
                    messages=(
                        Message(
                            role=MessageRole.USER,
                            content=(ImageContent(uri="https://example.org/image"),),
                        ),
                    )
                )
                with self.assertRaises(CapabilityError):
                    await model.generate(image, context=CTX)
            finally:
                await model.aclose()

    async def test_stream_text_and_tools(self):
        for cls in (AnthropicModel, GoogleModel, OllamaModel):
            for calls in (False, True):
                payload = chunks(cls.provider, calls=calls)
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(
                        lambda req, payload=payload: httpx.Response(200, text=payload)
                    )
                ) as client:
                    model = cls("m", api_key="fake", client=client)
                    req = REQ.model_copy(update={"tools": (add.definition,)}) if calls else REQ
                    events = [e async for e in model.stream(req, context=CTX)]
                    self.assertEqual(events[-1].type.value, "completed")
                    self.assertIn("response", events[-1].metadata)
                    if calls:
                        call = next(e.tool_call for e in events if e.tool_call)
                        self.assertEqual(call.arguments, {"value": 2})
                        self.assertEqual(call.name, "math.add")
                    else:
                        self.assertEqual("".join(e.delta or "" for e in events), "3")

    async def test_native_malformed_and_truncated(self):
        for cls in (AnthropicModel, GoogleModel, OllamaModel):
            for payload in ("", 'data: {"error":{}}\n\n'):
                async with httpx.AsyncClient(
                    transport=httpx.MockTransport(
                        lambda req, payload=payload: httpx.Response(200, text=payload)
                    )
                ) as client:
                    with self.assertRaises(ModelResponseError):
                        _ = [
                            e
                            async for e in cls("m", api_key="fake", client=client).stream(
                                REQ, context=CTX
                            )
                        ]
            async with httpx.AsyncClient(
                transport=httpx.MockTransport(lambda req: httpx.Response(200, json={"message": []}))
            ) as client:
                with self.assertRaises(ModelResponseError):
                    await cls("m", api_key="fake", client=client).generate(REQ, context=CTX)

    async def test_limits_and_unsupported_settings(self):
        for cls in (AnthropicModel, GoogleModel, OllamaModel):
            model = cls("m", api_key="fake", capabilities=ModelCapabilities())
            try:
                for req in (
                    REQ.model_copy(update={"tools": (add.definition,)}),
                    REQ.model_copy(update={"output_schema": SCHEMA}),
                    REQ.model_copy(update={"settings": {"unsafe": True}}),
                ):
                    with self.assertRaises(CapabilityError):
                        await model.generate(req, context=CTX)
                with self.assertRaises(CapabilityError):
                    _ = [e async for e in model.stream(REQ, context=CTX)]
            finally:
                await model.aclose()
        model = GoogleModel("m", api_key="fake")
        try:
            with self.assertRaises(CapabilityError):
                model._body(
                    REQ.model_copy(update={"tools": (add.definition,), "output_schema": SCHEMA})
                )
        finally:
            await model.aclose()
        model = AnthropicModel("m", api_key="fake")
        try:
            with self.assertRaises(CapabilityError):
                model._body(REQ.model_copy(update={"settings": {"seed": 1}}))
        finally:
            await model.aclose()

    async def test_local_ollama_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            model = OllamaModel("local")
            self.assertEqual(model._http._headers, {})
            await model.aclose()
            for cls in (AnthropicModel, GoogleModel):
                with self.assertRaises(ConfigurationError):
                    cls("m")
                with self.assertRaises(ConfigurationError):
                    cls("m", api_key="   ")
            with self.assertRaises(ConfigurationError):
                OllamaModel("")

    async def test_native_async_context_manager(self):
        model = AnthropicModel("  model-name  ", api_key="fake")
        client = model._http.client
        async with model as entered:
            self.assertIs(entered, model)
            self.assertEqual(model.model, "model-name")
        self.assertTrue(client.is_closed)

    async def test_anthropic_thinking_stream(self):
        items = [
            {"type": "message_start", "message": {"id": "r", "model": "m"}},
            {"type": "content_block_start", "index": 0, "content_block": {"type": "thinking"}},
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "thinking_delta", "thinking": "private reasoning"},
            },
            {
                "type": "content_block_delta",
                "index": 0,
                "delta": {"type": "signature_delta", "signature": "opaque"},
            },
            {
                "type": "content_block_start",
                "index": 1,
                "content_block": {"type": "text", "text": "answer"},
            },
            {"type": "message_delta", "delta": {"stop_reason": "end_turn"}},
            {"type": "message_stop"},
        ]
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, text=sse(items)))
        ) as client:
            model = AnthropicModel("m", api_key="fake", client=client)
            events = [e async for e in model.stream(REQ, context=CTX)]
            final = events[-1].metadata["response"]
            self.assertEqual(final["metadata"]["anthropic_content"][0]["signature"], "opaque")
            self.assertNotIn("private reasoning", "".join(e.delta or "" for e in events))

    async def test_native_refusal_and_length(self):
        for cls in (AnthropicModel, GoogleModel, OllamaModel):
            data = response(cls.provider)
            if cls is AnthropicModel:
                data["stop_reason"] = "max_tokens"
            elif cls is GoogleModel:
                data["candidates"][0]["finishReason"] = "MAX_TOKENS"
            else:
                data["done_reason"] = "length"
            model = cls("m", api_key="fake")
            try:
                self.assertEqual(model._response(data, REQ).finish_reason.value, "length")
            finally:
                await model.aclose()
