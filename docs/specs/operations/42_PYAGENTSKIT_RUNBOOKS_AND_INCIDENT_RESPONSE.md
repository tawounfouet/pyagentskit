# PyAgentsKit — Runbooks & Incident Response

**Document :** `../operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Operations — Incident Response & Runbooks  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../operations/41_PYAGENTSKIT_DEPLOYMENT_AND_OPERATIONS.md`
- `../operations/43_PYAGENTSKIT_PERFORMANCE_AND_CAPACITY_MODEL.md`
- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`

---

# 1. Objet

Ce document définit les **runbooks opérationnels et procédures d’incident** de PyAgentsKit V2.

Il décrit :

- les niveaux de sévérité ;
- les rôles d’incident ;
- les signaux de détection ;
- les premières actions sûres ;
- les procédures de diagnostic ;
- les runbooks spécifiques aux principaux modes de panne ;
- les règles de recovery ;
- les conditions de kill switch ;
- les critères d’escalade ;
- la clôture et le postmortem ;
- les preuves à conserver.

Le principe directeur est :

> **Pendant un incident, l’objectif n’est pas de “faire repartir coûte que coûte” ; l’objectif est de rétablir le service sans créer une seconde panne plus dangereuse que la première.**

---

# 2. Philosophie de réponse aux incidents

Ordre de priorité :

```text
1. Stop unsafe progress
2. Preserve evidence
3. Establish authoritative state
4. Reconcile ambiguity
5. Restore safe service
6. Recover backlog
7. Investigate root cause
```

---

# 3. Invariant d’incident IR-INV-01

```text
No action may convert uncertainty into certainty without evidence.
```

Exemple :

```text
Effect.UNKNOWN
must not become
Effect.FAILED
```

simplement pour relancer le système.

---

# 4. IR-INV-02

```text
A stale worker must never be trusted because it is still alive.
```

---

# 5. IR-INV-03

```text
A restored database snapshot is not automatically safe to resume from.
```

---

# 6. IR-INV-04

```text
A human message is not a durable Approval unless recorded as such.
```

---

# 7. IR-INV-05

```text
A queue delivery is not proof of ownership.
```

---

# 8. IR-INV-06

```text
A runtime completion signal is not sufficient proof that a Run succeeded.
```

---

# 9. Severity Levels

## SEV-0 — Critical Safety Incident

Critères :

```text
possible duplicate irreversible Effect
stale worker may still act
fencing violation
cross-tenant authority leak
Approval bypass
data corruption affecting safety decisions
```

Réponse :

```text
immediate protected-effects freeze
incident commander
security/reliability escalation
```

---

# 10. SEV-1 — Major Production Incident

Exemples :

```text
PostgreSQL unavailable
large recovery storm
runtime fleet unavailable
connector outage affecting critical workloads
migration cutover failure
```

---

# 11. SEV-2 — Degraded Service

Exemples :

```text
slow lease renewals
outbox lag
approval backlog
single adapter unavailable
elevated latency
```

---

# 12. SEV-3 — Minor Operational Issue

Exemples :

```text
isolated Run stuck
single artifact mismatch
non-critical adapter warning
```

---

# 13. Incident Roles

## Incident Commander

Coordonne la réponse.

Ne doit pas nécessairement être l’expert technique principal.

## Technical Lead

Pilote le diagnostic et les actions techniques.

## Communications Lead

Communique aux parties prenantes si nécessaire.

## Scribe

Conserve la timeline et les décisions.

---

# 14. Incident Timeline

Toute action importante doit être enregistrée :

```text
timestamp
actor
action
reason
observed result
```

---

# 15. Evidence Preservation

Conserver :

```text
RunId
EffectId
ApprovalId
LeaseId
FencingToken
WorkerId
RuntimeInvocationId
external references
correlation ids
relevant logs
AuditEvents
DB state snapshots
```

---

# 16. First Response Checklist

```text
[ ] Identify affected tenant/workload
[ ] Determine safety risk
[ ] Determine whether protected Effects are still possible
[ ] Freeze if authority uncertain
[ ] Record incident start time
[ ] Preserve identifiers/evidence
[ ] Avoid blind retries
[ ] Identify current authoritative state
```

---

# 17. Kill Switch

Le kill switch permet de bloquer :

```text
new Protected Effects
```

sans nécessairement arrêter :

```text
read operations
safe computation
diagnostics
```

---

# 18. When to Trigger Kill Switch

Déclencher si :

```text
fencing integrity uncertain
Effect duplication suspected
Approval system unavailable in fail-closed profile
tenant isolation breach suspected
database authority lost
```

---

# 19. Kill Switch Levels

## KS-1 — Connector-specific

Bloquer un Connector.

## KS-2 — Effect-class-specific

Exemple :

```text
deploy
payment
git push
```

## KS-3 — Tenant-specific

Bloquer Protected Effects pour un tenant.

## KS-4 — Global

Bloquer tous les Protected Effects.

---

# 20. Runbook RB-001 — PostgreSQL Unavailable

## Symptoms

```text
repository errors
lease renew failures
readiness false
commit failures
connection pool errors
```

## Immediate action

```text
stop new protected writes
preserve worker processes
do not infer transaction outcome
```

---

# 21. RB-001 — Diagnostic

Vérifier :

```text
DB reachability
primary role
connection pool
DNS
network
disk
replication/failover state
```

---

# 22. RB-001 — Safety Rule

Si DB authority n’est plus accessible :

```text
protected Effects must stop
```

car PyAgentsKit ne peut plus prouver :

```text
ownership
Effect state
Approval state
```

---

# 23. RB-001 — Recovery

Après retour DB :

```text
1. verify primary
2. verify schema version
3. verify migration state
4. inspect uncertain commits
5. inspect expired leases
6. identify STARTED/UNKNOWN Effects
7. restart recovery gradually
```

---

# 24. RB-001 — Do Not

Ne pas :

```text
restart all workers at full concurrency immediately
```

---

# 25. Runbook RB-002 — Lease Renewal Failures

## Symptoms

```text
lease_renew_failures_total increasing
renew latency near TTL
workers reporting ownership loss
```

## Immediate action

```text
stop new Protected Effects on affected worker
```

---

# 26. RB-002 — Diagnostic

Vérifier :

```text
DB latency
worker pause
GC pause
network
clock assumptions
TTL configuration
pool starvation
```

---

# 27. RB-002 — Recovery

Si lease expiré :

```text
do not renew stale lease
perform takeover through normal acquisition path
issue higher FencingToken
```

---

# 28. Runbook RB-003 — Stale / Zombie Worker

## Symptoms

```text
old worker still running after takeover
stale fencing rejects
duplicate progress attempts
```

## Immediate action

```text
identify current authoritative lease
confirm highest fencing generation
```

---

# 29. RB-003 — Expected Behavior

Un zombie worker peut rester vivant.

Il doit être incapable de créer un nouveau Protected Effect valide.

---

# 30. RB-003 — Actions

```text
1. keep higher-generation worker authoritative
2. terminate stale worker when safe
3. inspect attempted stale operations
4. verify connector/store rejected stale token
5. audit event
```

---

# 31. Runbook RB-004 — Split-Brain Suspected

## Definition

Deux workers pensent posséder la même ressource.

## Severity

```text
SEV-0
```

---

# 32. RB-004 — Immediate Action

```text
global or scoped Protected Effects freeze
```

---

# 33. RB-004 — Diagnostic

Collecter :

```text
lease rows
lease_resource row
fencing tokens
worker logs
DB timestamps
external operations
```

---

# 34. RB-004 — Decision

Seul :

```text
highest valid fencing generation
```

peut être considéré candidat à l’autorité.

---

# 35. RB-004 — External Reconciliation

Pour chaque Protected Effect pendant la fenêtre :

```text
verify external reality
```

---

# 36. Runbook RB-005 — Effect UNKNOWN

## Symptoms

```text
external timeout
connection reset
worker crash after send
missing provider response
```

---

# 37. RB-005 — Immediate Action

```text
do not retry
```

---

# 38. RB-005 — Diagnostic

Identifier :

```text
EffectId
idempotency key
fingerprint
provider
external reference if any
send evidence
```

---

# 39. RB-005 — Reconciliation

Appeler :

```text
ReconciliationPort
```

si disponible.

---

# 40. RB-005 — Possible outcomes

```text
CONFIRMED_SUCCESS
CONFIRMED_FAILURE
STILL_UNKNOWN
NOT_FOUND
MANUAL_REQUIRED
```

---

# 41. RB-005 — Success

Si success confirmé :

```text
mark SUCCEEDED
do not replay
resume Run
```

---

# 42. RB-005 — Failure

Si failure confirmé :

```text
mark FAILED
evaluate retry policy
```

---

# 43. RB-005 — Still Unknown

```text
keep Run WAITING
manual intervention if required
```

---

# 44. Runbook RB-006 — Suspected Duplicate Effect

## Severity

```text
SEV-0 or SEV-1
```

selon impact.

---

# 45. RB-006 — Immediate Action

```text
freeze same Effect class / connector
```

---

# 46. RB-006 — Investigate

Comparer :

```text
idempotency keys
fingerprints
external references
provider records
audit
worker ownership
```

---

# 47. RB-006 — Do Not

Ne pas lancer de compensation avant d’avoir déterminé :

```text
what actually happened
```

---

# 48. Runbook RB-007 — Approval Stuck

## Symptoms

```text
Run WAITING too long
Approval remains PENDING
notification failed
```

---

# 49. RB-007 — Diagnostic

Vérifier :

```text
Approval exists
scope correct
expiry
notification channel
authorized approvers
```

---

# 50. RB-007 — Safe Recovery

Réémettre une notification est possible.

Ne pas recréer l’Approval si elle existe déjà.

---

# 51. Runbook RB-008 — Approval Store Unavailable

## High Assurance profile

```text
fail closed
```

---

# 52. RB-008 — Behavior

Protected Effects nécessitant Approval restent :

```text
blocked
```

---

# 53. Runbook RB-009 — Approval Scope Drift

## Symptoms

Action modifiée après Approval.

Exemple :

```text
different commit SHA
different deployment target
different payload
```

---

# 54. RB-009 — Response

```text
invalidate applicability
request new Approval
```

---

# 55. Runbook RB-010 — Unauthorized Approval Attempt

## Severity

```text
SEV-1 security
```

ou SEV-0 si action a été exécutée.

---

# 56. RB-010 — Response

```text
deny
audit
inspect principal
inspect policy
review affected Runs
```

---

# 57. Runbook RB-011 — Runtime Unavailable

## Symptoms

```text
runtime.start/resume fails
runtime provider outage
```

---

# 58. RB-011 — Classification

Distinguer :

```text
not started
started but unknown
runtime session lost
provider temporarily unavailable
```

---

# 59. RB-011 — Recovery

Utiliser :

```text
RuntimeCapability
RuntimeHandle
inspect()
RecoveryPlanner
```

---

# 60. RB-011 — Do Not

Ne pas redémarrer un runtime si cela peut recréer des Effects déjà exécutés sans passer par Effect state.

---

# 61. Runbook RB-012 — Runtime Reports Completed but Run Cannot Complete

## Causes

```text
UNKNOWN Effect
pending Approval
missing audit requirement
unfinished artifact registration
```

---

# 62. RB-012 — Action

```text
keep Run non-terminal
resolve blocker
```

---

# 63. Runbook RB-013 — Connector Unavailable

## Symptoms

```text
timeouts
5xx
connection errors
```

---

# 64. RB-013 — Action

Si request non envoyée avec certitude :

```text
Effect remains NOT_STARTED
```

Si envoi ambigu :

```text
UNKNOWN
```

---

# 65. Runbook RB-014 — Connector Rate Limited

## Symptoms

```text
429
quota exceeded
```

---

# 66. RB-014 — Action

```text
backoff
jitter
respect provider retry-after
bound retries
```

---

# 67. RB-014 — Safety

Ne pas confondre rate limiting avec Effect failure définitive.

---

# 68. Runbook RB-015 — Outbox Lag

## Symptoms

```text
outbox_pending rising
oldest event age above SLO
```

---

# 69. RB-015 — Diagnostic

```text
publisher health
broker health
DB claim contention
poison event
```

---

# 70. RB-015 — Safety

Le domaine peut être commit même si publication est retardée.

---

# 71. Runbook RB-016 — Inbox Duplicate Surge

## Symptoms

```text
high duplicate rate
```

---

# 72. RB-016 — Diagnostic

```text
broker redelivery
ack failures
producer retries
external webhook behavior
```

---

# 73. RB-016 — Expected

Inbox doit dédupliquer sans répéter le command logique.

---

# 74. Runbook RB-017 — Audit Store Unavailable

## Standard profile

Selon policy :

```text
buffer / degrade / alert
```

---

# 75. RB-017 — High Assurance profile

Pour actions exigeant audit durable :

```text
fail closed
```

---

# 76. Runbook RB-018 — Artifact Upload Failure

## Cases

```text
blob failed before metadata
blob succeeded metadata failed
metadata succeeded blob missing
```

---

# 77. RB-018 — Response

Créer/rechercher :

```text
orphan blob
orphan metadata
```

et réconcilier.

---

# 78. Runbook RB-019 — Artifact Checksum Mismatch

## Severity

SEV-1 si artifact utilisé pour décision critique.

---

# 79. RB-019 — Action

```text
mark artifact invalid/untrusted
stop dependent protected actions
preserve original blob
investigate corruption
```

---

# 80. Runbook RB-020 — Conversation / Message Duplication

## Symptoms

Duplicate webhook/message.

## Response

Utiliser :

```text
dedup key
Inbox
conversation sequence
```

---

# 81. Runbook RB-021 — Worker Crash

## Immediate

Pas d’action manuelle immédiate si architecture fonctionne.

Attendre :

```text
lease expiry
takeover
RecoveryPlanner
```

---

# 82. RB-021 — Escalate if

```text
recovery backlog grows
takeover fails
Effect UNKNOWN increases
```

---

# 83. Runbook RB-022 — Worker SIGSTOP / Long Pause

C’est le scénario classique de worker zombie potentiel.

---

# 84. RB-022 — Response

Après TTL :

```text
other worker may takeover
old worker becomes stale
```

À reprise de l’ancien process :

```text
fencing must block protected writes
```

---

# 85. Runbook RB-023 — Worker Drain Fails

Graceful drain peut échouer.

---

# 86. RB-023 — Safety

Ne pas attendre indéfiniment.

Après timeout opérationnel :

```text
terminate
let lease expiry/takeover handle recovery
```

---

# 87. Runbook RB-024 — High Recovery Backlog

## Symptoms

```text
recoverable_runs_pending rising
recovery lag rising
```

---

# 88. RB-024 — Response

```text
increase bounded recovery workers
throttle normal admissions
prioritize safety-critical recovery
avoid all-at-once storm
```

---

# 89. Runbook RB-025 — DB Connection Pool Saturation

## Symptoms

```text
pool wait
timeouts
high active connections
```

---

# 90. RB-025 — Response

Avant d’augmenter le pool :

```text
inspect slow queries
transaction duration
N+1
worker concurrency
```

---

# 91. Runbook RB-026 — Slow Queries

Utiliser :

```text
EXPLAIN ANALYZE
lock inspection
index review
```

---

# 92. Runbook RB-027 — Lease Renewal p99 Approaches TTL

## Severity

```text
SEV-1
```

car safety headroom disparaît.

---

# 93. RB-027 — Response

```text
reduce admissions
inspect DB latency
temporarily increase TTL only with review
```

---

# 94. Runbook RB-028 — Out-of-Memory Worker

## Action

```text
terminate/restart process
do not trust in-memory state
recover from durable state
```

---

# 95. RB-028 — Investigation

```text
active Runs
large payloads
runtime buffers
artifact loads
task leaks
```

---

# 96. Runbook RB-029 — File Descriptor Exhaustion

## Causes

```text
stream leaks
HTTP connection leak
subprocess leak
```

---

# 97. RB-029 — Response

```text
drain affected worker
restart after evidence
fix leak
```

---

# 98. Runbook RB-030 — Provider Credential Failure

## Symptoms

```text
401
403
token expired
secret resolution error
```

---

# 99. RB-030 — Response

```text
do not retry aggressively
verify SecretReference
rotate/reload credentials
audit security-sensitive changes
```

---

# 100. Runbook RB-031 — Suspected Secret Exposure

## Severity

```text
SEV-0 security
```

---

# 101. RB-031 — Immediate

```text
revoke/rotate secret
freeze affected connector if necessary
preserve evidence
review logs/artifacts
```

---

# 102. Runbook RB-032 — Cross-Tenant Access Suspected

## Severity

```text
SEV-0
```

---

# 103. RB-032 — Immediate

```text
freeze affected surface
stop impacted workers if needed
preserve DB/audit evidence
```

---

# 104. RB-032 — Investigation

```text
SecurityContext
TenantId
repository filters
RLS if enabled
API authorization
logs
```

---

# 105. Runbook RB-033 — Migration Preflight Fails

## Action

```text
do not cut over
```

---

# 106. RB-033 — Typical blockers

```text
duplicate idempotency keys
invalid fencing history
orphan critical references
corrupt Effect state
```

---

# 107. Runbook RB-034 — Migration Fails Mid-Batch

## Response

```text
stop
inspect last migration checkpoint
verify idempotency
resume from durable cursor
```

---

# 108. Runbook RB-035 — Migration Cutover Failure

## Severity

```text
SEV-1 / SEV-0 depending writes
```

---

# 109. RB-035 — Decision Point

Déterminer :

```text
did V2 produce any irreversible external Effect?
```

---

# 110. RB-035 — If no irreversible V2 Effect

Rollback may be possible.

---

# 111. RB-035 — If V2 produced irreversible Effect

Prefer :

```text
forward-fix
```

after reconciliation.

---

# 112. Runbook RB-036 — Restore / PITR Performed

## Mandatory

```text
do not resume workers immediately
```

---

# 113. RB-036 — Safety Gate

```text
1. verify schema
2. verify fencing epochs
3. inspect Effects since restore point
4. reconcile external reality
5. inspect approvals
6. only then re-enable workers
```

---

# 114. Runbook RB-037 — Fencing Token Regression Suspected

## Severity

```text
SEV-0
```

---

# 115. RB-037 — Immediate

```text
global Protected Effects freeze
```

---

# 116. RB-037 — Investigation

```text
max historical token
lease_resources
restored DB point
migration history
manual edits
```

---

# 117. Runbook RB-038 — Unknown Commit Outcome

## Symptom

DB connection lost during commit.

---

# 118. RB-038 — Rule

```text
connection loss != rollback
```

---

# 119. RB-038 — Response

```text
reconnect
read by durable identity/idempotency key
determine whether commit exists
```

---

# 120. Runbook RB-039 — Schema Mismatch

## Symptoms

```text
worker readiness false
missing column
migration head mismatch
```

---

# 121. RB-039 — Response

```text
do not force worker ready
align schema/code versions
```

---

# 122. Runbook RB-040 — Runtime Capability Mismatch

## Example

Adapter announces RESUME but runtime cannot safely resume.

---

# 123. RB-040 — Response

```text
disable capability
fail safely
review adapter qualification
```

---

# 124. Runbook RB-041 — Adapter Regression after Provider Update

## Response

```text
pin known-good version
disable affected feature
run contract/integration suite
```

---

# 125. Runbook RB-042 — Provider Retry Behavior Changed

## Risk

Hidden retries may duplicate Effects.

---

# 126. RB-042 — Response

```text
freeze relevant writes
inspect SDK release behavior
verify idempotency
update adapter semantics
```

---

# 127. Runbook RB-043 — Git Push UNKNOWN

## Scenario

Coding agent invokes push and connection fails.

---

# 128. RB-043 — Reconciliation

Inspect :

```text
remote ref
expected commit SHA
branch state
```

---

# 129. RB-043 — Outcome

If remote ref points to expected SHA :

```text
Effect SUCCEEDED
```

Else if unchanged :

```text
failure/not applied
```

Else :

```text
manual intervention
```

---

# 130. Runbook RB-044 — PR Creation UNKNOWN

Inspect provider using :

```text
idempotency metadata if available
head SHA
base branch
title/body fingerprint
```

---

# 131. Runbook RB-045 — Deploy UNKNOWN

Inspect deployment provider.

Do not trigger second deploy until state known.

---

# 132. Runbook RB-046 — Terraform Apply UNKNOWN

High risk.

```text
SEV-1
```

or SEV-0 depending environment.

---

# 133. RB-046 — Response

```text
freeze further apply
inspect state backend
inspect cloud resources
reconcile manually/provider-specifically
```

---

# 134. Runbook RB-047 — Package Publish UNKNOWN

Inspect registry for exact version/digest.

Never blindly republish same version.

---

# 135. Runbook RB-048 — Human Approved Wrong Target

If scope fingerprint differs :

```text
Approval does not apply
```

---

# 136. Runbook RB-049 — Policy Engine Unavailable

For high-risk operations :

```text
fail closed
```

For low-risk according profile :

```text
degrade if explicitly allowed
```

---

# 137. Runbook RB-050 — Identity Provider Unavailable

Existing authenticated sessions policy-dependent.

New sensitive actions should generally fail closed.

---

# 138. Incident Triage Matrix

| Symptom | Likely Severity | First Safe Action |
|---|---:|---|
| UNKNOWN Effect | SEV-1/2 | Stop retry, reconcile |
| Fencing regression | SEV-0 | Freeze Protected Effects |
| Cross-tenant access | SEV-0 | Freeze affected surface |
| DB outage | SEV-1 | Stop protected writes |
| Runtime outage | SEV-1/2 | WAIT / inspect |
| Connector 429 | SEV-2 | Backoff |
| Approval stuck | SEV-2/3 | Verify durable Approval |
| Outbox lag | SEV-2 | Inspect publisher |
| Worker crash | SEV-2 | Let takeover/recovery |
| Restore/PITR | SEV-1 | Safety gate before resume |

---

# 139. Diagnostic Order

Toujours privilégier :

```text
1. authoritative DB state
2. external system evidence
3. audit
4. runtime inspection
5. logs
6. metrics
```

Les logs seuls ne sont pas la source de vérité.

---

# 140. Run Snapshot

Pour incident sur un Run, capturer :

```text
Run
RuntimeInvocations
Effects
Approvals
Lease
Checkpoints
AuditEvents
ExternalReferences
```

---

# 141. Effect Snapshot

```text
EffectId
status
idempotency key
fingerprint
started_at
outcome
external reference
ownership token
```

---

# 142. Lease Snapshot

```text
resource_id
lease_id
owner_id
fencing_token
acquired_at
expires_at
DB now()
```

---

# 143. Approval Snapshot

```text
approval_id
status
scope
fingerprint
principal
expires_at
policy version
```

---

# 144. Runtime Snapshot

```text
RuntimeDescriptor
RuntimeHandle
capabilities
inspect result
last RuntimeEvent
```

---

# 145. Communication Guidelines

Pendant incident :

```text
facts
impact
current mitigation
next decision point
```

Éviter spéculation.

---

# 146. Incident Update Template

```text
Incident:
Severity:
Start time:
Affected scope:
User impact:
Safety impact:
Current mitigation:
Known facts:
Unknowns:
Next action:
```

---

# 147. Escalation Criteria

Escalade immédiate si :

```text
possible irreversible duplicate
security authority compromise
cross-tenant issue
fencing integrity issue
data corruption
restore affecting external reality
```

---

# 148. Escalation — External Provider

Escalader provider si :

```text
reconciliation endpoint inconsistent
provider returns contradictory status
idempotency guarantee appears broken
```

---

# 149. Incident Command Rule

Une seule personne coordonne les décisions d’incident.

---

# 150. Change Freeze During Incident

Éviter déploiements non liés.

---

# 151. Emergency Change

Possible si :

```text
necessary to restore safety
```

mais doit être :

```text
reviewed
audited
documented
```

---

# 152. Manual Database Changes

Fortement déconseillées.

---

# 153. If Manual DB Change Is Unavoidable

Exiger :

```text
incident commander approval
two-person review
backup/snapshot
exact SQL captured
post-change verification
audit entry
```

---

# 154. Never Manually Decrease Fencing Token

Interdit.

---

# 155. Never Force Effect SUCCESS Without Evidence

Interdit.

---

# 156. Never Delete UNKNOWN to Unblock Run

Interdit.

---

# 157. Never Forge Approval

Interdit.

---

# 158. Never Reassign Tenant IDs Casually

Interdit.

---

# 159. Recovery Restart Strategy

Après incident :

```text
small batch
observe
increase gradually
```

---

# 160. Recovery Throttling

Priorités :

```text
critical unresolved Effects
ownership recovery
interactive Runs
background Runs
```

---

# 161. Recovery Storm Guard

Ne pas remettre toute la flotte à pleine concurrence.

---

# 162. Post-Incident Verification

Après rétablissement :

```text
Effect UNKNOWN backlog
lease conflicts
pending approvals
outbox lag
audit continuity
readiness
```

---

# 163. Incident Closure Criteria

Fermer seulement si :

```text
service stable
safety verified
backlog under control
no unresolved SEV-0 ambiguity
follow-up owners assigned
```

---

# 164. Postmortem Requirement

Obligatoire pour :

```text
SEV-0
SEV-1
repeated SEV-2
```

---

# 165. Postmortem Structure

```text
Summary
Impact
Timeline
Detection
Root cause
Contributing factors
What went well
What failed
Safety assessment
Corrective actions
Preventive actions
```

---

# 166. Blameless but Precise

Le postmortem cherche :

```text
system causes
```

sans diluer la responsabilité des décisions techniques.

---

# 167. Corrective Action Types

```text
code
test
monitoring
runbook
architecture
security
capacity
documentation
```

---

# 168. Action Priority

```text
P0 safety
P1 recurrence prevention
P2 operability
P3 convenience
```

---

# 169. Incident-to-Test Rule

Tout incident important doit produire au moins un test ou qualification supplémentaire lorsque possible.

---

# 170. Example

Incident :

```text
Effect duplicated after timeout
```

Action :

```text
add W3 failure test
add reconciliation integration test
```

---

# 171. Incident-to-ADR Rule

Si incident révèle une ambiguïté de design :

```text
create/update ADR
```

---

# 172. Incident-to-Runbook Rule

Si opérateur a dû improviser :

```text
update runbook
```

---

# 173. Incident-to-Metric Rule

Si détection était tardive :

```text
add metric/alert
```

---

# 174. Alert Design

Une alerte doit indiquer :

```text
what is wrong
why it matters
first runbook link
```

---

# 175. Avoid Alert Fatigue

Pas d’alerte pour chaque warning individuel.

---

# 176. Critical Alerts

```text
fencing regression
duplicate Effect detected
UNKNOWN backlog spike
lease renewal near expiry
cross-tenant violation
audit loss in high assurance
```

---

# 177. Warning Alerts

```text
outbox lag
connector throttling
approval backlog
slow queries
```

---

# 178. Health Endpoints

## Liveness

Process alive.

## Readiness

Capable d’accepter du travail de façon sûre.

---

# 179. Readiness False Conditions

Exemples :

```text
DB schema incompatible
PostgreSQL unavailable
migration not complete
global Effect freeze
critical dependency unavailable
```

---

# 180. Degraded Mode

Readiness peut rester true pour :

```text
read-only
non-protected operations
```

si routing supporte plusieurs readiness classes.

---

# 181. Protected Effect Readiness

Un endpoint séparé peut exposer :

```text
protected_effects_ready
```

---

# 182. Operational State

Worker states candidats :

```text
STARTING
READY
DRAINING
DEGRADED
STOPPING
STOPPED
```

---

# 183. Incident Runbook — High CPU

Vérifier :

```text
busy loop
recovery storm
serialization
runtime adapter
subprocess
```

---

# 184. High CPU Response

```text
reduce admissions
identify worker
drain if safe
profile
```

---

# 185. Incident Runbook — High Memory

Déjà RB-028, mais surveiller :

```text
conversation payload
artifact buffering
runtime event buffering
```

---

# 186. Incident Runbook — High Disk

Particulièrement coding workers.

```text
workspace cleanup
artifact spill
logs
temporary files
```

---

# 187. Incident Runbook — Object Storage Unavailable

New large Artifact writes may fail.

Protected action depending on artifact integrity must wait.

---

# 188. Incident Runbook — Observability Backend Unavailable

Core execution may continue if Audit remains healthy.

---

# 189. Incident Runbook — Broker Unavailable

Outbox accumulates.

Do not duplicate integration events manually.

---

# 190. Broker Recovery

Resume publisher gradually.

---

# 191. Incident Runbook — Clock Skew

Workers should not use local clock as Lease authority.

If DB time healthy, coordination remains authoritative.

---

# 192. Incident Runbook — Database Time Anomaly

SEV-0/1 depending impact on lease authority.

Freeze distributed Protected Effects until resolved.

---

# 193. Incident Runbook — Corrupt Checkpoint

Do not trust checkpoint.

Use authoritative Effect/Approval state and alternate recovery path.

---

# 194. Incident Runbook — Missing RuntimeHandle

RecoveryPlanner may choose:

```text
restart runtime
manual intervention
```

depending on guarantees.

---

# 195. Incident Runbook — Runtime State Contradicts Durable State

Durable authority wins for PyAgentsKit-owned semantics.

Provider-specific state may trigger reconciliation.

---

# 196. Incident Runbook — Audit/Event Ordering Gap

Audit timeline gap does not necessarily mean domain loss.

Check authoritative entities.

---

# 197. Incident Runbook — Poison Outbox Event

Quarantine after bounded retries.

Do not block entire publisher indefinitely.

---

# 198. Incident Runbook — Poison Inbox Event

Mark failure/quarantine according policy.

Preserve raw envelope/evidence.

---

# 199. Incident Runbook — Reconciliation Provider Unavailable

Keep Effect ambiguous.

Do not downgrade UNKNOWN.

---

# 200. Incident Runbook — Too Many Manual Intervention Cases

Likely systemic adapter/reconciliation weakness.

Escalate architecture review.

---

# 201. Incident Runbook — Capacity Saturation

Use metrics from document 43.

Actions :

```text
reduce admissions
protect lease renewals
protect recovery capacity
throttle background workloads
```

---

# 202. Capacity Incident Priority

Reserve resources for :

```text
lease renewal
Effect outcome persistence
recovery
```

before ordinary new Runs.

---

# 203. Incident Runbook — Tenant Noisy Neighbor

Apply :

```text
tenant concurrency quota
rate limit
priority adjustment
```

without affecting others.

---

# 204. Incident Runbook — Provider Cost Spike

Not necessarily service incident unless budget policy breached.

Can trigger :

```text
admission throttle
model policy
```

---

# 205. Incident Runbook — Security Policy Misconfiguration

If it broadens access unexpectedly :

```text
SEV-0/1
```

Fail closed where possible.

---

# 206. Incident Runbook — Permission Revoked Mid-Run

Revalidate before Protected Effect.

Do not rely on permission captured at Run start.

---

# 207. Incident Runbook — Approval Principal Disabled

Previously approved action may require revalidation depending policy.

---

# 208. Incident Runbook — Connector External Object Deleted

Reconciliation returns :

```text
NOT_FOUND
```

Interpret according Effect semantics, not automatically FAILED.

---

# 209. Incident Runbook — External State Changed Manually

Example :

```text
operator manually modifies PR/deployment
```

Reconciliation must record drift.

---

# 210. Drift

External state differs from expected state.

Can require manual intervention.

---

# 211. Incident Runbook — Artifact Tampering Suspected

Verify checksum/provenance.

Freeze dependent sensitive actions.

---

# 212. Incident Runbook — Plugin/Adapter Supply-Chain Incident

Disable adapter/package version.

Revert/pin.

Rotate credentials if exposure possible.

---

# 213. Incident Runbook — Dependency CVE

Classify by exploitability in PyAgentsKit deployment.

Patch supported lines according security policy.

---

# 214. Incident Runbook — Version Skew Between Workers

Workers with incompatible schemas/contracts should fail readiness.

---

# 215. Incident Runbook — Mixed V1/V2 Worker Fleet

Only supported during explicit migration phases.

Routing/source-of-truth rules must be clear.

---

# 216. Incident Runbook — V1 Worker Writes After V2 Cutover

Potential SEV-0/1.

Stop V1 writer immediately.

Reconcile all overlapping writes.

---

# 217. Incident Runbook — Migration Flag Misconfiguration

Confirm authoritative source-of-truth phase.

Avoid simultaneous authority.

---

# 218. Incident Runbook — Duplicate Idempotency Key with Different Fingerprint

This is a real conflict.

Do not overwrite.

Escalate to caller/application.

---

# 219. Incident Runbook — Orphan Lease

If lease expired, normal takeover can proceed.

If not expired but owner dead, follow force-takeover policy if supported.

---

# 220. Force Takeover

Requires :

```text
authorization
reason
audit
higher fencing token
```

---

# 221. Incident Runbook — Force Takeover Used Incorrectly

Treat as governance incident.

Inspect all Effects after takeover.

---

# 222. Operational Commands

Candidate safe admin commands :

```text
inspect run
inspect effect
inspect lease
freeze effects
unfreeze effects
drain worker
trigger reconciliation
trigger recovery
```

---

# 223. Dangerous Admin Commands

Need stronger controls :

```text
manual effect resolution
force takeover
migration cutover
state repair
```

---

# 224. Two-Person Rule

Recommended for high-risk manual operations in High Assurance profile.

---

# 225. Runbook Tooling

CLI/admin tooling should emit :

```text
structured output
dry-run
explicit target IDs
reason
```

---

# 226. No Hidden Admin Magic

Admin tools must use same Domain/Application rules where possible.

---

# 227. Incident Data Export

Possible command :

```text
pyagentskit ops incident-bundle --run <id>
```

future concept.

---

# 228. Incident Bundle

Would include :

```text
Run snapshot
Effects
Approvals
Lease
Audit refs
Runtime refs
config metadata
```

with sensitive redaction.

---

# 229. Privacy During Incident

Do not copy full prompts/messages into incident channels unless necessary.

---

# 230. Sensitive Data

Redact :

```text
secrets
tokens
personal data
raw provider credentials
```

---

# 231. Incident Retention

Incident bundles retained per security/compliance policy.

---

# 232. Audit of Incident Actions

High-risk operational actions must create AuditEvents.

---

# 233. Recovery Verification

For each recovered Run :

```text
verify next state
verify no duplicate Effect
verify ownership
```

---

# 234. Bulk Recovery Verification

Use aggregate metrics + sampling + critical-case full checks.

---

# 235. Incident Read Models

Operational UI should expose :

```text
Run timeline
Effect status
Approval status
Lease owner
Recovery blocker
```

---

# 236. Timeline Caveat

Timeline is a read model.

Authoritative entities still decide.

---

# 237. Escalation to Manual Reconciliation

Appropriate when :

```text
provider lacks lookup API
evidence contradictory
high-risk action
```

---

# 238. Manual Reconciliation Record

Record :

```text
who
what evidence
decision
reason
timestamp
```

---

# 239. Compensation

Only after Effect success confirmed and business compensation defined.

---

# 240. Compensation Is a New Effect

Important :

```text
compensation
=
new Effect
```

with its own safety semantics.

---

# 241. Never Call Compensation Rollback

Rollback applies to local transaction.

---

# 242. Incident Training

Operators should practice :

```text
UNKNOWN Effect
worker takeover
DB outage
restore gate
kill switch
```

---

# 243. Game Days

Periodic exercises with fault injection.

---

# 244. Game Day Scenario 1

```text
kill worker during external write
```

---

# 245. Game Day Scenario 2

```text
pause worker > TTL
```

---

# 246. Game Day Scenario 3

```text
DB unavailable 2 minutes
```

---

# 247. Game Day Scenario 4

```text
restore database to earlier point
```

---

# 248. Game Day Scenario 5

```text
provider returns timeout after commit
```

---

# 249. Qualification Link

Each runbook should map to at least one qualification scenario where possible.

---

# 250. Runbook Ownership

Each runbook should have :

```text
owner
last reviewed
last exercised
```

---

# 251. Runbook Review Cadence

At least :

```text
each major release
after relevant incident
after major architecture change
```

---

# 252. Runbook Staleness

A stale runbook is dangerous.

---

# 253. Runbook Versioning

Version with code/docs release.

---

# 254. Environment Differences

Document deviations for :

```text
dev
staging
prod
high-assurance
```

---

# 255. High Assurance Overrides

May require :

```text
more fail-closed behavior
two-person repair
mandatory audit
lower automation in ambiguity
```

---

# 256. Standard Profile

May allow graceful degradation for non-critical capabilities.

---

# 257. Local Profile

Some runbooks not applicable.

But semantics remain educational.

---

# 258. Incident Metrics

Track :

```text
MTTD
MTTA
MTTR
UNKNOWN resolution time
recovery backlog time
duplicate-effect incidents
```

---

# 259. MTTD

Mean Time To Detect.

---

# 260. MTTA

Mean Time To Acknowledge.

---

# 261. MTTR

Mean Time To Restore/Resolve.

---

# 262. Safety Metric

Number of incidents where unsafe action occurred despite controls.

Target :

```text
0
```

---

# 263. Near Miss

Track situations where controls blocked a potentially unsafe action.

These are valuable signals.

---

# 264. Near-Miss Examples

```text
stale fencing rejected
approval scope drift blocked
duplicate idempotency conflict rejected
```

---

# 265. Learning from Near Misses

Do not treat as noise.

They validate safeguards and reveal pressure points.

---

# 266. Incident Response Maturity

Levels :

```text
IR-L0 ad hoc
IR-L1 documented
IR-L2 monitored
IR-L3 exercised
IR-L4 production qualified
```

---

# 267. Target

Before V2 stable :

```text
critical runbooks >= IR-L3
```

Selected safety-critical runbooks :

```text
IR-L4
```

---

# 268. Critical Runbooks for L4

```text
RB-004 Split Brain
RB-005 Effect UNKNOWN
RB-006 Duplicate Effect
RB-036 Restore/PITR
RB-037 Fencing Regression
RB-043 Git Push UNKNOWN
```

---

# 269. Operational Readiness Checklist

```text
[ ] Kill switch tested
[ ] Worker drain tested
[ ] Unknown Effect reconciliation tested
[ ] Lease takeover tested
[ ] Restore gate tested
[ ] Incident bundle capability available
[ ] On-call access available
[ ] Runbooks linked from alerts
```

---

# 270. Production Launch Checklist

Before GA :

```text
[ ] SEV model agreed
[ ] incident roles documented
[ ] P0 alerts configured
[ ] runbooks reviewed
[ ] game day completed
[ ] manual repair controls reviewed
[ ] escalation contacts available
```

---

# 271. Runbook Template

```markdown
# RB-XXX — Title

