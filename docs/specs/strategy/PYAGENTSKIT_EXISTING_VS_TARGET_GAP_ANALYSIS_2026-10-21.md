# PyAgentsKit — Analyse approfondie de l’existant vs architecture cible

**Date d’analyse :** 21 octobre 2026  
**Dépôt analysé :** `tawounfouet/pyagentskit` — branche `main`  
**Version déclarée :** `1.6.0`  
**Dernier jalon substantiel observé :** commit `674538e` — *PyAgentsKit 1.6.0 — Distributed Operations & Production Qualification est terminé*  
**Commit le plus récent observé :** `90bd8e7` — *remove workflow*  

## 1. Conclusion exécutive

L’existant n’est pas un prototype faible qu’il faudrait remplacer.

Au contraire, PyAgentsKit 1.6.0 possède déjà un **socle de fiabilité très sérieux** :

- exécution bornée et typée ;
- tools gouvernés ;
- sessions/mémoire ;
- approvals persistantes ;
- checkpoints ;
- journal d’Effects ;
- état `UNKNOWN` ;
- reprise durable ;
- leases ;
- fencing tokens ;
- takeover ;
- PostgreSQL ;
- S3/Azure Blob ;
- métriques ;
- OpenTelemetry ;
- tests SIGTERM/SIGKILL/SIGSTOP ;
- qualification multi-processus et PostgreSQL.

Le problème est ailleurs :

> **la cible documentaire 11→25 a déplacé le centre de gravité du produit.**

Le code actuel est encore principalement :

> **un runtime d’agent mono-agent, provider-neutral, qui possède lui-même la boucle Model → Tool → Model.**

La cible devient :

> **une Agent Reliability Layer framework-neutral qui doit pouvoir sécuriser et rendre durable un runtime externe qu’elle ne contrôle pas nécessairement.**

C’est un changement architectural majeur.

### Verdict synthétique

- **Maturité de l’existant dans son périmètre V1.6 : élevée.**
- **Couverture fonctionnelle/architecturale de la nouvelle cible : ~55 %.**
- **Les briques les plus difficiles de coordination distribuée existent déjà.**
- **Les écarts les plus importants concernent l’abstraction runtime, le modèle de domaine, les connectors, les coding agents, le modèle PostgreSQL normalisé et les contrats publics de la future Reliability Layer.**
- **La cible correspond beaucoup plus naturellement à PyAgentsKit 2.0 qu’à un simple 1.7.0.**

Le point le plus important est donc :

> **Il ne faut pas réécrire PyAgentsKit ; il faut reclasser le runtime V1 comme une implémentation native parmi plusieurs runtimes, puis construire autour de lui la couche de fiabilité cible.**

---

# 2. État réel du dépôt

Le dépôt annonce dans son README :

```text
PyAgentsKit is a typed, observable and provider-neutral Python runtime
for bounded mono-agent execution.
```

Le README précise également parmi ses contraintes stables :

```text
Mono-agent execution only.
```

Le contrat V1 gèle :

```text
155 symboles publics dans pyagentskit.__all__
28 EventType
signatures centrales
schémas sérialisés
constructeurs providers
```

La version actuelle dans `pyproject.toml` est :

```text
1.6.0
```

La qualification 1.6.0 rapporte notamment :

```text
276 tests passés
12 tests live skippés
90.15 % branch coverage
mypy strict
Ruff
Python 3.11 / 3.12 / 3.13 en CI
SIGTERM
SIGKILL
SIGSTOP
PostgreSQL 16
two-worker takeover
reproducible builds
```

Cela signifie qu’il faut distinguer deux questions :

1. **Le code actuel est-il mature ?** → oui, dans son scope.
2. **Le code actuel implémente-t-il la nouvelle cible documentaire ?** → seulement partiellement.

---

# 3. Méthode d’évaluation

Échelle utilisée :

| Score | Signification |
|---:|---|
| 0/5 | absent |
| 1/5 | traces ou primitive très limitée |
| 2/5 | partiellement présent mais modèle différent |
| 3/5 | substantiel, refactor important nécessaire |
| 4/5 | très proche de la cible |
| 5/5 | aligné avec la cible |

Le score global de **55,3 %** mesure la **couverture de la nouvelle cible**, pas la qualité intrinsèque de V1.6.

---

# 4. Matrice globale d’écart

