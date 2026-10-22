# PyAgentsKit — Repositories & Unit of Work

**Document :** `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Persistence Architecture — Repositories, Stores & Unit of Work  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`

---

# 1. Objet

Ce document définit la stratégie de persistance de PyAgentsKit V2 autour de deux patterns principaux :

```text
Repository
+
Unit of Work
```

Il précise :

- la différence Repository / Store ;
- les repositories par aggregate ;
- le Unit of Work ;
- les transactions ;
- les règles de concurrence ;
- l’optimistic locking ;
- les idempotency constraints ;
- le mapping Domain ↔ Persistence ;
- les boundaries PostgreSQL ;
- l’Outbox / Inbox ;
- la gestion des Effects ;
- les règles de recovery ;
- la compatibilité Memory / SQLite / PostgreSQL.

Le principe directeur est :

> **La persistance doit préserver les invariants du domaine sans faire du modèle de base de données le modèle métier.**

---

# 2. Repository vs Store

## Repository

Un Repository représente une collection d’aggregates métier.

Exemples :

```text
RunRepository
EffectRepository
ApprovalRepository
LeaseRepository
ConversationRepository
```

Il travaille avec :

```text
domain entities
value objects
aggregate roots
```

## Store

Un Store représente une infrastructure de stockage technique.

Exemples :

```text
BlobStore
AuditStore
OutboxStore
InboxStore
```

Il peut manipuler :

```text
records
bytes
append-only entries
messages
```

---

# 3. Règle de nommage

Convention recommandée :

```text
Repository
= persistence of aggregate roots

Store
= technical durable storage
```

---

# 4. Anti-pattern — Generic Repository

Éviter :

```python
class Repository(Generic[T]):
    async def get(...)
    async def save(...)
```

comme unique abstraction universelle.

Pourquoi ?

Parce que :

```text
Run
Effect
Approval
Lease
Conversation
```

ont des besoins différents.

---

# 5. Repositories P0

```text
REP-01 RunRepository
REP-02 SessionRepository
REP-03 ConversationRepository
REP-04 MessageRepository
REP-05 MemoryRepository
REP-06 EffectRepository
REP-07 ReconciliationRepository
REP-08 ApprovalRepository
REP-09 LeaseRepository
REP-10 WorkerRepository
REP-11 ArtifactRepository
```

---

# 6. Technical Stores P0

```text
STORE-01 BlobStore
STORE-02 AuditStore
STORE-03 OutboxStore
STORE-04 InboxStore
```

---

# 7. Unit of Work P0

```text
UOW-01 UnitOfWork
```

---

# 8. Repository ownership

Chaque repository appartient au Bounded Context de son aggregate.

| Repository | Context |
|---|---|
| RunRepository | Execution |
| SessionRepository | Conversations |
| ConversationRepository | Conversations |
| MessageRepository | Conversations |
| MemoryRepository | Conversations |
| EffectRepository | Effects |
| ReconciliationRepository | Effects |
| ApprovalRepository | Governance |
| LeaseRepository | Coordination |
| WorkerRepository | Coordination |
| ArtifactRepository | Artifacts |

---

# 9. Rule REP-001 — Repositories return domain objects

Mauvais :

```python
async def get(...) -> RunRow
```

Bon :

```python
async def get(...) -> Run
```

---

# 10. Rule REP-002 — ORM models stay in adapters

ORM / persistence models vivent dans :

```text
adapters/outbound/persistence/
```

et jamais dans :

```text
domain/
application/
api/
```

---

# 11. Rule REP-003 — Domain does not know persistence schema

Le Domain ne connaît pas :

```text
table
column
JSONB
index
foreign key
SQL
```

---

# 12. Rule REP-004 — Repository contract is technology-neutral

Le même contrat doit pouvoir être implémenté par :

```text
Memory
SQLite
PostgreSQL
```

---

# 13. RunRepository

Contrat conceptuel :

```python
class RunRepository(Protocol):
    async def get(self, run_id: RunId) -> Run: ...
    async def add(self, run: Run) -> None: ...
    async def save(
        self,
        run: Run,
        *,
        expected_version: Version,
    ) -> None: ...
```

---

# 14. RunRepository — queries candidates

```text
find_recoverable
list_by_session
list_by_state
exists
```

Ces opérations doivent rester :

```text
domain/application oriented
```

et non devenir un moteur de reporting.

---

# 15. RunRepository — optimistic concurrency

Chaque Run possède :

```text
version
```

Lors du save :

```text
UPDATE ...
WHERE id = ?
AND version = expected_version
```

si aucune ligne modifiée :

```text
ConcurrencyConflict
```

---

# 16. RunRepository — no hidden transition

Un repository ne doit jamais :

```text
RUNNING → SUCCEEDED
```

