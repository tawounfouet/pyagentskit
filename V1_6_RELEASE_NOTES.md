# PyAgentsKit 1.6.0 — Distributed Operations & Production Qualification

Release date: 2026-09-11

PyAgentsKit 1.6.0 operationalizes the fenced durable execution introduced in 1.5.0. It adds
bounded worker admission, graceful draining, health snapshots, safe audit/metrics and optional
OpenTelemetry spans while preserving the mono-agent and no-scheduler boundary.

## Added

- `DistributedWorkerController` with finite concurrent admission and duplicate-run rejection;
- readiness over worker state, capacity and an application-owned coordination probe;
- bounded graceful drain that never cancels an active effect after timeout;
- payload-free `DistributedOperationEvent` lifecycle vocabulary;
- dependency-free `DistributedMetricsSink` and `MemoryDistributedEventSink`;
- append-only local `JsonLinesDistributedEventSink` reference;
- optional `OpenTelemetryDistributedEventSink` lease spans;
- real multi-process `SIGTERM`, `SIGKILL` and `SIGSTOP` lease qualification;
- opt-in PostgreSQL two-worker durable takeover qualification;
- distributed operations benchmark, runbook and Kubernetes integration template.

## Safety and compatibility

- observer failures never change run or effect semantics;
- drain timeout leaves the worker draining and does not resubmit work;
- acquisition remains single-shot and takeover still obeys durable reconciliation;
- operational events exclude prompts, tool payloads, credentials and exception messages;
- the frozen root API, event vocabulary, providers and existing store protocols are unchanged;
- queues, scheduling, autoscaling and forced process replacement remain external.
