# PyAgentsKit — Deployment & Operations

**Document :** `../operations/41_PYAGENTSKIT_DEPLOYMENT_AND_OPERATIONS.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Deployment Architecture & Operations Model  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md`
- `../operations/43_PYAGENTSKIT_PERFORMANCE_AND_CAPACITY_MODEL.md`
- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`

---

# 1. Objet

Ce document définit le **modèle de déploiement et d’exploitation** de PyAgentsKit V2.

Il formalise :

- les profils de déploiement ;
- la topologie des composants ;
- le rôle des workers ;
- la persistance et les dépendances d’infrastructure ;
- les mécanismes de health, liveness et readiness ;
- les procédures de démarrage et d’arrêt ;
- les rolling upgrades ;
- les migrations ;
- la haute disponibilité ;
- la sauvegarde et restauration ;
- les pratiques Kubernetes ;
- l’observabilité ;
- les opérations de maintenance ;
- les principes de sécurité opérationnelle ;
- les exigences de production.

Le principe directeur est :

> **PyAgentsKit doit pouvoir être déployé comme une reliability layer indépendante, sans transformer l’infrastructure en source implicite de vérité métier.**

---

# 2. Principes d’exploitation

Les opérations PyAgentsKit suivent les priorités :

```text
1. Safety
2. Durability
3. Recoverability
4. Operability
5. Availability
6. Performance
7. Cost optimization
```

---

# 3. OPS-INV-01

```text
No deployment topology may weaken Effect safety semantics.
```

---

# 4. OPS-INV-02

```text
No worker process is authoritative merely because it is alive.
```

---

# 5. OPS-INV-03

```text
Readiness means safe to accept work, not only process alive.
```

---

# 6. OPS-INV-04

```text
A database restore is not equivalent to safe application resume.
```

---

# 7. OPS-INV-05

```text
A rolling upgrade must not create two incompatible sources of truth.
```

---

# 8. OPS-INV-06

```text
Protected Effects must stop when authority cannot be proven.
```

---

# 9. Deployment Profiles

PyAgentsKit doit supporter plusieurs profils.

```text
DEV-LOCAL
DEV-DURABLE
SINGLE-NODE-PROD
DISTRIBUTED-PROD
HIGH-ASSURANCE
KUBERNETES
```

---

# 10. DEV-LOCAL

Objectif :

```text
developer productivity
```

Composants :

```text
Python process
Memory stores
optional filesystem artifacts
```

Garanties limitées :

```text
no multi-process ownership
no production durability
```

---

# 11. DEV-DURABLE

Composants :

```text
Python process
SQLite
filesystem/object store
```

Objectif :

```text
local durable development
crash/restart testing
```

---

# 12. SINGLE-NODE-PROD

Composants :

```text
1 worker/service process
PostgreSQL
object storage
external observability
```

Peut être adapté à petite production si :

```text
HA worker not required
downtime acceptable
```

---

# 13. DISTRIBUTED-PROD

Composants :

```text
N workers
PostgreSQL authoritative state
object storage
observability
optional broker
external identity provider
```

C’est le profil de référence V2 pour haute disponibilité applicative.

---

# 14. HIGH-ASSURANCE

Ajoute :

```text
strict fail-closed governance
mandatory audit
stronger secrets isolation
two-person manual intervention
additional redundancy
more conservative rollout
```

---

# 15. KUBERNETES

Kubernetes est un environnement de déploiement recommandé, mais :

```text
Kubernetes != PyAgentsKit ownership model
```

Pods et Deployments ne remplacent pas :

```text
Lease
FencingToken
Run ownership
```

---

# 16. Reference Logical Topology

```text
                ┌──────────────────────┐
                │      Clients         │
                │ CLI / API / UI       │
                └──────────┬───────────┘
                           │
                           ▼
                ┌──────────────────────┐
                │   API / Inbound      │
                │      Adapter         │
                └──────────┬───────────┘
                           │
                           ▼
              ┌───────────────────────────┐
              │   Application Services    │
              └───────────┬───────────────┘
                          │
          ┌───────────────┼────────────────┐
          ▼               ▼                ▼
      Workers         PostgreSQL       Object Store
       N pods         authority         Artifacts
          │
          ▼
   Runtime Adapters
          │
          ▼
 Agent Runtimes / Coding Agents
          │
          ▼
     Connectors
          │
          ▼
 External Systems
