"""Deterministic scripted model implementing the common Model protocol."""

from collections.abc import AsyncIterator, Iterable
from typing import Any

from .exceptions import ModelResponseError
from .models import (
    ModelCapabilities,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
)
from .runs import RunContext


class FakeModel:
    """One script per test/run; exhausted scripts fail, never repeat silently."""

    def __init__(self, script: Iterable[ModelResponse | Exception]) -> None:
        self._script = tuple(script)
        self.requests: list[ModelRequest] = []
        self._index = 0

    @property
    def capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            tool_calling=True, structured_output=True, streaming=True, parallel_tool_calls=True
        )

    async def generate(self, request: ModelRequest, *, context: RunContext[Any]) -> ModelResponse:
        self.requests.append(request.model_copy(deep=True))
        if self._index >= len(self._script):
            raise ModelResponseError("FakeModel script exhausted")
        item = self._script[self._index]
        self._index += 1
        if isinstance(item, Exception):
            raise item
        return item.model_copy(deep=True)

    async def stream(
        self, request: ModelRequest, *, context: RunContext[Any]
    ) -> AsyncIterator[ModelStreamEvent]:
        yield ModelStreamEvent(type=ModelStreamEventType.STARTED)
        response = await self.generate(request, context=context)
        for part in response.content:
            if part.type == "text":
                yield ModelStreamEvent(type=ModelStreamEventType.TEXT_DELTA, delta=part.text)
        for call in response.tool_calls:
            yield ModelStreamEvent(type=ModelStreamEventType.TOOL_CALL_COMPLETED, tool_call=call)
        yield ModelStreamEvent(type=ModelStreamEventType.USAGE, usage=response.usage)
        yield ModelStreamEvent(type=ModelStreamEventType.COMPLETED)
