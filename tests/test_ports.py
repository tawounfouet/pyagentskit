from __future__ import annotations

import unittest
from collections.abc import AsyncIterator
from typing import Any

from pyagentskit import (
    AgentEvent,
    EventSink,
    Model,
    ModelCapabilities,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    RunContext,
    SecretProvider,
    Tool,
    ToolDefinition,
    ToolResult,
)


class DummyModel:
    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities()

    async def generate(
        self,
        request: ModelRequest,
        *,
        context: RunContext[Any],
    ) -> ModelResponse:
        raise NotImplementedError

    async def _stream(
        self,
        request: ModelRequest,
        *,
        context: RunContext[Any],
    ) -> AsyncIterator[ModelStreamEvent]:
        if False:
            yield ModelStreamEvent.model_construct()

    def stream(
        self,
        request: ModelRequest,
        *,
        context: RunContext[Any],
    ) -> AsyncIterator[ModelStreamEvent]:
        return self._stream(request, context=context)


class DummyTool:
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="example.tool",
            description="Example.",
            input_schema={"type": "object"},
        )

    async def invoke(
        self,
        arguments: dict[str, Any],
        *,
        context: RunContext[Any],
    ) -> ToolResult:
        raise NotImplementedError


class DummySink:
    async def emit(self, event: AgentEvent) -> None:
        return None


class DummySecrets:
    async def get_secret(self, name: str) -> str | None:
        return None


class PortTests(unittest.TestCase):
    def test_structural_runtime_protocols(self) -> None:
        self.assertIsInstance(DummyModel(), Model)
        self.assertIsInstance(DummyTool(), Tool)
        self.assertIsInstance(DummySink(), EventSink)
        self.assertIsInstance(DummySecrets(), SecretProvider)


if __name__ == "__main__":
    unittest.main()
