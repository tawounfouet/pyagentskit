"""Canonical domain errors for V2."""


class DomainError(Exception):
    """Base error raised by an invalid V2 domain operation."""


class InvalidTransitionError(DomainError):
    """Raised when an aggregate receives an invalid state transition."""


class ImmutableScopeError(DomainError):
    """Raised when an approval scope is changed after creation."""


class StaleFencingTokenError(DomainError):
    """Raised when a lease operation uses an older fencing token."""
