"""OpenAI Chat Completions adapter with native SSE streaming."""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from typing import Any

from ..exceptions import CapabilityError, ConfigurationError, ModelResponseError
from ..messages import TextContent
from ..models import (
    FinishReason,
    Modality,
    ModelCapabilities,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
)
from ..runs import RunContext
from ..tools import ToolCall
from ..usage import Usage
from ._http import HttpTransport
from ._mapping import arguments, original_name, strict_schema, wire_name


class OpenAIModel:
    """Specify a model explicitly; capabilities describe the selected deployment.

    No credentials, HTTP objects or SDK classes enter normalized results.
    Client injection supports HTTPX MockTransport; injected clients are not closed.
    """

    provider = "openai"
    endpoint = "https://api.openai.com/v1"
    key_variable = "OPENAI_API_KEY"

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
        if not key or not key.strip():
            raise ConfigurationError(f"Set {self.key_variable} or provide api_key")
        self.model = normalized_model
        self._capabilities = capabilities or ModelCapabilities(
            tool_calling=True,
            structured_output=True,
            streaming=True,
            parallel_tool_calls=True,
            input_modalities=(Modality.TEXT, Modality.IMAGE),
            metadata={"source": "adapter_default", "model_verified": False},
        )
        self._http = HttpTransport(
            base_url or self.endpoint,
            {"Authorization": f"Bearer {key}"},
            client=client,
            timeout=timeout,
            retries=retries,
        )

    @property
    def capabilities(self) -> ModelCapabilities:
        return self._capabilities

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> OpenAIModel:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    def _body(self, request: ModelRequest, *, stream: bool = False) -> dict[str, Any]:
        if request.tools and not self.capabilities.tool_calling:
            raise CapabilityError("Tool calling disabled for this model")
        if request.output_schema and not self.capabilities.structured_output:
            raise CapabilityError("Structured output disabled for this model")
        if stream and not self.capabilities.streaming:
            raise CapabilityError("Streaming disabled for this model")
        unknown = set(request.settings) - {"temperature", "top_p", "max_output_tokens", "seed"}
        if unknown:
            raise CapabilityError("Unsupported model settings")
        messages: list[dict[str, Any]] = []
        for message in request.messages:
            parts: list[dict[str, Any]] = []
            for part in message.content:
                if part.type == "text":
                    parts.append({"type": "text", "text": part.text})
                elif part.type == "image" and Modality.IMAGE in self.capabilities.input_modalities:
                    parts.append(
                        {"type": "image_url", "image_url": {"url": part.uri, "detail": part.detail}}
                    )
                else:
                    raise CapabilityError("Unsupported input modality")
            row: dict[str, Any] = {"role": message.role.value, "content": parts or None}
            if message.role.value == "tool":
                row["tool_call_id"] = message.tool_call_id
                if any(p["type"] != "text" for p in parts):
                    raise CapabilityError("Tool results must be text")
                row["content"] = "".join(p["text"] for p in parts)
            if message.tool_calls:
                row["tool_calls"] = [
                    {
                        "id": c.id,
                        "type": "function",
                        "function": {
                            "name": wire_name(c.name),
                            "arguments": json.dumps(c.arguments),
                        },
                    }
                    for c in message.tool_calls
                ]
            messages.append(row)
        body: dict[str, Any] = {"model": self.model, "messages": messages, "stream": stream}
        for key, value in request.settings.items():
            body["max_completion_tokens" if key == "max_output_tokens" else key] = value
        if request.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": wire_name(t.name),
                        "description": t.description,
                        "parameters": t.input_schema,
                        "strict": False,
                    },
                }
                for t in request.tools
            ]
        if request.output_schema:
            body["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": "agent_output",
                    "schema": strict_schema(request.output_schema),
                    "strict": True,
                },
            }
        if stream:
            body["stream_options"] = {"include_usage": True}
        return body

    @staticmethod
    def _usage(data: dict[str, Any]) -> Usage:
        return Usage(
            input_tokens=data.get("prompt_tokens", 0),
            output_tokens=data.get("completion_tokens", 0),
            cached_input_tokens=(data.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
            reasoning_tokens=(data.get("completion_tokens_details") or {}).get(
                "reasoning_tokens", 0
            ),
            model_calls=1,
        )

    def _stream_event_metadata(self, chunk: dict[str, Any]) -> dict[str, Any]:
        """Return safe adapter metadata to attach to the terminal stream event."""
        metadata: dict[str, Any] = {
            "provider": self.provider,
            "requested_model": self.model,
            "resolved_model": chunk.get("model", self.model),
        }
        if isinstance(chunk.get("id"), str):
            metadata["generation_id"] = chunk["id"]
        return metadata

    def _response(self, raw: dict[str, Any], request: ModelRequest) -> ModelResponse:
        choice = raw["choices"][0]
        message = choice["message"]
        calls = tuple(
            ToolCall(
                id=c["id"],
                name=original_name(c["function"]["name"], request),
                arguments=arguments(c["function"]["arguments"]),
            )
            for c in message.get("tool_calls", [])
        )
        reason = {
            "stop": FinishReason.STOP,
            "tool_calls": FinishReason.TOOL_CALLS,
            "length": FinishReason.LENGTH,
            "content_filter": FinishReason.CONTENT_FILTER,
        }.get(choice.get("finish_reason"), FinishReason.UNKNOWN)
        if calls:
            reason = FinishReason.TOOL_CALLS
        if message.get("refusal"):
            reason = FinishReason.CONTENT_FILTER
        text = message.get("content")
        return ModelResponse(
            id=raw["id"],
            model=raw.get("model", self.model),
            content=(TextContent(text=text),) if text else (),
            tool_calls=calls,
            finish_reason=reason,
            usage=self._usage(raw.get("usage") or {}),
            metadata={
                "provider": self.provider,
                "requested_model": self.model,
                "resolved_model": raw.get("model", self.model),
                "usage_reported": raw.get("usage") is not None,
            },
        )

    async def generate(self, request: ModelRequest, *, context: RunContext[Any]) -> ModelResponse:
        body = self._body(request)
        raw = await self._http.post("/chat/completions", body)
        try:
            return self._response(raw, request)
        except (ValueError, KeyError, TypeError, IndexError, AttributeError):
            raise ModelResponseError("Malformed provider response") from None

    async def stream(
        self, request: ModelRequest, *, context: RunContext[Any]
    ) -> AsyncIterator[ModelStreamEvent]:
        body = self._body(request, stream=True)
        yield ModelStreamEvent(type=ModelStreamEventType.STARTED)
        calls: dict[int, dict[str, str]] = {}
        finished = False
        stream_metadata: dict[str, Any] = {}
        try:
            async for chunk in self._http.stream("/chat/completions", body):
                stream_metadata.update(self._stream_event_metadata(chunk))
                if chunk.get("usage"):
                    yield ModelStreamEvent(
                        type=ModelStreamEventType.USAGE, usage=self._usage(chunk["usage"])
                    )
                for choice in chunk.get("choices", []):
                    delta = choice.get("delta") or {}
                    if delta.get("refusal"):
                        raise ModelResponseError("Provider refused the streamed request")
                    if delta.get("content"):
                        yield ModelStreamEvent(
                            type=ModelStreamEventType.TEXT_DELTA, delta=delta["content"]
                        )
                    for call in delta.get("tool_calls", []):
                        current = calls.setdefault(
                            call["index"], {"id": "", "name": "", "arguments": ""}
                        )
                        current["id"] += call.get("id", "")
                        function = call.get("function") or {}
                        current["name"] += function.get("name", "")
                        current["arguments"] += function.get("arguments", "")
                    reason = choice.get("finish_reason")
                    if reason is not None:
                        if reason not in {"stop", "tool_calls"}:
                            raise ModelResponseError(
                                "Provider stream did not complete successfully"
                            )
                        finished = True
            if not finished:
                raise ModelResponseError("Truncated provider stream")
            for current in calls.values():
                call = ToolCall(
                    id=current["id"],
                    name=original_name(current["name"], request),
                    arguments=arguments(current["arguments"]),
                )
                yield ModelStreamEvent(
                    type=ModelStreamEventType.TOOL_CALL_COMPLETED, tool_call=call
                )
        except (ValueError, KeyError, TypeError, AttributeError):
            raise ModelResponseError("Malformed provider stream") from None
        yield ModelStreamEvent(
            type=ModelStreamEventType.COMPLETED,
            metadata=stream_metadata,
        )
