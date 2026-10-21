"""Deterministic evaluation datasets, execution and regression comparison."""

from __future__ import annotations

import json
import re
from collections.abc import Awaitable, Callable
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from time import monotonic
from typing import Any, Protocol, runtime_checkable

from pydantic import Field, field_validator, model_validator

from ._base import ContractModel
from .runs import RunResult, RunStatus, utc_now
from .types import Identifier, NonEmptyString, SemanticVersion

__all__ = [
    "AssertionKind",
    "EvalAssertion",
    "EvalAssertionResult",
    "EvalCase",
    "EvalCaseResult",
    "EvalDataset",
    "EvalReport",
    "EvalTarget",
    "Evaluator",
    "JudgeScore",
    "ModelJudge",
    "RegressionComparison",
    "compare_reports",
    "load_eval_report",
    "save_eval_report",
]


class AssertionKind(StrEnum):
    """Assertions evaluated locally without another model call."""

    STATUS = "status"
    EXACT_OUTPUT = "exact_output"
    CONTAINS = "contains"
    REGEX = "regex"
    MAX_COST_USD = "max_cost_usd"
    MAX_DURATION_SECONDS = "max_duration_seconds"


class EvalAssertion(ContractModel):
    """One deterministic expectation."""

    kind: AssertionKind
    expected: Any
    case_sensitive: bool = True

    @model_validator(mode="after")
    def validate_expected_value(self) -> EvalAssertion:
        if self.kind in {
            AssertionKind.MAX_COST_USD,
            AssertionKind.MAX_DURATION_SECONDS,
        } and (not isinstance(self.expected, int | float) or self.expected < 0):
            raise ValueError(f"{self.kind.value} requires a non-negative number")
        if self.kind is AssertionKind.STATUS:
            try:
                RunStatus(self.expected)
            except (TypeError, ValueError) as exc:
                raise ValueError("status assertion requires a valid RunStatus value") from exc
        if self.kind is AssertionKind.REGEX:
            try:
                re.compile(str(self.expected))
            except re.error as exc:
                raise ValueError("regex assertion contains an invalid expression") from exc
        return self


class EvalCase(ContractModel):
    """Versioned input plus deterministic expectations."""

    id: Identifier
    input: NonEmptyString
    assertions: tuple[EvalAssertion, ...]
    tags: tuple[Identifier, ...] = ()
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_case(self) -> EvalCase:
        if not self.assertions:
            raise ValueError("an evaluation case requires at least one assertion")
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("evaluation tags must be unique")
        return self


class EvalDataset(ContractModel):
    """Portable deterministic evaluation dataset."""

    id: Identifier
    version: SemanticVersion
    cases: tuple[EvalCase, ...]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_dataset(self) -> EvalDataset:
        if not self.cases:
            raise ValueError("an evaluation dataset requires at least one case")
        ids = [case.id for case in self.cases]
        if len(set(ids)) != len(ids):
            raise ValueError("evaluation case IDs must be unique")
        return self


class EvalAssertionResult(ContractModel):
    """Evidence for one deterministic assertion."""

    kind: AssertionKind
    passed: bool
    expected: Any
    actual: Any = None
    message: str | None = None


class JudgeScore(ContractModel):
    """Advisory model-judge result, kept separate from deterministic pass/fail."""

    judge_id: Identifier
    score: float = Field(ge=0, le=1)
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalCaseResult(ContractModel):
    """One case outcome with separate deterministic and advisory evidence."""

    case_id: Identifier
    passed: bool
    assertions: tuple[EvalAssertionResult, ...]
    duration_seconds: float = Field(ge=0)
    run_result: RunResult[Any]
    judge_scores: tuple[JudgeScore, ...] = ()


