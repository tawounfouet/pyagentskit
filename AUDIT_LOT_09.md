# Lot 09 closure audit — PyAgentsKit 0.4.0

Audit date: 2026-09-06

## Verdict

**Approved for release.** The governance layer intercepts every required boundary, prevents
unverified sensitive actions and supports persistent human decisions without pretending to be a
general durable workflow engine.

## Closed findings

| ID | Severity | Finding | Resolution |
|---|---:|---|---|
| L09-01 | Critical | Approval-required tools were always unavailable. | Runner now suspends, persists and resumes after a verified decision. |
| L09-02 | Critical | A resolved approval could be replayed. | Atomic claim plus revision transition provides single consumption. |
| L09-03 | High | Semantically identical argument maps could hash differently. | Fingerprints use sorted canonical JSON. |
| L09-04 | High | Rejected decisions could be resumed repeatedly. | Approved, rejected and cancelled decisions are all claimed once. |
| L09-05 | High | Agent metadata could self-assert privacy guarantees. | Egress guarantees are read only from adapter-owned policy metadata. |
| L09-06 | Medium | Guardrail reasons could leak policy details in traces. | Runtime audit records stage/action/policy only. |
| L09-07 | Medium | Multiple gated calls complicated partial side effects. | A gated response is restricted to one tool call in `0.4.0`. |

## Accepted residual risks

- SHA-256 binds content but is not an authorization signature;
- SQLite durability is local and storage encryption remains application-owned;
- a crash after atomic claim and before result persistence requires operator reconciliation;
- external approval interfaces must authenticate actors and authorize tenant access;
- redaction patterns reduce accidental disclosure but do not replace data-loss prevention;
- end-to-end crash recovery and `unknown_effect` semantics remain Lot 10 work.

No live provider call or production credential was used during this audit.
