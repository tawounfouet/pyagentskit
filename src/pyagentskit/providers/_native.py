"""Shared lifecycle for native REST adapters; wire formats remain separate."""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator
from typing import Any

from ..exceptions import CapabilityError, ConfigurationError, ModelResponseError
from ..models import (
    FinishReason,
    ModelCapabilities,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
)
from ..runs import RunContext
from ._http import HttpTransport


class NativeModel(ABC):
    provider: str
    endpoint: str
    key_variable: str
    path: str

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        client: Any = None,
        base_url: str | None = None,
        timeout: float = 60,
        retries: int = 0,
        capabilities: ModelCapabilities | None = None,
    ) -> None:
        normalized_model = model.strip()
        if not normalized_model:
            raise ConfigurationError("Model name is required")
        key = api_key or os.getenv(self.key_variable)
        if (not key or not key.strip()) and self.provider != "ollama":
            raise ConfigurationError(f"Set {self.key_variable} or provide api_key")
        self.model = normalized_model
        self._capabilities = capabilities or ModelCapabilities(
            tool_calling=True,
            structured_output=True,
            streaming=True,
            parallel_tool_calls=True,
            metadata={"source": "adapter_default", "model_verified": False},
        )
        headers = self._headers(key)
        self._http = HttpTransport(
            base_url or self.endpoint, headers, client=client, timeout=timeout, retries=retries
        )

    def _headers(self, key: str | None) -> dict[str, str]:
        if self.provider == "anthropic":
            return {"x-api-key": key or "", "anthropic-version": "2023-06-01"}
        if self.provider == "google":
            return {"x-goog-api-key": key or ""}
        return {"Authorization": f"Bearer {key}"} if key else {}

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._capabilities

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> NativeModel:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    def _check(self, request: ModelRequest, *, stream: bool = False) -> None:
        if request.tools and not self.capabilities.tool_calling:
            raise CapabilityError("Tool calling disabled")
        if request.output_schema and not self.capabilities.structured_output:
            raise CapabilityError("Structured output disabled")
        if stream and not self.capabilities.streaming:
            raise CapabilityError("Streaming disabled")
        if set(request.settings) - {"temperature", "top_p", "max_output_tokens", "seed"}:
            raise CapabilityError("Unsupported model setting")

    @abstractmethod
    def _body(self, request: ModelRequest, *, stream: bool = False) -> dict[str, Any]: ...

    @abstractmethod
    def _response(self, raw: dict[str, Any], request: ModelRequest) -> ModelResponse: ...

    async def generate(self, request: ModelRequest, *, context: RunContext[Any]) -> ModelResponse:
        self._check(request)
        body = self._body(request)
        raw = await self._http.post(self.path, body)
        try:
            return self._response(raw, request)
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            raise ModelResponseError("Malformed native provider response") from None

    @abstractmethod
    async def _stream_raw(
        self, request: ModelRequest
    ) -> AsyncIterator[ModelStreamEvent | dict[str, Any]]:
        yield {}  # pragma: no cover

    async def stream(
        self, request: ModelRequest, *, context: RunContext[Any]
    ) -> AsyncIterator[ModelStreamEvent]:
        self._check(request, stream=True)
        yield ModelStreamEvent(type=ModelStreamEventType.STARTED)
        final: ModelResponse | None = None
        try:
            async for item in self._stream_raw(request):
                if isinstance(item, ModelStreamEvent):
                    yield item
                else:
                    final = self._response(item, request)
            if final is None:
                raise ModelResponseError("Truncated native provider stream")
            if final.finish_reason not in {FinishReason.STOP, FinishReason.TOOL_CALLS}:
                raise ModelResponseError("Native stream did not complete successfully")
            for call in final.tool_calls:
                yield ModelStreamEvent(
                    type=ModelStreamEventType.TOOL_CALL_COMPLETED, tool_call=call
                )
            yield ModelStreamEvent(type=ModelStreamEventType.USAGE, usage=final.usage)
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            raise ModelResponseError("Malformed native provider stream") from None
        yield ModelStreamEvent(
            type=ModelStreamEventType.COMPLETED,
            metadata={"response": final.model_dump(mode="json")},
        )
