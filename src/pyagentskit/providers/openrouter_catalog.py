"""OpenRouter model catalog, bounded cache and conservative capability negotiation."""

from __future__ import annotations

import asyncio
import hashlib
import json
import math
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import Field, model_validator

from .._base import ContractModel
from ..exceptions import CapabilityError, ConfigurationError, ModelResponseError
from ..models import Modality, ModelCapabilities
from ._http import HttpTransport
from .openrouter import _raise_openrouter_error

__all__ = [
    "ModelCapabilityRequirements",
    "OpenRouterCatalog",
    "OpenRouterModelDescriptor",
    "common_capabilities",
    "require_capabilities",
]

_MODALITIES = {
    "text": Modality.TEXT,
    "image": Modality.IMAGE,
    "audio": Modality.AUDIO,
    "video": Modality.VIDEO,
    "file": Modality.DOCUMENT,
    "document": Modality.DOCUMENT,
}


class ModelCapabilityRequirements(ContractModel):
    """Capabilities an application requires before a model may be selected."""

    tool_calling: bool = False
    structured_output: bool = False
    streaming: bool = False
    parallel_tool_calls: bool = False
    input_modalities: tuple[Modality, ...] = ()
    output_modalities: tuple[Modality, ...] = ()
    min_context_tokens: int | None = Field(default=None, gt=0)
    min_output_tokens: int | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_modalities(self) -> ModelCapabilityRequirements:
        if len(set(self.input_modalities)) != len(self.input_modalities):
            raise ValueError("required input modalities must be unique")
        if len(set(self.output_modalities)) != len(self.output_modalities):
            raise ValueError("required output modalities must be unique")
        return self


class OpenRouterModelDescriptor(ContractModel):
    """Normalized, serializable subset of one dynamic catalog entry."""

    id: str = Field(min_length=3)
    name: str
    canonical_slug: str | None = None
    supported_parameters: tuple[str, ...] = ()
    input_modalities: tuple[Modality, ...] = (Modality.TEXT,)
    output_modalities: tuple[Modality, ...] = (Modality.TEXT,)
    max_context_tokens: int | None = Field(default=None, gt=0)
    max_output_tokens: int | None = Field(default=None, gt=0)

    @classmethod
    def from_api(cls, raw: dict[str, Any]) -> OpenRouterModelDescriptor:
        try:
            model_id = raw["id"]
            if not isinstance(model_id, str) or "/" not in model_id:
                raise ValueError
            architecture = raw.get("architecture") or {}
            top_provider = raw.get("top_provider") or {}
            if not isinstance(architecture, dict) or not isinstance(top_provider, dict):
                raise ValueError
            inputs = cls._modalities(architecture.get("input_modalities"), (Modality.TEXT,))
            outputs = cls._modalities(architecture.get("output_modalities"), (Modality.TEXT,))
            parameters = raw.get("supported_parameters") or []
            if not isinstance(parameters, list) or not all(isinstance(p, str) for p in parameters):
                raise ValueError
            context = raw.get("context_length")
            output = top_provider.get("max_completion_tokens")
            raw_name = raw.get("name")
            name = raw_name if isinstance(raw_name, str) else model_id
            return cls(
                id=model_id,
                name=name,
                canonical_slug=(
                    raw.get("canonical_slug")
                    if isinstance(raw.get("canonical_slug"), str)
                    else None
                ),
                supported_parameters=tuple(dict.fromkeys(parameters)),
                input_modalities=inputs,
                output_modalities=outputs,
                max_context_tokens=context if isinstance(context, int) and context > 0 else None,
                max_output_tokens=output if isinstance(output, int) and output > 0 else None,
            )
        except (KeyError, TypeError, ValueError):
            raise ModelResponseError("Malformed OpenRouter model catalog entry") from None

    @staticmethod
    def _modalities(value: Any, default: tuple[Modality, ...]) -> tuple[Modality, ...]:
        if not isinstance(value, list):
            return default
        result = tuple(dict.fromkeys(_MODALITIES[item] for item in value if item in _MODALITIES))
        return result or default

    @property
    def capabilities(self) -> ModelCapabilities:
        parameters = set(self.supported_parameters)
        return ModelCapabilities(
            tool_calling="tools" in parameters,
            structured_output="response_format" in parameters,
            streaming=True,
            parallel_tool_calls="parallel_tool_calls" in parameters,
            input_modalities=self.input_modalities,
            output_modalities=self.output_modalities,
            max_context_tokens=self.max_context_tokens,
            max_output_tokens=self.max_output_tokens,
            metadata={
                "source": "openrouter_catalog",
                "model_verified": False,
                "catalog_reported": True,
            },
        )


