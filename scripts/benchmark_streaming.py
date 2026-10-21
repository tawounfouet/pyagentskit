"""Measure deterministic Runner-integrated streaming overhead without network access."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time
from typing import Any

from pyagentskit import (
    AgentDefinition,
    FinishReason,
    ModelRef,
    ModelResponse,
    ModelStreamEvent,
    Runner,
    TextContent,
)
from pyagentskit.testing import FakeModel


async def benchmark(iterations: int) -> dict[str, Any]:
    agent = AgentDefinition(
        id="benchmark.stream",
        version="1.0.0",
        instructions="Return the scripted response.",
        model=ModelRef(provider="fake", name="benchmark"),
    )
    responses = tuple(
        ModelResponse(
            id=f"stream-{index}",
            model="benchmark",
            content=(TextContent(text="ok"),),
            finish_reason=FinishReason.STOP,
        )
        for index in range(iterations + 5)
    )
    runner = Runner(FakeModel(responses))
    event_count = 0

    async def on_stream(event: ModelStreamEvent) -> None:
        nonlocal event_count
        event_count += 1

    samples: list[float] = []
    for _ in range(5):
        await runner.run(agent, "warmup", stream_handler=on_stream)
    started = time.perf_counter()
    for _ in range(iterations):
        sample_started = time.perf_counter()
        result = await runner.run(agent, "benchmark", stream_handler=on_stream)
        if result.output != "ok":
            raise RuntimeError("stream benchmark output mismatch")
        samples.append((time.perf_counter() - sample_started) * 1000)
    elapsed = time.perf_counter() - started
    ordered = sorted(samples)
    p95_index = min(len(ordered) - 1, int(len(ordered) * 0.95))
    return {
        "iterations": iterations,
        "events": event_count,
        "total_seconds": round(elapsed, 6),
        "runs_per_second": round(iterations / elapsed, 2),
        "mean_ms": round(statistics.fmean(samples), 4),
        "median_ms": round(statistics.median(samples), 4),
        "p95_ms": round(ordered[p95_index], 4),
        "network_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=250)
    parser.add_argument("--max-mean-ms", type=float, default=8.0)
    arguments = parser.parse_args()
    if arguments.iterations < 1 or arguments.max_mean_ms <= 0:
        parser.error("iterations and max-mean-ms must be positive")
    report = asyncio.run(benchmark(arguments.iterations))
    print(json.dumps(report, indent=2))
    return 0 if report["mean_ms"] <= arguments.max_mean_ms else 1


if __name__ == "__main__":
    raise SystemExit(main())
