# ADR-0011 — Native providers before 0.1.0 stable

Accepted 2026-09-05 on explicit user request.

Release 0.1.0rc2 adds Anthropic, Google Gemini, xAI and Ollama before stable 0.1.0.
The earlier plan placing non-OpenAI-native validation after V1 is superseded for these adapters.
OpenRouter stays in planned 0.2.0. No multi-agent, persistence or session scope is added.

Anthropic, Gemini and Ollama own native request/response/history mappings. Only xAI inherits
the OpenAI-compatible wire implementation. HTTP lifecycle code is shared, domain contracts are not
vendor SDK objects. Native opaque blocks live in namespaced metadata and must not be logged.

Default features are explicitly limited to the documented capability matrix. Model-specific live
acceptance remains pending; mocked transport tests are not evidence of all-model compatibility.
