# ADR-0006 — Govern tools as capabilities

- **Status:** Accepted
- **Date:** 2026-09-04

## Decision

Every tool declares a schema, risk class, timeout, idempotence and approval requirement.

## Consequences

Tool registration is more explicit. The runtime can enforce policy before executing untrusted
model output.

