# PyAgentsKit 0.1.0

Release date: 2026-09-05  
Baseline: `0.1.0rc2`

PyAgentsKit `0.1.0` is the first stable pre-1.0 release of the typed, observable and
provider-neutral mono-agent runtime.

## Stable scope

- Immutable public contracts for agents, messages, model calls, tools, runs, events and usage.
- Strict `@tool` decoration, schema generation, registry, policies, timeouts and execution.
- Bounded async `Runner`, safe synchronous facade, cancellation and structured output validation.
- Deterministic `FakeModel` and in-memory event infrastructure for network-free tests.
- Five optional HTTP provider adapters: OpenAI, Anthropic, Google Gemini, xAI and Ollama.
- Text, tool calls, structured output and native streaming within each documented adapter envelope.
- Provider-neutral error, usage and requested/resolved model normalization.

## Stabilization since RC2

- Provider/model declarations are checked against the injected adapter before networking.
- Exact token limits are valid; only actual overruns fail.
- Exhausted output budgets stop before an additional provider request.
- Model events identify the requested and resolved provider/model and response ID.
- HTTP 408 maps to a retryable timeout.
- Model IDs are normalized and whitespace-only cloud credentials are rejected.
- Every provider adapter supports `async with` for owned resource cleanup.
- Default capability declarations state that they are adapter, not model, defaults.
- Stable documentation, release audit, provider matrix and reproducible release-check are included.

## Qualification statement

The complete offline suite uses deterministic HTTPX transports to exercise the five protocols.
The wheel is installed and exercised outside the source tree. Live account/model tests remain
explicitly opt-in and were not run because credentials and a local Ollama service were unavailable.
This release therefore claims protocol-contract and distribution qualification, not live-provider
or model-quality certification.

## Compatibility and migration

- The public package version is now `0.1.0`.
- The preferred OpenAI live-test gate is `PYAGENTSKIT_OPENAI_LIVE=1`; the RC legacy gate remains
  accepted in this release.
- `AgentDefinition.model.provider` and `.name` must match the injected provider adapter.
- Code that relied on exact-limit rejection should update its expectations: limits are inclusive.
- Provider HTTP clients created by PyAgentsKit can now be managed with `async with`.

## Known limitations

- Single agent and sequential tool execution only.
- No persistent sessions, checkpoints, approval workflow or multi-agent orchestration.
- No automatic routing, fallback, model catalog, pricing table or cost guarantee.
- `Runner` uses complete responses; direct adapter streaming is a separate API.
- Model capability and availability still require deployment-specific verification.

## Verification

Run:

```bash
python scripts/release_check.py
```

Measured results for this archive are recorded in `CHECK_RESULTS.md`. The detailed RC2 findings
and provider evidence are in `AUDIT_RC2.md` and `PROVIDER_QUALIFICATION.md`.

## Next milestone

`0.2.0a1` will add a minimal optional OpenRouter adapter while preserving the independent
`Model` contract. Routing, dynamic catalog, fallbacks and data-governance policy follow in later
`0.2.0` prereleases.
