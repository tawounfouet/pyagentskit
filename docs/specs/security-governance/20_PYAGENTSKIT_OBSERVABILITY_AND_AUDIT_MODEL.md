# PyAgentsKit — Observability & Audit Model

**Document :** `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Spécification métier et technique — Observability & Audit  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../architecture/08_PYAGENTSKIT_ERD.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md`

---

# 1. Objet

Ce document définit le modèle d’**observabilité et d’audit** de PyAgentsKit.

Il précise comment le framework doit :

- produire des logs structurés ;
- exposer des métriques ;
- produire des traces distribuées ;
- propager un contexte de corrélation ;
- distinguer observabilité technique et audit métier ;
- reconstruire la timeline d’un Run ;
- reconstruire la timeline d’un Effect ;
- suivre approvals, leases, takeovers et workers ;
- exposer health et readiness ;
- détecter les états bloqués ou incohérents ;
- définir alertes et SLOs ;
- protéger les données sensibles ;
- assurer une rétention adaptée ;
- permettre l’analyse d’incident ;
- rester compatible avec OpenTelemetry.

Le principe directeur est :

> **Tout comportement critique doit être observable ; toute décision critique doit être auditable ; aucune de ces deux propriétés ne doit dépendre de l’autre.**

---

# 2. Distinction Observability / Audit

## Observability

Répond à :

```text
What is happening?
Why is the system behaving this way?
Is it healthy?
Where is the latency?
What failed?
```

Elle repose principalement sur :

```text
logs
metrics
traces
health/readiness
diagnostics
```

## Audit

Répond à :

```text
Who did what?
On which object?
When?
Why?
Under which policy/approval/ownership?
What changed?
```

L’audit est une trace métier durable et autoritative.

---

# 3. Principe de séparation

```text
Log
!=
AuditEvent

Metric
!=
AuditEvent

TraceSpan
!=
AuditEvent

DomainEvent
!=
AuditEvent
```

Ces objets peuvent être corrélés mais ne sont pas interchangeables.

---

# 4. Objectifs

Le modèle doit offrir :

```text
traceability
debuggability
operability
incident reconstruction
distributed correlation
performance visibility
security visibility
audit durability
data minimization
backend neutrality
```

---

# 5. Non-objectifs

PyAgentsKit ne doit pas devenir :

```text
log storage platform
SIEM
APM SaaS
Prometheus server
Grafana replacement
trace backend
data warehouse
security analytics platform
```

Il produit des signaux compatibles avec ces systèmes.

---

# 6. Les quatre piliers opérationnels

PyAgentsKit distingue :

```text
Logs
Metrics
Traces
Audit
```

avec en complément :

```text
Health
Readiness
Diagnostics
```

---

# 7. Architecture générale

```text
PyAgentsKit Components
       │
       ├── Logs
       ├── Metrics
       ├── Traces
       └── AuditEvents
              │
      ┌───────┼─────────┐
      ▼       ▼         ▼
 OpenTelemetry       AuditStore
 Collector              │
      │                  ▼
      ▼             Audit Queries
Observability
 Backends
```

---

# 8. OpenTelemetry

OpenTelemetry est le standard privilégié pour :

```text
traces
metrics
logs where appropriate
context propagation
```

PyAgentsKit doit rester compatible avec une exécution sans OTel, mais l’intégration OTel doit être de premier niveau.

---

# 9. TelemetryPort

Port conceptuel :

```python
class TelemetryPort(Protocol):
    def counter(...): ...
    def histogram(...): ...
    def gauge(...): ...
    def start_span(...): ...
    def log(...): ...
```

L’API publique réelle pourra être plus spécialisée.

---

# 10. LoggingPort

Optionnellement séparé :

```python
class LoggingPort(Protocol):
    def emit(self, record: StructuredLogRecord) -> None:
        ...
```

---

# 11. MetricsPort

```python
class MetricsPort(Protocol):
    def increment(...): ...
    def observe(...): ...
    def set_gauge(...): ...
```

---

# 12. TracingPort

```python
class TracingPort(Protocol):
    def start_span(...): ...
```

---

# 13. AuditPublisher

Le composant métier d’audit est séparé :

```python
class AuditPublisher(Protocol):
    async def publish(self, event: AuditEvent) -> None:
        ...
```

---

# 14. AuditStore

Port conceptuel :

```python
class AuditStore(Protocol):
    async def append(self, event: AuditEvent) -> None:
        ...
    async def list_for_object(...): ...
    async def list_for_run(...): ...
    async def list_for_actor(...): ...
```

---

# 15. CorrelationContext

Structure conceptuelle :

```text
trace_id?
span_id?
correlation_id?
run_id?
session_id?
conversation_id?
message_id?
effect_id?
approval_id?
lease_id?
worker_id?
runtime_invocation_id?
tenant_id?
```

---

# 16. Règle de corrélation

Le contexte doit être propagé entre :

```text
API
DurableRunner
RuntimeAdapter
ToolGateway
EffectExecutionService
Stores
External connectors
Audit
```

---

# 17. Correlation ≠ Identity

`correlation_id` sert à relier des opérations.

Il ne remplace pas :

```text
Principal
Actor
Tenant
RunId
```

---

# 18. Trace ID

Le `trace_id` est principalement technique et peut être géré par OpenTelemetry.

Le `correlation_id` peut représenter une corrélation applicative plus durable.

---

