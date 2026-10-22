# PyAgentsKit — Application Services & Use Cases

**Document :** `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Application Architecture — Use Cases & Orchestration  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`

---

# 1. Objet

Ce document définit la **couche Application** de PyAgentsKit V2.

Il formalise :

- les Application Services ;
- les Use Cases ;
- les Commands ;
- les Queries ;
- les Read Models ;
- l’orchestration inter-contextes ;
- les transactions ;
- la gestion des ports ;
- les règles d’idempotence ;
- la gestion des erreurs ;
- la coordination des Effects ;
- la reprise durable ;
- la frontière entre Domain Service et Application Service ;
- la structure de packages recommandée.

Le principe directeur est :

> **Le domaine décide ce qui est valide ; l’application décide dans quel ordre mobiliser les domaines et les ports pour réaliser un cas d’usage.**

---

# 2. Rôle de la couche Application

La couche Application répond à :

```text
What does the system do for an external actor?
```

et non :

```text
What business rule makes this valid?
```

La première question appartient à Application.

La seconde appartient au Domain.

---

# 3. Application Service ≠ Domain Service

## Application Service

Responsabilité :

```text
orchestration
transactions
port calls
loading aggregates
saving aggregates
calling external capabilities
publishing events
```

## Domain Service

Responsabilité :

```text
business rule
invariant
domain decision
```

---

# 4. Exemple

Mauvais :

```python
class ResumeRunService:
    async def resume(...):
        if effect.status == "UNKNOWN":
            ...
```

si la règle métier est cachée dans Application.

Bon :

```text
Application
loads state
↓
Domain/RecoveryPlanner
decides NextAction
↓
Application executes that plan
```

---

# 5. Structure cible

```text
application/
├── execution/
├── recovery/
├── effects/
├── governance/
├── coordination/
├── conversations/
├── artifacts/
├── queries/
├── ports/
└── shared/
```

---

# 6. Use Case categories

```text
UC-EXEC   Execution
UC-REC    Recovery
UC-EFF    Effects
UC-GOV    Governance
UC-COORD  Coordination
UC-CONV   Conversations
UC-ART    Artifacts
UC-QUERY  Queries / Read Models
UC-ADMIN  Administration / Operations
```

---

# 7. Command vs Query

## Command

Peut modifier l’état.

```text
CreateRun
StartRun
ResumeRun
Approve
Reject
ReconcileEffect
TakeoverLease
```

## Query

Lecture seule.

```text
GetRun
ListEffects
GetApproval
GetTimeline
```

Principe :

```text
Command may mutate.
Query never mutates.
```

---

# 8. CQRS léger

PyAgentsKit peut utiliser un CQRS léger :

```text
Commands
→ Aggregates / repositories

Queries
→ Read models / projections
```

sans imposer :

```text
full event sourcing
```

---

# 9. Command objects

Exemple :

```python
@dataclass(frozen=True)
class CreateRunCommand:
    session_id: SessionId
    runtime: RuntimeDescriptor
    tenant_id: TenantId
    actor: ActorReference
    metadata: Mapping[str, Any]
```

---

# 10. Query objects

Exemple :

```python
@dataclass(frozen=True)
class GetRunQuery:
    run_id: RunId
    tenant_id: TenantId
```

---

# 11. Application Result

Les use cases retournent de préférence :

```text
View
Result
Reference
```

et non directement l’aggregate mutable.

---

# 12. Use Case UC-EXEC-001 — CreateRun

## Intent

Créer un Run durable.

## Entrées

```text
SessionId
RuntimeDescriptor
TenantId
ActorReference
optional ConversationId
optional metadata
```

## Orchestration

```text
validate request
↓
load Session
↓
Domain creates Run
↓
persist Run
↓
append AuditEvent
↓
return RunView
```

---

# 13. CreateRun — invariants

```text
Session exists
tenant matches
runtime descriptor allowed
Run begins in CREATED/READY according lifecycle
```

---

# 14. Use Case UC-EXEC-002 — StartRun

## Orchestration

```text
load Run
↓
validate transition
↓
resolve runtime
↓
acquire ownership if distributed
↓
create RuntimeInvocation
↓
runtime.start()
↓
persist RuntimeHandle / invocation
↓
transition Run
↓
audit
```

---

# 15. StartRun — important rule

Ne jamais :

```text
start runtime
before
durable Run intent exists
```

---

# 16. Use Case UC-EXEC-003 — ResumeRun

C’est l’un des use cases centraux.

## Orchestration

```text
load Run
↓
if terminal → return
↓
acquire/validate Lease
↓
revalidate SecurityContext
↓
load blocking Effects
↓
load Approvals
↓
inspect runtime
↓
compute RecoveryPlan
↓
execute NextAction
↓
persist resulting state
```

---

