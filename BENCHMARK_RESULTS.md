# Runtime benchmarks — 1.6.0

The release benchmarks run locally with deterministic in-memory doubles and no network. The first
three preserve the V1.2 Runner gates. The fourth checks the raw lease lifecycle. The fifth executes
the complete admission, durable run, lease, audit-metrics and release path.

```bash
PYTHONPATH=src python scripts/benchmark_runtime.py --iterations 250 --max-mean-ms 5
PYTHONPATH=src python scripts/benchmark_streaming.py --iterations 250 --max-mean-ms 8
PYTHONPATH=src python scripts/benchmark_retry.py --iterations 250 --max-mean-ms 10
PYTHONPATH=src python scripts/benchmark_coordination.py --iterations 250
PYTHONPATH=src python scripts/benchmark_distributed_operations.py --iterations 250
```

Reference measurements on Linux / Python 3.12.14:

| Path | Iterations | Mean | Median | p95 | Throughput | Ceiling |
|---|---:|---:|---:|---:|---:|---:|
| Complete response | 250 | 0.3850 ms | 0.3340 ms | 0.6373 ms | 2,594.71/s | 5 ms |
| Integrated streaming | 250 | 0.4592 ms | 0.3884 ms | 0.8205 ms | 2,175.71/s | 8 ms |
| One explicit retry | 250 | 0.5402 ms | 0.4382 ms | 0.6854 ms | 1,849.83/s | 10 ms |
| Lease acquire/assert/release | 250 | 0.0103 ms | 0.0081 ms | 0.0108 ms | — | 5 ms |
| Distributed operational lifecycle | 250 | 0.8548 ms | 0.7941 ms | 1.1224 ms | — | 5 ms |

The stream benchmark delivered 1,020 callback events. The retry benchmark performed 500 model
attempts and zero tool calls. The coordination benchmark ended at fencing token 250. The
distributed benchmark recorded exactly 250 acquisitions and 250 releases. Every path made zero
network calls.

Values vary with hardware. These microbenchmarks detect large framework regressions; they are not
provider, database latency or deployment-capacity claims.
