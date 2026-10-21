"""Provider-neutral model request and response contracts."""

from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from ._base import ContractModel
from .messages import Message, MessageContent
from .tools import ToolCall, ToolDefinition
from .types import Identifier, NonEmptyString
from .usage import Usage


class Modality(StrEnum):
    """Normalized model input and output modalities."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    DOCUMENT = "document"


class ModelRef(ContractModel):
    """Serializable selection of a provider model."""

    provider: Identifier
    name: NonEmptyString
    revision: str | None = None

    @property
    def qualified_name(self) -> str:
        """Return a stable display name without assuming a provider URL format."""

        return f"{self.provider}:{self.name}"


class ModelCapabilities(ContractModel):
    """Capabilities declared by a concrete model adapter configuration.

    Adapter defaults describe the implemented transport envelope. Applications should
    provide model-specific capabilities when they require stronger guarantees.
    """

    tool_calling: bool = False
    structured_output: bool = False
    streaming: bool = False
    parallel_tool_calls: bool = False
    input_modalities: tuple[Modality, ...] = (Modality.TEXT,)
    output_modalities: tuple[Modality, ...] = (Modality.TEXT,)
    max_context_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_modalities(self) -> "ModelCapabilities":
        if not self.input_modalities or not self.output_modalities:
            msg = "input_modalities and output_modalities cannot be empty"
            raise ValueError(msg)
        if len(set(self.input_modalities)) != len(self.input_modalities):
            msg = "input_modalities must be unique"
            raise ValueError(msg)
        if len(set(self.output_modalities)) != len(self.output_modalities):
            msg = "output_modalities must be unique"
            raise ValueError(msg)
        return self


class ModelRequest(ContractModel):
    """Normalized input to a model adapter."""

    messages: tuple[Message, ...]
    tools: tuple[ToolDefinition, ...] = ()
    output_schema: dict[str, Any] | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_request(self) -> "ModelRequest":
        if not self.messages:
            msg = "a model request requires at least one message"
            raise ValueError(msg)
        tool_names = [tool.name for tool in self.tools]
        if len(set(tool_names)) != len(tool_names):
            msg = "model request tool names must be unique"
            raise ValueError(msg)
        return self


class FinishReason(StrEnum):
    """Normalized reason a model stopped producing output."""

    STOP = "stop"
    TOOL_CALLS = "tool_calls"
    LENGTH = "length"
    CONTENT_FILTER = "content_filter"
    CANCELLED = "cancelled"
    ERROR = "error"
    UNKNOWN = "unknown"


class ModelResponse(ContractModel):
    """Normalized complete response from a model adapter."""

    id: NonEmptyString
    model: NonEmptyString
    content: tuple[MessageContent, ...] = ()
    tool_calls: tuple[ToolCall, ...] = ()
    finish_reason: FinishReason
    usage: Usage = Field(default_factory=Usage)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_response_shape(self) -> "ModelResponse":
        if (
            not self.content
            and not self.tool_calls
            and self.finish_reason
            not in {
                FinishReason.CANCELLED,
                FinishReason.CONTENT_FILTER,
                FinishReason.ERROR,
            }
        ):
            msg = "model response must contain content or tool calls"
            raise ValueError(msg)
        if self.finish_reason is FinishReason.TOOL_CALLS and not self.tool_calls:
            msg = "finish_reason=tool_calls requires at least one tool call"
            raise ValueError(msg)
        return self


class ModelStreamEventType(StrEnum):
    """Normalized incremental model event kinds."""

    STARTED = "started"
    TEXT_DELTA = "text_delta"
    TOOL_CALL_DELTA = "tool_call_delta"
    TOOL_CALL_COMPLETED = "tool_call_completed"
    USAGE = "usage"
    COMPLETED = "completed"
    ERROR = "error"


class ModelStreamEvent(ContractModel):
    """Provider-neutral incremental event emitted by a streaming model call."""

    type: ModelStreamEventType
    delta: str | None = None
    tool_call: ToolCall | None = None
    usage: Usage | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
