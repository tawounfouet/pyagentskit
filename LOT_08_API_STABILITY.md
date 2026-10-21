# Lot 08 API stability contract — PyAgentsKit 0.3.x

Effective version: `0.3.0`.

## Public modules

- `pyagentskit.sessions`
- `pyagentskit.context`
- `pyagentskit.memory`
- `pyagentskit.artifact_store`
- `pyagentskit.state`

Their declared `__all__` symbols and root-package exports are public for the `0.3.x` line. The
serialized fields of `Session`, `SessionEntry`, `MemoryRecord`, `ArtifactRecord`, `ContextBudget`,
`ContextDecision` and `ContextSelection` are additive-only within patch releases.

## Behavioral guarantees

- session appends are ordered, tenant-scoped, idempotent by key and reject key/payload reuse;
- optimistic revision conflicts fail before model execution;
- SQLite schema migrations reject databases newer than the package;
- context selection returns explicit keep/drop/summarize decisions;
- system/current messages and complete immediate tool exchanges are kept atomically;
- known context-budget violations fail before provider access;
- offline memory is lexical and never performs hidden embedding/model calls;
- artifact reads verify persisted size and SHA-256;
- missing, cross-tenant and corrupt artifacts remain distinguishable;
- state features are opt-in and do not alter a stateless `Runner`.

## Patch compatibility

`0.3.x` will not remove public symbols, serialized fields or existing method parameters, nor make
optional parameters required. Additive metadata and optional parameters are permitted. Security
fixes may reject inputs whose previous acceptance violates documented isolation or integrity
invariants.

Private helpers, SQLite table layout beyond the migration contract, token-estimation internals and
filesystem layout are not public APIs. The executable contract is
`tests/test_state_public_api.py`.
