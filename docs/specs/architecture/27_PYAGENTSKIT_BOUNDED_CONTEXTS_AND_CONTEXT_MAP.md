# PyAgentsKit — Bounded Contexts & Context Map

**Document :** `../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Strategic DDD — Bounded Contexts & Context Map  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../architecture/08_PYAGENTSKIT_ERD.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`

---

# 1. Objet

Ce document définit la **carte stratégique des Bounded Contexts** de PyAgentsKit V2.

Il répond à quatre questions fondamentales :

```text
1. Quel contexte possède quel langage métier ?
2. Quel contexte possède quelles entités et quels invariants ?
3. Comment les contextes collaborent-ils ?
4. Quelles dépendances sont interdites ?
```

Le principe directeur est :

> **Un Bounded Context possède son modèle, son vocabulaire, ses invariants et sa responsabilité métier ; il ne partage pas ses objets internes avec les autres contextes.**

---

# 2. Pourquoi des Bounded Contexts

PyAgentsKit manipule plusieurs domaines proches mais non équivalents :

```text
Run
RuntimeInvocation
Effect
Approval
Lease
Conversation
Message
Artifact
AuditEvent
Connector
RuntimeHandle
```

Sans frontières explicites, les mêmes classes finiraient par absorber plusieurs significations.

Exemple :

```text
Run
```

ne doit pas devenir simultanément :

```text
execution state
runtime session
worker ownership
approval container
conversation
audit timeline
```

Le Bounded Context empêche cette dérive.

---

# 3. Principe de modélisation

Chaque contexte doit pouvoir répondre à :

```text
What does this concept mean here?
Who owns this state?
Who may mutate it?
Which invariants are local?
Which information is imported?
Which information is published?
```

---

# 4. Contextes cibles

La cible V2 retient huit Bounded Contexts métier principaux :

```text
BC-01 Execution
BC-02 Effects
BC-03 Governance
BC-04 Coordination
BC-05 Conversations
BC-06 Runtime Integration
BC-07 Artifacts
BC-08 Audit
```

Autour d’eux existent des contextes/adapters externes :

```text
External Runtime Ecosystem
External Systems / Connectors
Identity & Authorization Providers
Storage Providers
Telemetry Backends
```

---

# 5. Context Map — vue générale

```text
                     ┌──────────────────────┐
                     │   Conversations      │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │      Execution       │
                     └─────┬────┬────┬─────┘
                           │    │    │
                           ▼    ▼    ▼
                       Effects Governance Coordination
                           │       │        │
                           │       │        │
                           └──┬────┴────┬───┘
                              │         │
                              ▼         ▼
                        Runtime Integration
                              │
                              ▼
                       External Runtimes

Execution / Effects / Governance
              │
              ├──────────────► Artifacts
              │
              └──────────────► Audit

Effects
  └──────────────────────────► External Connectors

Governance
  └──────────────────────────► Identity/AuthZ Providers
```

---

# 6. Règle de propriété

Un concept métier possède **un seul contexte d’autorité**.

Exemples :

```text
Run                  → Execution
Effect               → Effects
Approval             → Governance
Lease                → Coordination
Conversation         → Conversations
RuntimeHandle        → Runtime Integration
Artifact             → Artifacts
AuditEvent           → Audit
```

Les autres contextes ne reçoivent que :

```text
ID
Reference
Snapshot
Published DTO
Domain/Integration Event
```

---

# 7. Bounded Context BC-01 — Execution

## Mission

Piloter le cycle de vie durable d’un travail agentique.

## Ubiquitous Language

```text
Run
RunState
Checkpoint
RuntimeInvocation
RecoveryPlan
RecoveryBlocker
NextAction
```

## Aggregate principal

```text
Run
```

## Entités

```text
Run
RuntimeInvocation
Checkpoint
```

selon granularité finale.

## Value Objects

```text
RunId
RunState
RunVersion
CheckpointId
RuntimeInvocationId
RuntimeInvocationStatus
NextAction
RecoveryBlocker
```

## Invariants

```text
RUN-INV-01
Run terminal cannot return to non-terminal state without explicit new Run semantics.

RUN-INV-02
WAITING is non-terminal.

RUN-INV-03
PAUSED is explicit voluntary suspension.

RUN-INV-04
Run != RuntimeInvocation.

RUN-INV-05
A Run may survive many runtime invocations.

RUN-INV-06
A Run state transition must be concurrency-safe.
```

---

# 8. Execution — responsabilités

Le contexte Execution possède :

```text
Run lifecycle
Run transition rules
checkpoint references
runtime invocation history
recovery decision orchestration semantics
completion/failure/cancellation semantics
```

Il ne possède pas :

```text
Effect implementation
Approval decision
Lease internals
runtime provider state
conversation content
audit storage
```

---

# 9. Execution — dépendances

Execution consomme des informations de :

```text
Effects
Governance
Coordination
Runtime Integration
Conversations
```

mais uniquement via :

```text
ports
references
published states
```

---

# 10. Bounded Context BC-02 — Effects

## Mission

Garantir la sûreté des conséquences externes durables.

## Ubiquitous Language

```text
Effect
EffectIntent
EffectStatus
IdempotencyKey
InputFingerprint
EffectRiskLevel
ExternalReference
ReconciliationCase
ReconciliationResult
```

## Aggregate principal

```text
Effect
```

## Aggregate associé

```text
ReconciliationCase
```

## Invariants