| Domaine cible | Poids | Existant | Score | Écart |
|---|---:|---|---:|---|
| Framework-neutral Runtime Adapter | 12 % | `Model`, `Runner`, provider adapters | 1.5/5 | **Critique** |
| Modèle de domaine | 8 % | Run, Session, Message, Effect partiels | 2/5 | **Fort** |
| Durable Execution | 10 % | `DurableRunner`, checkpoints, resume | 4/5 | Faible/modéré |
| Effect Safety & Reconciliation | 10 % | Effect journal, UNKNOWN, manual resolution | 3.5/5 | Modéré |
| Distributed Coordination | 10 % | Lease, fencing, takeover, workers | 4.5/5 | Faible |
| Persistence & State Stores | 8 % | Memory/SQLite/PostgreSQL/S3/Azure | 3.5/5 | Modéré |
| Human Governance | 7 % | durable approvals | 3/5 | Modéré |
| Security & Trust | 7 % | guardrails, secrets, privacy, tenant scope | 2.5/5 | Fort |
| Observability & Audit | 7 % | events, metrics, OTel, JSONL | 3.5/5 | Modéré |
| Coding Agent Integration | 7 % | seulement `CODE_EXECUTION` risk | 0.5/5 | **Critique** |
| External Systems & Connectors | 5 % | LLM providers, pas de connector model | 1/5 | **Critique** |
| API & Public Contracts | 4 % | Python API très stable | 2.5/5 | Fort |
| PostgreSQL Data Model | 3 % | PostgreSQL présent, JSONB agrégé | 2/5 | Fort |
| Failure & Recovery | 2 % | bons tests distributed, plan minimal | 3.5/5 | Modéré |

**Couverture pondérée estimée : 55,3 %.**

---

# 5. Écart architectural principal : Runtime ≠ Runtime Adapter

## 5.1 Ce que fait l’existant

`src/pyagentskit/runtime.py` contient un `Runner` d’environ 1 000 lignes.

Il possède directement :

```text
Model
ToolRegistry
EventBus
SessionStore
ContextPolicy
ArtifactStore
Guardrails
DataPolicy
ApprovalStore
RetryPolicy
```

Le `Runner` :

```text
construit les messages
→ appelle le Model
→ interprète les ToolCalls
→ exécute les Tools
→ réinjecte les résultats
→ continue la boucle
```

Le port principal externe est :

```python
class Model(Protocol):
    async def generate(...)
    def stream(...)
```

Les implémentations actuelles sont notamment :

```text
OpenAI
Anthropic
Google Gemini
xAI
Ollama
OpenRouter
```

C’est un bon **LLM runtime abstraction layer**.

Ce n’est pas encore la cible :

```text
AgentRuntimeAdapter
```

qui doit piloter :

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
custom runtime
```

## 5.2 Pourquoi l’écart est structurel

La cible affirme :

```text
Build/use agents with any runtime.
Execute them with PyAgentsKit reliability guarantees.
```

Or l’existant dit encore implicitement :

```text
Build the agent loop inside PyAgentsKit Runner.
```

Cela change la relation de dépendance.

### Actuel

```text
PyAgentsKit
 ├─ owns agent loop
 ├─ owns model calls
 ├─ owns tool execution
 └─ integrates LLM providers
```

### Cible

```text
PyAgentsKit Reliability Layer
       │
       ├─ LangGraph
       ├─ PydanticAI
       ├─ OpenAI Agents SDK
       ├─ Claude Agent SDK
       ├─ Codex / Claude Code / OpenCode
       └─ Native PyAgentsKit Runner
```

La V1 doit donc devenir :

```text
NativePyAgentsRuntimeAdapter
```

ou équivalent.

### Recommandation

Ne pas supprimer `Runner`.

Le repositionner comme :

```text
PyAgentsKit Native Runtime
```

et construire devant lui :

```python
class AgentRuntimeAdapter(Protocol):
    async def start(...): ...
    async def resume(...): ...
    async def cancel(...): ...
    async def inspect(...): ...
    async def events(...): ...
    async def checkpoint(...): ...
    async def close(...): ...
```

**Écart : critique.**

---

# 6. Modèle de domaine : plusieurs concepts sont encore fusionnés

## 6.1 Session et Conversation

Dans `sessions.py` :

```python
class Session(ContractModel):
    """Conversation identity and optimistic revision metadata."""
```

Autrement dit, la V1 assimile encore largement :

```text
Session ≈ Conversation
```

La cible impose explicitement :

```text
Session != Conversation
```

avec :

```text
Session
 ├─ Runs
 ├─ Conversations
 └─ MemoryEntries

Conversation
 ├─ Participants
 └─ Messages
