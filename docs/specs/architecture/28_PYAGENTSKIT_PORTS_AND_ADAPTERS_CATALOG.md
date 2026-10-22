# PyAgentsKit — Ports & Adapters Catalog

**Document :** `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Architecture hexagonale — Catalogue des Ports & Adapters  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md`
- `../architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`

---

# 1. Objet

Ce document définit le **catalogue canonique des Ports & Adapters** de PyAgentsKit V2.

Il formalise :

- les ports entrants ;
- les ports sortants ;
- les adapters inbound ;
- les adapters outbound ;
- leurs responsabilités ;
- leurs modèles d’échange ;
- leurs capacités ;
- leurs erreurs ;
- leurs garanties de sûreté ;
- leurs règles de composition ;
- leurs obligations de contract testing ;
- leur positionnement dans la topologie DDD/hexagonale.

Le principe directeur est :

> **Le domaine et l’application définissent ce dont PyAgentsKit a besoin ; les adapters décident comment ces besoins sont réalisés technologiquement.**

---

# 2. Architecture hexagonale — rappel

```text
                    INBOUND ADAPTERS
             Python / CLI / HTTP / Queue
                         │
                         ▼
                    INBOUND PORTS
                         │
                         ▼
                   APPLICATION
                         │
                         ▼
                       DOMAIN
                         │
                         ▼
                   OUTBOUND PORTS
                         │
                         ▼
                   OUTBOUND ADAPTERS
        Runtime / DB / Connector / Storage / IAM
```

---

# 3. Règle fondamentale

Les ports appartiennent au **cœur de l’application**.

Les adapters appartiennent à l’infrastructure.

Donc :

```text
application
defines the port

adapter
implements the port
```

et jamais l’inverse.

---

# 4. Port entrant vs port sortant

## Inbound Port

Répond à :

```text
What can an external actor ask PyAgentsKit to do?
```

Exemples :

```text
CreateRun
ResumeRun
Approve
Reject
ReconcileEffect
AppendMessage
```

## Outbound Port

Répond à :

```text
What does PyAgentsKit need from the outside world?
```

Exemples :

```text
RunRepository
AgentRuntimeAdapter
Connector
AuthorizationPort
BlobStore
AuditStore
```

---

# 5. Catalogue global

## Inbound Ports

```text
IP-01 RunCommandPort
IP-02 RunQueryPort
IP-03 EffectCommandPort
IP-04 EffectQueryPort
IP-05 ApprovalCommandPort
IP-06 ApprovalQueryPort
IP-07 ConversationCommandPort
IP-08 ConversationQueryPort
IP-09 ArtifactQueryPort
IP-10 WorkerAdminPort
IP-11 HealthQueryPort
IP-12 AuditQueryPort
```

## Outbound Ports

```text
OP-01 RunRepository
OP-02 SessionRepository
OP-03 ConversationRepository
OP-04 MessageRepository
OP-05 MemoryRepository
OP-06 EffectRepository
OP-07 ReconciliationRepository
OP-08 ApprovalRepository
OP-09 LeaseRepository
OP-10 WorkerRepository
OP-11 ArtifactRepository
OP-12 AuditStore
OP-13 OutboxStore
OP-14 InboxStore
OP-15 BlobStore
OP-16 AgentRuntimeAdapter
OP-17 RuntimeRegistry
OP-18 Connector
OP-19 ConnectorRegistry
OP-20 ReconciliationPort
OP-21 AuthorizationPort
OP-22 IdentityProviderPort
OP-23 SecretProvider
OP-24 PolicyEvaluator
OP-25 TelemetryPort
OP-26 EventPublisher
OP-27 ClockPort
OP-28 UnitOfWork
```

---

# 6. Inbound Adapter Catalog

Adapters entrants candidats :

```text
IA-01 Python Async SDK
IA-02 Python Sync SDK
IA-03 CLI
IA-04 HTTP / REST API
IA-05 Worker Loop
IA-06 Queue Consumer
IA-07 Webhook Receiver
IA-08 Admin Console / Operations API
```

---

# 7. Outbound Adapter Catalog

Adapters sortants candidats :

```text
OA-01 Memory Persistence
OA-02 SQLite Persistence
OA-03 PostgreSQL Persistence
OA-04 Native Runtime
OA-05 LangGraph Runtime
OA-06 PydanticAI Runtime
OA-07 OpenAI Agents Runtime
OA-08 Codex Runtime
OA-09 Claude Code Runtime
OA-10 OpenCode Runtime
OA-11 GitHub Connector
OA-12 GitLab Connector
OA-13 Slack Connector
OA-14 Jira Connector
OA-15 Generic HTTP Connector
OA-16 S3 Blob Adapter
OA-17 Azure Blob Adapter
OA-18 Filesystem Blob Adapter
OA-19 OIDC/AuthZ Adapter
OA-20 Environment Secret Adapter
OA-21 Vault-like Secret Adapter
OA-22 OpenTelemetry Adapter
OA-23 Structured Logging Adapter
OA-24 PostgreSQL Audit Adapter
```

---

# 8. Port Design Principles

Chaque port doit être :

```text
small
cohesive
typed
stable
technology-neutral
capability-aware where needed
```

Éviter :

```text
GenericInfrastructurePort
execute_anything()
save_anything()
call_provider()
```

---

# 9. Inbound Port IP-01 — RunCommandPort

## Responsabilité

Mutations du lifecycle des Runs.

## Opérations candidates

```text
create_run
start_run
resume_run
pause_run
cancel_run
```

## Contrat conceptuel

```python
class RunCommandPort(Protocol):
    async def create(self, command: CreateRunCommand) -> RunView: ...
    async def start(self, command: StartRunCommand) -> RunView: ...
    async def resume(self, command: ResumeRunCommand) -> RunView: ...
    async def pause(self, command: PauseRunCommand) -> RunView: ...
    async def cancel(self, command: CancelRunCommand) -> RunView: ...
```

## Invariants

```text
WAITING non-terminal
invalid transition rejected
mutations audited where required
```

---

# 10. Inbound Port IP-02 — RunQueryPort

## Opérations

```text
get_run
list_runs
timeline
status
```

## Règle

Lecture uniquement.

Aucune mutation cachée.

---

# 11. Inbound Port IP-03 — EffectCommandPort

## Opérations

