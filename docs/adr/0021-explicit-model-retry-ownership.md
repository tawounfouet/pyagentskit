# ADR 0021 - Explicit model retry ownership

Status: Accepted  
Date: 2026-09-09

## Context

Provider transports, OpenRouter routing and the Runner can each repeat work. Uncoordinated retries
multiply latency, cost and ambiguity. Retrying the whole agent step could also replay tools.

## Decision

Add a disabled-by-default `ModelRetryPolicy` owned by `Runner`. It wraps only one normalized model
request, counts every attempt against run limits and uses deterministic bounded exponential
backoff. It recognizes typed transient model errors rather than matching messages.

Never wrap tool execution, guardrails, approvals, persistence or durable effects. Refuse built-in
provider HTTP retry stacking. Require explicit consent before combining Runner retries with routed
fallbacks. For streams, allow retry only before any text, tool or usage payload is observed.

Reuse the frozen V1 event vocabulary and add only safe payload counters. Do not add event enum
values in a minor release.

## Consequences

Applications gain auditable transient-failure handling without changing 1.1 defaults. Failed model
attempts can still incur cost, custom adapters must disclose hidden retry behavior, and deterministic
backoff can synchronize many workers. Jitter remains a future explicit policy decision.