```text
EFF-INV-01
SUCCEEDED Effect is never implicitly replayed.

EFF-INV-02
UNKNOWN != FAILED.

EFF-INV-03
Same idempotency key with different fingerprint is a conflict.

EFF-INV-04
Ambiguous external write requires reconciliation.

EFF-INV-05
Manual resolution requires evidence and authorization.

EFF-INV-06
Effect can exist independently of ToolCall.
```

---

# 11. Effects — ce qu’il possède

```text
durable intent
risk classification
idempotency
fingerprint
status
external references
reconciliation lifecycle
manual resolution semantics
```

---

# 12. Effects — ce qu’il ne possède pas

```text
Approval lifecycle
worker lease
runtime session
connector SDK type
GitHub PullRequest object
Stripe Charge object
```

---

# 13. ToolCall vs Effect

Dans le langage cible :

```text
ToolCall
= demande émise par un runtime

Effect
= conséquence durable contrôlée par PyAgentsKit
```

Donc :

```text
ToolCall != Effect
```

Un ToolCall pur peut ne jamais produire d’Effect.

Un Effect peut provenir d’autre chose qu’un ToolCall.

---

# 14. Bounded Context BC-03 — Governance

## Mission

Décider si une action peut être autorisée, approuvée ou bloquée.

## Ubiquitous Language

```text
Principal
Actor
Authorization
Approval
ApprovalScope
PolicyDecision
SegregationOfDuties
DecisionEvidence
```

## Aggregate principal

```text
Approval
```

## Concepts

```text
Principal
ApprovalScope
ApprovalDecision
PolicyDecision
AuthorizationDecision
```

## Invariants

```text
GOV-INV-01
Authentication != Authorization != Approval.

GOV-INV-02
Runtime output cannot grant authority.

GOV-INV-03
Terminal Approval decision is immutable.

GOV-INV-04
Approval applies only to its scope.

GOV-INV-05
Scope drift invalidates approval applicability.

GOV-INV-06
Approval survives worker loss.
```

---

# 15. Governance — responsabilité

Le contexte Governance possède :

```text
Approval request
Approval decision
Approval expiry
Approval scope
policy evaluation result
SoD rules
authorization-related decision models
```

Il ne possède pas :

```text
Effect execution
Run lifecycle
worker ownership
identity provider internals
```

---

# 16. Actor vs Principal

Ces deux notions ne doivent pas être fusionnées.

```text
Actor
= identité logique métier participant à une interaction

Principal
= identité de sécurité authentifiée pouvant exercer une autorité
```

Un humain peut être les deux.

Un agent peut être un Actor sans être un Principal autorisé pour certaines opérations.

---

# 17. Bounded Context BC-04 — Coordination

## Mission

Garantir qu’un seul worker possède l’autorité opérationnelle sur une ressource distribuée.

## Ubiquitous Language

```text
Lease
Owner
Worker
ResourceIdentity
FencingToken
Takeover
Renewal
OwnershipContext
```

## Aggregate principal

```text
Lease
```

ou `LeaseResource` + Lease history selon implémentation.

## Invariants

```text
COORD-INV-01
At most one authoritative active owner per resource.

COORD-INV-02
New fencing token is strictly greater.

COORD-INV-03
Heartbeat != ownership.

COORD-INV-04
Queue delivery != ownership.

COORD-INV-05
Stale owner cannot execute new Protected Effect.

COORD-INV-06
Safety does not depend on graceful cleanup.
```

---

# 18. Coordination — responsabilité

```text
acquire
renew
release
expire
takeover
fencing generation
worker lifecycle authority
ownership validation
```

---

# 19. Coordination — ce qu’il ne possède pas

```text
Run business status
Effect business outcome
Approval decision
runtime session state
```

Un Lease ne fait qu’autoriser une progression opérationnelle.

---

# 20. Bounded Context BC-05 — Conversations

## Mission

Gérer les interactions durables entre humains, agents et systèmes.

## Ubiquitous Language

```text
Session
Conversation
Message
Participant
Actor
MemoryEntry
```

## Aggregates

```text
Session
Conversation
```

## Invariants

```text
CONV-INV-01
Session != Conversation.

CONV-INV-02
Message belongs to one Conversation.

CONV-INV-03
A free-text Message is not an Approval.

CONV-INV-04
A ToolCall is not a Message unless explicitly represented as communication.

CONV-INV-05
Message deduplication is explicit when transport can redeliver.
```

---

# 21. Session

La Session représente :

```text
durable global context
```

Elle peut contenir :

```text
multiple Runs
multiple Conversations
MemoryEntries
```

---

# 22. Conversation

La Conversation représente :

```text
communication thread
```

avec :

```text
Participants
Messages
```

---

# 23. Message

Le Message métier possède potentiellement :

```text
MessageId
ConversationId
Sender
Recipients
MessageType
MessageContent
CreatedAt
DeduplicationKey
References
```

Il doit être distingué du :

```text
RuntimeMessage / ModelMessage
```

---

# 24. Bounded Context BC-06 — Runtime Integration

## Mission

Exprimer les capacités d’un runtime agentique de façon canonique.

## Ubiquitous Language

```text
Runtime
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeStatus
RuntimeEvent
RuntimeCheckpoint
RuntimeBinding
```

## Invariants

```text
RT-INV-01
Runtime-specific types never leak into core domain.

RT-INV-02
RuntimeHandle is opaque.

RT-INV-03
Capabilities are explicit.

RT-INV-04
Runtime is never source of truth for durable Effects.

RT-INV-05
Unsupported capability fails explicitly.
```

