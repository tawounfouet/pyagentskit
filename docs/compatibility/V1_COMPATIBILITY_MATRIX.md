# PyAgentsKit 1.0.0 — Compatibility matrix

## Runtime

| Target | Status | Evidence |
|---|---|---|
| Python 3.11 | Supported | CI matrix |
| Python 3.12 | Supported | CI matrix and local release-check |
| Python 3.13 | Supported | CI matrix |
| Pydantic 2.10–2.x | Supported | Declared bounded dependency and contract tests |
| Base install without HTTPX | Supported | Provider imports remain optional |
| Linux | Qualified | Local release-check and CI |
| macOS/Windows | Expected | Pure Python package; not locally qualified for this release |

## Provider adapters

| Adapter | Transport | Tools | Structured output | Streaming | V1 contract |
|---|---|---:|---:|---:|---|
| OpenAI | Chat Completions / SSE | Yes | Yes | Yes | Deterministic HTTP qualification |
| Anthropic | Messages / SSE | Yes | Yes | Yes | Deterministic HTTP qualification |
| Google Gemini | `generateContent` / SSE | Yes | Yes, constrained | Yes | Deterministic HTTP qualification |
| xAI | Chat Completions / SSE | Yes | Yes | Yes | Deterministic HTTP qualification |
| Ollama | Native chat / NDJSON | Yes | Yes | Yes | Deterministic HTTP qualification |
| OpenRouter | Routed Chat Completions / SSE | Yes | Yes | Yes | Stable routing/catalog/API suite |

These rows describe adapter envelopes, not every available model ID. Concrete model revisions,
provider regions, ZDR eligibility, pricing and quotas require deployment-time live qualification.
The nine live tests remain opt-in and were not run during the offline release build.
