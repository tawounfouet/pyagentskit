# PyAgentsKit — Modèle conceptuel du domaine

**Document :** `../domain/PYAGENTSKIT_MODELE_CONCEPTUEL_DU_DOMAINE.md`  
**Version :** 1.0  
**Date :** 19 octobre 2026  
**Statut :** Domain Model / DDD Conceptual Model  
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

---

# 1. Objet du document

Ce document formalise le **modèle conceptuel du domaine** de PyAgentsKit.

Il décrit :
- les sous-domaines ;
- les bounded contexts ;
- les agrégats ;
- les entités ;
- les Value Objects ;
- les services métier ;
- les événements du domaine ;
- les invariants ;
- les frontières transactionnelles ;
- les dépendances entre concepts ;
- les frontières avec les runtimes agentiques et l’infrastructure.

L’objectif est de répondre à la question :

> **Quels concepts doivent exister dans PyAgentsKit pour garantir l’exécution fiable, durable, contrôlée et récupérable d’agents IA ?**

---

# 2. Positionnement du domaine

PyAgentsKit ne modélise pas comment un agent raisonne, comment un LLM génère une réponse, comment un coding agent écrit du code ou comment un ERP gère ses objets métier.

Il modélise :

```text
identité de l’exécution
état durable
reprise
effets externes
validation humaine
coordination distribuée
messages et conversations
audit
observabilité
```

Le domaine central de PyAgentsKit est donc :

> **Agent Runtime Reliability**

---

# 3. Langage ubiquitaire

| Terme | Définition |
|---|---|
| Session | contexte durable regroupant runs, conversations et mémoire |
| Conversation | fil durable d’échanges entre humains, agents et systèmes |
| Message | unité durable de communication dans une conversation |
| Actor | identité logique émettant ou recevant une action/message |
| Participant | présence d’un Actor dans une Conversation |
| Run | exécution durable d’un runtime agentique |
| Checkpoint | état cohérent permettant la reprise d’un Run |
| Effect | conséquence externe produite par un Run |
| Approval | décision humaine explicitement requise |
| ReconciliationCase | traitement permettant de résoudre un Effect ambigu |
| Lease | droit temporaire d’exécution sur une ressource |
| Worker | processus capable d’exécuter un Run |
| FencingToken | jeton monotone protégeant contre un worker obsolète |
| Artifact | fichier ou résultat durable associé à une exécution |
| MemoryEntry | information persistante réutilisable au-delà d’un Run |
| RuntimeBinding | association entre PyAgentsKit et un runtime agentique |
| RuntimeInvocation | appel concret au runtime agentique |
| AuditEvent | fait durable permettant de reconstruire l’historique |
| Policy | règle déterminant si une action est autorisée ou contrôlée |
| RecoveryPlan | décision structurée de reprise après incident |

---

# 4. Sous-domaines

Le domaine PyAgentsKit est divisé en huit sous-domaines :

```text
1. Execution
2. Conversation & Context
3. Effect Safety
4. Human Governance
5. Distributed Coordination
6. Runtime Integration
7. Observability & Audit
8. Artifact & Memory Management
```

---

# 5. Execution

## Responsabilité

Gérer le cycle de vie d’une exécution agentique durable.

## Concepts

```text
Run
RunState
Checkpoint
RecoveryPlan
NextAction
```

## Questions couvertes

```text
Quel run est en cours ?
Dans quel état est-il ?
Peut-il être repris ?
Depuis quel checkpoint ?
Quel est le prochain comportement sûr ?
```

---

# 6. Conversation & Context

## Responsabilité

Conserver le contexte conversationnel durable entre humains, agents et systèmes.

## Concepts

```text
Session
Conversation
ConversationStatus
Message
MessageType
MessageContent
MessageReference
Actor
Participant
MemoryEntry
```

## Interactions supportées

```text
Human → Agent
Agent → Human
Agent → Agent
System → Agent
Agent → System
```

PyAgentsKit gère la **sémantique durable** de la communication, pas le transport physique.

---

# 7. Effect Safety

## Responsabilité

Garantir qu’une action externe peut être exécutée, reprise ou réconciliée de manière sûre.

## Concepts

```text
Effect
EffectStatus
EffectIntent
EffectOutcome
IdempotencyKey
InputFingerprint
ExternalReference
EffectRiskLevel
ReconciliationCase
EffectReconciler
ProtectedEffectContext
```

## Principe fondamental

```text
UNKNOWN != FAILED
```