# 19. Propagation distribuée

Lorsqu’un Run change de worker :

```text
Worker A
↓
checkpoint / takeover
↓
Worker B
```

la nouvelle invocation doit conserver :

```text
run_id
correlation_id
```

tout en pouvant produire une nouvelle trace ou un nouveau span root lié.

---

# 20. Trace continuity after takeover

Deux options :

```text
same trace if technically practical
```

ou :

```text
new trace linked to previous trace
```

Le Run reste la corrélation durable principale.

---

# 21. Structured Logs

Les logs doivent être structurés.

Format recommandé :

```text
JSON
```

avec champs normalisés.

---

# 22. Champs de logs

Selon contexte :

```text
timestamp
level
event_name
component
operation
run_id
session_id
conversation_id
effect_id
approval_id
lease_id
worker_id
runtime_name
trace_id
correlation_id
tenant_id
duration_ms
status
error_type
```

---

# 23. Logging levels

```text
DEBUG
INFO
WARNING
ERROR
CRITICAL
```

---

# 24. DEBUG

Pour :

```text
internal transitions
adapter details
non-sensitive diagnostic context
```

Ne doit pas contenir de secrets.

---

# 25. INFO

Pour :

```text
run started
run resumed
effect succeeded
lease takeover
approval decided
worker draining
```

---

# 26. WARNING

Pour :

```text
retryable degradation
lease renewal uncertainty
runtime degraded
reconciliation pending
approaching timeout
```

---

# 27. ERROR

Pour :

```text
failed operation
store unavailable
runtime failure
reconciliation failure
```

---

# 28. CRITICAL

Réservé à :

```text
security control unavailable
possible invariant violation
audit integrity failure
critical state corruption
```

---

# 29. Sensitive logging

Ne jamais loguer par défaut :

```text
access tokens
passwords
private keys
full prompts
raw sensitive messages
credit card data
full secrets
```

---

# 30. Payload logging policy

Niveaux :

```text
NONE
METADATA_ONLY
REDACTED
FULL
```

`FULL` doit être explicitement activé et sécurisé.

---

# 31. Redaction

Le pipeline doit permettre :

```text
field redaction
secret masking
pattern redaction
classification-based filtering
```

---

# 32. Metrics Philosophy

Les métriques servent à :

```text
health
capacity
latency
failure rate
backlog
saturation
coordination behavior
```

---

# 33. Metric cardinality

Éviter comme labels :

```text
run_id
effect_id
approval_id
worker_id
message_id
external_reference
```

sauf cas très contrôlé.

---

# 34. Labels autorisés candidats

```text
runtime
effect_kind
status
risk_level
store_type
adapter
environment
result
worker_pool
tenant_tier
```

avec prudence sur cardinalité.

---

# 35. Run Metrics

```text
runs_created_total
runs_started_total
runs_resumed_total
runs_recovered_total
runs_succeeded_total
runs_failed_total
runs_cancelled_total
runs_waiting
runs_paused
```

---

# 36. Run Latency Metrics

```text
run_duration_seconds
run_wait_duration_seconds
run_recovery_duration_seconds
```

---

# 37. Checkpoint Metrics

```text
checkpoints_created_total
checkpoint_write_latency_seconds
checkpoint_read_latency_seconds
checkpoint_failures_total
```

---

# 38. Effect Metrics

```text
effects_started_total
effects_succeeded_total
effects_failed_total
effects_unknown_total
effects_reconciled_total
effects_manual_review_total
effect_idempotency_conflicts_total
```

---

# 39. Effect Latency

```text
effect_execution_duration_seconds
effect_reconciliation_duration_seconds
effect_approval_wait_seconds
```

---

# 40. Approval Metrics

```text
approvals_requested_total
approvals_approved_total
approvals_rejected_total
approvals_expired_total
approvals_cancelled_total
approvals_pending
```

---

# 41. Approval Latency

```text
approval_decision_latency_seconds
approval_execution_gap_seconds
```

---

# 42. Lease Metrics

```text
leases_acquired_total
leases_renewed_total
lease_renewal_failures_total
leases_lost_total
leases_expired_total
lease_takeovers_total
lease_conflicts_total
fencing_rejections_total
```

---

# 43. Lease Latency

```text
lease_acquire_latency_seconds
lease_renew_latency_seconds
lease_takeover_latency_seconds
```

---

# 44. Worker Metrics

```text
workers_ready
workers_busy
workers_draining
workers_unhealthy
active_runs
active_leases
worker_heartbeat_age_seconds
```

---

# 45. Runtime Adapter Metrics

```text
runtime_invocations_total
runtime_invocation_failures_total
runtime_resume_total
runtime_cancel_total
runtime_event_stream_disconnects_total
runtime_adapter_errors_total
```

---

# 46. Runtime Latency

```text
runtime_start_latency_seconds
runtime_resume_latency_seconds
runtime_status_latency_seconds
```

---

# 47. Store Metrics

```text
store_operations_total
store_errors_total
store_operation_latency_seconds
db_pool_in_use
db_pool_wait_seconds
transaction_retries_total
```

---

# 48. Outbox Metrics

```text
outbox_pending
outbox_publish_total
outbox_publish_failures_total
outbox_oldest_pending_age_seconds
```

---

# 49. Inbox Metrics

```text
inbox_received_total
inbox_duplicates_total
inbox_processing_failures_total
```

---

