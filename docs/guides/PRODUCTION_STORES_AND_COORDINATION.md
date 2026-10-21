# Production stores and distributed coordination

PyAgentsKit provides PostgreSQL-backed durable runs and leases while retaining every V1 local
store. Version 1.5 adds their explicit distributed runner composition. PostgreSQL support is optional:

```bash
pip install "pyagentskit[postgres]"
```

## Choose the store by deployment shape

| Store | Scope | Concurrency | Recommended use |
|---|---|---|---|
| `MemoryLeaseStore` | One process | Async tasks | Unit tests and ephemeral local runs |
| `SQLiteLeaseStore` | One host/file | Multiple cooperating processes | Local services and development |
| `PostgresLeaseStore` | PostgreSQL cluster | Distributed workers | Production coordination |
| `MemoryRunStore` | One process | Async tasks | Tests |
| `SQLiteRunStore` | One process/host | Transactional file | Local durability |
| `PostgresRunStore` | PostgreSQL cluster | Row-serialized transitions | Production durable runs |

All keys include `tenant_id`; `None` is a distinct single-tenant scope. Multi-tenant applications
should require a non-empty tenant at their own ingress and use a database role/RLS policy as a
second enforcement layer.

## PostgreSQL setup

```python
from pyagentskit.postgres import (
    PostgresLeaseStore,
    PostgresRunStore,
    create_asyncpg_pool,
)

pool = await create_asyncpg_pool(postgres_dsn, min_size=2, max_size=20)
leases = PostgresLeaseStore(pool)
runs = PostgresRunStore(pool)

# Prefer fail-fast startup over the lazy first-operation path.
await leases.initialize()
await runs.initialize()
```

The DSN is passed to `asyncpg` and is not retained or serialized by a store. The application owns
the pool and must close it at shutdown. A custom asyncpg-compatible pool can be injected without
installing the convenience extra.

The database role needs permission to create the version, lease, token, run-lock and run tables on
first initialization. Deployments with controlled migrations may initialize once using a migration
role, then run with narrower DML permissions. The canonical-prefix DDL is available in
[`docs/sql/postgres_v1.sql`](../sql/postgres_v1.sql).

## Lease lifecycle

```python
lease = await leases.acquire(
    "run:46f...",
    owner_id=worker_instance_id,
    tenant_id=tenant_id,
    ttl_seconds=30,
)

try:
    await leases.assert_current(lease)
    lease = await leases.renew(lease, ttl_seconds=30)
finally:
    await leases.release(lease)
```

Use a unique, stable `owner_id` for one worker incarnation. Acquisition by the same owner is
idempotent while the lease is active. Renewal increments the lease revision but preserves the
fencing token. A takeover after release or expiry receives a strictly larger token.

## Why fencing is mandatory

`assert_current()` can succeed immediately before a lease expires. Therefore the protected
resource must atomically reject stale tokens:

```text
accept write only when supplied_token >= highest_token_seen
```

The comparison must be scoped by tenant and resource and executed in the same transaction as the
protected write. This is especially important for external tool effects. PyAgentsKit never retries
or replays those effects implicitly.

## Run-store guarantees

`PostgresRunStore` implements the existing V1 `RunStore` protocol:

- checkpoint sequences remain contiguous;
- effect transitions retain optimistic revisions and idempotency fingerprints;
- tenant scope is part of every primary key and lookup;
- first writes are serialized by a per-run lock row;
- aggregate payloads use JSONB plus a GIN index for effect lookup;
- schema versions newer than the installed package fail closed.

`DurableRunner` does not acquire a lease automatically and remains independently usable.
`DistributedDurableRunner` provides the opt-in composition for exclusive worker ownership,
bounded heartbeat and fencing propagation. The application must still enforce the fencing token
atomically at every protected external resource. See
[`DISTRIBUTED_DURABLE_EXECUTION.md`](DISTRIBUTED_DURABLE_EXECUTION.md).

## Live qualification

The normal release suite never opens a PostgreSQL connection. An operator can run the explicit
integration test against a disposable database:

```bash
PYAGENTSKIT_LIVE_POSTGRES=I_ACCEPT_DATABASE_WRITES \
PYAGENTSKIT_POSTGRES_DSN='postgresql://...' \
pytest -q tests/test_postgres_live_qualification.py
```

The test uses a unique table prefix and removes only those test tables. Do not target a database
unless the role is authorized to create and drop test tables.

## Operational checklist

- enforce TLS and certificate verification in the DSN;
- obtain credentials from an application secret provider;
- set database statement, lock and idle transaction timeouts;
- monitor lease conflicts, expiry and database availability;
- schedule retention for durable state according to policy;
- test backups and restore procedures;
- use RLS or separate databases where regulatory isolation requires it;
- never log DSNs, serialized run payloads, tool arguments or approval contents.