---

# 25. Runtime Integration — responsabilité

```text
canonical runtime model
capabilities
runtime references
runtime state vocabulary
runtime event vocabulary
```

---

# 26. Runtime Integration — hors contexte

Les implémentations concrètes :

```text
LangGraph
PydanticAI
OpenAI Agents
Codex
Claude Code
OpenCode
```

sont des **adapters externes** au Bounded Context.

---

# 27. Bounded Context BC-07 — Artifacts

## Mission

Représenter des productions durables, identifiables et vérifiables.

## Ubiquitous Language

```text
Artifact
ArtifactReference
Checksum
Provenance
ContentType
ArtifactStatus
```

## Aggregate principal

```text
Artifact
```

## Invariants

```text
ART-INV-01
Artifact identity is durable.

ART-INV-02
Checksum mismatch invalidates integrity.

ART-INV-03
Storage URI is not business identity.

ART-INV-04
Large bytes remain outside core aggregate state.

ART-INV-05
Artifact provenance is explicit.
```

---

# 28. Artifacts — dépendance storage

Le domaine connaît :

```text
Artifact
ArtifactReference
Checksum
```

Le port connaît :

```text
ArtifactStore
BlobStore
```

Les adapters connaissent :

```text
filesystem
S3
Azure Blob
MinIO
```

---

# 29. Bounded Context BC-08 — Audit

## Mission

Conserver une trace durable de responsabilité et de décision.

## Ubiquitous Language

```text
AuditEvent
AuditSubject
AuditAction
AuditActor
AuditEvidence
AuditReason
```

## Invariants

```text
AUD-INV-01
Audit is append-oriented.

AUD-INV-02
AuditEvent != DomainEvent.

AUD-INV-03
AuditEvent != Log.

AUD-INV-04
AuditEvent != Trace.

AUD-INV-05
Sensitive data is minimized.

AUD-INV-06
Critical manual repair is auditable.
```

---

# 30. Audit — responsabilité

Audit capture :

```text
who
what
when
why
object
before/after where appropriate
evidence
correlation
```

---

# 31. Domain Events

Chaque contexte peut produire des Domain Events.

Exemples :

```text
RunStarted
RunWaiting
EffectPlanned
EffectSucceeded
EffectBecameUnknown
ApprovalRequested
ApprovalApproved
LeaseTakenOver
MessageAppended
ArtifactCreated
```

---

# 32. DomainEvent ≠ IntegrationEvent

```text
DomainEvent
= fait interne au domaine

IntegrationEvent
= message publié hors du contexte
```

Un DomainEvent peut être projeté vers un IntegrationEvent via Application/Outbox.

---

# 33. Shared Kernel

Un Shared Kernel minimal est autorisé.

Il contient uniquement des concepts transversaux réellement stables.

Candidats :

```text
typed IDs
CorrelationContext
TenantId
DomainEvent base
Clock abstraction
Version
```

---

# 34. Shared Kernel interdit

Ne pas placer dans Shared Kernel :

```text
Run
Effect
Approval
Lease
Message
RuntimeHandle
```

sinon les frontières disparaissent.

---

# 35. Context Relationship Patterns

Les relations DDD utilisées sont :

```text
Published Language
Open Host Service
Anti-Corruption Layer
Customer/Supplier
Conformist — exceptionnellement
Shared Kernel — minimal
Separate Ways — lorsque nécessaire
```

---

# 36. Execution ↔ Effects

Relation :

```text
Execution = Customer
Effects = Supplier
```

Execution a besoin de connaître l’état des Effects pour décider de la progression.

Mais Execution ne lit pas les internals de Effect.

Published Language :

```text
EffectId
EffectStatus
EffectSummary
```

---

# 37. Execution ↔ Governance

Relation :

```text
Execution = Customer
Governance = Supplier
```

Execution demande :

```text
is this blocker satisfied?
```

Governance publie :

```text
ApprovalStatus
ApprovalApplicability
```

---

# 38. Execution ↔ Coordination

Relation :

```text
Execution = Customer
Coordination = Supplier
```

Execution a besoin de :

```text
OwnershipContext
```

pour autoriser un worker à progresser.

---

# 39. Execution ↔ Runtime Integration

Relation majeure :

```text
Execution = Customer
Runtime Integration = Supplier
```

Le port :

```text
AgentRuntimeAdapter
```

est un Open Host Service logique de Runtime Integration.

---

# 40. Execution ↔ Conversations

Relation :

```text
Execution = Customer
Conversations = Supplier
```

Execution peut recevoir :

```text
SessionId
ConversationContext
MessageReferences
```

mais ne possède pas les messages.

---

# 41. Effects ↔ Governance

Relation :

```text
Effects = Customer
Governance = Supplier
```

Avant un Protected Effect :

```text
policy
authorization
approval
```

peuvent être requis.

---

# 42. Effects ↔ Coordination

Relation :

```text
Effects = Customer
Coordination = Supplier
```

Un Protected Effect peut exiger :

```text
OwnershipContext
FencingToken
```

---

# 43. Effects ↔ External Systems

Relation :

```text
Effects
  ↓
Connector Port
  ↓
Anti-Corruption Layer
  ↓
External Provider
```

Le Connector agit comme ACL.

---

# 44. Governance ↔ Identity Provider

Relation :

