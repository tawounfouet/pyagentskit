# ADR-0002 — Async-native runtime

- **Status:** Accepted
- **Date:** 2026-09-04

## Decision

Provider and tool ports are asynchronous. A later runtime may expose a synchronous convenience
facade, but async contracts remain canonical.

## Consequences

Streaming, cancellation and concurrent I/O remain natural. Sync integration must avoid nested
event-loop magic.