```

### Conséquence

Il manque :

```text
Conversation
Participant
Actor
MessageRecipient
ConversationStatus
ConversationContext
```

---

# 7. Message actuel ≠ Message métier cible

Le `Message` actuel est un excellent contrat de transport LLM :

```text
role
content
tool_calls
name
tool_call_id
metadata
```

Rôles :

```text
SYSTEM
USER
ASSISTANT
TOOL
```

Mais la cible attend un Message durable de domaine :

```text
message_id
conversation_id
sender Actor
recipients
direction
status
deduplication key
created_at
references
```

Le modèle actuel répond à :

> « comment normaliser un message pour le Model ? »

La cible répond à :

> « comment représenter durablement un échange entre humains, agents et systèmes ? »

Ce sont deux abstractions différentes.

### Recommandation

Conserver l’actuel sous une abstraction du type :

```text
RuntimeMessage / ModelMessage
```

et introduire séparément :

```text
ConversationMessage
```

---

# 8. Run lifecycle : incompatibilité sémantique importante

Le `RunStatus` actuel :

```text
CREATED
RUNNING
WAITING_APPROVAL
COMPLETED
FAILED
CANCELLED
LIMIT_EXCEEDED
UNKNOWN_EFFECT
```

La cible :

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

L’écart le plus important n’est pas le vocabulaire.

Dans la V1 :

```python
WAITING_APPROVAL
UNKNOWN_EFFECT
```

sont considérés par `RunStatus.is_terminal` comme des états pouvant produire un `RunResult` final.

C’est logique pour une invocation de fonction Python qui doit rendre la main.

Mais la cible dit :

```text
WAITING != terminal
UNKNOWN Effect != terminal Run state
```

Un Run durable peut n’avoir aucun process actif tout en restant non terminal.

### Problème conceptuel

La V1 fusionne partiellement :

```text
"cette invocation du Runner est terminée"
```

et :

```text
"le Run métier est terminé"
```

### Cible recommandée

Séparer :

```text
RunState
```

de :

```text
RuntimeInvocationStatus
```

C’est précisément l’un des changements structurants nécessaires en V2.

---

# 9. Durable Execution : une base déjà très avancée

C’est l’une des zones les plus proches de la cible.

`durability.py` fournit :

```text
RunCheckpoint
EffectRecord
JournalEntry
RunStore
MemoryRunStore
SQLiteRunStore
DurableRunner
RecoveryPlan
```

`DurableRunner` :

- exige une Session persistante ;
- écrit des checkpoints ;
- journalise les Effects ;
- reprend un Run ;
- vérifie l’identité/version de l’Agent ;
- refuse de reprendre un Run avec Effect `UNKNOWN` non résolu ;
- restaure les Tool messages à partir des Effects persistés.

Cela correspond fortement au principe cible :

> le process n’est pas la source de vérité.

## Limite

Le `RecoveryPlan` actuel reste très minimal :

```text
run_id
resumable: bool
unknown_effect_ids
recovered_effect_ids
reason
```

La cible attend plutôt :

```text
NextAction[]
RecoveryBlocker[]
RecoveryPlan
```

avec des décisions telles que :

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

### Verdict

Le moteur existe.

Le **RecoveryPlanner généraliste** n’existe pas encore.

**Écart : faible à modéré.**

---

# 10. Effect Safety : fondations excellentes, domaine encore trop lié au ToolCall

Le modèle actuel :

```text
PLANNED
STARTED
COMPLETED
FAILED
UNKNOWN
```

et :

```text
EffectResolution.NOT_APPLIED
EffectResolution.COMMITTED
```

sont de très bonnes fondations.

L’Effect actuel possède :

```text
effect_id
run_id
trace_id
agent_id
session_id
tenant_id
idempotency_key
fingerprint
ToolCall
tool_version
idempotent
status
revision
timestamps
ToolResult
```

Le système possède déjà :

```text
durable intent
idempotency fingerprint
optimistic revision
UNKNOWN
manual reconciliation conclusion
no implicit replay
```

C’est très proche de la philosophie cible.

## Écarts

### A. `COMPLETED` vs `SUCCEEDED`

La cible distingue explicitement :

```text
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

### B. `RECONCILIATION_REQUIRED` absent comme état propre

L’existant bloque sur `UNKNOWN` mais ne modélise pas encore un sous-domaine complet :

```text
ReconciliationCase
ReconciliationStrategy
ReconciliationResult
ReconciliationPort
evidence
external observations
manual review lifecycle
```

### C. Effect encore lié à ToolCall

La cible veut que :

```text
Effect > ToolCall
```

Un Effect peut provenir de :

```text
tool
connector
runtime
coding agent
deployment operation
human-mediated operation
```

