"""Outbound ports for Effect reconciliation."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ..domain.effects import Effect, ReconciliationCase, ReconciliationEvidence, ReconciliationObservation
from ..domain.shared import AggregateVersion, EffectId


@runtime_checkable
class ReconciliationPort(Protocol):
    """Read-only connector used to establish external Effect reality."""

    async def reconcile(
        self,
        effect: Effect,
        case: ReconciliationCase,
    ) -> ReconciliationObservation: ...


@runtime_checkable
class EffectRepository(Protocol):
    async def get(self, effect_id: EffectId) -> Effect: ...

    async def save(
        self,
        effect: Effect,
        *,
        expected_version: AggregateVersion,
    ) -> None: ...


@runtime_checkable
class ReconciliationRepository(Protocol):
    async def get_active(self, effect_id: EffectId) -> ReconciliationCase | None: ...

    async def save(
        self,
        case: ReconciliationCase,
        *,
        expected_version: AggregateVersion | None,
    ) -> None: ...

    async def append_evidence(self, evidence: ReconciliationEvidence) -> None: ...
