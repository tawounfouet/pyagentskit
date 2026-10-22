"""Provider-neutral event semantics for PyAgentsKit V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Mapping
from uuid import uuid4

from .shared import TenantId, utc_now


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """An in-process fact emitted by the domain/application boundary."""

    name: str
    aggregate_type: str
    aggregate_id: str
    payload: Mapping[str, object] = field(default_factory=dict)
    tenant_id: TenantId | None = None
    event_id: str = field(default_factory=lambda: uuid4().hex)
    occurred_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.name or not self.aggregate_type or not self.aggregate_id:
            raise ValueError("domain event name and aggregate identity are required")


@dataclass(frozen=True, slots=True)
class IntegrationEvent:
    """Durable event intended to cross a process/system boundary."""

    name: str
    payload: Mapping[str, object] = field(default_factory=dict)
    tenant_id: TenantId | None = None
    aggregate_type: str | None = None
    aggregate_id: str | None = None
    event_id: str = field(default_factory=lambda: uuid4().hex)
    occurred_at: datetime = field(default_factory=utc_now)

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("integration event name is required")
