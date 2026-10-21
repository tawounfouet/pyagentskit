from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from uuid import uuid4

from pyagentskit import (
    AgentDefinition,
    AgentEvent,
    AssertionKind,
    DoctorStatus,
    EvalAssertion,
    EvalCase,
    EvalDataset,
    Evaluator,
    EventType,
    JudgeScore,
    ModelRef,
    OpenTelemetryEventSink,
    RunResult,
    RunStatus,
    RuntimeMetricsSink,
    Usage,
    compare_reports,
    load_eval_report,
    run_doctor,
    save_eval_report,
)
from pyagentskit.cli import main


def result(output: str, *, status: RunStatus = RunStatus.COMPLETED) -> RunResult[str]:
    now = datetime.now(UTC)
    return RunResult(
        run_id=uuid4(),
        trace_id=uuid4(),
        agent_id="eval.agent",
        status=status,
        output=output,
        started_at=now,
        completed_at=now,
    )


def dataset(*, expected: str = "Hello world", version: str = "1.0.0") -> EvalDataset:
    return EvalDataset(
        id="support.eval",
        version=version,
        cases=(
            EvalCase(
                id="greeting",
                input="Say hello",
                assertions=(
                    EvalAssertion(kind=AssertionKind.STATUS, expected="completed"),
                    EvalAssertion(kind=AssertionKind.EXACT_OUTPUT, expected=expected),
                    EvalAssertion(
                        kind=AssertionKind.CONTAINS,
                        expected="WORLD",
                        case_sensitive=False,
                    ),
                    EvalAssertion(kind=AssertionKind.REGEX, expected=r"Hello\s+world"),
                    EvalAssertion(
                        kind=AssertionKind.MAX_DURATION_SECONDS,
                        expected=10.0,
                    ),
                ),
            ),
        ),
    )


class FixedJudge:
    async def score(self, case: EvalCase, run_result: RunResult[object]) -> JudgeScore:
        return JudgeScore(judge_id="advisory", score=0.25, rationale=case.id)


class EvaluationTests(unittest.IsolatedAsyncioTestCase):
    async def test_deterministic_evaluation_and_advisory_judge(self) -> None:
        calls: list[str] = []

        async def target(case: EvalCase) -> RunResult[str]:
            calls.append(case.id)
            return result("Hello world")

        report = await Evaluator(judges=(FixedJudge(),)).evaluate(dataset(), target)
        self.assertEqual(calls, ["greeting"])
        self.assertEqual(report.pass_rate, 1.0)
        self.assertTrue(report.results[0].passed)
        self.assertEqual(report.results[0].judge_scores[0].score, 0.25)

    async def test_report_round_trip_and_regression(self) -> None:
        async def passing(case: EvalCase) -> RunResult[str]:
            return result("Hello world")

        async def failing(case: EvalCase) -> RunResult[str]:
            return result("Goodbye")

        baseline = await Evaluator().evaluate(dataset(), passing)
        candidate = await Evaluator().evaluate(dataset(version="1.1.0"), failing)
        comparison = compare_reports(baseline, candidate)
        self.assertFalse(comparison.acceptable)
        self.assertEqual(comparison.regressed_case_ids, ("greeting",))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "report.json"
            save_eval_report(baseline, path)
            self.assertEqual(load_eval_report(path), baseline)

    async def test_report_mismatch_and_invalid_threshold_fail(self) -> None:
        async def target(case: EvalCase) -> RunResult[str]:
            return result("Hello world")

        baseline = await Evaluator().evaluate(dataset(), target)
        different = baseline.model_copy(update={"dataset_id": "other.eval"})
        with self.assertRaises(ValueError):
            compare_reports(baseline, different)
        with self.assertRaises(ValueError):
            compare_reports(baseline, baseline, max_pass_rate_regression=-0.1)

        improved = compare_reports(baseline.model_copy(update={"pass_rate": 0.0}), baseline)
        self.assertTrue(improved.acceptable)

    async def test_cost_and_structured_output_assertions(self) -> None:
        case = EvalCase(
            id="structured",
            input="return data",
            assertions=(
                EvalAssertion(kind=AssertionKind.CONTAINS, expected='"answer":"ok"'),
                EvalAssertion(kind=AssertionKind.MAX_COST_USD, expected=0.03),
            ),
        )

        async def target(item: EvalCase) -> RunResult[object]:
            return result("unused").model_copy(
                update={
                    "output": {"answer": "ok"},
                    "usage": Usage(estimated_cost_usd=Decimal("0.02")),
                }
            )

        report = await Evaluator().evaluate(
            EvalDataset(id="structured.eval", version="1.0.0", cases=(case,)), target
        )
        self.assertTrue(report.results[0].passed)

    def test_invalid_eval_contracts_fail_early(self) -> None:
        with self.assertRaises(ValueError):
            EvalAssertion(kind=AssertionKind.REGEX, expected="[")
        with self.assertRaises(ValueError):
            EvalAssertion(kind=AssertionKind.MAX_COST_USD, expected=-1)
        with self.assertRaises(ValueError):
            EvalAssertion(kind=AssertionKind.STATUS, expected="unknown")
        with self.assertRaises(ValueError):
            EvalCase(id="empty", input="x", assertions=())


