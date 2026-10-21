# ADR-0018 — Durable effects without a workflow engine

- Status: accepted
- Date: 2026-09-07

## Context

Lot 10 must recover interrupted agent runs without repeating an external side effect. The user has
explicitly deferred PyWorkflowKit integration.

## Decision

PyAgentsKit owns semantic checkpoints, an effect ledger and controlled recovery through the
provider-neutral `RunStore` contract. An effect is planned and claimed before tool code executes.
An interruption inside this boundary becomes `unknown_effect` and requires an explicit operator
resolution. Replay is analytical only.

The base package supplies memory and SQLite reference stores. It does not supply scheduling,
workers, distributed leases, DAG orchestration or a PyWorkflowKit adapter.

## Consequences

- completed effects can be observed after restart without re-execution;
- ambiguous effects fail closed;
- resumes bind to the stored agent ID and version;
- SQLite remains a local/single-process reference implementation;
- a later workflow integration can implement `RunStore` without changing core semantics.
