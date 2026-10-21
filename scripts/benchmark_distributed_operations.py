"""Deterministic distributed admission/lease/audit benchmark with no network."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from datetime import UTC, datetime

from pyagentskit import (
    AgentDefinition,
    DurableRunner,
    FinishReason,
    MemoryRunStore,
    MemorySessionStore,
    ModelRef,
    ModelResponse,
    RunContext,
    Session,
    TextContent,
    ToolRegistry,
)
from pyagentskit.coordination import MemoryLeaseStore
from pyagentskit.distributed import (
    DistributedDurableRunner,
    DistributedMetricsSink,
    DistributedWorkerController,
)
from pyagentskit.runtime import Runner
from pyagentskit.testing import FakeModel


async def benchmark(iterations: int) -> dict[str, float | int]:
    sessions = MemorySessionStore()
    now = datetime.now(UTC)
    for index in range(iterations):
        await sessions.create(
            Session(
                session_id=f"benchmark-{index}",
                agent_id="benchmark.distributed",
                created_at=now,
                updated_at=now,
            )
        )
    response = ModelResponse(
        id="complete",
        model="fake",
        content=(TextContent(text="ok"),),
        finish_reason=FinishReason.STOP,
    )
    model = FakeModel([response] * iterations)
    durable = DurableRunner(
        Runner(model, tools=ToolRegistry(), session_store=sessions), MemoryRunStore()
    )
    metrics = DistributedMetricsSink()
    controller = DistributedWorkerController(
        DistributedDurableRunner(
            durable,
            MemoryLeaseStore(),
            owner_id="benchmark-worker",
            event_sinks=(metrics,),
        ),
        max_active_runs=1,
    )
    agent = AgentDefinition(
        id="benchmark.distributed",
        version="1.0.0",
        instructions="Complete",
        model=ModelRef(provider="fake", name="fake"),
    )
    durations: list[float] = []
    for index in range(iterations):
        context = RunContext(agent_id=agent.id, deps=None, session_id=f"benchmark-{index}")
        started = time.perf_counter()
        await controller.run(agent, "complete", context=context)
        durations.append((time.perf_counter() - started) * 1_000)
    snapshot = metrics.snapshot()
    if snapshot.acquisitions != iterations or snapshot.releases != iterations:
        raise RuntimeError("distributed lifecycle metrics are incomplete")
    ordered = sorted(durations)
    return {
        "iterations": iterations,
        "mean_ms": round(statistics.mean(durations), 4),
        "median_ms": round(statistics.median(durations), 4),
        "p95_ms": round(ordered[max(0, int(len(ordered) * 0.95) - 1)], 4),
        "acquisitions": snapshot.acquisitions,
        "releases": snapshot.releases,
        "network_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=250)
    parser.add_argument("--max-mean-ms", type=float, default=5.0)
    args = parser.parse_args()
    if args.iterations <= 0 or args.max_mean_ms <= 0:
        raise SystemExit("benchmark bounds must be positive")
    result = asyncio.run(benchmark(args.iterations))
    if float(result["mean_ms"]) > args.max_mean_ms:
        raise SystemExit("distributed operations benchmark exceeded its mean gate")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
