# PyAgentsKit 0.4.0 — guardrails, privacy and Human-in-the-Loop

Release date: 2026-09-06. Baseline: `0.3.0`.

## Delivered

- five provider-neutral guardrail stages: input, model request, tool call, tool result and output;
- normalized `allow`, `transform`, `retry_with_feedback`, `require_approval`, `reject` and
  `abort` decisions;
- ordered fail-closed `GuardrailPipeline` and application-owned callable adapter;
- data classification and provider/model egress allowlists;
- explicit ZDR and training-exclusion guarantees before provider access;
- allowlisted environment `SecretProvider` and recursive credential redaction helper;
- tenant-scoped `ApprovalStore` with memory and SQLite implementations;
- argument fingerprinting, expiry, optimistic revisions and idempotent resolution;
- atomic approval claiming and single-consumption protection;
- `WAITING_APPROVAL` Runner results and persistent approval events;
- approval/rejection resume from ordered session history;
- golden `0.4.x` public API tests and offline HITL example.

## Compatibility

Every `0.3.0` state API and all six provider adapters remain compatible. Guardrails, data policies
and approval stores are opt-in. Existing stateless runs and tools that do not require approval keep
their previous behavior.

## Deliberate boundaries

- one approval-gated model response must contain exactly one tool call;
- approval claim is fail-closed: a process failure after claiming requires operator inspection;
- general run checkpoints, unknown external effects and crash replay belong to Lot 10;
- the framework provides no approval UI and sends no notification;
- encryption, access control and retention of SQLite files remain deployment responsibilities;
- provider privacy guarantees must be exposed by the configured adapter, never asserted only by a
  prompt or agent-authored metadata.

## Next milestone

Lot 10 / `0.5.0`: versioned checkpoints, durable run recovery and optional PyWorkflowKit adapter.