```

---

# 17. Component Roles

## API / Inbound Adapter

Responsable de :

```text
request validation
authentication context extraction
command/query dispatch
```

Pas responsable de :

```text
business truth
Effect execution authority
```

---

# 18. Worker

Responsable de :

```text
Run execution
runtime invocation
Effect orchestration
lease ownership
recovery
```

---

# 19. PostgreSQL

Autorité durable principale pour :

```text
Runs
Sessions
Conversations
Effects
Approvals
Leases
RuntimeInvocations
Audit metadata
Outbox/Inbox
```

---

# 20. Object Storage

Autorité blob pour :

```text
large artifacts
attachments
runtime outputs
```

---

# 21. Message Broker

Optionnel.

Peut transporter :

```text
work notifications
integration events
```

Mais :

```text
broker delivery != Run ownership
```

---

# 22. Observability Backend

Exemples :

```text
OpenTelemetry Collector
Prometheus
Grafana
Datadog
Langfuse/LangSmith if integrated
```

Pas source de vérité métier.

---

# 23. Identity Provider

Fournit :

```text
authentication
principal identity
claims
```

Ne fournit pas automatiquement :

```text
Approval authority
```

---

# 24. Secret Manager

Exemples :

```text
Environment in dev
Vault
AWS Secrets Manager
Azure Key Vault
Kubernetes Secrets with appropriate hardening
```

---

# 25. Process Types

Recommandation :

```text
api
worker
ops/admin
migration job
outbox publisher
optional reconciliation worker
```

Peuvent être regroupés au début mais doivent rester conceptuellement séparés.

---

# 26. API Process

Optimisé pour :

```text
short request/response
queries
commands
```

Ne devrait pas héberger des Runs longs par défaut.

---

# 27. Worker Process

Optimisé pour :

```text
long-lived execution
runtime calls
Effects
recovery
```

---

# 28. Migration Process

Doit être :

```text
explicit
one-shot
versioned
```

Pas exécuté implicitement par chaque worker en production.

---

# 29. Outbox Publisher

Peut être :

```text
dedicated process
or bounded worker subsystem
```

---

# 30. Reconciliation Worker

Peut traiter :

```text
UNKNOWN Effects
provider status polling
external drift
```

avec bounded concurrency.

---

# 31. Worker Identity

Chaque worker doit posséder un identifiant unique :

```text
worker_id
```

et idéalement :

```text
instance_id
startup_time
deployment_version
```

---

# 32. Worker Registry

Le WorkerRegistry peut enregistrer :

```text
worker_id
status
version
capabilities
heartbeat
started_at
```

---

# 33. Worker Lifecycle

```text
STARTING
  ↓
READY
  ↓
DRAINING
  ↓
STOPPING
  ↓