def common_capabilities(
    descriptors: tuple[OpenRouterModelDescriptor, ...],
) -> ModelCapabilities:
    """Return only capabilities guaranteed by every model in a routed chain."""

    if not descriptors:
        raise ConfigurationError("At least one model descriptor is required")
    capabilities = tuple(descriptor.capabilities for descriptor in descriptors)
    first = capabilities[0]
    inputs = tuple(
        modality
        for modality in first.input_modalities
        if all(modality in item.input_modalities for item in capabilities[1:])
    )
    outputs = tuple(
        modality
        for modality in first.output_modalities
        if all(modality in item.output_modalities for item in capabilities[1:])
    )

    def common_bound(values: tuple[int | None, ...]) -> int | None:
        if any(value is None for value in values):
            return None
        return min(value for value in values if value is not None)

    if not inputs or not outputs:
        raise CapabilityError("Routed models have no common input/output modality")
    return ModelCapabilities(
        tool_calling=all(item.tool_calling for item in capabilities),
        structured_output=all(item.structured_output for item in capabilities),
        streaming=all(item.streaming for item in capabilities),
        parallel_tool_calls=all(item.parallel_tool_calls for item in capabilities),
        input_modalities=inputs,
        output_modalities=outputs,
        max_context_tokens=common_bound(tuple(item.max_context_tokens for item in capabilities)),
        max_output_tokens=common_bound(tuple(item.max_output_tokens for item in capabilities)),
        metadata={
            "source": "openrouter_catalog_intersection",
            "model_verified": False,
            "catalog_reported": True,
            "routed_models": [descriptor.id for descriptor in descriptors],
        },
    )


def require_capabilities(
    model_id: str,
    available: ModelCapabilities,
    required: ModelCapabilityRequirements,
) -> None:
    missing: list[str] = []
    for name in ("tool_calling", "structured_output", "streaming", "parallel_tool_calls"):
        if getattr(required, name) and not getattr(available, name):
            missing.append(name)
    if not set(required.input_modalities).issubset(available.input_modalities):
        missing.append("input_modalities")
    if not set(required.output_modalities).issubset(available.output_modalities):
        missing.append("output_modalities")
    if required.min_context_tokens and (
        available.max_context_tokens is None
        or available.max_context_tokens < required.min_context_tokens
    ):
        missing.append("max_context_tokens")
    if required.min_output_tokens and (
        available.max_output_tokens is None
        or available.max_output_tokens < required.min_output_tokens
    ):
        missing.append("max_output_tokens")
    if missing:
        raise CapabilityError(
            f"OpenRouter model {model_id} does not satisfy required capabilities: "
            + ", ".join(missing)
        )


