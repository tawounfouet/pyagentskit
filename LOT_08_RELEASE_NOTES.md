# PyAgentsKit 0.3.0 — sessions, context, memory and artifacts

Release date: 2026-09-05. Baseline: `0.2.0`.

## Delivered

- immutable `Session` and ordered `SessionEntry` contracts;
- replaceable `SessionStore` protocol with memory and SQLite implementations;
- idempotent append fingerprints and optimistic session revisions;
- tenant-scoped session, memory and artifact access;
- versioned SQLite migrations shared safely by session and memory components;
- `FullContextPolicy`, `WindowContextPolicy` and injected `SummarizingContextPolicy`;
- pre-request approximate context budgeting with explainable decisions;
- atomic preservation of assistant tool calls with their immediate tool results;
- explicit `ContextSource` hook for application-owned RAG/retrieval;
- lexical `MemoryStore` protocol with memory and SQLite implementations;
- opt-in `MemoryContextSource` bridge;
- memory and filesystem artifact stores with SHA-256 verification;
- retention, expiry, deletion and session-artifact cascade policy;
- optional runtime session reconstruction and large tool-result externalization;
- session/context/artifact events and result metadata;
- stable `0.3.x` API contract and offline example.

## Compatibility

Existing stateless `Runner` construction and all six provider adapters remain compatible. Session,
memory, context-source and artifact behavior is opt-in. The OpenRouter `0.2.x` API freeze remains
covered by its golden tests.

## Boundaries

- SQLite provides local durable conversation state, not a distributed run/checkpoint engine.
- Approximate token budgeting cannot replace provider tokenization or billed-usage checks.
- Memory retrieval is lexical; no vector database or embedding model is imposed.
- An injected summarizer or RAG source is an external operation governed by its application.
- Filesystem artifact storage assumes an application-controlled local root.
- Cross-store session/artifact deletion is coordinated but not transactionally distributed.
- Run crash recovery, approvals and durable tool-effect replay remain later lots.

## Next milestone

Lot 09 / `0.4.0`: guardrails, classified-data policy and human approval workflows.
