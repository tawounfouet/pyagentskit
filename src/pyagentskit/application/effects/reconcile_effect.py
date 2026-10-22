"""Application orchestration for safe Effect reconciliation."""

from __future__ import annotations

from dataclasses import dataclass, replace

from ...contracts.audit import AuditSink
from ...contracts.effects import EffectRepository, ReconciliationPort, ReconciliationRepository
from ...domain.effects import (
    Effect,
    ReconciliationCase,
    ReconciliationObservation,
    ReconciliationResolution,
    ReconciliationStrategy,
)
from ...domain.entities import AuditEvent
from ...domain.errors import ReconciliationError
from ...domain.lifecycle import EffectStatus, ReconciliationStatus
from ...domain.shared import EffectId


@dataclass(frozen=True, slots=True)
class ReconcileEffectResult:
    effect: Effect
    case: ReconciliationCase
    observation: ReconciliationObservation


class ReconcileEffect:
    """Resolve ambiguous external reality without replaying the Effect."""

    def __init__(
        self,
        *,
        effects: EffectRepository,
        reconciliations: ReconciliationRepository,
        port: ReconciliationPort,
        audit: AuditSink,
    ) -> None:
        self._effects = effects
        self._reconciliations = reconciliations
        self._port = port
        self._audit = audit

    async def execute(
        self,
        effect_id: EffectId,
        *,
        strategy: ReconciliationStrategy = ReconciliationStrategy.MANUAL_ONLY,
        max_attempts: int = 3,
    ) -> ReconcileEffectResult:
        effect = await self._effects.get(effect_id)
        expected_effect_version = effect.version

        if effect.status is EffectStatus.STARTED:
            effect = effect.mark_unknown()
        if effect.status is EffectStatus.UNKNOWN:
            effect = effect.open_reconciliation()
        if effect.status is not EffectStatus.RECONCILIATION_REQUIRED:
            raise ReconciliationError(
                f"effect {effect.id} in state {effect.status.value} does not require reconciliation"
            )

        case = await self._reconciliations.get_active(effect.id)
        expected_case_version = None if case is None else case.version
        if case is None:
            case = ReconciliationCase(
                effect_id=effect.id,
                reason="external effect outcome is ambiguous",
                strategy=strategy,
                max_attempts=max_attempts,
            )

        if case.status in {ReconciliationStatus.PENDING, ReconciliationStatus.FAILED}:
            case = case.start()
        elif case.status is ReconciliationStatus.MANUAL_REVIEW:
            raise ReconciliationError("reconciliation requires manual review")

        observation = await self._port.reconcile(effect, case)
        evidence = tuple(
            item if item.case_id == case.id else replace(item, case_id=case.id)
            for item in observation.evidence
        )
        for item in evidence:
            await self._reconciliations.append_evidence(item)

        case = case.record_result(observation.resolution, detail=observation.detail)

        if observation.resolution is ReconciliationResolution.CONFIRMED_SUCCESS:
            effect = effect.reconcile_success(
                external_reference=observation.external_reference,
            )
        elif observation.resolution is ReconciliationResolution.CONFIRMED_FAILURE:
            effect = effect.reconcile_failure()

        await self._effects.save(effect, expected_version=expected_effect_version)
        await self._reconciliations.save(case, expected_version=expected_case_version)
        await self._audit.append(
            AuditEvent(
                event_type="effect.reconciliation_decided",
                subject=str(effect.id),
                metadata=(
                    ("case_id", str(case.id)),
                    ("resolution", observation.resolution.value),
                    ("status", case.status.value),
                ),
            )
        )
        return ReconcileEffectResult(effect=effect, case=case, observation=observation)