```text
reconcile_effect
resolve_effect_manually
retry_effect_when_safe
cancel_effect_if_supported
```

## Safety

Ne doit jamais offrir :

```text
force_success_without_reason
blind_retry_unknown
```

---

# 12. Inbound Port IP-04 — EffectQueryPort

## Opérations

```text
get_effect
list_effects
list_unresolved
get_reconciliation_case
```

---

# 13. Inbound Port IP-05 — ApprovalCommandPort

## Opérations

```text
approve
reject
cancel
```

Éventuellement :

```text
delegate
escalate
```

si futur modèle.

---

# 14. Inbound Port IP-06 — ApprovalQueryPort

```text
get_approval
list_pending
list_for_run
```

---

# 15. Inbound Port IP-07 — ConversationCommandPort

```text
create_session
create_conversation
append_message
add_participant
write_memory
```

---

# 16. Inbound Port IP-08 — ConversationQueryPort

```text
get_session
get_conversation
list_messages
read_memory
```

---

# 17. Inbound Port IP-09 — ArtifactQueryPort

```text
get_artifact
open_artifact
list_for_run
verify_checksum
```

---

# 18. Inbound Port IP-10 — WorkerAdminPort

Opérations sensibles :

```text
drain_worker
inspect_worker
force_takeover
freeze_effects
resume_effects
```

Admin-only.

---

# 19. Inbound Port IP-11 — HealthQueryPort

```text
liveness
readiness
dependencies
capabilities
```

---

# 20. Inbound Port IP-12 — AuditQueryPort

```text
list_for_run
list_for_effect
list_for_approval
timeline
search
```

Read-only.

---

# 21. Inbound Adapter IA-01 — Python Async SDK

## Rôle

Façade de référence.

```python
from pyagentskit.api import PyAgentsKit

kit = PyAgentsKit(...)
run = await kit.runs.create(...)
```

## Règle

L’Async SDK appelle les Inbound Ports, jamais directement les repositories.

---

# 22. Inbound Adapter IA-02 — Python Sync SDK

Façade sync au-dessus des mêmes use cases.

Elle ne doit pas avoir de sémantique différente.

---

# 23. Inbound Adapter IA-03 — CLI

Commandes candidates :

```text
pyagentskit runs get
pyagentskit runs resume
pyagentskit effects reconcile
pyagentskit approvals approve
pyagentskit workers drain
pyagentskit db migrate
```

Le CLI est un adapter.

Aucune business rule dans Click/Typer/argparse.

---

# 24. Inbound Adapter IA-04 — HTTP API

Mappe :

```text
HTTP Request
→ Command/Query
→ Application
→ DTO
→ HTTP Response
```

---

# 25. HTTP Adapter — interdictions

Ne pas mettre dans les routes :

```text
Run transition logic
Approval scope logic
Effect retry policy
Lease takeover logic
```

---

# 26. Inbound Adapter IA-05 — Worker Loop

Le Worker Loop convertit :

```text
work availability
→ application command
```

Il ne possède pas la logique de Run.

---

# 27. Inbound Adapter IA-06 — Queue Consumer

Un message reçu :

```text
does not grant ownership
```

Flux :

```text
receive
↓
Inbox dedup
↓
application command
↓
lease acquisition if needed
```

---

# 28. Inbound Adapter IA-07 — Webhook Receiver

Responsabilités :

```text
signature validation
timestamp validation
replay protection
Inbox persistence
schema validation
command mapping
```

Pas de mutation métier directe.

---

# 29. Inbound Adapter IA-08 — Admin / Ops

Opérations à forte sensibilité.

Exemples :

```text
force takeover
manual Effect resolution
kill switch
repair
migration verification
```

Doit exiger :

```text
authorization
reason
audit
```

---

# 30. Outbound Port OP-01 — RunRepository

## Responsabilité

Persister l’aggregate Run.

```python
class RunRepository(Protocol):
    async def get(self, run_id: RunId) -> Run: ...
    async def add(self, run: Run) -> None: ...
    async def save(self, run: Run, expected_version: int) -> None: ...
```

## Contrat

```text
optimistic concurrency
tenant-safe
no hidden transition
```

---

# 31. RunRepository — opérations additionnelles

Possibles :

```text
find_recoverable
list_by_session
exists
```

Mais éviter un repository de reporting générique.

---

# 32. Outbound Port OP-02 — SessionRepository

```text
get
add
save
```

Session reste distincte de Conversation.

---

# 33. Outbound Port OP-03 — ConversationRepository

```text
get
add
save
list_for_session
```

---

# 34. Outbound Port OP-04 — MessageRepository

Le Message pouvant être append-oriented :

```text
append
get
list
deduplicate
```

---

# 35. Outbound Port OP-05 — MemoryRepository

```text
get
put
delete/expire according policy
list_by_scope
```

---

# 36. Outbound Port OP-06 — EffectRepository

Port critique.

```python
class EffectRepository(Protocol):
    async def get(self, effect_id: EffectId) -> Effect: ...
    async def reserve(self, effect: Effect) -> EffectReservationResult: ...
    async def save(self, effect: Effect, expected_version: int) -> None: ...
    async def find_by_idempotency_key(...) -> Effect | None: ...
```

---

# 37. EffectRepository — garanties

```text
idempotency uniqueness
optimistic concurrency
durable intent before external call
no silent overwrite
```

---

# 38. Outbound Port OP-07 — ReconciliationRepository

```text
create_case
get_case
save_case
list_open
```

---

# 39. Outbound Port OP-08 — ApprovalRepository

```text
get
add
decide
list_pending
```

Le repository ne décide pas si une approval est applicable.

Cette règle est dans Domain/Application.

---

# 40. Outbound Port OP-09 — LeaseRepository

Port safety-critical.

```text
acquire
renew
release
validate
takeover
get_current
```

---

# 41. LeaseRepository — garanties

```text
one active authoritative lease per resource
monotonic fencing
database-authoritative time
atomic takeover
```

---

# 42. Outbound Port OP-10 — WorkerRepository

```text
register
heartbeat
mark_draining
mark_stopped
get
list
```

---

# 43. Outbound Port OP-11 — ArtifactRepository

Persiste les **métadonnées** Artifact.

Les bytes vivent dans BlobStore.

---

# 44. Outbound Port OP-12 — AuditStore

