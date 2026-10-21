# ADR-0019 — Thin CLI and deterministic evaluation gates

- Status: Accepted
- Date: 2026-09-08

## Decision

The CLI uses `argparse` and delegates to public Python contracts. It does not load arbitrary Python
entry points. Offline `run`, validation, comparison, diagnostics and durable-state inspection are
the supported 0.9.0 operations.

Evaluation release gates use deterministic assertions. Model judges are permitted as advisory
scores and cannot alter deterministic pass/fail. Eval cases execute sequentially in 0.9.0.

## Consequences

The base install remains small, CI behavior is reproducible, and using the CLI cannot silently
trigger a billable provider request. Rich interactive UX and parallel eval scheduling may be added
later as compatible layers.