de sa propre initiative.

---

# 17. SessionRepository

Contrat :

```text
get
add
save
```

Session V2 reste distincte de Conversation.

---

# 18. ConversationRepository

Responsabilités :

```text
get
add
save
list_for_session
```

---

# 19. MessageRepository

Le Message peut suivre un modèle append-oriented.

Contrat :

```text
append
get
list_for_conversation
find_by_deduplication_key
```

---

# 20. Message ordering

Si ordre requis :

```text
conversation sequence
```

doit être explicite.

Possibilités :

```text
sequence_number
created_at + id
```

mais préférence :

```text
explicit monotonic conversation sequence
```

---

# 21. Message deduplication

Contrainte potentielle :

```text
UNIQUE(tenant_id, conversation_id, deduplication_key)
```

si clé présente.

---

# 22. MemoryRepository

Peut fournir :

```text
get
put
delete
list_by_scope
expire
```

selon modèle mémoire final.

---

# 23. EffectRepository

Le port le plus safety-critical côté persistence.

Contrat conceptuel :

```python
class EffectRepository(Protocol):
    async def get(self, effect_id: EffectId) -> Effect: ...
    async def reserve(self, effect: Effect) -> EffectReservationResult: ...
    async def save(
        self,
        effect: Effect,
        *,
        expected_version: Version,
    ) -> None: ...
    async def find_by_idempotency_key(
        self,
        scope: IdempotencyScope,
        key: IdempotencyKey,
    ) -> Effect | None: ...
```

---

# 24. Effect durable intent

Avant tout Protected Effect :

```text
Effect intent
must be durably persisted
```

---

# 25. Effect idempotency constraint

Référence PostgreSQL :

```text
UNIQUE(
    tenant_id,
    idempotency_scope,
    idempotency_key
)
```

---

# 26. Effect fingerprint conflict

Même clé + fingerprint différent :

```text
IdempotencyConflict
```

---

# 27. Effect status persistence

États :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

# 28. Effect success immutability

Une fois :

```text
SUCCEEDED
```

le repository doit refuser une transition de replay/restart invalide.

Le domaine porte la règle.

Le DB peut ajouter une protection défensive.

---

# 29. Effect partial index

Index candidat :

```text
WHERE status IN (
    'STARTED',
    'UNKNOWN',
    'RECONCILIATION_REQUIRED'
)
```

pour recovery scanner.

---

# 30. ReconciliationRepository

Contrat :

```text
add
get
save
list_open
list_for_effect
```

---

# 31. ReconciliationCase versioning

Optimistic concurrency recommandé.

---

# 32. ApprovalRepository

Contrat :

```text
get
add
save
list_pending
list_for_run
list_for_effect
```

---

# 33. Approval terminality

Le repository ne doit jamais permettre d’écraser :

```text
APPROVED
REJECTED
EXPIRED
CANCELLED
```

par un autre terminal status.

---

# 34. Approval race

Deux décisions concurrentes :

```text
one CAS wins
other gets conflict
```

---

# 35. LeaseRepository

Leasing demande des primitives plus spécifiques qu’un Repository générique.

Contrat :

```text
acquire
renew
release
get_current
validate
takeover
```

---

# 36. Lease Resource

Structure recommandée :

```text
lease_resources
```

avec :

```text
resource_id
tenant_id
current_fencing_token
```

---

# 37. Lease history

Table séparée :

```text
leases
```

pour :

```text
lease_id
owner_id
resource_id
fencing_token
acquired_at
expires_at
released_at
status
```

---

# 38. Fencing monotonicity

Règle :

```text
new token > previous token
```

protégée par transaction/lock.

---

# 39. DB time authority

Pour expiration distribuée :

```text
database time
```

est préférée à l’horloge locale du worker.

---

# 40. Lease acquire transaction

Pattern :

```text
BEGIN
lock lease_resource row
check current lease
increment fencing token if acquire/takeover allowed
insert lease
COMMIT
```

---

# 41. Lease renew transaction

Doit vérifier :

```text
lease id
owner
current token
not expired according DB time
```

---

# 42. Lease release

Best effort explicite.

Safety ne dépend pas de sa réussite.

---

# 43. WorkerRepository

Responsabilités :

```text
register
heartbeat
mark_draining
mark_stopped
get
list
```

---

# 44. Worker heartbeat

Heartbeat ne crée pas l’ownership.

Principe :

```text
heartbeat != lease
```

---

# 45. ArtifactRepository

Persiste :

```text
Artifact metadata
checksum
provenance
content type
blob reference
status
```

---

# 46. Artifact bytes

Vivent dans :

```text
BlobStore
```

pas dans l’aggregate sauf petit payload exceptionnel.

---

# 47. BlobStore

Contrat :

```text
put
open/read
exists
delete
metadata
```