```text
append
query
```

Pas :

```text
update
delete
```

dans l’API normale.

---

# 45. Outbound Port OP-13 — OutboxStore

```text
append
claim_batch
mark_published
mark_failed
```

---

# 46. Outbound Port OP-14 — InboxStore

```text
reserve_external_event
mark_processed
mark_failed
```

Doit fournir déduplication.

---

# 47. Outbound Port OP-15 — BlobStore

Contrat conceptuel :

```python
class BlobStore(Protocol):
    async def put(...): ...
    async def open(...): ...
    async def exists(...): ...
    async def delete(...): ...
```

---

# 48. BlobStore — règle

Le BlobStore ne connaît pas :

```text
RunState
EffectStatus
Approval
```

C’est un port technique.

---

# 49. Outbound Port OP-16 — AgentRuntimeAdapter

Port central de la V2.

```python
class AgentRuntimeAdapter(Protocol):
    async def start(...): ...
    async def resume(...): ...
    async def cancel(...): ...
    async def inspect(...): ...
    async def checkpoint(...): ...
    async def close(...): ...
    def events(...): ...
```

---

# 50. AgentRuntimeAdapter — responsabilités

```text
translate canonical request
invoke runtime
translate runtime state
surface events
surface checkpoints
surface capabilities
```

---

# 51. AgentRuntimeAdapter — interdictions

Ne doit pas :

```text
decide Approval
decide Authorization
own Run state
own Effect truth
bypass EffectGateway
```

---

# 52. RuntimeAdapter capabilities

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
SUBAGENTS
SESSION_RESUME
STRUCTURED_OUTPUT
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
```

---

# 53. Outbound Port OP-17 — RuntimeRegistry

```text
register
get
list
capabilities
resolve
```

---

# 54. RuntimeRegistry — règle

La sélection du runtime doit être déclarative.

Pas :

```python
if runtime == "codex":
```

dans Application.

---

# 55. Outbound Port OP-18 — Connector

Contrat générique de systèmes externes.

Le Connector ne doit pas être trop universel.

Il expose un descriptor + opérations capability-aware.

---

# 56. Connector capabilities

```text
READ
WRITE
NATIVE_IDEMPOTENCY
RECONCILIATION
WEBHOOKS
POLLING
PAGINATION
BATCHING
LONG_RUNNING_OPERATION
```

---

# 57. Connector — design

Exemple conceptuel :

```python
class Connector(Protocol):
    @property
    def descriptor(self) -> ConnectorDescriptor: ...

    async def read(...): ...
    async def write(...): ...
```

Mais les connectors spécialisés peuvent exposer des interfaces plus précises.

---

# 58. Outbound Port OP-19 — ConnectorRegistry

```text
register
get
resolve
list
capabilities
```

---

# 59. Outbound Port OP-20 — ReconciliationPort

Port provider-specific.

```python
class ReconciliationPort(Protocol):
    async def reconcile(
        self,
        request: ReconciliationRequest,
    ) -> ReconciliationResult:
        ...
```

---

# 60. ReconciliationPort — résultat

```text
CONFIRMED_SUCCESS
CONFIRMED_FAILURE
STILL_UNKNOWN
NOT_FOUND
MANUAL_REQUIRED
```

selon sémantique finale.

---

# 61. Outbound Port OP-21 — AuthorizationPort

```text
authorize(principal, action, resource, context)
```

Retour :

```text
AuthorizationDecision
```

---

# 62. AuthorizationPort — règle

Le port ne doit jamais retourner simplement :

```text
True / False
```

si la cible nécessite :

```text
reason
policy
decision id
obligations
```

---

# 63. Outbound Port OP-22 — IdentityProviderPort

Responsabilité :

```text
resolve/validate principal identity
```

Le domaine ne connaît pas :

```text
OIDC token
JWT library
provider claims object
```

---

# 64. Outbound Port OP-23 — SecretProvider

```text
resolve(SecretReference)
```

Ne retourne jamais un secret au runtime si non nécessaire.

---

# 65. SecretProvider — contraintes

```text
scoped retrieval
short-lived where possible
no logs
no audit payload
no LLM context by default
```

---

# 66. Outbound Port OP-24 — PolicyEvaluator

```text
evaluate(policy_context)
→ PolicyDecision
```

Peut décider :

```text
ALLOW
DENY
REQUIRE_APPROVAL
REQUIRE_STRONGER_CONTROL
```

---

# 67. PolicyEvaluator ≠ AuthorizationPort

```text
AuthorizationPort
→ may this principal do this?

PolicyEvaluator
→ under current business/security policy, what controls are required?
```

---

# 68. Outbound Port OP-25 — TelemetryPort

```text
emit metric
create span
record structured event
```

Pas de dépendance au SDK OpenTelemetry dans Application.

---

# 69. Outbound Port OP-26 — EventPublisher

Pour Integration Events.

```text
publish
```

Souvent couplé à Outbox.

---

# 70. Outbound Port OP-27 — ClockPort

Permet :

```text
deterministic testing
time control
expiry logic
```

Attention :

pour Lease authority distribuée, PostgreSQL time reste autoritatif.

---

# 71. Outbound Port OP-28 — UnitOfWork

Contrat conceptuel :

```python
class UnitOfWork(Protocol):
    async def __aenter__(self): ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

---

# 72. UnitOfWork — règle

Ne doit pas exposer :

```text
psycopg connection
SQLAlchemy Session
```

au domaine/application.

---

# 73. Memory Persistence Adapter

Usage :

```text
unit tests
examples
single-process demos
```

Ne doit pas prétendre fournir les garanties de PostgreSQL distribué.

---

# 74. SQLite Persistence Adapter

Usage :

```text
local development
single-node durability
tests
```

Limitations explicites :

```text
distributed ownership
concurrent worker semantics
```

---

# 75. PostgreSQL Persistence Adapter

Backend production de référence.

Doit implémenter :

```text
repositories
UnitOfWork
LeaseRepository
OutboxStore
InboxStore
AuditStore
```

---

# 76. PostgreSQL adapter — contraintes

```text
transaction boundaries explicit
optimistic concurrency
unique idempotency
fencing monotonicity
primary reads for safety
```

---

# 77. Native Runtime Adapter

Encapsule le Runner V1.

```text
V2 canonical runtime contracts
↓ ACL
V1 Runner
```