```text
Governance
↓
IdentityProviderPort / AuthorizationPort
↓
ACL
↓
OIDC / IAM / external provider
```

Les tokens provider ne doivent pas contaminer le domaine.

---

# 45. Artifacts ↔ Object Storage

Relation :

```text
Artifacts
↓
ArtifactStore / BlobStore
↓
S3/Azure/FileSystem adapter
```

---

# 46. Audit ↔ Telemetry

Ce sont des contextes séparés.

Un AuditEvent peut générer de la telemetry.

Une trace ne remplace jamais l’AuditStore.

---

# 47. Runtime Integration ↔ External Runtime

Relation :

```text
Runtime Integration
↓
AgentRuntimeAdapter Port
↓
Anti-Corruption Layer
↓
Runtime SDK / process / API
```

---

# 48. Native Runtime relation

Le Runner V1 est traité comme un système/runtime externe au Reliability Core V2.

Relation :

```text
V2 Runtime Integration
↓
NativeRuntimeAdapter
↓
V1 Runner
```

Cela protège le modèle V2 des sémantiques historiques V1.

---

# 49. Context Map détaillée

```text
┌───────────────────────────────────────────────────────────────┐
│                        CONVERSATIONS                          │
│ Session · Conversation · Message · Actor · Participant       │
└─────────────────────────────┬─────────────────────────────────┘
                              │ Published context refs
                              ▼
┌───────────────────────────────────────────────────────────────┐
│                         EXECUTION                             │
│ Run · RuntimeInvocation · Checkpoint · Recovery              │
└─────────────┬────────────────┬────────────────┬───────────────┘
              │                │                │
              ▼                ▼                ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│     EFFECTS     │  │   GOVERNANCE    │  │  COORDINATION   │
│ Effect          │  │ Approval        │  │ Lease           │
│ Reconciliation  │  │ Policy          │  │ Fencing         │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         │                    │                    │
         └──────────────┬─────┴──────────────┬─────┘
                        │                    │
                        ▼                    ▼
             ┌─────────────────┐     ┌─────────────────┐
             │ RUNTIME         │     │     AUDIT       │
             │ INTEGRATION     │     │ responsibility  │
             └────────┬────────┘     └─────────────────┘
                      │
                      ▼
             Runtime Adapters

Effects ─────────────► Connector Adapters
Artifacts ───────────► Storage Adapters
Governance ──────────► Identity/AuthZ Adapters
```

---

# 50. Upstream / Downstream matrix

| Upstream | Downstream | Relation |
|---|---|---|
| Effects | Execution | Customer/Supplier |
| Governance | Execution | Customer/Supplier |
| Coordination | Execution | Customer/Supplier |
| Runtime Integration | Execution | Open Host Service |
| Conversations | Execution | Published Language |
| Governance | Effects | Customer/Supplier |
| Coordination | Effects | Customer/Supplier |
| Artifacts | Execution/Effects | Published Language |
| Audit | All contexts | Sink / Published contract |
| External Runtime | Runtime Integration | ACL |
| External Systems | Effects | ACL via Connector |
| Identity Provider | Governance | ACL |

---

# 51. Published Language

Les contrats inter-contextes doivent être petits et stables.

Exemples :

```text
RunReference
EffectSummary
ApprovalSummary
OwnershipContext
RuntimeDescriptor
RuntimeStatus
ConversationContext
ArtifactReference
AuditSubjectReference
```

---

# 52. Published Language anti-pattern

Ne pas publier directement :

```text
Run aggregate
Effect aggregate
Approval aggregate
Lease aggregate
```

aux autres contextes.

Préférer DTO/reference immuable.

---

# 53. Open Host Services

Les services ouverts principaux sont :

```text
AgentRuntimeAdapter
Connector
AuthorizationPort
PolicyEvaluator
ArtifactStore
AuditPublisher
Repository ports
```

Ils définissent des contrats stables autour du domaine.

---

# 54. Anti-Corruption Layer — runtime

Chaque runtime adapter possède son ACL.

Exemple :

```text
LangGraph state
↓ mapper
RuntimeStatus

LangGraph checkpoint
↓ mapper
RuntimeCheckpoint
```

---

# 55. Anti-Corruption Layer — coding agent

```text
Codex session/process/event
↓ ACL
RuntimeHandle / RuntimeEvent / Artifact / EffectIntent
```

---

# 56. Anti-Corruption Layer — connector

Exemple GitHub :

```text
GitHub PullRequest
↓ mapper
ExternalReference

GitHub API status
↓ reconciliation mapper
ReconciliationResult
```

---

# 57. Anti-Corruption Layer — identity

```text
OIDC claims
↓ mapper
Principal

provider roles
↓ mapper
AuthorizationContext
```

---

# 58. Context autonomy

Chaque contexte doit pouvoir évoluer indépendamment tant que son Published Language reste compatible.

Exemple :

```text
Governance may introduce multi-approval
```

sans modifier directement :

```text
Execution.Run
```

---

# 59. Context versioning

Les échanges inter-contextes versionnés peuvent porter :

```text
schema_version
contract_version
```

si persistence/event transport le nécessite.

---

# 60. Shared database ≠ shared model

Plusieurs contextes peuvent initialement utiliser le même PostgreSQL physique.

Cela ne signifie pas qu’ils partagent leur modèle.

```text
same DB
!=
same Bounded Context
```

---

# 61. Cross-context SQL

Interdit pour logique métier.

Exemple interdit :

