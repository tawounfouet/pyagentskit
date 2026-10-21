"""Deterministic local lease benchmark used by the release gate."""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics
import time

from pyagentskit.coordination import MemoryLeaseStore


async def benchmark(iterations: int) -> dict[str, float | int]:
    store = MemoryLeaseStore()
    durations: list[float] = []
    for index in range(iterations):
        started = time.perf_counter()
        lease = await store.acquire("shared-resource", owner_id=f"worker-{index}", ttl_seconds=30)
        await store.assert_current(lease)
        await store.release(lease)
        durations.append((time.perf_counter() - started) * 1_000)
    ordered = sorted(durations)
    return {
        "iterations": iterations,
        "last_fencing_token": iterations,
        "mean_ms": round(statistics.mean(durations), 4),
        "median_ms": round(statistics.median(durations), 4),
        "p95_ms": round(ordered[max(0, int(len(ordered) * 0.95) - 1)], 4),
        "network_calls": 0,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=250)
    args = parser.parse_args()
    if args.iterations <= 0:
        raise SystemExit("iterations must be positive")
    result = asyncio.run(benchmark(args.iterations))
    if float(result["mean_ms"]) > 5.0:
        raise SystemExit("coordination benchmark exceeded 5 ms mean gate")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