# 17. ResumeRun — rule

```text
resume != blindly call runtime.resume()
```

Il s’agit d’abord d’une décision de recovery.

---

# 18. Use Case UC-EXEC-004 — PauseRun

## Intent

Suspendre volontairement un Run à une frontière sûre.

## Orchestration

```text
load Run
↓
validate pause allowed
↓
checkpoint if applicable
↓
pause/cancel runtime according capability
↓
persist PAUSED
↓
release Lease if policy
```

---

# 19. Use Case UC-EXEC-005 — CancelRun

## Important distinction

```text
Cancel Run
!=
rollback Effects
```

---

# 20. CancelRun flow

```text
load Run
↓
validate cancellation
↓
runtime.cancel if supported
↓
mark future progression cancelled
↓
preserve existing Effect outcomes
↓
audit
```

---

# 21. Use Case UC-EXEC-006 — CompleteRun

Peut être interne à Application.

Conditions :

```text
runtime completed
no unresolved blocker
no required Effect unresolved
completion invariant satisfied
```

---

# 22. Use Case UC-REC-001 — RecoverRun

Cœur de la reprise.

## Entrées

```text
RunId
WorkerId
RecoveryTrigger
```

---

# 23. RecoverRun flow

```text
load durable Run
↓
validate ownership
↓
load checkpoints
↓
load unresolved Effects
↓
load Approvals
↓
inspect runtime
↓
RecoveryPlanner.plan()
↓
execute actions
```

---

# 24. RecoveryTrigger

Valeurs candidates :

```text
WORKER_START
LEASE_TAKEOVER
PROCESS_RESTART
MANUAL_RESUME
APPROVAL_DECIDED
RECONCILIATION_COMPLETED
RUNTIME_EVENT
```

---

# 25. RecoveryPlanner

Le planner peut appartenir :

```text
application/recovery/
```

s’il orchestre plusieurs contextes.

Les règles locales restent dans les Domain Services.

---

# 26. NextAction execution

Exemple :

```text
ACQUIRE_LEASE
→ Coordination use case

RECONCILE_EFFECT
→ Effects use case

WAIT_FOR_APPROVAL
→ persist waiting state

RESUME_RUNTIME
→ Runtime port

MANUAL_INTERVENTION
→ create operational blocker
```

---

# 27. Use Case UC-EFF-001 — PlanEffect

## Intent

Créer durablement une intention avant effet externe.

## Flow

```text
receive EffectIntent
↓
classify risk
↓
compute idempotency/fingerprint
↓
check Governance
↓
reserve Effect
↓
return EffectReference
```

---

# 28. PlanEffect — safety rule

```text
durable intent
before
external mutation
```

---

# 29. Use Case UC-EFF-002 — ExecuteEffect

## Flow

```text
load Effect
↓
ensure state allows execution
↓
validate ownership
↓
validate authorization
↓
validate Approval if required
↓
resolve Connector/Tool capability
↓
transition STARTED
↓
invoke external system
↓
persist outcome
↓
audit
```

---

# 30. ExecuteEffect — forbidden behavior

```text
generic retry around whole use case
```

car cela peut rejouer l’appel externe.

---

# 31. Use Case UC-EFF-003 — ReconcileEffect

## Flow

```text
load UNKNOWN Effect
↓
resolve provider-specific ReconciliationPort
↓
query external state
↓
collect evidence
↓
Domain decides reconciliation result
↓
persist
```

---

# 32. Use Case UC-EFF-004 — ResolveEffectManually

Exige :

```text
authorized Principal
reason
evidence
scope
audit
```

---

# 33. Manual resolution outcomes

```text
CONFIRM_SUCCESS
CONFIRM_FAILURE
RETRY_ALLOWED
KEEP_UNKNOWN
```

selon policy finale.

---

# 34. Use Case UC-EFF-005 — RetryEffect

Ce use case ne peut être invoqué que si :

```text
Effect retry is explicitly safe
```

---

# 35. RetryEffect preconditions

Exemples :

```text
NOT_STARTED
FAILED with safe retry policy
UNKNOWN reconciled as NOT_APPLIED
```

---

# 36. Use Case UC-GOV-001 — RequestApproval

## Flow

```text
Effect/Action requires approval
↓
create immutable ApprovalScope
↓
persist Approval PENDING
↓
publish notification event
↓
Run may become WAITING
```

---

# 37. Use Case UC-GOV-002 — Approve

## Flow

```text
load Approval
↓
validate principal
↓
validate status
↓
validate expiry
↓
validate SoD
↓
apply APPROVED
↓
persist
↓
Outbox wake-up
↓
audit
```

---

# 38. Use Case UC-GOV-003 — Reject

Même logique.

---

# 39. Use Case UC-GOV-004 — RevalidateApproval

Critique après :

