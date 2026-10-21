# ADR 0020 — Opt-in streaming and safe parallel tools

Status: Accepted  
Date: 2026-09-09

## Context

V1 exposes provider streaming independently from `Runner`, and executes tools sequentially. Users
need lower perceived response latency and bounded concurrency without weakening guardrails or the
mono-agent architecture.

## Decision

Add an asynchronous stream callback to `Runner.run`. The Runner consumes the provider-neutral
stream, forwards defensive event copies, reconstructs a validated terminal response and continues
through the existing loop.

Add constructor-level, opt-in parallel tool execution. A batch qualifies only when the model
supports it and every tool is declared idempotent with `PURE` or `READ` risk. Concurrency is bounded
by `RunLimits.max_parallel_tools`; results are restored to model order. All other batches use the
existing sequential path.

## Consequences

The 1.0.0 defaults and frozen V1 contracts remain compatible. Applications gain controlled latency
improvements, but own the correctness of tool metadata and callback behavior. This does not add
multi-agent orchestration, transactional batching or parallel writes.

