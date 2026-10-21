# Audit — PyAgentsKit 1.1.0

Audit date: 2026-09-09

## Conclusion

The 1.1.0 change is additive and stays inside the V1 mono-agent boundary. The default execution
path is unchanged. The V1 public manifest and frozen data contracts remain intact.

## Controls reviewed

- Streaming is capability-checked before provider invocation.
- Every callback receives a deep copy, preventing mutation of the runtime event.
- Terminal response validation uses the existing `ModelResponse` contract.
- Stream truncation, explicit error and duplicate completion fail the run.
- Model-call usage and all existing run limits apply to streamed turns.
- Parallel mode is explicit, batch-wide and bounded by `max_parallel_tools`.
- Only idempotent `PURE`/`READ` declarations qualify; all other batches are sequential.
- Cancellation is not converted into a recoverable tool error.
- Results and subsequent model history preserve original tool-call order.
- Guardrails, approvals, session persistence and artifacts remain on the coordinated runtime path.

## Residual risks

- Tool risk and idempotence declarations are trusted application metadata.
- Parallel read tools may still contend for an external resource or observe different snapshots.
- A callback may add latency or fail the run; it must avoid secrets and remain non-blocking.
- Provider usage may arrive only at stream completion, so it cannot guarantee a hard pre-token cost
  cutoff.
- A provider connection can fail after partial deltas have been shown; only `RunResult` confirms
  successful completion.

These risks are documented and do not justify changing the safe defaults.