---

# 78. LangGraph Runtime Adapter

Responsabilités :

```text
map graph invocation
map thread/checkpoint
map events
map status
map resume semantics
```

---

# 79. PydanticAI Runtime Adapter

Même principe.

Ne pas exposer les classes PydanticAI hors adapter.

---

# 80. OpenAI Agents Runtime Adapter

Doit mapper :

```text
session/run
handoffs
tools
streaming
structured outputs
```

selon capabilities disponibles.

---

# 81. Coding Runtime Adapters

Famille :

```text
Codex
Claude Code
OpenCode
```

Ils doivent être traités comme runtimes agentiques, pas comme de simples subprocess.

---

# 82. Coding runtime capability examples

```text
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
SESSION_RESUME
SUBAGENTS
STRUCTURED_OUTPUT
```

---

# 83. GitHub Connector Adapter

Responsabilités possibles :

```text
repository lookup
branch lookup
commit lookup
PR create
PR inspect
PR merge
workflow status
reconciliation
```

Mutations persistantes deviennent Effects.

---

# 84. GitLab Connector Adapter

Equivalent conceptuel.

---

# 85. Slack Connector Adapter

```text
send message
read thread
webhook/events
```

Envoi de message peut être Effect selon use case.

---

# 86. Generic HTTP Connector

Doit rester limité.

Il fournit :

```text
transport primitives
```

mais ne remplace pas la sémantique provider-specific.

Principe :

```text
Generic HTTP != Provider semantics
```

---

# 87. Storage Adapters

```text
FilesystemBlobStore
S3BlobStore
AzureBlobStore
```

Tous passent :

```text
BlobStoreContract
```

---

# 88. Security Adapters

```text
EnvironmentSecretProvider
VaultSecretProvider
OIDCIdentityProvider
ExternalAuthorizationAdapter
```

---

# 89. Telemetry Adapters

```text
OpenTelemetryAdapter
StructuredLoggingAdapter
PrometheusMetricsAdapter
```

Ils ne deviennent pas source d’audit autoritative.

---

# 90. Port input models

Les ports doivent utiliser :

```text
Command
Query
Request
Reference
Value Object
```

pas des dictionnaires arbitraires lorsque la sémantique est importante.

---

# 91. Port output models

Préférer :

```text
Domain object within application boundary
Published DTO
Result object
```

selon contexte.

---

# 92. Result pattern

Pour les opérations où plusieurs résultats métier sont normaux :

```text
Result objects
```

peuvent être préférables aux exceptions.

Exemple :

```text
EffectReservationResult
LeaseAcquireResult
ReconciliationResult
```

---

# 93. Exceptions

Réserver les exceptions aux erreurs :

```text
unexpected
invalid
infrastructure
authorization failures
```

selon contrat.

---

# 94. Error taxonomy

Ports doivent définir des erreurs canoniques :

```text
NotFound
Conflict
Unavailable
Timeout
Unauthorized
PolicyDenied
StaleOwnership
AmbiguousOutcome
UnsupportedCapability
```

---

# 95. Adapter error translation

```text
psycopg.UniqueViolation
→ IdempotencyConflict / ConcurrencyConflict

HTTP 429
→ ConnectorRateLimited

provider timeout after write
→ AmbiguousOutcome

runtime SDK exception
→ RuntimeAdapterError
```

---

# 96. No raw provider errors

Ne pas laisser remonter :

```text
botocore.ClientError
httpx.ConnectError
psycopg.Error
github.UnknownObjectException
```

au domaine/public API.

---

# 97. Adapter descriptors

Chaque adapter complexe peut publier :

```text
name
version
capabilities
health
compatibility
control_level
```

---

# 98. RuntimeDescriptor

Exemple :

```text
runtime_name
runtime_version
adapter_name
adapter_version
capabilities
control_level
```

---

# 99. ConnectorDescriptor

Exemple :

```text
connector_name
provider
version
capabilities
idempotency_mode
reconciliation_level
```

---

# 100. SideEffectControlLevel

Valeurs candidates :

```text
OBSERVE_ONLY
PARTIAL_CONTROL
FULL_CONTROL
```

---

# 101. Runtime control level

Même logique :

```text
OBSERVE_ONLY
LIFECYCLE_CONTROL
FULL_INTERCEPTION
```

selon design final.

---

# 102. Adapter registration

Toujours explicite.

Exemple :

```python
registry.register(
    "native",
    NativeRuntimeAdapter(...),
)
```

---

# 103. Auto-discovery

Si supportée :

```text
opt-in
```

en production.

Ne jamais exécuter silencieusement un plugin découvert.

---

# 104. Adapter version compatibility

Chaque adapter peut déclarer :

```text
core_min_version
core_max_version
provider_version_range
```

---

# 105. Adapter health

Un adapter peut exposer :

```text
healthy
degraded
unavailable
misconfigured
```

sans que le domaine dépende directement de ces enums si non nécessaires.

---

# 106. Adapter readiness

Readiness globale peut dépendre de :

```text
required adapters
```

mais pas nécessairement de tous les adapters configurés.

---

# 107. Optional adapters

Exemple :

```text
S3 unavailable
```

ne doit pas rendre toute l’application non-ready si aucun workflow actif ne nécessite S3.

---

# 108. Required adapters

Exemple :

```text
PostgreSQL unavailable
```

dans profil distributed production :

```text
readiness false
```

---

# 109. Port granularity

Préférer plusieurs ports cohérents à un mega-port.

Mauvais :

```text
InfrastructurePort
```

Bon :

```text
RunRepository
LeaseRepository
BlobStore
AuthorizationPort
```

---

# 110. Repository vs Store

Convention :

```text
Repository
= aggregate persistence

Store
= technical durable storage
```

Exemple :

```text
RunRepository
EffectRepository

BlobStore
AuditStore
OutboxStore
```

---

# 111. Connector vs Repository

Un Connector parle à un système externe métier.

Un Repository persiste un aggregate PyAgentsKit.

---

# 112. Runtime Adapter vs Model Adapter

```text
Model Adapter
= LLM generation interface

Runtime Adapter
= agent lifecycle/control interface
```

Les providers V1 OpenAI/Anthropic restent des Model Adapters.

---

# 113. Runtime Adapter vs Connector

```text
Runtime Adapter
= controls an agent runtime

Connector
= talks to a business/external system
```