### D. ExternalReference insuffisamment explicite

La cible prévoit un `ExternalReference` durable et générique.

### Verdict

**Très bonne base technique, mais le modèle doit être généralisé.**

---

# 11. Distributed Coordination : zone la plus proche de la cible

Cette partie est déjà remarquablement alignée.

L’existant fournit :

```text
Lease
LeaseStore
MemoryLeaseStore
SQLiteLeaseStore
PostgresLeaseStore
FencingToken
FencedOperationStore
DistributedExecutionPolicy
DistributedDurableRunner
DistributedWorkerController
```

Le `Lease` contient :

```text
lease_id
resource_id
owner_id
tenant_id
fencing_token
acquired_at
expires_at
revision
```

Le `FencingToken` contient :

```text
resource_id
owner_id
tenant_id
value
lease_id
```

Le code impose :

```text
renewal_interval < TTL
finite max renewals
current ownership validation
monotonic fencing
atomic protected-store fencing contract
```

Les tests couvrent explicitement :

```text
SIGTERM
SIGKILL
SIGSTOP
expiry
takeover
split-brain stale token
database outage
drain timeout
readiness
```

Exemples de tests présents :

```text
test_sigkill_crash_allows_takeover_only_after_expiry
test_suspended_worker_becomes_fenced_after_expiry
test_expired_worker_stops_before_planning_a_new_effect
test_crash_expiry_takeover_never_replays_ambiguous_effect
test_protected_store_rejects_split_brain_stale_token
test_heartbeat_emits_renewal_and_database_outage_fails_closed
```

### Écarts restants

La cible enrichit encore :

```text
WorkerRegistry
OwnershipContext.expires_at
Lease audit history
ResourceIdentity VO
richer worker lifecycle
```

Le Worker actuel possède surtout :

```text
ACCEPTING
DRAINING
STOPPED
```

La cible prévoit :

```text
STARTING
READY
BUSY
DRAINING
UNHEALTHY
STOPPED
```

Mais c’est un écart de raffinement, pas de fondation.

**Écart : faible.**

---

# 12. Persistence : les bons ports existent, mais le schéma cible est différent

## Existant

Ports et stores :

```text
SessionStore
MemoryStore
ApprovalStore
ArtifactStore
BlobStore
RunStore
LeaseStore
```

Implémentations :

```text
Memory
SQLite
PostgreSQL
Filesystem
S3
Azure Blob
```

C’est une excellente base Ports & Adapters.

## Écart majeur : PostgreSQL physique

### `PostgresRunStore`

L’actuel stocke essentiellement un agrégat complet :

```sql
tenant_scope
run_id
payload_json JSONB
updated_at
```

Le `payload_json` contient :

```text
checkpoints
effects
journal
```

### `postgres_state.py`

Sessions, memories et approvals partagent un modèle générique :

```sql
tenant_scope
collection
owner_id
record_id
payload_json
search_text
session_id
tags
status
...
```

### Cible 24

Le document cible attend une modélisation beaucoup plus explicite :

```text
runs
sessions
conversations
messages
participants
memory_entries
checkpoints
effects
reconciliation_cases
approvals
artifacts
workers
leases
runtime_bindings
runtime_invocations
audit_events
outbox
inbox
```

avec :

```text
FK
UNIQUE
partial unique indexes
typed columns
optimistic versions
append-oriented audit
```

## Conséquence

L’existant est :

> très bon comme backend compatible avec le contrat V1 gelé.

La cible est :

> un véritable modèle de données de plateforme de fiabilité.

Il faudra donc **une nouvelle génération de stores PostgreSQL**, sans casser les anciens.

### Recommandation

Ne pas transformer directement `PostgresRunStore` V1.

Introduire :

```text
PostgresRunRepositoryV2
PostgresEffectStore
PostgresCheckpointStore
PostgresConversationStore
PostgresMessageStore
PostgresReconciliationStore
PostgresAuditStore
PostgresOutboxStore
PostgresInboxStore
```

et fournir une migration V1 → V2.

---

# 13. Approvals : solide, mais encore orienté "gated tool call"

L’existant est déjà conséquent :

```text
ApprovalRequest
ApprovalDecision
ApprovalStatus
ApprovalStore
MemoryApprovalStore
SQLiteApprovalStore
PostgresApprovalStore
```

Statuts actuels :

```text
PENDING
APPROVED
REJECTED
CANCELLED
CLAIMED
EXECUTED
EXPIRED
```

L’approbation est liée cryptographiquement au contenu logique par :

```text
tool_call_fingerprint
```

L’implémentation gère :