class TelemetryTests(unittest.IsolatedAsyncioTestCase):
    def event(self, event_type: EventType, **payload: object) -> AgentEvent:
        return AgentEvent(
            event_type=event_type,
            occurred_at=datetime.now(UTC),
            run_id=self.run_id,
            trace_id=self.trace_id,
            agent_id="agent",
            payload=payload,
        )

    async def asyncSetUp(self) -> None:
        self.run_id = uuid4()
        self.trace_id = uuid4()

    async def test_local_metrics_snapshot(self) -> None:
        sink = RuntimeMetricsSink()
        await sink.emit(self.event(EventType.RUN_STARTED))
        await sink.emit(
            self.event(
                EventType.MODEL_REQUEST_STARTED,
                is_retry=True,
                streaming=True,
            )
        )
        await sink.emit(
            self.event(
                EventType.MODEL_REQUEST_FAILED,
                streaming=True,
                stream_event_count=1,
            )
        )
        await sink.emit(
            self.event(
                EventType.MODEL_RESPONSE_COMPLETED,
                streaming=True,
                stream_event_count=2,
            )
        )
        await sink.emit(
            self.event(
                EventType.USAGE_UPDATED,
                usage=Usage(
                    input_tokens=10,
                    output_tokens=4,
                    estimated_cost_usd=Decimal("0.02"),
                ).model_dump(mode="json"),
            )
        )
        await sink.emit(self.event(EventType.RUN_COMPLETED))
        snapshot = sink.snapshot()
        self.assertEqual(snapshot.runs_started, 1)
        self.assertEqual(snapshot.runs_completed, 1)
        self.assertEqual(snapshot.model_calls, 1)
        self.assertEqual(snapshot.model_attempts, 1)
        self.assertEqual(snapshot.model_retries, 1)
        self.assertEqual(snapshot.stream_events, 3)
        self.assertEqual(snapshot.streams_completed, 1)
        self.assertEqual(snapshot.stream_failures, 1)
        self.assertEqual(snapshot.input_tokens, 10)
        self.assertEqual(snapshot.estimated_cost_usd, 0.02)

    async def test_opentelemetry_bridge_ends_terminal_span(self) -> None:
        class Span:
            def __init__(self) -> None:
                self.events: list[str] = []
                self.attributes: dict[str, object] = {}
                self.ended = False

            def set_attribute(self, name: str, value: object) -> None:
                self.attributes[name] = value

            def add_event(self, name: str, attributes: dict[str, object] | None = None) -> None:
                self.events.append(name)

            def end(self, end_time: int | None = None) -> None:
                self.ended = True

        class Tracer:
            def __init__(self) -> None:
                self.span = Span()

            def start_span(self, name: str, *, attributes: dict[str, object] | None = None) -> Span:
                return self.span

        tracer = Tracer()
        sink = OpenTelemetryEventSink(tracer)
        await sink.emit(self.event(EventType.RUN_STARTED))
        await sink.emit(self.event(EventType.STEP_STARTED))
        await sink.emit(self.event(EventType.RUN_COMPLETED))
        self.assertTrue(tracer.span.ended)
        self.assertIn("step.started", tracer.span.events)
        self.assertEqual(tracer.span.attributes["pyagentskit.run.status"], "run.completed")


class DiagnosticsAndCliTests(unittest.TestCase):
    def test_doctor_reports_core_health(self) -> None:
        report = run_doctor()
        self.assertTrue(report.healthy)
        self.assertEqual(report.checks[0].status, DoctorStatus.PASS)

    def test_doctor_and_config_cli(self) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = main(["doctor"])
        self.assertEqual(code, 0)
        self.assertIn('"healthy": true', stdout.getvalue())

        definition = AgentDefinition(
            id="cli.agent",
            version="1.0.0",
            instructions="Help",
            model=ModelRef(provider="fake", name="test"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "agent.json"
            path.write_text(definition.model_dump_json(), encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(["config", "validate", str(path)])
            self.assertEqual(code, 0)
            self.assertIn("cli.agent", stdout.getvalue())

    def test_invalid_eval_cli_returns_two(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "invalid.json"
            path.write_text(json.dumps({"id": "broken"}), encoding="utf-8")
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["eval", "validate", str(path)])
            self.assertEqual(code, 2)
            self.assertIn("error:", stderr.getvalue())

    def test_safe_offline_run_cli(self) -> None:
        definition = AgentDefinition(
            id="cli.agent",
            version="1.0.0",
            instructions="Help",
            model=ModelRef(provider="fake", name="test"),
        )
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "agent.json"
            path.write_text(definition.model_dump_json(), encoding="utf-8")
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                code = main(
                    [
                        "run",
                        str(path),
                        "--input",
                        "hello",
                        "--response",
                        "offline response",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertIn('"status": "completed"', stdout.getvalue())
        self.assertIn('"output": "offline response"', stdout.getvalue())

    def test_checkpoint_inspection_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            database = Path(temporary) / "runs.sqlite"
            stderr = io.StringIO()
            with redirect_stderr(stderr):
                code = main(["checkpoint", "inspect", str(database), str(uuid4())])
        self.assertEqual(code, 2)
        self.assertIn("Durable run not found", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
