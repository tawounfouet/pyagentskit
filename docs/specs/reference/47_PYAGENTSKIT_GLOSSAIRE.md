# PyAgentsKit — Glossaire Canonique

**Document :** `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Ubiquitous Language — Référence canonique V2  
**Projet :** PyAgentsKit

## 1. Objet

Ce document définit le **vocabulaire canonique** de PyAgentsKit V2.

Il doit être utilisé de manière cohérente dans le code, la documentation, les tests, les API, les ADR, les runbooks, les logs structurés et les interfaces opérateur.

> **Un terme central possède une définition unique et une seule autorité sémantique.**

Le glossaire sert notamment à empêcher les confusions suivantes :

```text
Run                  != RuntimeInvocation
Session              != Conversation
RuntimeMessage       != ConversationMessage
ToolCall             != Effect
FAILED               != UNKNOWN
Retry                != Recovery
Retry                != Reconciliation
Approval             != Authorization
Actor                != Principal
Lease                != Lock
Heartbeat            != Ownership
Queue Delivery       != Ownership
RuntimeAdapter       != ModelAdapter
RuntimeAdapter       != Connector
DomainEvent          != IntegrationEvent
DomainEvent          != RuntimeEvent
AuditEvent           != TelemetryEvent
Repository           != Store
Transaction          != Distributed Transaction
Restore              != Safe Resume
Runtime completion   != Run success
Client timeout       != Effect failure
```

---

## 2. Règles générales de vocabulaire

Tout nouveau terme structurant doit :

1. avoir une définition explicite ;
2. appartenir à un Bounded Context précis ;
3. être distinct des concepts adjacents ;
4. être utilisé de façon homogène dans le code et les docs ;
5. être ajouté à ce glossaire s’il devient public ou transversal.

Les termes vagues `job`, `task`, `process`, `status`, `event`, `manager`, `service`, `utils`, `common` doivent être évités lorsqu’un terme métier plus précis existe.

---

# 3. Execution

## Run

**Contexte :** Execution.

Un `Run` représente une **intention de travail agentique durable** suivie par PyAgentsKit jusqu’à un état terminal.

```text
Run != process
Run != worker
Run != RuntimeInvocation
Run != Conversation
```

Un Run peut survivre à un crash process, une perte de worker, une reprise runtime ou un lease takeover.

## RunId

Identifiant durable et opaque d’un Run.

## RunState

État métier du Run. Valeurs candidates :

```text
CREATED
READY
RUNNING
WAITING
PAUSED
SUCCEEDED
FAILED
CANCELLED
```

## WAITING

État durable **non terminal** indiquant qu’un Run ne peut pas progresser tant qu’un blocker persiste.

Exemples : approval requise, Effect inconnu, dépendance indisponible, intervention manuelle.

## PAUSED

Suspension volontaire et explicite.

```text
PAUSED != WAITING
```

## Terminal State

État après lequel le Run ne reprend pas normalement.

## RuntimeInvocation

Tentative concrète d’exécution d’un Run par un runtime.

```text
Run 1 ──► RuntimeInvocation 1
       ├─► RuntimeInvocation 2
       └─► RuntimeInvocation N
