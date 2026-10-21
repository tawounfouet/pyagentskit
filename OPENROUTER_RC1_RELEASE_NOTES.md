# PyAgentsKit 0.2.0rc1 — OpenRouter resilience and qualification closure

Date: 2026-09-05. Baseline: `0.2.0b1`.

This release candidate closes the advanced OpenRouter routing lot before the stable `0.2.0` audit.

## Delivered

- capability validation over the complete ordered model-fallback chain;
- conservative common capability envelope for routed models;
- safe router metadata on terminal streaming events and failure events;
- correct differentiation between authentication and typed HTTP 403 policy/guardrail failures;
- snapshot schema v2 with canonical payload checksum and v1 read compatibility;
- truly offline snapshot catalogs with no key, HTTP client or implicit refresh;
- evaluation-provider pinning and stricter invalid configuration handling;
- three separate live gates for evaluation, compliance and expected model fallback.

## Compatibility

Existing `0.2.0b1` snapshot files remain readable. New snapshots use schema v2. The legacy
`OpenRouterModel(..., allow_fallbacks=..., require_parameters=...)` constructor remains available.
`from_catalog(...)` now rejects a manual `capabilities` override because catalog resolution is its
authority.

## Qualification boundary

The complete automated suite is offline. Live tests are present but were not run because no
explicit credentials/gates were configured. This release therefore qualifies mappings,
validation, packaging and failure behavior—not any specific remote account/model combination.

See `AUDIT_OPENROUTER_BETA1.md`, `OPENROUTER_RC1_QUALIFICATION.md`, ADR-0014 and
`CHECK_RESULTS.md`.
