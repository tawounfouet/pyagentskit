# RC2 audit — qualification for PyAgentsKit 0.1.0

Audit date: 2026-09-05  
Audited baseline: `0.1.0rc2`  
Stable target: `0.1.0`

## Scope and method

The audit covered the public core contracts, the mono-agent state machine, typed tool execution,
event envelopes, all five HTTP adapters, packaging, examples, security notes and release evidence.
It used code inspection, targeted regression tests, the complete offline suite and installation of
the built wheel outside the source directory.

No provider key was present and no Ollama service was reachable on loopback. Consequently, live
account access and concrete remote model quality are not part of this audit's evidence.

## Findings closed for stable

| ID | Severity | Finding | Stable resolution | Regression evidence |
|---|---|---|---|---|
| A-01 | High | An agent definition could name a different provider/model than the injected adapter. | `Runner` rejects the mismatch before networking. | `test_stable_release.py` |
| A-02 | High | A run reaching exactly its configured token limit was rejected. | Limits now reject only actual overruns. | `test_beta_runtime.py` |
| A-03 | High | A second model call could start with zero output tokens remaining. | The runtime raises `RunLimitExceeded` before the next call. | `test_beta_runtime.py` |
| A-04 | Medium | Model events did not consistently identify requested and resolved models. | Request/response/failure events carry normalized identity fields. | `test_beta_runtime.py` |
| A-05 | Medium | README, roadmap and lifecycle wording still described prereleases. | Documentation and examples now describe `0.1.0`. | package/sdist checks |
| A-06 | Medium | Whitespace around model IDs was preserved. | Constructors normalize model IDs and reject empty results. | provider tests |
| A-07 | Medium | Whitespace-only API keys passed construction. | Cloud adapters fail configuration immediately. | provider tests |
| A-08 | Medium | HTTP 408 did not normalize as a timeout. | It maps to retryable `ModelTimeoutError`. | OpenAI transport test |
| A-09 | Low | Owned HTTP clients required manual `aclose()` boilerplate. | Every adapter is an async context manager. | provider tests |
| A-10 | Medium | Adapter capabilities could be mistaken for model-level certification. | Defaults expose `source=adapter_default`, `model_verified=false`. | stable contract test |
| A-11 | Medium | Resolved model identity was not uniform in native response metadata. | Adapters expose normalized `resolved_model`. | native provider tests |
| A-12 | Low | Prior distributions contained prerelease metadata. | Stable wheel and sdist are rebuilt and checked from source. | release-check |

## Core invariants rechecked

- Every model and tool loop is bounded by explicit call, step, time and reported-usage limits.
- Model responses, tool arguments, tool results and provider metadata remain untrusted inputs.
- Tools are resolved through a registry and receive strictly validated Pydantic inputs.
- Approval-required tools fail closed because the stable release has no approval workflow.
- Sync tools execute outside the event-loop thread; cancellation cannot terminate an already
  running Python thread and this limitation remains documented.
- Provider types and HTTPX do not enter the dependency-minimal core contract modules.
- Exceptions and public events omit prompts, raw tool arguments, credentials and transport headers.
- Streaming buffers tool arguments until complete JSON and never retries after partial delivery.

## Accepted stable limitations

The following are deliberate scope boundaries, not unresolved release blockers:

- single-agent execution and sequential tool calls;
- no sessions, durable checkpoints, HITL workflow or multi-agent orchestration;
- no automatic model catalog, model fallback, provider routing or cost lookup;
- complete-response `Runner`; streaming is consumed directly from adapters;
- provider-reported usage can enforce observed token limits but not a guaranteed billing ceiling;
- adapter capability envelopes require deployment-specific model selection and qualification;
- provider APIs can change independently of this release.

## Audit conclusion

No known critical or high-severity finding remains open within the declared `0.1.0` scope. The
release is qualified as a stable pre-1.0 development library, subject to the accepted limitations
and the provider evidence boundary documented in `PROVIDER_QUALIFICATION.md`.
