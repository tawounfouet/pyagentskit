# OpenRouter advanced qualification — PyAgentsKit 0.2.0b1

Qualification date: 2026-09-05

| Area | Result | Evidence boundary |
|---|---:|---|
| Routing policy serialization | Pass | Exact offline request fixtures |
| Privacy policy serialization | Pass | ZDR, collection and allowlist body assertions |
| Model fallbacks | Pass | Ordered `models` request and resolved-model fixture |
| Router metadata | Pass | Stable safe fields only; opaque fields excluded |
| Catalog and TTL | Pass | Mocked `/models`, expiry, invalidation and coalescing |
| Offline snapshots | Pass | Atomic round-trip and malformed-file rejection |
| Capability negotiation | Pass | Positive and fail-closed fixture cases |
| Retry coordination | Pass | Invalid local/server fallback combinations rejected |
| Live OpenRouter | Not run | No account/model guarantee claimed |

## Capability interpretation

`tools`, `response_format` and `parallel_tool_calls` are derived only when the catalog reports the
matching supported parameters. Modalities and token bounds come from the current catalog entry.
Streaming describes the OpenRouter Chat Completions transport. Every descriptor is marked
`catalog_reported=true` and `model_verified=false`.

## Trace interpretation

`fallback_used` is true when the resolved model differs from the requested primary model or the
router reports a successful attempt greater than one. The response may omit router metadata on a
cache hit; missing fields remain unknown rather than being fabricated.

## Excluded claims

This release does not certify live availability, model quality, exact prices, an account's provider
preferences, BYOK credentials, regional residency, effective ZDR enforcement, or the behavior of
third-party plugins and server tools. Those require deployment-specific live acceptance.

## Official references

- [Provider selection](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks)
- [Model catalog](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties)
- [Router metadata](https://openrouter.ai/docs/guides/features/router-metadata)
- [Zero Data Retention](https://openrouter.ai/docs/guides/features/zdr)