Un résultat externe ambigu reste ambigu jusqu’à reconciliation.

---

# 8. Human Governance

## Responsabilité

Introduire une décision humaine durable dans le cycle de vie d’un run.

## Concepts

```text
Approval
ApprovalStatus
ApprovalDecision
ApprovalPolicy
Policy
PolicyDecision
```

Principe :

```text
Message != ApprovalDecision
```

---

# 9. Distributed Coordination

## Responsabilité

Garantir qu’un seul worker détient le droit valide de produire des effets protégés sur une ressource donnée.

## Concepts

```text
Worker
WorkerStatus
Lease
LeaseStatus
ResourceIdentity
ProtectedResource
FencingToken
OwnershipContext
LeaseCoordinator
FencingValidator
```

---

# 10. Runtime Integration

## Responsabilité

Découpler PyAgentsKit du framework ou runtime agentique utilisé.

## Concepts

```text
AgentRuntime
AgentRuntimeAdapter
RuntimeBinding
RuntimeInvocation
RuntimeEvent
RuntimeCapability
```

## Runtimes potentiels

```text
LangGraph
PydanticAI
OpenAI Agents SDK
Claude Agent SDK
AutoGen
CrewAI
Codex
Claude Code
OpenCode
Antigravity CLI (agy)
Custom Runtime
```

---

# 11. Observability & Audit

## Responsabilité

Permettre diagnostic, tracing, audit et reconstruction historique.

## Concepts

```text
DomainEvent
AuditEvent
CorrelationContext
Actor
```

## Distinction

```text
DomainEvent = fait métier
RuntimeEvent = événement du runtime externe
AuditEvent = fait durable de traçabilité
Log = information technique de diagnostic
```

---

# 12. Artifact & Memory Management

## Responsabilité

Conserver les données durables non transactionnelles ou contextuelles.

## Concepts

```text
Artifact
MemoryEntry
ExternalReference
```

---

# 13. Bounded Contexts proposés

```text
┌──────────────────────────────┐
│ Execution Context            │
│ Run / Checkpoint / Recovery  │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Conversation Context         │
│ Session / Conversation       │
│ Message / Memory             │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Effect Safety Context        │
│ Effect / Reconciliation      │
│ Idempotency                  │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Governance Context           │
│ Approval / Policy            │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Coordination Context         │
│ Lease / Worker / Fencing     │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Runtime Integration Context  │
│ Adapter / Invocation         │
└──────────────────────────────┘

┌──────────────────────────────┐
│ Audit Context                │
│ AuditEvent / Correlation     │
└──────────────────────────────┘
```

---

# 14. Context Map

```text
Conversation Context
        │
        ▼
Execution Context
   ┌────┴────┐
   ▼         ▼
Effect     Governance
Safety       │
   └────┬────┘
        ▼
Coordination
        │
        ▼
Runtime Integration
        │
        ▼
External Agent Runtime

Tous les contexts
        │
        ▼
Audit / Observability
```

---

# 15. Agrégat `Run`

## Aggregate Root

```text
Run
```

## Concepts internes ou directement contrôlés

```text
RunState
Checkpoint references
Recovery metadata
```

## Références externes

```text
Effect IDs
Approval IDs
Lease ID
RuntimeBinding ID
Artifact IDs
```

Le `Run` ne doit pas charger tout l’historique des effects/messages/approvals dans une seule transaction.

---

# 16. Agrégat `Conversation`

## Aggregate Root

```text
Conversation
```

## Concepts

```text
ConversationStatus
Participant
Message references
```

Les messages sont appendés indépendamment.

---

# 17. Agrégat `Effect`

## Aggregate Root

```text
Effect
```

## Value Objects

```text
EffectStatus
IdempotencyKey
InputFingerprint
ExternalReference
EffectRiskLevel
FencingToken
```

## Sous-entité possible

```text
ReconciliationCase
```

---

# 18. Agrégat `Approval`

## Aggregate Root

```text
Approval
```

## Value Objects

```text
ApprovalStatus
ApprovalDecision
```

---

# 19. Agrégat `Lease`

## Aggregate Root

```text
Lease
```

## Value Objects

```text
ResourceIdentity
FencingToken
LeaseStatus
```

---

# 20. Agrégat `Session`

## Aggregate Root

```text
Session
```

## Références

```text
Conversation IDs
Run IDs
MemoryEntry IDs
```

---

# 21. Entités principales