```text
takeover
resume
scope change
policy change
tenant change
```

---

# 40. RevalidateApproval checks

```text
approval status
scope fingerprint
expiry
principal validity
policy version
target Effect identity
```

---

# 41. Use Case UC-COORD-001 — AcquireLease

## Flow

```text
ResourceIdentity
WorkerId
TenantId
↓
LeaseRepository.acquire()
↓
OwnershipContext
```

---

# 42. Use Case UC-COORD-002 — RenewLease

```text
current Lease
↓
validate owner
↓
renew
↓
new expires_at
```

---

# 43. Use Case UC-COORD-003 — ReleaseLease

Explicit release.

Safety ne dépend pas de son succès.

---

# 44. Use Case UC-COORD-004 — TakeoverLease

## Preconditions

```text
current lease expired
or authorized force takeover
```

## Result

```text
strictly greater FencingToken
```

---

# 45. Use Case UC-COORD-005 — DrainWorker

## Flow

```text
Worker ACCEPTING
↓
DRAINING
↓
stop admissions
↓
wait boundedly
↓
release/expire work
↓
STOPPED
```

---

# 46. Use Case UC-CONV-001 — CreateSession

Crée le contexte durable global.

---

# 47. Use Case UC-CONV-002 — CreateConversation

Associe un thread à :

```text
Session
Participants
Purpose
```

---

# 48. Use Case UC-CONV-003 — AppendMessage

## Flow

```text
load Conversation
↓
validate open/active
↓
resolve sender
↓
deduplicate if needed
↓
append Message
↓
publish event
```

---

# 49. AppendMessage — rule

Un Message texte ne doit pas automatiquement déclencher :

```text
Approval
Authorization
Effect
```

sans use case explicite.

---

# 50. Use Case UC-CONV-004 — AddParticipant

Gère participation sans modifier directement Actor identity.

---

# 51. Use Case UC-CONV-005 — WriteMemory

Scope explicite :

```text
Session
Conversation
Actor
Run
```

selon modèle final.

---

# 52. Use Case UC-ART-001 — RegisterArtifact

## Flow

```text
compute/provide checksum
↓
store bytes through BlobStore
↓
persist metadata
↓
return ArtifactReference
```

---

# 53. Artifact transactional nuance

Blob storage et PostgreSQL ne partagent pas une transaction distribuée.

Donc besoin :

```text
staging
status
reconciliation
garbage collection
```

---

# 54. Use Case UC-ART-002 — VerifyArtifact

```text
load metadata
↓
load/check blob
↓
verify checksum
```

---

# 55. Use Case UC-QUERY-001 — GetRun

Retour :

```text
RunView
```

et non `Run` aggregate.

---

# 56. Use Case UC-QUERY-002 — GetRunTimeline

Peut joindre :

```text
Run
RuntimeInvocation
Effect
Approval
Lease
Audit
```

en read-only.

---

# 57. Timeline authority rule

La Timeline est une projection.

Elle n’est pas source de vérité métier.

---

# 58. Use Case UC-QUERY-003 — ListUnresolvedEffects

Utilisé pour ops/reconciliation.

---

# 59. Use Case UC-QUERY-004 — ListPendingApprovals

Read model.

---

# 60. Use Case UC-QUERY-005 — WorkerStatus

Agrège :

```text
worker state
lease count
health
readiness
```

---

# 61. Use Case UC-ADMIN-001 — ForceTakeover

Admin-only.

Exige :

```text
authorization
reason
audit
new fencing token
```

---

# 62. Use Case UC-ADMIN-002 — FreezeProtectedEffects

Kill switch.

---

# 63. Use Case UC-ADMIN-003 — ResumeProtectedEffects

Ne réactive pas automatiquement les Runs.

Ils doivent être revalidés.

---

# 64. Use Case UC-ADMIN-004 — RepairState

Très restreint.

Chaque repair doit être :

```text
explicit
authorized
audited
reversible where possible
```

---

# 65. Use Case UC-ADMIN-005 — MigrationControl

Expose éventuellement :

```text
inspect
verify
cutover
```

mais seulement dans tooling/admin plane.

---

# 66. Application transaction model

Application détermine la transaction locale.

Exemple :

```text
begin UoW
load Effect
change state
append Outbox
save Effect
commit
```

---

# 67. No remote call inside long transaction

Ne pas garder transaction DB ouverte pendant :

```text
LLM call
GitHub call
deployment
external API
```

---

# 68. Effect execution transaction pattern

Préférer :

```text
TX1
reserve STARTED
commit

external call

TX2
persist SUCCEEDED/FAILED/UNKNOWN
commit
```

---

# 69. Crash between TX1 and external call

Recovery analyse :

```text
STARTED
```

selon proof-of-send/reconciliation semantics.

---

# 70. Application UnitOfWork

