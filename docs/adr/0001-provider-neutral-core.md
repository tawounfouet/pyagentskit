# ADR-0001 — Provider-neutral core

- **Status:** Accepted
- **Date:** 2026-09-04

## Decision

Public core types do not import or expose provider SDK types. Providers implement PyAgentsKit's
`Model` protocol and map their wire formats at the adapter boundary.

## Consequences

Provider features require explicit capability modelling. Adapter code is slightly larger, while
applications, tools and tests remain portable.

