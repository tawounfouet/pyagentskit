# Lot 10 API stability — PyAgentsKit 0.5.x

The public names documented in `docs/guides/DURABLE_CHECKPOINTS_RECOVERY.md` are supported for the
`0.5.x` line. Checkpoint/effect documents expose `schema_version=1`; additions may be backward
compatible, while field removal or semantic reinterpretation requires a migration and release note.

`RunStore` is the portability boundary. Implementations must preserve tenant scope, contiguous
checkpoints, idempotency-key conflicts, optimistic effect revisions and append-only journal order.

`DurableRunner` takes ownership of its wrapped `Runner` tool registry in order to install the
effect policy. Applications must not share that runner with non-durable concurrent execution.

Not frozen in `0.5.x`: distributed lease/heartbeat APIs, CLI checkpoint inspection, backend-specific
retention/compaction and any future PyWorkflowKit adapter.