Codex :

```text
Runtime Adapter
```

GitHub :

```text
Connector
```

---

# 114. Runtime Adapter vs Worker

Un worker héberge/coordonne l’exécution.

Le runtime adapter contrôle le runtime.

Ce sont deux responsabilités différentes.

---

# 115. Port ownership

Ports sont placés dans :

```text
application/ports/
```

sauf certaines interfaces purement domain-specific.

---

# 116. Inbound port placement

```text
application/ports/inbound/
```

---

# 117. Outbound port placement

```text
application/ports/outbound/
```

---

# 118. Persistence port placement

```text
application/ports/outbound/repositories/
```

---

# 119. Runtime port placement

```text
application/ports/outbound/runtime/
```

---

# 120. Connector port placement

```text
application/ports/outbound/connectors/
```

---

# 121. Security port placement

```text
application/ports/outbound/security/
```

---

# 122. Storage port placement

```text
application/ports/outbound/storage/
```

---

# 123. Messaging port placement

```text
application/ports/outbound/messaging/
```

---

# 124. Telemetry port placement

```text
application/ports/outbound/telemetry/
```

---

# 125. Adapter topology

```text
adapters/
├── inbound/
└── outbound/
```

---

# 126. Inbound adapter topology

```text
adapters/inbound/
├── python/
├── cli/
├── http/
├── workers/
└── webhooks/
```

---

# 127. Outbound adapter topology

```text
adapters/outbound/
├── persistence/
├── runtimes/
├── models/
├── connectors/
├── storage/
├── security/
└── telemetry/
```

---

# 128. Anti-Corruption Layer

Chaque adapter vers système externe complexe doit inclure :

```text
mapper
translator
normalizer
```

selon besoin.

---

# 129. Runtime ACL example

```text
LangGraph native state
↓
mapper.py
↓
RuntimeStatus
```

---

# 130. Connector ACL example

```text
GitHub PullRequest
↓
mapper.py
↓
ExternalReference
```

---

# 131. Persistence mapper example

```text
Postgres row
↓
mapping.py
↓
Effect aggregate
```

---

# 132. Inbound DTO mapper

```text
HTTP JSON
↓
schema
↓
CreateRunCommand
```

---

# 133. No direct cross-adapter calls

Un adapter GitHub ne doit pas appeler directement l’adapter PostgreSQL.

Le flux passe par Application.

---

# 134. Adapter independence

```text
runtime adapter A
must not import
runtime adapter B
```

Même règle pour connectors.

---

# 135. Contract Testing Strategy

Chaque port ayant plusieurs implémentations doit avoir une suite de tests contractuels.

---

# 136. Repository Contracts

```text
RunRepositoryContract
EffectRepositoryContract
ApprovalRepositoryContract
LeaseRepositoryContract
ConversationRepositoryContract
```

---

# 137. Runtime Adapter Contract

Teste :

```text
start
inspect
cancel if supported
resume if supported
event behavior
capability truthfulness
handle round-trip
error normalization
```

---

# 138. Connector Contract

Teste :

```text
descriptor
capabilities
read semantics
write semantics
idempotency
reconciliation
error mapping
```

---

# 139. BlobStore Contract

Teste :

```text
put
read/open
exists
checksum
delete
```

---

# 140. Authorization Contract

Teste :

```text
allow
deny
unavailable
tenant isolation
reason propagation
```

---

# 141. UnitOfWork Contract

Teste :

```text
commit
rollback
nested behavior if supported
exception rollback
```

---

# 142. Safety contract tests

Adapters safety-critical doivent prouver :

```text
no duplicate critical write
stale fencing rejected
UNKNOWN preserved
scope isolation
```

---

# 143. Fake Adapters

Le package `testing/` peut fournir :

```text
FakeRuntimeAdapter
FakeConnector
FakeAuthorizationPort
FakeSecretProvider
InMemoryRepositories
```

---

# 144. Fake adapter rule

Un fake doit simuler le contrat, pas inventer une sémantique simplifiée incompatible.

---

# 145. Fault Injection Adapters

Exemples :

```text
TimeoutRuntimeAdapter
AmbiguousWriteConnector
FailingAuditStore
SlowLeaseRepository
```

utile pour tests Recovery.

---

# 146. Capability negotiation

Avant opération optionnelle :

```text
inspect capability
```

Exemple :

```text
RESUME absent
→ logical restart policy
```

---

# 147. Capability truthfulness

Un adapter ne doit jamais annoncer :

```text
NATIVE_IDEMPOTENCY
```

si le provider ne la garantit pas réellement.

---

# 148. Safe degradation

Chaque port/adaptor doit documenter :

```text
what happens when unavailable?
```

---

# 149. Safe degradation — Runtime

Runtime indisponible :

```text
Run WAITING / failed according policy
```

Pas de fallback silencieux vers autre runtime.

---

# 150. Safe degradation — Connector

Connector indisponible :

```text
Effect NOT_STARTED / UNKNOWN depending send boundary
```

---

# 151. Safe degradation — Authorization

Pour action critique :

```text
fail closed
```

---

# 152. Safe degradation — Audit

Selon profil :

```text
STANDARD
HIGH_ASSURANCE
```

---

# 153. Safe degradation — PostgreSQL

Si autorité durable non disponible :

```text
no new Protected Effects
readiness false
```

---

# 154. Safe degradation — BlobStore

Peut bloquer uniquement les workflows nécessitant artifacts.

---

# 155. Composition Root

Tout wiring concret vit dans :

```text
bootstrap/
```

---

# 156. Composition example

```python
run_repo = PostgresRunRepository(...)
effect_repo = PostgresEffectRepository(...)
runtime = NativeRuntimeAdapter(...)
authorization = OIDCAuthorizationAdapter(...)
audit = PostgresAuditStore(...)

app = Application(
    run_repository=run_repo,
    effect_repository=effect_repo,
    runtime=runtime,
    authorization=authorization,
    audit=audit,
)
```

---

# 157. Profiles

Profils candidats :

```text
Local
SQLite
PostgresSingleNode
DistributedPostgres
HighAssurance
```

---

# 158. Local Profile

```text
Memory/SQLite
NativeRuntime
Filesystem
simple telemetry
```

---

# 159. Distributed Profile

