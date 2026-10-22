# PyAgentsKit — Architecture cible

**Document :** `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`  
**Version :** 1.0  
**Date :** 19 octobre 2026  
**Statut :** Architecture logique et technique cible  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/02_PYAGENTSKIT_PARTIES_PRENANTES_ET_CAS_D_USAGE.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../architecture/08_PYAGENTSKIT_ERD.md`
- `../domain/PYAGENTSKIT_MODELE_CONCEPTUEL_DU_DOMAINE.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`

---

# 1. Objet du document

Ce document décrit l’**architecture cible** de PyAgentsKit.

Il traduit les besoins fonctionnels, non fonctionnels et le modèle métier en une architecture cohérente permettant :

- l’exécution durable de runtimes agentiques ;
- la persistence des runs, sessions, conversations et effets ;
- le contrôle humain ;
- la reprise après panne ;
- la coordination multi-worker ;
- le fencing ;
- l’intégration de runtimes généralistes et coding agents ;
- l’observabilité ;
- l’audit ;
- la sécurité ;
- l’extensibilité.

La finalité de l’architecture est :

> **Permettre à un runtime agentique d’agir sur des systèmes réels avec des garanties explicites de cohérence, de durabilité, de contrôle et de reprise.**

---

# 2. Vision architecturale

PyAgentsKit doit être conçu comme une **Agent Reliability Layer** indépendante du runtime agentique.

Vue macro :

```text
┌───────────────────────────────────────────┐
│          Applications / Interfaces        │
│ API / CLI / UI / Scheduler / Webhooks     │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│        Runtime Integration Layer          │
│ AgentRuntimeAdapter                       │
│ LangGraph / OpenAI / Claude / Codex ...   │
└─────────────────────┬─────────────────────┘
                      │
                      ▼
┌───────────────────────────────────────────┐
│              PyAgentsKit Core             │
│                                           │
│ Runs        Conversations       Approvals │
│ Effects     Recovery            Policies  │
│ Leases      Fencing             Audit     │
└───────┬─────────────┬─────────────┬───────┘
        │             │             │
        ▼             ▼             ▼
┌──────────────┐ ┌─────────────┐ ┌───────────────┐
│ Persistence  │ │ Artifact    │ │ Observability │
│ PostgreSQL   │ │ Storage     │ │ OTel / Logs   │
└──────┬───────┘ └─────┬───────┘ └──────┬────────┘
       │               │                 │
       └───────────────┼─────────────────┘
                       ▼
              External Systems
```

---

# 3. Objectifs architecturaux

L’architecture cible doit garantir :

```text
framework-neutral
durable-by-design
effect-safe
human-controllable
distributed
observable
auditable
portable
extensible
production-ready
```

---

# 4. Style architectural principal

L’architecture cible combine :

```text
Domain-Driven Design
Hexagonal Architecture
Ports & Adapters
Event-driven integration
Durable execution
Distributed coordination
```

sans imposer :

```text
CQRS complet
Event Sourcing complet
microservices obligatoires
Kubernetes obligatoire
workflow engine externe obligatoire
```

---

# 5. Couches de l’architecture

Les couches principales sont :

```text
1. Interfaces
2. Application
3. Domain
4. Ports
5. Adapters
6. Infrastructure
7. External Systems
```

---

# 6. Couche Interfaces

## Responsabilité

Exposer PyAgentsKit aux consommateurs externes.

## Interfaces possibles

```text
Python API
CLI
HTTP API
Admin API
Webhook handlers
Scheduler integration
Health endpoints
Readiness endpoints
```

## Exemples de cas d’usage

```text
create run
resume run
inspect run
approve action
append message
list effects
trigger reconciliation
```

## Règle

La couche Interface ne porte pas de règle métier critique.

Elle délègue à la couche Application.

---

# 7. Couche Application

## Responsabilité

Orchestrer les cas d’usage.

Exemples :

```text
CreateRunUseCase
StartRunUseCase
ResumeRunUseCase
PauseRunUseCase
CancelRunUseCase

OpenConversationUseCase
AppendMessageUseCase

PrepareEffectUseCase
ExecuteEffectUseCase
ReconcileEffectUseCase

RequestApprovalUseCase
DecideApprovalUseCase

