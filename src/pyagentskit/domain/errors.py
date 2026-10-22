"""Canonical domain errors for V2."""


class DomainError(Exception):
    """Base error raised by an invalid V2 domain operation."""


class InvalidTransitionError(DomainError):
    """Raised when an aggregate receives an invalid state transition."""


class ImmutableScopeError(DomainError):
    """Raised when an approval scope is changed after creation."""


class StaleFencingTokenError(DomainError):
    """Raised when a lease operation uses an older fencing token."""


class RuntimeNegotiationError(DomainError):
    """Raised when no runtime satisfies the requested guarantees."""


class CapabilityNegotiationError(RuntimeNegotiationError):
    """Raised when capability negotiation rejects every candidate."""


class RuntimeRegistrationError(DomainError):
    """Raised when a runtime cannot be registered safely."""


class RuntimeBindingError(DomainError):
    """Raised when a Run would violate its durable runtime binding."""


class RuntimeAdapterError(DomainError):
    """Raised when an adapter cannot honour the runtime contract."""


class RuntimeCapabilityError(RuntimeAdapterError):
    """Raised when an adapter operation is not contractually supported."""


class IdempotencyConflictError(DomainError):
    """Raised when one idempotency identity is reused for another logical intent."""


class StaleRecoveryPlanError(DomainError):
    """Raised when a RecoveryPlan is executed after its assumptions became stale."""


class ReconciliationError(DomainError):
    """Raised when an Effect cannot be reconciled safely."""


class PersistenceError(DomainError):
    """Base error raised by a V2 persistence adapter."""


class ConcurrencyConflictError(PersistenceError):
    """Raised when an optimistic concurrency compare-and-swap fails."""


class DuplicateAggregateError(PersistenceError):
    """Raised when an aggregate is inserted twice without idempotent semantics."""


class PersistenceCorruptionError(PersistenceError):
    """Raised when durable data cannot reconstruct a valid domain object."""


class InboxDigestConflictError(PersistenceError):
    """Raised when one external event id is reused with a different payload digest."""
