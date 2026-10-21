from __future__ import annotations

import unittest

from pydantic import ValidationError

from pyagentskit import ImageContent, Message, MessageRole, TextContent


class MessageTests(unittest.TestCase):
    def test_builds_text_message(self) -> None:
        message = Message.from_text(MessageRole.USER, "Hello")

        self.assertEqual(message.role, MessageRole.USER)
        self.assertEqual(message.content, (TextContent(text="Hello"),))

    def test_supports_multimodal_content(self) -> None:
        message = Message(
            role=MessageRole.USER,
            content=(
                TextContent(text="Describe this image"),
                ImageContent(uri="artifact://image-1", media_type="image/png"),
            ),
        )

        self.assertEqual(len(message.content), 2)

    def test_tool_message_requires_call_id(self) -> None:
        with self.assertRaises(ValidationError):
            Message(role=MessageRole.TOOL, content=(TextContent(text="result"),))

    def test_non_tool_message_rejects_call_id(self) -> None:
        with self.assertRaises(ValidationError):
            Message(
                role=MessageRole.USER,
                content=(TextContent(text="result"),),
                tool_call_id="call-1",
            )

    def test_message_cannot_be_empty(self) -> None:
        with self.assertRaises(ValidationError):
            Message(role=MessageRole.USER, content=())


if __name__ == "__main__":
    unittest.main()
