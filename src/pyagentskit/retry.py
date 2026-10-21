"""Explicit, bounded retry policy for model calls owned by the Runner."""

from __future__ import annotations

import math
from enum import StrEnum

from pydantic import Field, model_validator

from ._base import ContractModel
from .exceptions import (
    ModelAuthenticationError,
    ModelError,
    ModelRateLimitError,
    ModelResponseError,
    ModelTimeoutError,
    ModelUnavailableError,
)

__all__ = ["ModelRetryPolicy", "ModelRetryReason"]


class ModelRetryReason(StrEnum):
    """Stable categories eligible for an explicit model retry."""

    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    UNAVAILABLE = "unavailable"
    ADAPTER_RETRYABLE = "adapter_retryable"


class ModelRetryPolicy(ContractModel):
    """Serializable retry and exponential-backoff configuration.

    ``max_attempts`` includes the first call. Authentication and response
    normalization failures are never retried by this policy.
    """

    max_attempts: int = Field(default=1, ge=1, le=8)
    initial_delay_seconds: float = Field(default=0.25, ge=0, le=60)
    backoff_multiplier: float = Field(default=2.0, ge=1, le=10)
    max_delay_seconds: float = Field(default=5.0, ge=0, le=300)
    retry_on: tuple[ModelRetryReason, ...] = (
        ModelRetryReason.RATE_LIMIT,
        ModelRetryReason.TIMEOUT,
        ModelRetryReason.UNAVAILABLE,
    )
    allow_provider_fallbacks: bool = False

    @model_validator(mode="after")
    def validate_policy(self) -> ModelRetryPolicy:
        numeric = (
            self.initial_delay_seconds,
            self.backoff_multiplier,
            self.max_delay_seconds,
        )
        if any(not math.isfinite(value) for value in numeric):
            raise ValueError("Retry delays and multiplier must be finite")
        if self.max_delay_seconds < self.initial_delay_seconds:
            raise ValueError("max_delay_seconds cannot be below initial_delay_seconds")
        if len(set(self.retry_on)) != len(self.retry_on):
            raise ValueError("retry_on entries must be unique")
        return self

    @property
    def enabled(self) -> bool:
        """Return whether the policy can perform more than one attempt."""

        return self.max_attempts > 1 and bool(self.retry_on)

    def reason_for(self, error: BaseException) -> ModelRetryReason | None:
        """Classify an exception without trusting its message or provider payload."""

        reason: ModelRetryReason | None = None
        if isinstance(error, ModelAuthenticationError | ModelResponseError):
            return None
        if isinstance(error, ModelRateLimitError):
            reason = ModelRetryReason.RATE_LIMIT
        elif isinstance(error, ModelTimeoutError):
            reason = ModelRetryReason.TIMEOUT
        elif isinstance(error, ModelUnavailableError):
            reason = ModelRetryReason.UNAVAILABLE
        elif isinstance(error, ModelError) and error.retryable:
            reason = ModelRetryReason.ADAPTER_RETRYABLE
        return reason if reason in self.retry_on else None

    def delay_after(self, failed_attempt: int) -> float:
        """Return bounded deterministic backoff after a one-based attempt number."""

        if failed_attempt < 1:
            raise ValueError("failed_attempt must be positive")
        delay = self.initial_delay_seconds * self.backoff_multiplier ** (failed_attempt - 1)
        return min(delay, self.max_delay_seconds)