```text
PostgreSQL
Lease/Fencing
Object Storage
OpenTelemetry
durable Audit
```

---

# 160. High Assurance Profile

Ajoute :

```text
strict authorization
mandatory audit
stronger approvals
restricted connectors
fail-closed policy
```

---

# 161. Adapter configuration

Les adapters reçoivent leur configuration via bootstrap.

Pas via Domain entities.

---

# 162. Secrets in adapters

Adapters reçoivent :

```text
SecretReference
```

ou mécanisme sécurisé.

Pas de secret hardcodé.

---

# 163. Tenant-aware adapters

Les adapters peuvent recevoir :

```text
TenantContext
```

mais doivent préserver isolation.

---

# 164. Multi-account connectors

Connector peut router vers :

```text
tenant-specific provider account
```

sans exposer credentials au domaine.

---

# 165. Observability of adapters

Chaque adapter doit produire :

```text
latency
error count
availability
operation name
```

sans payload sensible.

---

# 166. Trace boundaries

Créer des spans autour de :

```text
runtime.start
connector.write
repository.save
lease.acquire
artifact.put
```

---

# 167. Audit boundaries

Audit uniquement les événements significatifs de responsabilité.

Ne pas auditer chaque SQL.

---

# 168. Retry ownership

Le port/adaptor doit documenter :

```text
who owns retry?
```

Exemple :

```text
DB transient retry
→ persistence adapter

business Effect retry
→ application/effects

HTTP provider retry
→ connector if semantics permit
```

---

# 169. Retry ≠ Reconciliation

Principe obligatoire :

```text
adapter retry
must never hide ambiguous write
```

---

# 170. Timeout ownership

Timeouts de transport sont configurés dans adapters.

Mais leur interprétation métier appartient au niveau supérieur.

---

# 171. Circuit breaker

Peut vivre dans l’adapter ou decorator infrastructure.

Ne doit pas modifier la sémantique métier.

---

# 172. Rate limiting

Connector peut implémenter :

```text
backoff
Retry-After
budget
```

---

# 173. Bulk operations

Port doit expliciter :

```text
atomic?
partial?
ordered?
per-item result?
```

---

# 174. Streaming

Runtime/Event/Artifact ports peuvent utiliser :

```text
AsyncIterator
```

si adapté.

---

# 175. Backpressure

Streaming adapter doit documenter sa stratégie.

---

# 176. Cancellation

Cancellation d’une coroutine adapter :

```text
does not automatically mean external cancellation
```

Le port doit différencier :

```text
client cancellation
remote cancel request
```

---

# 177. Close semantics

`close()` ferme les ressources adapter.

Il ne doit pas implicitement :

```text
cancel durable Runs
```

---

# 178. Adapter lifecycle

Chaque adapter peut supporter :

```text
initialize
health
close
```

mais ces méthodes ne doivent pas devenir business API.

---

# 179. Adapter factories

Factories dans bootstrap :

```text
build_postgres_adapter
build_native_runtime
build_github_connector
```

---

# 180. No Service Locator in Domain

Interdit :

```text
get_adapter("github")
```

depuis une Entity.

La résolution appartient à Application/Registry.

---

# 181. Registry boundaries

RuntimeRegistry et ConnectorRegistry sont des ports/application services.

Pas des globals cachés.

---

# 182. Plugin ecosystem

Futur package tiers :

```text
pyagentskit-langgraph
pyagentskit-codex
pyagentskit-github
```

possible.

---

# 183. Plugin manifest

Doit déclarer :

```text
name
version
core compatibility
capabilities
security/control level
```

---

# 184. Third-party adapter trust

Installer un adapter tiers signifie exécuter du code.

Il doit être considéré dans threat model/supply chain.

---

# 185. Port stability levels

```text
EXPERIMENTAL
BETA
STABLE
DEPRECATED
```

---

# 186. Stable ports candidates

À terme :

```text
AgentRuntimeAdapter
RunRepository
EffectRepository
LeaseRepository
ApprovalRepository
BlobStore
Connector
```

---

# 187. Experimental ports

Exemple :

```text
multi-agent coordination port
```

si hors MVP V2.

---

# 188. Port versioning

Préférer extension additive.

Breaking change :

```text
major version
```

une fois stable.

---

# 189. Adapter versioning

Adapter version indépendant du core possible.

---

# 190. Error compatibility

Codes/erreurs canoniques doivent rester stables.

---

# 191. Dependency rules

```text
domain
!-> adapters

application
!-> concrete adapters

adapters
-> ports/domain contracts

bootstrap
-> all
```

---

# 192. Import-linter examples

```text
forbid domain -> adapters
forbid application -> adapters.outbound.*
forbid connector A -> connector B
forbid runtime A -> runtime B
```

---

# 193. Port anti-pattern — leaking ORM

Mauvais :

```python
async def save(session: AsyncSession, run: RunModel)
```

Bon :

```python
async def save(run: Run, expected_version: int)
```

---

# 194. Port anti-pattern — leaking HTTP

Mauvais :

```python
async def authorize(headers: dict)
```

Bon :

```python
async def authorize(request: AuthorizationRequest)
```

---

# 195. Port anti-pattern — leaking provider SDK

Mauvais :

```python
async def start(...) -> LangGraphState
```

Bon :

```python
async def start(...) -> RuntimeHandle
```

---

# 196. Port anti-pattern — generic dict

Mauvais :

```python
async def execute(payload: dict) -> dict
```

sauf cas transport générique réellement justifié.

---

# 197. Port anti-pattern — mega port

Mauvais :

```text
InfrastructurePort
```

qui combine :

```text
DB
Runtime
Connector
Audit
Storage
```

---

# 198. Adapter anti-pattern — business rule

Mauvais :

```text
GitHubConnector decides Approval requirement
```

La Governance décide.

---

# 199. Adapter anti-pattern — cross-context mutation

Mauvais :

```text
PostgresApprovalRepository updates runs table
```

---

# 200. Adapter anti-pattern — implicit fallback

Mauvais :

```text
Codex unavailable
→ silently use NativeRuntime
```

---

# 201. Adapter anti-pattern — swallowed ambiguity

Mauvais :

```text
timeout after write
→ retry automatically
```

---

# 202. Contract Test Matrix

