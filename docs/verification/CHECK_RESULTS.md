# PyAgentsKit 1.6.0 — stable release evidence

Execution date: 2026-09-11  
Execution environment: Linux, Python 3.12.14

## Full release-check

Command: `.venv/bin/python scripts/release_check.py`

| Gate | Result |
|---|---|
| Version consistency | Pass — package and metadata 1.6.0 |
| Ruff lint and format | Pass — 238 files formatted |
| Mypy strict | Pass — 54 source files |
| Byte compilation | Pass |
| Full Pytest suite | Pass — 276 passed, 12 live tests skipped |
| Branch coverage | Pass — 90.15% (minimum 90%) |
| Exact root API freeze | Pass — 155 symbols, V1 hash unchanged |
| Exact event vocabulary | Pass — 28 V1 values unchanged |
| Structured-contract/provider-signature freeze | Pass |
| Complete-response benchmark | Pass — below 5 ms mean ceiling |
| Integrated-stream benchmark | Pass — below 8 ms mean ceiling |
| One-retry benchmark | Pass — below 10 ms mean ceiling |
| Lease lifecycle benchmark | Pass — below 5 ms mean ceiling |
| Distributed operations benchmark | Pass — below 5 ms mean ceiling |
| Wheel and sdist build | Pass |
| Twine metadata | Pass |
| Required evidence and archive hygiene | Pass |
| Reproducible fixed-epoch rebuild | Pass — wheel and sdist byte-identical |
| Installed-wheel smoke test | Pass — version, CLI, `pip check` and ten examples |

The twelve skips are explicitly gated live-provider or live-PostgreSQL tests. No authenticated,
billable or database network request was made locally.

## 1.6 distributed operations qualification

- lease acquisition is explicit and single-shot;
- renewal interval and maximum renewal count are finite and validated;
- renewal loss cancels the active durable operation;
- current ownership is checked before durable effect planning and acknowledgement;
- tools receive a validated tenant/resource/owner fencing-token document;
- successful and approval-paused runs release their lease;
- takeover receives a strictly higher fencing token;
- crash-time ambiguity becomes `UNKNOWN_EFFECT` and blocks replay by the takeover worker;
- the protected-store fixture rejects a stale split-brain write atomically;
- caller context, root exports, events, provider signatures and existing store ports remain stable.
- admission, readiness and graceful drain are bounded and deterministic;
- drain timeout leaves active work running and rejects every new admission;
- operational events and traces exclude model and tool payloads;
- real subprocess tests cover `SIGTERM`, `SIGKILL`, `SIGSTOP`, expiry and takeover;
- the PostgreSQL 16 CI job includes a two-worker durable recovery scenario.

## Compatibility and qualification boundary

The local gate verifies Python 3.12; CI defines Python 3.11, 3.12 and 3.13 jobs. PostgreSQL 16 live
qualification remains an explicit CI service job and an opt-in local test. Real business stores
must implement atomic fencing; process scheduling, queue delivery and worker lifecycle remain
deployment-owned. PyPI publication remains exact-tag-gated and uses trusted publishing.
