"""Explicit data-classification, provider egress and redaction policies."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable, Mapping
from enum import IntEnum
from typing import Any

from pydantic import model_validator

from ._base import ContractModel
from .exceptions import ConfigurationError, PrivacyPolicyError
from .types import NonEmptyString

__all__ = [
    "DataClassification",
    "DataPolicy",
    "EnvironmentSecretProvider",
    "Redactor",
]


class DataClassification(IntEnum):
    """Ordered application data sensitivity levels."""

    PUBLIC = 0
    INTERNAL = 1
    CONFIDENTIAL = 2
    RESTRICTED = 3


class DataPolicy(ContractModel):
    """Fail-closed rules for sending classified data to a model provider."""

    max_classification: DataClassification = DataClassification.INTERNAL
    allowed_providers: tuple[NonEmptyString, ...] = ()
    allowed_models: tuple[NonEmptyString, ...] = ()
    require_zdr: bool = False
    allow_training: bool = False

    @model_validator(mode="after")
    def validate_unique_allowlists(self) -> DataPolicy:
        for label, values in (
            ("allowed_providers", self.allowed_providers),
            ("allowed_models", self.allowed_models),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"{label} entries must be unique")
        return self

    def authorize(
        self,
        *,
        provider: str,
        model: str,
        classification: DataClassification,
        provider_policy: Mapping[str, Any] | None = None,
    ) -> None:
        """Raise before network access when an egress rule cannot be guaranteed."""

        if classification > self.max_classification:
            raise PrivacyPolicyError("Data classification exceeds the configured egress limit")
        if self.allowed_providers and provider not in self.allowed_providers:
            raise PrivacyPolicyError("Provider is outside the configured allowlist")
        if self.allowed_models and model not in self.allowed_models:
            raise PrivacyPolicyError("Model is outside the configured allowlist")
        policy = dict(provider_policy or {})
        if self.require_zdr and policy.get("zdr") is not True:
            raise PrivacyPolicyError("The selected route does not guarantee zero data retention")
        if not self.allow_training and policy.get("allow_training") is not False:
            raise PrivacyPolicyError("The selected route does not guarantee training exclusion")


class EnvironmentSecretProvider:
    """Allowlisted environment lookup with no serializable secret cache."""

    def __init__(self, allowed_names: Iterable[str]) -> None:
        normalized = tuple(allowed_names)
        if not normalized or any(not item or item.strip() != item for item in normalized):
            raise ConfigurationError("Secret names must be non-empty and trimmed")
        if len(set(normalized)) != len(normalized):
            raise ConfigurationError("Secret names must be unique")
        self._allowed = frozenset(normalized)

    async def get_secret(self, name: str) -> str | None:
        if name not in self._allowed:
            raise ConfigurationError("Secret name is outside the configured allowlist")
        value = os.getenv(name)
        return value if value else None


class Redactor:
    """Recursively redact exact secrets and conservative credential patterns."""

    _patterns = (
        re.compile(r"\bsk-[A-Za-z0-9_-]{12,}\b"),
        re.compile(r"\bAIza[0-9A-Za-z_-]{20,}\b"),
        re.compile(r"Bearer\s+[A-Za-z0-9._~+/-]{12,}", re.IGNORECASE),
    )

    def __init__(self, secrets: Iterable[str] = (), *, replacement: str = "[REDACTED]") -> None:
        self.secrets = tuple(sorted({item for item in secrets if item}, key=len, reverse=True))
        self.replacement = replacement

    def redact(self, value: Any) -> Any:
        if isinstance(value, str):
            result = value
            for secret in self.secrets:
                result = result.replace(secret, self.replacement)
            for pattern in self._patterns:
                result = pattern.sub(self.replacement, result)
            return result
        if isinstance(value, dict):
            return {key: self.redact(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return tuple(self.redact(item) for item in value)
        if isinstance(value, list):
            return [self.redact(item) for item in value]
        return value