---

# 48. BlobStore integrity

Checksum applicatif recommandé.

---

# 49. AuditStore

Append-only.

Contrat :

```text
append
query
```

Pas d’update normal.

---

# 50. Audit deletion

Si exigence légale :

```text
specialized retention/privacy process
```

et non méthode générique de repository.

---

# 51. OutboxStore

Contrat :

```text
append
claim_batch
mark_published
mark_failed
release_claim
```

---

# 52. InboxStore

Contrat :

```text
reserve
mark_processed
mark_failed
get
```

---

# 53. Inbox deduplication

Contrainte candidate :

```text
UNIQUE(
    source,
    external_event_id
)
```

avec tenant scope si nécessaire.

---

# 54. Unit of Work — rôle

Le Unit of Work définit :

```text
a local consistency boundary
```

entre plusieurs repository operations.

---

# 55. Unit of Work contract

Exemple :

```python
class UnitOfWork(Protocol):
    runs: RunRepository
    effects: EffectRepository
    approvals: ApprovalRepository
    outbox: OutboxStore

    async def __aenter__(self) -> "UnitOfWork": ...
    async def __aexit__(self, exc_type, exc, tb) -> None: ...
    async def commit(self) -> None: ...
    async def rollback(self) -> None: ...
```

---

# 56. Unit of Work scope

Il peut exposer seulement les repositories utiles au use case ou un registry interne.

Éviter un mega-UoW trop couplé.

---

# 57. UoW lifetime

Recommandation :

```text
one application transaction
=
one UnitOfWork
```

---

# 58. UoW and remote calls

Interdit :

```text
open UoW
↓
call GitHub
↓
call LLM
↓
wait 30s
↓
commit
```

---

# 59. Effect execution transaction pattern

Pattern cible :

```text
TX1
load Effect
validate
mark STARTED
append Outbox/Audit intent if needed
commit

REMOTE CALL

TX2
reload Effect
persist SUCCEEDED / FAILED / UNKNOWN
append events
commit
```

---

# 60. Why two transactions

Parce que :

```text
PostgreSQL transaction
!=
distributed transaction
```

---

# 61. Crash window W1

Avant durable intent.

Résultat :

```text
no Effect exists
```

---

# 62. Crash window W2

Après durable intent, avant send.

Recovery peut décider selon preuve de non-send.

---

# 63. Crash window W3

Après send, avant response.

Résultat :

```text
UNKNOWN
```

si absence de certitude.

---

# 64. Crash window W4

Après response, avant durable outcome.

Résultat :

```text
reconciliation required
```

si la vérité externe peut avoir divergé de la DB.

---

# 65. Crash window W5

Après durable success, avant Run progress.

Recovery :

```text
continue
without replay
```

---

# 66. UnitOfWork and Domain Events

Pattern :

```text
aggregate mutates
↓
collect DomainEvents
↓
repository save
↓
Outbox append
↓
commit
```

---

# 67. DomainEvent collection

Option :

```text
aggregate.pending_events
```

ou event collector applicatif.

---

# 68. Outbox atomicity

Objectif :

```text
domain state
+
integration event
```

commités ensemble.

---

# 69. Outbox is not Domain authority

Un event absent dans broker ne signifie pas que le domaine n’a pas changé si DB commit existe.

---

# 70. Inbox transaction

Pattern :

```text
reserve Inbox
↓
apply command
↓
mark processed
↓
commit
```

si tout est local au même DB.

---

# 71. External broker acknowledgment

Ack après commit local.

---

# 72. Queue redelivery

Inbox rend l’opération idempotente.

---

# 73. Repository mapping

Chaque adapter persistence possède un mapping explicite :

```text
Persistence Model
↕
Domain Aggregate
```

---

# 74. Mapping rule

Interdit :

```text
ORM entity == Domain entity
```

par défaut.

---

# 75. Domain → row mapping

Exemple :

```text
Run
→ runs row
```

peut inclure :

```text
typed columns
JSONB metadata
```

mais le mapping est explicite.

---

# 76. Row → Domain mapping

Doit :

```text
validate stored representation
reconstruct value objects
reject impossible corrupt states
```

---

# 77. Corrupt persistence

Ne pas silently normalize.

Exemple :

```text
invalid RunState
→ PersistenceCorruptionError
```

---

# 78. Persistence DTOs

Peuvent exister dans adapter.

Exemple :

```text
RunRecord
EffectRecord
```

mais non exportés vers Domain.

---

# 79. JSONB policy

JSONB utile pour :

```text
metadata
provider-neutral extension data
non-critical flexible payloads
```

---

# 80. JSONB anti-pattern

Ne pas cacher dedans :

```text
critical status
tenant_id
fencing_token
idempotency_key
approval decision
```