class EvalReport(ContractModel):
    """Serializable evaluation result suitable for regression comparison."""

    schema_version: str = "1.0"
    dataset_id: Identifier
    dataset_version: SemanticVersion
    created_at: datetime
    duration_seconds: float = Field(ge=0)
    results: tuple[EvalCaseResult, ...]
    passed_cases: int = Field(ge=0)
    failed_cases: int = Field(ge=0)
    pass_rate: float = Field(ge=0, le=1)
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("created_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("evaluation timestamps must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_counts(self) -> EvalReport:
        if self.passed_cases + self.failed_cases != len(self.results):
            raise ValueError("evaluation counts do not match results")
        expected_rate = self.passed_cases / len(self.results) if self.results else 0.0
        if abs(self.pass_rate - expected_rate) > 1e-12:
            raise ValueError("evaluation pass rate does not match results")
        return self


class RegressionComparison(ContractModel):
    """Exact comparison between two reports for the same dataset."""

    dataset_id: Identifier
    baseline_version: SemanticVersion
    candidate_version: SemanticVersion
    pass_rate_delta: float
    duration_delta_seconds: float
    regressed_case_ids: tuple[Identifier, ...] = ()
    improved_case_ids: tuple[Identifier, ...] = ()
    acceptable: bool


@runtime_checkable
class EvalTarget(Protocol):
    """Application-owned callable target used by the deterministic evaluator."""

    def __call__(self, case: EvalCase) -> Awaitable[RunResult[Any]]: ...


@runtime_checkable
class ModelJudge(Protocol):
    """Optional advisory judge; never replaces deterministic security assertions."""

    def score(self, case: EvalCase, result: RunResult[Any]) -> Awaitable[JudgeScore]: ...


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def _assert(
    assertion: EvalAssertion, result: RunResult[Any], duration: float
) -> EvalAssertionResult:
    actual: Any
    if assertion.kind is AssertionKind.STATUS:
        actual = result.status.value
        passed = actual == str(assertion.expected)
    elif assertion.kind is AssertionKind.MAX_COST_USD:
        actual = result.usage.estimated_cost_usd
        passed = actual is not None and actual <= float(assertion.expected)
    elif assertion.kind is AssertionKind.MAX_DURATION_SECONDS:
        actual = duration
        passed = duration <= float(assertion.expected)
    else:
        actual = _text(result.output)
        expected = str(assertion.expected)
        haystack = actual if assertion.case_sensitive else actual.casefold()
        needle = expected if assertion.case_sensitive else expected.casefold()
        if assertion.kind is AssertionKind.EXACT_OUTPUT:
            passed = haystack == needle
        elif assertion.kind is AssertionKind.CONTAINS:
            passed = needle in haystack
        else:
            flags = 0 if assertion.case_sensitive else re.IGNORECASE
            passed = re.search(expected, actual, flags) is not None
    return EvalAssertionResult(
        kind=assertion.kind,
        passed=passed,
        expected=assertion.expected,
        actual=actual,
        message=None if passed else f"{assertion.kind.value} assertion failed",
    )


class Evaluator:
    """Sequential deterministic evaluator with optional advisory judges."""

    def __init__(
        self,
        *,
        clock: Callable[[], datetime] = utc_now,
        timer: Callable[[], float] = monotonic,
        judges: tuple[ModelJudge, ...] = (),
    ) -> None:
        self.clock = clock
        self.timer = timer
        self.judges = judges

    async def evaluate(
        self,
        dataset: EvalDataset,
        target: EvalTarget,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> EvalReport:
        """Execute cases in declared order and preserve exact evidence."""

        started = self.timer()
        results: list[EvalCaseResult] = []
        for case in dataset.cases:
            case_started = self.timer()
            run_result = await target(case)
            duration = max(0.0, self.timer() - case_started)
            assertions = tuple(_assert(item, run_result, duration) for item in case.assertions)
            judge_scores = tuple([await judge.score(case, run_result) for judge in self.judges])
            results.append(
                EvalCaseResult(
                    case_id=case.id,
                    passed=all(item.passed for item in assertions),
                    assertions=assertions,
                    duration_seconds=duration,
                    run_result=run_result,
                    judge_scores=judge_scores,
                )
            )
        passed = sum(item.passed for item in results)
        return EvalReport(
            dataset_id=dataset.id,
            dataset_version=dataset.version,
            created_at=self.clock(),
            duration_seconds=max(0.0, self.timer() - started),
            results=tuple(results),
            passed_cases=passed,
            failed_cases=len(results) - passed,
            pass_rate=passed / len(results),
            metadata=dict(metadata or {}),
        )


def compare_reports(
    baseline: EvalReport,
    candidate: EvalReport,
    *,
    max_pass_rate_regression: float = 0.0,
) -> RegressionComparison:
    """Compare matching cases and reject a pass-rate regression over the threshold."""

    if baseline.dataset_id != candidate.dataset_id:
        raise ValueError("evaluation reports belong to different datasets")
    if max_pass_rate_regression < 0:
        raise ValueError("max_pass_rate_regression must be non-negative")
    baseline_cases = {item.case_id: item.passed for item in baseline.results}
    candidate_cases = {item.case_id: item.passed for item in candidate.results}
    if baseline_cases.keys() != candidate_cases.keys():
        raise ValueError("evaluation reports contain different case IDs")
    regressed = tuple(
        case_id
        for case_id in baseline_cases
        if baseline_cases[case_id] and not candidate_cases[case_id]
    )
    improved = tuple(
        case_id
        for case_id in baseline_cases
        if not baseline_cases[case_id] and candidate_cases[case_id]
    )
    delta = candidate.pass_rate - baseline.pass_rate
    return RegressionComparison(
        dataset_id=baseline.dataset_id,
        baseline_version=baseline.dataset_version,
        candidate_version=candidate.dataset_version,
        pass_rate_delta=delta,
        duration_delta_seconds=candidate.duration_seconds - baseline.duration_seconds,
        regressed_case_ids=regressed,
        improved_case_ids=improved,
        acceptable=delta >= -max_pass_rate_regression,
    )


def save_eval_report(report: EvalReport, path: str | Path) -> None:
    """Persist one deterministic report as canonical UTF-8 JSON."""

    Path(path).write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")


def load_eval_report(path: str | Path) -> EvalReport:
    """Load and validate a report before comparison."""

    return EvalReport.model_validate_json(Path(path).read_text(encoding="utf-8"))