```

## RuntimeInvocationStatus

État d’une invocation runtime particulière. Ne pas le confondre avec `RunState`.

## Checkpoint

Snapshot ou référence durable utile à la reprise.

```text
Checkpoint != source of truth for Effects
Checkpoint != source of truth for Approvals
```

## Recovery

Processus visant à reprendre de manière sûre un Run après interruption.

## RecoveryPlan

Plan calculé à partir de l’état durable autoritatif.

## RecoveryBlocker

Condition empêchant une progression sûre.

Exemples :

```text
APPROVAL_REQUIRED
UNKNOWN_EFFECT
NO_OWNERSHIP
RUNTIME_UNAVAILABLE
MANUAL_REVIEW
```

## NextAction

Action suivante calculée par RecoveryPlanner.

Valeurs candidates :

```text
ACQUIRE_LEASE
WAIT_FOR_APPROVAL
RECONCILE_EFFECT
RESUME_RUNTIME
RESTART_RUNTIME
COMPLETE_RUN
FAIL_RUN
CANCEL_RUN
MANUAL_INTERVENTION
```

## Manual Intervention

Résultat valide indiquant que la sûreté ne peut plus être prouvée automatiquement.

```text
Manual Intervention != Failure
```

---

# 4. Effects

## Effect

**Contexte :** Effects.

Représentation durable d’une **conséquence observable ou persistante dans le monde extérieur** gouvernée par PyAgentsKit.

Exemples :

```text
send message
git push
create PR
merge PR
deploy
payment
write ERP
terraform apply
```

## ToolCall

Demande d’appel d’outil produite par un runtime.

```text
ToolCall != Effect
```

Un ToolCall pur peut ne produire aucun Effect. Un Effect peut aussi provenir d’une autre source qu’un ToolCall.

## EffectIntent

Description durable de ce que PyAgentsKit entend provoquer avant exécution.

## Protected Effect

Effect nécessitant des garanties renforcées : authorization, approval, ownership, fencing, idempotency ou audit.

## EffectStatus

États canoniques :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

## NOT_STARTED

Intent durable existant, appel externe non lancé.

## STARTED

L’appel externe a commencé ou peut avoir commencé.

## SUCCEEDED

La conséquence externe est confirmée réussie.

Invariant :

```text
SUCCEEDED Effect is never implicitly replayed.
```

## FAILED

Échec confirmé.

```text
FAILED != UNKNOWN
```

## UNKNOWN

PyAgentsKit ne peut pas prouver si l’Effect externe a réussi ou échoué.

## RECONCILIATION_REQUIRED

État indiquant qu’une reconciliation doit avoir lieu avant toute décision potentiellement destructive.

## IdempotencyKey

Clé identifiant une intention logique.

## IdempotencyScope

Scope dans lequel une clé d’idempotency doit être unique.

## InputFingerprint

Empreinte stable des paramètres significatifs de l’intention.

```text
same key + different fingerprint = conflict
```

## ExternalReference

Référence à un objet externe : PR GitHub, deployment id, provider operation id, message id, etc.

## Reconciliation

Processus permettant de déterminer l’état réel d’un Effect ambigu.

```text
Reconciliation != Retry
```

## ReconciliationCase

Cas durable d’investigation lié à un Effect ambigu.

## ReconciliationPort

Port provider-specific permettant d’interroger la réalité externe.

## ReconciliationResult

Valeurs candidates :

```text
CONFIRMED_SUCCESS
CONFIRMED_FAILURE
STILL_UNKNOWN
NOT_FOUND
MANUAL_REQUIRED
```

## Retry

Nouvelle tentative d’une opération.

```text
Retry != Recovery
Retry != Reconciliation
```

---

# 5. Governance & Security

## Principal

Identité de sécurité authentifiée pouvant exercer une autorité.

## Actor

Identité logique participant à une interaction.

```text
Actor != Principal
```

Un agent peut être un Actor sans disposer d’une autorité de sécurité suffisante.

## Authentication

Répond à :

```text
Who are you?
```

## Authorization

Répond à :

```text
May this Principal perform this action?
```

## Approval

Décision humaine ou gouvernée autorisant ou refusant une action dans un scope précis.

```text
Approval != Authorization
```

## ApprovalStatus

États canoniques :

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

## ApprovalScope

Description immuable de ce qui est approuvé.

Peut contenir `EffectId`, `InputFingerprint`, ressource, opération et policy version.

## ApprovalDecision

```text
APPROVE
REJECT
CANCEL
```

## Approval Applicability

Règle déterminant si une Approval existante s’applique encore à l’intention actuelle.

## Scope Drift

Modification de l’action rendant une Approval historique non applicable.

## Segregation of Duties / SoD

Règle empêchant certaines combinaisons de rôles ou décisions par une même identité.

## Policy

Règle gouvernant les contrôles nécessaires.

## PolicyDecision

Valeurs possibles :

```text
ALLOW
DENY
REQUIRE_APPROVAL
REQUIRE_STRONGER_CONTROL
```

## PolicyEvaluator

Port/service évaluant les policies.

## SecurityContext

Contexte de sécurité d’un use case : Principal, TenantId, authentication context, scopes, correlation, request origin.

## SecretReference

Référence opaque à un secret stocké hors du domaine.

## SecretProvider

Port permettant de résoudre un SecretReference.

---

# 6. Coordination

## Lease

**Contexte :** Coordination.

Autorisation temporaire et durable donnant à un owner le droit de progresser sur une ressource.

```text
Lease != Lock
```

## LeaseId

Identifiant d’une Lease.

## ResourceIdentity

Identité canonique de la ressource protégée.

## Worker

Processus/instance capable d’exécuter des Runs.

```text
Worker != Runtime
Worker != Run
```

## Owner

Worker actuellement détenteur de l’autorité opérationnelle.

## FencingToken

Jeton monotone associé à une génération d’ownership.

Un système protégé doit rejeter un token plus ancien.

## Stale Worker

Worker dont le Lease n’est plus autoritatif.

## Zombie Worker

Worker continuant d’exécuter du code après perte d’autorité.

## OwnershipContext

Value Object regroupant typiquement :

```text
worker_id
lease_id
resource_id
fencing_token
expires_at
```

## Takeover

Acquisition d’une nouvelle génération d’ownership après expiration/perte de l’ancienne.

## Heartbeat

Signal de vie d’un worker.

```text
Heartbeat != Ownership
```

## Queue Delivery

Livraison d’un message au worker.

```text
Queue Delivery != Ownership
```

## Drain

État où un worker cesse d’accepter du nouveau travail tout en terminant ou relâchant les travaux en cours selon policy.

---

# 7. Conversations

## Session

Contexte durable global.

Une Session peut contenir :

```text
multiple Runs
multiple Conversations
MemoryEntries
```

## Conversation

Thread de communication durable.

```text
Conversation != Session
```

## Message / ConversationMessage

Unité durable de communication dans une Conversation.

## RuntimeMessage

Message natif de protocole utilisé par un runtime/model.

Exemples :

```text
system
user
assistant
tool
```

```text
RuntimeMessage != ConversationMessage
```

## Participant

Relation entre un Actor et une Conversation.

## MemoryEntry

Unité durable de mémoire structurée ou référencée dans un scope donné.

---

# 8. Runtime Integration

## Runtime

Système capable d’exécuter une logique agentique.

Exemples :

```text
Native PyAgents Runner
LangGraph
PydanticAI
OpenAI Agents
Codex
Claude Code
OpenCode
```

## AgentRuntimeAdapter

Port canonique permettant à PyAgentsKit de piloter un runtime sans dépendre de ses types natifs.

## RuntimeDescriptor

Description canonique du runtime : nom, adapter, version, capabilities, control level.

## RuntimeCapability

Capacité explicitement déclarée.

Exemples :

```text
START
RESUME
CANCEL
STATUS
EVENT_STREAM
NATIVE_CHECKPOINT
TOOL_INTERCEPTION
MESSAGE_STREAM
HUMAN_APPROVAL_HOOK
SESSION_RESUME
STRUCTURED_OUTPUT
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
```

## RuntimeHandle

Référence opaque permettant de retrouver une session/instance runtime.

## RuntimeEvent

Événement canonique issu d’un runtime.

```text
RuntimeEvent != DomainEvent
RuntimeEvent != AuditEvent
```

## RuntimeCheckpoint

Checkpoint natif d’un runtime.

## Model

Abstraction de génération LLM, notamment utilisée par le Native Runtime.

```text
Model != Runtime
```

## Model Adapter

Adapter vers un fournisseur/model LLM : OpenAI, Anthropic, Google, xAI, OpenRouter, Ollama.

```text
ModelAdapter != RuntimeAdapter
```

## Native Runtime

Runtime fourni historiquement par PyAgentsKit V1 via `Runner`.

## NativeRuntimeAdapter

Adapter V2 encapsulant le Runner V1.

## Control Level

Niveau réel de contrôle fourni par un runtime.

Candidats :

```text
OBSERVE_ONLY
LIFECYCLE_CONTROL
FULL_INTERCEPTION
```

## Capability Negotiation

Vérification explicite qu’un adapter possède une capacité requise.

---

# 9. Connectors & External Systems

## Connector

Port/adaptor permettant d’interagir avec un système externe métier.

Exemples :

```text
GitHub
GitLab
Slack
Jira
ERP
AWS
Azure
```

```text
Connector != RuntimeAdapter
```

## ConnectorDescriptor

Description canonique d’un connector.

## ConnectorCapability

Exemples :

```text
READ
WRITE
NATIVE_IDEMPOTENCY
RECONCILIATION
WEBHOOKS
POLLING
PAGINATION
BATCHING
```

## ConnectorRegistry

Registry explicite des Connectors configurés.

## Generic HTTP Connector

Adapter de transport générique.

```text
Generic HTTP != Provider semantics
```

## External System

Système hors du cœur PyAgentsKit auquel un Connector parle.

## Provider

Fournisseur externe d’une capacité. Toujours qualifier : LLM provider, storage provider, identity provider, etc.

## Provider Payload

Objet/request/response natif d’un SDK provider.

Il ne doit pas devenir le modèle du core.

---

# 10. Artifacts

## Artifact

Production durable identifiable générée ou enregistrée par PyAgentsKit.

Exemples : fichier, patch, report, build output, structured payload.

## ArtifactId

Identifiant durable.

## ArtifactReference

Référence stable à un Artifact.

## Blob

Contenu binaire ou volumineux stocké hors aggregate principal.

## BlobStore

Port technique de stockage de blobs.

## ArtifactStore

Port de gestion des Artifacts ou de leurs métadonnées selon design final.

## Checksum

Empreinte permettant de vérifier l’intégrité d’un Artifact.

## Provenance

Informations décrivant l’origine et le contexte de production d’un Artifact.

---

# 11. Events, Audit & Observability

## DomainEvent

Fait métier interne émis par un aggregate/context.

Exemples :

```text
RunStarted
EffectSucceeded
ApprovalApproved
LeaseTakenOver
```

## IntegrationEvent

Message publié hors du contexte pour informer d’autres composants.

```text
IntegrationEvent != DomainEvent
```

## AuditEvent

Événement durable de responsabilité décrivant :

```text
who
did what
when
why
on what
with what evidence
```

## TelemetryEvent

Événement technique destiné à l’observabilité.

## Log

Enregistrement technique destiné au diagnostic.

```text
Log != AuditEvent
```

## Metric

Mesure numérique agrégée.

## Trace

Représentation distribuée d’un chemin d’exécution.

## Span

Unité d’une Trace.

## CorrelationContext

Informations permettant de relier plusieurs opérations : correlation_id, trace_id, request_id.

## AuditStore

Store append-oriented des AuditEvents.

## TelemetryPort

Port permettant d’émettre métriques, spans et événements techniques.

---

# 12. DDD & Hexagonal Architecture

## Bounded Context

Frontière dans laquelle un vocabulaire et un modèle métier sont cohérents et autoritatifs.

## Aggregate

Groupe cohérent d’objets métier contrôlé par une Aggregate Root.

## Aggregate Root

Entité par laquelle les mutations cohérentes d’un aggregate passent.

## Entity

Objet métier possédant une identité durable.

## Value Object

Objet défini par sa valeur, sans identité métier autonome.

## Domain Service

Service portant une règle métier ne s’attachant naturellement à aucun objet unique.

## Application Service

Service orchestrant un cas d’usage à travers Domain et Ports.

```text
Application Service != Domain Service
```

## Port

Interface définie par le core/Application décrivant une capacité attendue.

## Inbound Port

Ce qu’un acteur externe peut demander à PyAgentsKit.

## Outbound Port

Ce dont PyAgentsKit a besoin d’un système externe.

## Adapter

Implémentation technique d’un Port.

## Inbound Adapter

Python SDK, CLI, HTTP API, Queue Consumer, Webhook Receiver, Worker Loop.

## Outbound Adapter

PostgreSQL, runtime SDK, Connector, S3, OIDC, OpenTelemetry, etc.

## Anti-Corruption Layer / ACL

Couche traduisant un modèle externe vers le modèle canonique PyAgentsKit.

## Published Language

Petit contrat stable entre Bounded Contexts.

## Shared Kernel

Ensemble minimal de concepts communs réellement stables.

## Composition Root

Lieu unique où ports et implementations concrètes sont assemblés.

Dans la cible :

```text
bootstrap/
```

---

# 13. Application Layer

## Use Case

Interaction applicative cohérente réalisant une intention externe.

Exemples :

```text
CreateRun
ResumeRun
ExecuteEffect
Approve
TakeoverLease
```

## Command

Demande pouvant modifier l’état.

## Query

Demande de lecture sans mutation.

## Read Model

Projection optimisée pour la lecture.

```text
Read Model != authoritative aggregate
```

## View

DTO public/applicatif orienté lecture : `RunView`, `EffectView`, `ApprovalView`.

## DTO

Data Transfer Object sans autorité métier intrinsèque.

## PyAgentsKit Facade

Façade publique regroupant les principales commandes et queries.

## Sync Facade

Façade synchrone au-dessus de l’API async canonique.

```text
Sync facade != different semantics
```

## Client Timeout

Expiration côté appelant.

```text
Client timeout != Effect failure
```

---

# 14. Persistence

## Repository

Abstraction de persistance orientée aggregate métier.

## Store

Abstraction de stockage technique.

```text
Repository != Store
```

Exemples :

```text
RunRepository
EffectRepository