Use cases nécessitant atomicité locale utilisent :

```text
UnitOfWork
```

---

# 71. UnitOfWork example

```python
async with uow:
    effect = await uow.effects.get(effect_id)
    effect.mark_started(...)
    await uow.effects.save(effect)
    await uow.outbox.append(...)
    await uow.commit()
```

---

# 72. UnitOfWork anti-pattern

Ne pas exposer :

```text
psycopg connection
```

dans Application.

---

# 73. Command idempotency

Certains Commands doivent être idempotents.

Exemples :

```text
CreateRun with IdempotencyKey
Approve same approval with same decision
Append webhook-triggered message with dedup key
```

---

# 74. Command idempotency store

Peut utiliser :

```text
Inbox
unique constraint
domain key
```

selon use case.

---

# 75. Idempotency mismatch

Même clé + payload différent :

```text
Conflict
```

---

# 76. Application retries

Trois catégories :

```text
DB transaction retry
transport retry
business operation retry
```

---

# 77. DB transaction retry

Autorisé si :

```text
no external side effect occurred
```

---

# 78. Transport retry

Autorisé seulement si adapter/provider semantics le permettent.

---

# 79. Business Effect retry

Décidé explicitement par Effects Application Service.

---

# 80. Application error categories

```text
ValidationError
NotFound
Conflict
PolicyDenied
ApprovalRequired
StaleOwnership
RuntimeUnavailable
ConnectorUnavailable
AmbiguousOutcome
ManualInterventionRequired
```

---

# 81. Domain error translation

Exemple :

```text
InvalidRunTransition
→ Application Conflict
```

---

# 82. Adapter error translation

Exemple :

```text
ConnectorAmbiguousWrite
→ Effect UNKNOWN
→ Application result
```

---

# 83. Application results vs exceptions

Pour états métier attendus :

```text
WAITING
APPROVAL_REQUIRED
RECONCILIATION_REQUIRED
```

préférer résultat explicite.

---

# 84. WAITING is not exception

Principe :

```text
WAITING
= valid durable state
```

---

# 85. Manual intervention is not necessarily failure

`MANUAL_INTERVENTION` peut être une NextAction valide.

---

# 86. SecurityContext propagation

Chaque command sensible reçoit :

```text
SecurityContext
```

ou contexte équivalent injecté.

---

# 87. SecurityContext includes

Candidats :

```text
PrincipalReference
TenantId
authn method
scopes/claims summary
correlation
request origin
```

---

# 88. Authorization location

L’Application appelle :

```text
AuthorizationPort
```

aux frontières sensibles.

---

# 89. Policy evaluation location

Application orchestre :

```text
PolicyEvaluator
```

mais le modèle de PolicyDecision appartient Governance.

---

# 90. Approval applicability

La règle métier appartient au Governance Domain.

Application orchestre l’appel.

---

# 91. Ownership validation

Application Effects/Execution appelle Coordination.

Ne jamais supposer que :

```text
worker local memory
```

est suffisante.

---

# 92. Fencing propagation

Application transmet :

```text
OwnershipContext / FencingToken
```

aux ports protégés.

---

# 93. Runtime invocation lifecycle

Application crée :

```text
RuntimeInvocation
```

avant/au moment de démarrer un runtime selon transaction model.

---

# 94. Runtime start ambiguity

Si runtime start lui-même a un effet durable/remote ambigu :

```text
RuntimeInvocation status UNKNOWN
```

ou modèle équivalent à définir.

---

# 95. Runtime inspection

Application Recovery appelle :

```text
AgentRuntimeAdapter.inspect()
```

et ne fait pas confiance aux derniers events uniquement.

---

# 96. Runtime events

Les RuntimeEvents sont :

```text
input signals
```

pas automatiquement des DomainEvents.

---

# 97. Runtime event handling

```text
receive
↓
map
↓
application handler
↓
load authoritative state
↓
decide
```

---

# 98. Runtime completion

Un runtime qui dit :

```text
completed
```

ne signifie pas automatiquement :

```text
Run SUCCEEDED
```

si unresolved Effect/Approval existe.

---

# 99. Tool interception

Si adapter supporte :

```text
TOOL_INTERCEPTION
```

alors tool requests protégées passent par :

```text
EffectGateway
```

---

# 100. No interception capability

Si runtime ne permet pas interception :

```text
control level
```

doit être explicite.

Certaines garanties peuvent devenir impossibles.

---

# 101. Runtime capability negotiation

Avant use case :

```text
required capability
∈
runtime capabilities?
```

sinon :

```text
UnsupportedCapability
```

---

# 102. Connector capability negotiation

Même logique.

---

# 103. Application registry use

Application reçoit :

```text
RuntimeRegistry
ConnectorRegistry
```

via ports/services.

---

# 104. No global registry

