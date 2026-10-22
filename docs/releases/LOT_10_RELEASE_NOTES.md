# PyAgentsKit 0.5.0 — durable checkpoints and recovery

Date: 2026-09-07. Baseline: `0.4.0`.

Lot 10 adds versioned run checkpoints, an append-only analytical journal, durable tool-effect
records, explicit `unknown_effect` reconciliation and restart recovery backed by memory or SQLite.

## Public additions

- `RunStore`, `MemoryRunStore`, `SQLiteRunStore`;
- `RunCheckpoint`, `CheckpointKind`, `JournalEntry`;
- `EffectRecord`, `EffectStatus`, `EffectResolution`, `RecoveryPlan`;
- `DurableRunner`, `effect_fingerprint()`, `migrate_checkpoint_document()`;
- `RunStatus.UNKNOWN_EFFECT` and run-store exception types.

## Compatibility

Existing `Runner` behavior remains unchanged unless wrapped by `DurableRunner`. Provider adapters,
tools, sessions, context, memory, artifacts, guardrails and approvals remain source-compatible.
Durable runs require an existing session and `RunContext.session_id`.

## Safety

Ambiguous effects are never retried automatically. `COMMITTED` supplies observed external evidence;
`NOT_APPLIED` explicitly authorizes a controlled retry. Agent version mismatch, tenant mismatch,
checkpoint gaps and stale effect revisions fail closed. Known credential patterns are redacted from
durable effect/result snapshots.

## Exclusions

No PyWorkflowKit adapter, scheduler, worker queue, distributed lease or multi-process SQLite claim
is included in `0.5.0`.
