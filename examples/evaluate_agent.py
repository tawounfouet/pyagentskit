"""Run a deterministic offline evaluation and write its JSON report."""

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pyagentskit import (
    AssertionKind,
    EvalAssertion,
    EvalCase,
    EvalDataset,
    Evaluator,
    RunResult,
    RunStatus,
    save_eval_report,
)


async def target(case: EvalCase) -> RunResult[str]:
    now = datetime.now(UTC)
    return RunResult(
        run_id=uuid4(),
        trace_id=uuid4(),
        agent_id="example.agent",
        status=RunStatus.COMPLETED,
        output=f"Hello, {case.input}!",
        started_at=now,
        completed_at=now,
    )


async def main() -> None:
    dataset = EvalDataset(
        id="example.greetings",
        version="1.0.0",
        cases=(
            EvalCase(
                id="alice",
                input="Alice",
                assertions=(
                    EvalAssertion(kind=AssertionKind.STATUS, expected="completed"),
                    EvalAssertion(kind=AssertionKind.CONTAINS, expected="Hello, Alice"),
                ),
            ),
        ),
    )
    report = await Evaluator().evaluate(dataset, target)
    destination = Path("eval-report.json")
    save_eval_report(report, destination)
    print(f"pass_rate={report.pass_rate:.0%} report={destination}")


if __name__ == "__main__":
    asyncio.run(main())
