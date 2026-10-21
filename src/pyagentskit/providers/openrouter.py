"""Minimal deterministic OpenRouter Chat Completions adapter."""

from __future__ import annotations

import os
from decimal import Decimal, InvalidOperation
from typing import TYPE_CHECKING, Any, NoReturn
from urllib.parse import urlsplit

from ..exceptions import (
    CapabilityError,
    ConfigurationError,
    ModelAuthenticationError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)
from ..models import Modality, ModelCapabilities, ModelRequest, ModelResponse
from ..usage import Usage
from ._http import HttpTransport
from .openai import OpenAIModel
from .openrouter_routing import OpenRouterDataPolicy, OpenRouterRoutingPolicy

__all__ = ["OpenRouterModel"]

if TYPE_CHECKING:
    from .openrouter_catalog import (
        ModelCapabilityRequirements,
        OpenRouterCatalog,
    )


def _safe_error_metadata(status: int, payload: dict[str, Any] | None) -> dict[str, Any]:
    error = payload.get("error") if payload else None
    error = error if isinstance(error, dict) else {}
    upstream = error.get("metadata")
    upstream = upstream if isinstance(upstream, dict) else {}
    metadata: dict[str, Any] = {"router": "openrouter", "http_status": status}
    for target, value in {
        "error_code": error.get("code"),
        "error_type": upstream.get("error_type"),
        "provider_code": upstream.get("provider_code"),
    }.items():
        if isinstance(value, (str, int)) and not isinstance(value, bool):
            metadata[target] = value
    router = payload.get("openrouter_metadata") if payload else None
    if isinstance(router, dict):
        attempt = router.get("attempt")
        for target, value in {
            "route_strategy": router.get("strategy"),
            "route_region": router.get("region"),
            "route_attempt": attempt,
        }.items():
            if isinstance(value, (str, int)) and not isinstance(value, bool):
                metadata[target] = value
        if isinstance(attempt, int) and not isinstance(attempt, bool):
            metadata["fallback_used"] = attempt > 1
        endpoints = router.get("endpoints")
        available = endpoints.get("available") if isinstance(endpoints, dict) else None
        if isinstance(available, list):
            for endpoint in available:
                if isinstance(endpoint, dict) and endpoint.get("selected") is True:
                    provider = endpoint.get("provider")
                    if isinstance(provider, str):
                        metadata["upstream_provider"] = provider
                    break
    return metadata


def _safe_route_metadata(
    raw: dict[str, Any],
    *,
    requested_model: str,
    resolved_model: str,
) -> dict[str, Any]:
    router = raw.get("openrouter_metadata")
    router = router if isinstance(router, dict) else {}
    attempt = router.get("attempt")
    attempt = attempt if isinstance(attempt, int) and not isinstance(attempt, bool) else None
    endpoint_provider: str | None = None
    endpoints = router.get("endpoints")
    available = endpoints.get("available") if isinstance(endpoints, dict) else None
    if isinstance(available, list):
        for endpoint in available:
            if isinstance(endpoint, dict) and endpoint.get("selected") is True:
                candidate = endpoint.get("provider")
                if isinstance(candidate, str):
                    endpoint_provider = candidate
                break
    upstream_provider = raw.get("provider")
    if not isinstance(upstream_provider, str):
        upstream_provider = endpoint_provider
    return {
        "router": "openrouter",
        "requested_model": requested_model,
        "resolved_model": resolved_model,
        "upstream_provider": upstream_provider,
        "fallback_used": resolved_model != requested_model or (attempt is not None and attempt > 1),
        "route_strategy": (
            router.get("strategy") if isinstance(router.get("strategy"), str) else None
        ),
        "route_region": (router.get("region") if isinstance(router.get("region"), str) else None),
        "route_attempt": attempt,
        "is_byok": router.get("is_byok") if isinstance(router.get("is_byok"), bool) else None,
    }