# 50. Artifact Metrics

```text
artifacts_created_total
artifact_write_bytes_total
artifact_read_bytes_total
artifact_failures_total
artifact_storage_bytes
```

---

# 51. Conversation Metrics

```text
messages_appended_total
message_deduplications_total
conversations_open
```

Ne pas exposer le contenu.

---

# 52. Security Metrics

```text
authn_failures_total
authz_denials_total
policy_denials_total
sandbox_violations_total
secret_resolution_failures_total
tenant_violation_attempts_total
break_glass_total
```

---

# 53. Reconciliation Backlog

Métriques essentielles :

```text
reconciliation_open_cases
reconciliation_manual_review
reconciliation_oldest_age_seconds
```

---

# 54. Saturation Metrics

```text
worker_run_capacity_usage
effect_concurrency_usage
db_pool_usage
runtime_slot_usage
queue_depth
```

---

# 55. Tracing Model

Les traces doivent relier :

```text
request
Run
RuntimeInvocation
ToolInvocation
Effect
ExternalCall
Store operations
```

---

# 56. Span hierarchy

Exemple :

```text
run.start
└── runtime.start
    ├── runtime.events
    └── tool.invoke
        └── effect.execute
            ├── db.effect.reserve
            ├── external.call
            └── db.effect.complete
```

---

# 57. Spans Run

```text
run.create
run.start
run.resume
run.pause
run.cancel
run.recover
run.complete
```

---

# 58. Spans Runtime

```text
runtime.start
runtime.resume
runtime.status
runtime.cancel
runtime.events
```

---

# 59. Spans Effects

```text
effect.prepare
effect.authorize
effect.approval_validate
effect.fencing_validate
effect.execute
effect.reconcile
effect.persist_outcome
```

---

# 60. Spans Coordination

```text
lease.acquire
lease.renew
lease.release
lease.takeover
ownership.revalidate
```

---

# 61. Spans Stores

```text
db.run.transition
db.checkpoint.append
db.effect.reserve
db.approval.decide
db.lease.acquire
db.audit.append
```

---

# 62. Spans External

Suivre les conventions OpenTelemetry lorsque disponibles pour :

```text
HTTP
database
messaging
RPC
```

---

# 63. Span attributes

Attributs à faible cardinalité :

```text
runtime.name
effect.kind
effect.risk_level
operation
status
environment
store.type
```

Les IDs métier peuvent rester dans spans/logs si backend adapté, mais pas dans métriques globales.

---

# 64. Span events

Exemples :

```text
checkpoint.created
approval.required
lease.lost
reconciliation.started
```

---

# 65. Trace sampling

Les traces peuvent être samplées.

Mais :

```text
AuditEvent
```

ne doit jamais dépendre du sampling.

---

# 66. Error Recording

Une erreur doit inclure :

```text
error_type
message sanitized
retryability
component
operation
```

---

# 67. Stack traces

Peuvent être enregistrées dans logs/traces techniques, avec contrôle de sensibilité.

---

# 68. AuditEvent

Structure conceptuelle :

```text
audit_event_id
event_name
object_type
object_id
actor_reference?
principal_reference?
run_id?
tenant_id?
correlation_id?
timestamp
reason?
before?
after?
metadata
```

---

# 69. Audit object types

Exemples :

```text
Run
Effect
Approval
Lease
Worker
Message
Artifact
Policy
Adapter
Tenant
```

---

# 70. Audit Event Names

Convention :

```text
resource.action
```

Exemples :

```text
run.started
run.cancelled
effect.started
effect.succeeded
effect.unknown
approval.approved
lease.taken_over
policy.changed
security.break_glass_used
```

---

# 71. Audit append-only

Le modèle doit être :

```text
append-oriented
```

Une correction produit un nouvel événement.

---

# 72. Audit before/after

Pour certaines mutations :

```text
before
after
```

peuvent être utiles.

Mais éviter de dupliquer de gros payloads sensibles.

---

# 73. Audit Actor

L’audit doit distinguer :

```text
human actor
service principal
agent
worker
system
```

---

# 74. Audit Reason

Certaines actions doivent imposer un `reason`.

Exemples :

```text
force takeover
manual effect resolution
break-glass
policy change
manual cancellation
```

---

# 75. Audit and Policy

Pour une action sensible, conserver si pertinent :

```text
policy_id
policy_version
policy_decision
```

---

# 76. Audit and Approval

Conserver :

```text
approval_id
approval status
deciding actor
scope reference
```

---

# 77. Audit and Ownership

Conserver :

```text
worker_id
lease_id
fencing_token
```

pour les actions protégées.

---

# 78. Audit and ExternalReference

Un Effect peut enregistrer :

```text
external system
external reference
```

sans exposer un secret.

---

# 79. Run Timeline

Une vue opérateur doit pouvoir reconstruire :

```text
Run created
Run started
Checkpoint created
Effect reserved
Approval requested
Approval approved
Worker lost
Lease taken over
Effect reconciled
Runtime resumed
Run succeeded
```

---

# 80. Effect Timeline

Exemple :

```text
Effect intended
Effect started
External timeout
Effect unknown
Reconciliation opened
External reference found
Effect reconciled success
```

---

# 81. Approval Timeline

```text
Approval requested
Notification sent
Escalated
Approved
Run resumed
Effect executed
```

---

# 82. Lease Timeline