```text
expiry
optimistic revision
single claim
resume
actor_id
reason
```

## Écarts avec la cible

La cible veut séparer :

```text
Approval decision lifecycle
```

de :

```text
consumption/execution lifecycle
```

Actuellement :

```text
CLAIMED
EXECUTED
```

sont dans `ApprovalStatus`.

Il serait plus propre dans la cible que l’Approval reste une décision durable :

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

et que :

```text
Effect / ApprovalConsumption / Runtime
```

porte l’utilisation de cette décision.

Il manque également :

```text
PolicyEvaluator
AuthorizationPort
Principal
ApprovalScope générique
ApprovalValidity
SoD
N-of-M
sequential approvals
ApprovalVote
escalation
delegation
```

### Verdict

L’architecture de base est réutilisable.

Le domaine governance doit être élargi.

---

# 14. Security & Trust : de bonnes primitives, pas encore un trust model complet

L’existant possède :

```text
SecretProvider
EnvironmentSecretProvider
DataClassification
DataPolicy
Redactor
GuardrailPipeline
ToolRisk
tenant scoping
```

`ToolRisk` :

```text
PURE
READ
LOCAL_WRITE
EXTERNAL_WRITE
DESTRUCTIVE
CODE_EXECUTION
```

Le code impose par exemple :

```text
DESTRUCTIVE / CODE_EXECUTION → requires_approval
```

C’est une bonne base.

## Concepts cibles absents

Aucune implémentation centrale trouvée pour :

```text
Principal
Actor identity
SecurityContext
AuthorizationPort
Authentication boundary
Policy Decision Point
Policy Enforcement Point
SecretReference
service identity
runtime identity
trust level
sandbox policy
network restriction
filesystem restriction
capability grants
```

La cible 18 va donc au-delà de `guardrails.py`.

### Conclusion

La V1 possède des **security features**.

La cible nécessite un **security model**.

---

# 15. Observability : mature mais Audit ≠ EventSink

L’existant offre :

```text
AgentEvent
EventBus
MemoryEventSink
JsonLinesEventSink
RuntimeMetricsSink
OpenTelemetryEventSink
DistributedOperationEvent
DistributedMetricsSink
JsonLinesDistributedEventSink
OpenTelemetryDistributedEventSink
```

Points positifs :

- événements structurés ;
- redaction ;
- isolation des observers ;
- run_id / trace_id ;
- métriques ;
- distributed lease lifecycle ;
- OTel ;
- payload-free distributed events.

La documentation V1.6 reconnaît elle-même :

```text
JSON Lines is single-process local evidence,
not a centralized compliance journal.
```

C’est précisément l’écart.

## Cible

Il manque un véritable :

```text
AuditEvent domain model
AuditStore
tamper-evident / durable centralized audit
queryable audit trail
actor/action/object/result/evidence
retention rules
correlation across Run/Effect/Approval/Lease/Runtime
```

### Recommandation

Ne pas fusionner :

```text
telemetry
runtime event
audit event
```

La cible a raison de les séparer.

---

# 16. Coding Agents : l’écart le plus visible

Recherche dans `src/pyagentskit` :

```text
Codex             absent
Claude Code       absent
OpenCode          absent
CodingWorkspace   absent
git push          absent
terraform apply   absent
PullRequestRef    absent
workspace model   absent
```

La seule primitive directement utile est :

```text
ToolRisk.CODE_EXECUTION
```

et le système d’Effects/fencing.

La cible 21 nécessite pourtant :

```text
CodingAgentAdapter
Workspace
RepositoryReference
BranchReference
CommitReference
Diff/Patch artifacts
CommandExecution
Git Effects
PR Effects
Package Publish Effects
Deploy Effects
Terraform Effects
runtime session recovery
workspace reconstruction
```

### Conclusion

La **sûreté générique nécessaire** est déjà présente.

L’**intégration coding-agent proprement dite** est quasi absente.

**Écart : critique.**

---

# 17. External Systems & Connectors : attention à ne pas confondre avec providers LLM

Le dépôt possède d’excellents adapters :

```text
OpenAI
Anthropic
Google
xAI
Ollama
OpenRouter
```

Mais ce sont des **Model providers**.

La cible 22 parle de :

```text
business connectors
ERP
GitHub/GitLab
deployment APIs
payment APIs
ticketing
storage
external approval systems
webhooks
provider reconciliation
connector capabilities
```

Recherche des concepts :

```text
ConnectorRegistry       absent
ConnectorDescriptor     absent
ReconciliationPort      absent
ExternalReference       absent
Outbox                  absent
Inbox                   absent
Webhook abstraction     absent
```

