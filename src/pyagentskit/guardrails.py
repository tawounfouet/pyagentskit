"""Provider-neutral guardrail contracts and deterministic policy pipeline."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable, Mapping
from enum import StrEnum
from typing import Any, Protocol, runtime_checkable

from pydantic import Field, model_validator

from ._base import ContractModel
from .exceptions import GuardrailError
from .runs import RunContext
from .types import Identifier, NonEmptyString

__all__ = [
    "CallableGuardrail",
    "Guardrail",
    "GuardrailAction",
    "GuardrailDecision",
    "GuardrailPipeline",
    "GuardrailStage",
]


class GuardrailStage(StrEnum):
    """Runtime boundaries at which untrusted data can be governed."""

    INPUT = "input"
    MODEL_REQUEST = "model_request"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    OUTPUT = "output"


class GuardrailAction(StrEnum):
    """Normalized result of a guardrail evaluation."""

    ALLOW = "allow"
    TRANSFORM = "transform"
    RETRY_WITH_FEEDBACK = "retry_with_feedback"
    REQUIRE_APPROVAL = "require_approval"
    REJECT = "reject"
    ABORT = "abort"


class GuardrailDecision(ContractModel):
    """Serializable, explainable and intentionally secret-free policy decision."""

    action: GuardrailAction
    reason: NonEmptyString
    transformed_value: Any = None
    feedback: str | None = None
    policy_id: Identifier = "guardrail"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_action_payload(self) -> GuardrailDecision:
        if self.action is GuardrailAction.TRANSFORM and self.transformed_value is None:
            raise ValueError("TRANSFORM requires transformed_value")
        if self.action is GuardrailAction.RETRY_WITH_FEEDBACK and not self.feedback:
            raise ValueError("RETRY_WITH_FEEDBACK requires feedback")
        return self


@runtime_checkable
class Guardrail(Protocol):
    """Asynchronous policy evaluated at one or more runtime boundaries."""

    @property
    def stages(self) -> tuple[GuardrailStage, ...]: ...

    async def evaluate(
        self,
        value: Any,
        *,
        stage: GuardrailStage,
        context: RunContext[Any],
    ) -> GuardrailDecision: ...


GuardrailFunction = Callable[[Any, GuardrailStage, RunContext[Any]], Awaitable[GuardrailDecision]]


class CallableGuardrail:
    """Small adapter for application-owned asynchronous policy functions."""

    def __init__(
        self,
        policy_id: str,
        stages: Iterable[GuardrailStage],
        function: GuardrailFunction,
    ) -> None:
        normalized = tuple(stages)
        if not normalized or len(set(normalized)) != len(normalized):
            raise GuardrailError("Guardrail stages must be non-empty and unique")
        self.policy_id = policy_id
        self.stages = normalized
        self._function = function

    async def evaluate(
        self,
        value: Any,
        *,
        stage: GuardrailStage,
        context: RunContext[Any],
    ) -> GuardrailDecision:
        if stage not in self.stages:
            raise GuardrailError("Guardrail evaluated at an undeclared stage")
        decision = await self._function(value, stage, context)
        if not isinstance(decision, GuardrailDecision):
            raise GuardrailError("Guardrail returned an invalid decision")
        return decision.model_copy(update={"policy_id": self.policy_id})


class GuardrailPipeline:
    """Evaluate policies in order and fail closed on policy failures."""

    def __init__(self, guardrails: Iterable[Guardrail] = ()) -> None:
        self.guardrails = tuple(guardrails)

    async def evaluate(
        self,
        value: Any,
        *,
        stage: GuardrailStage,
        context: RunContext[Any],
    ) -> tuple[Any, tuple[GuardrailDecision, ...]]:
        current = value
        decisions: list[GuardrailDecision] = []
        for guardrail in self.guardrails:
            if stage not in guardrail.stages:
                continue
            try:
                decision = await guardrail.evaluate(current, stage=stage, context=context)
            except GuardrailError:
                raise
            except Exception as exc:
                raise GuardrailError("Guardrail evaluation failed") from exc
            decisions.append(decision)
            if decision.action is GuardrailAction.ALLOW:
                continue
            if decision.action is GuardrailAction.TRANSFORM:
                current = decision.transformed_value
                continue
            return current, tuple(decisions)
        return current, tuple(decisions)

    def stages(self) -> Mapping[GuardrailStage, int]:
        """Return an inspectable count of policies registered per stage."""

        return {
            stage: sum(stage in guardrail.stages for guardrail in self.guardrails)
            for stage in GuardrailStage
        }