def _raise_openrouter_error(status: int, payload: dict[str, Any] | None) -> NoReturn:
    metadata = _safe_error_metadata(status, payload)
    error_type = metadata.get("error_type")
    if error_type == "authentication" or (status in {401, 403} and error_type is None):
        raise ModelAuthenticationError("OpenRouter authentication rejected", metadata=metadata)
    if error_type == "rate_limit_exceeded" or status == 429:
        raise ModelRateLimitError(
            "OpenRouter rate limit reached", retryable=True, metadata=metadata
        )
    if error_type == "timeout" or status == 408:
        raise ModelTimeoutError("OpenRouter request timed out", retryable=True, metadata=metadata)
    if error_type in {"provider_overloaded", "provider_unavailable", "server"} or status >= 500:
        raise ModelUnavailableError(
            "OpenRouter provider unavailable", retryable=True, metadata=metadata
        )
    raise ModelResponseError("OpenRouter rejected the request", metadata=metadata)


class OpenRouterModel(OpenAIModel):
    """Access explicit models through inspectable OpenRouter routing policy."""

    provider = "openrouter"
    endpoint = "https://openrouter.ai/api/v1"
    key_variable = "OPENROUTER_API_KEY"

    def __init__(
        self,
        model: str,
        *,
        api_key: str | None = None,
        client: Any = None,
        base_url: str | None = None,
        timeout: float = 60,
        retries: int = 0,
        capabilities: ModelCapabilities | None = None,
        app_url: str | None = None,
        app_title: str | None = None,
        allow_fallbacks: bool = False,
        require_parameters: bool = True,
        routing: OpenRouterRoutingPolicy | None = None,
        include_router_metadata: bool = True,
    ) -> None:
        normalized_model = model.strip()
        organization, separator, model_name = normalized_model.partition("/")
        if not separator or not organization.strip() or not model_name.strip():
            raise ConfigurationError("OpenRouter model must include its organization prefix")
        if not isinstance(allow_fallbacks, bool) or not isinstance(require_parameters, bool):
            raise ConfigurationError("OpenRouter routing flags must be booleans")
        if not isinstance(include_router_metadata, bool):
            raise ConfigurationError("include_router_metadata must be a boolean")
        if routing is not None and (allow_fallbacks or not require_parameters):
            raise ConfigurationError("Use routing or legacy routing flags, not both")
        if routing is not None and not isinstance(routing, OpenRouterRoutingPolicy):
            raise ConfigurationError("routing must be an OpenRouterRoutingPolicy")
        policy = routing or OpenRouterRoutingPolicy(
            allow_fallbacks=allow_fallbacks,
            require_parameters=require_parameters,
            data=OpenRouterDataPolicy(),
        )
        policy.validate_local_retries(retries)
        if normalized_model in policy.model_fallbacks:
            raise ConfigurationError("The primary model cannot also be a fallback")
        key = api_key or os.getenv(self.key_variable)
        if not key or not key.strip():
            raise ConfigurationError(f"Set {self.key_variable} or provide api_key")
        headers = {"Authorization": f"Bearer {key}"}
        if app_url is not None:
            parts = urlsplit(app_url)
            if (
                parts.scheme != "https"
                or not parts.hostname
                or parts.username
                or parts.password
                or parts.query
                or parts.fragment
            ):
                raise ConfigurationError("OpenRouter app_url must be an HTTPS URL")
            headers["HTTP-Referer"] = app_url.rstrip("/")
        if app_title is not None:
            normalized_title = app_title.strip()
            if not normalized_title:
                raise ConfigurationError("OpenRouter app_title cannot be blank")
            headers["X-OpenRouter-Title"] = normalized_title
        if include_router_metadata:
            headers["X-OpenRouter-Metadata"] = "enabled"
        self.model = normalized_model
        self.routing = policy
        self.allow_fallbacks = policy.allow_fallbacks
        self.require_parameters = policy.require_parameters
        self._capabilities = capabilities or ModelCapabilities(
            tool_calling=True,
            structured_output=True,
            streaming=True,
            parallel_tool_calls=True,
            input_modalities=(Modality.TEXT, Modality.IMAGE),
            metadata={
                "source": "adapter_default",
                "model_verified": False,
                "router": "openrouter",
            },
        )
        self._http = HttpTransport(
            base_url or self.endpoint,
            headers,
            client=client,
            timeout=timeout,
            retries=retries,
            error_handler=_raise_openrouter_error,
        )

    @classmethod
    async def from_catalog(
        cls,
        model: str,
        *,
        catalog: OpenRouterCatalog,
        requirements: ModelCapabilityRequirements | None = None,
        **kwargs: Any,
    ) -> OpenRouterModel:
        """Resolve current catalog capabilities and fail before generation if required."""

        from .openrouter_catalog import (
            ModelCapabilityRequirements,
            common_capabilities,
            require_capabilities,
        )

        if "capabilities" in kwargs:
            raise ConfigurationError("from_catalog determines capabilities; do not override them")
        required = requirements or ModelCapabilityRequirements()
        routing = kwargs.get("routing")
        fallback_models = (
            routing.model_fallbacks if isinstance(routing, OpenRouterRoutingPolicy) else ()
        )
        requested_models = (model, *fallback_models)
        available = {descriptor.id: descriptor for descriptor in await catalog.list_models()}
        missing = [model_id for model_id in requested_models if model_id not in available]
        if missing:
            raise CapabilityError(
                "OpenRouter catalog does not contain routed model(s): " + ", ".join(missing)
            )
        descriptors = tuple(available[model_id] for model_id in requested_models)
        for descriptor in descriptors:
            require_capabilities(descriptor.id, descriptor.capabilities, required)
        return cls(model, capabilities=common_capabilities(descriptors), **kwargs)

    def _body(self, request: ModelRequest, *, stream: bool = False) -> dict[str, Any]:
        body = super()._body(request, stream=stream)
        if "max_completion_tokens" in body:
            body["max_tokens"] = body.pop("max_completion_tokens")
        body.pop("stream_options", None)
        for tool in body.get("tools", []):
            tool["function"].pop("strict", None)
        body["provider"] = self.routing.to_provider()
        if self.routing.model_fallbacks:
            body.pop("model", None)
            body["models"] = [self.model, *self.routing.model_fallbacks]
        return body

    @staticmethod
    def _usage(data: dict[str, Any]) -> Usage:
        cost: Decimal | None = None
        if data.get("cost") is not None:
            try:
                cost = Decimal(str(data["cost"]))
            except (InvalidOperation, ValueError):
                raise ModelResponseError("Malformed OpenRouter usage cost") from None
        return Usage(
            input_tokens=data.get("prompt_tokens", 0),
            output_tokens=data.get("completion_tokens", 0),
            cached_input_tokens=(data.get("prompt_tokens_details") or {}).get("cached_tokens", 0),
            reasoning_tokens=(data.get("completion_tokens_details") or {}).get(
                "reasoning_tokens", 0
            ),
            model_calls=1,
            estimated_cost_usd=cost,
        )

    def _response(self, raw: dict[str, Any], request: ModelRequest) -> ModelResponse:
        choice = raw.get("choices", [{}])[0]
        if isinstance(choice, dict) and isinstance(choice.get("error"), dict):
            _raise_openrouter_error(
                200,
                {
                    "error": choice["error"],
                    "openrouter_metadata": raw.get("openrouter_metadata"),
                },
            )
        response = super()._response(raw, request)
        raw_usage = raw.get("usage")
        usage: dict[str, Any] = raw_usage if isinstance(raw_usage, dict) else {}
        resolved_model = raw.get("model", self.model)
        if not isinstance(resolved_model, str):
            raise ModelResponseError("Malformed OpenRouter resolved model")
        route = _safe_route_metadata(
            raw,
            requested_model=self.model,
            resolved_model=resolved_model,
        )
        metadata = {
            **response.metadata,
            **route,
            "generation_id": raw.get("id"),
            "is_byok": (route["is_byok"] if route["is_byok"] is not None else usage.get("is_byok")),
            "openrouter_cost": usage.get("cost"),
        }
        return response.model_copy(update={"metadata": metadata})

    def _stream_event_metadata(self, chunk: dict[str, Any]) -> dict[str, Any]:
        resolved = chunk.get("model", self.model)
        resolved = resolved if isinstance(resolved, str) else self.model
        route = _safe_route_metadata(
            chunk,
            requested_model=self.model,
            resolved_model=resolved,
        )
        if not isinstance(chunk.get("openrouter_metadata"), dict):
            route = {
                key: value
                for key, value in route.items()
                if key in {"router", "requested_model", "resolved_model", "fallback_used"}
            }
        generation_id = chunk.get("id")
        if isinstance(generation_id, str):
            route["generation_id"] = generation_id
        return route