### Verdict

Infrastructure HTTP réutilisable.

Domaine Connector à créer.

---

# 18. API & Public Contracts : la V1 est stable, mais ce n’est pas encore l’API cible

L’actuel possède un point très fort :

```text
V1 root API frozen
155 symbols
SHA-256 manifest
API regression tests
```

C’est une excellente discipline de compatibilité.

Mais la cible 23 demande un niveau supplémentaire :

```text
application service API
Run commands/queries
Effect commands/queries
Approval commands/queries
runtime registration
event streaming/cursors
pagination
error taxonomy
idempotency headers
possibly HTTP/OpenAPI facade
```

Aucun modèle du type :

```text
RunView
EffectView
ApprovalView
EventCursor
/v1/runs
OpenAPI
```

n’est actuellement présent.

### Recommandation

Préserver le SDK V1.

Ajouter une couche :

```text
pyagentskit.api
```

au-dessus des Application Services, et non directement au-dessus du `Runner`.

---

# 19. Failure & Recovery : les tests existent avant même le modèle cible complet

L’existant est particulièrement fort sur les pannes distribuées.

Les tests couvrent déjà :

```text
SIGTERM
SIGKILL
SIGSTOP
lease expiry
takeover
stale fencing
database outage
drain timeout
ambiguous effect
approval resume
two-worker PostgreSQL recovery
```

C’est une avance réelle par rapport à beaucoup de frameworks.

## Mais le Recovery model cible est plus général

L’actuel :

```text
RecoveryPlan(resumable, unknown_effect_ids, reason)
```

La cible :

```text
RecoveryPlan
NextAction
RecoveryBlocker
runtime inspection
approval revalidation
effect reconciliation
security revalidation
checkpoint fallback
connector recovery
artifact recovery
post-restore safety gate
```

### Verdict

Les **mécanismes de panne difficiles** sont en grande partie là.

L’**orchestrateur sémantique de recovery** reste à construire.

---

# 20. Écarts sémantiques prioritaires

## 20.1 `WAITING_APPROVAL` terminal dans V1

À corriger conceptuellement en V2 :

```text
Invocation returned != Run terminal
```

## 20.2 `UNKNOWN_EFFECT` comme RunStatus

La cible préfère :

```text
Run WAITING
because Effect UNKNOWN
```

plutôt qu’un Run intrinsèquement `UNKNOWN_EFFECT`.

## 20.3 Approval consumption mélangée à Approval decision

```text
CLAIMED / EXECUTED
```

doivent probablement sortir de `ApprovalStatus`.

## 20.4 Session utilisée comme Conversation

À scinder.

## 20.5 Message LLM utilisé comme Message métier

À scinder.

## 20.6 Effect lié à ToolCall

À généraliser.

## 20.7 Model Adapter utilisé comme Runtime Adapter

À introduire un niveau d’abstraction supérieur.

---

# 21. Ce qui doit être conservé presque tel quel

Ces composants ont une valeur élevée et doivent être réutilisés :

```text
ToolDefinition
ToolRisk
ToolExecutionPolicy
ToolExecutor
GuardrailPipeline
DataPolicy
Redactor
SecretProvider
ArtifactStore
BlobStore
S3BlobStore
AzureBlobStore
Memory/SQLite local adapters
Lease
LeaseStore
PostgresLeaseStore
FencingToken
FencedOperationStore
DistributedExecutionPolicy
DistributedWorkerController
RuntimeMetrics
OpenTelemetry sinks
provider adapters
qualification infrastructure
release compatibility tests
```

---

# 22. Ce qui doit être refactoré plutôt que jeté

```text
Runner
DurableRunner
RunStatus
RunStore
EffectRecord
RecoveryPlan
Session
SessionStore
Message
ApprovalRequest
ApprovalStatus
PostgresRunStore
PostgresStateStore
Event/Audit surfaces
```

---

# 23. Ce qui doit être créé

```text
AgentRuntimeAdapter
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeBinding
RuntimeInvocation
RuntimeRegistry

Conversation
Actor
Participant
MessageRecipient
ConversationStore
MessageStore

Effect source/target abstraction
ExternalReference
ReconciliationCase
ReconciliationPort
ReconciliationStrategy

PolicyEvaluator
Principal
SecurityContext
AuthorizationPort
IdentityProviderPort

WorkerRegistry
OwnershipContext
ResourceIdentity

AuditStore
AuditEvent domain object

OutboxStore
InboxStore

Connector
ConnectorDescriptor
ConnectorCapability
ConnectorRegistry

CodingAgentAdapter
Workspace
Git references
CommandExecution boundary

V2 application services
Public API facade
HTTP/OpenAPI optional adapter

normalized PostgreSQL V2 schema
```