BlobStore
AuditStore
OutboxStore
InboxStore
```

## Unit of Work / UoW

Boundary transactionnelle locale coordonnant plusieurs opérations de persistence.

## Transaction

Unité atomique locale.

```text
Transaction != Distributed Transaction
```

## Optimistic Concurrency

Stratégie utilisant une version attendue / CAS.

## Compare-and-Swap / CAS

Mise à jour conditionnelle sur une version attendue.

## Pessimistic Locking

Verrouillage explicite pendant une transaction courte.

## Outbox

Store transactionnel contenant les IntegrationEvents à publier après commit.

## Inbox

Store permettant de dédupliquer les messages externes.

## Primary Database

Source autoritative pour writes et safety-critical reads.

## Read Replica

Copie potentiellement en retard.

```text
Read Replica != safety authority
```

## Schema Version

Version du schéma persistence.

## PersistenceCorruption

État stocké impossible ou incompatible avec le modèle attendu.

## ConcurrencyConflict

Conflit de version/CAS.

## IdempotencyConflict

Même idempotency key, intention incompatible.

---

# 15. Distributed Systems & Reliability

## Idempotency

Propriété selon laquelle répéter la même intention logique ne crée pas une nouvelle conséquence métier distincte.

## Deduplication

Détection d’un input déjà traité.

## At-Least-Once Delivery

Mode de transport où un message peut être livré plusieurs fois.

## Exactly-Once

Garantie globale à ne pas revendiquer abusivement.

PyAgentsKit préfère :

```text
idempotency
deduplication
fencing
reconciliation
```

## Safety

Empêcher les actions incorrectes ou non autorisées.

## Liveness

Permettre au système de continuer à progresser.

```text
Safety != Liveness
```

## Fail Closed

Bloquer une action critique lorsque l’autorité ou la sécurité ne peut pas être prouvée.

## Graceful Shutdown

Arrêt ordonné.

```text
Graceful Shutdown != safety primitive
```

## Durable Execution

Capacité à reprendre un travail à partir d’un état durable, y compris sur un autre worker.

## Durable State

État persistant nécessaire à une reprise sûre.

## Source of Truth

État autoritatif utilisé pour les décisions critiques.

## Restore

Restauration d’un état persistence antérieur.

```text
Restore != Safe Resume
```

## PITR

Point-In-Time Recovery. Peut créer une divergence avec des Effects externes déjà accomplis.

## Crash Window

Fenêtre dans laquelle une panne peut rendre l’issue ambiguë.

```text
W1 before durable intent
W2 after durable intent, before send
W3 after send, before response
W4 after response, before durable outcome
W5 after durable outcome, before next Run progress
```

---

# 16. Operations

## Readiness

Capacité actuelle d’une instance à accepter correctement du travail.

## Liveness Probe

Indique si le process lui-même fonctionne.

## Health

État de certaines dépendances/composants.

```text
Health != Readiness
```

## Kill Switch

Mécanisme permettant de bloquer rapidement certaines actions sensibles.

## Protected Effects Freeze

État empêchant de nouveaux Protected Effects.

## Safety Gate

Condition explicite bloquant une progression dangereuse.

## Operational Blocker

Condition nécessitant une action opérateur.

## Evidence

Information vérifiable supportant une décision.

## Decision Evidence

Evidence attachée à une décision Governance/Audit.

## Qualification Evidence

Preuve issue des tests de qualification.

## Production Qualified

Statut indiquant qu’un adapter/composant a satisfait les critères définis pour le niveau production.

## Adapter Qualification Level

Niveaux proposés :

```text
L0 fake
L1 contract
L2 integration
L3 failure
L4 production qualified
```

---

# 17. Coding Agents

## Coding Agent

Runtime spécialisé dans le travail sur code/repository/workspace.

Exemples :

```text
Codex
Claude Code
OpenCode
```

## Workspace

Environnement de travail isolé.

## Workspace Isolation

Mesures empêchant un coding agent d’affecter des espaces non autorisés.

## CommandExecution

Exécution d’une commande OS dans un environnement gouverné.

## Command Boundary

Frontière de validation, autorisation et exécution des commandes.

## RepositoryReference

Référence canonique à un repository.

## BranchReference

Référence à une branche.

## CommitReference

Référence à un commit.

## PatchArtifact

Artifact représentant un patch/diff.

## Protected Coding Effect

Exemples :

```text
git push
PR create
PR merge
package publish
deploy
terraform apply
```

## Build Evidence

Résultat de compilation/build.

## Test Evidence

Résultat de tests utilisé comme preuve.

---

# 18. Migration V1 → V2

## Strangler Pattern

Migration progressive remplaçant l’ancien système autour de frontières explicites.

## Compatibility Boundary

Couche isolant les contrats/comportements V1.

## Legacy

Composant historique conservé pour compatibilité.

## Deprecated

Encore disponible mais déconseillé pour les nouveaux usages.

## Backfill

Copie/transformation progressive des données vers le nouveau modèle.

## Shadow Read

Lecture parallèle V1/V2 à des fins de comparaison.

## Dual Write

Écriture dans deux modèles ; à minimiser.

## Cutover

Moment où la V2 devient source de vérité.

## Forward-Fix

Correction vers l’avant après cutover.

## Expand-Contract Migration

```text
expand
backfill
verify
switch
contract
```

## Migration Checkpoint

Position durable permettant de reprendre une migration interrompue.

## Migration Ambiguity

Donnée legacy impossible à interpréter avec certitude.

Principe :

```text
preserve ambiguity
```

## Legacy Evidence

Donnée historique utile mais non autoritative selon le nouveau modèle.

---

# 19. Build vs Buy vs Integrate

## BUILD

PyAgentsKit implémente directement la capacité car elle fait partie de son différenciateur sémantique.

Exemples :

```text
Effect semantics
RecoveryPlanner
Approval model
Lease/Fencing semantics
```

## BUY / USE

PyAgentsKit consomme une capacité standard existante.

Exemples :

```text
PostgreSQL
OpenTelemetry
S3-compatible storage
OIDC provider
```

## INTEGRATE

PyAgentsKit encapsule une capacité externe derrière un Port/Adapter.

Exemples :

```text
LangGraph
GitHub
S3
OIDC
```

## Commodity Infrastructure

Infrastructure largement standardisée que PyAgentsKit ne doit pas réimplémenter.

## Reliability Layer

Couche ajoutant durability, Effect safety, approvals, coordination, recovery et audit autour des runtimes.

## Framework-Neutral

Les sémantiques core ne dépendent pas d’un framework agentique précis.

## Provider-Neutral

Plusieurs fournisseurs peuvent remplir un même rôle derrière une abstraction.

---

# 20. Termes V1 à requalifier

| Terme V1 | Signification V1 | Cible V2 |
|---|---|---|
| `Session` | conversation identity/history | `Session` global + `Conversation` |
| `Message` | runtime/model message | `RuntimeMessage` ou `ConversationMessage` |
| `WAITING_APPROVAL` | Run status | `WAITING` + blocker `APPROVAL_REQUIRED` |
| `UNKNOWN_EFFECT` | Run status | `WAITING` + `Effect.UNKNOWN` |
| `EffectStatus.COMPLETED` | Effect success | `SUCCEEDED` |
| `ApprovalStatus.CLAIMED` | consumption state | hors lifecycle décision |
| `ApprovalStatus.EXECUTED` | consumption/execution | reclassé Effect/Execution |
| `RunStore` | Run + effects + checkpoints + journal | repositories/stores séparés |
| `SessionStore` | session/history | repositories Conversations séparés |
| `LeaseStore` | coordination persistence | `LeaseRepository` selon ADR final |

Règle :

> **La migration doit être sémantique, pas un simple renommage.**

---

# 21. Synonymes déconseillés

| Éviter | Préférer |
|---|---|
| job | Run |
| task | Run / work item qualifié |
| process | RuntimeInvocation / OS process |
| lock | Lease si l’on parle d’ownership distribué |
| tool effect | Effect, si conséquence durable |
| agent session | préciser Session, Conversation ou RuntimeHandle |
| event | DomainEvent / RuntimeEvent / AuditEvent / IntegrationEvent |
| status | RunState / EffectStatus / ApprovalStatus / RuntimeStatus |
| manager | use case / registry / repository précis |
| generic service | responsabilité/use case explicite |

---

# 22. Règles de nommage

## Classes métier

```text
Run
Effect
Approval
Lease
Conversation
Artifact
```

## Value Objects

```text
RunId
EffectId
FencingToken
InputFingerprint
OwnershipContext
```

## Use Cases

```text
CreateRun
ResumeRun
ExecuteEffect
ApproveRequest
TakeoverLease
```

## Repositories

```text
RunRepository
EffectRepository
ApprovalRepository
```

## Adapters

```text
PostgresRunRepository
NativeRuntimeAdapter
GitHubConnector
S3BlobStore
```

## Enums

Toujours qualifiés :

```text
RunState
EffectStatus
ApprovalStatus
RuntimeStatus
WorkerState
```

## Events

Toujours préciser le fait :

```text
RunStarted
EffectSucceeded
ApprovalApproved
LeaseTakenOver
```

## Erreurs

Nommer la cause :

```text
InvalidRunTransition
EffectAlreadySucceeded
ApprovalExpired
StaleOwnership
UnsupportedCapability
```

---

# 23. Ubiquitous Language par Bounded Context

## Execution

```text
Run
RunState
RuntimeInvocation
Checkpoint
RecoveryPlan
RecoveryBlocker
NextAction
```

## Effects

```text
Effect
EffectIntent
EffectStatus
IdempotencyKey
InputFingerprint
ExternalReference
ReconciliationCase
```

## Governance

```text
Principal
Approval
ApprovalScope
Policy
PolicyDecision
Authorization
SegregationOfDuties
```

## Coordination

```text
Lease
FencingToken
OwnershipContext
Worker
Takeover
Heartbeat
ResourceIdentity
```

## Conversations

```text
Session
Conversation
ConversationMessage
Actor
Participant
MemoryEntry
```

## Runtime Integration

```text
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeStatus
RuntimeEvent
RuntimeCheckpoint
```

## Artifacts

```text
Artifact
ArtifactReference
Checksum
Provenance
Blob
```

## Audit

```text
AuditEvent
AuditSubject
AuditAction
AuditEvidence
AuditReason
```

---

# 24. Glossary Invariants

```text
GLS-INV-01  Run != RuntimeInvocation.
GLS-INV-02  Session != Conversation.
GLS-INV-03  RuntimeMessage != ConversationMessage.
GLS-INV-04  ToolCall != Effect.
GLS-INV-05  FAILED != UNKNOWN.
GLS-INV-06  Retry != Recovery.
GLS-INV-07  Retry != Reconciliation.
GLS-INV-08  Approval != Authorization.
GLS-INV-09  Actor != Principal.
GLS-INV-10  Lease != Lock.
GLS-INV-11  Heartbeat != Ownership.
GLS-INV-12  Queue Delivery != Ownership.
GLS-INV-13  RuntimeAdapter != ModelAdapter.
GLS-INV-14  RuntimeAdapter != Connector.
GLS-INV-15  DomainEvent != IntegrationEvent != RuntimeEvent != AuditEvent.
GLS-INV-16  Repository != Store.
GLS-INV-17  Transaction != Distributed Transaction.
GLS-INV-18  Restore != Safe Resume.
GLS-INV-19  Runtime completion != Run success.
GLS-INV-20  Client timeout != Effect failure.
```

---

# 25. Gouvernance du glossaire

Toute évolution d’un terme structurant suit :

```text
identify owning context
→ assess architecture impact
→ ADR if needed
→ update glossary
→ update code/docs/tests
→ update V1→V2 mapping if applicable
```

Une redéfinition sémantique d’un terme public peut constituer une breaking change même si aucune signature Python ne change.

Les PRs doivent poser au minimum ces questions :

```text
Does this term already exist?
Does it have another meaning?
Which bounded context owns it?
Is this only a synonym?
Can a canonical term be reused?
```

---

# 26. Index alphabétique condensé

## A
ACL, Actor, Adapter, Aggregate, Aggregate Root, AmbiguousOutcome, Approval, ApprovalScope, Artifact, AuditEvent, Authentication, Authorization.

## B
Backfill, Blob, BlobStore, Bounded Context, Broker, Build, Build Evidence.

## C
Capability Negotiation, CAS, Checkpoint, Client Timeout, Command, CommandExecution, Compatibility Boundary, Composition Root, Connector, Conversation, CorrelationContext, Crash Window, Cutover.

## D
DataPolicy, Deduplication, DomainEvent, Domain Service, DTO, Durable Execution, Durable State.

## E
Effect, EffectIntent, EffectStatus, Entity, Evidence, ExternalReference, External Runtime, External System.

## F
Fail Closed, FAILED, FencingToken, Forward-Fix, Framework-Neutral.

## G
Generic HTTP Connector, Graceful Shutdown, Guardrail, GuardrailPipeline.

## H
Heartbeat, Health, High Assurance Profile.

## I
Idempotency, IdempotencyKey, IdempotencyScope, IdentityProviderPort, Inbox, InputFingerprint, IntegrationEvent.

## L
Lease, Liveness, Local Profile, Log.

## M
Manual Intervention, Manual Resolution, MemoryEntry, Message, Metric, Migration Checkpoint, Model, Model Adapter, Multi-Tenancy.

## N
Native Runtime, NativeRuntimeAdapter, NextAction, NOT_STARTED.

## O
Optimistic Concurrency, Outbox, Outbound Adapter, Outbound Port, OwnershipContext.

## P
Participant, PAUSED, PITR, Policy, PolicyDecision, Port, Principal, Protected Effect, Provider, Published Language.

## Q
Query, Queue Delivery.

## R
Read Model, Readiness, Reconciliation, Recovery, RecoveryPlan, Repository, Retry, Run, RunState, Runtime, RuntimeCapability, RuntimeEvent, RuntimeHandle, RuntimeInvocation.

## S
Safety, Safety Gate, Sandbox, SecretProvider, SecretReference, Session, Shared Kernel, Span, STARTED, Store, Strangler Pattern, SUCCEEDED, Supply Chain.

## T
Takeover, TelemetryEvent, Tenant, TenantId, Tool, ToolCall, ToolRisk, Trace, Transaction, Trust Boundary.

## U
Ubiquitous Language, Unit of Work, UNKNOWN, UnsupportedCapability, Use Case.

## V
Value Object, View.

## W
WAITING, Worker, Workspace.

---

# 27. Acceptance Criteria

Le glossaire est correctement appliqué si :

1. chaque terme central possède une définition unique ;
2. chaque concept a un contexte propriétaire clair ;
3. les distinctions `GLS-INV-*` sont reflétées dans le code ;
4. les enums sont qualifiés ;
5. les API publiques utilisent le vocabulaire canonique ;
6. les mappings V1→V2 utilisent des noms distincts lorsque les significations divergent ;
7. tout ADR introduisant un terme métier met à jour le glossaire ;
8. `job`, `task`, `process`, `event` et `status` ne sont pas utilisés comme synonymes vagues dans le core ;
9. les termes runtime/provider restent qualifiés ;
10. ce document est utilisé comme référence de review.

---

# 28. Definition of Done

`../reference/47_PYAGENTSKIT_GLOSSAIRE.md` est mature lorsque :

1. les huit Bounded Contexts sont couverts ;
2. tous les aggregates V2 sont définis ;
3. les principaux Value Objects sont couverts ;
4. tous les états safety-critical sont distingués ;
5. les termes V1 divergents sont identifiés ;
6. les synonymes ambigus sont documentés ;
7. les conventions code/API/DB sont alignées ;
8. l’index alphabétique est maintenu ;
9. les ADR constitutionnels référencent le glossaire ;
10. les documents ultérieurs utilisent ce vocabulaire.

---

# 29. Résumé

Le langage canonique de PyAgentsKit V2 n’est pas seulement une convention stylistique.

Il matérialise les frontières de responsabilité du système :

```text
Execution      → Run / RuntimeInvocation / Recovery
Effects        → Effect / Idempotency / Reconciliation
Governance     → Principal / Approval / Policy
Coordination   → Lease / Fencing / Ownership
Conversations  → Session / Conversation / Message
Runtime        → RuntimeHandle / Capabilities / RuntimeEvent
Artifacts      → Artifact / Checksum / Provenance
Audit          → AuditEvent / Evidence / Responsibility
```

> **Dans un système distribué de fiabilité, les mots portent directement les garanties de sûreté : employer le mauvais terme conduit souvent à attribuer la mauvaise responsabilité au mauvais composant.**

Le document suivant naturel est :

```text
../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md
```
