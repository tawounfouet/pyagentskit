# PyAgentsKit — Production Qualification Plan

**Document :** `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Production Qualification Master Plan  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../operations/38_PYAGENTSKIT_TEST_STRATEGY.md`
- `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../operations/41_PYAGENTSKIT_DEPLOYMENT_AND_OPERATIONS.md`
- `../operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md`
- `../operations/43_PYAGENTSKIT_PERFORMANCE_AND_CAPACITY_MODEL.md`
- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`

---

# 1. Objet

Ce document définit le **plan de qualification production de PyAgentsKit V2**.

Son objectif est de répondre à une question simple :

> **Quelles preuves doivent exister avant de pouvoir affirmer que PyAgentsKit est production-ready pour exécuter des agents capables d’avoir des effets réels ?**

La qualification ne se limite pas à :

```text
tests pass
coverage high
package builds
```

Elle doit démontrer que les garanties centrales de PyAgentsKit survivent à :

```text
crashes
timeouts
partial failures
network ambiguity
worker takeover
database outages
provider failures
restore/PITR
migration
load
version skew
human approval delays
```

---

# 2. Philosophy

La doctrine générale est :

```text
Specification
      ↓
Invariant
      ↓
Test
      ↓
Failure Injection
      ↓
Operational Evidence
      ↓