AcquireLeaseUseCase
TakeoverLeaseUseCase
```

## Principe

La couche Application coordonne :

```text
domain objects
domain services
ports
transactions
```

mais ne contient pas la logique métier centrale.

---

# 8. Couche Domain

## Responsabilité

Porter la sémantique PyAgentsKit.

## Concepts principaux

```text
Run
Session
Conversation
Message
Effect
Approval
Lease
Worker
Checkpoint
Artifact
MemoryEntry
RuntimeBinding
RuntimeInvocation
ReconciliationCase
AuditEvent
```

## Services métier

```text
RunTransitionService
RecoveryPlanner
EffectExecutionService
EffectReconciler
ApprovalService
LeaseCoordinator
FencingValidator
PolicyEvaluator
ConversationService
MessageService
```

---

# 9. Ports

Les ports constituent les contrats indépendants de l’infrastructure.

## Persistence

```text
RunStore
SessionStore
ConversationStore
MessageStore
MemoryStore
CheckpointStore
EffectStore
ApprovalStore
LeaseStore
ArtifactStore
AuditStore
RuntimeStore
WorkerRegistry
```

## Runtime

```text
AgentRuntimeAdapter
```

## Effects

```text
ToolPort
EffectExecutor
ReconciliationPort
```

## Observability

```text
TelemetryPort
MetricsPort
TracingPort
LoggingPort
```

## Security

```text
IdentityProviderPort
AuthorizationPort
SecretProviderPort
```

---

# 10. Adapters

Les adapters traduisent les ports vers des technologies concrètes.

## Persistence adapters

```text
PostgresRunStore
PostgresSessionStore
PostgresConversationStore
PostgresMessageStore
PostgresEffectStore
PostgresApprovalStore
PostgresLeaseStore
PostgresAuditStore
```

## Artifact adapters

```text
FilesystemArtifactStore
S3ArtifactStore
AzureBlobArtifactStore
```

## Runtime adapters

```text
LangGraphAdapter
PydanticAIAdapter
OpenAIAgentsAdapter
ClaudeAgentAdapter
AutoGenAdapter
CrewAIAdapter

CodexAdapter
ClaudeCodeAdapter
OpenCodeAdapter
AgyAdapter

CustomRuntimeAdapter
```

---

# 11. Architecture des runtimes

Les runtimes sont séparés en trois familles.

```text
General-purpose runtimes
────────────────────────
LangGraph
PydanticAI
OpenAI Agents SDK
Claude Agent SDK
AutoGen
CrewAI

Coding-agent runtimes
─────────────────────
Codex
Claude Code
OpenCode
Antigravity CLI (agy)

Custom runtimes
───────────────
Internal runtime
Python application
Future runtimes
```

Ils accèdent au core via :

```text
AgentRuntimeAdapter
```

---

# 12. `AgentRuntimeAdapter`

Contrat conceptuel :

```python
class AgentRuntimeAdapter(Protocol):

    async def start(...): ...
    async def resume(...): ...
    async def cancel(...): ...
    async def status(...): ...
    async def events(...): ...
```

Le contrat final pourra évoluer.

## Responsabilités

- traduire les appels PyAgentsKit vers le runtime ;
- normaliser les événements ;
- propager le contexte de run ;
- exposer les capacités supportées ;
- éventuellement intercepter les tools.

## Non-responsabilités

L’adapter ne doit pas :

```text
posséder la persistence métier
décider seul des retries critiques
contourner les approvals
contourner le fencing
```

---

# 13. Anti-Corruption Layer

L’`AgentRuntimeAdapter` joue le rôle d’ACL.

Exemple :

```text
Codex Thread
   ↓
CodexAdapter
   ↓
RuntimeInvocation
   ↓
PyAgentsKit
```

ou :

```text
LangGraph StateGraph
   ↓
LangGraphAdapter
   ↓
