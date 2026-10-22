"""Small, immutable value objects shared by the V2 domain."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from re import fullmatch
from typing import Self
from uuid import uuid4


@dataclass(frozen=True, slots=True)
class Identifier:
    """Non-empty stable identifier used by domain aggregates."""

    value: str

    def __post_init__(self) -> None:
        if not self.value or len(self.value) > 128:
            raise ValueError("identifier must contain between 1 and 128 characters")
        if fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]*", self.value) is None:
            raise ValueError("identifier contains unsupported characters")

    @classmethod
    def new(cls, prefix: str = "id") -> Self:
        return cls(f"{prefix}_{uuid4().hex}")

    def __str__(self) -> str:
        return self.value


class TenantId(Identifier):
    pass


class RunId(Identifier):
    pass


class SessionId(Identifier):
    pass


class ConversationId(Identifier):
    pass


class MessageId(Identifier):
    pass


class EffectId(Identifier):
    pass


class ApprovalId(Identifier):
    pass


class LeaseId(Identifier):
    pass


class WorkerId(Identifier):
    pass


class ArtifactId(Identifier):
    pass


class RuntimeBindingId(Identifier):
    pass


class RuntimeInvocationId(Identifier):
    pass


class ReconciliationCaseId(Identifier):
    pass


class AuditEventId(Identifier):
    pass


@dataclass(frozen=True, order=True, slots=True)
class AggregateVersion:
    """Monotonic version used for optimistic concurrency."""

    value: int = 0

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("aggregate version cannot be negative")

    def next(self) -> AggregateVersion:
        return AggregateVersion(self.value + 1)


@dataclass(frozen=True, order=True, slots=True)
class FencingToken:
    """Monotonic token that prevents stale lease owners from writing."""

    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("fencing token cannot be negative")


@dataclass(frozen=True, slots=True)
class Fingerprint:
    """Canonical SHA-256 identity for an effect or external operation."""

    value: str

    def __post_init__(self) -> None:
        if fullmatch(r"[0-9a-f]{64}", self.value) is None:
            raise ValueError("fingerprint must be a lowercase SHA-256 digest")

    @classmethod
    def from_text(cls, value: str) -> Fingerprint:
        return cls(sha256(value.encode("utf-8")).hexdigest())


@dataclass(frozen=True, slots=True)
class ExternalReference:
    """Opaque reference to a system outside the domain."""

    system: str
    key: str

    def __post_init__(self) -> None:
        if not self.system or not self.key:
            raise ValueError("external reference system and key are required")


@dataclass(frozen=True, slots=True)
class ArtifactChecksum:
    """Integrity checksum for an artifact."""

    algorithm: str
    value: str

    def __post_init__(self) -> None:
        if not self.algorithm or not self.value:
            raise ValueError("artifact checksum algorithm and value are required")


def utc_now() -> datetime:
    """Return an aware UTC timestamp for domain events and aggregates."""

    return datetime.now(UTC)