Pas de singleton global caché.

---

# 105. Application event publishing

Après transaction locale :

```text
DomainEvents
→ Outbox
```

---

# 106. Domain Event handling

Handlers applicatifs peuvent :

```text
create read model
wake Run
send notification
schedule reconciliation
```

---

# 107. Event handler idempotency

Obligatoire sous at-least-once.

---

# 108. Event as hint

Handler recharge la vérité durable avant décision critique.

---

# 109. Outbox transactional boundary

```text
aggregate save
+
outbox append
```

dans même transaction DB quand possible.

---

# 110. Inbox boundary

Inbound event :

```text
dedup
before
application handling
```

---

# 111. Cross-context orchestration

Use case example :

```text
ExecuteEffect
```

peut orchestrer :

```text
Governance
Coordination
Effects
Connector
Audit
```

---

# 112. No distributed aggregate transaction

Ne pas traiter :

```text
Run + Effect + Approval + Lease
```

comme un seul aggregate.

---

# 113. Saga-like orchestration

Certaines opérations ressemblent à des sagas.

Mais PyAgentsKit ne doit pas nécessairement introduire un moteur Saga générique.

---

# 114. Explicit workflow over generic workflow engine

Préférer :

```text
specific use-case orchestration
```

si cela rend les invariants lisibles.

---

# 115. Application service granularity

Éviter :

```text
class PyAgentsKitService
```

de 5 000 lignes.

Préférer :

```text
CreateRun
ResumeRun
ExecuteEffect
Approve
AcquireLease
```

---

# 116. Function vs class

Un use case peut être :

```text
class
function
callable object
```

selon besoin.

La priorité est :

```text
explicit dependencies
testability
cohesion
```

---

# 117. Constructor injection

Préféré.

Exemple :

```python
class ResumeRun:
    def __init__(
        self,
        runs: RunRepository,
        effects: EffectRepository,
        approvals: ApprovalRepository,
        runtime_registry: RuntimeRegistry,
        lease_service: LeaseApplicationService,
        recovery_planner: RecoveryPlanner,
    ):
        ...
```

---

# 118. Dependency count smell

Si un use case nécessite 15 dépendances :

```text
re-evaluate boundaries
extract orchestrator/facade
```

---

# 119. Application facade

Une façade peut regrouper les use cases pour l’API.

Exemple :

```text
RunApplication
EffectApplication
ApprovalApplication
```

mais sans re-centraliser toute la logique.

---

# 120. RunApplication

Candidate surface :

```text
create
start
resume
pause
cancel
get
list
timeline
```

---

# 121. EffectApplication

```text
plan
execute
reconcile
resolve
get
list
```

---

# 122. ApprovalApplication

```text
request
approve
reject
cancel
get
list_pending
```

---

# 123. ConversationApplication

```text
create_session
create_conversation
append_message
list_messages
```

---

# 124. WorkerApplication

```text
drain
status
takeover
```

---

# 125. Application API stability

Use case internals peuvent évoluer.

Les ports/public commands doivent être versionnés selon stabilité.

---

# 126. DTO ownership

Application Commands/Queries vivent dans Application.

Public API DTOs peuvent mapper vers eux.

---

# 127. No direct public DTO as aggregate

`RunView` ne doit pas être `Run`.

---

# 128. Input validation

Trois niveaux :

```text
transport validation
application validation
domain validation
```

---

# 129. Transport validation

Exemple :

```text
JSON parse
required field syntax
```

---

# 130. Application validation

Exemple :

```text
requested runtime exists
session accessible
```

---

# 131. Domain validation

Exemple :

```text
Run transition valid
Approval terminal immutability
```

---

# 132. Query model architecture

Read models peuvent être optimisés pour :

```text
operations
UI
timeline
search
```

---

# 133. Query model sources

Peuvent utiliser :

```text
PostgreSQL views
read tables
materialized projections
```

mais restent non-authoritative.

---

# 134. Query performance

Éviter de reconstruire un timeline complet en chargeant tous les aggregates si besoin élevé.

---

# 135. Query consistency

Peut être :

```text
eventually consistent
```

si documenté.

---

# 136. Command consistency

Safety-critical command lit source autoritative.

---

# 137. Application timeouts

Les use cases peuvent avoir :

```text
overall timeout
```

mais :

```text
client timeout != Effect failure
```

---

# 138. Application cancellation

Cancellation du caller :

```text
does not automatically cancel Run
```

---

# 139. Explicit cancel command

Pour annuler le Run :

```text
CancelRunCommand
```

---

# 140. Application background work

Long-running processing :

```text
worker
```

ré-invoque les mêmes use cases.

---

# 141. Worker is adapter

Le Worker Loop n’est pas un Application Service.

---

# 142. Worker admission

```text
queue/work scanner
↓
Start/ResumeRun use case
```

