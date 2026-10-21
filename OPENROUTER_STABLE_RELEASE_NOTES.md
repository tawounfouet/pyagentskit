# PyAgentsKit 0.2.0 — stable OpenRouter adapter

Release date: 2026-09-05. Baseline: `0.2.0rc1`.

PyAgentsKit `0.2.0` stabilizes the optional OpenRouter adapter without changing the provider-neutral
core or the existing direct-provider adapters.

## Stable deliverables

- frozen OpenRouter public import paths, signatures, defaults and serialized fields;
- executable golden compatibility suite for the full `0.2.x` patch line;
- final RC audit with all blocking findings closed;
- compatibility matrix separating adapter support from live model certification;
- ordered model fallbacks with conservative shared-capability preflight;
- safe route identity in normal responses, terminal streams and failures;
- four explicit routing profiles and per-request data constraints;
- integrity-checked schema-v2 snapshots with schema-v1 read compatibility;
- true network-free catalog loading;
- full offline release qualification and installed-wheel smoke.

## Upgrade from 0.2.0rc1

No application migration is required. Replace the prerelease constraint with `pyagentskit==0.2.0`.
The stable release adds explicit `__all__` declarations but preserves documented import paths.

## Evidence boundary

All deterministic protocol, runtime, packaging and API-freeze tests pass. Live OpenRouter account,
model, compliance and forced-fallback checks remain independently opt-in and were not executed in
the release environment. No authenticated or billable call was made.

## Next milestone

`0.3.0` starts Lot 08: sessions, context policies, memory and artifacts. OpenRouter `0.2.x` remains
in maintenance and must preserve the frozen API contract.