```text
Run
Session
Conversation
Message
Participant
Actor
MemoryEntry
Checkpoint
Effect
ReconciliationCase
Approval
Artifact
Lease
Worker
RuntimeBinding
RuntimeInvocation
AuditEvent
```

---

# 22. Value Objects principaux

```text
RunState
ConversationStatus
MessageType
MessageContent
MessageReference
EffectStatus
ApprovalStatus
ApprovalDecision
LeaseStatus
FencingToken
IdempotencyKey
InputFingerprint
ExternalReference
ResourceIdentity
EffectRiskLevel
CorrelationContext
ConversationContext
OwnershipContext
ProtectedEffectContext
PolicyDecision
NextAction
```

---

# 23. Services métier

```text
RunTransitionService
RecoveryPlanner
ConversationService
MessageService
EffectExecutionService
EffectReconciler
ApprovalService
LeaseCoordinator
FencingValidator
PolicyEvaluator
AuditPublisher
```

---

# 24. Domain Events

## Execution

```text
RunCreated
RunReady
RunStarted
RunWaiting
RunPaused
RunResumed
RunSucceeded
RunFailed
RunCancelled
CheckpointCreated
RecoveryPlanned
```

## Conversation

```text
ConversationOpened
ConversationPaused
ConversationClosed
MessageAppended
ParticipantJoined
ParticipantLeft
```

## Effects

```text
EffectIntended
EffectStarted
EffectSucceeded
EffectFailed
EffectUnknown
ReconciliationOpened
ReconciliationResolved
```

## Governance

```text
ApprovalRequested
ApprovalApproved
ApprovalRejected
ApprovalExpired
```

## Coordination

```text
LeaseAcquired
LeaseRenewed
LeaseLost
LeaseExpired
LeaseTakenOver
FencingRejected
WorkerStarted
WorkerDraining
WorkerStopped
```

## Runtime

```text
RuntimeInvocationStarted
RuntimeInvocationCompleted
RuntimeInvocationFailed
```

---

# 25. Domain Event vs Audit Event

Un `DomainEvent` décrit un fait métier.

Un `AuditEvent` est la représentation durable d’un fait retenu pour la traçabilité.

Exemple :

```text
EffectSucceeded
```

peut produire :

```text
AuditEvent(event_type="effect.succeeded")
```

---

# 26. Invariants globaux

```text
DOMAIN-INV-01  Un Run possède une identité stable.
DOMAIN-INV-02  Un Effect SUCCEEDED n’est jamais rejoué implicitement.
DOMAIN-INV-03  Un Effect UNKNOWN doit être réconcilié ou résolu manuellement.
DOMAIN-INV-04  Un worker sans lease valide ne produit pas de nouvel effet protégé.
DOMAIN-INV-05  Un fencing token obsolète est rejeté.
DOMAIN-INV-06  Une approval obligatoire bloque le run.
DOMAIN-INV-07  Un message durable appartient à une conversation.
DOMAIN-INV-08  Un message humain ne constitue pas automatiquement une approval.
DOMAIN-INV-09  Une reprise ne supprime pas l’historique précédent.
DOMAIN-INV-10  Un runtime adapter ne devient pas source de vérité du domaine.
DOMAIN-INV-11  Un AuditEvent persisté n’est pas modifié silencieusement.
DOMAIN-INV-12  Le transport de messages reste extérieur au domaine central.
```

---

# 27. Cycle de vie du Run

```text
CREATED
  ↓
READY
  ↓
RUNNING
 ├── WAITING ──→ RUNNING
 ├── PAUSED  ──→ RUNNING
 ├── FAILED
 ├── CANCELLED
 └── SUCCEEDED
```

---

# 28. Cycle de vie de l’Effect

```text
NOT_STARTED
    ↓
 STARTED
 ├── SUCCEEDED
 ├── FAILED
 └── UNKNOWN
       ↓
RECONCILIATION_REQUIRED
 ├── SUCCEEDED
 ├── FAILED
 └── MANUAL_REVIEW
```

---

# 29. Cycle de vie de l’Approval

```text
PENDING
 ├── APPROVED
 ├── REJECTED
 ├── EXPIRED
 └── CANCELLED
```

---

# 30. Cycle de vie du Lease

```text
ACQUIRED
   ↓
 ACTIVE
 ├── RENEWED → ACTIVE
 ├── RELEASED
 ├── EXPIRED
 ├── LOST
 └── TAKEN_OVER
```

---

# 31. Cycle de vie de la Conversation

```text
OPEN
 ├── PAUSED → OPEN
 ├── CLOSED
 └── ARCHIVED
```

