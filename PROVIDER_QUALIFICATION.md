# Provider qualification — PyAgentsKit 0.1.0

Qualification date: 2026-09-05

## Claim levels

This report intentionally separates three different claims:

1. **Contract-qualified** — request mapping, response normalization, tool history, streaming,
   errors and cancellation pass deterministic tests through real HTTPX request/response objects.
2. **Distribution-qualified** — the installed stable wheel imports and executes an offline agent
   scenario outside the source tree.
3. **Live-qualified** — authenticated calls to a concrete provider account and selected model pass
   smoke and feature tests.

Only the first two levels are release claims. Live tests were skipped because `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY` and `XAI_API_KEY` were absent and no local Ollama endpoint was
reachable. No billable request was made.

## Qualification matrix

| Provider adapter | Native protocol | Contract | Distribution | Live | Important constraint |
|---|---|---:|---:|---:|---|
| OpenAI | Chat Completions | Pass | Pass | Not run | Uses Chat Completions; no Responses API adapter in 0.1.0 |
| Anthropic | Messages | Pass | Pass | Not run | Images are rejected by this adapter version |
| Google Gemini | `generateContent` | Pass | Pass | Not run | Tools and output schema cannot be combined in one request |
| xAI | Chat Completions | Pass | Pass | Not run | Model capability depends on the selected xAI model |
| Ollama | Native `/api/chat` | Pass | Pass | Not run | User must run and provision the Ollama service/model |

## Contract evidence

The offline provider suite verifies, where supported:

- authentication placement and safe base-URL validation;
- normalized text responses, finish reasons and resolved model IDs;
- provider-safe tool aliases and mapping back to canonical tool names;
- assistant tool calls and tool-result history reconstruction;
- strict structured-output request mapping and local Pydantic validation;
- incremental SSE or NDJSON text/tool/usage events;
- buffering and validation of streamed tool arguments;
- cancellation and explicit stream closure;
- malformed response and refusal handling;
- normalized authentication, rate-limit, timeout and availability errors;
- no retry after partial stream delivery;
- usage normalization without inventing unavailable cost data.

Fixtures are hand-authored from documented provider formats. They are not recordings of production
responses and do not prove account access, latency, rate limits, current model availability or
model quality.

## Capability declaration policy

The default `ModelCapabilities` returned by an adapter describes features implemented by its
protocol mapper. It carries:

```json
{
  "source": "adapter_default",
  "model_verified": false
}
```

Applications should select a concrete model deliberately and supply a reduced/model-specific
capability declaration when necessary. `Runner` checks the agent's requested provider and model
against the injected adapter before the first network request. There is no automatic catalog or
remote capability probe in `0.1.0`.

## Reproducing optional live smoke tests

Live tests are disabled unless an exact provider gate is set to `1`; they can incur charges.

| Provider | Gate | Required model variable |
|---|---|---|
| OpenAI | `PYAGENTSKIT_OPENAI_LIVE=1` | `PYAGENTSKIT_OPENAI_MODEL` |
| Anthropic | `PYAGENTSKIT_ANTHROPIC_LIVE=1` | `PYAGENTSKIT_ANTHROPIC_MODEL` |
| Google | `PYAGENTSKIT_GOOGLE_LIVE=1` | `PYAGENTSKIT_GOOGLE_MODEL` |
| xAI | `PYAGENTSKIT_XAI_LIVE=1` | `PYAGENTSKIT_XAI_MODEL` |
| Ollama | `PYAGENTSKIT_OLLAMA_LIVE=1` | `PYAGENTSKIT_OLLAMA_MODEL` |

The embedding application should additionally qualify the exact production model for tools,
structured output, streaming, privacy policy, regional endpoint and budget behavior.

## Protocol references

- [OpenAI Chat Completions](https://developers.openai.com/api/reference/resources/chat/subresources/completions/methods/create)
- [Anthropic tool definitions](https://platform.claude.com/docs/en/agents-and-tools/tool-use/define-tools)
- [Google Gemini generateContent](https://ai.google.dev/api/generate-content)
- [xAI Chat Completions](https://docs.x.ai/developers/rest-api-reference/inference/chat)
- [Ollama chat](https://docs.ollama.com/api/chat)
