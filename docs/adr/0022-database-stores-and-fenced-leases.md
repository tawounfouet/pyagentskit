# ADR-0022 — PostgreSQL stores and fenced leases

- Status: Accepted
- Date: 2026-09-09

## Context

The V1 runtime already exposes tenant-scoped store protocols and local memory/SQLite
implementations. SQLite is not a distributed coordination service, and a worker pause can let a
lease expire while the stale worker continues running. Production deployments need transactional
state and an ownership primitive without importing scheduler or workflow-engine semantics.

## Decision

PyAgentsKit 1.3.0 adds:

- a provider-neutral `LeaseStore` port;
- immutable leases with expiry, revision and monotonically increasing fencing tokens;
- memory and SQLite reference implementations;
- an asyncpg-compatible `AsyncPostgresPool` port;
- optional PostgreSQL implementations for leases and the existing frozen `RunStore` contract;
- lazy, idempotent schema initialization with explicit startup initialization available.

Every key and every query includes `tenant_scope`. PostgreSQL uses database time for lease expiry,
row locks for existing lease records, a persistent token counter, and a per-run lock row to
serialize first-write creation. The PostgreSQL driver remains an optional extra and the pool is
owned by the embedding application.

## Fencing rule

Holding a lease alone cannot stop a paused process. A protected storage service must remember the
highest fencing token accepted for `(tenant_id, resource_id)` and reject every lower token. The
application must carry the token to the protected write. `assert_current()` is a diagnostic guard,
not a substitute for atomic fencing at that resource.

## Consequences

- The 155 V1 root exports, 28 event types and frozen provider signatures do not change.
- Existing memory, filesystem and SQLite stores remain supported.
- PyAgentsKit does not start workers, elect leaders, schedule jobs or renew leases implicitly.
- Database roles, TLS, credentials, backups, row-level security and migrations across deployments
  remain operational responsibilities.
- A real PostgreSQL qualification is explicit opt-in because it writes tables to the selected
  database; deterministic release gates use an async pool double and make no network calls.

## Rejected alternatives

- Redis-only locks without fencing tokens: insufficient against paused stale owners.
- Advisory locks bound to one long-lived connection: too driver- and lifecycle-specific.
- Replacing the V1 stores with PostgreSQL: would remove useful local implementations.
- Adding a worker scheduler: outside the PyAgentsKit agent-runtime boundary.
