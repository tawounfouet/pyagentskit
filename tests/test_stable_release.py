import unittest

from pyagentskit import (
    AgentDefinition,
    CapabilityError,
    FinishReason,
    Model,
    ModelRef,
    ModelResponse,
    RunStatus,
    TextContent,
)
from pyagentskit.providers.anthropic import AnthropicModel
from pyagentskit.providers.google import GoogleModel
from pyagentskit.providers.ollama import OllamaModel
from pyagentskit.providers.openai import OpenAIModel
from pyagentskit.providers.xai import XAIModel
from pyagentskit.runtime import Runner


def agent(provider: str = "openai", model: str = "configured") -> AgentDefinition:
    return AgentDefinition(
        id="stable",
        version="1.0.0",
        instructions="Help",
        model=ModelRef(provider=provider, name=model),
    )


class StubOpenAIModel(OpenAIModel):
    async def generate(self, request, *, context):
        return ModelResponse(
            id="response-1",
            model=self.model,
            content=(TextContent(text="done"),),
            finish_reason=FinishReason.STOP,
            metadata={
                "provider": self.provider,
                "requested_model": self.model,
                "resolved_model": self.model,
            },
        )


class StableRuntimePreflightTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_provider_adapters_conform_to_model_port(self):
        models = [
            OpenAIModel("m", api_key="fake"),
            AnthropicModel("m", api_key="fake"),
            GoogleModel("m", api_key="fake"),
            XAIModel("m", api_key="fake"),
            OllamaModel("m"),
        ]
        try:
            for model in models:
                self.assertIsInstance(model, Model)
                self.assertEqual(model.capabilities.metadata["source"], "adapter_default")
                self.assertFalse(model.capabilities.metadata["model_verified"])
        finally:
            for model in models:
                await model.aclose()

    async def test_declared_provider_and_model_must_match_adapter(self):
        model = StubOpenAIModel("configured", api_key="fake")
        try:
            for definition in (
                agent(provider="anthropic"),
                agent(model="different"),
            ):
                with self.assertRaises(CapabilityError):
                    await Runner(model).run(definition, "hello")
            result = await Runner(model).run(agent(), "hello")
            self.assertEqual(result.status, RunStatus.COMPLETED)
        finally:
            await model.aclose()


if __name__ == "__main__":
    unittest.main()
