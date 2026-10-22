# PyAgentsKit 1.6.0 qualification

## Qualification matrix

| Area | Deterministic local gate | Live/CI gate |
|---|---|---|
| Admission | Capacity, duplicate ID and draining rejection | Host queue integration |
| Graceful shutdown | Active completion and non-cancelling timeout | Pod termination rehearsal |
| Readiness | State/capacity/probe failure | Application health endpoint |
| Metrics/audit | Exact counters and payload exclusion | Exporter/backend acceptance |
| OpenTelemetry | Injected tracer span lifecycle | Deployment collector/exporter |
| Process crash | Real `SIGTERM` and `SIGKILL` against SQLite | Container/runtime kill |
| Process pause | Real `SIGSTOP`, expiry and token takeover | Node/pod suspension |
| PostgreSQL | Store doubles and existing contracts | Two worker identities, durable resume |
| Load | 250 complete distributed lifecycles | Deployment-specific concurrency test |

## Required release gates

- Ruff lint and format across code, tests and documentation;
- strict mypy over every source module;
- branch-aware full suite at or above 90% coverage;
- exact 155-name root API and 28-value core event freeze;
- process crash/pause/takeover tests;
- PostgreSQL 16 service qualification in CI, opt-in locally;
- five deterministic performance benchmarks with zero network calls;
- reproducible wheel/sdist build and Twine validation;
- installed-wheel import, CLI health and offline examples;
- ZIP integrity, secret hygiene and SHA-256 manifest.

Managed PostgreSQL, Kubernetes, queue products and telemetry backends remain deployment-qualified.
The project provides ports, lifecycle semantics and deterministic evidence, not certification of a
specific cloud topology.
