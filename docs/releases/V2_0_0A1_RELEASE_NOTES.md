# PyAgentsKit 2.0.0a1

## Domain Foundations

This alpha release introduces the first executable V2 boundary. The new domain package is
independent of providers, persistence, PostgreSQL, external runtimes and the V1 compatibility
surface.

### Included

- Shared Kernel value objects for typed identifiers, aggregate versions, fingerprints, external
  references and fencing tokens.
- P0 entities for runs, effects, approvals, leases, workers, sessions, conversations, runtime
  bindings, runtime invocations, artifacts, audit events and reconciliation cases.
- Explicit state transitions for Run, Effect, Approval, Lease and Worker.
- Immutable aggregate updates with monotonic versions.
- Domain architecture tests preventing imports from adapters, API and V1 compatibility layers.
- Reproducible wheel and sdist packaging checks for the alpha release.

### Compatibility

The existing V1 modules and root exports remain unchanged. V1 remains the maintenance baseline;
V2 is additive and is currently accessed through `pyagentskit.domain`.

### Not Included

Persistence V2, complete runtime adapters, external connectors, Kubernetes integration and
production qualification are deferred to later milestones.