```text
Lease acquired
Renewed
Renewal failed
Expired
Taken over
Old worker fencing rejected
```

---

# 83. Worker Timeline

```text
registered
ready
busy
draining
unhealthy
stopped
```

---

# 84. Coding Agent Timeline

Exemple :

```text
Run started
Codex invocation started
Files modified
Tests run
git_push Effect requested
Approval required
Approved
git_push succeeded
PR Effect requested
PR created
Run completed
```

---

# 85. Audit Query API

Candidates :

```text
GET /audit?run_id=...
GET /audit?effect_id=...
GET /audit?actor_id=...
GET /audit?event_name=...
GET /audit?from=...&to=...
```

---

# 86. CLI Candidates

```text
pyagentskit run timeline <run_id>
pyagentskit effect timeline <effect_id>
pyagentskit approval timeline <approval_id>
pyagentskit lease timeline <resource>
pyagentskit audit query ...
```

---

# 87. Audit Views

Read models possibles :

```text
run_audit_timeline
effect_audit_timeline
approval_audit_timeline
ownership_history
security_event_timeline
```

---

# 88. Audit Integrity

Le backend doit protéger :

```text
append semantics
write authorization
retention
tamper detection
```

---

# 89. Tamper-evident Audit

Extension possible :

```text
hash chaining
signed batches
external immutable archive
WORM storage
```

Pas obligatoire pour MVP, mais utile en profil `HIGH_ASSURANCE`.

---

# 90. Audit Availability

En profil `STANDARD`, une courte indisponibilité peut être traitée selon configuration.

En `HIGH_ASSURANCE` :

```text
critical action without durable audit
→ fail closed
```

---

# 91. Audit Outbox

Pour garantir :

```text
state committed
+
audit event not lost
```

un pattern Outbox peut être utilisé.

---

# 92. Transactional Audit

Pour certaines transitions :

```text
domain mutation
+
AuditEvent
```

peuvent être persistés dans la même transaction locale.

---

# 93. Health

`/livez` répond :

```text
is the process alive?
```

---

# 94. Readiness

`/readyz` répond :

```text
can this worker safely accept work?
```

---

# 95. Health != Readiness

Un worker peut être :

```text
alive
```

mais :

```text
not ready
```

---

# 96. Readiness dependencies

Selon workload :

```text
RunStore
EffectStore
LeaseStore
required runtime adapter
policy engine
SecretProvider
AuditStore
```

---

# 97. Partial readiness

Un worker peut être ready pour :

```text
LangGraph workloads
```

et non ready pour :

```text
Codex workloads
```

---

# 98. Component Health

Chaque composant peut exposer :

```text
HEALTHY
DEGRADED
UNAVAILABLE
UNKNOWN
```

---

# 99. Diagnostic Detail

Health response ne doit pas exposer :

```text
credentials
internal secrets
sensitive topology
```

---

# 100. Readiness fail conditions

Exemples :

```text
LeaseStore unavailable
schema incompatible
critical policy missing
required adapter unavailable
worker draining
```

---

# 101. SLI

Indicateurs candidates :

```text
Run success rate
Run recovery success rate
Effect unknown rate
Lease renewal success rate
Takeover recovery time
Approval latency
Store latency
Runtime adapter error rate
```

---

# 102. SLO — Run Reliability

Exemple cible initiale à qualifier :

```text
>= 99.9% of recoverable Runs recover successfully
```

Ce nombre doit être validé par qualification réelle avant engagement public.

---

# 103. SLO — Effect Safety

Indicateur plus important que simple availability :

```text
0 known implicit replay of successful protected Effects
```

Objectif :

```text
zero tolerance
```

---

# 104. SLO — Lease Renewal

Exemple à qualifier :

```text
p99 lease renewal latency < TTL safety margin
```

---

# 105. SLO — Takeover

Mesurer :

```text
time from lease expiry
to replacement worker resuming safely
```

---

# 106. SLO — Reconciliation

Mesurer :

```text
unknown Effect resolution time
```

par niveau de risque.

---

# 107. Error Budget

Peut être défini sur :

```text
run availability
runtime adapter reliability
store availability
```

Mais pas sur des invariants de safety tels que :

```text
duplicate critical effect
```

---

# 108. Safety Invariant vs SLO

```text
"no stale fencing token accepted"
```

est un invariant.

Ce n’est pas :

```text
99.9% SLO
```

---

# 109. Alerts

Alertes P0 candidates :

```text
fencing rejection spike
duplicate effect suspicion
audit unavailable in high assurance
cross-tenant violation
DB unavailable
multiple active owners detected
```

---

# 110. Alerts P1

```text
reconciliation backlog
approval backlog
lease renewal error rate
worker pool saturation
runtime adapter failure spike
outbox backlog
```

---

# 111. Alerts P2

```text
high latency
artifact storage growth
message backlog
non-critical adapter degraded
```

---

# 112. Alert Deduplication

Éviter :

```text
one alert per Run
```

si un incident global affecte des milliers de Runs.

---

# 113. Alert Grouping

Grouper par :

```text
component
failure mode
environment
runtime
store
```

---

# 114. Alert Fatigue

Les alertes doivent être :

```text
actionable
owned
severity-defined
linked to runbooks
```

---

# 115. Dashboards

Dashboards recommandés :

```text
System Overview
Run Reliability
Effect Safety
Distributed Coordination
Approvals
Runtime Adapters
Persistence
Security
```