---

# 143. Recovery scanner

Peut détecter :

```text
recoverable Runs
expired leases
stale STARTED Effects
```

puis appeler Application.

---

# 144. Scanner is not source of truth

Il ne fait que découvrir.

---

# 145. Scheduling

La planification de scanners/retries reste externe/ops.

---

# 146. Use case correlation

Chaque invocation reçoit :

```text
CorrelationContext
```

---

# 147. Correlation propagation

Transmise à :

```text
runtime
connector
audit
telemetry
outbox
```

sans devenir business identity.

---

# 148. Tenant propagation

Chaque use case multi-tenant doit avoir :

```text
TenantId
```

explicite ou SecurityContext fiable.

---

# 149. Tenant mismatch

Résultat :

```text
NotFound or Denied
```

selon anti-enumeration policy.

---

# 150. Audit integration

Application déclenche ou projette AuditEvents pour actions sensibles.

---

# 151. Audit use-case examples

```text
Approval decided
Effect manually resolved
Force takeover
Kill switch
Migration cutover
```

---

# 152. Telemetry integration

Application peut émettre :

```text
use case latency
outcome
blocker
recovery decision
```

sans payload sensible.

---

# 153. Application health

Pas un use case métier.

Mais HealthQueryPort peut agréger adapter readiness.

---

# 154. Readiness

Application/Bootstrap décide quelles dépendances sont requises par profil.

---

# 155. Application configuration

Configuration policy injectable.

Exemples :

```text
max recovery attempts
effect freeze
approval timeout defaults
```

à condition de ne pas devenir infrastructure-specific.

---

# 156. Feature policy vs config

Une règle métier structurante doit vivre Domain/Policy, pas être un simple booléen config.

---

# 157. Application anti-pattern — anemic pass-through

Un Application Service qui fait uniquement :

```text
repo.get
repo.save
```

sans use case réel peut être inutile.

---

# 158. Application anti-pattern — giant transaction script

Éviter 500 lignes avec tous les invariants inline.

---

# 159. Application anti-pattern — provider conditionals

Interdit :

```python
if runtime == "langgraph":
```

---

# 160. Application anti-pattern — repository-specific SQL knowledge

Interdit.

---

# 161. Application anti-pattern — catch Exception retry

Particulièrement dangereux autour des Effects.

---

# 162. Application anti-pattern — mutate foreign aggregate

Interdit.

---

# 163. Application anti-pattern — infer Approval from Message

Interdit.

---

# 164. Application anti-pattern — queue message = ownership

Interdit.

---

# 165. Application anti-pattern — runtime completed = run success

Interdit sans autres checks.

---

# 166. Application anti-pattern — hidden fallback

Runtime/connector fallback doit être explicite.

---

# 167. Use Case Contract Testing

Chaque use case critique doit avoir tests avec fake ports.

---

# 168. CreateRun tests

```text
happy path
session missing
tenant mismatch
duplicate idempotency
runtime unavailable
```

---

# 169. ResumeRun tests

```text
terminal
waiting approval
unknown effect
expired lease
stale worker
runtime missing
runtime resumable
manual intervention
```

---

# 170. ExecuteEffect tests

```text
approval required
unauthorized
stale fencing
idempotent duplicate
provider success
provider failure
provider ambiguous
```

---

# 171. Approve tests

```text
approve
duplicate same decision
conflicting decision
expired
SoD violation
scope drift
```

---

# 172. Takeover tests

```text
not expired
expired
force authorized
force unauthorized
monotonic token
```

---

# 173. AppendMessage tests

```text
duplicate transport delivery
closed conversation
invalid participant
```

---

# 174. Integration tests

Utiliser vrais adapters pour :

```text
PostgreSQL
NativeRuntime
one external runtime
one connector
```

---

# 175. Failure tests

Use cases doivent être testés avec fault injection.

---

# 176. Fault — DB commit uncertain

Application relit état.

---

# 177. Fault — external timeout after send

Effect devient `UNKNOWN`.

---

# 178. Fault — lease lost before Effect

Effect non exécuté.

---

# 179. Fault — approval store unavailable

Protected action bloquée.

---

# 180. Fault — runtime session lost

RecoveryPlanner décide restart/manual.

---

# 181. Contract invariants

```text
APP-INV-01
Application never bypasses domain invariants.

APP-INV-02
Application never imports concrete adapters.

APP-INV-03
WAITING is a valid result.

APP-INV-04
External Effect execution is not wrapped in blind retry.

APP-INV-05
Client cancellation does not imply Run cancellation.

APP-INV-06
Runtime completion does not alone imply Run success.

APP-INV-07
Application reloads authoritative state after ambiguous events.

APP-INV-08
Cross-context mutation occurs through owning use cases/ports.

APP-INV-09
SecurityContext is revalidated when required.

APP-INV-10
Manual intervention is an explicit supported outcome.
```

