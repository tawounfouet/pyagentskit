# PyAgentsKit 2.0.0a4

## Persistence V2

PyAgentsKit `2.0.0a4` turns the V2 reliability semantics into durable repository and store
contracts backed by in-memory, SQLite and PostgreSQL implementations.

The milestone is designed around fail-closed persistence guarantees rather than generic CRUD.

## Highlights

- Complete V2 repository contracts for Run, Session, Conversation, Message, Memory, Effect,
  Reconciliation, Approval, Lease, Worker, Runtime and Artifact state.
- Technology-neutral `AuditStore`, `OutboxStore`, `InboxStore`, `BlobStore` and
  `UnitOfWork` contracts.
- In-memory reference repositories used by the shared contract suite.
- SQLite V2 persistence with versioned incremental migrations.
- PostgreSQL V2 normalized persistence with real CI qualification.
- Durable RuntimeBinding and RuntimeInvocation persistence.
- Compare-and-swap writes for versioned aggregates.
- Durable Effect idempotency identity + fingerprint conflict detection.
- Monotonic fencing tokens and one-active-lease protection.
- Transactional domain state + Audit + Outbox boundaries.
- Outbox claim/reclaim lifecycle for publisher crash recovery.
- Inbox duplicate suppression with hard digest-conflict detection.
- Reusable P0 persistence contract suite executed on Memory, SQLite and PostgreSQL.
- Real PostgreSQL multi-process lease contention qualification.
- Explicit SQLite schema migration qualification from V2 schema version 1 to 2.

## Persistence topology

```text
Domain / Application
        │
        ▼
Persistence Ports
        │
        ├── Repositories
        ├── AuditStore
        ├── OutboxStore
        ├── InboxStore
        └── UnitOfWork
        │
        ├───────────────┬───────────────┐
        ▼               ▼               ▼
     Memory           SQLite        PostgreSQL
```

The Domain remains infrastructure-independent.

## Core guarantees

### Optimistic concurrency

Versioned aggregates use compare-and-swap semantics. A stale writer receives
`ConcurrencyConflictError` instead of silently overwriting a newer state.

### Effect idempotency

Effect idempotency is persisted independently from transport deduplication.

```text
same idempotency key + same fingerprint
→ reuse durable Effect intent

same idempotency key + different fingerprint
→ IdempotencyConflictError
```

### Lease safety

The durable coordination model preserves:

```text
one active lease per resource
+
monotonic fencing token
+
explicit CAS
```

The protected target still needs to reject stale fencing tokens where split-brain protection is
required.

### Transactional Outbox

Domain changes and Outbox append can share one local database transaction through the Unit of Work.

External network effects remain outside long-running database transactions.

### Inbox semantics

Inbox deduplication is transport-level state:

```text
same external ID + same digest
→ no-op

same external ID + different digest
→ hard conflict
```

It is intentionally distinct from Effect idempotency.

## Migrations

A4 introduces incremental V2 schema migrations:

```text
0001_v2_core.sql
0002_v2_catalog.sql
```

SQLite migration from schema version 1 to 2 is an executable test. PostgreSQL migration application
is exercised against a real PostgreSQL service in CI.

A database restore is not treated as authorization to resume work:

```text
restore != safe resume
```

Recovery must still re-evaluate Effect truth, ownership and fencing.

## PostgreSQL qualification

The dedicated `postgres-v2` CI gate runs against PostgreSQL 16 and proves:

- common P0 repository contracts;
- stale compare-and-swap rejection;
- Effect idempotency conflicts;
- monotonic fencing;
- one-active-owner lease behavior;
- transactional UnitOfWork + Outbox;
- Inbox deduplication;
- Outbox claim recovery;
- two-process lease contention.

## Example

Run the offline SQLite example:

```bash
python examples/v2_persistence.py
```

See `docs/guides/V2_PERSISTENCE.md` for the persistence model and operational boundaries.

## Compatibility

- The V1 public runtime remains available.
- V2 Domain does not import concrete persistence adapters.
- Database SDK types remain behind adapters.
- Existing V1 PostgreSQL/state-store implementations remain separate from the V2 persistence
  contract.

## Known limitations

- SQLite remains single-host/local durability, not distributed coordination.
- Exactly-once transport delivery is not promised.
- PostgreSQL credentials, TLS, pool sizing, backups, PITR and retention remain application-owned.
- Multi-region database architecture is outside this milestone.
- External write-capable connectors are deferred to later V2 milestones.
- Persistence does not make an ambiguous Effect safe to replay.

## Qualification target

Before tagging `v2.0.0a4`, the release must pass:

```text
ruff check
ruff format --check
mypy --strict
Python 3.11 tests
Python 3.12 tests
Python 3.13 tests
coverage >= 90%
real PostgreSQL V2 contracts
multi-process PostgreSQL qualification
package build
twine check
reproducible build
fresh wheel install
A4 persistence example
SHA-256 generation
```
