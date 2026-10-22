# Audit Lot 10 — durable checkpoints and recovery

Date: 2026-09-07.

## Conclusion

The Lot 10 scope is implemented without PyWorkflowKit. The core remains mono-agent and
provider-neutral. Durable behavior is opt-in through `DurableRunner`.

## Closed findings

| Risk | Control |
|---|---|
| Silent duplicate external write | planned/started ledger plus explicit unknown state |
| Lost acknowledgement | operator `COMMITTED` result, then observation without replay |
| Retry after proven non-application | revision-checked `NOT_APPLIED` transition |
| Changed code during resume | stored agent ID/version equality check |
| Cross-tenant state access | tenant-scoped keys and lookups |
| Analytical replay causing effects | journal-only `replay()` implementation |
| Credential leakage | configurable redactor before effect/checkpoint persistence |
| Schema drift | version field, v0 fixture migration and future-version rejection |

## Accepted constraints

- SQLite is a local single-process reference store, not a distributed coordination backend.
- Run and session persistence are separate stores and need coordinated operational backups.
- Redacted tool arguments cannot be replayed; the application must start a new run.
- Cumulative usage across a recovered segment is represented by checkpoints/segments; global
  accounting remains an application concern until the hardening lot.
- Abrupt power loss is covered by SQLite transactions, but no filesystem durability claim beyond
  SQLite/WAL guarantees is made.

## Explicitly absent

PyWorkflowKit integration, scheduler, distributed workers, background retries and DAG semantics.