---

# 182. Use Case naming conventions

Verbes impératifs :

```text
CreateRun
ResumeRun
ExecuteEffect
ApproveRequest
AcquireLease
AppendMessage
```

Éviter :

```text
RunManager
EffectManager
GenericService
```

---

# 183. Application package example

```text
application/
├── execution/
│   ├── create_run.py
│   ├── start_run.py
│   ├── resume_run.py
│   ├── pause_run.py
│   └── cancel_run.py
│
├── recovery/
│   ├── recover_run.py
│   ├── recovery_planner.py
│   └── next_action_executor.py
│
├── effects/
│   ├── plan_effect.py
│   ├── execute_effect.py
│   ├── reconcile_effect.py
│   └── resolve_effect.py
│
├── governance/
│   ├── request_approval.py
│   ├── decide_approval.py
│   └── revalidate_approval.py
│
├── coordination/
│   ├── acquire_lease.py
│   ├── renew_lease.py
│   ├── takeover.py
│   └── drain_worker.py
│
├── conversations/
│   ├── create_session.py
│   ├── create_conversation.py
│   ├── append_message.py
│   └── write_memory.py
│
├── artifacts/
│   ├── register_artifact.py
│   └── verify_artifact.py
│
└── queries/
    ├── run_queries.py
    ├── effect_queries.py
    ├── approval_queries.py
    └── timeline_queries.py
```

---

# 184. Application shared package

Doit rester petit.

Candidats :

```text
CommandContext
QueryContext
UseCaseResult
ApplicationError
```

---

# 185. No shared god module

Éviter :

```text
application/shared/services.py
```

avec toutes les abstractions.

---

# 186. CommandContext

Peut contenir :

```text
tenant
principal
correlation
request id
idempotency key
```

---

# 187. QueryContext

Peut contenir :

```text
tenant
principal
correlation
pagination
```

---

# 188. Idempotency context

Pour commands publics :

```text
IdempotencyKey
```

peut être porté par CommandContext.

---

# 189. Application execution boundary

Chaque invocation use case doit être observable comme unité logique.

---

# 190. Middleware applicatif

Possible pour concerns transverses :

```text
correlation
telemetry
authorization precheck
idempotency envelope
```

mais sans cacher les règles safety.

---

# 191. Middleware anti-pattern

Un middleware générique ne doit pas :

```text
retry Effect
approve request
acquire lease
```

implicitement.

---

# 192. Decorator use

Des decorators peuvent être employés pour :

```text
metrics
tracing
logging
```

---

# 193. Transaction decorator

À utiliser avec prudence.

Les limites de transaction doivent rester visibles pour les Effects.

---

# 194. Application command bus

Optionnel.

Un generic command bus n’est pas requis au départ.

---

# 195. Why no command bus initially

PyAgentsKit privilégie :

```text
explicit Python calls
clarity
traceability
```

sur une abstraction supplémentaire sans besoin.

---

# 196. Query bus

Même conclusion.

---

# 197. Future extensibility

Un bus peut être ajouté derrière les Inbound Ports si besoin.

---

# 198. Application service lifecycle

Services idéalement :

```text
stateless
```

hors références aux ports/config.

---

# 199. No in-memory authority

Application service ne conserve pas un Run authoritative en cache entre invocations.

---

# 200. Concurrency

Chaque command mutationnel doit considérer :

```text
expected_version
CAS
lease
idempotency
```

selon aggregate.

---

# 201. Optimistic concurrency

Conflit :

```text
reload
re-evaluate
```

pas overwrite silencieux.

---

# 202. Pessimistic locking

Utilisé localement lorsqu’il protège un invariant précis.

---

# 203. No lock around remote LLM/API call

Éviter lock DB long.

---

# 204. Recovery concurrency

Deux workers peuvent tenter recovery.

Lease/Fencing doit rendre un seul autoritatif.

---

# 205. Approval concurrency

Deux décisions simultanées :

```text
one terminal transition
```

---

# 206. Effect concurrency

Même idempotency key :

```text
one logical Effect
```

---

# 207. Message concurrency

Ordre explicite si requis.

---

# 208. Application performance

Ne doit pas sacrifier safety pour micro-optimisation.

---

# 209. Batch queries

Read side peut optimiser.

---

# 210. Batch commands

Doivent définir précisément :

```text
atomicity
partial success
ordering
```

---

# 211. Bulk effect execution

Très sensible.

Ne pas introduire avant modèle clair.

---

# 212. Pagination

Queries publiques utilisent :

```text
cursor-based pagination
```

si volume élevé.

---

# 213. Streaming query

Timeline/events peuvent utiliser async streaming.

---

# 214. Event cursor

