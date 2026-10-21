# ADR-0003 — Pydantic v2 at boundaries

- **Status:** Accepted
- **Date:** 2026-09-04

## Decision

Serializable configuration and untrusted boundary data use strict Pydantic v2 models.

## Consequences

PyAgentsKit gains validation and JSON Schema support. Internal runtime objects may still use
dataclasses when serialization is not required.