---

# 116. System Overview Dashboard

Afficher :

```text
active runs
waiting runs
run success/failure
worker health
DB health
unknown effects
pending approvals
lease takeovers
```

---

# 117. Effect Safety Dashboard

Afficher :

```text
effects by status
UNKNOWN effects
reconciliation backlog
idempotency conflicts
fencing rejections
manual reviews
```

---

# 118. Coordination Dashboard

Afficher :

```text
active leases
renewal failures
takeovers
conflicts
worker heartbeat age
```

---

# 119. Approval Dashboard

Afficher :

```text
pending approvals
age
decision latency
expiry
rejections
```

---

# 120. Runtime Dashboard

Afficher :

```text
invocations
errors
latency
resume rate
event stream disconnects
adapter health
```

---

# 121. Persistence Dashboard

Afficher :

```text
DB latency
pool saturation
transactions
deadlocks
outbox backlog
store errors
```

---

# 122. Security Dashboard

Afficher :

```text
AuthZ denials
sandbox violations
tenant violations
break-glass
force takeover
policy denials
```

---

# 123. Run Inspection

Un opérateur doit voir :

```text
Run status
latest checkpoint
current/last worker
current lease
runtime binding
pending approvals
unknown effects
recent events
trace links
```

---

# 124. Effect Inspection

Afficher :

```text
effect kind
status
idempotency key
fingerprint
approval
ownership context
external reference
reconciliation state
```

---

# 125. Approval Inspection

Afficher :

```text
status
scope
requester
approver
decision
reason
expiry
policy
effect reference
```

---

# 126. Lease Inspection

Afficher :

```text
resource
owner
fencing token
acquired_at
renewed_at
expires_at
history
```

---

# 127. Runtime Inspection

Afficher :

```text
adapter
runtime version
capabilities
RuntimeHandle reference
latest invocation
status
health
```

---

# 128. Privacy

Observability ne doit pas devenir un canal de fuite.

Contrôles :

```text
redaction
data classification
access control
retention
sampling
payload omission
```

---

# 129. Tenant Isolation in Telemetry

Éviter les dashboards ou queries permettant à un tenant de voir les données d’un autre.

---

# 130. Tenant Labels

`tenant_id` peut être dangereux comme metric label si cardinalité élevée.

Préférer :

```text
tenant_tier
tenant_class
```

pour métriques globales.

---

# 131. Tenant-specific Monitoring

Peut utiliser des dashboards/filters dédiés avec contrôle d’accès plutôt que labels métriques globaux.

---

# 132. Retention — Logs

Durée configurable selon :

```text
environment
sensitivity
cost
compliance
```

---

# 133. Retention — Metrics

Généralement plus longue car données agrégées.

---

# 134. Retention — Traces

Peut être plus courte et samplée.

---

# 135. Retention — Audit

Souvent plus longue car liée à :

```text
accountability
incident response
compliance
```

---

# 136. Different Retention Policies

```text
logs != traces != metrics != audit
```

La policy doit être définie séparément.

---

# 137. Audit Privacy

L’audit doit minimiser le contenu sensible tout en restant utile.

Conserver :

```text
who
what
when
why
result
references
```

plutôt que des payloads complets.

---

# 138. Right to Delete vs Audit

Dans certains contextes, obligations de suppression et exigences d’audit peuvent entrer en tension.

PyAgentsKit doit fournir les abstractions nécessaires à :

```text
redaction
pseudonymization
retention policy
```

sans coder une politique juridique universelle.

---

# 139. Pseudonymization

Un Actor peut être rendu :

```text
pseudonymous
```

dans certaines vues tout en gardant un lien sécurisé pour audit autorisé.

---

# 140. Telemetry Access Control

Rôles possibles :

```text
OPERATOR
SRE
SECURITY
AUDITOR
TENANT_ADMIN
```

avec vues différentes.

---

# 141. Operator vs Auditor

```text
Operator
= diagnostiquer et exploiter

Auditor
= reconstruire des décisions
```

Les besoins ne sont pas identiques.

---

# 142. Incident Reconstruction

Pour un incident, il faut pouvoir relier :

```text
Run
Worker
Lease
RuntimeInvocation
Effect
Approval
ExternalReference
AuditEvent
Trace
```

---

# 143. Incident Bundle

Commande future possible :

```text
pyagentskit incident bundle <run_id>
```

produisant :

```text
timeline
state snapshots
audit references
trace IDs
effect states
ownership history
```

sans secrets.

---

# 144. Runbook Linking

Une alerte devrait référencer un runbook.

Exemple :

```text
ALERT: reconciliation backlog
RUNBOOK: effect-reconciliation-backlog
```

---

# 145. Diagnostics Endpoint

Endpoint administratif possible :

```text
/diagnostics
```

avec accès restreint.

---

# 146. Diagnostic Snapshot

Peut inclure :

```text
worker status
store health
adapter health
active run count
lease count
outbox backlog
```

---

# 147. Debug Dumps

À éviter en production s’ils contiennent du state sensible.

---

# 148. Audit of Observability Changes

Les changements critiques de configuration observability doivent être audités.

Exemples :

```text
audit disabled
trace sampling reduced
security alerts disabled
retention shortened
```

---

# 149. Telemetry Failure

Une panne OTel Collector :

```text
should not normally fail business execution
```

---

# 150. Audit Failure