```sql
UPDATE runs
SET state = 'SUCCEEDED'
FROM effects
WHERE ...
```

si cela contourne les services/domain rules.

---

# 62. Read-model exception

Les queries opérateur peuvent produire des projections cross-context :

```text
Run Timeline
Operations Dashboard
```

mais elles sont :

```text
read-only
non-authoritative
```

---

# 63. CQRS léger

La V2 peut employer un CQRS léger :

```text
Commands
→ domain/application

Queries
→ optimized projections
```

sans imposer un full event sourcing.

---

# 64. Read Models

Exemples :

```text
RunView
EffectView
ApprovalView
WorkerView
RunTimelineView
```

Ils peuvent joindre plusieurs contextes.

Ils ne servent jamais à prendre une décision critique.

---

# 65. Transaction boundaries

Une transaction locale suit normalement un aggregate/context.

Cross-context orchestration appartient à Application Layer.

Exemple :

```text
Approve
↓
Governance transaction
↓
DomainEvent
↓
Outbox
↓
Execution wakes later
```

et non une mutation directe de Run dans ApprovalRepository.

---

# 66. Orchestration vs Choreography

Pour les opérations de safety critiques :

```text
orchestration explicite
```

est préférable.

Exemple :

```text
ResumeRun use case
```

orchestre :

```text
Coordination
Governance
Effects
Runtime Integration
```

---

# 67. Choreography

Adaptée pour :

```text
notifications
metrics
read model updates
non-critical integrations
```

---

# 68. Execution Application Service

Le use case `ResumeRun` peut :

```text
load Run
↓
obtain ownership
↓
inspect blockers
↓
inspect Effects
↓
validate Approval
↓
inspect runtime
↓
compute RecoveryPlan
↓
execute NextAction
```

mais chaque invariant reste dans son contexte propriétaire.

---

# 69. Couplage autorisé

Autorisé :

```text
Execution knows EffectId
Execution consumes EffectSummary
Execution calls EffectApplicationPort
```

Non autorisé :

```text
Execution mutates Effect.status directly
```

---

# 70. Context-specific repositories

Chaque repository appartient au contexte de son aggregate.

```text
RunRepository          → Execution
EffectRepository       → Effects
ApprovalRepository     → Governance
LeaseRepository        → Coordination
ConversationRepository → Conversations
ArtifactRepository     → Artifacts
AuditStore             → Audit
```

---

# 71. No generic repository

Éviter :

```python
Repository[T]
```

comme seule abstraction universelle.

Les opérations utiles diffèrent selon l’aggregate.

---

# 72. Domain services

Domain Service uniquement lorsque la règle :

```text
does not naturally belong to one entity/value object
```

Exemples candidats :

```text
RunTransitionService
EffectSafetyPolicy
ApprovalApplicabilityService
FencingValidator
```

---

# 73. Application service ≠ Domain service

```text
Domain service
= business rule

Application service
= orchestration
```

---

# 74. Context package mapping

```text
domain/execution/
domain/effects/
domain/governance/
domain/coordination/
domain/conversations/
domain/runtime_integration/
domain/artifacts/
domain/audit/
```

Les noms du code doivent refléter ces contextes.

---

# 75. Application mapping

```text
application/execution/
application/effects/
application/governance/
application/coordination/
application/conversations/
application/recovery/
```

---

# 76. Outbound ports mapping

```text
application/ports/outbound/
├── repositories/
├── runtime/
├── connectors/
├── security/
├── storage/
├── messaging/
└── telemetry/
```

---

# 77. Adapter mapping

```text
adapters/outbound/
├── persistence/
├── runtimes/
├── connectors/
├── models/
├── storage/
├── security/
└── telemetry/
```

---

# 78. External context — Model Providers

OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama sont externes au Reliability Core.

Ils restent principalement consommés par :

```text
Native Runtime
```

ou éventuellement d’autres adapters.

---

# 79. External context — Agent Runtimes

```text
LangGraph
PydanticAI
OpenAI Agents
AutoGen
CrewAI
Codex
Claude Code
OpenCode
```

Chaque runtime est traité comme système externe derrière ACL.

---

# 80. External context — Business Systems

```text
GitHub
GitLab
Slack
Jira
ERP
CRM
Cloud
Payment provider
CI/CD
Registry
```

Ils entrent via Connector adapters.

---

# 81. Context-specific errors

Chaque contexte possède son erreur métier.

Exemples :

```text
InvalidRunTransition
EffectAlreadySucceeded
IdempotencyConflict
ApprovalExpired
StaleOwnership
ConversationClosed
UnsupportedRuntimeCapability
ArtifactIntegrityError
```

---

# 82. Error translation

Les adapters traduisent :

```text
provider exception
→ adapter error
→ public/application error
```

Le domaine ne connaît pas :

```text
HTTP 409
psycopg error
GitHubApiException
```

---

# 83. Ubiquitous Language governance

Tout terme central doit avoir une définition unique dans le glossaire.

Exemple :

```text
Run
Effect
Approval
Lease
RuntimeInvocation
Conversation
```

doivent être employés avec la même signification dans :

```text
code
docs
tests
API
runbooks
```

---

# 84. Terms to forbid

Éviter les noms ambigus :

```text
Job
Task
Execution
Process
Session
State
Event
```

sans qualification.

Préférer :

```text
Run
RuntimeInvocation
Effect
RuntimeEvent
AuditEvent
DomainEvent
```

---

# 85. Context boundary tests