---

# 24. Proposition d’architecture de transition

## Ne pas remplacer V1

Construire :

```text
                    PyAgentsKit 2 Reliability Core
                              │
        ┌─────────────────────┼──────────────────────┐
        │                     │                      │
 Native V1 Runner      External Agent Runtime    Coding Runtime
 Adapter                Adapters                  Adapters
        │                     │                      │
  Current Runner        LangGraph/etc.        Codex/Claude Code
```

Le `Runner` actuel devient :

```text
NativeRuntimeAdapter
```

et continue de fournir une excellente expérience autonome.

---

# 25. Namespace cible recommandé

Une option compatible :

```text
pyagentskit/
├── v1 compatibility modules
│
├── reliability/
│   ├── runs.py
│   ├── recovery.py
│   ├── effects.py
│   ├── approvals.py
│   ├── conversations.py
│   ├── coordination.py
│   └── security.py
│
├── runtime_adapters/
│   ├── base.py
│   ├── native.py
│   ├── langgraph.py
│   ├── pydantic_ai.py
│   └── coding/
│
├── connectors/
│
├── stores/
│   ├── postgres/
│   ├── sqlite/
│   └── memory/
│
├── application/
│
└── api/
```

Le détail exact peut varier, mais la séparation est importante.

---

# 26. Pourquoi la cible doit probablement être V2.0

Le contrat V1 actuel est volontairement très fort :

```text
exact 155 root symbols
frozen RunStatus
frozen schemas
frozen provider signatures
```

Or la cible implique :

- nouvelle signification du Run ;
- Session ≠ Conversation ;
- nouveau runtime abstraction layer ;
- nouvelles entités ;
- nouvel Effect lifecycle ;
- nouveaux stores ;
- nouveau schéma PostgreSQL ;
- nouvelle API applicative.

Forcer cela en 1.7 tout en prétendant préserver exactement les sémantiques V1 créerait une dette importante.

### Recommandation

```text
1.6.x
= maintenance/hardening V1

2.0.0a1
= Reliability Core foundations

2.0.0a2
= Runtime Adapter + Native adapter

2.0.0a3
= Effect/Reconciliation V2

2.0.0a4
= PostgreSQL normalized stores

2.0.0b1
= Governance/Security/Audit

2.0.0b2
= Connectors + Coding Agents

2.0.0rc1
= Public API + migration + production qualification
```

---

# 27. Plan de fermeture de l’écart

## Phase A — Domain Core V2

Priorité maximale.

Créer :

```text
Run
Session
Conversation
Message
Actor
Participant
Effect
Approval
Lease
RuntimeInvocation
Artifact
AuditEvent
```

et les Value Objects.

**Objectif :** figer les sémantiques avant d’ajouter les adapters.

---

## Phase B — AgentRuntimeAdapter

Créer le contrat cible.

Puis implémenter d’abord :

```text
NativePyAgentsRuntimeAdapter
```

au-dessus du `Runner` actuel.

Cela valide immédiatement que l’architecture fonctionne sans perdre la V1.

Ensuite :

```text
CustomRuntimeAdapter test fixture
```

puis un premier vrai runtime externe.

---

## Phase C — Recovery + Reconciliation V2

Transformer :

```text
RecoveryPlan(bool)
```

en :

```text
RecoveryPlan
RecoveryBlocker
NextAction
```

Créer :

```text
ReconciliationCase
ReconciliationPort
```

---

## Phase D — Persistence V2

Créer des tables sémantiques séparées.

Ne pas commencer par remplacer tout le PostgreSQL existant.

Introduire une deuxième famille de stores.

---

## Phase E — Governance + Security

Ajouter :

```text
Principal
SecurityContext
PolicyEvaluator
AuthorizationPort
ApprovalScope
SoD
multi-approval
```

---

## Phase F — Audit + Outbox/Inbox

Indispensable pour la cible production.

```text
AuditStore
OutboxStore
InboxStore
```

---

## Phase G — Coding Agent

Premier adapter recommandé :

```text
CLI/process-based coding adapter
```

avant les SDK plus complexes.

Il permettra de tester :

```text
workspace
command
patch
git push
PR
deploy
Effect safety
```

---

## Phase H — Connectors

Formaliser :

```text
Connector
Capabilities
ExternalReference
reconciliation
webhook/inbox
```

---

## Phase I — Public API V2