Une panne AuditStore peut être plus critique.

Le comportement dépend du profil :

```text
STANDARD
HIGH_ASSURANCE
```

---

# 151. Telemetry Backpressure

Le pipeline observability doit être borné.

Éviter :

```text
unbounded log queue
```

qui pourrait faire tomber le worker.

---

# 152. Drop Policy

En saturation :

```text
drop DEBUG first
preserve ERROR/CRITICAL where possible
never silently drop required AuditEvents
```

---

# 153. Async Export

Logs/traces peuvent être exportés de manière asynchrone et batchée.

---

# 154. Graceful Shutdown Telemetry

Lors d’un shutdown :

```text
flush telemetry
```

dans une fenêtre bornée.

---

# 155. Audit Flush

Les AuditEvents transactionnels critiques ne doivent pas dépendre d’un flush mémoire final.

---

# 156. Sampling Policy

Traces candidates :

```text
100% errors
100% critical Effects
100% security-relevant flows
sample normal low-risk runs
```

selon backend/coût.

---

# 157. Tail Sampling

Une architecture OTel peut utiliser tail sampling pour conserver les traces intéressantes.

---

# 158. Logs / Traces Correlation

Inclure :

```text
trace_id
span_id
```

dans les logs lorsque disponible.

---

# 159. Audit / Trace Correlation

AuditEvent peut contenir :

```text
trace_id
correlation_id
```

mais l’audit reste utilisable sans trace.

---

# 160. DomainEvent / AuditEvent Correlation

Un DomainEvent peut déclencher un AuditEvent, avec :

```text
causation_id
correlation_id
```

si le modèle le justifie.

---

# 161. CausationContext

Value Object candidat :

```text
event_id
caused_by_event_id?
caused_by_message_id?
caused_by_effect_id?
```

---

# 162. Event Ordering

L’ordre global distribué n’est pas supposé.

L’ordre local peut utiliser :

```text
timestamp
sequence
aggregate version
```

---

# 163. Clock Considerations

Les timestamps doivent être :

```text
UTC
timezone-aware
```

Pour coordination critique, le temps DB reste autoritatif.

---

# 164. Audit Sequence

Une séquence par aggregate peut aider :

```text
Run audit sequence
Effect audit sequence
```

mais n’est pas forcément nécessaire au MVP.

---

# 165. Metrics Naming

Convention recommandée :

```text
pyagentskit_<subsystem>_<metric>
```

Exemple :

```text
pyagentskit_effects_unknown_total
```

---

# 166. Units

Utiliser les conventions OTel/Prometheus :

```text
seconds
bytes
items
```

éviter les unités ambiguës.

---

# 167. Histogram Buckets

Les buckets doivent être adaptés au workload et configurables.

---

# 168. Semantic Conventions

Lorsque OpenTelemetry définit une convention standard :

```text
HTTP
DB
messaging
RPC
```

la réutiliser plutôt que créer un vocabulaire propriétaire.

---

# 169. Custom Semantic Attributes

Namespace recommandé :

```text
pyagentskit.*
```

Exemples :

```text
pyagentskit.run.state
pyagentskit.effect.kind
pyagentskit.effect.risk_level
pyagentskit.runtime.adapter
```

---

# 170. Alert — Stuck Run

Un Run peut être considéré bloqué selon :

```text
RUNNING too long without checkpoint
WAITING beyond expected blocker TTL
PAUSED unexpectedly long
```

---

# 171. Alert — Stuck Effect

```text
STARTED too long
UNKNOWN too long
RECONCILIATION_REQUIRED too long
```

---

# 172. Alert — Stale Worker

Signaux :

```text
heartbeat old
lease still active
renewals failing
```

---

# 173. Alert — Lease Churn

Trop de takeovers peut indiquer :

```text
worker instability
TTL too short
DB latency
network issues
```

---

# 174. Alert — Idempotency Conflicts

Un spike peut indiquer :

```text
bug
duplicate triggers
malicious attempts
bad key design
```

---

# 175. Alert — Approval Backlog

Peut indiquer :

```text
missing approvers
policy too strict
notification failure
```

---

# 176. Alert — Unknown Effect Rate

Une hausse est critique car elle augmente le risque opérationnel.

---

# 177. Alert — Audit Failure

Toujours hautement visible.

---

# 178. Alert — Security Denial Spike

Peut signaler :

```text
attack
bad deployment
policy regression
misconfigured runtime
```

---

# 179. Operational Runbooks

Runbooks candidats :

```text
RUNBOOK_RUN_STUCK
RUNBOOK_EFFECT_UNKNOWN
RUNBOOK_RECONCILIATION_BACKLOG
RUNBOOK_LEASE_STORM
RUNBOOK_WORKER_ZOMBIE
RUNBOOK_DB_OUTAGE
RUNBOOK_RUNTIME_OUTAGE
RUNBOOK_AUDIT_OUTAGE
RUNBOOK_SECURITY_DENIAL_SPIKE
```

---

# 180. Audit and Manual Resolution

Une résolution manuelle d’Effect doit enregistrer :

```text
actor
reason
previous state
new resolution
evidence
timestamp
```

---

# 181. Audit and Force Takeover

Doit enregistrer :

```text
resource
old owner
new owner
old token
new token
actor
reason
```

---

# 182. Audit and Break-glass

Doit être :

```text
high-severity
searchable
alertable
retained
```

---