Run / RuntimeEvent
```

Les concepts spécifiques aux frameworks ne doivent pas entrer directement dans le core.

---

# 14. Execution Engine

Le moteur d’exécution PyAgentsKit orchestre :

```text
Run
Checkpoint
RuntimeInvocation
Effects
Approvals
Recovery
```

Composant logique :

```text
DurableRunner
```

## Responsabilités

```text
start
resume
pause
cancel
recover
checkpoint
validate blockers
```

---

# 15. `DurableRunner`

Vue conceptuelle :

```text
DurableRunner
├── RunStore
├── CheckpointStore
├── EffectStore
├── ApprovalStore
├── LeaseStore
├── RecoveryPlanner
├── AgentRuntimeAdapter
└── AuditPublisher
```

Il constitue l’orchestrateur principal du cycle de vie d’un run.

---

# 16. Recovery Engine

Le recovery ne doit pas redémarrer aveuglément l’agent.

Flux :

```text
load Run
↓
load Checkpoint
↓
validate ownership
↓
inspect approvals
↓
inspect effects
↓
reconcile UNKNOWN
↓
compute RecoveryPlan
↓
resume
```

Composant central :

```text
RecoveryPlanner
```

---

# 17. Effect Safety Layer

Architecture :

```text
Agent / Runtime
      │
      ▼
Tool request
      │
      ▼
EffectExecutionService
      │
 ┌────┼─────────────┐
 ▼    ▼             ▼
Policy Approval   Ownership
      │             │
      └─────┬───────┘
            ▼
      Effect Intent
            │
            ▼
      External Call
            │
            ▼
      Effect Outcome
```

---

# 18. `EffectExecutionService`

Responsabilités :

```text
validate effect state
validate approval
validate ownership
validate fencing
persist intent
execute
persist outcome
emit audit event
```

---

# 19. Reconciliation Engine

Lorsqu’un effect devient :

```text
UNKNOWN
```

le système crée ou ouvre un :

```text
ReconciliationCase
```

puis utilise :

```text
EffectReconciler
```

Exemples :

```text
PaymentReconciler
GitPushReconciler
DeploymentReconciler
InvoiceReconciler
```

---

# 20. Human Governance Layer

Composants :

```text
ApprovalService
PolicyEvaluator
IdentityProviderPort
AuthorizationPort
```

Flux :

```text
Action proposed
↓
PolicyEvaluator
├── ALLOW
├── DENY
├── REQUIRE_APPROVAL
└── DEFER
```

---

# 21. Conversation Layer

Composants :

```text
ConversationService
MessageService
ConversationStore
MessageStore
```

Flux :

```text
Human / Agent
    ↓
Message
    ↓
Conversation
    ↓
Session
```

Le transport réel reste extérieur au core.

---

# 22. Message transport

PyAgentsKit peut s’intégrer à :

```text
in-process calls
HTTP
WebSocket
Redis
Kafka
NATS
runtime-native channels
```

mais ne doit pas imposer un broker.

---

# 23. Distributed Coordination Layer

Composants :

```text
LeaseCoordinator
LeaseStore
FencingValidator
WorkerRegistry
```

Architecture :

```text
Worker A
  │
  ├── acquire lease
  ▼
LeaseStore
  │
  └── fencing token 41

Worker B
  │
  └── conflict

After expiry:

Worker B
  │
  ├── takeover
  ▼
token 42
```

---

# 24. Fencing

Un fencing token doit être propagé vers les ressources protégées lorsque possible.

```text
Worker
 ↓
OwnershipContext
 ↓
ProtectedEffectContext
 ↓
Tool / Store / External Guard
```

Le token obsolète doit être rejeté.

---

# 25. Worker Architecture

Un worker logique contient :

```text
AdmissionController
DurableRunner
LeaseManager
HeartbeatManager
RuntimeAdapter(s)
Telemetry
ShutdownCoordinator
```

---

# 26. Admission Control

Responsabilités :

```text
accept new run
reject when draining
reject when not ready
apply concurrency limit
apply backpressure
```

---

# 27. Heartbeat Manager

Le heartbeat :

```text
proves liveness
```

mais ne prouve pas :

```text
ownership
```

L’ownership appartient au `LeaseStore`.

---

# 28. Graceful Shutdown

Flux recommandé :

```text
SIGTERM
↓
AdmissionController.stop()
↓
Worker = DRAINING
↓
checkpoint active runs
↓
finish / stop lease renewals
↓
release leases where appropriate
↓
flush audit / telemetry
↓
STOPPED
```

---

# 29. Persistence Architecture

Backend de référence :

```text
PostgreSQL
```

## Rôles

PostgreSQL héberge notamment :

```text
runs
sessions
conversations
messages
effects
approvals
leases
workers
runtime bindings
audit metadata
```

---

# 30. Séparation logique des stores

Même si les stores utilisent le même PostgreSQL :

```text
RunStore
EffectStore
ApprovalStore
LeaseStore
```

restent des ports distincts.

Séparation logique ≠ base physique séparée.

---

# 31. Transactions PostgreSQL

Transactions fortes candidates :

```text
lease acquisition + fencing token
run transition + checkpoint
approval decision + audit event
effect outcome + external reference
```

---

# 32. Optimistic Concurrency

Entités candidates :

```text
Run
Effect
Approval
Conversation
MemoryEntry
```

via :

```text
version
expected_version
compare-and-swap
```

---

# 33. Pessimistic Coordination

Utilisation limitée à :

```text
lease acquisition
takeover
fencing token generation
```

ou autres opérations réellement concurrentes.

---

# 34. Artifact Storage Architecture

Séparation :

```text
metadata
→ PostgreSQL

