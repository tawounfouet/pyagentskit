# PyAgentsKit 0.2.0b1 — OpenRouter routing and capabilities

Date: 2026-09-05. Baseline: `0.2.0a1`.

This beta delivers lot 07's advanced OpenRouter layer without adding OpenRouter concepts to the
provider-neutral runtime contracts.

## Delivered

- `OpenRouterRoutingPolicy`, `OpenRouterDataPolicy` and named development, production,
  compliance and evaluation profiles;
- upstream provider order, allowlist and ignore list;
- explicit provider-endpoint fallback and ordered model fallback list;
- `require_parameters`, ZDR and provider data-collection selection;
- `/models` catalog normalization with a bounded TTL and concurrent request coalescing;
- atomic JSON snapshots for explicit offline catalog use;
- conservative capability derivation and preflight requirements;
- `OpenRouterModel.from_catalog(...)` construction;
- safe route strategy, region, successful attempt, selected provider and fallback status;
- reported cost and requested/resolved model identity retained from alpha1.

## Determinism and safety

Evaluation keeps fallback disabled. The compliance profile refuses construction without an
explicit provider allowlist and sends ZDR plus `data_collection=deny`. Local HTTP retries are
rejected when OpenRouter fallbacks are active, preventing multiplicative attempts.

The catalog is advisory. Descriptors retain `model_verified=false`; snapshots expire in memory
like network results and are never refreshed silently after a network error. Router summaries,
pipeline records and arbitrary attempt details are not copied into PyAgentsKit metadata.

## Qualification boundary

All automated tests use hand-authored HTTP fixtures. No authenticated or billable provider call
was made. The included live test remains opt-in and does not prove every catalog capability,
provider endpoint, privacy setting or fallback path.

See `OPENROUTER_ADVANCED_QUALIFICATION.md`, `docs/guides/OPENROUTER.md`, ADR-0013 and
`CHECK_RESULTS.md`.