---

# 81. Typed columns

Les invariants critiques doivent utiliser colonnes typées/indexables.

---

# 82. Foreign Keys

Utiliser pour relations critiques.

Exemples :

```text
effects.run_id → runs.id
approvals.effect_id → effects.id
runtime_invocations.run_id → runs.id
```

selon design final.

---

# 83. Cross-context FK nuance

Une FK physique est possible même entre Bounded Contexts dans même DB.

Mais elle ne crée pas une dépendance objet dans Domain.

---

# 84. Referential integrity

FK protège :

```text
physical consistency
```

Domain/Application protègent :

```text
semantic consistency
```

---

# 85. Unique constraints

Utiliser pour :

```text
idempotency
deduplication
one active lease
external event dedup
```

---

# 86. Check constraints

Utiles pour :

```text
basic allowed values
non-negative version
timestamp ordering
```

---

# 87. DB ENUM policy

Préférence initiale :

```text
VARCHAR + CHECK
```

pour faciliter migrations.

---

# 88. Version column

Chaque aggregate mutable important :

```text
version BIGINT
```

---

# 89. Optimistic concurrency pattern

```sql
UPDATE table
SET ..., version = version + 1
WHERE id = :id
  AND version = :expected_version
```

---

# 90. Zero-row update

Mappe à :

```text
ConcurrencyConflict
```

---

# 91. Concurrency retry

Application peut :

```text
reload
re-evaluate
retry local transaction
```

seulement si aucun remote Effect n’est en jeu.

---

# 92. Deadlock handling

Persistence adapter peut retry deadlock transaction si :

```text
transaction contains no external Effect
```

---

# 93. Serialization failure

Ne doit pas être retried aveuglément.

---

# 94. DB failover

Après failover :

```text
reconnect
reload authoritative state
```

---

# 95. Read replicas

Autorisé pour :

```text
reporting
non-critical queries
```

Interdit pour :

```text
Lease authority
Effect current status before execution
Approval applicability
```

---

# 96. Primary authority

Safety-critical reads utilisent :

```text
primary
```

---

# 97. Cache policy

Cache non-authoritatif uniquement.

---

# 98. Cache forbidden data

Ne pas décider depuis cache :

```text
current lease
effect status
approval terminality
fencing token
```

---

# 99. Isolation level

Default candidat :

```text
READ COMMITTED
```

avec row locks ciblés.

---

# 100. Serializable

À utiliser seulement si un invariant l’exige.

---

# 101. Lock strategy

Préférer :

```text
short explicit row locks
```

aux transactions longues.

---

# 102. SKIP LOCKED

Utilisable pour :

```text
Outbox claim
work scanning
```

mais pas pour masquer un conflit d’autorité.

---

# 103. FOR UPDATE

Candidat pour :

```text
lease_resource
approval decision
critical counter
```

---

# 104. Advisory locks

À éviter comme seule source de vérité si une contrainte relationnelle peut mieux exprimer l’invariant.

---

# 105. DB constraints as defense-in-depth

Le DB aide à rendre certains états impossibles.

Mais :

```text
DB constraint
!=
Domain transition logic
```

---

# 106. Repository error taxonomy

```text
RepositoryError
NotFound
ConcurrencyConflict
ConstraintConflict
PersistenceUnavailable
PersistenceCorruption
```

---

# 107. Store error taxonomy

```text
StoreUnavailable
BlobNotFound
IntegrityMismatch
OutboxClaimConflict
InboxDuplicate
```

---

# 108. Error translation

Exemple :

```text
psycopg.UniqueViolation
→ IdempotencyConflict or ConstraintConflict
```

selon contrainte.

---

# 109. No raw DB errors

Ne pas propager au Domain/API.

---

# 110. UnitOfWork errors

```text
CommitFailed
RollbackFailed
TransactionUnavailable
```

---

# 111. Uncertain COMMIT

Cas critique.

Si client perd connexion pendant commit :

```text
commit outcome may be unknown
```

---

# 112. Uncertain commit handling

Pattern :

```text
reconnect
↓
read by durable identity/idempotency key
↓
determine committed state
```

---

# 113. Never assume rollback

Connection loss pendant commit ne prouve pas rollback.

---

# 114. Transaction idempotency

Les inserts critiques doivent permettre de déterminer si commit a eu lieu.

---

# 115. Run creation idempotency

Possible via :

```text
request_id / idempotency_key
```

si API l’expose.

---

# 116. Effect reserve idempotency

Obligatoire.

---

# 117. Approval decision idempotency

Même décision répétée peut être :

```text
idempotent success
```

selon contrat.

Décision contraire :

```text
conflict
```

---

# 118. Lease acquire idempotency

Même owner/lease request peut avoir sémantique spécifique.

À formaliser.

