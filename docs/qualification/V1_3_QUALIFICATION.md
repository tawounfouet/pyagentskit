# PyAgentsKit 1.3.0 qualification

The stable release gate is deterministic and network-free. PostgreSQL behavior is qualified
through an asyncpg-compatible transactional pool double; an actual database test exists behind an
explicit write-acceptance gate.

## Required evidence

| Area | Qualified behavior |
|---|---|
| Lease contract | acquire, idempotent same-owner acquire, renew, release and current-owner check |
| Fencing | monotonic token across release and expiry takeover |
| Tenant isolation | identical resource/run IDs remain isolated by tenant scope |
| Contention | one winner for competing local/SQLite acquisitions |
| SQLite | transactional counter persistence across independent store instances |
| PostgreSQL leases | database time, row locks, persistent counters and safe prefixes |
| PostgreSQL runs | frozen `RunStore`, per-run serialization, JSONB and optimistic transitions |
| Durable effects | plan, start, complete, unknown and explicit reconciliation |
| Schema safety | newer schema versions rejected at initialization |
| Optional dependency | no asyncpg import or socket at module import time |
| V1 compatibility | frozen root exports, event vocabulary, schemas and provider signatures |
| Packaging | reproducible wheel/sdist plus installed-wheel offline example |

## PostgreSQL boundary

The SQL uses PostgreSQL transactions, `FOR UPDATE`, `ON CONFLICT`, `TIMESTAMPTZ`, JSONB containment
and a GIN index. Deterministic tests validate generated operations and state semantics without a
server. `tests/test_postgres_live_qualification.py` requires both a DSN and the exact
`I_ACCEPT_DATABASE_WRITES` gate; it is skipped by default and was not used to claim database-version
certification.

The embedding application must separately validate its PostgreSQL version, asyncpg version, TLS,
database role, connection limits, lock timeouts, backups and RLS policy.