| Port | Memory | SQLite | PostgreSQL | External |
|---|---:|---:|---:|---:|
| RunRepository | ✓ | ✓ | ✓ | — |
| EffectRepository | ✓ | ✓ | ✓ | — |
| ApprovalRepository | ✓ | ✓ | ✓ | — |
| LeaseRepository | ✓ | ✓ | ✓ | — |
| BlobStore | ✓ optional | FS | S3/Azure | ✓ |
| AgentRuntimeAdapter | Fake | — | — | Native/LangGraph/Codex |
| Connector | Fake | — | — | GitHub/etc. |
| AuditStore | Memory | SQLite optional | PostgreSQL | external optional |

---

# 203. Adapter Qualification Levels

```text
L0 — unit fake
L1 — contract compliant
L2 — integration tested
L3 — failure tested
L4 — production qualified
```

---

# 204. Runtime Adapter Qualification

Pour atteindre L4 :

```text
real provider/runtime
restart behavior
event disconnect
capability truthfulness
timeout behavior
recovery behavior
```

---

# 205. Connector Qualification

L4 nécessite :

```text
real idempotency semantics
ambiguous write tests
reconciliation
rate limits
schema evolution
auth failure
```

---

# 206. Persistence Qualification

L4 PostgreSQL nécessite :

```text
real PostgreSQL
multi-process
deadlocks
failover/restart
takeover
load
backup/restore
```

---

# 207. Port documentation template

Chaque port documenté avec :

```text
Purpose
Owner
Methods
Inputs
Outputs
Errors
Idempotency
Concurrency
Timeout
Retry
Security
Observability
Contract Tests
```

---

# 208. Adapter documentation template

Chaque adapter documenté avec :

```text
Implements
Provider/technology
Capabilities
Configuration
Secrets
Failure semantics
Retry semantics
Reconciliation
Health/readiness
Known limitations
Qualification level
```

---

# 209. Adapter selection

Application sélectionne un adapter via registry/config.

Pas via code provider-specific.

---

# 210. Adapter aliases

Possible :

```text
runtime="native"
connector="github-primary"
```

---

# 211. Multi-runtime deployment

Un worker peut annoncer :

```text
supported runtime capabilities
```

mais le scheduler/admission doit respecter la configuration.

---

# 212. Multi-connector deployment

Plusieurs comptes/providers possibles.

La sélection doit être explicite et tenant-safe.

---

# 213. Cross-cutting decorators

Certains concerns peuvent être implémentés comme decorators :

```text
TelemetryRunRepository
RetryingBlobStore
MetricsConnector
```

si la sémantique reste inchangée.

---

# 214. Decorator safety

Un decorator ne doit pas :

```text
turn UNKNOWN into FAILED
replay writes
bypass authz
```

---

# 215. Caching

Cache uniquement pour données non autoritatives ou avec invalidation sûre.

Jamais pour :

```text
Lease authority
Effect current status
Approval finality
```

---

# 216. Read replicas

Même règle.

Adapters de lecture peuvent les utiliser pour reporting.

Pas pour safety-critical decisions.

---

# 217. Health aggregation

Le bootstrap peut agréger :

```text
Postgres
Runtime
Connector
BlobStore
Authorization
```

selon dépendances requises.

---

# 218. Readiness policy

Readiness dépend du profil.

Exemple distributed :

```text
PostgreSQL required
LeaseRepository required
at least one configured runtime required
```

---

# 219. Liveness policy

Liveness :

```text
process alive and event loop functional
```

ne dépend pas forcément des providers.

---

# 220. Packaging extras

```text
pyagentskit[postgres]
pyagentskit[s3]
pyagentskit[azure]
pyagentskit[opentelemetry]
pyagentskit[langgraph]
pyagentskit[codex]
```

---

# 221. Core dependency policy

Le core ne doit pas forcer :

```text
psycopg
boto3
azure-storage-blob
langgraph
OpenTelemetry SDK
```

si l’adapter n’est pas utilisé.

---

# 222. Third-party extension path

Futur :

```text
entry points
```

ou registry explicite.

---

# 223. Default adapters

Le core peut fournir :

```text
MemoryRepository
NativeRuntimeAdapter
FilesystemBlobStore
```

comme expérience minimale.

---

# 224. Production reference adapters

Référence :

```text
PostgreSQL
Object Storage
OpenTelemetry
OIDC/AuthZ
```

---

# 225. Adapter migration V1

Mapping principal :

```text
providers/*
→ adapters/outbound/models/*

runtime.py
→ NativeRuntimeAdapter + V1 compatibility

postgres.py
→ adapters/outbound/persistence/postgres/*

blobs.py
→ adapters/outbound/storage/*

telemetry.py
→ adapters/outbound/telemetry/*
```

---

# 226. V1 ports.py migration

Le fichier générique :

```text
ports.py
```

doit être progressivement éclaté en ports spécifiques.

---

# 227. V1 RunStore migration

```text
RunStore
→ RunRepository + EffectRepository + Checkpoint persistence
```

selon V2 normalized model.

---

# 228. V1 SessionStore migration

```text
SessionStore
→ SessionRepository
```

et création séparée de :

```text
ConversationRepository
MessageRepository
```

---

# 229. V1 ApprovalStore migration

```text
ApprovalStore
→ ApprovalRepository
```

avec lifecycle V2.

---

# 230. V1 BlobStore

Peut probablement être réutilisé avec faible adaptation.

---

# 231. V1 LeaseStore

Peut devenir `LeaseRepository` ou garder `LeaseStore` selon ADR.

La sémantique est déjà proche de la cible.

---

# 232. Naming decision — Store vs Repository

Recommandation finale :

```text
Repository
for domain aggregates

Store
for technical append/blob/inbox/outbox
```

---

# 233. Port ownership matrix

| Port | Application Area |
|---|---|
| RunRepository | Execution |
| EffectRepository | Effects |
| ApprovalRepository | Governance |
| LeaseRepository | Coordination |
| ConversationRepository | Conversations |
| AgentRuntimeAdapter | Runtime Integration |
| Connector | Effects / Integrations |
| BlobStore | Artifacts |
| AuditStore | Audit |
| AuthorizationPort | Governance |
| UnitOfWork | Application shared |

---

# 234. Adapter ownership matrix

