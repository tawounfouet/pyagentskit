"""Artifact reference contracts."""

from typing import Any

from pydantic import Field

from ._base import ContractModel
from .types import NonEmptyString


class ArtifactRef(ContractModel):
    """Reference to durable output stored outside the model context."""

    artifact_id: NonEmptyString
    name: NonEmptyString
    media_type: NonEmptyString
    uri: NonEmptyString
    size_bytes: int | None = Field(default=None, ge=0)
    checksum: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
