from __future__ import annotations

import unittest

from pydantic import ValidationError

from pyagentskit import (
    FinishReason,
    Message,
    MessageRole,
    ModelCapabilities,
    ModelRequest,
    ModelResponse,
    TextContent,
    ToolCall,
    ToolDefinition,
)


def make_tool() -> ToolDefinition:
    return ToolDefinition(
        name="weather.get",
        description="Get weather.",
        input_schema={"type": "object"},
    )


class ModelContractTests(unittest.TestCase):
    def test_capabilities_require_modalities(self) -> None:
        with self.assertRaises(ValidationError):
            ModelCapabilities(input_modalities=())

    def test_request_requires_message(self) -> None:
        with self.assertRaises(ValidationError):
            ModelRequest(messages=())

    def test_request_rejects_duplicate_tool_names(self) -> None:
        with self.assertRaises(ValidationError):
            ModelRequest(
                messages=(Message.from_text(MessageRole.USER, "Weather?"),),
                tools=(make_tool(), make_tool()),
            )

    def test_final_response_contains_content(self) -> None:
        response = ModelResponse(
            id="response-1",
            model="example:model",
            content=(TextContent(text="Sunny"),),
            finish_reason=FinishReason.STOP,
        )

        self.assertEqual(response.content[0], TextContent(text="Sunny"))

    def test_tool_finish_reason_requires_tool_call(self) -> None:
        with self.assertRaises(ValidationError):
            ModelResponse(
                id="response-1",
                model="example:model",
                finish_reason=FinishReason.TOOL_CALLS,
            )

    def test_tool_call_response_is_valid(self) -> None:
        response = ModelResponse(
            id="response-1",
            model="example:model",
            tool_calls=(ToolCall(id="call-1", name="weather.get", arguments={"city": "Paris"}),),
            finish_reason=FinishReason.TOOL_CALLS,
        )

        self.assertEqual(response.tool_calls[0].arguments["city"], "Paris")


if __name__ == "__main__":
    unittest.main()