---

# 32. Flux nominal d’exécution

```text
Session
  ↓
Run created
  ↓
Lease acquired
  ↓
RuntimeInvocation
  ↓
Agent runtime
  ↓
Tool request
  ↓
Effect intent persisted
  ↓
Effect executed
  ↓
Outcome persisted
  ↓
Checkpoint
  ↓
Run continues
```

---

# 33. Flux approval

```text
Run
 ↓
Sensitive Effect
 ↓
ApprovalPolicy
 ↓
ApprovalRequested
 ↓
Run WAITING
 ↓
Human Decision
 ├── REJECTED
 └── APPROVED
        ↓
    Run resumes
```

---

# 34. Flux crash après effet externe

```text
Effect STARTED
      ↓
external system executes
      X
   worker crash
      ↓
new worker
      ↓
RecoveryPlanner
      ↓
Effect state = UNKNOWN
      ↓
EffectReconciler
 ├── success found
 ├── failure found
 └── manual review
```

---

# 35. Flux agent-to-agent

```text
Human
 ↓
Planner Agent
 ↓ message
Research Agent
 ↓ message
Data Agent
 ↓ message
Research Agent
 ↓ message
Planner Agent
 ↓
Human
```

Chaque échange peut être persisté comme `Message` au sein d’une `Conversation`.

---

# 36. Flux coding agent

```text
Issue
 ↓
Run
 ↓
Coding Agent
 ├── read repo
 ├── edit files
 ├── tests
 └── commit
 ↓
Effect: git_push
 ↓
Approval / Policy
 ↓
Push
 ↓
Effect: create_pull_request
 ↓
CI
 ↓
Effect: merge / deploy
```

PyAgentsKit contrôle les effets ; le coding agent reste responsable du code.

---

# 37. Frontières transactionnelles

Cohérence forte recommandée pour :

```text
Run transition
Effect state
Approval decision
Lease ownership
Fencing token
Idempotency reservation
```

Cohérence éventuelle acceptable pour :

```text
metrics
dashboards
analytics
secondary projections
search indexes
```

---

# 38. Consistency boundaries

Éviter une transaction globale couvrant :

```text
Run
Effect
Approval
Conversation
Lease
Artifact
```

Les agrégats communiquent via :

```text
commands
domain events
application services
```

---

# 39. Ports de domaine

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
AuditPublisher
```

---

# 40. Adapters

```text
PostgresRunStore
PostgresEffectStore
PostgresLeaseStore
S3ArtifactStore
AzureBlobArtifactStore

LangGraphAdapter
PydanticAIAdapter
OpenAIAgentsAdapter
ClaudeAgentAdapter

CodexAdapter
ClaudeCodeAdapter
OpenCodeAdapter
AgyAdapter
```

---

# 41. Anti-Corruption Layer

L’`AgentRuntimeAdapter` empêche les concepts externes de polluer le domaine.

```text
External Runtime Model
        ↓
AgentRuntimeAdapter
        ↓
PyAgentsKit Domain Model
```

Exemples de concepts externes qui ne doivent pas entrer directement :

```text
LangGraph node
Claude tool result
Codex thread
OpenAI handoff
```

---

# 42. Frontière avec les systèmes métier

PyAgentsKit ne réplique pas les modèles ERP/CRM.

Exemple :

```text
Effect(kind=create_invoice)
+
ExternalReference(invoice_id)
```

suffit pour relier l’exécution à la facture externe.

---

# 43. Frontière avec Git et CI/CD

PyAgentsKit peut modéliser :

```text
Effect(kind=git_push)
ExternalReference(commit_sha)
Lease(resource=repository_branch)
```

mais pas le modèle complet Git.

---

# 44. Frontière avec l’IAM

`Actor` ne signifie pas que PyAgentsKit devient un IAM.

Le domaine peut simplement conserver :

```text
actor_id
external_identity_reference
```

---

# 45. Frontière avec le transport de messages

Le domaine connaît :

```text
Conversation
Message
Actor
Recipient
```

mais pas nécessairement :

```text
Kafka partition
NATS subject
WebSocket connection
HTTP channel
```

---

# 46. Frontière avec Temporal / DBOS / Restate

Ces moteurs peuvent être des backends de durable execution.

Le modèle PyAgentsKit reste centré sur :

```text
Run
Checkpoint
Effect
Approval
Lease
```

---

# 47. Domain Services vs Application Services

## Domain Service

Contient une règle métier.

Exemple :

```text
RecoveryPlanner
```

## Application Service

Orchestre plusieurs objets et ports.

Exemple :

```text
ResumeRunUseCase
```

---

# 48. Use Cases applicatifs candidats

```text
CreateRun
StartRun
PauseRun
ResumeRun
CancelRun

