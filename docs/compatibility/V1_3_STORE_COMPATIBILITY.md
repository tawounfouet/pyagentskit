# PyAgentsKit 1.3.0 store compatibility matrix

| Capability | Memory | SQLite | PostgreSQL |
|---|---:|---:|---:|
| Session store | Yes | Yes | Not added in 1.3 |
| Lexical memory store | Yes | Yes | Not added in 1.3 |
| Approval store | Yes | Yes | Not added in 1.3 |
| Artifact store | Yes | Filesystem | External object store port remains application-owned |
| Durable run store | Yes | Yes | Yes |
| Lease store | Yes | Yes | Yes |
| Tenant key in every operation | Yes | Yes | Yes |
| Multi-process coordination | No | One host/file | Yes |
| Database-time lease expiry | No | No | Yes |
| Monotonic fencing token | Yes | Yes | Yes |
| Network dependency | No | No | Optional asyncpg/PostgreSQL |

## Qualification levels

| Target | Default release suite | Live opt-in | Certification claim |
|---|---|---|---|
| Memory | Full semantic contract | Not needed | Local reference |
| SQLite | Full semantic and two-instance contention contract | Not needed | Local reference |
| asyncpg-compatible PostgreSQL port | Transactional fake-pool contract | Available | Adapter/protocol qualified |
| Concrete PostgreSQL deployment | Not contacted | Operator-provided DSN | Deployment-owned |

“Adapter/protocol qualified” does not certify a particular managed PostgreSQL product, topology or
database version. Production acceptance requires the deployment checklist in the guide.
