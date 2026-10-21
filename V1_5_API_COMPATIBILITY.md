# PyAgentsKit 1.5.0 API compatibility

| Frozen surface | 1.5.0 result |
|---|---|
| Root `__all__` | Exactly 155 names; hash unchanged |
| `EventType` | Exactly 28 values |
| Core Pydantic field order | Unchanged |
| `RunContext` dataclass layout | Unchanged |
| Provider constructors | Unchanged |
| Store protocols from 1.0–1.4 | Unchanged |

The new API is additive and submodule-scoped:

```python
from pyagentskit.distributed import (
    DistributedDurableRunner,
    DistributedExecutionPolicy,
    FencedOperationStore,
    FencingToken,
    LeaseLostError,
    LeaseRenewalLimitError,
    fencing_token_from_context,
    resource_id_for_run,
)
```

`DurableRunner` and `LeaseStore` keep their signatures and remain independently usable. Existing
local deployments need no migration. Distributed execution stores only primitive token metadata
inside the copied run context and does not change frozen serialized core schemas.
