# Lot 08 qualification — PyAgentsKit 0.3.0

Qualification date: 2026-09-05

| Area | Status | Evidence |
|---|---:|---|
| Memory session store | Pass | Shared store contract |
| SQLite session store | Pass | Shared contract, migration and concurrency tests |
| Append idempotency | Pass | Same key/same payload replay; changed payload conflict |
| Optimistic concurrency | Pass | Concurrent Runner single-writer test |
| Tenant isolation | Pass | Cross-tenant session/memory/artifact denial |
| Memory and SQLite lexical memory | Pass | CRUD, tags, query, retention |
| Context full/window policies | Pass | Budget and explainability tests |
| Tool-call context atomicity | Pass | Assistant call + result grouping |
| Injected summaries | Pass | Valid, blank, oversized and over-budget cases |
| External context hook | Pass | Explicit memory-source integration |
| Memory artifact store | Pass | Shared lifecycle contract |
| Filesystem artifact store | Pass | Atomic write, missing data, corruption and traversal checks |
| SHA-256 verification | Pass | Tampered bytes rejected |
| Retention and cascade | Pass | Expiry purge and configurable session deletion |
| Runtime session resume | Pass | Two-run conversation reconstruction |
| Large tool-result externalization | Pass | Artifact reference replaces oversized inline result |
| Existing runtime/providers | Pass | Complete regression suite |
| Wheel/sdist execution | Pass | Full release-check |

All tests are local and deterministic. Existing provider live tests remain opt-in and are not
required for this provider-neutral state release.