Severity:
Scope:
Owner:

## Symptoms
## Safety impact
## Immediate action
## Diagnostic
## Authoritative sources
## Recovery
## Verification
## Do not
## Escalation
## Evidence to preserve
## Related metrics
## Related qualification test
```

---

# 272. Incident Decision Tree

```text
INCIDENT
   │
   ▼
Can safety authority be proven?
   │
 ┌─┴─┐
No   Yes
│     │
▼     ▼
Freeze  Is external outcome ambiguous?
Effects      │
             ├─ Yes → Reconcile
             └─ No  → Recover normally
```

---

# 273. UNKNOWN Decision Tree

```text
Effect UNKNOWN
     │
     ▼
Reconciliation available?
   ┌─┴─┐
  Yes No
   │   │
   ▼   ▼
Query  Manual Review
   │
   ▼
Confirmed?
 ┌─┼──────────┐
Yes failure  Still unknown
│    │           │
▼    ▼           ▼
Success Failure  WAITING
```

---

# 274. Lease Decision Tree

```text
Worker owns lease?
   │
 ┌─┴─┐
Yes No
│    │
▼    ▼
Validate  Stop protected progress
token      │
           ▼
       Lease expired?
        ┌──┴──┐
       Yes    No
        │      │
        ▼      ▼
    Takeover   Wait / investigate
