"""Runtime-checkable extension ports."""

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from .events import AgentEvent
from .models import ModelCapabilities, ModelRequest, ModelResponse, ModelStreamEvent
from .runs import RunContext
from .tools import ToolDefinition, ToolResult


@runtime_checkable
class Model(Protocol):
    """Provider-neutral asynchronous model adapter."""

    @property
    def capabilities(self) -> ModelCapabilities:
        """Capabilities guaranteed for the configured model."""
        ...

    async def generate(
        self,
        request: ModelRequest,
        *,
        context: RunContext[Any],
    ) -> ModelResponse:
        """Generate one complete normalized response."""
        ...

    def stream(
        self,
        request: ModelRequest,
        *,
        context: RunContext[Any],
    ) -> AsyncIterator[ModelStreamEvent]:
        """Return a normalized asynchronous event stream."""
        ...


@runtime_checkable
class Tool(Protocol):
    """Callable capability exposed to the future tool executor."""

    @property
    def definition(self) -> ToolDefinition:
        """Return serializable schema and policy metadata."""
        ...

    async def invoke(
        self,
        arguments: dict[str, Any],
        *,
        context: RunContext[Any],
    ) -> ToolResult:
        """Execute the capability after runtime validation and authorization."""
        ...


@runtime_checkable
class EventSink(Protocol):
    """Destination for structured runtime events."""

    async def emit(self, event: AgentEvent) -> None:
        """Persist or forward one immutable event."""
        ...


@runtime_checkable
class SecretProvider(Protocol):
    """Application-owned lookup port for credentials and sensitive values."""

    async def get_secret(self, name: str) -> str | None:
        """Return a secret without exposing it in serializable configuration."""
        ...
