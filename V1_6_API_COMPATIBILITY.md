# PyAgentsKit 1.6.0 API compatibility

| Frozen surface | 1.6.0 result |
|---|---|
| Root `__all__` | Exactly 155 names; hash unchanged |
| Core `EventType` | Exactly 28 values |
| Core serialized schemas | Unchanged |
| `RunContext` layout | Unchanged |
| Provider constructors | Unchanged |
| Session/memory/approval/artifact/run/lease ports | Unchanged |
| `DistributedDurableRunner` 1.5 methods | Preserved |

New contracts are additive under `pyagentskit.distributed`:

```python
from pyagentskit.distributed import (
    DistributedEventType,
    DistributedMetricsSink,
    DistributedWorkerController,
    DistributedWorkerHealth,
    JsonLinesDistributedEventSink,
    OpenTelemetryDistributedEventSink,
)
```

`DistributedDurableRunner` adds only the optional keyword `event_sinks`. Existing 1.5 construction
and execution remain valid. Operational event types are deliberately separate from the frozen core
agent `EventType` enum.
