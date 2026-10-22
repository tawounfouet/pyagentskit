# PyAgentsKit 2.0.0a3

## Effects & Recovery Core

PyAgentsKit `2.0.0a3` makes external side effects, ambiguous outcomes and recovery explicit V2
concepts. The release is intentionally safety-first: an uncertain external outcome blocks dangerous
automatic progress until reconciliation or manual review establishes a safe decision.

## Highlights

- Complete V2 Effect lifecycle:
  `NOT_STARTED → STARTED → SUCCEEDED | FAILED | UNKNOWN → RECONCILIATION_REQUIRED`.
- Typed idempotency keys, input fingerprints, effect kinds, risk levels, external references and
  fencing-token capture.
- `EffectExecutionGate` for durable intent and STARTED persistence before external send.
- Explicit reconciliation cases, observations, evidence, strategies and confidence.
- Provider-neutral `ReconciliationPort`; reconciliation observes external truth and never resends
  the original write.
- Pure deterministic `RecoveryPlanner` with canonical `NextAction` and `RecoveryBlocker`.
- Recovery plans snapshot lease/fencing generation and fail closed after takeover.
- Application-level audit events for reconciliation and recovery decisions.
- Executable W1-W5 crash-window scenarios.
- Native runtime restart is routed through the generic runtime recovery execution gate.

## Core invariants

```text
SUCCEEDED Effect -> never implicit replay
UNKNOWN != FAILED
missing response -> UNKNOWN / reconciliation
checkpoint != Effect truth
recovery -> revalidate ownership and security
stale lease/fencing -> discard plan and replan
manual intervention -> valid safe outcome
```

## Crash windows

| Window | Durable observation | Safe recovery |
|---|---|---|
| W1 — before durable intent | no Effect | restart pure work |
| W2 — intent persisted, before send | NOT_STARTED | execute/restart only from durable intent |
| W3 — send happened, response missing | STARTED/UNKNOWN | reconcile |
| W4 — response happened, outcome not persisted | STARTED/UNKNOWN | reconcile |
| W5 — outcome persisted before runtime progress | SUCCEEDED/FAILED | continue without replay |

## Native runtime qualification

The Native runtime remains deliberately conservative. A3 proves that Native restart is controlled by
the same `RecoveryPlan` boundary as other runtimes. It does **not** advertise
`TOOL_INTERCEPTION`, `RESUME` or `NATIVE_CHECKPOINT` merely because the underlying V1 engine
has related mechanisms.

This preserves the A2 rule:

> advertised capabilities must not exceed demonstrated V2 guarantees.

## Persistence boundary

A3 defines repository ports and CAS/version expectations needed by Effects and reconciliation.
Production V2 persistence, Unit of Work, PostgreSQL mappings and transactional constraints belong to
`2.0.0a4 — Persistence V2`.

No external I/O is placed inside a long-running database transaction by the A3 contracts.

## Compatibility

- The V1 public runtime remains available through the existing compatibility surface.
- V2 Domain never imports `compat.v1`.
- Existing A1/A2 Effect and ReconciliationCase imports remain compatible while physical ownership
  moves into the Effects bounded context.

## Qualification targets

Before release:

```text
ruff
format
mypy --strict
Python 3.11 tests
Python 3.12 tests
Python 3.13 tests
W1-W5
package build
twine check
true fresh install
pip check
release checksums
```

## Known limitations

- No production V2 PostgreSQL repository implementation in this milestone.
- No external connector write adapters are introduced.
- Remote fencing strength depends on later store/connector capabilities.
- Native effectful-tool interception is not claimed until a dedicated V2 interception contract is
  implemented and qualified.
