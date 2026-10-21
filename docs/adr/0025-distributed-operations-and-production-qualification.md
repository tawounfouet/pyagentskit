# ADR-0025 — Distributed operations without a scheduler

Status: Accepted  
Date: 2026-09-11

## Context

Version 1.5 established safe lease-coordinated durable execution. Production workers additionally
need admission control, readiness, graceful draining, payload-safe metrics/traces and repeatable
failure qualification. Those responsibilities must not turn PyAgentsKit into a queue, scheduler or
workflow engine.

## Decision

Add submodule-scoped operational contracts around `DistributedDurableRunner`:

- `DistributedWorkerController` admits a finite number of runs and rejects work while draining;
- graceful drain waits within a caller-supplied bound and never cancels an effect when it expires;
- readiness combines worker state, capacity and an application-supplied coordination probe;
- lifecycle events contain identifiers, tokens and reason codes, never prompts or tool payloads;
- local metrics, JSON Lines audit and optional OpenTelemetry sinks consume that vocabulary;
- PostgreSQL live qualification uses two worker identities and the existing durable recovery path;
- real processes establish `SIGTERM`, `SIGKILL` and suspension behavior against SQLite leases.

## Consequences

Applications can expose worker health and automate graceful shutdown without giving PyAgentsKit
control of assignment or scheduling. Observability sinks are best-effort and cannot change effect
semantics. A drain timeout leaves the worker in `DRAINING`; it does not cancel or resubmit active
work. Queue delivery, pod replacement and forced termination remain platform responsibilities.
