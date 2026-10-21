# ADR-0008 — Exclude arbitrary code execution from core

- **Status:** Accepted
- **Date:** 2026-09-04

## Decision

The core does not execute model-generated code. A future sandboxed extension requires a separate
threat model and release decision.

## Consequences

The V1 attack surface is smaller. Code-agent use cases are not served by the base package.