---

# 119. PostgreSQL schema ownership

Adapter PostgreSQL contient :

```text
schema
migrations
repositories
unit_of_work
mapping
queries
```

---

# 120. Suggested topology

```text
adapters/outbound/persistence/postgres/
├── connection.py
├── unit_of_work.py
├── schema.py
├── mapping/
├── repositories/
├── stores/
├── queries/
└── migrations/
```

---

# 121. Repository implementation split

```text
repositories/
├── run_repository.py
├── effect_repository.py
├── approval_repository.py
├── lease_repository.py
├── conversation_repository.py
└── artifact_repository.py
```

---

# 122. Store implementation split

```text
stores/
├── audit_store.py
├── outbox_store.py
└── inbox_store.py
```

---

# 123. Query implementation

Read-only optimized SQL peut vivre :

```text
queries/
```

séparé des repositories aggregates.

---

# 124. Query repository anti-pattern

Ne pas forcer toutes les queries complexes dans `RunRepository`.

---

# 125. Read Model Repository

Peut exister :

```text
RunViewQueryService
TimelineQueryService
```

sans être Repository métier.

---

# 126. Memory adapters

But :

```text
unit tests
examples
```

---

# 127. Memory semantics

Doivent reproduire les contrats :

```text
version conflict
idempotency
terminal immutability
```

autant que possible.

---

# 128. Memory limitation

Ne pas prétendre simuler :

```text
real multi-process race
real DB time
real transaction isolation
```

---

# 129. SQLite adapters

But :

```text
local durable development
single-node
```

---

# 130. SQLite limitation

Distributed lease qualification :

```text
not production authority
```

---

# 131. PostgreSQL adapters

Backend production de référence.

---

# 132. Repository contract tests

Chaque implémentation passe :

```text
RunRepositoryContract
EffectRepositoryContract
ApprovalRepositoryContract
LeaseRepositoryContract
...
```

---

# 133. Contract test principle

Même suite de tests sur :

```text
Memory
SQLite
PostgreSQL
```

là où sémantique comparable.

---

# 134. PostgreSQL-specific tests

En plus :

```text
multi-process
deadlock
row lock
failover/restart
SKIP LOCKED
backup/restore
```

---

# 135. UnitOfWork contract tests

Tester :

```text
commit
rollback
exception rollback
visibility
atomic outbox
```

---

# 136. Outbox contract tests

Tester :

```text
claim
concurrent claim
publish mark
retry
crash after claim
```

---

# 137. Inbox contract tests

Tester :

```text
duplicate delivery
process success
process failure
redelivery
```

---

# 138. Lease contract tests

Tester :

```text
acquire
renew
expiry
takeover
monotonic fencing
stale token rejection
```

---

# 139. Effect contract tests

Tester :

```text
reserve
same key same fingerprint
same key different fingerprint
SUCCEEDED immutability
UNKNOWN preservation
```

---

# 140. Approval contract tests

Tester :

```text
terminal transition
concurrent decision
expiry
idempotent same decision
conflict opposite decision
```

---

# 141. Migration compatibility

V1 stores restent séparés.

Ne pas modifier directement `PostgresRunStore` V1 pour le faire devenir V2.

---

# 142. V2 persistence coexistence

Pendant migration :

```text
V1 persistence
+
V2 persistence
```

peuvent coexister.

---

# 143. V1 compatibility bridge

Un bridge peut lire V1 et produire V2 migration DTOs.

---

# 144. No runtime dependency on migration bridge

Après cutover, runtime normal V2 ne dépend pas des legacy mappers.

---

# 145. Repository versioning

Les repository interfaces internes peuvent évoluer avant V2 stable.

Après stable :

```text
compatibility policy
```

à définir.

---

# 146. Schema versioning

Chaque DB déploiement doit connaître :

```text
schema version
migration version
```

---

# 147. Readiness and schema compatibility

Worker V2 ne devient ready que si :

```text
DB schema compatible
```

---

# 148. Expand-contract migrations

Séquence :

```text
expand
backfill
switch
contract
```

---

# 149. Migration anti-pattern

Ne pas :

```text
rename/drop critical column
and deploy code simultaneously
```

sans compat window.

---

# 150. Backfill

Doit être :

```text
restartable
chunked
observable
```

---

# 151. Large table migrations

Préférer techniques online quand possible.

---

# 152. Backup / Restore

Persistence architecture doit supporter :

```text
backup
PITR
restore verification
```

---

# 153. Restore != safe resume

Après restore :

```text
Effects
Leases
Fencing
Approvals
```

doivent être revalidés.

---

# 154. Restore safety gate

Avant workers :

```text
verify fencing generation
reconcile uncertain Effects
verify schema
```

---

# 155. PITR ambiguity

