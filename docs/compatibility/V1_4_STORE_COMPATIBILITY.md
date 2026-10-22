# PyAgentsKit 1.4.0 store compatibility matrix

| Capability | Memory | SQLite/filesystem | PostgreSQL | S3 | Azure Blob |
|---|---:|---:|---:|---:|---:|
| Sessions | Yes | Yes | Yes | — | — |
| Lexical memory | Yes | Yes | Yes | — | — |
| Approvals | Yes | Yes | Yes | — | — |
| Durable runs | Yes | Yes | Yes | — | — |
| Leases/fencing | Yes | Yes | Yes | — | — |
| Artifact bytes | Yes | Yes | — | Yes | Yes |
| Tenant-scoped keys | Yes | Yes | Yes | Hashed prefix | Hashed prefix |
| Optimistic transitions | Process lock | Transaction | Row lock | Conditional create | Conditional create |
| Multi-host | No | No | Yes | Yes | Yes |
| Default release test | Full | Full | Protocol double | Client double | Client double |
| CI live test | N/A | N/A | PostgreSQL 16 | Opt-in | Opt-in |

PostgreSQL state uses JSONB for validated domain documents plus indexed ownership, search, status,
session and expiry columns. S3/Azure artifacts use an immutable byte object and JSON sidecar; a
partially failed metadata write cleans up the newly written byte object.
