from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from pydantic import ValidationError

from pyagentskit import RunContext, RunError, RunLimits, RunResult, RunStatus


class RunContractTests(unittest.TestCase):
    def test_context_generates_full_identifiers(self) -> None:
        context = RunContext(agent_id="support.triage", deps={"tenant": "demo"})

        self.assertNotEqual(context.run_id, context.trace_id)
        self.assertIsNotNone(context.started_at.utcoffset())

    def test_context_rejects_naive_time(self) -> None:
        with self.assertRaises(ValueError):
            RunContext(
                agent_id="support.triage",
                deps=None,
                started_at=datetime(2026, 9, 4),
            )

    def test_limits_are_positive(self) -> None:
        with self.assertRaises(ValidationError):
            RunLimits(max_steps=0)

    def test_completed_result_is_terminal(self) -> None:
        now = datetime.now(UTC)
        result = RunResult[str](
            run_id=uuid4(),
            trace_id=uuid4(),
            agent_id="support.triage",
            status=RunStatus.COMPLETED,
            output="done",
            started_at=now,
            completed_at=now + timedelta(seconds=1),
        )

        self.assertTrue(result.status.is_terminal)
        self.assertEqual(result.output, "done")

    def test_failed_result_requires_error(self) -> None:
        now = datetime.now(UTC)
        with self.assertRaises(ValidationError):
            RunResult[None](
                run_id=uuid4(),
                trace_id=uuid4(),
                agent_id="support.triage",
                status=RunStatus.FAILED,
                started_at=now,
                completed_at=now,
            )

    def test_failed_result_accepts_normalized_error(self) -> None:
        now = datetime.now(UTC)
        result = RunResult[None](
            run_id=uuid4(),
            trace_id=uuid4(),
            agent_id="support.triage",
            status=RunStatus.FAILED,
            error=RunError(type="model.timeout", message="Provider timed out", retryable=True),
            started_at=now,
            completed_at=now,
        )

        self.assertTrue(result.error and result.error.retryable)

    def test_result_rejects_reversed_timestamps(self) -> None:
        now = datetime.now(UTC)
        with self.assertRaises(ValidationError):
            RunResult[str](
                run_id=uuid4(),
                trace_id=uuid4(),
                agent_id="support.triage",
                status=RunStatus.COMPLETED,
                output="done",
                started_at=now,
                completed_at=now - timedelta(seconds=1),
            )


if __name__ == "__main__":
    unittest.main()
