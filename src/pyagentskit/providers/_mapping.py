"""Neutral-to-wire helpers shared by adapters, not by the runtime."""

import copy
import hashlib
import json
from typing import Any

from ..exceptions import CapabilityError, ModelResponseError
from ..messages import Message
from ..models import ModelRequest


def wire_name(name: str) -> str:
    """Provider-safe, collision-resistant alias; original names may contain dots."""
    return "t_" + hashlib.sha256(name.encode()).hexdigest()[:40]


def original_name(wire: str, request: ModelRequest) -> str:
    for tool in request.tools:
        if wire_name(tool.name) == wire:
            return tool.name
    raise ModelResponseError("Provider returned an unknown tool name")


def arguments(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise ModelResponseError("Tool arguments must be a JSON object")
    return value


def text_content(message: Message) -> str:
    if any(part.type != "text" for part in message.content):
        raise CapabilityError("This adapter supports text input only")
    return "".join(part.text for part in message.content if part.type == "text")


def opaque_blocks(value: object) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise CapabilityError("Invalid opaque provider history")
    return copy.deepcopy(value)


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Copy and close objects for OpenAI strict output; reject optional semantics.

    Making optional fields required silently would change the user's contract.
    Use required nullable fields when a provider strict schema needs absence.
    """
    result = copy.deepcopy(schema)

    def visit(node: Any) -> None:
        if isinstance(node, dict):
            node.pop("default", None)
            if node.get("type") == "object":
                props = node.get("properties", {})
                if set(node.get("required", [])) != set(props):
                    raise CapabilityError("Strict output requires all properties to be required")
                if node.get("additionalProperties") not in (None, False):
                    raise CapabilityError("Strict output cannot use open dictionary schemas")
                node["additionalProperties"] = False
            for item in node.values():
                visit(item)
        elif isinstance(node, list):
            for item in node:
                visit(item)

    visit(result)
    return result
