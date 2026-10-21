# PyAgentsKit 1.5.0 qualification

## Distributed execution matrix

| Scenario | Expected result | Deterministic evidence |
|---|---|---|
| Normal completion | Token reaches tool; lease released | Memory lease + protected-store test |
| Renewal | Revision advances before TTL | Heartbeat unit path |
| Renewal budget exhausted | Active work cancelled | Typed `LeaseRenewalLimitError` |
| Expiry before effect | No plan and no tool call | Empty effect journal |
| Crash during effect | Effect becomes `UNKNOWN` | Durable journal assertion |
| Takeover | New owner receives larger token | Worker A/B integration test |
| Pause/HITL | Lease released; approval resumes under new token | Two-worker approval test |
| Split-brain | Lower token rejected atomically | Protected-store contract test |
| Unknown effect resume | New worker blocked | Call count remains exactly one |

## Release gates

- Ruff lint and format;
- strict mypy across all source modules;
- complete branch-aware suite at or above 90% coverage;
- frozen API/event/contract tests;
- deterministic distributed safety tests with no socket;
- existing PostgreSQL 16 opt-in CI qualification;
- wheel/sdist build, Twine validation and reproducible rebuild;
- installed-wheel distributed import and offline scenario;
- archive integrity, secret hygiene and SHA-256 manifest.

The release qualifies the runtime protocol and existing lease stores. Production acceptance must
still test database latency, TTL margins, process signals, clock behavior of local stores and
atomic fencing inside each real business resource.