binary content
→ BlobStore
```

Backends :

```text
filesystem
S3
Azure Blob
other object store
```

---

# 35. Audit Architecture

Audit orienté append.

```text
DomainEvent
   ↓
AuditPublisher
   ↓
AuditStore
```

Exemples :

```text
RunStarted
EffectSucceeded
ApprovalApproved
LeaseTakenOver
FencingRejected
```

---

# 36. Observability Architecture

Trois dimensions :

```text
logs
metrics
traces
```

Standards privilégiés :

```text
OpenTelemetry
structured JSON logs
Prometheus-compatible metrics
```

---

# 37. Tracing

Une trace peut relier :

```text
incoming request
↓
Run
↓
RuntimeInvocation
↓
Effect
↓
External API
```

Contexte :

```text
trace_id
run_id
effect_id
worker_id
```

---

# 38. Metrics

Métriques essentielles :

```text
runs created/running/waiting/succeeded/failed
effects started/succeeded/failed/unknown
approvals pending/approved/rejected
leases acquired/renewed/lost/taken_over
reconciliation backlog
worker readiness
store latency
```

---

# 39. Logging

Les logs critiques doivent inclure si applicable :

```text
run_id
session_id
conversation_id
effect_id
approval_id
worker_id
lease_id
trace_id
```

sans exposer les secrets.

---

# 40. Security Architecture

Principes :

```text
least privilege
secrets externalized
explicit authorization
approval != authorization
audit all critical actions
```

---

# 41. Secret Management

Les secrets doivent rester dans :

```text
environment
Kubernetes Secret
Vault
AWS Secrets Manager
Azure Key Vault
GCP Secret Manager
```

et non dans :

```text
Run
Session
Memory
Message
AuditEvent
```

---

# 42. Identity Architecture

`Actor` peut référencer une identité externe.

```text
Actor
↓
external_identity_reference
↓
IAM
```

PyAgentsKit ne devient pas IAM.

---

# 43. Authorization

L’autorisation peut être déléguée via :

```text
AuthorizationPort
```

Exemples :

```text
can_approve(effect)
can_cancel(run)
can_merge_pr()
```

---

# 44. Coding Agent Architecture

Les coding agents utilisent le même core.

```text
Codex
Claude Code
OpenCode
agy
   │
   ▼
Coding Agent Adapter
   │
   ▼
AgentRuntimeAdapter
   │
   ▼