PITR peut perdre un commit DB alors que l’Effect externe a réussi.

Donc :

```text
mandatory reconciliation
```

---

# 156. Audit retention

Audit peut avoir :

```text
longer retention
```

que Run operational state.

---

# 157. Data retention by context

Définir séparément :

```text
Run
Messages
Memory
Effects
Approvals
Audit
Artifacts
```

---

# 158. Hard delete policy

Safety-critical history :

```text
prefer archival/tombstone
```

à suppression immédiate.

---

# 159. Tenant isolation

Toutes les tables shared-tenant doivent porter :

```text
tenant_id
```

si applicable.

---

# 160. Tenant-aware uniqueness

Les contraintes doivent inclure tenant scope.

---

# 161. RLS

PostgreSQL Row-Level Security peut être utilisé en defense-in-depth.

---

# 162. RLS limitation

RLS ne remplace pas :

```text
application tenant checks
```

---

# 163. Tenant in repository API

Tenant context explicite ou attaché au SecurityContext.

---

# 164. Cross-tenant reference

Bloqué au Domain/Application et idéalement par DB constraints là où possible.

---

# 165. Encryption

Data at rest gérée par infra/provider.

Field-level encryption uniquement si besoin explicite.

---

# 166. Secrets

Ne jamais stocker les valeurs résolues des secrets dans repositories métier.

---

# 167. SecretReference persistence

Possible :

```text
reference only
```

si nécessaire.

---

# 168. Sensitive payload minimization

Éviter stocker :

```text
raw prompts
full provider payloads
credentials
```

sans besoin explicite.

---

# 169. Persistence observability

Metrics :

```text
repository_latency
repository_errors
transaction_duration
pool_usage
deadlocks
outbox_lag
inbox_duplicates
```

---

# 170. Cardinality

Ne pas utiliser :

```text
run_id
effect_id
```

comme metric label à haute cardinalité.

---

# 171. Tracing

Spans :

```text
repo.run.get
repo.effect.reserve
uow.commit
lease.acquire
outbox.claim
```

---

# 172. SQL logging

Pas de payload sensible.

---

# 173. Slow query monitoring

Important pour :

```text
recovery scanners
outbox
timeline queries
```

---

# 174. Index strategy

Query-driven.

Ne pas indexer tout arbitrairement.

---

# 175. Index candidates

```text
runs(state, updated_at)
effects(status, updated_at)
approvals(status, expires_at)
leases(resource_id, status)
outbox(status, available_at)
inbox(source, external_event_id)
messages(conversation_id, sequence)
```

---

# 176. Partial indexes

Très utiles pour :

```text
active leases
pending approvals
unresolved effects
unpublished outbox
```

---

# 177. Partitioning

À envisager plus tard pour :

```text
audit_events
messages
outbox
```

si volume justifie.

---

# 178. Partitioning anti-pattern

Ne pas introduire avant preuve de besoin.

---

# 179. Vacuum/bloat

Surveiller tables à forts updates :

```text
leases
workers
outbox
```

---

# 180. Append-heavy tables

```text
audit_events
messages
runtime_invocations
```

ont profils différents.

---

# 181. Repository transaction boundaries

RunRepository save seul :

```text
one aggregate transaction
```

Cross aggregate orchestration :

```text
Application + UoW
```

---

# 182. Aggregate consistency

Un aggregate doit être sauvegardé atomiquement.

---

# 183. Cross-aggregate consistency

Ne pas exiger atomicité globale si Outbox/Eventual consistency suffit.

---

# 184. Approval + Outbox

Exemple :

```text
Approval APPROVED
+
ApprovalApproved event
```

dans même transaction.

---

# 185. Effect + Outbox

Même principe.

---

# 186. Run + RuntimeInvocation

Peut nécessiter même UoW si cohérence locale.

---

# 187. Lease + Run

Éviter transaction couplée si appartenant à contexts différents.

Ownership validé avant action.

---

# 188. UnitOfWork composition

Option 1 :

```text
single database UoW
```

si tous repos partagent PostgreSQL.

---

# 189. UnitOfWork future portability

Le contrat ne doit pas supposer PostgreSQL.

---

# 190. Multiple databases

Si futur split :

```text
one UoW per transactional resource
```

Pas de pseudo transaction distribuée.

---

# 191. Multi-resource consistency

Utiliser :

```text
Outbox
reconciliation
compensation
```

selon besoin.

---

# 192. Repository method design

Préférer méthodes métier utiles.

Exemple :

```text
find_recoverable
find_by_idempotency_key
```

plutôt qu’un query builder universel exposé.

---

# 193. Query builder leakage

Interdit dans port :

```text
filter(**kwargs)
order_by(...)
```

si cela reflète trop le stockage.

---

# 194. Pagination

Les listes importantes utilisent :

