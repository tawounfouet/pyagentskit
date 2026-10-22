# Audit — PyAgentsKit 1.3.0

Audit date: 2026-09-09

## Conclusion

The implementation adds distributed ownership and a production durable-run backend without
changing the mono-agent runtime or V1 contracts. Tenant scope is part of all storage keys and SQL
predicates. Fencing tokens remain monotonic independently of active lease deletion.

## Controls reviewed

- strict immutable lease model with aware ordered timestamps;
- finite positive TTL and non-blank resource/owner validation;
- tenant-scoped acquisition, read, renewal, release and purge;
- same-owner acquisition idempotence and competing-owner rejection;
- stale revision, stale lease ID and expired lease rejection;
- SQLite `BEGIN IMMEDIATE`, WAL and persistent token counters;
- PostgreSQL database-time expiry and transactional `FOR UPDATE` locks;
- safe table-prefix validation before SQL interpolation;
- per-run lock row preventing lost first-write races;
- JSONB effect lookup constrained by tenant scope;
- frozen `RunStore` transition and checkpoint logic reused by PostgreSQL;
- optional asyncpg import and explicit application-owned pool lifecycle;
- no DSN, payload, tool argument or database exception text in telemetry;
- no automatic store retry or external-effect replay.

## Residual risks

- all contenders must honor the lease protocol;
- a lease check alone has a race with expiry, so protected writes must enforce fencing atomically;
- database availability, pool exhaustion and lock timeouts can interrupt runs;
- the PostgreSQL aggregate row grows with checkpoints and journal entries;
- session, memory, approval and binary-artifact PostgreSQL adapters are not part of 1.3.0;
- application database roles and RLS determine defense in depth beyond query scoping;
- default qualification does not connect to a real PostgreSQL server;
- migration from local stores to PostgreSQL is an operator-controlled process.

These limits are documented and do not weaken the existing local path.
