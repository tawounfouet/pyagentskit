# PyAgentsKit 1.5.0 distributed execution compatibility

| Run store | Lease store | Deployment scope | Qualified use |
|---|---|---|---|
| Memory | Memory | One process | Deterministic tests |
| SQLite | SQLite | One host | Local durable workers with process coordination |
| PostgreSQL | PostgreSQL | Multiple hosts | Production distributed durable execution |
| PostgreSQL | Memory/SQLite | Mixed scope | Not production-safe |
| Memory/SQLite | PostgreSQL | Shared owner, local journal | Not takeover-safe across hosts |

## Fencing compatibility

| Target resource | Required integration |
|---|---|
| PostgreSQL business table | Compare/update highest token in the same transaction as the write |
| Object metadata/index | Conditional transactional index write before publishing visibility |
| Remote API | API-native idempotency key plus a durable fenced gateway owned by the application |
| Non-fenceable legacy service | Treat crash result as ambiguous; never automate replay |

The runtime can stop future work after discovering lease loss, but it cannot revoke code already
executing on another machine. Only the target resource's atomic fencing rule rejects that stale
worker at the final write boundary.