```text
cursor
```

pas offset si gros volume.

---

# 195. Repository cursor

Opaque à l’API publique.

---

# 196. Query side cursor

Peut être spécifique aux Read Models.

---

# 197. Repository batch methods

Acceptables si use case réel.

Exemple :

```text
claim_recoverable_runs(limit)
```

---

# 198. Claim semantics

Si claim implique ownership :

```text
must not replace Lease
```

---

# 199. Work queue table

Possible comme optimisation.

Mais :

```text
queue claim != lease ownership
```

---

# 200. Eventual consistency

Read models peuvent lagger.

---

# 201. Safety reads

Toujours authoritative repository.

---

# 202. Repository caching decorator

Possible pour read-only non-critical.

---

# 203. Write-through cache

À éviter initialement.

---

# 204. Testing fakes

Fakes doivent reproduire :

```text
version conflicts
idempotency constraints
terminal state protections
```

---

# 205. Testing anti-pattern

Un fake trop permissif peut masquer bugs de production.

---

# 206. Database fixture strategy

Tests PostgreSQL :

```text
ephemeral DB
transaction cleanup
schema migration real
```

---

# 207. Migration tests

Toujours appliquer les vraies migrations.

---

# 208. Schema drift detection

CI peut comparer :

```text
migration head
expected schema
```

---

# 209. Database compatibility matrix

À publier :

```text
PostgreSQL versions supported
```

---

# 210. SQLite compatibility

Documenter les garanties non équivalentes.

---

# 211. Repository Qualification Levels

```text
L0 fake only
L1 contract compliant
L2 integration tested
L3 failure tested
L4 production qualified
```

---

# 212. PostgreSQL L4

Nécessite :

```text
real PG
multi-process
kill/restart
load
backup/restore
failover-like scenario
```

---

# 213. Store Qualification Levels

Même approche.

---

# 214. Repository invariants

```text
REP-INV-01
Repositories return domain aggregates, not persistence models.

REP-INV-02
Optimistic version conflicts are explicit.

REP-INV-03
Effect idempotency is physically protected.

REP-INV-04
Approval terminal decisions cannot be overwritten.

REP-INV-05
Lease fencing tokens are monotonic.

REP-INV-06
Audit is append-oriented.

REP-INV-07
Inbox deduplicates external delivery.

REP-INV-08
Outbox persists atomically with local state where required.

REP-INV-09
No external Effect is executed inside a long DB transaction.

REP-INV-10
Safety-critical reads use authoritative state.
```

---

# 215. Unit of Work invariants

```text
UOW-INV-01
Commit is explicit.

UOW-INV-02
Exception causes rollback unless already committed.

UOW-INV-03
UoW does not span remote calls.

UOW-INV-04
UoW does not expose DB implementation details.

UOW-INV-05
Outbox writes can participate in same local transaction.
```

---

# 216. Anti-pattern — ORM everywhere

Mauvais :

```text
Domain entity
=
SQLAlchemy model
=
API DTO
```

---

# 217. Anti-pattern — transaction per repository method only

Certain use cases require plusieurs writes atomiques.

D’où UoW.

---

# 218. Anti-pattern — UoW around everything

Ne pas créer une transaction DB englobant tout un Run.

---

# 219. Anti-pattern — remote call in transaction

Déjà interdit.

---

# 220. Anti-pattern — repository owns business decision

Exemple :

```text
EffectRepository decides retry allowed
```

interdit.

---

# 221. Anti-pattern — generic JSON persistence

Ne pas revenir au modèle :

```text
one giant payload_json
```

pour tout le domaine V2.

---

# 222. Anti-pattern — dual source of truth

Ne pas stocker le même status critique dans deux tables indépendantes sans règle claire.

---

# 223. Anti-pattern — hidden soft delete semantics

Si soft delete utilisé :

```text
must be explicit
```

---

# 224. Anti-pattern — repository side effects

Repository save ne doit pas :

```text
send webhook
publish message directly
call runtime
```

---

# 225. Anti-pattern — transparent retry after uncertain commit

Après uncertain commit :

```text
re-read first
```

---

# 226. Anti-pattern — stale replica for lease

Interdit.

---

# 227. Repository package topology target

```text
application/ports/outbound/repositories/
├── run_repository.py
├── session_repository.py
├── conversation_repository.py
├── message_repository.py
├── memory_repository.py
├── effect_repository.py
├── reconciliation_repository.py
├── approval_repository.py
├── lease_repository.py
├── worker_repository.py
└── artifact_repository.py
```

---

# 228. Store topology target

```text
application/ports/outbound/storage/
├── blob_store.py
└── artifact_store.py

application/ports/outbound/messaging/
├── outbox_store.py
└── inbox_store.py

application/ports/outbound/telemetry/
└── audit_store.py
```