Créer des tests statiques qui garantissent :

```text
domain.execution cannot import domain.effects.Effect aggregate directly
```

si seul un Published Contract est autorisé.

Selon implémentation, certains imports de VOs partagés peuvent rester permis.

---

# 86. Import-linter contracts

Exemple conceptuel :

```text
Contract: Domain must not depend on adapters
Contract: Application must not depend on concrete adapters
Contract: Contexts must not import other context aggregates
Contract: Runtime adapters are independent
Contract: Connectors are independent
```

---

# 87. Separate Ways

Certains concepts peuvent rester complètement séparés.

Exemple :

```text
RuntimeProvider configuration
```

n’a pas besoin d’être partagé avec :

```text
Connector configuration
```

Même si les deux utilisent HTTP.

---

# 88. Conformist

Le pattern Conformist doit rester exceptionnel.

Exemple acceptable :

```text
OpenTelemetry semantic conventions
```

car PyAgentsKit n’a pas besoin d’inventer son propre format si cela ne pollue pas le domaine.

---

# 89. Customer/Supplier governance

Quand un contexte upstream change son Published Language, il doit considérer ses downstreams.

Exemple :

```text
Governance changes ApprovalSummary
```

impacte :

```text
Execution
Effects
```

---

# 90. Compatibility policy inter-contextes

Pour contrats internes stables :

```text
additive changes preferred
```

Breaking changes nécessitent :

```text
version bump
migration
contract test update
```

---

# 91. Event-driven context collaboration

Exemple Approval :

```text
Governance
ApprovalApproved
↓
Outbox
↓
Execution wake-up
```

Execution re-charge ensuite la vérité actuelle.

---

# 92. Event as hint

Un event n’est pas nécessairement la vérité autoritative.

Le consumer peut :

```text
receive event
↓
load authoritative aggregate
```

---

# 93. Duplicate event

Les Integration Events peuvent être at-least-once.

Consumer :

```text
Inbox dedup
```

---

# 94. Context Map — Runtime flow

```text
Execution
↓ request runtime action
Runtime Integration
↓ AgentRuntimeAdapter
Runtime ACL
↓
External Runtime
```

Retour :

```text
provider/runtime response
↓
ACL mapping
↓
RuntimeStatus / RuntimeEvent
↓
Execution
```

---

# 95. Context Map — Effect flow

```text
Runtime
↓ proposes action
Application EffectGateway
↓
Governance
↓
Coordination
↓
Effects creates durable intent
↓
Connector
↓
External System
↓
Effects stores outcome/reference
```

---

# 96. Context Map — Approval flow

```text
Effect needs approval
↓
Governance creates Approval
↓
Execution becomes WAITING
↓
Human/API decision
↓
Governance terminal decision
↓
Outbox wake-up
↓
Execution revalidates
```

---

# 97. Context Map — Recovery flow

```text
Execution RecoveryPlanner
├── Coordination → ownership?
├── Effects → unknown/reconciliation?
├── Governance → approval valid?
└── Runtime Integration → runtime resumable?
```

Output :

```text
NextAction
```

---

# 98. Context Map — Conversation flow

```text
Conversation
↓ Message
Session
↓ context reference
Execution
↓
Runtime Integration
```

Le runtime reçoit une représentation dérivée, pas nécessairement l’aggregate Message.

---

# 99. Context Map — Artifact flow

```text
Runtime/Effect/Application
↓ creates artifact intent
Artifacts
↓ store port
Object Storage
```

Le domaine Artifact conserve :

```text
identity
checksum
provenance
```

---

# 100. Context Map — Audit flow

Chaque contexte émet des faits pertinents.

Application traduit certains événements vers :

```text
AuditEvent
```

Audit persiste append-only.

---

# 101. Ownership matrix

| Concept | Owning Context |
|---|---|
| Run | Execution |
| RunState | Execution |
| RuntimeInvocation | Execution |
| Checkpoint | Execution |
| Effect | Effects |
| ReconciliationCase | Effects |
| Approval | Governance |
| Principal | Governance |
| Lease | Coordination |
| FencingToken | Coordination |
| Worker | Coordination |
| Session | Conversations |
| Conversation | Conversations |
| Message | Conversations |
| Actor | Conversations/Governance reference boundary |
| RuntimeDescriptor | Runtime Integration |
| RuntimeHandle | Runtime Integration |
| Artifact | Artifacts |
| AuditEvent | Audit |

---

# 102. Actor ownership nuance

`Actor` existe conceptuellement dans Conversations.

Governance ne doit pas réutiliser directement l’aggregate Actor.

Il utilise :

```text
ActorReference
PrincipalReference
```

---

# 103. Tenant ownership

`TenantId` peut appartenir au Shared Kernel car tous les contextes l’utilisent pour isolation.

Mais :

```text
Tenant aggregate
```

n’est pas nécessairement dans PyAgentsKit core.

---

# 104. Correlation ownership

`CorrelationContext` est un Value Object transversal candidat au Shared Kernel.

---

# 105. Context data duplication

Une duplication contrôlée est acceptable.

Exemple :

Effect peut conserver :

```text
run_id
tenant_id
```

sans posséder le Run.

---

# 106. Snapshot duplication

Approval peut conserver :

```text
scope fingerprint
policy version
```

pour audit historique.

Cette duplication est intentionnelle.

---

# 107. Never distributed object graph

Éviter de reconstruire un objet global :

