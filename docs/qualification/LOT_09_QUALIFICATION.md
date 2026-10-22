# Lot 09 qualification — PyAgentsKit 0.4.0

Qualification date: 2026-09-06

| Area | Status | Evidence |
|---|---:|---|
| Five guardrail boundaries | Pass | Runtime and pipeline tests |
| Ordered transformations | Pass | Input/output transformation tests |
| Output retry | Pass | One bounded feedback retry |
| Reject/abort behavior | Pass | Provider/action blocked before side effect |
| Guardrail failure | Pass | Exception normalized, run fails closed |
| Data classification | Pass | Ordered sensitivity limit tests |
| Provider/model allowlists | Pass | Denial before model request |
| ZDR/training exclusion | Pass | Missing guarantee rejected |
| Secret lookup | Pass | Environment names explicitly allowlisted |
| Redaction | Pass | Recursive exact/pattern fixtures |
| Memory approval store | Pass | Shared lifecycle and tenant tests |
| SQLite approval store | Pass | Shared lifecycle, migration and isolation tests |
| Argument binding | Pass | Canonical SHA-256 fingerprint |
| Expiry | Pass | Expired requests cannot be resolved or claimed |
| Optimistic resolution | Pass | Revision conflicts rejected |
| Single consumption | Pass | Second claim/resume rejected |
| Approved HITL resume | Pass | Tool executes once, then model completes |
| Rejected HITL resume | Pass | Denied observation, no tool execution |
| Missing persistence | Pass | Approval-gated tool fails closed |
| Existing runtime/providers | Pass | Complete regression suite |
| Wheel/sdist execution | Pass | Full release-check |

Qualification is deterministic and network-free. The provider live tests remain explicit opt-ins;
no credential or billable request is needed to validate this provider-neutral governance release.
