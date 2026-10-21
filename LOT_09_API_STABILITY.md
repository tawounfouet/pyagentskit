# Lot 09 API stability contract — PyAgentsKit 0.4.x

Effective version: `0.4.0`.

## Public modules

- `pyagentskit.guardrails`
- `pyagentskit.privacy`
- `pyagentskit.approvals`

Their declared exports, root-package exports and serialized contract fields are additive-only for
the `0.4.x` line. The executable golden contract is `tests/test_guardrails_public_api.py`.

## Behavioral guarantees

- guardrails run in declared order and exceptions fail closed;
- transformations are revalidated at their runtime boundary;
- guardrail rejection reasons are not copied into run metadata or structured events;
- model egress policy is checked before provider access;
- privacy guarantees must come from adapter-owned metadata;
- approvals are tenant-scoped and bound to canonical tool name/arguments by SHA-256;
- expired, modified, stale or already-consumed approvals never authorize a tool;
- a sensitive tool cannot execute through `ToolExecutor` without verified approval bypass;
- approval resume rebuilds context from the durable session and consumes the decision once;
- existing stateless Runner and provider contracts remain unchanged.

## Patch compatibility

`0.4.x` will not remove public symbols, serialized fields, enum members or existing parameters.
Additive optional metadata and parameters are permitted. Security patches may reject previously
accepted inputs that violate documented isolation, fingerprint, expiry or fail-closed invariants.
