# PyAgentsKit 1.3.0 — production stores and distributed coordination ports

Release date: 2026-09-09

PyAgentsKit 1.3.0 is a backward-compatible post-V1 feature release. It adds transactional
PostgreSQL durable-run storage and tenant-scoped leases with fencing tokens while preserving all
memory, filesystem and SQLite implementations.

## Added

- `pyagentskit.coordination.LeaseStore` and immutable `Lease` contracts;
- `MemoryLeaseStore` and multi-process `SQLiteLeaseStore` reference implementations;
- strictly increasing fencing tokens across release and expiry takeover;
- `pyagentskit.postgres.AsyncPostgresPool`, compatible with asyncpg pools;
- optional `PostgresLeaseStore` using database time and row locking;
- optional `PostgresRunStore` implementing the frozen V1 `RunStore` protocol;
- lazy/idempotent schema initialization and explicit fail-fast `initialize()`;
- `create_asyncpg_pool()` convenience helper behind `pyagentskit[postgres]`;
- deterministic fake-pool qualification, explicit live PostgreSQL gate, offline example and
  coordination benchmark.

## Safety rules

- every lease and run query is constrained by tenant scope;
- lease counters survive release and expiry so tokens never go backward;
- PostgreSQL lease expiration uses database time to avoid worker clock disagreement;
- per-run lock rows serialize initial aggregate creation before optimistic transitions;
- schema versions newer than the package fail closed;
- table prefixes accept only bounded lowercase identifiers;
- pools and credentials remain application-owned and are never serialized;
- fencing must be enforced atomically by each protected external resource.

## Compatibility

- the V1 root package still exports exactly 155 frozen names;
- `EventType` remains the exact 28-value V1 vocabulary;
- provider constructors and serialized core layouts are unchanged;
- all new APIs live under `pyagentskit.coordination` and `pyagentskit.postgres`;
- existing local deployments require no migration and no new dependency.

## Explicit exclusions

- no scheduler, worker registry, leader-election loop or workflow engine;
- no implicit lease acquisition or renewal by `Runner`/`DurableRunner`;
- no hidden retry of database operations or external effects;
- no bundled database credentials, global pool or import-time connection;
- no claim of live PostgreSQL certification in the default offline release suite.
