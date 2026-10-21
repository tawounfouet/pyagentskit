# ADR-0009 — OpenRouter as an optional routed provider

- **Status:** Accepted
- **Date:** 2026-09-04

## Decision

OpenRouter will be implemented after the direct OpenAI reference adapter as an optional
`OpenRouterModel`. Its OpenAI-compatible transport remains an adapter detail.

## Consequences

The integration can expose routing, fallback, BYOK and data-policy metadata without making
OpenRouter the framework abstraction. A native non-OpenAI-compatible provider remains necessary
to prove provider independence.