PyAgentsKit Core
```

---

# 45. Coding Effects

Actions potentiellement protégées :

```text
git commit
git push
create PR
merge PR
publish package
deploy
terraform apply
```

---

# 46. Coding Workspace

Le workspace reste hors du core généraliste.

Module optionnel :

```text
CodingWorkspace
RepositoryResource
CodeChange
```

Coordination possible via :

```text
Lease(resource=repository_branch)
```

---

# 47. Architecture des systèmes externes

PyAgentsKit peut agir vers :

```text
APIs
ERP
CRM
databases
GitHub / GitLab
CI/CD
package registries
cloud
email
Slack
object storage
```

via des tools/adapters.

---

# 48. Tool Architecture

Un tool peut être :

```text
pure function
read-only integration
protected effect
```

Classification :

```text
READ
COMPUTE
WRITE
SENSITIVE_WRITE
CRITICAL_EFFECT
```

---

# 49. Protected Tools

Un wrapper peut vérifier :

```text
policy
approval
ownership
fencing
idempotency
```

avant appel.

Concept :

```text
ProtectedTool
```

---

# 50. Event Architecture

Trois familles :

```text
DomainEvent
RuntimeEvent
IntegrationEvent
```

## DomainEvent

fait métier interne.

## RuntimeEvent

fait produit par un runtime externe.

## IntegrationEvent

fait publié vers d’autres systèmes.

---

# 51. Outbox Pattern

Pour les IntegrationEvents critiques :

```text
transaction
├── domain state
└── outbox row
```

puis :

```text
publisher
↓
external bus/webhook
```

Cela évite :

```text
state committed
but event lost
```

---

# 52. API Architecture

Une future API HTTP peut être organisée autour de :

```text
/runs
/sessions
/conversations
/messages
/effects
/approvals
/leases
/workers
/artifacts
/audit
/health
/readiness
```

Le modèle HTTP ne doit pas dicter le domaine.

---

# 53. CLI Architecture

Exemples :

```text
pyagentskit run inspect <run_id>
pyagentskit run resume <run_id>
pyagentskit effect inspect <effect_id>
pyagentskit reconcile <effect_id>
pyagentskit lease list
pyagentskit worker status
pyagentskit db migrate
```

---

# 54. Scheduler Integration

PyAgentsKit ne devient pas scheduler.

Un système externe peut déclencher :

```text
PyScheduleKit
cron
Airflow
Temporal schedule
Kubernetes CronJob
```

puis :

```text
create Run
```

---

# 55. Durable Execution Backend

Le moteur natif doit rester remplaçable.

Port futur :

```text
DurableExecutionBackend
```

Adapters possibles :

```text
Native
Temporal
DBOS
Restate
```

---

# 56. Native Durable Backend

Le backend natif combine :

```text
PostgreSQL
DurableRunner
LeaseStore
CheckpointStore
EffectStore
```

Il reste la référence pour la sémantique PyAgentsKit.

---

# 57. Topologie de déploiement minimale

```text
┌──────────────────┐
│ Application/API  │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ PyAgentsKit      │
│ Worker           │
└────────┬─────────┘
         │
         ▼
┌──────────────────┐
│ PostgreSQL       │
└──────────────────┘
```

Optionnel :

```text
Blob Storage
OpenTelemetry Collector
```

---

# 58. Topologie de production distribuée

```text
                 Load Balancer / API
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
     Worker A         Worker B         Worker C
         │               │               │
         └───────────────┼───────────────┘
                         ▼
                    PostgreSQL
                         │
             ┌───────────┼───────────┐
             ▼           ▼           ▼
         RunStore    LeaseStore   EffectStore

Workers
   │
   ├── runtime adapters
   ├── external tools
   └── telemetry
```

---

# 59. Kubernetes Deployment

Architecture possible :

```text
Deployment
├── replica worker-1
├── replica worker-2
└── replica worker-N

Service / API
PostgreSQL external
Object storage external
OTel Collector
```

Probes :

```text
/livez
/readyz
```

---

# 60. Readiness

Un worker est `ready` si :

```text
process initialized
critical stores reachable
migration compatible
admission enabled
```

Il peut être vivant mais :

```text
not ready
```

---

# 61. Scalabilité

Scalabilité horizontale :

```text
1 worker
→ N workers
```

Les garanties ne changent pas.

---

# 62. Backpressure

Le système doit pouvoir ralentir ou refuser :

```text
new runs
new effects
new runtime invocations
```

si :

```text
DB overloaded
worker saturated
external dependency degraded
```

---

# 63. Fault Domains

Les défaillances sont isolées par domaine.

Exemples :

```text
runtime failure
!=
PostgreSQL failure

artifact store failure
!=
lease failure

telemetry failure
!=
effect state failure
```

Chaque dépendance possède une stratégie de dégradation.

---

# 64. Safe Degradation

Exemple :

```text
PostgreSQL unavailable
↓
readiness false
↓
stop protected effects
↓
stop admissions
↓
preserve local execution only if safe
```

---

# 65. Architecture multi-tenant

Le core doit rester compatible avec :

```text
tenant_id
organization_id
namespace_id
workspace_id
```

sans imposer immédiatement une implémentation complète.

---

# 66. Extension points

Points d’extension principaux :

```text
AgentRuntimeAdapter
EffectReconciler
Store implementations
ArtifactStore
PolicyEvaluator
TelemetryExporter
IdentityProvider
AuthorizationProvider
DurableExecutionBackend
```

---

# 67. Plugin Model

Un futur plugin pourra enregistrer :

```text
runtime adapter
store adapter
reconciler
tool
policy provider
telemetry exporter
```

sans modifier le core.

---

# 68. Package boundaries candidates

Architecture Python possible :

```text
pyagentskit/
├── domain/
│   ├── runs/
│   ├── conversations/
│   ├── effects/
│   ├── approvals/
│   ├── coordination/
│   └── audit/
│
├── application/
│   ├── commands/
│   ├── queries/
│   └── services/
│
├── ports/
│   ├── stores/
│   ├── runtime/
│   ├── telemetry/
│   └── security/
│
├── adapters/
│   ├── postgres/
│   ├── runtime/
│   ├── blob/
│   └── telemetry/
│
├── runtime/
│   ├── durable_runner.py
│   ├── recovery.py
│   └── worker.py
│
└── api/
```

---

# 69. Dependency Rule

Direction autorisée :

```text
Interfaces
   ↓
