"""Serializable OpenRouter routing and data-governance policies."""

from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from .._base import ContractModel
from ..exceptions import ConfigurationError

__all__ = [
    "OpenRouterDataPolicy",
    "OpenRouterProfile",
    "OpenRouterRoutingPolicy",
]


def _validate_names(values: tuple[str, ...], label: str) -> None:
    if any(not value.strip() or value != value.strip() for value in values):
        raise ValueError(f"{label} entries must be non-blank and trimmed")
    if len(set(values)) != len(values):
        raise ValueError(f"{label} entries must be unique")


def _validate_models(values: tuple[str, ...]) -> None:
    _validate_names(values, "model_fallbacks")
    if any("/" not in value or value.startswith("/") or value.endswith("/") for value in values):
        raise ValueError("fallback model IDs must include an organization prefix")


class OpenRouterProfile(StrEnum):
    """Named policy presets; every resulting value remains inspectable."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    COMPLIANCE = "compliance"
    EVALUATION = "evaluation"


class OpenRouterDataPolicy(ContractModel):
    """Constraints applied by OpenRouter when selecting upstream endpoints."""

    require_zdr: bool = False
    allow_training: bool | None = None
    allowed_providers: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_policy(self) -> OpenRouterDataPolicy:
        _validate_names(self.allowed_providers, "allowed_providers")
        return self

    def to_provider(self) -> dict[str, object]:
        result: dict[str, object] = {}
        if self.allow_training is not None:
            result["data_collection"] = "allow" if self.allow_training else "deny"
        if self.require_zdr:
            result["zdr"] = True
        if self.allowed_providers:
            result["only"] = list(self.allowed_providers)
        return result


class OpenRouterRoutingPolicy(ContractModel):
    """Explicit server-side routing configuration with bounded model failover."""

    provider_order: tuple[str, ...] = ()
    ignored_providers: tuple[str, ...] = ()
    model_fallbacks: tuple[str, ...] = ()
    allow_fallbacks: bool = False
    require_parameters: bool = True
    data: OpenRouterDataPolicy = Field(default_factory=OpenRouterDataPolicy)

    @model_validator(mode="after")
    def validate_policy(self) -> OpenRouterRoutingPolicy:
        _validate_names(self.provider_order, "provider_order")
        _validate_names(self.ignored_providers, "ignored_providers")
        _validate_models(self.model_fallbacks)
        allowed = set(self.data.allowed_providers)
        if allowed and not set(self.provider_order).issubset(allowed):
            raise ValueError("provider_order must be a subset of allowed_providers")
        if set(self.provider_order) & set(self.ignored_providers):
            raise ValueError("a provider cannot be ordered and ignored")
        if allowed & set(self.ignored_providers):
            raise ValueError("a provider cannot be both allowed and ignored")
        if self.model_fallbacks and not self.allow_fallbacks:
            raise ValueError("model_fallbacks require allow_fallbacks=True")
        return self

    @classmethod
    def for_profile(
        cls,
        profile: OpenRouterProfile,
        *,
        allowed_providers: tuple[str, ...] = (),
    ) -> OpenRouterRoutingPolicy:
        if not isinstance(profile, OpenRouterProfile):
            raise ConfigurationError("profile must be an OpenRouterProfile")
        if profile is OpenRouterProfile.DEVELOPMENT:
            return cls(
                allow_fallbacks=True,
                data=OpenRouterDataPolicy(allowed_providers=allowed_providers),
            )
        if profile is OpenRouterProfile.PRODUCTION:
            return cls(
                allow_fallbacks=True,
                data=OpenRouterDataPolicy(
                    allow_training=False,
                    allowed_providers=allowed_providers,
                ),
            )
        if profile is OpenRouterProfile.COMPLIANCE:
            if not allowed_providers:
                raise ConfigurationError("Compliance profile requires allowed_providers")
            return cls(
                allow_fallbacks=False,
                data=OpenRouterDataPolicy(
                    require_zdr=True,
                    allow_training=False,
                    allowed_providers=allowed_providers,
                ),
            )
        return cls(
            allow_fallbacks=False,
            require_parameters=True,
            data=OpenRouterDataPolicy(allowed_providers=allowed_providers),
        )

    def to_provider(self) -> dict[str, object]:
        result = self.data.to_provider()
        result.update(
            {
                "allow_fallbacks": self.allow_fallbacks,
                "require_parameters": self.require_parameters,
            }
        )
        if self.provider_order:
            result["order"] = list(self.provider_order)
        if self.ignored_providers:
            result["ignore"] = list(self.ignored_providers)
        return result

    def validate_local_retries(self, retries: int) -> None:
        if retries and (self.allow_fallbacks or self.model_fallbacks):
            raise ConfigurationError(
                "Local HTTP retries must be zero when OpenRouter fallbacks are enabled"
            )