| Adapter | Implements |
|---|---|
| PostgresRunRepository | RunRepository |
| PostgresEffectRepository | EffectRepository |
| NativeRuntimeAdapter | AgentRuntimeAdapter |
| CodexRuntimeAdapter | AgentRuntimeAdapter |
| GitHubConnector | Connector + ReconciliationPort |
| S3BlobStore | BlobStore |
| OIDCIdentityAdapter | IdentityProviderPort |
| OpenTelemetryAdapter | TelemetryPort |

---

# 235. Security boundary

Chaque outbound adapter est une potentielle trust boundary.

Donc adapter review inclut :

```text
input validation
output validation
credential scope
network policy
data classification
error leakage
```

---

# 236. Provider payload validation

Toute réponse provider est non fiable jusqu’à validation.

---

# 237. Runtime output validation

Même règle.

Un runtime peut produire :

```text
malformed event
unexpected tool request
untrusted text
```

---

# 238. Connector output validation

Schémas canoniques obligatoires.

---

# 239. Adapter observability contract

Minimum :

```text
operation
duration
success/failure
provider/adapter name
correlation
```

---

# 240. Payload minimization

Ne jamais inclure par défaut dans telemetry :

```text
prompts
tool args
secrets
raw messages
full provider payloads
```

---

# 241. Adapter audit contract

Audit seulement les changements significatifs.

Exemple :

```text
connector write
manual resolution
force takeover
runtime ownership change
```

---

# 242. Adapter configuration validation

Validation au startup autant que possible.

---

# 243. Misconfigured adapter

Doit apparaître :

```text
unavailable/misconfigured
```

et non échouer seulement au premier Run critique.

---

# 244. Dynamic reload

Option future.

Si supporté :

```text
safe
audited
versioned
```

---

# 245. Adapter shutdown

Shutdown borné.

Ne pas retenir indéfiniment le process.

---

# 246. Adapter thread safety

Doit être documentée.

---

# 247. Adapter async safety

Doit être documentée.

---

# 248. Fork safety

Clients/pools externes ne sont pas supposés fork-safe.

---

# 249. Contract compatibility CI

Chaque release :

```text
run adapter contracts
repository contracts
connector contracts
public API contracts
```

---

# 250. Adapter certification evidence

Pour adapter officiel :

```text
contract test report
integration report
failure test report
known limitations
```

---

# 251. Minimal V2 Adapter Set

Pour `2.0.0a2` :

```text
NativeRuntimeAdapter
Memory repositories
FakeConnector
FilesystemBlobStore
```

---

# 252. Alpha Persistence Set

Pour `2.0.0a4` :

```text
Postgres repositories
SQLite local adapters
```

---

# 253. Beta Runtime Set

Pour `2.0.0b2` :

```text
Native
one general external runtime
one coding runtime
```

---

# 254. Beta Connector Set

Minimum :

```text
GitHub
Generic HTTP
```

avec reconciliation réelle.

---

# 255. Port & Adapter invariants

```text
PA-INV-01
Core never imports concrete adapter.

PA-INV-02
Adapter never grants business authority.

PA-INV-03
Adapter cannot redefine domain state semantics.

PA-INV-04
Runtime-specific types do not cross ACL.

PA-INV-05
Provider-specific payloads do not cross Connector ACL.

PA-INV-06
UNKNOWN remains explicit across boundaries.

PA-INV-07
Capabilities must be truthful.

PA-INV-08
No silent adapter fallback.

PA-INV-09
Retries respect idempotency semantics.

PA-INV-10
Safety-critical ports have contract tests.
```

---

# 256. Anti-pattern summary

À éviter :

```text
domain imports boto3
application imports psycopg
HTTP route mutates repository directly
Connector decides Approval
Runtime adapter owns Run state
generic execute(dict) everywhere
silent provider fallback
raw SDK object in public API
generic repository for all aggregates
generic retry around external writes
```

---

# 257. Acceptance Criteria

Le catalogue est correctement implémenté si :

1. les ports sont définis côté application ;
2. le domaine n’importe aucun adapter ;
3. chaque adapter implémente un port explicite ;
4. AgentRuntimeAdapter est indépendant des runtimes concrets ;
5. Connector est distinct de RuntimeAdapter ;
6. ModelAdapter est distinct de RuntimeAdapter ;
7. persistence adapters n’exposent aucun ORM object ;
8. provider SDK objects restent dans ACL ;
9. les capabilities sont explicites ;
10. les retries ne masquent jamais l’ambiguïté ;
11. les adapters safety-critical ont des contract tests ;
12. le bootstrap est le seul composition root concret ;
13. les erreurs provider sont normalisées ;
14. la safe degradation est documentée ;
15. les secrets restent externalisés ;
16. les adapters peuvent être remplacés sans modifier les invariants métier.

---

# 258. Definition of Done

Le modèle Ports & Adapters est mature lorsque :

1. tous les ports P0 sont typés ;
2. les packages inbound/outbound sont stabilisés ;
3. le NativeRuntimeAdapter passe son contract suite ;
4. Memory et PostgreSQL passent les mêmes repository contracts ;
5. un connector réel passe le ConnectorContract ;
6. BlobStore possède plusieurs implémentations interchangeables ;
7. AuthorizationPort est indépendant de l’IAM choisi ;
8. OpenTelemetry reste un adapter ;
9. import-linter protège la direction des dépendances ;
10. le bootstrap assemble explicitement les adapters ;
11. chaque adapter officiel documente ses capabilities ;
12. la compatibilité de version est testée ;
13. aucune mutation critique ne contourne les ports applicatifs ;
14. les profiles Local/Distributed/HighAssurance fonctionnent ;
15. les failure semantics sont qualifiées.

---

# 259. Résumé

L’architecture PyAgentsKit V2 repose sur une règle simple :

```text
DOMAIN
defines meaning

APPLICATION
defines orchestration

PORTS
define needs and capabilities

ADAPTERS
implement technologies

BOOTSTRAP
connects everything
```

Les séparations critiques sont :

```text
RuntimeAdapter != Connector
RuntimeAdapter != ModelAdapter
Repository != Connector
Repository != Store
AuthorizationPort != PolicyEvaluator
AuditStore != TelemetryPort
```

Le principe fondamental est :

> **Un bon adapter peut être remplacé ; un bon port peut être testé ; un bon domaine n’a pas besoin de savoir quelle technologie se trouve derrière.**

Le document suivant naturel est :

```text
../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md
```
