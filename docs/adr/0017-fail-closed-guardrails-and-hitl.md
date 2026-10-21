# ADR-0017 — Fail-closed guardrails and claim-before-effect HITL

- Status: Accepted
- Date: 2026-09-06

## Context

Lot 09 must allow human review of sensitive actions without turning PyAgentsKit into a scheduler or
claiming exactly-once external effects before durable checkpoints exist.

## Decision

Guardrails intercept five normalized runtime boundaries and fail closed. Approval-gated responses
contain one tool call. The request is tenant-scoped, persisted and bound to canonical arguments.
After human resolution, the runtime atomically claims the decision before any approved effect and
consumes approved and rejected decisions once.

Provider privacy guarantees come from adapter-owned configuration. Agent text and metadata cannot
self-assert ZDR or training exclusion.

## Consequences

- sensitive actions cannot execute without verifiable state;
- duplicate resumes are rejected;
- a crash after claim is visible and safe but requires manual reconciliation;
- general checkpoints and unknown-effect recovery remain assigned to Lot 10;
- applications own reviewer authentication, authorization, UI and notifications.
