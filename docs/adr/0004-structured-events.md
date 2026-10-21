# ADR-0004 — Structured events as the observability foundation

- **Status:** Accepted
- **Date:** 2026-09-04

## Decision

Every significant runtime transition will emit a versioned `AgentEvent` with full identifiers and
a timezone-aware timestamp.

## Consequences

Logs, traces, metrics, streaming, persistence and replay can consume the same facts. Event payloads
must be safe for serialization and redaction.