STOPPED
```

Option :

```text
DEGRADED
```

---

# 34. STARTING

Pendant cette phase :

```text
load config
verify dependencies
verify schema
register worker
```

Pas d’admission de Run.

---

# 35. READY

Le worker peut :

```text
admit
acquire leases
execute Runs
```

---

# 36. DRAINING

Le worker :

```text
stops new admissions
continues bounded active work
renews leases as needed
```

---

# 37. STOPPING

Le worker termine les tâches d’arrêt.

---

# 38. Graceful Shutdown

Séquence recommandée :

```text
1. set DRAINING
2. stop new admissions
3. stop pulling new work
4. allow bounded in-flight completion
5. persist safe checkpoints
6. release leases when appropriate
7. flush audit/outbox buffers
8. close runtime adapters
9. close DB pools
10. exit
```

---

# 39. Shutdown Timeout

Doit être borné.

Une terminaison forcée reste un scénario normal de recovery.

---

# 40. SIGTERM

Doit déclencher :

```text
graceful drain
```

---

# 41. SIGKILL

Impossible à intercepter.

Recovery doit fonctionner sans dépendre du shutdown gracieux.

---

# 42. SIGSTOP

Important scénario de qualification.

Peut créer :

```text
stale worker
```

après expiration du Lease.

---

# 43. Health Model

Séparer :

```text
liveness
readiness
dependency health
protected-effects readiness
```

---

# 44. Liveness

Question :

```text
Is this process alive?
```

Ne doit pas dépendre de toutes les dependencies.

---

# 45. Readiness

Question :

```text
Can this instance safely accept new work?
```

---

# 46. Readiness Preconditions

Typiquement :

```text
config valid
schema compatible
PostgreSQL reachable
worker not draining
critical migrations complete
```

---

# 47. Protected Effects Readiness

Question :

```text
Can this instance safely execute Protected Effects?
```

Peut devenir false indépendamment de read-only capability.

---

# 48. Health Endpoint Proposal

```text
/health/live
/health/ready
/health/dependencies
/health/effects
```

---

# 49. Dependency Health

Expose état de :

```text
PostgreSQL
Object Storage
Runtime Providers
Connectors
Identity Provider
Observability
```

sans exposer secrets.

---

# 50. Startup Probe

Sous Kubernetes :

```text
startupProbe
```

peut protéger les applications lentes au démarrage.

---

# 51. Kubernetes Deployment Pattern

```text
Deployment: pyagentskit-api
Deployment: pyagentskit-worker
Job: pyagentskit-migrate
Deployment: pyagentskit-outbox (optional)
```

---

# 52. Pod Anti-Affinity

Pour HA :

```text
avoid all workers on same node
```

---

# 53. PodDisruptionBudget

Peut protéger un minimum de workers disponibles.

---

# 54. PDB Limitation

PDB ne protège pas contre :

```text
node crash
SIGKILL
application deadlock
```

---

# 55. RollingUpdate

API et workers peuvent utiliser :

```text
RollingUpdate
```

si versions sont compatibles.

---

# 56. maxUnavailable

Doit préserver capacité suffisante.

---

# 57. maxSurge

Permet nouvelle capacité avant suppression ancienne.

---

# 58. Version Skew

Le système doit définir la fenêtre supportée :

```text
N and N+1
```

si rolling upgrade sans arrêt global.

---

# 59. Version Compatibility

Pendant rolling upgrade :

```text
old worker
new worker
same DB
```

doivent être compatibles avec :

```text
schema
public contracts
event envelopes
```

---

# 60. Expand/Contract Migrations

Pattern préféré :

```text
EXPAND
BACKFILL
SWITCH
CONTRACT
```

---

# 61. Expand

Ajouter schema compatible avec ancienne et nouvelle version.

---

# 62. Backfill

Migrer données progressivement.

---

# 63. Switch

Changer source d’écriture/lecture.

---

# 64. Contract

Supprimer ancien schema seulement après retrait anciennes versions.

---

# 65. Migration Job

Doit vérifier :

```text
current schema version
target version
migration lock
preconditions
```

---

# 66. Migration Lock

Une seule migration schema active à la fois.

---

# 67. Worker Readiness and Schema

Un worker doit refuser readiness si schema incompatible.

---

# 68. Deployment Order

Pattern général :

```text
1. apply backward-compatible DB expand
2. deploy new code
3. backfill
4. switch feature/source
5. retire old code
6. contract later
```

---

# 69. Breaking Domain Migration

Exige plan explicite.

Pas de migration automatique “best effort”.

---

# 70. V1 → V2 Deployment

Suit le document 30.

Stratégie :

```text
strangler
dual-read where controlled
single source of truth per phase
```

---

# 71. Source of Truth

À tout instant, chaque donnée critique doit avoir :

```text
one declared authoritative writer
```

---

# 72. Feature Flags

Peuvent aider le cutover.

Mais :

```text
feature flag != authority model
```

---

# 73. Deployment Environments

Minimum :

```text
local
test
staging
production
```

---

# 74. Staging

Doit être suffisamment proche de production sur :

```text
PostgreSQL
worker count
network behavior
runtime adapters
connectors
```

---

# 75. Production-Like Qualification

Les garanties distribuées ne peuvent pas être validées uniquement avec :

```text
unit tests
in-memory stores
```

---

# 76. Configuration Model

Configuration via :

```text
environment variables
config file
secret references
```

avec validation au démarrage.

---

# 77. Configuration Principles

```text
explicit
typed
validated
immutable during critical execution where possible
```

---

# 78. Dynamic Configuration

Possible pour :

```text
quotas
feature flags
policy refs
```

avec versioning/audit.

---

# 79. Secrets

Ne jamais stocker :

```text
resolved secrets
```

dans Run, Audit, Message ou Checkpoint.

---

# 80. Secret Rotation

Adapters doivent supporter rotation sans restart lorsque possible.

---

# 81. Environment Separation

Prod secrets et credentials ne doivent jamais être réutilisés en staging.

---

# 82. Network Architecture

Recommandations :

```text
private DB network
TLS
restricted outbound where possible
egress controls
```

---

# 83. Egress

Coding agents et connectors peuvent nécessiter outbound internet.

Limiter par :

```text
allowlists
proxy
network policy
```

si environnement sensible.

---

# 84. Kubernetes NetworkPolicy

Peut limiter :

```text
DB
object storage
provider endpoints
```

---

# 85. TLS

Requis pour :

```text
external APIs
database where network not fully trusted
```

---

# 86. mTLS

Option High Assurance pour certains services internes.

---

# 87. Service Accounts

Chaque composant devrait avoir :

```text
least privilege identity
```

---

# 88. API Identity

N’a pas forcément besoin des mêmes permissions que Worker.

---

# 89. Worker Identity

Peut avoir accès à :

```text
runtime credentials
connector credentials
```

selon scope.

---

# 90. Migration Identity

Doit avoir DDL privileges.

Ne pas donner ces privileges aux workers si possible.

---

# 91. Read-Only Ops Identity

Pour diagnostics :

```text
read-only
```

préférable.

---

# 92. Database Roles

Candidats :

```text
pyagentskit_runtime
pyagentskit_migrator
pyagentskit_readonly
```

---

# 93. PostgreSQL Deployment

Préférer :

```text
managed PostgreSQL
or mature HA deployment
```

plutôt qu’un cluster custom non maîtrisé.

---

# 94. PostgreSQL Requirements

```text
durable storage
backup
PITR
monitoring
connection limits known
primary consistency for critical reads
```

---

# 95. Read Replicas

Peuvent servir :

```text
non-critical read models
analytics
```

---

# 96. Never Use Replica for Safety-Critical Decisions

Interdit pour :

```text
Lease
Approval
Effect status
Fencing
```

si replication lag possible.

---

# 97. DB High Availability

Failover doit être testé.

---

# 98. Failover Consequence

Une transaction en vol peut devenir :

```text
unknown commit outcome
```

---

# 99. Failover Recovery

Application doit :

```text
reconnect
re-read durable identity
```

---

# 100. Backup Strategy

Minimum :

```text
regular full backups
WAL/PITR
backup verification
restore tests
```

---

# 101. Backup Is Not Enough

Un backup inutilisé/testé n’est pas une garantie.

---

# 102. Restore Drills

Exécuter périodiquement.

---

# 103. Restore Safety

Après restore :

```text
workers remain disabled
```

jusqu’au safety gate.

---

# 104. Restore Gate

Vérifier :

```text
schema
fencing monotonicity
Effects after restore point
external system state
Approvals
```

---

# 105. Disaster Recovery

Définir :

```text
RPO
RTO
```

par profil.

---

# 106. RPO

Recovery Point Objective.

---

# 107. RTO

Recovery Time Objective.

---

# 108. High Assurance RPO

Peut viser proche de zéro avec WAL/PITR.

Mais external Effects imposent reconciliation.

---

# 109. Cross-Region DR

Non-goal initial V2 sauf besoin explicite.

---

# 110. Object Storage Deployment

Doit supporter :

```text
durability
versioning if useful
lifecycle rules
encryption
```

---

# 111. Artifact Metadata

Reste dans DB.

Blob dans object storage.

---

# 112. Artifact Retention

Définir par :

```text
tenant
artifact type
compliance
```

---

# 113. Garbage Collection

Supprimer orphans avec job contrôlé.

---

# 114. Message Broker Deployment

Optionnel.

---

# 115. Broker Requirements

Si utilisé :

```text
at-least-once expected
redelivery tolerated
dedup via Inbox
```

---

# 116. Do Not Depend on Exactly-Once Broker

PyAgentsKit garde ses propres sémantiques.

---

# 117. Runtime Adapter Deployment

Certains runtimes :

```text
in-process
local subprocess
remote service
cloud API
```

---

# 118. In-Process Runtime

Simple mais partage :

```text
memory
failure domain
```

---

# 119. Subprocess Runtime

Ajoute isolation partielle.

---

# 120. Remote Runtime

Ajoute réseau et external failure semantics.

---

# 121. Runtime Isolation

Pour coding agents, envisager :

```text
container
sandbox
VM
```

---

# 122. Workspace Isolation

Chaque Run/Invocation sensible peut avoir :

```text
dedicated workspace
```

---

# 123. Workspace Cleanup

Après terminal state selon policy.

---

# 124. Workspace Persistence

Peut être nécessaire pour recovery.

---

# 125. Coding Agent Deployment

Séparer éventuellement worker pool :

```text
coding-workers
```

des :

```text
general-workers
```

---

# 126. Why Separate

Coding workloads peuvent consommer :

```text
CPU
RAM
disk
subprocesses
network
```

---

# 127. Worker Pools

Candidats :

```text
general
coding
recovery
reconciliation
```

---

# 128. Pool Routing

Basé sur :

```text
runtime capability
workload class
risk class
resource requirements
```

---

# 129. Autoscaling

Peut utiliser :

```text
queue backlog
ready Runs
worker utilization
CPU
```

---

# 130. HPA

Sous Kubernetes :

```text
HorizontalPodAutoscaler
```

possible.

---

# 131. HPA Caveat

CPU seul insuffisant pour I/O-heavy workloads.

---

# 132. KEDA

Peut être utile pour event/backlog-driven scaling.

Non obligatoire.

---

# 133. Scale-Out Safety

Nouveaux workers acquièrent leases normalement.

---

# 134. Scale-In Safety

Workers doivent :

```text
drain
```

avant termination lorsque possible.

---

# 135. PreStop Hook

Kubernetes :

```text
preStop
```

peut déclencher drain.

---

# 136. terminationGracePeriodSeconds

Doit être aligné avec :

```text
graceful shutdown timeout
```

---

# 137. But Safety Must Not Depend on Grace Period

SIGKILL recovery reste obligatoire.

---

# 138. Scheduling

Pod resources :

```text
requests
limits
```

doivent être définis.

---

# 139. CPU Requests

Évitent sur-scheduling.

---

# 140. Memory Limits

OOMKill est récupérable mais doit être minimisé.

---

# 141. Ephemeral Storage Limits

Important pour coding agents.

---

# 142. Dedicated Nodes

Option pour :

```text
high-risk coding workloads
GPU workloads
```

si nécessaire.

---

# 143. Taints/Tolerations

Peuvent isoler pools spécialisés.

---

# 144. Node Failure

Leases expirent.

Autres workers prennent la suite.

---

# 145. Control Plane Failure

Kubernetes control plane failure ne doit pas immédiatement compromettre Runs déjà actifs si pods continuent.

---

# 146. Database Failure Still Critical

Parce que durable authority vit dans PostgreSQL.

---

# 147. Observability Architecture

```text
Application
→ OpenTelemetry SDK
→ Collector
→ backend(s)
```

---

# 148. Metrics

Doivent inclure :

```text
Runs
Effects
Leases
Recovery
DB
Workers
Outbox
Approvals
```

---

# 149. Logs

Structured logs.

Inclure :

```text
run_id
effect_id
worker_id
correlation_id
```

quand approprié.

---

# 150. Log Redaction

Ne jamais loguer :

```text
secrets
raw access tokens
sensitive payloads by default
```

---

# 151. Traces

Tracer :

```text
Run command
RuntimeInvocation
Effect execution
Reconciliation
Approval flow
```

---

# 152. Audit

Séparé des traces.

---

# 153. Alerting

Alertes critiques :

```text
fencing errors
UNKNOWN spike
lease renewal danger
DB unavailable
cross-tenant violation
audit failure in High Assurance
```

---

# 154. Deployment Dashboard

Afficher :

```text
version
worker count
ready workers
draining workers
active Runs
lease health
DB health
```

---

# 155. Version Metadata

Chaque worker expose :

```text
package version
git SHA
build id
schema compatibility
```

---

# 156. Build Reproducibility

Release doit être :

```text
reproducible
signed if possible
```

---

# 157. Container Image

Recommandation :

```text
small base image
non-root user
pinned dependencies
```

---

# 158. Container Security

```text
read-only root filesystem where possible
drop capabilities
no privileged mode
```

---

# 159. SBOM

Recommandé pour releases production.

---

# 160. Dependency Scanning

Automatisé en CI.

---

# 161. Image Scanning

Recommandé.

---

# 162. Supply Chain

Signer artifacts/packages/images selon maturité.

---

# 163. Release Channels

```text
alpha
beta
rc
stable
```

---

# 164. Deployment Promotion

```text
dev
→ test
→ staging
→ production
```

---

# 165. Canary Deployment

Très utile pour runtime/connector changes.

---

# 166. Canary Scope

Limiter :

```text
tenant
workload class
percentage
```

---

# 167. Canary Safety

Les deux versions doivent respecter mêmes invariants DB.

---

# 168. Blue/Green

Possible pour API.

Plus délicat pour workers distribués si ownership partagé.

---

# 169. Blue/Green Workers

Possible si :

```text
shared compatible DB
leases arbitrate authority
```

---

# 170. Rollback

Rollback code est possible si schema compatible.

---

# 171. Rollback Limitation

Si nouvelle version a produit :

```text
irreversible external Effects
```

le rollback ne réverse pas le monde externe.

---

# 172. Forward Fix

Souvent préférable après changement ayant produit Effects.

---

# 173. Deployment Freeze

Avant opérations sensibles :

```text
migration
restore
major incident
```

peut être nécessaire.

---

# 174. Maintenance Mode

Modes :

```text
read-only
no-new-runs
no-protected-effects
full maintenance
```

---

# 175. No-New-Runs

Runs existants peuvent continuer selon policy.

---

# 176. No-Protected-Effects

Permet diagnostics et reads.

---

# 177. Maintenance Endpoint/Flag

Doit être durable et audité si utilisé en production.

---

# 178. Deployment Configuration Drift

Détecter différences entre :

```text
declared
effective
```

configuration.

---

# 179. GitOps

Compatible et recommandé dans Kubernetes.

Mais GitOps ne remplace pas migration/run safety.

---

# 180. Helm/Kustomize

Peuvent être utilisés.

Pas partie du core sémantique.

---

# 181. IaC

Terraform/Pulumi/etc.

Peuvent déployer infrastructure.

---

# 182. Infrastructure Changes

À traiter comme changements à risque.

---

# 183. Runtime Provider Credentials

Scope minimal.

---

# 184. Connector Credentials

Idéalement :

```text
per connector
per tenant
or per environment
```

selon besoin.

---

# 185. Multi-Tenant Deployment

Deux grands modèles :

```text
shared infrastructure
isolated infrastructure
```

---

# 186. Shared Infrastructure

Besoin fort de :

```text
tenant filters
authorization
quotas
audit
```

---

# 187. Isolated Infrastructure

Plus coûteux mais réduit blast radius.

---

# 188. Hybrid Isolation

Exemple :

```text
shared API
dedicated worker pools
dedicated DB per critical tenant
```

---

# 189. Tenant Routing

Doit préserver :

```text
TenantId
SecurityContext
```

---

# 190. Tenant-Aware Secrets

Secrets ne doivent pas fuiter entre tenants.

---

# 191. Tenant-Aware Artifacts

Object paths/buckets peuvent inclure tenant scope.

---

# 192. Data Residency

Peut imposer région spécifique.

---

# 193. Region Configuration

Runtime/connector endpoints peuvent varier par région.

---

# 194. Multi-Region Active/Active

Deferred.

Très complexe pour :

```text
fencing
leases
external Effects
```

---

# 195. Multi-Region Active/Passive

Possible futur DR profile.

---

# 196. Backup Encryption

Recommandée.

---

# 197. Key Management

Délégué à provider/KMS.

---

# 198. Database Encryption

At-rest + TLS in-transit.

---

# 199. Object Encryption

At-rest provider-side.

---

# 200. Key Rotation

Doit être planifiée.

---

# 201. Operational Access

Les opérateurs ne doivent pas avoir par défaut :

```text
full DB superuser
all connector secrets
```

---

# 202. Break-Glass Access

Peut exister pour urgence.

Doit être :

```text
time-limited
audited
reviewed
```

---

# 203. Admin API

Séparée ou fortement protégée.

---

# 204. Dangerous Operations

Exemples :

```text
force takeover
manual Effect resolution
unfreeze Effects
migration cutover
```

---

# 205. Two-Person Control

Recommandé en High Assurance.

---

# 206. Operational Runbooks

Voir document 42.

---

# 207. Deployment Runbook — Fresh Install

Séquence :

```text
1. provision PostgreSQL
2. provision object storage
3. configure secrets
4. apply schema
5. deploy API
6. deploy workers
7. verify health
8. run smoke test
9. enable traffic
```

---

# 208. Fresh Install Smoke Test

Inclure :

```text
CreateRun
simple RuntimeInvocation
Effect safe mock
Audit
Lease acquire/release
```

---

# 209. Deployment Runbook — Upgrade

```text
1. confirm backup
2. verify compatibility
3. apply expand migration
4. deploy canary
5. validate
6. rollout
7. backfill
8. switch
9. monitor
10. contract later
```

---

# 210. Deployment Runbook — Rollback

Avant rollback :

```text
check external Effects produced by new version
check schema compatibility
```

---

# 211. Deployment Runbook — Worker Pool Resize

Scale out :

```text
increase replicas
observe lease distribution
```

Scale in :

```text
drain selected workers
then terminate
```

---

# 212. Deployment Runbook — Connector Disable

```text
set scoped maintenance/kill switch
wait in-flight decision
preserve UNKNOWN state
```

---

# 213. Deployment Runbook — Runtime Adapter Disable

Prevent new invocations.

Existing Runs become WAITING/recovery-dependent.

---

# 214. Deployment Runbook — Database Failover

```text
observe connection loss
stop unsafe progress
reconnect primary
re-read authoritative state
resume bounded recovery
```

---

# 215. Deployment Runbook — Object Storage Outage

Allow metadata-only operations if safe.

Block artifact-dependent Effects.

---

# 216. Deployment Runbook — Broker Outage

Outbox accumulates.

Core domain may continue if no hard broker dependency.

---

# 217. Deployment Runbook — Observability Outage

Core may continue if Audit remains available.

---

# 218. Deployment Runbook — IdP Outage

New sensitive actions may fail closed.

---

# 219. DR Runbook

Sequence :

```text
declare disaster
freeze writes if possible
restore DB
restore/configure object storage
verify schema
run restore safety gate
reconcile external Effects
start workers disabled
enable reads
enable safe execution gradually
```

---

# 220. Operational Data Retention

Définir pour :

```text
Audit
Messages
Artifacts
RuntimeEvents
Outbox/Inbox
```

---

# 221. Purge

Doit respecter :

```text
referential integrity
audit requirements
legal retention
```

---

# 222. Archive

Peut déplacer old audit/artifact data vers colder storage.

---

# 223. Database Maintenance

Inclut :

```text
vacuum
analyze
index health
connection review
storage growth
```

---

# 224. Schema Maintenance

Toutes modifications via migration versionnée.

---

# 225. Manual DDL

Éviter en production hors incident contrôlé.

---

# 226. Operational Metrics — Deployment

```text
workers_total
workers_ready
workers_draining
deployment_version_count
```

---

# 227. Operational Metrics — Health

```text
readiness_failures_total
dependency_health
```

---

# 228. Operational Metrics — Coordination

```text
leases_active
lease_renew_failures
lease_takeovers
stale_fencing_rejections
```

---

# 229. Operational Metrics — Recovery

```text
recoverable_runs_pending
recovery_lag_seconds
```

---

# 230. Operational Metrics — Migration

```text
schema_version
migration_status
backfill_progress
```

---

# 231. Operational SLOs

Candidats :

```text
worker readiness availability
protected effects readiness
DB availability
outbox lag
recovery detection
```

---

# 232. Error Budget

Peut être défini pour :

```text
API availability
worker availability
```

Mais safety violations ont budget :

```text
zero
```

---

# 233. Zero-Budget Events

```text
duplicate irreversible Effect due to framework bug
stale fencing accepted
cross-tenant authorization leak
fabricated Approval
```

---

# 234. Capacity Planning

Voir document 43.

---

# 235. Deployment Sizing Inputs

```text
active Runs
Effects/sec
active leases
artifact throughput
runtime concurrency
```

---

# 236. Minimum HA Topology

Conceptuellement :

```text
2+ workers
HA PostgreSQL
durable object storage
```

---

# 237. Why 2+ Workers

Permet :

```text
real takeover
rolling upgrades
worker maintenance
```

---

# 238. Single Worker Limitation

Ne valide pas :

```text
distributed recovery
```

---

# 239. Production Qualification

Le deployment model doit être testé avec :

```text
SIGTERM
SIGKILL
SIGSTOP
DB outage
DB failover
worker replacement
rolling upgrade
```

---

# 240. Chaos Tests

Fault injection contrôlée.

---

# 241. Chaos Safety

Ne jamais lancer sur production sans garde-fous explicites.

---

# 242. Staging Chaos

Recommandé.

---

# 243. Worker Handover Test

```text
Worker A owns Run
Worker A stopped
Lease expires
Worker B takes over
No Effect replay
```

---

# 244. Rolling Upgrade Test

Versions N et N+1 coexistent.

---

# 245. Restore Test

PITR puis :

```text
no immediate workers
reconciliation
safe resume
```

---

# 246. Deployment Security Test

Vérifier :

```text
non-root
secret redaction
network policies
least privilege DB
```

---

# 247. Dependency Failure Matrix

| Dependency | Can Reads Continue? | Can New Runs Start? | Can Protected Effects Execute? |
|---|---:|---:|---:|
| PostgreSQL down | limited/no | no | no |
| Object Store down | yes | often | only if no artifact dependency |
| Broker down | yes | often | yes, if broker optional |
| OTel down | yes | yes | yes |
| Audit critical store down | profile dependent | maybe | High Assurance: no |
| IdP down | existing context only | limited | sensitive: no |
| Runtime provider down | yes | no affected runtime | no runtime progress |
| Connector down | yes | yes | no affected Effect |

---

# 248. Operational Degradation Modes

```text
FULL
DEGRADED
READ_ONLY
NO_NEW_RUNS
NO_PROTECTED_EFFECTS
MAINTENANCE
```

---

# 249. Mode Transitions

Doivent être :

```text
explicit
audited
observable
```

---

# 250. Operational Controls

Candidats :

```text
freeze connector
freeze Effect class
drain worker
pause tenant
resume tenant
trigger recovery
trigger reconciliation
```

---

# 251. Ops UI / CLI

Pas obligatoire dans core initial, mais interfaces doivent être prévues.

---

# 252. CLI Example

```text
pyagentskit ops workers list
pyagentskit ops worker drain <id>
pyagentskit ops effects freeze --connector github
pyagentskit ops run inspect <run_id>
```

---

# 253. Safe Defaults

En absence de config explicite :

```text
fail safe
```

pour opérations à haut risque.

---

# 254. Operational Documentation

Chaque production setup doit inclure :

```text
architecture diagram
dependency list
secret ownership
backup policy
restore procedure
scaling procedure
incident contacts
```

---

# 255. Deployment Manifest Ownership

Les manifests sont versionnés avec code ou infra repo.

---

# 256. Environment Promotion

Éviter mutations manuelles non versionnées.

---

# 257. Drift Detection

Comparer :

```text
Git desired state
runtime actual state
```

si GitOps utilisé.

---

# 258. Service Discovery

Utiliser primitives plateforme.

Ne pas construire un service registry custom sauf besoin.

---

# 259. DNS

Doit être monitored indirectly via dependency failures.

---

# 260. Time

Coordination s’appuie sur DB time pour leases.

---

# 261. NTP

Workers doivent néanmoins garder clocks raisonnables pour logs/traces.

---

# 262. Locale

Timestamps stockés UTC.

---

# 263. Time Zones

Conversion uniquement aux interfaces utilisateur.

---

# 264. Deployment Names

Convention :

```text
pyagentskit-api
pyagentskit-worker
pyagentskit-migrate
pyagentskit-outbox
```

---

# 265. Labels

Sous Kubernetes :

```text
app
component
version
environment
```

---

# 266. Runtime Adapter Version

Doit être identifiable dans diagnostics.

---

# 267. Connector Version

Même règle.

---

# 268. Configuration Version

Policy/config changes importantes doivent être traçables.

---

# 269. Release Artifact

Doit inclure :

```text
wheel
source distribution
checksums
release notes
migration notes
```

---

# 270. Container Artifact

Si fourni :

```text
immutable tag/digest
```

---

# 271. Never Deploy `latest` in Production

Préférer version/digest immuable.

---

# 272. Python Runtime

Version minimale contrôlée par package.

---

# 273. Dependency Pinning

Prod builds doivent être reproductibles.

---

# 274. OS Packages

Minimiser.

---

# 275. Optional Dependencies

Runtime/connector SDKs restent extras quand possible.

---

# 276. Image Variants

Éviter trop de variantes prématurément.

---

# 277. Startup Migration Anti-Pattern

Ne pas lancer automatiquement DDL concurrent depuis tous les workers.

---

# 278. Long Init Anti-Pattern

Un pod ne doit pas masquer une migration longue comme simple startup.

---

# 279. Shared Local Filesystem Anti-Pattern

Ne pas supposer un filesystem local partagé entre workers.

---

# 280. In-Memory Authority Anti-Pattern

Interdit en distributed prod.

---

# 281. Sticky Session Dependency Anti-Pattern

Run recovery doit pouvoir changer de worker.

---

# 282. Broker-as-Authority Anti-Pattern

Déjà interdit.

---

# 283. Kubernetes Lease as Business Lease Anti-Pattern

Les objets Lease Kubernetes ne remplacent pas nécessairement la sémantique PyAgentsKit.

---

# 284. Replica Read for Approval Anti-Pattern

Interdit.

---

# 285. Deployment Rollback as Business Rollback Anti-Pattern

Un rollback logiciel ne compense pas les external Effects.

---

# 286. Autoscale Without Quota Anti-Pattern

Peut déplacer la saturation vers provider/DB.

---

# 287. Unbounded Worker Startup Anti-Pattern

Peut créer thundering herd.

---

# 288. Startup Jitter

Peut réduire contention.

---

# 289. Reconciliation Scheduling

Doit être bounded et observable.

---

# 290. Background Maintenance

Jobs possibles :

```text
approval expiry
orphan artifact cleanup
outbox cleanup
reconciliation
retention
```

---

# 291. Scheduler

Peut être :

```text
Kubernetes CronJob
external scheduler
internal bounded background loop
```

---

# 292. Do Not Build General Scheduler

Le besoin opérationnel reste limité.

---

# 293. Data Migration Jobs

Doivent être :

```text
restartable
idempotent
checkpointed
```

---

# 294. Backfill Metrics

```text
rows_total
rows_done
errors
ETA
```

---

# 295. Backfill Throttling

Pour protéger production.

---

# 296. Backfill Pause

Doit être possible.

---

# 297. Maintenance Windows

Option selon criticité.

---

# 298. Zero-Downtime Goal

Souhaitable mais pas absolu si safety exige maintenance explicite.

---

# 299. Deployment Maturity Levels

```text
DEP-L0 local only
DEP-L1 single node durable
DEP-L2 distributed staging
DEP-L3 HA production
DEP-L4 production qualified
```

---

# 300. DEP-L4 Requirements

```text
tested failover
tested rolling upgrade
tested restore
tested worker takeover
tested kill switch
documented capacity
documented runbooks
```

---

# 301. Environment Matrix

| Capability | Local | Staging | Production |
|---|---:|---:|---:|
| Memory | ✓ | optional | no authority |
| SQLite | ✓ | optional | limited |
| PostgreSQL | optional | ✓ | ✓ |
| Multi-worker | optional | ✓ | ✓ |
| Object Store | optional | ✓ | ✓ |
| OTel | optional | ✓ | ✓ |
| Real connectors | sandbox | sandbox/limited | ✓ |
| Backup/PITR | no | recommended | ✓ |

---

# 302. High Assurance Matrix

Ajoute :

```text
strict audit
two-person ops
network restrictions
stronger secret isolation
longer evidence retention
```

---

# 303. Disaster Matrix

| Event | Expected System Behavior |
|---|---|
| Worker loss | takeover after lease expiry |
| Node loss | pods rescheduled, leases recovered |
| DB outage | protected progress stops |
| Object store outage | artifact-dependent work waits |
| Runtime outage | affected Runs wait |
| Connector outage | affected Effects wait/UNKNOWN |
| Region outage | DR procedure |
| Restore | safety gate before resume |

---

# 304. Operational RACI

Exemple :

```text
Platform Team
- cluster
- DB
- network
- observability