Release Gate
```

> **A guarantee that has never been tested under the failure mode it is meant to survive is not yet a production guarantee.**

---

# 3. Qualification Scope

La qualification couvre :

```text
Domain
Application
Persistence
Coordination
Effects
Reconciliation
Governance
Security
Runtime Adapters
Connectors
Audit
Outbox/Inbox
Migration
Deployment
Recovery
Performance
Operations
```

---

# 4. Qualification Levels

```text
QL0 — Unit Correctness
QL1 — Contract Compliance
QL2 — Integration Correctness
QL3 — Failure Semantics
QL4 — Distributed Qualification
QL5 — Production Readiness
```

## QL0 — Unit Correctness

Prouver les invariants locaux :

```text
state transitions
fingerprints
approval scope
RecoveryPlanner decisions
Effect transitions
fencing comparisons
```

## QL1 — Contract Compliance

Prouver que chaque adapter implémente le même contrat :

```text
Repository contract tests
AgentRuntimeAdapter contract tests
Connector contract tests
ReconciliationPort contract tests
```

## QL2 — Integration Correctness

Tester avec infrastructure réelle :

```text
PostgreSQL
filesystem/object store
runtime SDK
sandbox connector
```

## QL3 — Failure Semantics

Injecter :

```text
timeout
process crash
DB interruption
network ambiguity
provider 500/429
```

## QL4 — Distributed Qualification

Prouver :

```text
lease takeover
fencing rejection
split-brain prevention
concurrent reservations
```

## QL5 — Production Readiness

Prouver :

```text
deployability
operability
recovery
performance
migration
release discipline
```

---

# 5. Qualification Environments

```text
QE-LOCAL
QE-CI
QE-INTEGRATION
QE-DISTRIBUTED
QE-PROD-LIKE
```

### QE-LOCAL

```text
Memory
SQLite
Fakes
```

### QE-CI

```text
unit
contract
static checks
package build
```

### QE-INTEGRATION

```text
real PostgreSQL
real process boundaries where relevant
```

### QE-DISTRIBUTED

```text
2+ independent worker processes
real PostgreSQL
lease/fencing
failure injection
```

### QE-PROD-LIKE

```text
production-like topology
health probes
object storage
telemetry
real runtime sandbox
real connector sandbox
```

---

# 6. Evidence Policy

Chaque qualification doit produire :

```text
test identifier
commit SHA
environment
configuration
result
logs
metrics
artifacts
timestamp
```

Le release candidate doit produire un **Qualification Evidence Pack** :

```text
qualification-report.md
test-results.xml
coverage report
performance report
migration report
failure-injection report
SBOM
checksums
release metadata
```

---

# 7. Release Gates

```text
GATE-01 Public Contracts
GATE-02 Domain Invariants
GATE-03 Runtime Adapters
GATE-04 Effect Safety
GATE-05 Recovery
GATE-06 Coordination
GATE-07 Persistence
GATE-08 Governance
GATE-09 Audit
GATE-10 Security
GATE-11 Migration
GATE-12 Operations
GATE-13 Performance
GATE-14 Documentation
```

## GATE-01 — Public Contracts

Vérifier :

```text
stable public imports
public models
errors
event envelopes
semver expectations
```

## GATE-02 — Domain Invariants

Vérifier :

```text
Run state machine
Effect state machine
Approval state machine
Lease/Fencing invariants
Conversation distinctions
```

## GATE-03 — Runtime Adapters

Chaque adapter officiel doit avoir :

```text
capability declaration
contract suite
integration tests
failure tests
known limitations
```

## GATE-04 — Effect Safety

Prouver :

```text
SUCCEEDED not replayed
UNKNOWN not converted to FAILED
idempotency conflict detected
duplicate protected Effect prevented where possible
```

## GATE-05 — Recovery

Prouver :

```text
recovery after worker crash
recovery after process replacement
recovery after runtime interruption
manual intervention when proof insufficient
```

## GATE-06 — Coordination

Prouver :

```text
lease acquisition
renewal
expiration
takeover
fencing monotonicity
stale worker rejection
```

## GATE-07 — Persistence

Prouver :

```text
transactional invariants
constraints
optimistic concurrency
unknown commit outcome handling
schema migration
```

## GATE-08 — Governance

Prouver :

```text
approval required
approval scope
expiry
revalidation
authorization separation
```

## GATE-09 — Audit

Prouver :

```text
critical actions auditable
append semantics
evidence links
no secret leakage
```

## GATE-10 — Security

Prouver :

```text
tenant isolation
least privilege
secret handling
authorization checks
adapter trust boundary
```

## GATE-11 — Migration

Prouver :

```text
V1 → V2 migration
no lost successful Effect
no fabricated Approval
no fencing regression
```

## GATE-12 — Operations

Prouver :

```text
health endpoints
graceful shutdown
worker drain
kill switch
backup/restore
runbooks
```

## GATE-13 — Performance

Prouver :

```text
baseline
safe capacity envelope
failure-under-load
lease renewal headroom
recovery storm control
```

## GATE-14 — Documentation

Prouver :

```text
architecture
migration
operations
runbooks
adapter limitations
release notes
```

---

# 8. Mandatory Crash Windows — W1 to W5

Les crash windows sont centrales :

```text
W1 — before durable intent
W2 — after durable intent, before external send
W3 — after send, before response
W4 — after response, before durable outcome
W5 — after durable outcome, before next Run progress
```

## Q-EFF-W1

Injecter crash avant persistence de l’intention.

Attendu :

```text
no external Effect
no false durable Effect
```

## Q-EFF-W2

Crash après réservation durable mais avant send.

Attendu :

```text
Effect remains safe to evaluate/retry according policy
no external duplicate
```

## Q-EFF-W3

Crash après send, avant réponse.

Attendu :

```text
UNKNOWN
no blind retry
reconciliation required
```

## Q-EFF-W4

Réponse reçue, crash avant persistence outcome.

Attendu :

```text
UNKNOWN or recoverable ambiguous state
reconciliation
no replay
```

## Q-EFF-W5

Outcome durable, crash avant progression du Run.

Attendu :

```text
Effect SUCCEEDED remains authoritative
Run resumes without repeating Effect
```

---

# 9. Effect State Qualification

États cibles :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

Scénarios obligatoires :

```text
Q-EFF-001 NOT_STARTED → STARTED durable before send
Q-EFF-002 STARTED → SUCCEEDED with evidence
Q-EFF-003 STARTED → FAILED only when failure is known
Q-EFF-004 timeout ambiguity → UNKNOWN
Q-EFF-005 UNKNOWN → SUCCEEDED after reconciliation
Q-EFF-006 UNKNOWN → FAILED after reconciliation
Q-EFF-007 unresolved ambiguity → manual/reconciliation blocker
```

---

# 10. Idempotency Qualification

Couvrir :

```text
same key + same fingerprint
same key + different fingerprint
concurrent same key
provider-native idempotency
```

### Q-IDEMP-001

Deux appels simultanés même key/fingerprint.

Attendu :

```text
one logical Effect
```

### Q-IDEMP-002

Même key, fingerprint différent.

Attendu :

```text
hard conflict
```

### Q-IDEMP-003

Retry safe après failure prouvée.

Attendu :

```text
policy-controlled retry
```

### Q-IDEMP-004

SUCCEEDED déjà présent.

Attendu :

```text
return/reuse prior result
no re-execution
```

---

# 11. Reconciliation Qualification

Chaque Connector officiel à effets critiques doit définir :

```text
lookup strategy
evidence quality
ambiguous outcomes
manual fallback
```

Scénarios :

```text
Q-REC-001 external reference known
Q-REC-002 no external reference, use business/idempotency key
Q-REC-003 contradictory external state → manual intervention
Q-REC-004 provider unavailable → remain ambiguous
Q-REC-005 eventual consistency → bounded re-check
```

---

# 12. Run State Qualification

Valider :

```text
RUNNING
WAITING
PAUSED
SUCCEEDED
FAILED
CANCELLED
```

Scénarios :

```text
Q-RUN-001 pending Approval → WAITING, non-terminal
Q-RUN-002 UNKNOWN Effect → WAITING, not FAILED
Q-RUN-003 explicit suspension → PAUSED
Q-RUN-004 runtime completed + unresolved Effect → Run not SUCCEEDED
Q-RUN-005 cancellation does not imply rollback
```

---

# 13. RecoveryPlanner Qualification

Chaque `NextAction` doit être couvert :

```text
ACQUIRE_LEASE
WAIT_FOR_APPROVAL
RECONCILE_EFFECT
RESUME_RUNTIME
RESTART_RUNTIME
COMPLETE_RUN
FAIL_RUN
MANUAL_INTERVENTION
```

Scénarios :

```text
Q-RP-001 no lease → ACQUIRE_LEASE
Q-RP-002 pending Approval → WAIT_FOR_APPROVAL
Q-RP-003 UNKNOWN Effect → RECONCILE_EFFECT
Q-RP-004 resumable runtime → RESUME_RUNTIME
Q-RP-005 safe restart only → RESTART_RUNTIME
Q-RP-006 insufficient proof → MANUAL_INTERVENTION
```

---

# 14. Lease & Fencing Qualification

Tests obligatoires :

```text
Q-LEASE-001 acquire free resource
Q-LEASE-002 concurrent conflict → one owner
Q-LEASE-003 renew
Q-LEASE-004 expiry
Q-LEASE-005 takeover
Q-LEASE-006 new fencing token > previous
Q-LEASE-007 stale worker rejected
Q-LEASE-008 concurrent takeover → one authority
Q-LEASE-009 local clock skew does not break DB-time authority
Q-LEASE-010 DB latency does not silently extend authority
```

---

# 15. Multi-Process Qualification

Minimum :

```text
2 separate OS processes
real PostgreSQL
```

Scénarios :

```text
Q-DIST-001 Worker A owns, Worker B denied
Q-DIST-002 kill A → B takeover
Q-DIST-003 SIGSTOP A → B takeover → resume A → A fenced
Q-DIST-004 concurrent Effect reservation → one valid authority
Q-DIST-005 split-brain attempt → no dual valid protected Effect
```

---

# 16. PostgreSQL Qualification

Tests :

```text
Q-PG-001 FK/unique/check constraints
Q-PG-002 Effect idempotency physically enforced
Q-PG-003 one authoritative active lease per resource
Q-PG-004 fencing monotonic under concurrency
Q-PG-005 Approval terminality under races
Q-PG-006 optimistic concurrency
Q-PG-007 transaction rollback
Q-PG-008 unknown commit outcome
Q-PG-009 primary failover
Q-PG-010 stale replica never used for safety decision
```

---

# 17. Approval Qualification

```text
Q-APR-001 valid approver + exact scope
Q-APR-002 unauthorized principal denied
Q-APR-003 expired Approval unusable
Q-APR-004 fingerprint changes → Approval no longer applies
Q-APR-005 takeover → Approval revalidated
Q-APR-006 free-text "ok" != Approval
Q-APR-007 concurrent approve/reject follows terminality rules
```

---

# 18. Authorization Qualification

```text
Q-AUTHZ-001 missing permission blocks Effect
Q-AUTHZ-002 permission revoked mid-Run blocks Effect
Q-AUTHZ-003 tenant mismatch hard deny
Q-AUTHZ-004 policy engine unavailable follows security profile
```

---

# 19. Security Qualification

```text
Q-SEC-001 no resolved secrets in durable state
Q-SEC-002 secrets/tokens redacted in logs
Q-SEC-003 cross-tenant reads blocked
Q-SEC-004 cross-tenant writes blocked
Q-SEC-005 tampered SecurityContext rejected
Q-SEC-006 stale authorization revalidated
Q-SEC-007 dependency/supply-chain scan
Q-SEC-008 admin operations authorized and audited
```

---

# 20. Runtime Adapter Qualification

Niveaux :

```text
L0 Fake
L1 Contract
L2 Integration
L3 Failure
L4 Production Qualified
```

### L1

Tester les opérations supportées :

```text
start
resume
cancel
inspect
events
checkpoint
close
```

### L2

Runtime réel.

### L3

Faults :

```text
timeout
disconnect
500
429
lost session
partial event stream
```

### L4

Production-like + limitations publiées.

Règle :

```text
declared capability
must equal
demonstrated capability
```

---

# 21. Connector Qualification

Chaque Connector critique doit passer :

```text
Q-CONN-001 read operation
Q-CONN-002 successful write
Q-CONN-003 timeout before send
Q-CONN-004 timeout after send
Q-CONN-005 429
Q-CONN-006 5xx
Q-CONN-007 credential expiry
Q-CONN-008 reconciliation confirms success
Q-CONN-009 reconciliation confirms failure
Q-CONN-010 reconciliation impossible → manual path
```

---

# 22. Coding Agent Qualification

Avant toute promesse de support officiel :

```text
Q-CODE-001 workspace creation
Q-CODE-002 file modification
Q-CODE-003 command execution
Q-CODE-004 git commit
Q-CODE-005 git push as Protected Effect
Q-CODE-006 push timeout after send → reconcile remote SHA
Q-CODE-007 Approval bound to exact SHA
Q-CODE-008 SHA changes after Approval → invalid
Q-CODE-009 worker crash → no duplicate push
Q-CODE-010 stale worker push rejected
```

---

# 23. Audit Qualification

```text
Q-AUD-001 critical action creates AuditEvent
Q-AUD-002 actor/principal exact
Q-AUD-003 Approval decision auditable
Q-AUD-004 force takeover auditable
Q-AUD-005 manual reconciliation auditable
Q-AUD-006 no secret leakage
```

---

# 24. Outbox & Inbox Qualification

## Outbox

```text
Q-OUT-001 domain commit + outbox atomic
Q-OUT-002 publisher crash after send → duplicate delivery tolerated
Q-OUT-003 poison event quarantined after bounded retries
```

## Inbox

```text
Q-IN-001 duplicate delivery → one logical application
Q-IN-002 same message id with different payload → conflict
```

---

# 25. Conversation Qualification

```text
Q-CONV-001 Session can contain multiple Conversations
Q-CONV-002 RuntimeMessage != ConversationMessage
Q-CONV-003 duplicate external message deduped
Q-CONV-004 Message is not an Approval
```

---

# 26. Artifact Qualification

```text
Q-ART-001 upload + checksum
Q-ART-002 blob success / metadata failure → orphan detected
Q-ART-003 metadata success / blob missing → detected
Q-ART-004 checksum mismatch → invalid/untrusted artifact
Q-ART-005 large artifact path is streamed
```

---

# 27. V1 → V2 Migration Qualification

Safety-critical.

```text
Q-MIG-001 preflight catches invalid source states
Q-MIG-002 every RunStatus maps deterministically
Q-MIG-003 WAITING_APPROVAL → WAITING + Approval blocker
Q-MIG-004 UNKNOWN_EFFECT → WAITING + Effect.UNKNOWN
Q-MIG-005 COMPLETED Effect → SUCCEEDED and never replayed
Q-MIG-006 CLAIMED/EXECUTED Approval states are reclassified
Q-MIG-007 fencing generation never decreases
Q-MIG-008 interrupted migration resumes idempotently
Q-MIG-009 cutover has one authoritative writer
Q-MIG-010 irreversible V2 Effect prevents unsafe rollback assumption
```

---

# 28. Restore / PITR Qualification

Cette zone est **P0**.

### Q-RESTORE-001

Restaurer DB avant un Effect déjà appliqué à l’extérieur.

Attendu :

```text
workers disabled
external reality reconciled
no replay
```

### Q-RESTORE-002

Restore ferait régresser fencing generation.

Attendu :

```text
safety gate blocks execution
```

### Q-RESTORE-003

Approval réapparaît PENDING alors que l’action externe est déjà faite.

Attendu :

```text
reconciliation before any action
```

### Q-RESTORE-004

Outbox events réapparaissent.

Attendu :

```text
deduplication prevents repeated consequence
```

### Q-RESTORE-005

Restore procedure fully documented and evidenced.

---

# 29. Operational Qualification

```text
Q-OPS-001 liveness
Q-OPS-002 readiness false on incompatible schema
Q-OPS-003 protected-effects readiness false without authority
Q-OPS-004 SIGTERM graceful drain
Q-OPS-005 SIGKILL safe takeover
Q-OPS-006 SIGSTOP zombie fencing
Q-OPS-007 rolling upgrade N/N+1
Q-OPS-008 kill switch
Q-OPS-009 worker drain
Q-OPS-010 dependency degradation modes
Q-OPS-011 fresh install smoke test
Q-OPS-012 backup/restore drill
```

---

# 30. Performance Qualification

Minimum :

```text
Q-PERF-001 single-worker baseline
Q-PERF-002 two-worker baseline
Q-PERF-003 lease renewal pressure
Q-PERF-004 Effect burst
Q-PERF-005 Approval-heavy population
Q-PERF-006 recovery storm
Q-PERF-007 DB latency injection
Q-PERF-008 Connector throttling
Q-PERF-009 4h+ soak
Q-PERF-010 no memory/FD/task leak
```

Les chiffres finaux proviennent de mesures reproductibles, jamais d’estimations seules.

---

# 31. Failure Injection Harness

Faults requis :

```text
kill process
pause process
drop network
inject latency
inject 500
inject 429
drop DB connection
delay DB
force timeout
interrupt response
```

Des fault points déterministes peuvent être introduits **uniquement pour les tests** autour des crash windows.

---

# 32. Chaos Scenarios

```text
C-01 kill worker during pure compute
C-02 kill during W2
C-03 kill during W3
C-04 pause worker beyond Lease TTL
C-05 PostgreSQL unavailable during renewal
C-06 Outbox publisher crash
C-07 Object Storage outage
C-08 Runtime 429
C-09 Connector timeout after external apply
C-10 PITR followed by attempted resume
```

Chaque chaos test exige :

```text
hypothesis
blast radius
abort condition
evidence
expected invariant
```

---

# 33. Negative Qualification

Tester ce qui **ne doit jamais être possible** :

```text
NQ-001 blind retry of UNKNOWN
NQ-002 stale fencing accepted
NQ-003 free text satisfies Approval
NQ-004 stale replica decides Approval/Lease/Effect
NQ-005 Runtime self-authorizes Protected Effect
NQ-006 Connector bypasses Application/Governance
NQ-007 privileged admin mutation without audit
NQ-008 compat.v1 bypasses V2 invariants
NQ-009 Run succeeds while blocker remains unresolved
NQ-010 restore resumes automatically without safety gate
```

---

# 34. Static & Architecture Qualification

CI bloque sur :

```text
Ruff
mypy strict
architecture/import rules
dependency rules
public API checks
```

Règles architecturales :

```text
Domain imports no Adapters
Domain imports no API
Application imports no concrete adapters
API does not bypass Application
Runtime adapters do not depend on each other
Connectors do not define Domain semantics
V2 Domain does not import compat.v1
```

---

# 35. Package Qualification

```text
Q-PKG-001 wheel builds
Q-PKG-002 sdist builds
Q-PKG-003 fresh virtualenv install
Q-PKG-004 minimal core install without provider SDKs
Q-PKG-005 extras install independently
Q-PKG-006 no undeclared dependency
Q-PKG-007 version metadata correct
Q-PKG-008 SHA256SUMS generated
Q-PKG-009 import smoke test
Q-PKG-010 reproducible packaging evidence
```

---

# 36. Compatibility Qualification

```text
Q-COMP-001 V1 public compatibility promise preserved
Q-COMP-002 deprecated APIs warn
Q-COMP-003 promised V1 behaviors remain stable
Q-COMP-004 V1 shortcuts do not leak into V2 semantics
```

---

# 37. Public API Qualification

```text
Q-API-001 stable serialization
Q-API-002 stable error taxonomy
Q-API-003 schema/version compatibility
Q-API-004 idempotent command behavior where specified
Q-API-005 cancellation semantics
Q-API-006 public import freeze
Q-API-007 no accidental internal symbols exported
```

---

# 38. Documentation Qualification

Chaque capability publique décrit :

```text
usage
guarantees
non-guarantees
failure semantics
example
```

Chaque adapter officiel décrit :

```text
capabilities
limitations
idempotency
reconciliation
credentials
qualification level
```

Chaque release fournit :

```text
release notes
migration guide
known issues
breaking changes
```

---

# 39. Qualification Matrix

| Area | Unit | Contract | Integration | Failure | Distributed | Prod-like |
|---|---:|---:|---:|---:|---:|---:|
| Domain | ✓ |  |  |  |  |  |
| Repositories | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Effects | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Recovery | ✓ |  | ✓ | ✓ | ✓ | ✓ |
| Leases | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Approval | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Runtime Adapter | ✓ | ✓ | ✓ | ✓ | optional | ✓ |
| Connector | ✓ | ✓ | ✓ | ✓ | optional | ✓ |
| Audit | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| Migration | ✓ |  | ✓ | ✓ | ✓ | ✓ |
| Operations |  |  | ✓ | ✓ | ✓ | ✓ |
| Performance |  |  | ✓ | ✓ | ✓ | ✓ |

---

# 40. Release Maturity Model

```text
EXPERIMENTAL
BETA
RC
STABLE
```

### EXPERIMENTAL

```text
domain semantics defined
unit tests
no stable API promise
```

### BETA

```text
contract tests
real PostgreSQL integration
runtime integration
Effect/Recovery semantics functional
```

### RC

```text
all P0 gates green
migration tested
operations tested
performance baseline
known issues bounded
```

### STABLE

```text
all 14 gates green
distributed qualification green
restore/PITR green
failure-under-load green
documentation complete
evidence archived
```

---

# 41. Release-by-Release Qualification

## 2.0.0a1 — Domain Foundations

Must pass :

```text
Domain state machines
core invariants
architecture dependency checks
```

## 2.0.0a2 — Runtime Abstraction

Must pass :

```text
AgentRuntimeAdapter contract
NativeRuntimeAdapter
RuntimeCapability truthfulness
```

## 2.0.0a3 — Effects & Recovery

Must pass :

```text
W1–W5
UNKNOWN
Reconciliation
RecoveryPlanner
```

## 2.0.0a4 — Persistence V2

Must pass :

```text
normalized PostgreSQL
transactional invariants
multi-process baseline
```

## 2.0.0b1 — Governance, Security & Audit

Must pass :

```text
Approval scope
Authorization
Tenant isolation
Audit
Outbox/Inbox
```

## 2.0.0b2 — External Runtimes & Connectors

Minimum :

```text
Native Runtime
one external general-purpose runtime
one coding runtime
GitHub or equivalent connector
```

## 2.0.0rc1

Must include :

```text
migration rehearsal
public API freeze
operations
performance
restore
evidence pack
```

## 2.0.0

Requires all stable exit criteria.

---

# 42. Waiver Policy

Une gate non critique peut être waived uniquement si :

```text
known limitation
documented impact
explicit owner
planned remediation
not safety-critical
```

Aucune waiver autorisée pour les protections centrales de :

```text
Effect Safety
Fencing
Tenant Isolation
Approval Integrity
Restore Safety
Migration Integrity
```

---

# 43. Flaky Test Policy

Les tests safety-critical ne peuvent pas être acceptés comme flaky.

Un test instable doit être :

```text
quarantined temporarily
root-caused
fixed
returned to blocking
```

---

# 44. Race & Repetition Qualification

Les scénarios concurrents doivent tourner de façon répétée :

```text
lease acquisition
approval terminality
idempotency uniqueness
takeover
```

Utiliser au besoin :

```text
stress loops
property-based testing
model-based testing
```

---

# 45. Coverage Policy

Coverage est une preuve secondaire.

La priorité reste :

```text
invariant coverage
failure-mode coverage
```

La branch coverage doit néanmoins rester élevée, particulièrement dans :

```text
Effects
Recovery
Governance
Coordination
```

---

# 46. External Qualification Safety

Ne pas utiliser de credentials de production pour tests destructifs.

Utiliser :

```text
sandbox providers
test repositories
non-production cloud accounts
```

Marqueurs recommandés :

```text
external
destructive
costly
```

---

# 47. Qualification Data

Maintenir des fixtures déterministes pour :

```text
UNKNOWN
expired Approval
stale Lease
idempotency conflict
migration edge states
restore edge states
```

---

# 48. Performance Report Metadata

Chaque rapport doit inclure :

```text
CPU
RAM
OS
Python
PostgreSQL version
DB size
worker count
pool size
Lease TTL
renew interval
commit SHA
```

---

# 49. Failure Report Metadata

```text
fault
fault point
expected outcome
actual outcome
recovery duration
affected IDs
```

---

# 50. Security Report Metadata

```text
principal
tenant
policy version
decision
target
```

---

# 51. Adapter Qualification Registry

Exemple :

| Adapter | L0 | L1 | L2 | L3 | L4 |
|---|---:|---:|---:|---:|---:|
| NativeRuntime | ✓ | ✓ | ✓ | ✓ | target |
| External General Runtime | ✓ | ✓ | target | target | target |
| Coding Runtime | ✓ | ✓ | target | target | target |
| GitHub Connector | ✓ | ✓ | target | target | target |

Les statuts réels doivent être alimentés exclusivement par evidence.

---

# 52. Operational Game Days

Avant stable :

```text
GD-01 Worker SIGKILL
GD-02 Worker SIGSTOP
GD-03 PostgreSQL outage
GD-04 Restore/PITR
GD-05 Connector timeout-after-send
GD-06 Kill switch
GD-07 Rolling upgrade
GD-08 recovery storm
```

Chaque Game Day capture :

```text
timeline
alerts
operator decisions
runbook used
recovery outcome
```

---

# 53. Runbook Qualification

Un runbook est qualifié si :

```text
an operator can execute it
using available tooling
and obtain the expected safe outcome
```

---

# 54. Alert Qualification

Les alertes critiques doivent réellement se déclencher pendant leurs Game Days associés.

---

# 55. Readiness Qualification

Readiness doit devenir false lorsqu’un composant ne peut plus accepter de nouveau travail en sécurité.

Exemples :

```text
schema mismatch
DB authority unavailable
worker draining
global Effect freeze
```

---

# 56. Kill Switch Qualification

Prouver :

```text
new protected Effects blocked
scope respected
safe reads remain available when designed
action audited
unfreeze authorized
```

---

# 57. Backup & Restore Qualification

Tester :

```text
backup creation
backup integrity
actual restore
restore safety gate
reconciliation
resume
```

Un backup jamais restauré n’est pas qualifié.

---

# 58. RPO / RTO

Mesurer réellement :

```text
RPO
RTO
time to safe resume
```

La dernière métrique est distincte du simple temps de restauration DB.

---

# 59. Release Decision Review

Pour RC/stable, examiner :

```text
gates
open defects
known limitations
qualification reports
security
performance
migration
operations
```

---

# 60. Release Sign-Off Roles

Recommandés :

```text
Technical Lead
Reliability/Platform Owner
Security Reviewer
Release Owner
```

Aucune personne ne doit silencieusement bypass une gate critique.

---

# 61. Defect Severity

```text
P0 — Safety / Data Integrity / Security
P1 — Major Reliability
P2 — Functional
P3 — Minor
```

P0 exemples :

```text
duplicate irreversible Effect
fencing bypass
cross-tenant leak
Approval bypass
migration loses successful Effect
unsafe restore
```

Règle :

```text
open P0 = NO RELEASE
```

---

# 62. Production Qualification Scorecard

| Gate | Stable Required | Evidence Type |
|---|---:|---|
| Public Contracts | ✓ | API freeze |
| Domain Invariants | ✓ | state-machine tests |
| Runtime Adapters | ✓ | adapter reports |
| Effect Safety | ✓ | W1–W5 |
| Recovery | ✓ | crash/takeover |
| Coordination | ✓ | multi-process |
| Persistence | ✓ | PostgreSQL integration |
| Governance | ✓ | Approval/AuthZ |
| Audit | ✓ | audit evidence |
| Security | ✓ | tenant/secret tests |
| Migration | ✓ | V1→V2 rehearsal |
| Operations | ✓ | Game Days |
| Performance | ✓ | load/soak |
| Documentation | ✓ | release docs |

---

# 63. P0 Qualification Scenarios

Les scénarios suivants sont non négociables avant `2.0.0` :

```text
P0-Q-01 W3 timeout-after-send
P0-Q-02 W4 response-before-persist crash
P0-Q-03 SIGSTOP + takeover + stale worker rejection
P0-Q-04 concurrent lease takeover
P0-Q-05 Approval scope drift
P0-Q-06 cross-tenant write attempt
P0-Q-07 unknown DB commit
P0-Q-08 PITR behind external reality
P0-Q-09 fencing regression after restore
P0-Q-10 V1 successful Effect migration
P0-Q-11 Git push UNKNOWN reconciliation
P0-Q-12 kill switch
```

---

# 64. Production Qualification Exit Criteria

PyAgentsKit V2 peut être déclaré **Production Qualified** lorsque :

1. tous les P0 invariants ont des tests exécutables ;
2. les crash windows W1–W5 sont couvertes ;
3. PostgreSQL réel est utilisé pour la qualification distribuée ;
4. au moins deux workers indépendants sont testés ;
5. un stale worker est réellement fenced après takeover ;
6. UNKNOWN est reconcilié sans retry aveugle ;
7. Approval est durable et scope-bound ;
8. Authorization et Approval sont testés séparément ;
9. runtime completion ne suffit pas à terminer un Run bloqué ;
10. Restore/PITR a été réellement exécuté ;
11. la migration V1→V2 est répétable ;
12. package build/install est reproductible ;
13. health/readiness/drain fonctionnent ;
14. kill switch est qualifié ;
15. baseline, saturation et safe capacity envelope existent ;
16. recovery storm reste bornée ;
17. Audit critique est vérifié ;
18. les runbooks critiques ont été exercés ;
19. limitations et non-guarantees sont publiées ;
20. aucun P0 ouvert n’existe.

---

# 65. Definition of Done

`../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md` est considéré mature lorsque :

1. tous les IDs `Q-*` critiques pointent vers des tests réels ;
2. les suites CI sont organisées par QL0–QL5 ;
3. les environnements `QE-*` sont reproductibles ;
4. les crash windows disposent de fault hooks fiables ;
5. les adapters officiels publient leur niveau ;
6. PostgreSQL multi-process est testé automatiquement ;
7. SIGTERM, SIGKILL et SIGSTOP sont couverts ;
8. Restore/PITR possède un scénario reproductible ;
9. V1→V2 possède un rehearsal complet ;
10. les performances sont enregistrées avec métadonnées ;
11. les Game Days P0 ont été réalisés ;
12. les release gates sont automatisées autant que possible ;
13. l’Evidence Pack est généré pour chaque RC ;
14. les règles de waiver sont appliquées ;
15. les no-waiver gates sont protégées ;
16. les runbooks sont liés aux scénarios de qualification ;
17. les alertes critiques sont testées ;
18. tenants et secrets sont testés ;
19. l’API publique est gelée avant stable ;
20. le sign-off final est archivé.

---

# 66. Résumé

La chaîne cible est :

```text
DOMAIN INVARIANTS
       │
       ▼
CONTRACT TESTS
       │
       ▼
REAL INFRASTRUCTURE
       │
       ▼
FAILURE INJECTION
       │
       ▼
MULTI-WORKER
       │
       ▼
RESTORE / MIGRATION
       │
       ▼
PERFORMANCE / SOAK
       │
       ▼
RUNBOOK GAME DAYS
       │
       ▼
RELEASE GATES
       │
       ▼
PRODUCTION QUALIFIED
```

La hiérarchie de confiance est :

```text
unit test
<
integration test
<
failure test
<
distributed test
<
production-like qualification
```

Et la règle fondamentale est :

> **PyAgentsKit V2 n’est pas production-ready lorsque tout fonctionne dans le scénario nominal ; il l’est lorsque ses garanties les plus importantes restent vraies précisément au moment où les processus meurent, les réponses disparaissent, les leases expirent, les providers deviennent ambigus et l’état interne doit être reconstruit sans inventer ce qui s’est passé dans le monde extérieur.**