selon découpage final.

---

# 229. PostgreSQL topology target

```text
adapters/outbound/persistence/postgres/
├── connection.py
├── unit_of_work.py
├── repositories/
├── stores/
├── queries/
├── mapping/
└── migrations/
```

---

# 230. Memory topology target

```text
adapters/outbound/persistence/memory/
├── run_repository.py
├── effect_repository.py
├── approval_repository.py
├── lease_repository.py
└── ...
```

---

# 231. SQLite topology target

Même approche.

---

# 232. Migration from V1 RunStore

V1 `RunStore` mélange :

```text
Run
checkpoints
effects
journal
```

V2 doit séparer :

```text
RunRepository
Checkpoint persistence
EffectRepository
Audit/Journal model
```

---

# 233. Migration from V1 PostgresRunStore

Ne pas le muter directement en V2.

Préférer :

```text
PostgresRunRepositoryV2
```

ou nouveau namespace.

---

# 234. Migration from V1 postgres_state

Collections génériques deviennent repositories spécialisés.

---

# 235. Migration safety

Aucun Run V2 ne reprend avant :

```text
Run
Effect
Approval
Lease/Fencing
```

migrés et vérifiés.

---

# 236. Repository ADR candidates

```text
ADR-REP-001 Repository vs Store
ADR-REP-002 UnitOfWork
ADR-REP-003 Optimistic concurrency
ADR-REP-004 Effect idempotency constraints
ADR-REP-005 Lease resource/fencing model
ADR-REP-006 Outbox atomicity
ADR-REP-007 Inbox deduplication
ADR-REP-008 JSONB policy
ADR-REP-009 Primary vs replica
ADR-REP-010 Restore safety
```

---

# 237. Acceptance Criteria

L’architecture persistence est conforme si :

1. chaque aggregate principal possède un repository dédié ;
2. repositories retournent des Domain objects ;
3. ORM/SQL restent dans adapters ;
4. Effect idempotency est protégée par contrainte unique ;
5. optimistic concurrency est explicite ;
6. Approval terminality est protégée ;
7. Lease fencing est monotonic ;
8. DB time est utilisé pour Lease authority ;
9. UnitOfWork ne traverse pas les remote calls ;
10. Outbox est atomique avec state change pertinent ;
11. Inbox fournit deduplication ;
12. Audit est append-oriented ;
13. Safety reads utilisent primary ;
14. Memory/SQLite/PostgreSQL passent les contract tests appropriés ;
15. uncertain COMMIT est traité par re-read ;
16. restore/PITR déclenchent safety gate ;
17. mapping persistence ↔ domain est explicite ;
18. V1/V2 persistence peut coexister pendant migration.

---

# 238. Definition of Done

Le modèle Repositories & Unit of Work est mature lorsque :

1. tous les repository ports P0 sont typés ;
2. tous les stores P0 sont typés ;
3. UnitOfWork est implémenté pour Memory/SQLite/PostgreSQL selon scope ;
4. PostgreSQL V2 implémente les repositories normalisés ;
5. les contract tests tournent sur plusieurs adapters ;
6. les tests multi-processus couvrent Lease/Effect concurrence ;
7. les migrations DB sont versionnées ;
8. Outbox/Inbox sont opérationnels ;
9. les uncertain commit scenarios sont testés ;
10. les restore/PITR scenarios sont qualifiés ;
11. les read models sont séparés des repositories aggregates ;
12. les métriques persistence existent ;
13. les erreurs DB sont normalisées ;
14. les tenants sont isolés ;
15. aucun Effect critique n’est rejoué à cause d’un retry de transaction.

---

# 239. Résumé

La stratégie V2 doit converger vers :

```text
DOMAIN AGGREGATE
      │
      ▼
REPOSITORY PORT
      │
      ▼
APPLICATION + UNIT OF WORK
      │
      ▼
PERSISTENCE ADAPTER
      │
      ▼
PostgreSQL / SQLite / Memory
```

Avec en parallèle :

```text
Technical Stores
├── BlobStore
├── AuditStore
├── OutboxStore
└── InboxStore
```

Les principes essentiels sont :

```text
Repository != ORM
Repository != Generic CRUD
Store != Repository
DB constraint != Domain rule
Transaction != Distributed transaction
Queue claim != Lease
Read replica != safety authority
Restore != Safe resume
```

Le principe fondamental est :

> **La persistance de PyAgentsKit ne doit pas seulement sauver des objets ; elle doit rendre les races détectables, les duplications critiques impossibles, la reprise reconstructible et les décisions de sûreté vérifiables.**

Le document suivant naturel est :

```text
../domain/33_PYAGENTSKIT_DOMAIN_EVENTS_AND_OUTBOX_INBOX.md
```
