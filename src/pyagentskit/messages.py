"""Provider-neutral message and multimodal content contracts."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import Field, model_validator

from ._base import ContractModel
from .tools import ToolCall
from .types import NonEmptyString


class MessageRole(StrEnum):
    """Normalized roles understood by the agent runtime."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class TextContent(ContractModel):
    """Plain text message content."""

    type: Literal["text"] = "text"
    text: NonEmptyString


class ImageContent(ContractModel):
    """Reference to an image accessible to an adapter."""

    type: Literal["image"] = "image"
    uri: NonEmptyString
    media_type: str | None = None
    detail: Literal["auto", "low", "high"] = "auto"


class AudioContent(ContractModel):
    """Reference to audio content."""

    type: Literal["audio"] = "audio"
    uri: NonEmptyString
    media_type: str | None = None


class DocumentContent(ContractModel):
    """Reference to a document or artifact."""

    type: Literal["document"] = "document"
    uri: NonEmptyString
    media_type: str | None = None
    name: str | None = None


MessageContent = Annotated[
    TextContent | ImageContent | AudioContent | DocumentContent,
    Field(discriminator="type"),
]


class Message(ContractModel):
    """A normalized conversation message."""

    role: MessageRole
    content: tuple[MessageContent, ...] = ()
    tool_calls: tuple[ToolCall, ...] = ()
    name: str | None = None
    tool_call_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_content_and_tool_role(self) -> "Message":
        if not self.content and not self.tool_calls:
            msg = "message content must contain at least one part"
            raise ValueError(msg)
        if self.tool_calls and self.role is not MessageRole.ASSISTANT:
            raise ValueError("Only assistant messages may contain tool calls")
        if self.role is MessageRole.TOOL and not self.tool_call_id:
            msg = "tool messages require tool_call_id"
            raise ValueError(msg)
        if self.role is not MessageRole.TOOL and self.tool_call_id is not None:
            msg = "tool_call_id is only valid for tool messages"
            raise ValueError(msg)
        return self

    @classmethod
    def from_text(
        cls,
        role: MessageRole,
        text: str,
        *,
        name: str | None = None,
        tool_call_id: str | None = None,
        metadata: dict[str, object] | None = None,
    ) -> "Message":
        """Build a message containing one text part."""

        return cls(
            role=role,
            content=(TextContent(text=text),),
            name=name,
            tool_call_id=tool_call_id,
            metadata={} if metadata is None else metadata,
        )
