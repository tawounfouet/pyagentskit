# ADR-0005 — Separate agents from workflows

- **Status:** Accepted
- **Date:** 2026-09-04

## Decision

PyAgentsKit owns model-driven decisions. PyWorkflowKit owns deterministic workflow execution and
durability. Integrations are optional and unidirectional.

## Consequences

An agent may trigger a workflow and a workflow may host an agent step. Neither project duplicates
the other's runtime.