# 183. Audit and Policy Change

Conserver :

```text
policy_id
old_version
new_version
actor
reason
timestamp
```

---

# 184. Audit and Adapter Change

Conserver :

```text
adapter name
old version
new version
actor
compatibility result
```

---

# 185. Audit and Migration

Migrations de schéma importantes doivent être auditées :

```text
migration id
from version
to version
operator
result
```

---

# 186. Coding Agent Observability

Pour coding agents, suivre :

```text
runtime invocation
workspace
commands
tests
Effects Git/PR/publish/deploy
artifacts
approval decisions
```

---

# 187. Command Logging

Ne pas logger nécessairement la sortie complète de chaque commande.

Préférer :

```text
command identity
exit code
duration
output artifact reference
```

---

# 188. Test Output

Peut être stocké comme Artifact pour éviter des logs gigantesques.

---

# 189. Git Observability

Références utiles :

```text
repository
branch
commit SHA
PR number
```

sans stocker inutilement des credentials ou le repository complet.

---

# 190. Deployment Observability

Conserver :

```text
environment
artifact checksum
deployment reference
result
duration
approval reference
```

---

# 191. Cost Observability

Extension utile :

```text
runtime token usage
LLM cost
tool cost
storage cost
```

mais sans mélanger coût et correctness.

---

# 192. Cost Metrics

Candidates :

```text
runtime_input_tokens_total
runtime_output_tokens_total
runtime_cost_estimated
artifact_storage_bytes
```

---

# 193. Cost Cardinality

Éviter des labels par Run si backend métrique global.

---

# 194. Performance Budget

Mesurer l’overhead PyAgentsKit :

```text
store latency
effect gate latency
approval validation latency
lease operations
telemetry overhead
```

---

# 195. Observability Overhead

L’observabilité ne doit pas :

```text
materially break latency
exhaust memory
block critical paths unnecessarily
```

---

# 196. Audit Overhead

L’audit critique peut justifier une transaction supplémentaire, mais doit être mesuré.

---

# 197. Test Strategy — Logs

Vérifier :

```text
structured fields
correlation
no secret leakage
correct levels
```

---

# 198. Test Strategy — Metrics

Vérifier :

```text
counter increments
histograms
gauges
cardinality
no IDs as labels
```

---

# 199. Test Strategy — Traces

Vérifier :

```text
parent/child relationships
context propagation
error recording
external call spans
```

---

# 200. Test Strategy — Audit

Vérifier :

```text
append-only semantics
actor
object
timestamp
reason
state transition
```

---

# 201. Test — Takeover Trace

Scénario :

```text
Worker A starts
A freezes
B takeover
Run resumes
```

Vérifier :

```text
one Run timeline
multiple worker/trace segments
ownership history preserved
```

---

# 202. Test — Unknown Effect

Vérifier :

```text
metric increment
audit event
trace
alert candidate
reconciliation timeline
```

---

# 203. Test — Secret Leakage

Injecter un secret connu et vérifier qu’il n’apparaît pas dans :

```text
logs
traces
metrics
audit
diagnostics
```

---

# 204. Test — Audit Store Outage

Vérifier le comportement selon profil :

```text
STANDARD
HIGH_ASSURANCE
```

---

# 205. Test — Telemetry Backend Outage

Le business flow ne doit généralement pas tomber.

---

# 206. Test — High Cardinality Protection

Créer de nombreux Runs et vérifier que :

```text
metrics label cardinality remains bounded
```

---

# 207. Test — Retention

Vérifier purge/archivage selon policies sans supprimer ce qui doit rester auditable.

---

# 208. Test — Multi-tenant Telemetry

Vérifier isolation des vues et absence de fuite inter-tenant.

---

# 209. Production Qualification

L’observabilité est production-ready lorsque :

```text
real OTel exporter
real metrics backend
distributed traces across workers
real audit persistence
alerts
dashboards
runbooks
load-tested telemetry pipeline
```

---

# 210. Acceptance Criteria

Le modèle Observability & Audit est opérationnel si :

1. logs, metrics, traces et audit sont clairement séparés ;
2. un `CorrelationContext` est propagé ;
3. un Run peut être suivi à travers plusieurs workers ;
4. les Effects inconnus sont visibles ;
5. les leases/takeovers sont mesurés ;
6. les approvals sont mesurées et auditables ;
7. health et readiness sont distincts ;
8. les security events sont visibles ;
9. les IDs métier ne provoquent pas de cardinalité métrique non bornée ;
10. les secrets ne fuient pas dans la télémétrie ;
11. l’AuditStore est append-oriented ;
12. une timeline de Run peut être reconstruite ;
13. une timeline d’Effect peut être reconstruite ;
14. des dashboards et alertes opérationnels existent ;
15. les alertes critiques sont liées à des runbooks ;
16. l’OTel Collector peut tomber sans casser l’exécution normale ;
17. le comportement en panne AuditStore est défini ;
18. takeover et recovery sont traçables de bout en bout.

---

# 211. Invariants

```text
OBS-INV-01
AuditEvent is not a log line.

OBS-INV-02
Trace sampling never removes required audit.

OBS-INV-03
Metric labels remain bounded.

OBS-INV-04
Secrets are redacted before telemetry export.

OBS-INV-05
Run identity survives worker takeover.

OBS-INV-06
Health and readiness are distinct.

OBS-INV-07
Critical ownership changes are auditable.

OBS-INV-08
Protected Effect decisions are traceable.

OBS-INV-09
Telemetry backend failure does not normally become business failure.

OBS-INV-10
High-assurance audit requirements may fail closed.
```

