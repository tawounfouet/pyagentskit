# PyAgentsKit 0.9.0 — evaluations, CLI and pre-V1 hardening

Lot 11 closes the implementation roadmap before the final 1.0.0 audit.

## Added

- strict evaluation datasets, assertions, reports and regression comparison;
- advisory model-judge scores separated from release gates;
- dependency-free CLI for diagnostics, validation, offline smoke runs, eval comparison and
  checkpoint inspection;
- local runtime metrics and optional OpenTelemetry span bridge;
- deterministic offline benchmark and reference evaluation dataset;
- deprecation policy and migration checklist for V1;
- reproducible wheel/sdist verification under a fixed `SOURCE_DATE_EPOCH`.

## Compatibility and safety

Existing 0.5.0 APIs remain compatible. The CLI performs no automatic provider call, loads no
application Python code and prints no secret values. OpenTelemetry receives correlation metadata,
not event payloads. Live provider tests remain opt-in.

See `LOT_11_QUALIFICATION.md`, `AUDIT_LOT_11.md` and `CHECK_RESULTS.md` for release evidence.
