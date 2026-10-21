# Sessions, context, memory and artifacts — 0.3.0

## Session lifecycle

Create a session explicitly, then pass its ID and optional tenant scope through `RunContext`:

```python
from pyagentskit import MemorySessionStore, RunContext, Session
from pyagentskit.runs import utc_now

store = MemorySessionStore()
now = utc_now()
await store.create(
    Session(
        session_id="conversation-1",
        agent_id="support",
        tenant_id="tenant-a",
        created_at=now,
        updated_at=now,
    )
)
context = RunContext(
    agent_id="support",
    deps=None,
    session_id="conversation-1",
    metadata={"tenant_id": "tenant-a"},
)
result = await Runner(model, session_store=store).run(agent, "Hello", context=context)
```

The runtime stores user, assistant and tool messages with idempotency keys derived from the run.
It rejects an agent mismatch, a cross-tenant lookup or a concurrent stale revision before calling
the model. Applications should use a new `RunContext` for each logical turn.

`SQLiteSessionStore(path)` offers the same contract with WAL mode and migration version 1. The
SQLite store survives process restart; it is not a distributed checkpoint or worker system.

## Context policies

`FullContextPolicy` retains everything and rejects a known overflow. `WindowContextPolicy` keeps
system messages, the current message and the newest groups fitting the message/token budget.
Assistant tool calls and their immediate tool results are atomic.

`SummarizingContextPolicy` calls an injected async summarizer only when messages were removed. Blank,
oversized and over-budget summaries fail closed. The summarizer's network access, credentials,
privacy and cost are owned by the embedding application.

Token estimation serializes each normalized message and divides characters by a configurable
ratio. It is deterministic and conservative but is not equivalent to any provider tokenizer.
Provider-reported usage limits still apply after each call.

## Memory and external retrieval

`InMemoryMemoryStore` and `SQLiteMemoryStore` provide explicit lexical records scoped by tenant,
agent and optional session. Search supports substring matching and tags. No embedding, vector index
or hidden model request occurs.

`MemoryContextSource` is an opt-in bridge. Any RAG system can implement `ContextSource.retrieve()`
and return normalized messages. Retrieved content is not automatically persisted in the session.
Treat retrieved text as untrusted unless the application controls its provenance; Lot 09 will add
guardrail and classified-data policy hooks.

## Artifacts and large results

`MemoryArtifactStore` is ephemeral. `FileSystemArtifactStore` writes bytes atomically beneath an
application-controlled root and persists a metadata sidecar. Every read checks size and SHA-256.
Serialized sessions/results contain only `ArtifactRef`, never the bytes.

Configure runtime externalization explicitly:

```python
runner = Runner(
    model,
    artifact_store=artifact_store,
    artifact_policy=ArtifactRetentionPolicy(
        inline_threshold_bytes=64_000,
        default_ttl_seconds=86_400,
        delete_with_session=True,
    ),
)
```

When a normalized tool result crosses the threshold, the model receives a compact JSON artifact
reference. This is appropriate when the model does not need the full payload for its next decision.
Applications requiring content-aware retrieval should provide a `ContextSource` that reads and
selects relevant artifact content.

Use `SessionStateManager.delete()` to apply `delete_with_session`. Coordination across replaceable
stores is best-effort, not a distributed transaction.

## Sensitive data and retention

- Do not place credentials in messages, memory content, artifact provenance or metadata.
- Use tenant IDs on every operation in multi-tenant applications.
- Define expirations and run `purge_expired()` from an application-owned maintenance job.
- Restrict filesystem permissions and backups outside PyAgentsKit.
- Encrypt disks/databases through the deployment platform when required.
- Do not treat SHA-256 as encryption or proof of artifact origin.
- Keep external summarizer/RAG logging and provider retention policies explicit.
