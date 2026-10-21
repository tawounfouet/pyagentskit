# ADR-0010 — Optional HTTP adapters and typed tool history

Accepted 2026-09-05 for 0.1.0rc1.

Adapters use HTTPX against documented REST endpoints, rather than vendor SDK types.
Each provider extra installs HTTPX; the core still only requires Pydantic.
OpenAI uses Chat Completions for this milestone, not Responses or the Agents SDK.
This choice limits the delivered scope to explicit user-defined tools and normalized messages.

Message.tool_calls is now the canonical typed history of assistant tool requests. Beta code
putting calls in metadata must migrate. Vendor-only opaque data remains in namespaced metadata.
Tool identifiers are hashed to valid wire aliases and mapped back on responses; names with dots
therefore remain usable without leaking vendor naming restrictions into the tool registry.

Retries default to zero. Up to three retries may be configured for explicit HTTP 429/5xx only.
Streams and ambiguous transport failures are never retried. No SDK adds hidden retries.
Client lifetime is explicit through aclose; injected clients stay application-owned.

This is an implementation choice, not a claim of universal model capability. Applications select
a model supporting the declared capabilities and may disable capabilities on the adapter.
