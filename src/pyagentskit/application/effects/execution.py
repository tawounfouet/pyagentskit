"""Application boundary that makes durable Effect intent precede external sends."""

from __future__ import annotations

from dataclasses import dataclass

from ...contracts.audit import AuditSink
from ...contracts.effects import EffectRepository
from ...domain.effects import Effect
from ...domain.entities import AuditEvent
from ...domain.errors import ReconciliationError
from ...domain.lifecycle import EffectStatus
from ...domain.shared import ExternalReference, OwnershipContext


@dataclass(frozen=True, slots=True)
class EffectPreparation:
    """Result of the pre-send gate.

    The execute flag is true only when the caller may cross the external
    side-effect boundary. A previously succeeded Effect is reused instead of replayed.
    """

    effect: Effect
    execute: bool
    reused: bool = False


class EffectExecutionGate:
    """Split local durable transactions from the external call boundary."""

    def __init__(self, *, effects: EffectRepository, audit: AuditSink) -> None:
        self._effects = effects
        self._audit = audit

    async def prepare(
        self,
        effect: Effect,
        *,
        ownership: OwnershipContext | None = None,
        protected: bool = False,
    ) -> EffectPreparation:
        reservation = await self._effects.reserve(effect)
        durable = reservation.effect
        durable.assert_same_intent(effect.idempotency_key, effect.fingerprint)

        if durable.status is EffectStatus.SUCCEEDED:
            return EffectPreparation(effect=durable, execute=False, reused=True)

        if durable.status is not EffectStatus.NOT_STARTED:
            raise ReconciliationError(
                "effect is not replay-safe; recovery/reconciliation must decide the next step"
            )

        started = durable.begin(ownership=ownership, protected=protected)
        await self._effects.save(started, expected_version=durable.version)
        await self._audit.append(
            AuditEvent(
                event_type="effect.started",
                subject=str(started.id),
                metadata=(
                    ("kind", str(started.kind)),
                    ("protected", str(protected).lower()),
                ),
            )
        )
        return EffectPreparation(effect=started, execute=True)

    async def confirm_success(
        self,
        effect: Effect,
        *,
        external_reference: ExternalReference | None = None,
    ) -> Effect:
        succeeded = effect.mark_succeeded(external_reference=external_reference)
        await self._effects.save(succeeded, expected_version=effect.version)
        await self._audit.append(
            AuditEvent(
                event_type="effect.succeeded",
                subject=str(succeeded.id),
            )
        )
        return succeeded

    async def confirm_failure(self, effect: Effect) -> Effect:
        failed = effect.mark_failed()
        await self._effects.save(failed, expected_version=effect.version)
        await self._audit.append(
            AuditEvent(
                event_type="effect.failed",
                subject=str(failed.id),
            )
        )
        return failed

    async def mark_unknown(self, effect: Effect, *, reason: str) -> Effect:
        if not reason:
            raise ValueError("unknown effect outcome requires a reason")
        unknown = effect.mark_unknown()
        await self._effects.save(unknown, expected_version=effect.version)
        await self._audit.append(
            AuditEvent(
                event_type="effect.outcome_unknown",
                subject=str(unknown.id),
                metadata=(("reason", reason),),
            )
        )
        return unknown