Doit être opaque/stable.

---

# 215. Application versioning

Commands publics stables peuvent porter :

```text
schema_version
```

si nécessaire pour HTTP/events.

---

# 216. Backward compatibility

Internal use-case classes peuvent évoluer plus librement que public API.

---

# 217. Application documentation template

Pour chaque use case :

```text
ID
Intent
Inputs
Preconditions
Domain objects
Ports used
Transaction boundary
External Effects
Outputs
Errors
Idempotency
Security
Observability
Failure semantics
Tests
```

---

# 218. Use Case catalog P0

Priorité V2 alpha :

```text
CreateRun
StartRun
ResumeRun
CancelRun
RecoverRun
PlanEffect
ExecuteEffect
ReconcileEffect
RequestApproval
Approve
Reject
AcquireLease
RenewLease
TakeoverLease
```

---

# 219. Use Case catalog P1

```text
CreateSession
CreateConversation
AppendMessage
RegisterArtifact
GetRunTimeline
DrainWorker
ManualEffectResolution
```

---

# 220. Use Case catalog P2

```text
advanced admin repair
multi-approval orchestration
delegation
bulk operations
```

---

# 221. First vertical slice

```text
CreateRun
↓
StartRun
↓
NativeRuntimeAdapter
↓
RuntimeInvocation
↓
Run SUCCEEDED
```

---

# 222. Second vertical slice

```text
PlanEffect
↓
ExecuteEffect
↓
ambiguous connector
↓
UNKNOWN
↓
ReconcileEffect
```

---

# 223. Third vertical slice

```text
RequestApproval
↓
WAITING
↓
Approve
↓
ResumeRun
```

---

# 224. Fourth vertical slice

```text
Worker A
↓
Run
↓
crash
↓
Takeover
↓
Worker B
↓
RecoverRun
```

---

# 225. Fifth vertical slice

```text
External Runtime
↓
same Application use cases
↓
same Effect/Governance/Recovery semantics
```

---

# 226. Application Architecture Acceptance Criteria

Le modèle est conforme si :

1. chaque mutation utilisateur correspond à un use case explicite ;
2. les use cases n’importent aucun adapter concret ;
3. les business invariants restent dans Domain ;
4. les cross-context flows sont orchestrés par Application ;
5. `ResumeRun` passe par RecoveryPlanner ;
6. `ExecuteEffect` valide Governance + Coordination ;
7. aucun generic retry ne rejoue un Effect ambigu ;
8. les Commands et Queries sont séparés ;
9. les Views ne sont pas des aggregates ;
10. les events ne sont pas traités comme source de vérité ;
11. les transactions sont explicites ;
12. les remote calls ne vivent pas dans une longue transaction DB ;
13. WAITING et MANUAL_INTERVENTION sont des résultats valides ;
14. SecurityContext et Tenant sont propagés ;
15. les use cases P0 ont des tests unitaires avec fake ports.

---

# 227. Definition of Done

La couche Application est mature lorsque :

1. le catalogue P0 est implémenté ;
2. les Commands/Queries sont typés ;
3. les use cases sont petits et cohésifs ;
4. RecoveryPlanner orchestre les reprises ;
5. EffectGateway gouverne les effets protégés ;
6. Governance est invoquée explicitement ;
7. Coordination est revalidée avant Protected Effect ;
8. RuntimeAdapter est toujours invoqué via port ;
9. Outbox/Inbox sont intégrés aux flows concernés ;
10. les erreurs sont normalisées ;
11. les use cases critiques sont failure-tested ;
12. aucune route/CLI/worker ne contient de business logic ;
13. les Read Models sont non-authoritative ;
14. la CI vérifie les dépendances ;
15. les vertical slices V2 fonctionnent avec Native Runtime puis un runtime externe.

---

# 228. Résumé

La couche Application V2 devient le lieu de l’orchestration explicite :

```text
INBOUND COMMAND
       │
       ▼
APPLICATION USE CASE
       │
       ├── load aggregates
       ├── invoke domain decisions
       ├── call ports
       ├── manage local transaction
       ├── persist
       └── publish/audit
```

Elle ne doit ni devenir un second Domain, ni un framework de workflow générique.

Les distinctions essentielles sont :

```text
Application Service != Domain Service
Command != Query
Run != RuntimeInvocation
Resume != Runtime.resume blindly
Retry != Recovery
Runtime completion != Run success
Client cancellation != Run cancellation
```

Le principe fondamental est :

> **L’Application Layer doit rendre les workflows de sûreté lisibles dans le code : lorsqu’un Run reprend, lorsqu’un Effect part, lorsqu’une Approval est requise ou lorsqu’un worker prend le contrôle, l’orchestration doit être visible, testable et impossible à contourner accidentellement.**

Le document suivant naturel est :

```text
../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md
```