Application
   ↓
Domain
```

et :

```text
Adapters
   ↓
Ports / Application
```

Le domaine ne dépend pas de :

```text
PostgreSQL
OpenAI
Anthropic
GitHub
Kubernetes
S3
```

---

# 70. Anti-patterns architecturaux

Interdits :

```text
runtime-specific logic in core
hidden retries
implicit effect replay
global in-memory ownership
business state only in logs
approval as callback only
fencing ignored by effect execution
one giant store interface
one giant Run aggregate
```

---

# 71. Build vs Integrate

## Build

```text
Run semantics
Effect semantics
Approval semantics
Recovery
Lease semantics
Fencing
Runtime adapter contract
Audit model
```

## Integrate

```text
PostgreSQL
S3
OpenTelemetry
Kubernetes
Temporal
DBOS
Codex
Claude Code
LangGraph
OpenAI Agents SDK
```

---

# 72. Architecture Decision Records requis

```text
ADR-001 PostgreSQL reference backend
ADR-002 RunStore / EffectStore separation
ADR-003 AgentRuntimeAdapter contract
ADR-004 Effect UNKNOWN semantics
ADR-005 Fencing token strategy
ADR-006 Lease transaction model
ADR-007 Audit append model
ADR-008 Message persistence
ADR-009 Actor local vs external IAM
ADR-010 RuntimeInvocation persistence
ADR-011 DurableExecutionBackend
ADR-012 Coding-agent adapters outside core
ADR-013 Outbox strategy
ADR-014 Optimistic concurrency strategy
```

---

# 73. Diagramme cible complet

```text
┌───────────────────────────────────────────────────────────────┐
│                       INTERFACES                              │
│ Python API | CLI | HTTP API | Scheduler | Webhooks           │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                     APPLICATION LAYER                         │
│ Use Cases | Commands | Queries | Transactions                 │
└───────────────────────────┬───────────────────────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│                         DOMAIN                                │
│                                                               │
│  Execution      Conversation     Effect Safety                │
│  Governance     Coordination     Audit                        │
└────────────┬──────────────┬──────────────┬─────────────────────┘
             │              │              │
             ▼              ▼              ▼
┌────────────────┐ ┌────────────────┐ ┌─────────────────────────┐
│ Persistence    │ │ Runtime Ports  │ │ Security / Telemetry    │
│ Ports          │ │                │ │ Ports                   │
└──────┬─────────┘ └──────┬─────────┘ └──────────┬──────────────┘
       │                  │                      │
       ▼                  ▼                      ▼
┌──────────────┐ ┌───────────────────┐ ┌────────────────────────┐
│ PostgreSQL   │ │ Runtime Adapters  │ │ OTel / IAM / Secrets   │
│ Blob Storage │ │ LangGraph         │ │                        │
│              │ │ OpenAI Agents     │ │                        │
│              │ │ Claude Agent      │ │                        │
│              │ │ Codex / OpenCode  │ │                        │
└──────────────┘ └──────────┬────────┘ └────────────────────────┘
                            │
                            ▼
                   External Agent Runtime
                            │
                            ▼
                     Tools / Systems
