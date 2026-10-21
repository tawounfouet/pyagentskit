"""Normalized PyAgentsKit exception hierarchy."""

from typing import Any


class PyAgentsKitError(Exception):
    """Base class for all framework errors."""


class ConfigurationError(PyAgentsKitError):
    """Configuration is incomplete, invalid or internally inconsistent."""


class AgentDefinitionError(ConfigurationError):
    """An agent definition cannot be accepted."""


class CapabilityError(ConfigurationError):
    """A selected model or adapter cannot satisfy required capabilities."""


class ModelError(PyAgentsKitError):
    """A model adapter failed to complete a request."""

    def __init__(
        self,
        message: str,
        *,
        retryable: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.retryable = retryable
        self.metadata = dict(metadata or {})


class ModelAuthenticationError(ModelError):
    """Provider authentication failed."""


class ModelRateLimitError(ModelError):
    """A provider rate limit was reached."""


class ModelTimeoutError(ModelError):
    """A model call exceeded its timeout."""


class ModelUnavailableError(ModelError):
    """The requested model or upstream provider is unavailable."""


class ModelResponseError(ModelError):
    """A provider response could not be normalized or validated."""


class ToolError(PyAgentsKitError):
    """Base class for tool-related failures."""


class ToolNotFoundError(ToolError):
    """A requested tool is not registered."""


class ToolAlreadyRegisteredError(ToolError):
    """A tool name is already present in the registry."""


class ToolValidationError(ToolError):
    """Tool arguments or output failed schema validation."""


class ToolPermissionError(ToolError):
    """Runtime policy denied a tool call."""


class ToolTimeoutError(ToolError):
    """Tool execution exceeded its timeout."""


class ToolExecutionError(ToolError):
    """Tool code failed during execution."""


class GuardrailError(PyAgentsKitError):
    """A guardrail failed or rejected an operation."""


class PrivacyPolicyError(GuardrailError):
    """Classified data cannot cross the configured provider boundary."""


class ApprovalError(PyAgentsKitError):
    """An approval request could not be created or resolved."""


class ApprovalNotFoundError(ApprovalError):
    """An approval is absent, expired or outside the requested tenant scope."""


class ApprovalConflictError(ApprovalError):
    """An approval revision or state changed before an operation completed."""


class SessionError(PyAgentsKitError):
    """Session state could not be loaded or stored."""


class SessionNotFoundError(SessionError):
    """A session is absent, expired or outside the requested tenant scope."""


class SessionConflictError(SessionError):
    """A session revision changed before an optimistic write completed."""


class ContextBudgetError(SessionError):
    """Required conversation content cannot fit the configured context budget."""


class PersistenceError(PyAgentsKitError):
    """Durable state could not be read or written."""


class RunStoreError(PersistenceError):
    """Durable run state could not be read or changed."""


class RunNotFoundError(RunStoreError):
    """A durable run is absent or outside the requested tenant scope."""


class RunConflictError(RunStoreError):
    """A durable run or effect revision changed before an atomic write."""


class UnknownEffectError(RunStoreError):
    """An external effect must be reconciled before a run can continue."""


class ArtifactNotFoundError(PersistenceError):
    """An artifact is absent, expired or outside the requested tenant scope."""


class ArtifactIntegrityError(PersistenceError):
    """Artifact bytes do not match their persisted integrity metadata."""


class RunCancelledError(PyAgentsKitError):
    """A run was cancelled before completion."""


class RunLimitExceededError(PyAgentsKitError):
    """A configured run limit was exceeded."""
