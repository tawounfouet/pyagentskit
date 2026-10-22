# PyAgentsKit 1.4.0 API compatibility

| Frozen surface | 1.4.0 result |
|---|---|
| Root `__all__` | Exactly 155 names; hash unchanged |
| `EventType` | Exactly 28 values |
| Core Pydantic field order | Unchanged |
| `RunContext` dataclass layout | Unchanged |
| Provider constructors | Unchanged |
| `SessionStore`, `MemoryStore`, `ApprovalStore`, `ArtifactStore`, `RunStore` | Implemented unchanged |

The additive API is deliberately submodule-scoped:

```python
from pyagentskit.postgres_state import (
    PostgresSessionStore,
    PostgresMemoryStore,
    PostgresApprovalStore,
)
from pyagentskit.blobs import BlobStore, S3ArtifactStore, AzureBlobArtifactStore
from pyagentskit.state_migration import migrate_sqlite_to_postgres
```

Existing memory, filesystem and SQLite configurations require no migration. New cloud/database
extras are optional, and importing their modules does not import an SDK or create a connection.
