# Distributed operations and worker lifecycle

PyAgentsKit 1.6.0 adds an operational shell around the fenced durable runner. It remains
dependency-free unless the optional PostgreSQL or OpenTelemetry adapters are selected.

```python
from pyagentskit.distributed import (
    DistributedDurableRunner,
    DistributedMetricsSink,
    DistributedWorkerController,
    JsonLinesDistributedEventSink,
)

metrics = DistributedMetricsSink()
audit = JsonLinesDistributedEventSink("state/distributed-audit.jsonl")
runner = DistributedDurableRunner(
    durable_runner,
    lease_store,
    owner_id=worker_incarnation_id,
    event_sinks=(metrics, audit),
)
worker = DistributedWorkerController(
    runner,
    max_active_runs=16,
    readiness_probe=postgres_readiness,
)
```

The application calls `worker.run()`, `worker.resume()` or `worker.resume_approval()`. Admission
rejects duplicate active run IDs, capacity overflow and every request received after drain begins.

## Health endpoint integration

`await worker.health()` returns a serializable `DistributedWorkerHealth`. A web application can
map `health.ready` to HTTP 200/503 without importing a web framework into PyAgentsKit.

Readiness is false when:

- the worker is draining or stopped;
- `active_runs == max_active_runs`;
- the optional coordination probe returns false or raises.

The probe must be read-only, bounded by the host application and free of business effects.

## Graceful shutdown

On `SIGTERM`, the host should stop queue consumption first and then call:

```python
drained = await worker.drain(timeout_seconds=75)
```

The controller rejects new admissions immediately. It waits for active runs but never cancels one
when the grace period expires. `False` means the host must decide whether to keep waiting or allow
the platform to terminate the process. A potentially interrupted effect will still follow the
durable `UNKNOWN_EFFECT` rules.

## Metrics and audit

`DistributedMetricsSink.snapshot()` exposes counters for acquisition attempts, conflicts,
renewals, lease losses, releases, takeovers, rejected admissions and drain outcomes.

`JsonLinesDistributedEventSink` is a local append-only reference. For distributed production,
implement `DistributedEventSink` with a durable centralized backend. Observer failures are
best-effort and never modify run or effect results; alert separately on exporter health.

Operational events deliberately exclude:

- prompts and model output;
- tool names, arguments and results;
- credentials, DSNs and exception messages;
- application dependency objects.

## OpenTelemetry

`OpenTelemetryDistributedEventSink` creates one span per acquired lease and uses only safe
identifiers, lease revision and fencing token attributes. Inject a tracer for tests or install the
`opentelemetry` extra. The application owns exporters, sampling, retention and tenant access.

## TTL sizing

Choose values from measured production latency, not examples. A conservative starting relation is:

```text
lease_ttl >= 3 × renewal_interval
renewal_interval >= p99(database round trip + event-loop delay) + safety margin
termination_grace > longest expected run shutdown + one lease_ttl
```

Alert when renewal latency consumes more than half the interval. Test process suspension and
database unavailability before each deployment class. See the
[distributed worker runbook](../runbooks/DISTRIBUTED_WORKER_OPERATIONS.md).