---

# 212. Anti-patterns

À éviter :

```text
logs as source of truth
AuditEvent generated only from logs
run_id as Prometheus label
full prompt logging by default
one alert per failing Run
health == readiness
audit coupled to trace sampling
telemetry queues unbounded
security events mixed invisibly with debug logs
```

---

# 213. Architecture cible

```text
                    PyAgentsKit Components
                             │
             ┌───────────────┼────────────────┐
             ▼               ▼                ▼
        Structured Logs    Metrics          Traces
             │               │                │
             └───────────────┼────────────────┘
                             ▼
                    OpenTelemetry Layer
                             │
                             ▼
                     OTel Collector
                             │
                ┌────────────┼────────────┐
                ▼            ▼            ▼
               Logs        Metrics       Traces
              Backend      Backend       Backend

                    Domain / Security
                             │
                             ▼
                       AuditPublisher
                             │
                             ▼
                        AuditStore
                             │
                             ▼
                Timelines / Compliance /
                 Incident Reconstruction
```

---

# 214. Flux nominal

```text
API request
↓
trace starts
↓
Run created
↓
structured log
↓
metric increment
↓
AuditEvent run.created
↓
runtime invocation
↓
Effect
↓
external call
↓
Run completed
↓
trace closes
```

---

# 215. Flux takeover

```text
Worker A trace
↓
lease lost
↓
AuditEvent lease.lost
↓
Worker B new trace segment
↓
same run_id / correlation_id
↓
AuditEvent lease.taken_over
↓
Run resumes
```

---

# 216. Flux incident

```text
alert fires
↓
operator opens dashboard
↓
inspect Run
↓
load audit timeline
↓
follow trace
↓
inspect Effect / Lease
↓
apply runbook
```

---

# 217. Questions ouvertes

```text
Q-OBS-01 AuditEvent doit-il être persisté dans la même DB que le core ?
Q-OBS-02 Faut-il une hash chain pour High Assurance ?
Q-OBS-03 Quel sampling par défaut ?
Q-OBS-04 Faut-il exposer Prometheus nativement ?
Q-OBS-05 Quel niveau de log par défaut ?
Q-OBS-06 Quels payloads runtime peut-on tracer ?
Q-OBS-07 Comment versionner le schéma AuditEvent ?
Q-OBS-08 Faut-il un IncidentBundle natif ?
Q-OBS-09 Quels SLOs officiels publier ?
Q-OBS-10 Quel comportement exact si AuditStore indisponible ?
Q-OBS-11 Faut-il supporter tail sampling de référence ?
Q-OBS-12 Comment exposer tenant-level observability sans cardinalité excessive ?
```

---

# 218. ADR induits

```text
ADR-OBS-001 OpenTelemetry as reference telemetry standard
ADR-OBS-002 CorrelationContext schema
ADR-OBS-003 AuditEvent model
ADR-OBS-004 Audit append semantics
ADR-OBS-005 Metric cardinality policy
ADR-OBS-006 Health vs readiness
ADR-OBS-007 Audit fail-closed behavior
ADR-OBS-008 Trace sampling policy
ADR-OBS-009 Telemetry payload redaction
ADR-OBS-010 Audit retention
ADR-OBS-011 High-assurance tamper evidence
ADR-OBS-012 Incident bundle format
```

---

# 219. Definition of Done

Le modèle Observability & Audit est mature lorsque :

1. OpenTelemetry est intégré comme standard de référence ;
2. les logs sont structurés ;
3. les métriques critiques sont exposées ;
4. les traces couvrent Run → Runtime → Effect → External System ;
5. le contexte de corrélation survit au takeover ;
6. AuditEvent possède un modèle stable ;
7. l’audit est append-oriented ;
8. les timelines Run/Effect/Approval/Lease sont reconstructibles ;
9. health et readiness sont séparés ;
10. les dashboards principaux existent ;
11. les alertes P0/P1 sont définies ;
12. chaque alerte critique possède un runbook ;
13. les secrets sont testés contre fuite télémétrique ;
14. la cardinalité métrique est contrôlée ;
15. le pipeline telemetry supporte les pannes ;
16. les comportements AuditStore outage sont définis ;
17. la qualification inclut multi-worker, takeover et traces distribuées ;
18. les invariants de safety sont visibles comme événements/métriques sans être réduits à de simples SLOs.

---

# 220. Résumé

L’observabilité de PyAgentsKit repose sur :

```text
LOGS
+
METRICS
+
TRACES
+
HEALTH
+
READINESS
```

L’audit repose sur :

```text
DURABLE AUDIT EVENTS
+
ACTOR / PRINCIPAL
+
OBJECT
+
DECISION
+
TIMESTAMP
+
REASON
+
CORRELATION
```

Les distinctions fondamentales sont :

```text
LOG != AUDIT
TRACE != AUDIT
METRIC != AUDIT
DOMAIN EVENT != AUDIT EVENT
HEALTH != READINESS
```

Le principe central reste :

> **L’observabilité permet de comprendre le système ; l’audit permet d’en établir la responsabilité. PyAgentsKit doit fournir les deux sans les confondre.**

Le document suivant naturel est :

```text
../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md
```
