# OpenRouter compatibility matrix — PyAgentsKit 0.2.0

Qualification date: 2026-09-05. This matrix distinguishes adapter support from remote model
certification.

## Runtime and dependency matrix

| Surface | Supported range | Release evidence |
|---|---|---|
| Python | 3.11, 3.12, 3.13 | Declared package and CI matrix; local release-check on 3.12.13 |
| Pydantic | `>=2.10,<3` | Core contract suite |
| HTTPX | `>=0.27,<1` | Mock-transport protocol suite and installed-wheel smoke |
| OpenRouter endpoint | `/api/v1/chat/completions` | Request, response, streaming and error fixtures |
| OpenRouter catalog | `/api/v1/models` | Mapping, TTL, concurrency and malformed-response tests |
| Catalog snapshots | schema v1 read; schema v2 read/write | Compatibility and integrity tests |

Python 3.11 and 3.13 are CI responsibilities for this archive; they were not independently
executed in the local release environment.

## Feature matrix

| Capability | Adapter | Qualification | Important boundary |
|---|---:|---|---|
| Text messages | Yes | Offline contract pass | Concrete model must support text |
| Image input | Yes | Mapping pass | Catalog/model dependent |
| Audio/document input | Core types only | Not mapped by this adapter | Outside 0.2.0 adapter contract |
| Tool calling | Yes | Request/response pass | Catalog/model/provider dependent |
| Parallel tool calls | Yes | Mapping and capability pass | Runtime executes tools sequentially |
| Structured output | Yes | Mapping pass | Requires catalog support and `require_parameters` |
| SSE streaming | Yes | Fragment and terminal-event pass | `Runner` still consumes complete responses |
| Usage and reported cost | Yes | Normalization pass | No local price calculation or billing guarantee |
| Provider endpoint fallback | Yes | Policy fixture pass | Disabled by evaluation/default legacy policy |
| Model fallback | Yes | Ordered body and capability-chain pass | Live failover not executed in release environment |
| Provider allow/ignore/order | Yes | Validation and wire fixture pass | Slugs remain upstream-controlled |
| ZDR constraint | Yes | Policy/wire fixture pass | Inference endpoints only; not third-party plugins/tools |
| Data-collection constraint | Yes | Policy/wire fixture pass | Account and provider policy remain external |
| Router metadata | Yes | Normal, error and stream fixture pass | Safe subset only; cache hits may omit it |
| Offline catalog | Yes | Secret-free round-trip pass | Snapshot integrity is not provenance |

## Named routing profiles

| Profile | Provider fallback | Parameter support | Data policy | Intended use |
|---|---:|---:|---|---|
| Development | Enabled | Required | Optional allowlist | Local integration work |
| Production | Enabled | Required | Collection denied; optional allowlist | Availability-oriented deployment |
| Compliance | Disabled | Required | ZDR + collection denied + mandatory allowlist | Controlled data path |
| Evaluation | Disabled | Required | Optional pinned allowlist | Reproducible tests and benchmarks |

Profiles are transparent presets, not remote compliance certifications.

## Provider and model qualification levels

| Level | Meaning | Status in 0.2.0 |
|---|---|---|
| Adapter contract | Payloads, parsing, policies, errors and events against deterministic fixtures | Passed |
| Package contract | Wheel/sdist, metadata, import and offline installed-wheel scenario | Passed |
| Account contract | Authentication, credits and account policy against a real OpenRouter account | Not run |
| Concrete model contract | One selected model/provider combination tested live | Not run |
| Fallback contract | A forced real fallback resolves to the expected model/provider | Available opt-in; not run |
| Compliance contract | A real request proves the configured ZDR/provider allowlist path | Available opt-in; not run |

Therefore `0.2.0` is stable at the framework/API level. It does not certify every model exposed by
OpenRouter. Deployment owners should run the gated qualification suite with their actual account,
models and policies before production use.