OpenConversation
AppendMessage

RequestApproval
DecideApproval

PrepareEffect
ExecuteEffect
ReconcileEffect

AcquireLease
RenewLease
ReleaseLease
TakeoverLease

AttachArtifact
WriteMemory
InspectRun
RecoverRun
```

---

# 49. Commands candidats

```text
CreateRunCommand
StartRunCommand
ResumeRunCommand
AppendMessageCommand
PrepareEffectCommand
ExecuteEffectCommand
RequestApprovalCommand
DecideApprovalCommand
AcquireLeaseCommand
RenewLeaseCommand
TakeoverLeaseCommand
```

---

# 50. Queries candidates

```text
GetRun
ListRuns
GetRunTimeline
GetConversation
ListMessages
GetEffect
ListPendingReconciliations
ListPendingApprovals
GetLease
ListWorkers
GetAuditTimeline
```

---

# 51. CQRS

PyAgentsKit n’impose pas CQRS.

La séparation logique entre commandes et requêtes reste néanmoins compatible avec :

- audit ;
- dashboards ;
- projections ;
- observabilité.

---

# 52. Event Sourcing

PyAgentsKit n’impose pas Event Sourcing.

Le modèle recommandé reste :

```text
current state
+
append-oriented audit events
```

---

# 53. Cohérence de la conversation

Un message persisté est durable.

La reprise ne doit pas produire de doublon logique simplement parce qu’un transport ou runtime a rejoué un événement.

Une future clé de déduplication pourra être envisagée :

```text
message_deduplication_key
```

---

# 54. Cohérence des effets

La sûreté des effets repose sur quatre mécanismes :

```text
idempotency
deduplication
fencing
reconciliation
```

---

# 55. Cohérence des approvals

Une approval doit être :

```text
durable
immutable once terminal
linked to an Actor
linked to an action
auditable
```

---

# 56. Cohérence des leases

```text
heartbeat = liveness signal
lease = authority
```

Le heartbeat ne prouve jamais à lui seul l’ownership.

---

# 57. Recovery model

`RecoveryPlanner` analyse :

```text
Run
Checkpoint
Effects
Approvals
Lease state
RuntimeBinding
```

et produit un :

```text
RecoveryPlan
```

---

# 58. RecoveryPlan

Propriétés possibles :

```text
run_id
checkpoint_reference
next_action
unresolved_effects
pending_approvals
lease_required
blockers
metadata
```

---

# 59. NextAction

Valeurs candidates :

```text
ACQUIRE_LEASE
WAIT_FOR_APPROVAL
RECONCILE_EFFECT
RESUME_RUNTIME
COMPLETE_RUN
FAIL_RUN
MANUAL_INTERVENTION
```

---

# 60. Objets hors du domaine central

```text
PromptTemplate
Embedding
VectorStore
LLMModel
GitCommitParser
CodeGenerator
PatchGenerator
KubernetesPod
PostgresConnection
KafkaPartition
S3Bucket
```

---

# 61. Extensions coding agents

Bounded context optionnel :

```text
CodingWorkspace
CodeChange
RepositoryResource
```

Relations possibles :

```text
CodingWorkspace
 ├── RuntimeBinding
 ├── RepositoryResource
 └── CodeChange

RepositoryResource
 └── Lease
```

---

# 62. Extension multi-agent

Le modèle existant suffit déjà pour :

```text
Agent A → Agent B
```

Une conversation contient simplement plusieurs participants.

---

# 63. `SubRun` — décision différée

Une délégation agent→agent peut être modélisée par :

```text
same Run + multiple RuntimeInvocations
```

ou :

```text
parent Run → child Run
```

Une entité spécifique `SubRun` n’est pas nécessaire tant qu’une relation parent/enfant suffit.

---

# 64. `Task` — décision différée

Le concept `Task` ne doit être introduit que si un besoin clair apparaît entre :

```text
Run
et
RuntimeInvocation
```

---

# 65. Multi-tenancy

Le domaine doit rester compatible avec un futur :

```text
Tenant
Organization
Namespace
Workspace
```

sans imposer ces concepts trop tôt.

---

# 66. Modèle conceptuel global

```text
                               SESSION
                                  │
                ┌─────────────────┼─────────────────┐
                ▼                 ▼                 ▼
         CONVERSATION            RUN             MEMORY
                │                 │
          ┌─────┴─────┐           ├── CHECKPOINT
          ▼           ▼           ├── EFFECT
     PARTICIPANT    MESSAGE       │     │
          │           │           │     └── RECONCILIATION
          └──── ACTOR ┘           │
                                  ├── APPROVAL
                                  ├── ARTIFACT
                                  ├── RUNTIME INVOCATION
                                  ├── AUDIT EVENT
                                  └── LEASE
                                        │
                                        ▼
                                      WORKER

                                  RUN
                                   │
                                   ▼
                           RUNTIME BINDING
                                   │
                                   ▼
                          AGENT RUNTIME ADAPTER
                                   │
                                   ▼
                           EXTERNAL RUNTIME
