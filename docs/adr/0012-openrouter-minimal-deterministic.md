# ADR 0012 — Deterministic OpenRouter minimal adapter

- Status: Accepted
- Date: 2026-09-05

## Context

OpenRouter exposes an OpenAI-like Chat Completions surface while adding routing, provider
fallbacks, model fallback lists, usage cost and router-specific error metadata. Reusing
`OpenAIModel` directly would hide those semantics and create router lock-in inside the core.

The first OpenRouter release must prove adapter interoperability without prematurely introducing
the dynamic model catalog, privacy profiles and advanced routing policy planned for Lot 07.

## Decision

Add a distinct `OpenRouterModel` behind the provider-neutral `Model` protocol.

The minimal adapter:

- requires an explicit organization-prefixed model ID;
- uses `OPENROUTER_API_KEY` and the native `/api/v1/chat/completions` endpoint;
- maps normalized messages, tools, strict structured output and SSE streaming;
- records requested/resolved model, upstream provider, generation ID, usage and reported cost;
- preserves stable `error_type`, HTTP code and provider code as sanitized exception metadata;
- defaults to `allow_fallbacks=false` and `require_parameters=true`;
- does not expose model fallback lists, provider ordering, plugins, catalog access or ZDR policy.

The adapter may reuse tested Chat Completions mapping behavior internally, but its public class,
configuration, metadata, error handling and documentation remain OpenRouter-specific.

## Consequences

Benchmark and test requests are reproducible by default and cannot silently drop requested
parameters. Applications that explicitly enable endpoint fallback accept the corresponding
infrastructure variability. Advanced governance remains a separate compatible layer in Lot 07.
