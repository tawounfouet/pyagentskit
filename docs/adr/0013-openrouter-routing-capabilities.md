# ADR-0013 — Explicit OpenRouter routing and dynamic capabilities

Status: Accepted  
Date: 2026-09-05

## Context

OpenRouter can change upstream endpoints or models and its catalog evolves independently of a
PyAgentsKit release. Treating its OpenAI-compatible envelope as a permanent capability guarantee
would make runs hard to reproduce and policies hard to audit.

## Decision

- Advanced routing is represented by immutable, serializable provider-specific contracts.
- Evaluation defaults to no fallback; compliance requires ZDR and a provider allowlist.
- Model fallback order is explicit and the resolved model remains observable.
- Catalog capabilities are cached for a bounded TTL and marked as reported, not live-certified.
- Required capabilities are checked before model generation whenever a catalog descriptor is used.
- Local HTTP retries and server-side fallback cannot be enabled together.
- Router metadata is opt-in at the protocol layer but only a safe stable subset is normalized.

## Consequences

The core `Model` protocol remains independent of OpenRouter. Deployments gain inspectable routing
without mistaking a changing catalog for proof of model quality, availability or compliance.
Applications must still qualify exact account/model combinations with opt-in live tests.