Exposer les Application Services seulement quand le domaine est stabilisé.

---

# 28. Ordre de priorité réel

Ne pas attaquer le schéma PostgreSQL 24 en premier.

Le meilleur ordre est :

```text
1. Domain semantics
2. AgentRuntimeAdapter
3. RuntimeInvocation
4. Effect/Reconciliation V2
5. RecoveryPlanner
6. Persistence ports V2
7. PostgreSQL V2
8. Governance/Security
9. Audit/Outbox/Inbox
10. Coding agents
11. Connectors
12. Public API
13. Full production qualification
```

Le PostgreSQL doit matérialiser le domaine, pas le définir.

---

# 29. Risque principal si l’on continue sans transition V2

Le plus grand risque n’est pas un bug.

C’est de créer deux modèles en parallèle à l’intérieur des mêmes classes :

```text
Session = Conversation et Session != Conversation
Run WAITING est terminal et non-terminal
Effect = ToolCall et Effect > ToolCall
Model adapter = Runtime adapter et Runtime adapter > Model adapter
```

Cela produirait progressivement :

```text
flags
special cases
if runtime == ...
metadata conventions
status overloading
JSONB polymorphism
```

et détruirait précisément la clarté architecturale recherchée.

---

# 30. Forces particulières de l’existant

La nouvelle cible ne part pas de zéro.

Elle part avec des avantages rares :

### A. Le problème difficile du fencing est déjà traité

Beaucoup de frameworks n’ont aucune réponse sérieuse au zombie worker.

PyAgentsKit en a une.

### B. `UNKNOWN` existe déjà

C’est une excellente décision.

### C. Les retries ne sont pas naïfs

Le projet sépare déjà model retry et tool effects.

### D. La compatibilité publique est testée

Le discipline V1 est solide.

### E. La production qualification n’est pas uniquement documentaire

Les tests SIGKILL/SIGSTOP/PostgreSQL réels sont très précieux.

### F. Les adapters storage sont déjà bien séparés

Memory / SQLite / PostgreSQL / S3 / Azure constituent une bonne base.

---

# 31. Evaluation finale

## Maturité du produit actuel dans son propre scope

```text
ÉLEVÉE
```

Le dépôt possède des preuves concrètes de qualité et de robustesse.

## Alignement avec la cible actuelle

```text
≈ 55 %
```

## Alignement des fondations de fiabilité

```text
FORT
```

## Alignement du modèle de produit

```text
MOYEN
```

## Alignement runtime/framework-neutral

```text
FAIBLE
```

## Alignement coding agents/connectors

```text
TRÈS FAIBLE
```

---

# 32. Verdict architectural

L’existant PyAgentsKit 1.6.0 est **plus mature techniquement que son alignement avec la cible ne le laisse croire**.

Le score ~55 % ne signifie donc pas :

> « il reste la moitié de V1.6 à coder ».

Il signifie :

> « la cible a changé de niveau d’abstraction ».

La V1.6 a déjà construit une grande partie du moteur de fiabilité :

```text
Durability
Effects
Approvals
Leases
Fencing
PostgreSQL
Artifacts
Observability
Failure qualification
```

La prochaine étape doit maintenant transformer ce moteur en une plateforme réellement :

```text
framework-neutral
runtime-neutral
connector-aware
coding-agent-aware
domain-explicit
production-queryable
```

La stratégie la plus sûre est donc :

> **conserver la V1.6 comme runtime natif stable, construire un Reliability Core V2 au-dessus, puis migrer progressivement les mécanismes actuels derrière les nouveaux ports.**

---

# 33. Next step recommandé

Le prochain artefact utile n’est pas encore un nouveau document théorique.

Il faut produire un **plan d’implémentation de convergence V1.6 → Target V2**, package par package et PR par PR.

Je recommande :

```text
../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md
```

avec :

```text
Epic 0 — Freeze V1 compatibility boundary
Epic 1 — Domain Core V2
Epic 2 — AgentRuntimeAdapter
Epic 3 — Native Runner Adapter
Epic 4 — Effect/Reconciliation V2
Epic 5 — RecoveryPlanner V2
Epic 6 — Persistence Ports V2
Epic 7 — PostgreSQL Normalized Model
Epic 8 — Governance/Security
Epic 9 — Audit/Outbox/Inbox
Epic 10 — Coding Agent Adapter
Epic 11 — External Connectors
Epic 12 — Public API
Epic 13 — Migration
Epic 14 — Production Qualification
```

Chaque Epic devrait ensuite être découpé en PRs atomiques, avec critères d’acceptation et stratégie de compatibilité.
