# PyAgentsKit 0.2.0a1 — OpenRouter minimal

Release date: 2026-09-05  
Baseline: PyAgentsKit `0.1.0`

## Delivered

- Distinct optional `OpenRouterModel` implementing the provider-neutral `Model` protocol.
- Native OpenRouter `/api/v1/chat/completions` transport through HTTPX.
- Text and image messages, client tools, strict structured outputs and SSE streaming.
- Explicit organization-prefixed model IDs and `OPENROUTER_API_KEY` authentication.
- Optional `HTTP-Referer` and `X-OpenRouter-Title` application attribution.
- Requested/resolved model, upstream provider and generation ID response metadata.
- Reported token usage, cache/reasoning counters, BYOK marker and reported cost normalization.
- Stable `error_type` mapping with sanitized original code metadata.
- HTTP 200 embedded error detection for complete and streaming responses.
- Deterministic routing defaults: endpoint fallbacks disabled and parameter support required.
- Contract tests, live opt-in smoke test, dedicated guide, ADR and qualification report.

## Defaults

```python
OpenRouterModel(
    model="provider/model",
    allow_fallbacks=False,
    require_parameters=True,
)
```

These defaults favor reproducibility and early incompatibility errors. Applications may opt in to
endpoint fallback explicitly. Model fallback lists and provider ordering are not exposed in this
alpha.

## Compatibility

- Python 3.11+.
- The core dependency remains Pydantic only.
- Install HTTPX through `pyagentskit[openrouter]` or `pyagentskit[providers]`.
- Existing `0.1.0` agents and direct-provider adapters remain compatible.
- `ModelError` now exposes a sanitized `metadata` dictionary in addition to `retryable`.

## Qualification boundary

OpenRouter contract tests use real HTTPX request/response objects with deterministic mock
transports. The wheel is installed outside the source tree and exercised offline. The live test is
disabled by default and was not run because no `OPENROUTER_API_KEY` was configured. No billable
request was made.

## Deferred to 0.2.0b1 / 0.2.0rc1

- dynamic model and endpoint catalog;
- cache/TTL and offline catalog snapshot;
- provider order, allowlist and denylist policy objects;
- model fallback lists and fallback-reason tracing;
- ZDR, data-collection and provider privacy policies;
- model-level capability negotiation from catalog descriptors;
- generation-stat follow-up and advanced router metadata;
- retry/fallback coordination across runtime layers.

See `../qualification/OPENROUTER_QUALIFICATION.md`, `../guides/OPENROUTER.md` and `../verification/CHECK_RESULTS.md`.
