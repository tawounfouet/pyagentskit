"""Serializable agent definition contract."""

from typing import Any

from pydantic import Field, model_validator

from ._base import ContractModel
from .models import ModelRef
from .runs import RunLimits
from .types import Identifier, NonEmptyString, SemanticVersion


class AgentDefinition(ContractModel):
    """Provider-neutral, serializable definition of an agent."""

    id: Identifier
    version: SemanticVersion
    instructions: NonEmptyString
    model: ModelRef
    description: str | None = None
    tools: tuple[Identifier, ...] = ()
    limits: RunLimits = Field(default_factory=RunLimits)
    output_schema: dict[str, Any] | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_tool_names(self) -> "AgentDefinition":
        if len(set(self.tools)) != len(self.tools):
            msg = "agent tool names must be unique"
            raise ValueError(msg)
        return self