```text
Run {
  Effects[]
  Approvals[]
  Messages[]
  Lease
  Runtime
  AuditEvents[]
}
```

Ce serait un anti-DDD.

---

# 108. Aggregate size

Chaque aggregate doit rester petit et transactionnellement cohérent.

---

# 109. Cross-context consistency

La consistance globale est souvent :

```text
eventually consistent
```

mais les invariants de safety localement critiques doivent être synchrones au point de décision.

---

# 110. Synchronous safety checks

Avant Protected Effect :

```text
Authorization
Approval applicability
Ownership/Fencing
Effect idempotency reservation
```

doivent être validés de manière suffisamment forte.

---

# 111. Eventual consistency acceptable

Exemples :

```text
dashboard update
notification
analytics
non-critical timeline projection
```

---

# 112. Context Map evolution

La carte peut évoluer.

Un nouveau contexte doit être créé seulement si :

```text
language differs
invariants differ
ownership differs
rate of change differs
integration boundary matters
```

---

# 113. Context candidates not retained

Pas de Bounded Context séparé au départ pour :

```text
Testing
Configuration
Telemetry
CLI
HTTP
PostgreSQL
```

Ce sont des concerns/adapters, pas des domaines métier.

---

# 114. Coding Agents

Le coding-agent support n’est pas un Bounded Context core séparé initialement.

Il est principalement :

```text
Runtime Adapter family
+
specialized application policies
+
Effect kinds
+
Artifact kinds
```

---

# 115. Connectors

Les connectors ne forment pas un Bounded Context métier central unique.

Ils sont des adapters vers des External Systems avec contrats communs.

---

# 116. Scheduling

PyAgentsKit ne crée pas un Scheduling Bounded Context général.

La planification reste hors scope principal.

---

# 117. IAM

PyAgentsKit ne devient pas un IAM.

Governance consomme des Identity/AuthZ providers.

---

# 118. Observability

Observability n’est pas un Bounded Context métier principal.

Audit, lui, possède une sémantique métier de responsabilité.

---

# 119. Context integration testing

Tests requis :

```text
Execution ↔ Effects contract
Execution ↔ Governance contract
Execution ↔ Coordination contract
Execution ↔ Runtime Integration contract
Effects ↔ Connector contract
Governance ↔ Authorization contract
Artifacts ↔ Storage contract
Audit append contract
```

---

# 120. Consumer-driven contracts

Pour les Published Languages critiques, utiliser si utile :

```text
consumer-driven contract tests
```

afin de détecter une rupture avant intégration.

---

# 121. Context API surfaces

Chaque contexte doit exposer peu de contrats.

Exemple Effects :

```text
EffectSummary
EffectCommandPort
EffectQueryPort
```

et non tous ses internals.

---

# 122. Mapping functions

Tous les mappings inter-contextes doivent être explicites.

Éviter :

```text
model_dump() → pass dictionary everywhere
```

---

# 123. Context-level package privacy

Utiliser `_internal` ou absence d’export public pour empêcher l’usage accidentel d’objets internes.

---

# 124. Bounded Context documentation

Chaque contexte doit avoir :

```text
README
Ubiquitous Language
Aggregates
Invariants
Published Language
Inbound contracts
Outbound dependencies
Failure semantics
```

---

# 125. Suggested directory

```text
docs/architecture/contexts/
├── execution.md
├── effects.md
├── governance.md
├── coordination.md
├── conversations.md
├── runtime_integration.md
├── artifacts.md
└── audit.md
```

---

# 126. ADR candidates

```text
ADR-CTX-001 Bounded Context boundaries
ADR-CTX-002 Shared Kernel contents
ADR-CTX-003 Run vs RuntimeInvocation
ADR-CTX-004 Session vs Conversation
ADR-CTX-005 Effect vs ToolCall
ADR-CTX-006 Approval ownership
ADR-CTX-007 Runtime Integration ACL
ADR-CTX-008 Audit separation
ADR-CTX-009 Cross-context consistency
ADR-CTX-010 Domain events vs integration events
```

---

# 127. Context-level Acceptance Criteria

Le Context Map est correctement implémenté si :

1. chaque aggregate possède un contexte unique ;
2. aucun runtime SDK type ne fuit dans le domaine ;
3. aucun aggregate d’un contexte n’est directement muté par un autre ;
4. les échanges utilisent IDs, references, Published Language ou ports ;
5. `Session != Conversation` dans code et persistence ;
6. `Run != RuntimeInvocation` dans code et persistence ;
7. `ToolCall != Effect` dans code et runtime mapping ;
8. `Approval != Authorization` ;
9. `Lease != Run` ;
10. `AuditEvent != DomainEvent != RuntimeEvent` ;
11. les ACL runtime/connectors sont explicites ;
12. les tests d’architecture interdisent les imports invalides.

---

# 128. Context-specific Definition of Done

## Execution

```text
Run lifecycle tests
RuntimeInvocation separation
Recovery integration
```

## Effects

```text
idempotency
UNKNOWN
reconciliation
no implicit replay
```

## Governance

```text
approval scope
authz separation
expiry
revalidation
```

## Coordination

```text
lease
fencing
takeover
stale worker rejection
```

## Conversations

```text
session/conversation split
message identity
participants
```

## Runtime Integration

```text
adapter contract
capability negotiation
opaque handles
```

## Artifacts

```text
integrity
provenance
storage independence
```

## Audit

```text
append-only
queryability
privacy
```

---

# 129. Package topology reminder

