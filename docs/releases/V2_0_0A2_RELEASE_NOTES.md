# PyAgentsKit 2.0.0a2

## Runtime Abstraction

This alpha release adds the first executable V2 runtime integration boundary. Runtime selection is
capability-driven and does not depend on provider or framework names.

### Included

- `AgentRuntimeAdapter` with start, resume, cancel, status, event, checkpoint and close operations.
- Runtime descriptors, opaque handles, normalized requests/events and compatibility metadata.
- Explicit `SideEffectControlLevel` (`FULL`, `BOUNDED`, `OPAQUE`) and qualification levels `L0` to
  `L4`.
- Deterministic `CapabilityNegotiator` and `InMemoryRuntimeRegistry` with explainable rejection
  reasons and no silent fallback for exact runtime or mandatory capability requests.
- Durable `RuntimeBinding` snapshots distinct from per-attempt `RuntimeInvocation` records.
- `NativeRuntimeEngine` and `NativeRuntimeAdapter` over the existing V1 `Runner`, using the same
  adapter port as future external runtimes.
- Contract tests covering native execution, event normalization, cancellation boundaries,
  capability mismatch and deterministic selection.

### Minimal Selection Example

```python
from pyagentskit.application import InMemoryRuntimeRegistry
from pyagentskit.domain import RuntimeCapability, RuntimeRequirements

registry = InMemoryRuntimeRegistry()
requirements = RuntimeRequirements(
    required_capabilities=frozenset({RuntimeCapability.START, RuntimeCapability.STATUS}),
)
selection = registry.negotiate(requirements)
```

An empty registry raises `CapabilityNegotiationError`; mandatory guarantees are never silently
downgraded.

### Compatibility

The existing V1 root API and `Runner` behavior remain unchanged. The new runtime contracts are
additive and are exposed through `pyagentskit.domain`, `pyagentskit.application` and
`pyagentskit.adapters`.

### Limitations

- The native adapter currently supports start, status, cancellation, event streaming and tool
  interception; native resume/checkpoint are not advertised until their semantics are qualified.
- V2 persistence, full recovery planning and external runtime connectors are deferred to later
  milestones.
