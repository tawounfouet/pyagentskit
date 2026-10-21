"""Native Anthropic Messages API adapter, including tool-use history."""

import json
from collections.abc import AsyncIterator
from typing import Any

from ..exceptions import CapabilityError, ModelResponseError
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
from ._mapping import (
    arguments,
    opaque_blocks,
    original_name,
    strict_schema,
    text_content,
    wire_name,
)
from ._native import NativeModel


class AnthropicModel(NativeModel):
    provider = "anthropic"
    endpoint = "https://api.anthropic.com/v1"
    key_variable = "ANTHROPIC_API_KEY"
    path = "/messages"

    def _body(self, request: ModelRequest, *, stream: bool = False) -> dict[str, Any]:
        if "seed" in request.settings:
            raise CapabilityError("Anthropic seed setting is not supported")
        system = []
        messages: list[dict[str, Any]] = []
        for message in request.messages:
            text = text_content(message)
            if message.role.value == "system":
                system.append(text)
                continue
            role = "assistant" if message.role.value == "assistant" else "user"
            blocks: list[dict[str, Any]] = []
            if message.role.value == "tool":
                blocks.append(
                    {"type": "tool_result", "tool_use_id": message.tool_call_id, "content": text}
                )
            elif message.metadata.get("anthropic_content") and role == "assistant":
                # Replay signed thinking/redacted blocks exactly, never invent signatures.
                blocks = opaque_blocks(message.metadata["anthropic_content"])
            else:
                if text:
                    blocks.append({"type": "text", "text": text})
                blocks.extend(
                    {
                        "type": "tool_use",
                        "id": c.id,
                        "name": wire_name(c.name),
                        "input": c.arguments,
                    }
                    for c in message.tool_calls
                )
            if messages and messages[-1]["role"] == role:
                messages[-1]["content"].extend(blocks)
            else:
                messages.append({"role": role, "content": blocks})
        body: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "max_tokens": request.settings.get("max_output_tokens", 1024),
            "stream": stream,
        }
        if system:
            body["system"] = "\n\n".join(system)
        for setting in ("temperature", "top_p"):
            if setting in request.settings:
                body[setting] = request.settings[setting]
        if request.tools:
            body["tools"] = [
                {
                    "name": wire_name(t.name),
                    "description": t.description,
                    "input_schema": t.input_schema,
                }
                for t in request.tools
            ]
        if request.output_schema:
            body["output_config"] = {
                "format": {"type": "json_schema", "schema": strict_schema(request.output_schema)}
            }
        return body

    def _response(self, raw: dict[str, Any], request: ModelRequest) -> ModelResponse:
        blocks = raw["content"]
        content = tuple(
            TextContent(text=b["text"]) for b in blocks if b["type"] == "text" and b.get("text")
        )
        calls = tuple(
            ToolCall(
                id=b["id"], name=original_name(b["name"], request), arguments=arguments(b["input"])
            )
            for b in blocks
            if b["type"] == "tool_use"
        )
        reason = {
            "end_turn": FinishReason.STOP,
            "stop_sequence": FinishReason.STOP,
            "tool_use": FinishReason.TOOL_CALLS,
            "max_tokens": FinishReason.LENGTH,
            "refusal": FinishReason.CONTENT_FILTER,
        }.get(raw.get("stop_reason", ""), FinishReason.UNKNOWN)
        used = raw.get("usage") or {}
        # Anthropic input_tokens excludes cache reads and writes; normalize to total input.
        cached = used.get("cache_read_input_tokens", 0)
        input_tokens = (
            used.get("input_tokens", 0) + cached + used.get("cache_creation_input_tokens", 0)
        )
        return ModelResponse(
            id=raw["id"],
            model=raw.get("model", self.model),
            content=content,
            tool_calls=calls,
            finish_reason=reason,
            usage=Usage(
                input_tokens=input_tokens,
                output_tokens=used.get("output_tokens", 0),
                cached_input_tokens=cached,
                model_calls=1,
            ),
            metadata={
                "provider": self.provider,
                "requested_model": self.model,
                "resolved_model": raw.get("model", self.model),
                "usage_reported": "usage" in raw,
                "anthropic_content": blocks,
            },
        )

    async def _stream_raw(
        self, request: ModelRequest
    ) -> AsyncIterator[ModelStreamEvent | dict[str, Any]]:
        raw: dict[str, Any] = {}
        blocks: dict[int, dict[str, Any]] = {}
        buffers: dict[int, str] = {}
        async for item in self._http.stream(self.path, self._body(request, stream=True)):
            kind = item.get("type")
            if kind == "message_start":
                raw = item["message"]
            elif kind == "content_block_start":
                blocks[item["index"]] = item["content_block"]
            elif kind == "content_block_delta":
                index = item["index"]
                delta = item["delta"]
                if delta["type"] == "text_delta":
                    blocks[index]["text"] = blocks[index].get("text", "") + delta["text"]
                    yield ModelStreamEvent(
                        type=ModelStreamEventType.TEXT_DELTA, delta=delta["text"]
                    )
                elif delta["type"] == "input_json_delta":
                    buffers[index] = buffers.get(index, "") + delta["partial_json"]
                elif delta["type"] == "thinking_delta":
                    blocks[index]["thinking"] = (
                        blocks[index].get("thinking", "") + delta["thinking"]
                    )
                elif delta["type"] == "signature_delta":
                    blocks[index]["signature"] = delta["signature"]
            elif kind == "message_delta":
                raw.update(item["delta"])
                raw.setdefault("usage", {}).update(item.get("usage", {}))
            elif kind == "message_stop":
                if not raw:
                    raise ModelResponseError("Missing Anthropic message start")
                for index, value in buffers.items():
                    blocks[index]["input"] = json.loads(value)
                raw["content"] = [blocks[i] for i in sorted(blocks)]
                yield raw
                return
