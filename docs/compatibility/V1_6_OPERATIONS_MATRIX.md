# PyAgentsKit 1.6.0 production operations matrix

| Capability | PyAgentsKit owns | Deployment owns |
|---|---|---|
| Admission | Per-worker finite active-run limit | Queue partition and assignment |
| Drain | Reject new runs and wait without cancellation | Signal handling and termination grace |
| Readiness | Serializable worker/capacity/probe result | HTTP endpoint and service routing |
| Lease health | Renewal/loss lifecycle facts | PostgreSQL SLO and alert routing |
| Audit | Safe event contract and local JSONL reference | Central durable backend and retention |
| Tracing | Safe span mapping | SDK, exporter, collector and sampling |
| Takeover | Fenced lease plus durable recovery plan | Replacement worker scheduling |
| Crash effects | `UNKNOWN_EFFECT` block | Business-system investigation and resolution |

## Deployment qualification levels

| Topology | Evidence in 1.6.0 | Status |
|---|---|---|
| Memory / one process | Full deterministic suite | Qualified for tests |
| SQLite / multiple processes | Real terminate, kill and suspend tests | Qualified for one host |
| PostgreSQL / multiple worker identities | Opt-in CI two-worker takeover | Qualified reference path |
| Managed PostgreSQL / Kubernetes | Runbook and manifest template | Operator qualification required |
| External queue or scheduler | No built-in adapter | Application integration required |

No matrix entry authorizes replaying an ambiguous business effect.