```

---

# 67. Dépendances

```text
Domain
  ↓
Application Layer
  ↓
Ports
  ↓
Adapters
  ↓
Infrastructure / External Systems
```

Le domaine ne dépend pas de l’infrastructure.

---

# 68. Priorités

## P0 — Core Reliability

```text
Run
Checkpoint
Effect
Approval
Lease
Worker
FencingToken
AuditEvent
```

## P1 — Durable Context

```text
Session
Conversation
Message
MemoryEntry
Artifact
RuntimeBinding
RuntimeInvocation
ReconciliationCase
```

## P2 — Extensions

```text
Policy
Actor persistence
Participant
CodingWorkspace
CodeChange
RepositoryResource
```

---

# 69. Questions ouvertes

```text
Q-DOM-01 Actor local ou référence IAM ?
Q-DOM-02 Participant entité ou Value Object ?
Q-DOM-03 Checkpoint aggregate/store indépendant ?
Q-DOM-04 ReconciliationCase aggregate indépendant ?
Q-DOM-05 RuntimeInvocation durable ?
Q-DOM-06 Policy aggregate root ?
Q-DOM-07 Resource générique pour les leases ?
Q-DOM-08 clé de déduplication des messages ?
Q-DOM-09 messages agent→agent toujours persistés ?
Q-DOM-10 Tenant dans le core ou extension ?
```

---

# 70. ADR induits

```text
ADR-001 Run aggregate boundary
ADR-002 Effect as aggregate root
ADR-003 Message persistence semantics
ADR-004 Actor local vs external IAM
ADR-005 Lease resource model
ADR-006 Fencing token semantics
ADR-007 ReconciliationCase lifecycle
ADR-008 RuntimeInvocation persistence
ADR-009 Approval immutability
ADR-010 Audit append model
ADR-011 Conversation aggregate boundary
ADR-012 Coding agents outside core
```

---

# 71. Critères de validation

Le modèle conceptuel est acceptable si :

1. chaque concept possède une responsabilité claire ;
2. les agrégats restent suffisamment petits ;
3. les transactions critiques sont limitées ;
4. les effets externes sont explicitement représentés ;
5. la reprise après panne est modélisable ;
6. les approvals sont durables ;
7. humain↔agent et agent↔agent sont représentés ;
8. le multi-worker est modélisé ;
9. le runtime reste interchangeable ;
10. l’infrastructure reste extérieure au domaine ;
11. les coding agents ne polluent pas le core ;
12. les événements sont auditables.

---

# 72. Résumé

Le modèle conceptuel de PyAgentsKit s’articule autour de cinq responsabilités :

```text
CONTEXT
Session / Conversation / Message / Memory

EXECUTION
Run / Checkpoint / Recovery

EFFECT SAFETY
Effect / Idempotency / Reconciliation

CONTROL
Approval / Policy / Actor

DISTRIBUTED RELIABILITY
Lease / Worker / Fencing
```

Ces concepts sont reliés aux runtimes externes par :

```text
AgentRuntimeAdapter
RuntimeBinding
RuntimeInvocation
```

et rendus observables par :

```text
DomainEvent
AuditEvent
CorrelationContext
```

La phrase centrale du modèle conceptuel est :

> **PyAgentsKit ne modélise pas l’intelligence de l’agent ; il modélise les garanties nécessaires pour que son exécution reste cohérente lorsqu’elle interagit avec des humains, d’autres agents et des systèmes réels.**

Les prochains documents naturels sont :

```text
../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md
../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md
11_PYAGENTSKIT_AGREGATS_ET_FRONTIERES_TRANSACTIONNELLES.md
12_PYAGENTSKIT_SCHEMA_POSTGRESQL.md
```