```

---

# 275. Restore Decision Tree

```text
Restore completed
      │
      ▼
Workers OFF
      │
      ▼
Verify schema/fencing
      │
      ▼
Identify external Effects after restore point
      │
      ▼
Reconcile
      │
      ▼
Safety gate green?
    ┌─┴─┐
   Yes No
    │   │
    ▼   ▼
Resume  Manual intervention
```

---

# 276. Incident Anti-Pattern — Restart Everything

A restart can destroy evidence and cause duplicate actions.

---

# 277. Anti-Pattern — Retry Everything

Dangerous for external Effects.

---

# 278. Anti-Pattern — Trust Latest Log

Logs are not authoritative state.

---

# 279. Anti-Pattern — Force Success

Interdit without evidence.

---

# 280. Anti-Pattern — Ignore Fencing Rejects

A fencing reject is a safety signal, not nuisance.

---

# 281. Anti-Pattern — Bypass Approval During Incident

Incident pressure is not authorization.

---

# 282. Anti-Pattern — Manual DB Surgery First

Use supported Application/Admin controls first.

---

# 283. Anti-Pattern — Resume Immediately After Restore

Already prohibited.

---

# 284. Anti-Pattern — Treat Provider 404 as Failure Automatically

Could mean :

```text
never created
deleted
different account
eventual consistency
```

Interpret through connector semantics.

---

# 285. Anti-Pattern — Assume Provider Timeout Means Not Applied

Interdit.

---

# 286. Anti-Pattern — Ignore Partial Success

Many multi-step external operations can partially apply.

---

# 287. Partial Success

Should create explicit reconciliation/manual state.

---

# 288. Incident Escalation Matrix

| Situation | Reliability | Security | Product/Owner |
|---|---:|---:|---:|
| UNKNOWN Effect | ✓ | if sensitive | ✓ |
| Fencing regression | ✓ | ✓ | ✓ |
| Cross-tenant issue | ✓ | ✓✓ | ✓ |
| Provider outage | ✓ |  | ✓ |
| Approval bypass | ✓ | ✓✓ | ✓ |
| Restore/PITR | ✓✓ | maybe | ✓ |
| Migration cutover | ✓✓ | maybe | ✓ |

---

# 289. Postmortem Action Tracking

Chaque action :

```text
owner
priority
deadline
status
verification
```

---

# 290. Recurrence

Si même incident se répète :

```text
runbook-only fix is insufficient
```

Revoir architecture.

---

# 291. Incident Automation

Automatiser :

```text
evidence collection
safe freezes
read-only inspection
reconciliation lookup
```

---

# 292. What Not to Automate Blindly

```text
manual Effect success resolution
force takeover
compensation
cross-tenant repair
```

---

# 293. Operations API

Candidate future namespace :

```text
kit.ops
```

pour :

```text
inspect
freeze
drain
reconcile
recover
```

---

# 294. Ops API Safety

Must require explicit authorization and audit.

---

# 295. CLI Safety

Dangerous actions require :

```text
explicit ID
reason
confirmation
```

---

# 296. Dry Run

Preferred where possible.

---

# 297. Recovery Dry Run

Potentially show :

```text
RecoveryPlan
NextAction
blockers
```

without execution.

---

# 298. Manual Effect Resolution Dry Run

Show consequences before commit.

---

# 299. Runbook Testability

A runbook is better if its steps can be exercised automatically.

---

# 300. Production Qualification Integration

Runbooks are not complete until failure scenarios demonstrate that the prescribed steps work.

---

# 301. Runbook Metrics Summary

Critical metrics :

```text
effects_unknown_total
reconciliation_backlog
lease_renew_failures
stale_fencing_rejections
recoverable_runs_pending
outbox_lag
approval_backlog
db_pool_wait
worker_readiness
```

---

# 302. Alerts to Runbook Mapping

```text
Effect UNKNOWN spike → RB-005
Fencing rejects spike → RB-003/RB-004
DB down → RB-001
Lease p99 high → RB-027
Outbox lag → RB-015
Restore event → RB-036
```

---

# 303. Incident Bundle Example

```text
incident_id
run_id
tenant_id
effects[]
approvals[]
lease
runtime_invocations[]
external_refs[]
audit_refs[]
metrics_snapshot
```

---

# 304. Redaction

Incident bundle must remove :

```text
secret values
raw tokens
sensitive prompt content unless necessary
```

---

# 305. Chain of Custody

For security/compliance incidents, preserve who accessed/changed incident evidence.

---

# 306. Time Source

Use a canonical time source in incident timeline where possible.

---

# 307. Clock Confusion

Distinguish :

```text
worker local time
DB authoritative time
provider timestamps
```

---

# 308. Incident Recovery Principle

> **Re-read before re-act.**

---

# 309. Incident Governance Principle

> **Authority must be re-proven after disruption.**

---

# 310. Incident Effects Principle

> **Unknown external reality must be reconciled, not guessed.**

---

# 311. Incident Coordination Principle

> **A live process without a valid lease is not an owner.**

---

# 312. Incident Migration Principle

> **After cutover, forward-fix is often safer than rollback if irreversible V2 Effects occurred.**

---

# 313. Incident Restore Principle

> **Restoring internal state can move the database backward while the outside world stays forward.**

---

# 314. Acceptance Criteria

Le modèle incident response est conforme si :

1. les incidents sont classés par sévérité ;
2. le kill switch est défini ;
3. UNKNOWN Effect possède un runbook explicite ;
4. split-brain possède un runbook explicite ;
5. DB outage possède un runbook fail-safe ;
6. restore/PITR possède un safety gate ;
7. stale worker est couvert par fencing ;
8. Approval incidents sont distingués des AuthZ incidents ;
9. migration incidents sont couverts ;
10. coding Effects critiques ont des runbooks ;
11. les alertes pointent vers un runbook ;
12. chaque action manuelle critique est auditée ;
13. aucun runbook ne recommande un retry aveugle ;
14. postmortem et action tracking sont standardisés ;
15. les runbooks sont exercés régulièrement.

---

# 315. Definition of Done

`../operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md` est considéré mature lorsque :

1. les runbooks P0 sont implémentés ;
2. les commandes opérateur nécessaires existent ;
3. le kill switch est testable ;
4. l’incident bundle est automatisable ;
5. les alertes critiques sont reliées aux RB correspondants ;
6. les runbooks ont des owners ;
7. les game days ont été exécutés ;
8. les procédures restore/PITR ont été qualifiées ;
9. les scénarios UNKNOWN ont été testés avec vrais adapters ;
10. les manual interventions sont auditées ;
11. le postmortem template est adopté ;
12. les incidents importants alimentent tests/ADR/docs ;
13. les profils Standard/High Assurance sont distingués ;
14. aucun runbook safety-critical ne repose uniquement sur des mocks ;
15. les runbooks sont révisés à chaque release majeure.

---

# 316. Résumé

La réponse aux incidents PyAgentsKit suit la chaîne :

```text
DETECT
  │
  ▼
CLASSIFY
  │
  ▼
FREEZE UNSAFE ACTIONS
  │
  ▼
PRESERVE EVIDENCE
  │
  ▼
READ AUTHORITATIVE STATE
  │
  ▼
RECONCILE AMBIGUITY
  │
  ▼
RESTORE SAFE AUTHORITY
  │
  ▼
RECOVER GRADUALLY
  │
  ▼
VERIFY
  │
  ▼
POSTMORTEM
```

Les règles les plus importantes restent :

```text
UNKNOWN != FAILED
Retry != Reconciliation
Lease != Liveness
Restore != Safe Resume
Approval != Authorization
Cancellation != Rollback
```

Le principe fondamental est :

> **Lorsqu’un incident touche un agent capable d’agir dans le monde réel, la première responsabilité n’est pas de remettre le système en mouvement ; c’est d’empêcher qu’un système incertain continue à agir comme s’il savait.**