```text
domain/
├── execution/
├── effects/
├── governance/
├── coordination/
├── conversations/
├── runtime_integration/
├── artifacts/
└── audit/
```

Cette arborescence doit refléter le Context Map.

---

# 130. Application topology reminder

```text
application/
├── execution/
├── recovery/
├── effects/
├── governance/
├── coordination/
├── conversations/
└── queries/
```

L’application orchestre les contextes sans les fusionner.

---

# 131. Adapter topology reminder

```text
adapters/outbound/
├── persistence/
├── runtimes/
├── connectors/
├── models/
├── storage/
├── security/
└── telemetry/
```

Les adapters ne deviennent jamais le centre du modèle.

---

# 132. Migration V1 mapping

## V1 Session

Doit être progressivement décomposée vers :

```text
Session
Conversation
RuntimeMessage
ConversationMessage
```

selon la sémantique réelle.

---

# 133. V1 RunStatus mapping

`WAITING_APPROVAL` V1 peut devenir :

```text
RunState.WAITING
+
RecoveryBlocker.APPROVAL_REQUIRED
```

---

# 134. V1 UNKNOWN_EFFECT mapping

Peut devenir :

```text
RunState.WAITING
+
EffectStatus.UNKNOWN
+
RecoveryBlocker.UNKNOWN_EFFECT
```

---

# 135. V1 Runner mapping

```text
Runner
→ NativeRuntimeAdapter
```

Le modèle du runtime est contenu derrière ACL.

---

# 136. V1 EffectRecord mapping

```text
EffectRecord
→ Effect
```

avec mapping explicite :

```text
PLANNED → NOT_STARTED/STARTED depending durable semantics
COMPLETED → SUCCEEDED
FAILED → FAILED
UNKNOWN → UNKNOWN
```

À préciser par ADR et migration.

---

# 137. V1 Approval mapping

La partie décision va dans Governance.

Les notions :

```text
CLAIMED
EXECUTED
```

doivent être reclassées dans la consommation/application, pas conservées comme décision métier d’Approval.

---

# 138. V1 Event mapping

Les événements actuels doivent être classifiés entre :

```text
RuntimeEvent
DomainEvent
TelemetryEvent
AuditEvent
```

---

# 139. Migration invariant

Aucune migration inter-contextes ne doit changer silencieusement une signification métier.

---

# 140. Context Map quality questions

Avant de placer un objet dans un contexte :

```text
Who owns its invariants?
Who decides its lifecycle?
Who is authoritative?
Who may mutate it?
What does the term mean here?
```

---

# 141. Smell — shared mutable model

Si deux contextes modifient la même classe, la frontière est mauvaise.

---

# 142. Smell — giant shared package

Si `shared/` grossit plus vite que les contexts, le modèle dérive vers un monolithe sans frontières.

---

# 143. Smell — infrastructure vocabulary in domain

Exemples :

```text
postgres_row
http_status
langgraph_node
github_pr_object
```

dans Domain = violation.

---

# 144. Smell — context hopping

Une operation qui traverse six repositories directement depuis un adapter inbound indique que l’Application Layer manque.

---

# 145. Smell — generic status

Éviter :

```text
Status
```

partagé.

Préférer :

```text
RunState
EffectStatus
ApprovalStatus
LeaseStatus
RuntimeStatus
ArtifactStatus
```

---

# 146. Smell — generic event

Éviter :

```text
Event
```

sans nature.

Préférer :

```text
DomainEvent
RuntimeEvent
AuditEvent
IntegrationEvent
```

---

# 147. Strategic DDD summary

Les huit contextes répondent à huit questions :

```text
Execution
→ What work is progressing?

Effects
→ What real-world consequence may occur?

Governance
→ Is it allowed and approved?

Coordination
→ Which worker may act?

Conversations
→ Who is communicating what?

Runtime Integration
→ How is the agent runtime controlled?

Artifacts
→ What durable output was produced?

Audit
→ Who did what, when and why?
```

---

# 148. Context Map final

```text
                         Conversations
                              │
                              ▼
                          Execution
                  ┌───────────┼───────────┐
                  ▼           ▼           ▼
               Effects    Governance   Coordination
                  │           │           │
                  ├───────────┼───────────┘
                  │           │
                  ▼           ▼
            Connectors    Identity/AuthZ
                  │
                  ▼
          External Systems

Execution ───────────────► Runtime Integration
                                │
                                ▼
                         Runtime Adapters
                                │
                                ▼
                        External Runtimes

Execution / Effects / Governance / Coordination
                  │
                  ├────────────► Artifacts
                  └────────────► Audit
```

---

# 149. Résumé

PyAgentsKit V2 ne doit pas être structuré autour de classes techniques.

Il doit être structuré autour de huit responsabilités métier autonomes :

```text
Execution
Effects
Governance
Coordination
Conversations
Runtime Integration
Artifacts
Audit
```

Les principes structurants sont :

```text
one concept → one authoritative context

references over shared object graphs

published language over internal model sharing

anti-corruption layers around external runtimes/providers

application orchestration over cross-context mutation

shared kernel kept minimal
```

Le principe fondamental est :

> **Les Bounded Contexts ne servent pas seulement à ranger le code ; ils empêchent les différentes significations de “Run”, “Effect”, “Approval”, “Session”, “Runtime” et “Event” de se mélanger jusqu’à rendre la sûreté impossible à raisonner.**

Le document suivant naturel est :

```text
../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md
```