```

---

# 74. Flux cible de bout en bout

```text
Request
↓
Create Run
↓
Acquire Lease
↓
Runtime Adapter
↓
Agent decision
↓
Tool request
↓
Effect Policy
↓
Approval if required
↓
Persist Effect Intent
↓
Execute external action
↓
Persist Outcome
↓
Audit / Metrics / Trace
↓
Checkpoint
↓
Continue or Complete
```

---

# 75. Flux de reprise

```text
Worker crash
↓
Lease expires
↓
new Worker takeover
↓
RecoveryPlanner
↓
load Checkpoint
↓
inspect Effects
↓
reconcile UNKNOWN
↓
inspect Approvals
↓
resume Runtime
```

---

# 76. Flux agent-to-agent

```text
Agent A
 ↓
Message
 ↓
ConversationStore
 ↓
AgentRuntimeAdapter
 ↓
Agent B
```

avec :

```text
correlation
persistence
audit
recovery
```

mais sans imposer le transport.

---

# 77. Flux coding-agent

```text
Issue
↓
Run
↓
Codex / Claude Code / OpenCode
↓
Adapter
↓
edit / tests
↓
Effect: git_push
↓
Policy / Approval
↓
GitHub
↓
Effect: create_pr
↓
CI/CD
```

---

# 78. Critères de validation de l’architecture

L’architecture cible est acceptable si :

1. le core reste framework-neutral ;
2. les runtimes passent par adapters ;
3. les stores sont derrière des ports ;
4. PostgreSQL peut être backend de référence ;
5. les effects sont explicitement protégés ;
6. la reprise n’entraîne pas de replay implicite ;
7. le fencing est applicable aux opérations protégées ;
8. les approvals sont durables ;
9. les conversations sont persistables indépendamment du transport ;
10. les workers peuvent fonctionner en multi-processus ;
11. health et readiness sont séparés ;
12. l’observabilité est intégrée ;
13. l’audit est append-oriented ;
14. les coding agents restent hors du core métier ;
15. une nouvelle integration peut être ajoutée sans modifier le domaine.

---

# 79. Architecture MVP

Le MVP architectural doit inclure au minimum :

```text
Domain Core

RunStore
SessionStore
EffectStore
ApprovalStore
LeaseStore

DurableRunner
RecoveryPlanner
EffectExecutionService

PostgreSQL adapters

AgentRuntimeAdapter
CustomRuntimeAdapter

AuditPublisher
structured logging

health
readiness
```

---

# 80. Architecture production complète

La cible production ajoute :

```text
ConversationStore
MessageStore
MemoryStore
ArtifactStore

S3/Azure Blob adapters

OpenTelemetry
metrics
distributed traces

multi-worker
Kubernetes deployment

runtime adapters
coding-agent adapters

outbox
policy engine
advanced reconciliation
```

---

# 81. Non-objectifs architecturaux

PyAgentsKit ne doit pas devenir :

```text
LLM provider
prompt framework
vector database
RAG platform
coding agent
Git engine
workflow engine généraliste
scheduler généraliste
message broker
IAM
observability backend
cloud platform
```

---

# 82. Roadmap architecturale suggérée

## Phase A — Core

```text
Domain model
Stores
Run lifecycle
Effects
Approvals
```

## Phase B — Durable distributed runtime

```text
Leases
Fencing
Recovery
Multi-worker
```

## Phase C — Runtime adapters

```text
AgentRuntimeAdapter
LangGraph
OpenAI
Claude
Custom
```

## Phase D — Conversation

```text
Conversation
Message
Agent-to-agent
```

## Phase E — Coding agents

```text
Codex
Claude Code
OpenCode
agy
```

## Phase F — Production operations

```text
OTel
Kubernetes
runbooks
load tests
incident qualification
```

---

# 83. Résumé

L’architecture cible de PyAgentsKit peut être résumée ainsi :

```text
ANY AGENT RUNTIME
       │
       ▼
AgentRuntimeAdapter
       │
       ▼
PyAgentsKit Core
       │
 ┌─────┼─────┬──────┬─────────┐
 ▼     ▼     ▼      ▼         ▼
Run  Effect Approval Lease  Conversation
       │             │
       ▼             ▼
 Recovery         Fencing
       │
       ▼
Stores / Audit / Telemetry
       │
       ▼
External Systems
```

Le principe directeur de l’architecture est :

> **PyAgentsKit doit fournir une couche de contrôle et de fiabilité autour des runtimes agentiques sans devenir lui-même le runtime qui raisonne, le système métier sur lequel il agit, ni l’infrastructure générique qui l’héberge.**

Les documents suivants peuvent approfondir cette architecture par domaine :

```text
../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md
../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md
../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md
../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md
../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md
```
