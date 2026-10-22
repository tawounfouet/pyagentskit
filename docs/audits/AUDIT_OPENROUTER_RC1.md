# Final RC1 audit — PyAgentsKit 0.2.0 stable

Audit date: 2026-09-05  
Baseline: `0.2.0rc1`  
Target: `0.2.0`

## Verdict

**Release approved.** No blocking correctness, compatibility, packaging or documented-security
finding remains in the audited scope. The stable release preserves RC1 behavior and adds an
executable public-API freeze plus explicit compatibility evidence.

## Audit scope

- public OpenRouter imports, signatures, defaults and serialized fields;
- request mapping for routing, tools, structured output and model fallbacks;
- normal, streaming and error response normalization;
- safe event and route metadata;
- dynamic catalog validation, cache behavior and offline snapshots;
- capability preflight across complete fallback chains;
- error classification and retry coordination;
- credential, redirect, plaintext HTTP and artifact hygiene;
- wheel/sdist contents and installed-wheel execution;
- documentation claims versus automated and live evidence.

## Findings and disposition

| ID | Severity | Finding | Stable disposition |
|---|---:|---|---|
| S-01 | High | Public RC surface had no executable compatibility lock. | Closed: explicit module exports and golden API tests. |
| S-02 | Medium | Stable support levels could be confused with certification of every routed model. | Closed: compatibility matrix separates adapter, account and model qualification. |
| S-03 | Medium | The snapshot compatibility promise was implemented but not part of the stable API policy. | Closed: v1 read and v2 read/write guarantees are frozen and tested. |
| S-04 | Low | Dynamic metadata could be mistaken for a closed schema. | Closed: additive metadata and unknown-field tolerance are documented. |

## Compatibility audit

| Baseline | Result |
|---|---|
| `0.2.0a1` constructor flags | Preserved |
| `0.2.0b1` routing policy and catalog types | Preserved |
| `0.2.0b1` schema-v1 snapshots | Read-compatible |
| `0.2.0rc1` signatures and defaults | Frozen for `0.2.x` |
| Provider-neutral core contracts | Unchanged |
| OpenAI, Anthropic, Google, xAI and Ollama adapters | Regression suite preserved |

## Security and privacy audit

- API keys remain header-only and absent from agents, events and snapshots.
- Arbitrary router summaries, attempts, pipelines and provider messages are not copied to events.
- ZDR and provider allowlists remain explicit request policies.
- Non-loopback plaintext HTTP, redirects and unsafe attribution URLs remain rejected.
- Local retries and router fallbacks cannot amplify each other silently.
- Partial streams are never retried.
- No project `.env`, cache, virtual environment or detected credential pattern is released.

## Residual risks — accepted and documented

1. Live account, concrete-model, ZDR and forced-fallback qualification were not run without user
   credentials and explicit billable gates.
2. Catalog capabilities are upstream-reported and may change after a snapshot is produced.
3. Provider-reported usage and cost are observational; they are not a hard billing ceiling.
4. ZDR covers eligible inference endpoints, not external plugins or application tools.
5. The stable runtime remains mono-agent, sequential for tool execution and non-durable.

These are product boundaries rather than release blockers. They are surfaced in the README,
compatibility matrix, security policy and qualification guide.

## Evidence

- `tests/test_openrouter_stable_api.py` — frozen API contract;
- `tests/test_openrouter_provider.py` — minimal adapter protocol;
- `tests/test_openrouter_advanced.py` — routing, catalog, resilience and metadata;
- `tests/test_openrouter_live_qualification.py` — separately gated live paths;
- `../verification/CHECK_RESULTS.md` — final reproducible release-check;
- `../compatibility/OPENROUTER_COMPATIBILITY_MATRIX.md` — qualification boundary;
- `../compatibility/OPENROUTER_API_STABILITY.md` — patch-line compatibility policy.
