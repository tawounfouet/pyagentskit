# ADR-0016 — Explicit state stores and context policies

- Status: Accepted
- Date: 2026-09-05

## Context

Conversation history, long-term memory, model context and binary artifacts have different lifecycle,
privacy and size properties. Treating them as one opaque memory object would couple the runtime to
a database or RAG implementation and make retention decisions invisible.

## Decision

Define separate `SessionStore`, `MemoryStore`, `ContextPolicy`, `ContextSource` and `ArtifactStore`
contracts. Provide memory/SQLite implementations for structured state and memory/filesystem
implementations for bytes. Keep all integrations opt-in.

Session appends are idempotent and revisioned. Context selection is explainable and budgeted before
provider access. Artifacts are tenant-scoped references with size and SHA-256 metadata. External RAG
and summarization enter only through injected protocols.

## Consequences

- a stateless application keeps the existing Runner behavior;
- stores can be replaced without changing providers or tools;
- no vector database, embedding model or workflow engine becomes mandatory;
- local SQLite provides restart persistence but not durable run replay;
- applications retain responsibility for encryption, maintenance scheduling and external retrieval
  policy.
