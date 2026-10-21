"""Tool contracts and the public tool-system API."""

from collections.abc import Awaitable, Callable
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Protocol, TypeVar, overload, runtime_checkable

from pydantic import Field, model_validator

from ._base import ContractModel
from .artifacts import ArtifactRef
from .types import Identifier, NonEmptyString, SemanticVersion

ToolFunction = TypeVar("ToolFunction", bound=Callable[..., Any])


class ToolRisk(StrEnum):
    """Security-relevant effect classification."""

    PURE = "pure"
    READ = "read"
    LOCAL_WRITE = "local_write"
    EXTERNAL_WRITE = "external_write"
    DESTRUCTIVE = "destructive"
    CODE_EXECUTION = "code_execution"


class ToolDefinition(ContractModel):
    """Serializable schema and governance metadata for a tool."""

    name: Identifier
    version: SemanticVersion = "1.0.0"
    description: NonEmptyString
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None = None
    risk: ToolRisk = ToolRisk.PURE
    idempotent: bool = False
    requires_approval: bool = False
    timeout_seconds: float = Field(default=30.0, gt=0)
    concurrency_limit: int | None = Field(default=None, gt=0)
    tags: tuple[Identifier, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_security_invariants(self) -> "ToolDefinition":
        if self.risk in {ToolRisk.DESTRUCTIVE, ToolRisk.CODE_EXECUTION} and not (
            self.requires_approval
        ):
            msg = f"{self.risk.value} tools must require approval"
            raise ValueError(msg)
        if len(set(self.tags)) != len(self.tags):
            msg = "tool tags must be unique"
            raise ValueError(msg)
        return self


class ToolCall(ContractModel):
    """A validated representation of a model-requested tool invocation."""

    id: NonEmptyString
    name: Identifier
    arguments: dict[str, Any]
    metadata: dict[str, Any] = Field(default_factory=dict)


class ToolResultStatus(StrEnum):
    """Normalized tool result status."""

    SUCCEEDED = "succeeded"
    FAILED = "failed"
    DENIED = "denied"
    CANCELLED = "cancelled"


class ToolResult(ContractModel):
    """Normalized tool output returned to the agent loop."""

    call_id: NonEmptyString
    tool_name: Identifier
    status: ToolResultStatus
    content: Any = None
    display_text: str | None = None
    artifacts: tuple[ArtifactRef, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)
    retryable: bool = False


@runtime_checkable
class ToolExecutionPolicy(Protocol):
    """Optional interception hook around a validated tool execution.

    Approval orchestration is handled by the runtime before this hook. A policy
    may still reject an execution by raising :class:`ToolPermissionError`.
    """

    def before_execute(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        *,
        context: "RunContext[Any]",
    ) -> Awaitable[None]:
        """Authorize or reject a call before user code runs."""
        ...

    def after_execute(
        self,
        call: ToolCall,
        definition: ToolDefinition,
        result: ToolResult,
        *,
        context: "RunContext[Any]",
    ) -> Awaitable[ToolResult]:
        """Inspect or transform a normalized result."""
        ...


if TYPE_CHECKING:
    from .runs import RunContext


@overload
def tool(function: ToolFunction, /) -> "FunctionTool": ...


@overload
def tool(
    function: None = None,
    /,
    *,
    name: str | None = None,
    version: str = "1.0.0",
    description: str | None = None,
    risk: ToolRisk | str = ToolRisk.PURE,
    idempotent: bool = False,
    requires_approval: bool = False,
    timeout_seconds: float = 30.0,
    concurrency_limit: int | None = None,
    tags: tuple[str, ...] = (),
    metadata: dict[str, Any] | None = None,
) -> Callable[[ToolFunction], "FunctionTool"]: ...


def tool(
    function: ToolFunction | None = None,
    /,
    *,
    name: str | None = None,
    version: str = "1.0.0",
    description: str | None = None,
    risk: ToolRisk | str = ToolRisk.PURE,
    idempotent: bool = False,
    requires_approval: bool = False,
    timeout_seconds: float = 30.0,
    concurrency_limit: int | None = None,
    tags: tuple[str, ...] = (),
    metadata: dict[str, Any] | None = None,
) -> "FunctionTool | Callable[[ToolFunction], FunctionTool]":
    """Declare a Python callable as an explicitly governed tool."""

    from ._tool_function import create_function_tool

    def decorate(target: ToolFunction) -> FunctionTool:
        return create_function_tool(
            target,
            name=name,
            version=version,
            description=description,
            risk=risk,
            idempotent=idempotent,
            requires_approval=requires_approval,
            timeout_seconds=timeout_seconds,
            concurrency_limit=concurrency_limit,
            tags=tags,
            metadata=metadata,
        )

    if function is not None:
        return decorate(function)
    return decorate


# Imports remain at the bottom so implementation modules can reuse the contracts.
from ._tool_execution import ToolExecutor as ToolExecutor  # noqa: E402
from ._tool_function import FunctionTool as FunctionTool  # noqa: E402
from ._tool_registry import ToolRegistry as ToolRegistry  # noqa: E402