PyAgentsKit Team
- application
- migrations
- adapters
- runbooks

Security
- IAM
- secrets
- policy
- incident support
```

---

# 305. Ownership Must Be Explicit

Chaque dependency/service doit avoir un owner.

---

# 306. Pager Ownership

Alerts critiques doivent avoir une destination claire.

---

# 307. On-Call Readiness

Avant production :

```text
access
runbooks
dashboards
admin controls
```

doivent fonctionner.

---

# 308. Operational Review Before Release

Checklist :

```text
[ ] migrations reviewed
[ ] rollback/forward-fix plan
[ ] alerts updated
[ ] runbooks updated
[ ] capacity checked
[ ] dependency versions checked
[ ] feature flags documented
```

---

# 309. Production Change Categories

```text
low risk
medium risk
high risk
emergency
```

---

# 310. High-Risk Changes

Exemples :

```text
lease semantics
Effect state machine
Approval semantics
DB schema critical path
connector retries
```

---

# 311. High-Risk Deployment

Préférer :

```text
canary
small scope
extended observation
```

---

# 312. Emergency Patch

Doit quand même :

```text
build
test
version
audit
```

même si processus raccourci.

---

# 313. Deployment Evidence

Conserver :

```text
release version
migration version
deployment time
operator/automation identity
```

---

# 314. Security Boundary

Workers sont une zone de haute confiance relative.

---

# 315. Runtime Boundary

Un runtime externe n’est pas autorité de governance.

---

# 316. Connector Boundary

Un connector externe peut être compromis.

Le core doit valider :

```text
policy
scope
fencing
idempotency
```

avant appel.

---

# 317. Operations Boundary

Un opérateur humain ne doit pas contourner invariants sans trace.

---

# 318. Deployment Acceptance Criteria

Le modèle de déploiement est conforme si :

1. les profils local/distribué sont documentés ;
2. API et workers sont séparables ;
3. worker identity est explicite ;
4. liveness/readiness sont distincts ;
5. protected-effects readiness existe conceptuellement ;
6. graceful shutdown est défini ;
7. SIGKILL reste récupérable ;
8. PostgreSQL est l’autorité durable en distributed prod ;
9. les reads safety-critical évitent les replicas laggées ;
10. les migrations suivent expand/contract ;
11. rolling upgrade et version skew sont définis ;
12. Kubernetes n’est pas utilisé comme remplacement des Leases métier ;
13. secrets et identities suivent least privilege ;
14. backup/PITR et restore gate sont définis ;
15. maintenance/degraded modes sont explicites ;
16. object storage ne porte pas la vérité métier ;
17. observability est séparée de l’Audit ;
18. scaling respecte DB/provider bottlenecks ;
19. les manifests sont versionnés ;
20. les runbooks opérationnels existent.

---

# 319. Definition of Done

`../operations/41_PYAGENTSKIT_DEPLOYMENT_AND_OPERATIONS.md` est considéré mature lorsque :

1. un déploiement local reproductible existe ;
2. un déploiement PostgreSQL distribué existe ;
3. un exemple Kubernetes existe ;
4. health endpoints sont implémentés ;
5. graceful shutdown est implémenté ;
6. worker drain est testé ;
7. rolling upgrade N/N+1 est qualifié ;
8. migrations expand/contract sont démontrées ;
9. PITR + restore safety gate est testé ;
10. backup restore drill est automatisable ;
11. HA worker takeover est démontré ;
12. les métriques opératoires sont exposées ;
13. les alertes critiques existent ;
14. les secrets ne sont jamais persistés en clair dans le domain state ;
15. les profils de dégradation sont implémentables ;
16. le kill switch est exploitable ;
17. les manifests appliquent non-root/least privilege ;
18. le deployment model est couvert par les runbooks du document 42 ;
19. le capacity model du document 43 est appliqué ;
20. le déploiement final passe les gates du document 40.

---

# 320. Résumé

Le modèle opérationnel cible est :

```text
                USERS / SYSTEMS
                       │
                       ▼
                 API / COMMANDS
                       │
                       ▼
        ┌──────────────────────────┐
        │     WORKER FLEET         │
        │                          │
        │ Worker A  Worker B  ...  │
        └────────────┬─────────────┘
                     │
               Lease / Fencing
                     │
                     ▼
              ┌──────────────┐
              │ PostgreSQL   │
              │ Authority    │
              └──────┬───────┘
                     │
          ┌──────────┼──────────┐
          ▼          ▼          ▼
      Runtime     Connectors   Artifacts
      Adapters      APIs       Storage
          │
          ▼
      External World
```

Le comportement attendu en production est :

```text
deploy
→ become ready
→ acquire authority
→ execute
→ survive worker loss
→ drain cleanly
→ upgrade compatibly
→ restore cautiously
→ reconcile external reality
```

La règle fondamentale est :

> **PyAgentsKit doit pouvoir perdre un process, un pod ou un nœud sans perdre son autorité durable ; et il doit pouvoir perdre sa base ou restaurer un snapshot sans prétendre que le monde extérieur a, lui aussi, été restauré.**
