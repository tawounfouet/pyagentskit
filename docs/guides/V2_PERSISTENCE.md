# Persistence V2

PyAgentsKit `2.0.0a4` introduces the production persistence boundary for the V2 reliability
model. The persistence layer protects domain semantics; it does not redefine them.

## Supported V2 persistence surfaces

The V2 contracts cover:

- Run;
- Session;
- Conversation;
- ConversationMessage;
- MemoryEntry;
- Effect;
- ReconciliationCase and evidence;
- Approval;
- Lease and monotonic fencing;
- Worker;
- RuntimeBinding and RuntimeInvocation;
- Artifact metadata;
- Audit;
- Outbox;
- Inbox.

Reference adapters are available for in-memory execution, SQLite and PostgreSQL where applicable.

## Unit of Work

Use a Unit of Work when multiple durable changes must commit or roll back together.

Typical boundary:

```text
Domain state
+ Audit
+ Outbox append
= one local database transaction
```

External network effects are intentionally kept outside long-running database transactions.

Example:

```python
async with uow:
    await uow.sessions.add(session)
    await uow.conversations.add(conversation)
    await uow.outbox.append(event)
    await uow.commit()
```

If the context exits without `commit()`, the transaction rolls back.

## Optimistic concurrency

Versioned aggregates use compare-and-swap semantics.

A write supplies the version it observed:

```text
expected_version
→ update only if current_version matches
→ otherwise ConcurrencyConflictError
```

This prevents silent last-write-wins corruption.

## Effect idempotency

Effect idempotency is a durable business guarantee, not queue deduplication.

The persistence layer stores a logical idempotency identity and input fingerprint. Reusing the same
idempotency key with a different fingerprint fails closed with `IdempotencyConflictError`.

```text
Inbox dedup != Effect idempotency
```

## Leases and fencing

Lease ownership is protected by:

- one active owner per resource;
- monotonic fencing tokens;
- compare-and-swap updates;
- explicit takeover after prior ownership is no longer active.

A lease check alone is not enough for a protected external resource. The target system must reject
stale fencing tokens when the operation requires split-brain protection.

## Outbox and Inbox

The V2 Outbox supports durable publication with claim/reclaim behavior. A publisher crash may lead
to redelivery, so consumers must tolerate duplicates.

The Inbox provides transport-message deduplication:

- same external event ID + same digest → no-op;
- same external event ID + different digest → hard conflict.

Neither mechanism claims universal exactly-once delivery.

## SQLite

SQLite is retained for local/single-host durability and contract qualification.

The V2 schema is versioned:

```text
0001_v2_core.sql
0002_v2_catalog.sql
```

The migration runner applies missing versions incrementally and refuses a database whose schema is
newer than the code understands.

Run the offline example:

```bash
python examples/v2_persistence.py
```

## PostgreSQL

Install the optional dependency:

```bash
pip install "pyagentskit[postgres]"
```

PostgreSQL is the production-oriented V2 relational backend. CI qualifies it against a real
PostgreSQL service, including:

- repository contracts;
- compare-and-swap conflicts;
- Effect idempotency;
- monotonic fencing;
- one-active-lease behavior;
- transactional UnitOfWork + Outbox;
- Inbox deduplication;
- claim recovery;
- multi-process lease contention.

Applications remain responsible for connection lifecycle, credentials, TLS, backup/restore,
retention and deployment policy.

## Migrations

Persistence V2 migrations are forward, versioned migrations.

A4 proves the SQLite v1 → v2 migration path directly and exercises PostgreSQL migration application
against a real service.

Database restore is not equivalent to safe runtime resume. After restore, Effect truth, leases,
fencing generation and recovery preconditions must still be re-evaluated.

## Error normalization

Infrastructure adapters preserve canonical PyAgentsKit domain/persistence errors for expected
conflicts, including:

- `ConcurrencyConflictError`;
- `DuplicateAggregateError`;
- `IdempotencyConflictError`;
- `InboxDigestConflictError`;
- persistence corruption/failure errors.

Provider-specific database exceptions must not leak into the Domain contract.

## Known limitations

- SQLite is not a cross-host coordination backend.
- Exactly-once delivery is not promised.
- PostgreSQL credentials, pooling and operational policy are application-owned.
- Multi-region persistence architecture is outside A4.
- External runtime/provider connectors remain later milestones.
- Restore/PITR requires recovery revalidation; persistence alone does not authorize replay.
