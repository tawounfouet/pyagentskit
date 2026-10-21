# Durable checkpoints and recovery — 0.5.0

Lot 10 adds process-restart recovery to the mono-agent runtime. It does not add a scheduler,
workers, a DAG engine or a PyWorkflowKit dependency.

## Components

| Component | Responsibility |
|---|---|
| `RunStore` | Persist checkpoints, effects and analytical journal entries |
| `MemoryRunStore` | Deterministic tests and process-local development |
| `SQLiteRunStore` | Local durable state with WAL and schema migration |
| `DurableRunner` | Wrap one `Runner`, checkpoint transitions and recover sessions |
| `RecoveryPlan` | Explain whether operator action is required |

Durability requires a `SessionStore` and an explicit `RunContext.session_id`. The session owns
conversation messages; the run store owns transition/effect evidence. Both must use the same tenant
scope.

```python
runner = Runner(model, tools=registry, session_store=session_store)
durable = DurableRunner(runner, SQLiteRunStore("state/runs.db"))

result = await durable.run(agent, "Apply the change", context=context)
```

## Effect safety invariant

An effect is recorded as `planned` and then atomically moved to `started` before tool code runs.
Only a normalized `ToolResult` can move it to `completed`. If execution exits while it is
`started`, the run becomes `unknown_effect`.

`DurableRunner.resume()` never guesses. The application must reconcile each unknown effect:

- `committed`: supply the result observed in the external system; recovery appends it to the
  conversation without calling the tool again;
- `not_applied`: attest that the effect did not happen; recovery performs one controlled retry
  through the normal validation and policy chain.

```python
effect = await run_store.get_effect(effect_id, tenant_id=tenant)
await run_store.resolve_effect(
    effect.effect_id,
    EffectResolution.COMMITTED,
    tenant_id=tenant,
    expected_revision=effect.revision,
    result=observed_result,
)
resumed = await durable.resume(agent, effect.run_id, tenant_id=tenant)
```

Never use `NOT_APPLIED` without authoritative evidence. Arguments matching credential patterns are
redacted before persistence and cannot be replayed; start a new run with fresh input instead.

## Checkpoints and journal

Checkpoints are immutable, contiguous and schema-versioned. They bind the run and trace IDs, agent
ID/version, session, tenant, transition and terminal result. A resume refuses a changed agent
version. `migrate_checkpoint_document()` supports the synthetic v0 fixture used to establish the
N-1 migration contract; future schemas are rejected explicitly.

`replay()` returns append-only journal metadata. It does not call a model, tool or external system.
Tool arguments and results live in protected effect records, not journal entries.

## Persistence and deployment

`SQLiteRunStore` is a single-process/local reference backend. It uses transactional aggregate
replacement and WAL, but it is not a distributed lease service. A production multi-worker adapter
must implement `RunStore` with database-level optimistic concurrency and tenant authorization.

Protect the session and run stores consistently: encryption at rest, backups, retention, access
control and DLP belong to the embedding application. `Redactor` provides defense in depth; pass
known secrets to it when constructing `DurableRunner`.

## Deliberate exclusions

- no PyWorkflowKit adapter or dependency;
- no scheduler, worker queue, distributed lease or heartbeat;
- no automatic retry of an ambiguous effect;
- no arbitrary-code checkpointing;
- no guarantee that SQLite is safe for several processes.
