"""Shared configuration for serializable public contracts."""

from pydantic import BaseModel, ConfigDict


class ContractModel(BaseModel):
    """Strict, immutable and forward-compatible base for public contracts."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        strict=True,
        validate_default=True,
    )
