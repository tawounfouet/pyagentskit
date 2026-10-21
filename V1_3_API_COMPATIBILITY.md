# PyAgentsKit 1.3.0 API compatibility

## V1 freeze retained

| Contract | Stable requirement | 1.3.0 result |
|---|---|---|
| Root exports | 155 names and frozen SHA-256 | Unchanged |
| `EventType` | 28 exact values | Unchanged |
| Central Pydantic layouts | Frozen field order | Unchanged |
| `RunContext` | Frozen dataclass fields | Unchanged |
| Provider constructors | Frozen parameters | Unchanged |
| OpenRouter public surface | Frozen routing/provider signatures | Unchanged |
| `RunStore` | Existing method contract | Implemented unchanged by PostgreSQL |

New symbols are intentionally imported from submodules:

```python
from pyagentskit.coordination import LeaseStore, MemoryLeaseStore, SQLiteLeaseStore
from pyagentskit.postgres import PostgresLeaseStore, PostgresRunStore
```

This avoids changing the frozen root namespace. No existing constructor gains a required
parameter, and the default dependency set remains Pydantic-only.

## Persistence compatibility

- existing memory/SQLite stores and files are unchanged;
- PostgreSQL tables use their own schema-version records;
- initialization is idempotent and rejects unknown future versions;
- the PostgreSQL run payload uses checkpoint schema migration already defined by V1 durability;
- table prefixes permit multiple isolated installations in one database.

No automated data migration from SQLite to PostgreSQL is claimed. Applications should perform an
explicit export/import with validation and a cutover plan.
