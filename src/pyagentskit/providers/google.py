"""Native Google Gemini generateContent adapter with opaque part replay."""

from collections.abc import AsyncIterator
from typing import Any
from urllib.parse import quote
from uuid import uuid4

from ..exceptions import CapabilityError
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
from ._mapping import arguments, opaque_blocks, original_name, text_content, wire_name
from ._native import NativeModel


class GoogleModel(NativeModel):
    provider = "google"
    endpoint = "https://generativelanguage.googleapis.com/v1beta"
    key_variable = "GOOGLE_API_KEY"

    @property
    def path(self) -> str:  # type: ignore[override]
        return "/models/" + quote(self.model.removeprefix("models/"), safe="") + ":generateContent"

    def _body(self, request: ModelRequest, *, stream: bool = False) -> dict[str, Any]:
        if request.tools and request.output_schema:
            raise CapabilityError("Gemini tools + structured output combination is not enabled")
        system = []
        contents: list[dict[str, Any]] = []
        native_ids: set[str] = set()
        for message in request.messages:
            text = text_content(message)
            if message.role.value == "system":
                system.append({"text": text})
                continue
            role = "model" if message.role.value == "assistant" else "user"
            parts: list[dict[str, Any]] = []
            if message.role.value == "tool":
                # Use normalized tool identity, not the opaque call id, as function name.
                parts.append(
                    {
                        "functionResponse": {
                            "name": wire_name(message.name or ""),
                            "response": {"result": text},
                        }
                    }
                )
                if message.tool_call_id in native_ids:
                    parts[-1]["functionResponse"]["id"] = message.tool_call_id
            elif role == "model" and message.metadata.get("google_parts"):
                parts = opaque_blocks(message.metadata["google_parts"])
                native_ids.update(
                    p["functionCall"]["id"] for p in parts if p.get("functionCall", {}).get("id")
                )
            else:
                if text:
                    parts.append({"text": text})
                parts.extend(
                    {"functionCall": {"name": wire_name(c.name), "args": c.arguments}}
                    for c in message.tool_calls
                )
            if contents and contents[-1]["role"] == role:
                contents[-1]["parts"].extend(parts)
            else:
                contents.append({"role": role, "parts": parts})
        config: dict[str, Any] = {}
        names = {
            "temperature": "temperature",
            "top_p": "topP",
            "max_output_tokens": "maxOutputTokens",
            "seed": "seed",
        }
        for name, value in request.settings.items():
            config[names[name]] = value
        if request.output_schema:
            config.update(
                responseMimeType="application/json", responseJsonSchema=request.output_schema
            )
        body: dict[str, Any] = {"contents": contents, "generationConfig": config}
        if system:
            body["systemInstruction"] = {"parts": system}
        if request.tools:
            body["tools"] = [
                {
                    "functionDeclarations": [
                        {
                            "name": wire_name(t.name),
                            "description": t.description,
                            "parametersJsonSchema": t.input_schema,
                        }
                        for t in request.tools
                    ]
                }
            ]
        return body

    def _response(self, raw: dict[str, Any], request: ModelRequest) -> ModelResponse:
        candidate = (raw.get("candidates") or [{}])[0]
        parts = candidate.get("content", {}).get("parts", [])
        response_id = raw.get("responseId") or str(uuid4())
        calls = tuple(
            ToolCall(
                id=p["functionCall"].get("id") or f"{response_id}_{i}",
                name=original_name(p["functionCall"]["name"], request),
                arguments=arguments(p["functionCall"].get("args", {})),
            )
            for i, p in enumerate(parts)
            if "functionCall" in p
        )
        content = tuple(
            TextContent(text=p["text"]) for p in parts if p.get("text") and not p.get("thought")
        )
        reason = candidate.get("finishReason")
        finish = {
            "STOP": FinishReason.TOOL_CALLS if calls else FinishReason.STOP,
            "MAX_TOKENS": FinishReason.LENGTH,
            "SAFETY": FinishReason.CONTENT_FILTER,
            "RECITATION": FinishReason.CONTENT_FILTER,
        }.get(reason, FinishReason.UNKNOWN)
        if raw.get("promptFeedback", {}).get("blockReason"):
            finish = FinishReason.CONTENT_FILTER
        used = raw.get("usageMetadata") or {}
        thought = used.get("thoughtsTokenCount", 0)
        return ModelResponse(
            id=response_id,
            model=raw.get("modelVersion", self.model),
            content=content,
            tool_calls=calls,
            finish_reason=finish,
            usage=Usage(
                input_tokens=used.get("promptTokenCount", 0),
                output_tokens=used.get("candidatesTokenCount", 0) + thought,
                cached_input_tokens=used.get("cachedContentTokenCount", 0),
                reasoning_tokens=thought,
                model_calls=1,
            ),
            metadata={
                "provider": self.provider,
                "requested_model": self.model,
                "resolved_model": raw.get("modelVersion", self.model),
                "google_parts": parts,
                "usage_reported": "usageMetadata" in raw,
            },
        )

    async def _stream_raw(
        self, request: ModelRequest
    ) -> AsyncIterator[ModelStreamEvent | dict[str, Any]]:
        path = self.path.replace(":generateContent", ":streamGenerateContent?alt=sse")
        raw: dict[str, Any] = {}
        parts: list[dict[str, Any]] = []
        finished = False
        async for chunk in self._http.stream(path, self._body(request, stream=True)):
            raw.update(chunk)
            candidate = (chunk.get("candidates") or [{}])[0]
            for part in candidate.get("content", {}).get("parts", []):
                parts.append(part)
                if part.get("text") and not part.get("thought"):
                    yield ModelStreamEvent(type=ModelStreamEventType.TEXT_DELTA, delta=part["text"])
            if candidate.get("finishReason"):
                raw["finish_reason"] = candidate["finishReason"]
                finished = True
        if finished:
            raw["candidates"] = [
                {"content": {"parts": parts}, "finishReason": raw["finish_reason"]}
            ]
            yield raw
