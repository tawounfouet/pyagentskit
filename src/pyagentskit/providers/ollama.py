"""Native Ollama /api/chat adapter for local deployments."""

from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4

from ..messages import TextContent
from ..models import (
    FinishReason,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelStreamEventType,
)
from ..tools import ToolCall
from ..usage import Usage
from ._mapping import arguments, original_name, text_content, wire_name
from ._native import NativeModel


class OllamaModel(NativeModel):
    provider = "ollama"
    endpoint = "http://127.0.0.1:11434"
    key_variable = "OLLAMA_API_KEY"
    path = "/api/chat"

    def _body(self, request: ModelRequest, *, stream: bool = False) -> dict[str, Any]:
        messages = []
        for message in request.messages:
            row: dict[str, Any] = {"role": message.role.value, "content": text_content(message)}
            if message.tool_calls:
                row["tool_calls"] = [
                    {"function": {"name": wire_name(c.name), "arguments": c.arguments}}
                    for c in message.tool_calls
                ]
            if message.role.value == "tool":
                row["tool_name"] = wire_name(message.name or "")
            if message.metadata.get("ollama_thinking"):
                row["thinking"] = message.metadata["ollama_thinking"]
            messages.append(row)
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": stream,
            "options": {
                "num_predict" if k == "max_output_tokens" else k: v
                for k, v in request.settings.items()
            },
        }
        if request.tools:
            body["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": wire_name(t.name),
                        "description": t.description,
                        "parameters": t.input_schema,
                    },
                }
                for t in request.tools
            ]
        if request.output_schema:
            body["format"] = request.output_schema
        return body

    def _response(self, raw: dict[str, Any], request: ModelRequest) -> ModelResponse:
        message = raw["message"]
        response_id = str(uuid4())
        calls = tuple(
            ToolCall(
                id=f"{response_id}_{i}",
                name=original_name(c["function"]["name"], request),
                arguments=arguments(c["function"]["arguments"]),
            )
            for i, c in enumerate(message.get("tool_calls", []))
        )
        text = message.get("content")
        finish = FinishReason.TOOL_CALLS if calls else FinishReason.STOP
        if not raw.get("done"):
            finish = FinishReason.UNKNOWN
        elif raw.get("done_reason") == "length":
            finish = FinishReason.LENGTH
        return ModelResponse(
            id=response_id,
            model=raw.get("model", self.model),
            content=(TextContent(text=text),) if text else (),
            tool_calls=calls,
            finish_reason=finish,
            usage=Usage(
                input_tokens=raw.get("prompt_eval_count", 0),
                output_tokens=raw.get("eval_count", 0),
                model_calls=1,
            ),
            metadata={
                "provider": self.provider,
                "requested_model": self.model,
                "resolved_model": raw.get("model", self.model),
                "usage_reported": "eval_count" in raw,
                "ollama_thinking": message.get("thinking", ""),
            },
        )

    async def _stream_raw(
        self, request: ModelRequest
    ) -> AsyncIterator[ModelStreamEvent | dict[str, Any]]:
        message: dict[str, Any] = {"content": "", "thinking": "", "tool_calls": []}
        async for chunk in self._http.stream(
            self.path, self._body(request, stream=True), ndjson=True
        ):
            delta = chunk.get("message", {})
            text = delta.get("content", "")
            message["content"] += text
            message["thinking"] += delta.get("thinking", "")
            if text:
                yield ModelStreamEvent(type=ModelStreamEventType.TEXT_DELTA, delta=text)
            for call in delta.get("tool_calls", []):
                message["tool_calls"].append(call)
            if chunk.get("done"):
                chunk["message"] = message
                yield chunk
                return
