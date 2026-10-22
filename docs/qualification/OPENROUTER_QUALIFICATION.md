# OpenRouter qualification — PyAgentsKit 0.2.0a1

Qualification date: 2026-09-05

## Result

| Evidence level | Status | Meaning |
|---|---:|---|
| Core protocol conformance | Pass | Implements PyAgentsKit `Model` without core coupling |
| HTTP contract | Pass | Request, response, stream and error fixtures pass |
| Runner integration | Pass | Agent/provider/model preflight and complete run pass |
| Distribution | Pass | Built wheel installs and offline smoke scenario passes |
| Live OpenRouter | Not run | No API key; no account/model claim made |

## Contract-qualified behaviors

- bearer authentication and optional application attribution headers;
- organization-prefixed model selection;
- normalized messages, image references and tool-result history;
- provider-safe tool names and validated JSON arguments;
- strict JSON Schema response format;
- OpenRouter `max_tokens` parameter and SSE stream framing;
- deterministic provider preferences on every request;
- reported input, output, cached and reasoning tokens;
- reported cost and BYOK marker;
- requested model, resolved model, upstream provider and generation ID;
- HTTP errors, HTTP 200 error envelopes, choice errors and in-stream errors;
- sanitized stable `error_type` and original numeric/provider codes;
- malformed JSON, malformed costs, truncation, refusal and cancellation inherited from the
  qualified Chat Completions transport.

## Determinism statement

The adapter sends one explicit `model` and no `models` fallback list. It defaults to:

```json
{"provider":{"allow_fallbacks":false,"require_parameters":true}}
```

This prevents provider-endpoint fallback by default and rejects endpoints that do not support all
requested parameters. The response still records the resolved model and upstream provider when
OpenRouter supplies them.

## Capability boundary

The adapter's defaults describe implemented mapping features, not certification of every model in
the OpenRouter catalog. Default capability metadata therefore contains:

```json
{"source":"adapter_default","model_verified":false,"router":"openrouter"}
```

The deployment owner must qualify the concrete model for tools, JSON Schema, streaming, modality,
context size, regional endpoint, privacy policy and account quota.

## Error mapping

Stable `error_type` values are retained in `ModelError.metadata`. Raw error messages and arbitrary
provider metadata are deliberately excluded to avoid leaking prompts or upstream internals.
Authentication, rate-limit, timeout and availability categories map to their dedicated
PyAgentsKit exceptions; other policy and validation errors map to `ModelResponseError`.

## Live gate

The included smoke test runs only when both variables are configured deliberately:

```text
PYAGENTSKIT_OPENROUTER_LIVE=1
PYAGENTSKIT_OPENROUTER_MODEL=provider/model
```

It may incur charges. The release environment had no `OPENROUTER_API_KEY`, so the test remained
skipped and no authenticated request was attempted.

## Official protocol references

- [OpenRouter API reference](https://openrouter.ai/docs/api_reference/overview)
- [Tool calling](https://openrouter.ai/docs/guides/features/tool-calling)
- [Structured outputs](https://openrouter.ai/docs/guides/features/structured-outputs)
- [Streaming](https://openrouter.ai/docs/api_reference/streaming)
- [Typed errors](https://openrouter.ai/docs/api_reference/errors-and-debugging)
- [Provider routing](https://openrouter.ai/docs/guides/routing/provider-selection)
- [Model fallbacks](https://openrouter.ai/docs/guides/routing/model-fallbacks)