class OpenRouterCatalog:
    """Fetch `/models` once per TTL; snapshots are explicit offline inputs."""

    endpoint = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        *,
        api_key: str | None = None,
        client: Any = None,
        base_url: str | None = None,
        timeout: float = 30,
        retries: int = 1,
        ttl_seconds: float = 3600,
        clock: Callable[[], float] = time.monotonic,
        offline: bool = False,
    ) -> None:
        if not math.isfinite(ttl_seconds) or ttl_seconds <= 0:
            raise ConfigurationError("Catalog TTL must be finite and positive")
        if offline and (api_key is not None or client is not None or base_url is not None):
            raise ConfigurationError("Offline catalog cannot accept network configuration")
        if not offline and (api_key is None or not api_key.strip()):
            raise ConfigurationError("OpenRouter catalog API key cannot be blank")
        self._http = (
            None
            if offline
            else HttpTransport(
                base_url or self.endpoint,
                {"Authorization": f"Bearer {api_key}"},
                client=client,
                timeout=timeout,
                retries=retries,
                error_handler=_raise_openrouter_error,
            )
        )
        self._offline = offline
        self._ttl = ttl_seconds
        self._clock = clock
        self._expires_at = 0.0
        self._models: tuple[OpenRouterModelDescriptor, ...] | None = None
        self._lock = asyncio.Lock()

    async def aclose(self) -> None:
        if self._http is not None:
            await self._http.aclose()

    async def __aenter__(self) -> OpenRouterCatalog:
        return self

    async def __aexit__(self, exc_type: object, exc: object, traceback: object) -> None:
        await self.aclose()

    def invalidate(self) -> None:
        self._expires_at = 0.0

    async def list_models(self, *, force: bool = False) -> tuple[OpenRouterModelDescriptor, ...]:
        if self._offline:
            if force:
                raise ConfigurationError("Offline catalog cannot be refreshed")
            if self._models is None:
                raise ConfigurationError("Load an offline catalog snapshot first")
            return self._models
        if not force and self._models is not None and self._clock() < self._expires_at:
            return self._models
        async with self._lock:
            if not force and self._models is not None and self._clock() < self._expires_at:
                return self._models
            if self._http is None:  # pragma: no cover - guarded by offline branch
                raise ConfigurationError("Catalog transport is unavailable")
            payload = await self._http.get("/models")
            data = payload.get("data")
            if not isinstance(data, list):
                raise ModelResponseError("Malformed OpenRouter model catalog")
            models = tuple(
                OpenRouterModelDescriptor.from_api(row) for row in data if isinstance(row, dict)
            )
            if (
                not models
                or len(models) != len(data)
                or len({model.id for model in models}) != len(models)
            ):
                raise ModelResponseError("Malformed or duplicate OpenRouter catalog entries")
            self._models = models
            self._expires_at = self._clock() + self._ttl
            return models

    async def get(self, model_id: str, *, force: bool = False) -> OpenRouterModelDescriptor:
        for descriptor in await self.list_models(force=force):
            if descriptor.id == model_id:
                return descriptor
        raise CapabilityError(f"OpenRouter catalog does not contain model {model_id}")

    def save_snapshot(self, path: str | Path) -> None:
        if self._models is None:
            raise ConfigurationError("Refresh the catalog before saving a snapshot")
        target = Path(path)
        models = [model.model_dump(mode="json") for model in self._models]
        canonical = json.dumps(models, separators=(",", ":"), sort_keys=True).encode()
        document = {
            "schema_version": 2,
            "model_count": len(models),
            "models_sha256": hashlib.sha256(canonical).hexdigest(),
            "models": models,
        }
        temporary = target.with_suffix(target.suffix + ".tmp")
        temporary.write_text(
            json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        temporary.replace(target)

    def load_snapshot(self, path: str | Path) -> tuple[OpenRouterModelDescriptor, ...]:
        try:
            document = json.loads(Path(path).read_text(encoding="utf-8"))
            version = document.get("schema_version")
            raw_models = document.get("models")
            if version not in {1, 2} or not isinstance(raw_models, list) or not raw_models:
                raise ValueError
            models = tuple(
                OpenRouterModelDescriptor.model_validate_json(json.dumps(row)) for row in raw_models
            )
            if len({model.id for model in models}) != len(models):
                raise ValueError
            if version == 2:
                canonical = json.dumps(raw_models, separators=(",", ":"), sort_keys=True).encode()
                if (
                    document.get("model_count") != len(models)
                    or document.get("models_sha256") != hashlib.sha256(canonical).hexdigest()
                ):
                    raise ValueError
        except (OSError, ValueError, TypeError, AttributeError):
            raise ConfigurationError("Invalid OpenRouter catalog snapshot") from None
        self._models = models
        self._expires_at = self._clock() + self._ttl
        return models

    @classmethod
    def from_snapshot(
        cls,
        path: str | Path,
        *,
        clock: Callable[[], float] = time.monotonic,
    ) -> OpenRouterCatalog:
        """Create a network-free catalog whose snapshot never refreshes implicitly."""

        catalog = cls(clock=clock, offline=True)
        catalog.load_snapshot(path)
        return catalog
