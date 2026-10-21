# Provider adapters — 0.2.0

## Installation and identity

| Class/module under pyagentskit.providers | Extra | Environment key | API |
|---|---|---|---|
| OpenAIModel / openai | openai | OPENAI_API_KEY | OpenAI Chat Completions |
| AnthropicModel / anthropic | anthropic | ANTHROPIC_API_KEY | Anthropic Messages |
| GoogleModel / google | google | GOOGLE_API_KEY | Gemini generateContent |
| XAIModel / xai | xai | XAI_API_KEY | xAI Chat Completions |
| OllamaModel / ollama | ollama | Optional OLLAMA_API_KEY | Native Ollama chat |
| OpenRouterModel / openrouter | openrouter | OPENROUTER_API_KEY | OpenRouter Chat Completions |

Install `pip install '.[providers]'` to enable all adapters or select one extra.
All extras currently resolve to HTTPX >=0.27,<1. There is no SDK dependency.

```python
from pyagentskit.providers.anthropic import AnthropicModel
from pyagentskit.runtime import Runner

async with AnthropicModel(model="YOUR_MODEL_ID") as model:
    result = await Runner(model, tools=registry).run(agent_definition, "Question")
```

Model names are explicit and not hardcoded to a current/latest model. Keep `AgentDefinition.model`
aligned with the injected adapter: `Runner` validates the declared provider and model before the
first network request. It does not resolve model names or switch providers.
An injected HTTPX AsyncClient stays caller-owned. Default clients disable redirects and environment
proxy discovery. Do not log transport headers, raw prompts or opaque provider history.

## Delivered capability matrix

| Adapter | Text | Image input | Tools | Structured output | Native streaming |
|---|---|---|---|---|---|
| OpenAI | Yes | Yes | Yes | Strict schema subset | SSE |
| Anthropic | Yes | Rejected | Yes | Strict schema subset | SSE |
| Google | Yes | Rejected | Yes | JSON schema, without tools in same request | SSE |
| xAI | Yes | Yes | Yes | Strict schema subset | SSE |
| Ollama | Yes | Rejected | Yes | JSON schema format | NDJSON |
| OpenRouter | Yes | Yes | Yes | Strict schema subset | SSE |

Capabilities are adapter features, not a guarantee for every model name. Adapter defaults include
`source=adapter_default` and `model_verified=false`. Select a model with the required features or
supply a model-specific `ModelCapabilities` object. No automatic remote model catalog or runtime
capability probing is implemented. Audio, documents, server tools, browsing and arbitrary code
execution are outside these adapters.

## Tools and conversation history

Message.tool_calls is the canonical typed assistant-call field. Tool results use tool_call_id and
name. Qualified names such as customer.get become provider-safe hashes on the wire and are mapped
back to the registered name. Unknown returned tool names fail closed.

Anthropic maps tool calls to tool_use blocks and groups consecutive tool_result blocks in one user
message. Google maps to functionCall/functionResponse and preserves thoughtSignature in google_parts
metadata; native function IDs are returned when supplied. Ollama creates local correlation IDs when
the service has none. Opaque reasoning/signature blocks are replayed, not placed in public text.

## Streaming and cancellation

Use `async for event in model.stream(request, context=context)`. Events include STARTED, TEXT_DELTA,
TOOL_CALL_COMPLETED, USAGE and COMPLETED. Tool argument fragments are buffered until valid JSON;
they must not be executed incrementally. Native adapters include the normalized full response in
the terminal event metadata for history reconstruction. Runner continues to use generate, not stream.
Use contextlib.aclosing when leaving an async stream early; exhaust or close streams explicitly.
Cancellation propagates and closes the underlying response context. No retry occurs after partial
stream delivery. Truncated streams and provider refusal/error stops raise normalized errors.

## Settings, safety and budget semantics

Common settings: max_output_tokens, temperature, top_p; seed where supported (not Anthropic).
Arbitrary provider parameters are rejected. This excludes custom thinking controls and model-specific
options; support can be added through explicit provider configuration in a later release.

Retries default to zero and can be 0..3 for explicit 429/selected 5xx statuses, with bounded numeric
Retry-After delays. Transport failures and streams are not retried. Costs remain unknown; reported
usage limits cannot guarantee a billing ceiling. Missing usage uses legacy zero counters plus
usage_reported=false metadata. Anthropic normalized input includes cache reads/writes; Gemini
normalized output includes thought tokens. Neither cache nor reasoning counters are added twice.

Base URLs must be HTTPS except loopback HTTP. No redirect is followed. A remote Ollama deployment
requires an HTTPS endpoint. Applications remain responsible for selected hosts, TLS, data policy,
model capability checks, log redaction and credential management.

## Live smoke tests — opt-in and potentially billable

No live test was executed during delivery. Provide keys through your normal secret mechanism;
never commit them. Explicit gates:

| Provider | Opt-in variable = 1 | Model variable |
|---|---|---|
| OpenAI | PYAGENTSKIT_OPENAI_LIVE | PYAGENTSKIT_OPENAI_MODEL |
| Anthropic | PYAGENTSKIT_ANTHROPIC_LIVE | PYAGENTSKIT_ANTHROPIC_MODEL |
| Google | PYAGENTSKIT_GOOGLE_LIVE | PYAGENTSKIT_GOOGLE_MODEL |
| xAI | PYAGENTSKIT_XAI_LIVE | PYAGENTSKIT_XAI_MODEL |
| Ollama | PYAGENTSKIT_OLLAMA_LIVE | PYAGENTSKIT_OLLAMA_MODEL |
| OpenRouter | PYAGENTSKIT_OPENROUTER_LIVE | PYAGENTSKIT_OPENROUTER_MODEL |

The legacy OpenAI gate `PYAGENTSKIT_LIVE_OPENAI=1` remains accepted for this release. Run
`pytest tests/test_openai_provider.py tests/test_provider_regressions.py` after explicit opt-in.
Smoke tests only check text generation; real tool/schema/stream validation for each selected model
is a release-acceptance task for the deploying application, not a claim established by these mocks.

## Sources used to implement wire contracts

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [OpenAI structured output](https://developers.openai.com/api/docs/guides/structured-outputs)
- [Anthropic tool results](https://platform.claude.com/docs/en/agents-and-tools/tool-use/handle-tool-calls)
- [Anthropic SSE](https://platform.claude.com/docs/en/build-with-claude/streaming)
- [Anthropic output_config.format](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Gemini function calling](https://ai.google.dev/gemini-api/docs/function-calling)
- [Gemini generateContent REST](https://ai.google.dev/api/generate-content)
- [xAI text APIs](https://docs.x.ai/developers/model-capabilities/text/generate-text)
- [Ollama native chat](https://docs.ollama.com/api/chat)

## Revised release train

`0.1.0` stabilized the mono-agent runtime and five direct adapters. `0.2.0` stabilizes explicit
OpenRouter policies, catalog/cache, fallback-chain preflight, ZDR/data controls and safe streaming
route metadata. The OpenRouter public surface is frozen for `0.2.x`. Sessions, context policies,
guardrails and checkpoints remain later lots.

See [the dedicated OpenRouter guide](OPENROUTER.md) before enabling it in an application.
