import asyncio
import json
import os
import unittest

import httpx

from pyagentskit import Message, MessageRole, ModelRequest, RunContext, ToolCall
from pyagentskit.exceptions import ModelResponseError
from pyagentskit.providers._mapping import wire_name
from pyagentskit.providers.anthropic import AnthropicModel
from pyagentskit.providers.google import GoogleModel
from pyagentskit.providers.ollama import OllamaModel
from pyagentskit.providers.openai import OpenAIModel
from pyagentskit.providers.xai import XAIModel

CTX = RunContext(agent_id="test", deps=None)
REQ = ModelRequest(messages=(Message.from_text(MessageRole.USER, "Reply hello"),))


class Regressions(unittest.IsolatedAsyncioTestCase):
    async def test_openai_stream_refusal(self):
        payload = 'data: {"choices":[{"delta":{"refusal":"no"},"finish_reason":"stop"}]}\n\n'
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(lambda req: httpx.Response(200, text=payload))
        ) as client:
            with self.assertRaises(ModelResponseError):
                _ = [
                    e
                    async for e in OpenAIModel("m", api_key="fake", client=client).stream(
                        REQ, context=CTX
                    )
                ]

    async def test_cancellation_propagates_without_retry(self):
        started = asyncio.Event()
        attempts = 0

        async def handler(req):
            nonlocal attempts
            attempts += 1
            started.set()
            await asyncio.Event().wait()

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            model = OpenAIModel("m", api_key="fake", client=client, retries=3)
            task = asyncio.create_task(model.generate(REQ, context=CTX))
            await started.wait()
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task
            self.assertEqual(attempts, 1)

    async def test_google_native_call_id_replayed(self):
        call = ToolCall(id="native-id", name="math.add", arguments={})
        assistant = Message(
            role=MessageRole.ASSISTANT,
            tool_calls=(call,),
            metadata={
                "google_parts": [
                    {
                        "functionCall": {
                            "id": "native-id",
                            "name": wire_name("math.add"),
                            "args": {},
                        },
                        "thoughtSignature": "opaque",
                    }
                ]
            },
        )
        result = Message.from_text(MessageRole.TOOL, "ok", name="math.add", tool_call_id=call.id)
        model = GoogleModel("m", api_key="fake")
        try:
            body = model._body(ModelRequest(messages=(*REQ.messages, assistant, result)))
            self.assertEqual(
                body["contents"][-1]["parts"][0]["functionResponse"]["id"], "native-id"
            )
            self.assertNotIn("x-goog-api-key", json.dumps(body))
        finally:
            await model.aclose()


class LiveNativeProviders(unittest.IsolatedAsyncioTestCase):
    async def check_live(self, cls):
        prefix = "PYAGENTSKIT_" + cls.provider.upper()
        if os.getenv(prefix + "_LIVE") != "1":
            self.skipTest("Real provider call requires explicit opt-in")
        model = cls(os.environ[prefix + "_MODEL"])
        try:
            result = await model.generate(
                REQ.model_copy(update={"settings": {"max_output_tokens": 64}}), context=CTX
            )
            self.assertTrue(result.content)
        finally:
            await model.aclose()

    async def test_anthropic(self):
        await self.check_live(AnthropicModel)

    async def test_google(self):
        await self.check_live(GoogleModel)

    async def test_xai(self):
        await self.check_live(XAIModel)

    async def test_ollama(self):
        await self.check_live(OllamaModel)
