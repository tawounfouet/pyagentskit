# PyAgentsKit — Persistence & State Stores

**Document :** `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Spécification métier et technique — Persistence & State Stores  
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
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/PYAGENTSKIT_MODELE_CONCEPTUEL_DU_DOMAINE.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`

---

# 1. Objet du document

Ce document définit la couche de **persistance durable et de State Stores** de PyAgentsKit.

Il décrit :

- les ports de persistence ;
- les responsabilités de chaque store ;
- les frontières transactionnelles ;
- les garanties de cohérence ;
- le backend PostgreSQL de référence ;
- les alternatives locales comme SQLite ;
- la gestion des artefacts dans un BlobStore ;
- les migrations ;
- l’optimistic concurrency ;
- les verrous conditionnels ;
- l’Outbox / Inbox ;
- le multi-tenancy ;
- l’audit ;
- la reprise après incident ;
- les règles de sécurité et de rétention.

Le principe directeur est :

> **Le domaine définit la sémantique ; les stores garantissent la durabilité ; l’infrastructure ne doit jamais dicter le modèle métier.**

---

# 2. Position architecturale

```text
Domain
  │
  ▼
Ports
  │
  ▼
State Stores
  │
  ├── PostgreSQL
  ├── SQLite
  ├── Object Storage
  └── future adapters
```

Le domaine ne dépend pas directement de :

```text
SQLAlchemy
psycopg
asyncpg
SQLite
PostgreSQL
S3
Azure Blob
```

---

# 3. Objectifs

La couche persistence doit assurer :

```text
durability
consistency
recoverability
concurrency safety
auditability
backend replaceability
migration safety
operational observability
```

---

# 4. Non-objectifs

La couche persistence ne doit pas devenir :

```text
generic ORM abstraction framework
distributed database
event sourcing engine
data lake
analytics warehouse
document database abstraction for everything
```

---

# 5. Philosophie générale

Chaque store expose une responsabilité métier claire.

Exemple :

```text
RunStore
EffectStore
ApprovalStore
LeaseStore
```

plutôt que :

```text
GenericRepository[Any]
```

---

# 6. Ports principaux

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
WorkerRegistry
RuntimeStore
ArtifactStore
AuditStore
OutboxStore
InboxStore
```

---

# 7. Séparation logique

Même si tous les stores utilisent le même PostgreSQL :

```text
logical separation remains
```

Le fait qu’ils partagent la même base ne signifie pas qu’ils forment un seul repository générique.

---

# 8. RunStore

Responsabilités :

```text
create run
get run
transition run
save run state
list recoverable runs
list waiting runs
enforce optimistic concurrency
```

---

# 9. Contrat conceptuel RunStore

```python
class RunStore(Protocol):
    async def create(self, run: Run) -> None: ...
    async def get(self, run_id: RunId) -> Run | None: ...
    async def save(self, run: Run, expected_version: int) -> None: ...
    async def transition(
        self,
        run_id: RunId,
        expected_state: RunState,
        new_state: RunState,
        expected_version: int,
    ) -> Run:
        ...
```

---

# 10. SessionStore

Responsabilités :

```text
create session
load session
update durable context references
link runs
link conversations
manage session lifecycle
```

---

# 11. ConversationStore

Responsabilités :

```text
create conversation
load conversation
change status
list participants
append participant relation
```

---

# 12. MessageStore

Responsabilités :

```text
append message
load message
list conversation messages
deduplicate messages
archive/redact metadata where supported
```

Principe :

```text
append-oriented
```

---

# 13. MemoryStore

Responsabilités :

```text
put memory entry
get memory entry
list by scope
version updates
expire / archive entries
```

---

# 14. CheckpointStore

Responsabilités :

```text
append checkpoint
get latest checkpoint
get by sequence
list checkpoints
validate ordering
```

Un checkpoint validé doit être :

```text
immutable
```

---

# 15. EffectStore

Responsabilités :

```text
create/reserve effect
find by idempotency key
transition effect
attach external reference
list unresolved effects
detect idempotency conflict
```

---

# 16. ApprovalStore

Responsabilités :

```text
create approval
get approval
decide approval
expire approval
list pending approvals
```

---

# 17. LeaseStore

Responsabilités :

```text
acquire lease
renew lease
release lease
takeover lease
validate ownership
list leases
generate fencing token
```

---

# 18. WorkerRegistry

Responsabilités :

```text
register worker
heartbeat
set status
get worker
list workers
mark stopped
```

---

# 19. RuntimeStore

Responsabilités :

```text
persist runtime binding
persist runtime handle
create runtime invocation
update invocation status
attach runtime checkpoint reference
```

---

# 20. ArtifactStore

Responsabilité :

```text
persist artifact metadata
store artifact content
retrieve content
verify checksum
delete/archive according to retention
```

---

# 21. AuditStore

Responsabilité :

```text
append audit event
query audit timeline
filter by object
filter by actor
filter by run
```

Principe :

```text
append-oriented
```

---

# 22. OutboxStore

Responsabilité :

```text
persist integration event atomically with local state
publish later
mark published
retry publication
```

---

# 23. InboxStore

Responsabilité :

```text
deduplicate external messages/triggers
record processing status
prevent duplicate handling
```

---

# 24. PostgreSQL comme backend de référence

PostgreSQL est le backend de production de référence pour :

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
WorkerRegistry
RuntimeStore
AuditStore
OutboxStore
InboxStore
```

---

# 25. Pourquoi PostgreSQL

Atouts recherchés :

```text
ACID transactions
row-level locking
partial indexes
unique constraints
JSONB
mature concurrency
strong operational ecosystem
migrations
availability options
```

---

# 26. SQLite

SQLite peut servir pour :

```text
local development
tests
single-process mode
examples
CLI demos
```

Mais ne doit pas être présenté comme backend distribué de production.

---

# 27. InMemory stores

Utiles pour :

```text
unit tests
examples
fast prototyping
```

Non adaptés à :

```text
durable recovery
multi-process coordination
production state
```

---

# 28. Architecture de persistence

```text
                  Domain / Application
                          │
                 ┌────────┼────────┐
                 ▼        ▼        ▼
             RunStore  EffectStore LeaseStore
                 │        │        │
                 └────────┼────────┘
                          ▼
                  PostgreSQL Adapter
                          │
                          ▼
                     PostgreSQL
```

---

# 29. Persistence adapter

Un adapter concret peut regrouper physiquement plusieurs implémentations tout en gardant les ports distincts.

Exemple :

```text
PostgresRunStore
PostgresEffectStore
PostgresApprovalStore
PostgresLeaseStore
```

---

# 30. Unit of Work

Concept recommandé :

```text
UnitOfWork
```

pour regrouper les opérations devant être transactionnelles.

---

# 31. Contrat conceptuel UnitOfWork

```python
class UnitOfWork(Protocol):
    async def __aenter__(self): ...
    async def __aexit__(self, exc_type, exc, tb): ...
    async def commit(self): ...
    async def rollback(self): ...
```

---

# 32. Pourquoi un UnitOfWork

Permet de garantir des transitions comme :

```text
Run transition
+
Checkpoint
+
AuditEvent
```

dans une transaction locale cohérente.

---

# 33. Transaction boundaries

Transactions candidates :

```text
Run transition + Checkpoint
Approval decision + AuditEvent
Effect transition + ExternalReference
Lease takeover + new FencingToken
Domain state + OutboxRecord
```

---

# 34. Ce qui ne peut pas être transactionnel

Une transaction PostgreSQL ne couvre pas :

```text
GitHub
Stripe
ERP
email provider
S3
cloud deployment API
```

Ces cas nécessitent :

```text
idempotency
reconciliation
outbox
compensation
```

---

# 35. Atomicité locale

PyAgentsKit doit distinguer :

```text
local atomicity
```

de :

```text
cross-system consistency
```

---

# 36. Optimistic concurrency

Approche recommandée pour :

```text
Run
Conversation
MemoryEntry
Effect
Approval
RuntimeInvocation
```

via :

```text
version
expected_version
```

---

# 37. ConcurrencyVersion

Structure :

```text
version BIGINT
```

Incrément à chaque mutation significative.

---

# 38. Compare-and-swap

Pattern :

```sql
UPDATE runs
SET status = :new_status,
    version = version + 1
WHERE run_id = :run_id
  AND status = :expected_status
  AND version = :expected_version;
```

---

# 39. Zero-row update

Si :

```text
0 rows updated
```

alors :

```text
concurrent modification
or invalid state
```

Le code métier doit recharger et décider.

---

# 40. Pessimistic concurrency

À réserver à :

```text
lease acquisition
takeover
fencing token generation
critical coordination rows
```

---

# 41. `SELECT ... FOR UPDATE`

Utile lorsque :

```text
one transaction must serialize ownership mutation
```

mais ne doit pas être utilisé partout.

---

# 42. Advisory locks

Peuvent être utilisés dans des cas ciblés, mais ne doivent pas devenir la sémantique principale du domaine.

---

# 43. Idempotency constraints

L’EffectStore doit pouvoir garantir :

```text
same idempotency scope + key
→ one logical effect
```

---

# 44. Index logique Effect

Candidat :

```text
UNIQUE(tenant_id, idempotency_scope, idempotency_key)
```

selon modèle multi-tenant final.

---

# 45. InputFingerprint conflict

Même clé :

```text
same idempotency key
```

mais fingerprint différent :

```text
reject
```

---

# 46. Lease uniqueness

Invariant :

```text
at most one active lease
per resource identity
```

---

# 47. Partial unique index

Candidat PostgreSQL :

```text
UNIQUE(resource_type, resource_id)
WHERE status = 'ACTIVE'
```

selon modèle final.

---

# 48. Message ordering

Un message peut posséder :

```text
sequence
```

par conversation.

---

# 49. Message sequence

Contrainte candidate :

```text
UNIQUE(conversation_id, sequence)
```

---

# 50. MessageRecipient

Pour destinataires multiples :

```text
message_recipients
```

avec :

```text
UNIQUE(message_id, actor_id)
```

---

# 51. Checkpoint ordering

Contrainte :

```text
UNIQUE(run_id, sequence)
```

---

# 52. RuntimeInvocation ordering

Option :

```text
invocation_sequence
```

par Run.

---

# 53. ExternalReference

Peut être stocké sous forme :

```text
system
kind
value
```

plutôt qu’une string opaque unique.

---

# 54. ExternalReference index

Candidat :

```text
INDEX(system, kind, value)
```

pour reconciliation.

---

# 55. Audit append model

Les audit events doivent être :

```text
append only
```

dans le modèle métier.

Une correction produit :

```text
new audit event
```

et non suppression silencieuse.

---

# 56. Audit immutability

Le niveau physique peut empêcher :

```text
UPDATE
DELETE
```

par permissions dédiées ou policy DB si nécessaire.

---

# 57. DomainEvent vs AuditEvent

Ne pas fusionner automatiquement :

```text
DomainEvent
```

et :

```text
AuditEvent
```

Ils peuvent être liés, mais répondent à des besoins différents.

---

# 58. Outbox pattern

Transaction :

```text
save domain change
save outbox event
commit
```

Puis :

```text
publisher
↓
external transport
```

---

# 59. Outbox state

```text
PENDING
PUBLISHED
FAILED
DEAD_LETTER
```

---

# 60. Outbox retry

Les retries concernent :

```text
event publication
```

et non :

```text
replay of business effect
```

---

# 61. Inbox pattern

Permet de traiter :

```text
duplicate webhook
duplicate queue message
duplicate scheduler event
```

---

# 62. Inbox uniqueness

Candidat :

```text
UNIQUE(source, external_message_id)
```

---

# 63. Trigger deduplication

Un événement externe déjà traité peut retourner :

```text
existing processing result
```

ou être ignoré selon policy.

---

# 64. BlobStore

Le stockage binaire doit être séparé des metadata transactionnelles.

Port :

```text
BlobStore
```

---

# 65. BlobStore contract

```python
class BlobStore(Protocol):
    async def put(...)
    async def get(...)
    async def delete(...)
    async def exists(...)
    async def stat(...)
```

---

# 66. Backends BlobStore

```text
FilesystemBlobStore
S3BlobStore
AzureBlobStore
GCSBlobStore
```

---

# 67. Artifact metadata

PostgreSQL peut contenir :

```text
artifact_id
run_id
kind
storage_uri
checksum
content_type
size
created_at
retention_policy
```

---

# 68. Atomic artifact publication

Pattern recommandé :

```text
write temp object
↓
verify checksum
↓
finalize object
↓
persist ACTIVE artifact metadata
```

---

# 69. Incomplete artifact

Un artifact partiellement écrit ne doit pas être exposé comme :

```text
ACTIVE
```

---

# 70. Artifact states

Valeurs candidates :

```text
CREATED
STORED
ACTIVE
FAILED
DELETED
```

---

# 71. Checksums

Permettent :

```text
integrity validation
duplicate detection
recovery verification
```

---

# 72. Large payloads

Éviter de stocker dans PostgreSQL :

```text
large binary files
full repository archives
massive model outputs
```

Préférer BlobStore.

---

# 73. JSONB usage

JSONB est utile pour :

```text
runtime metadata
non-critical extensible metadata
adapter-specific data
correlation details
```

---

# 74. JSONB anti-pattern

Ne pas cacher dans JSONB :

```text
status
fencing_token
idempotency_key
version
tenant_id
```

si ces champs structurent les invariants.

---

# 75. Typed columns first

Principe :

> **Les données portant des contraintes fortes doivent être des colonnes explicites.**

---

# 76. Multi-tenancy

Les tables critiques doivent pouvoir supporter :

```text
tenant_id
```

ou autre scope logique.

---

# 77. Tenant isolation

Les requêtes doivent éviter :

```text
cross-tenant reads
cross-tenant idempotency collisions
cross-tenant lease collision
```

---

# 78. Composite keys

Des contraintes peuvent inclure :

```text
tenant_id
```

dans :

```text
unique indexes
foreign keys
idempotency scopes
```

---

# 79. Row Level Security

PostgreSQL RLS peut être envisagé pour certains déploiements.

Mais :

```text
RLS != domain authorization
```

---

# 80. Soft delete

À éviter par défaut pour les objets nécessitant une sémantique claire.

Préférer des états explicites :

```text
ARCHIVED
CANCELLED
DELETED
```

selon domaine.

---

# 81. Hard delete

Réservé à :

```text
retention
privacy requirements
test cleanup
ephemeral data
```

et audité si nécessaire.

---

# 82. Retention

Chaque famille peut avoir sa propre policy.

Exemple :

```text
AuditEvent → long retention
Message payload → configurable
Artifact binary → shorter
Worker heartbeat history → short
```

---

# 83. PII / sensitive data

La persistance doit permettre :

```text
redaction
encryption at rest
field-level minimization
retention controls
```

---

# 84. Secrets

Ne jamais persister par défaut :

```text
access token
password
private key
secret env value
```

dans les stores métier.

Utiliser :

```text
SecretReference
```

---

# 85. Encryption

Le backend peut s’appuyer sur :

```text
disk/database encryption
cloud KMS
application-level encryption
```

selon niveau de sensibilité.

---

# 86. Migrations

Les schémas doivent être versionnés.

Exemples :

```text
Alembic
custom migration framework
SQL migration files
```

Le choix d’outil reste infrastructure.

---

# 87. Migration invariants

Une migration de production doit être :

```text
versioned
repeatable in CI
observable
rollback-aware
backward-compatible when rolling deployment requires it
```

---

# 88. Expand / Contract

Pour rolling upgrades :

```text
expand schema
deploy compatible code
backfill
switch reads/writes
contract old schema
```

---

# 89. Migration locking

Une migration concurrente doit être empêchée.

Exemple :

```text
migration advisory lock
```

---

# 90. Migration state

Table candidate :

```text
schema_migrations
```

ou mécanisme fourni par l’outil choisi.

---

# 91. SQLite → PostgreSQL migration

Un outil ou commande peut supporter :

```text
development state migration
```

mais ne doit pas être confondu avec un système universel de réplication.

---

# 92. Migration command

Candidate :

```text
pyagentskit db migrate
pyagentskit db status
pyagentskit db upgrade
```

---

# 93. Store capability model

Tous les backends ne supportent pas les mêmes garanties.

Capabilities candidates :

```text
TRANSACTIONS
OPTIMISTIC_CONCURRENCY
PARTIAL_INDEX
ROW_LOCKING
JSON_DOCUMENTS
LISTEN_NOTIFY
DISTRIBUTED_LEASES
```

---

# 94. Production backend requirements

Un backend production distribué doit supporter au minimum :

```text
transactions
unique constraints
concurrent writers
conditional updates
durability
recovery
```

---

# 95. Store health

Chaque store peut exposer :

```text
HEALTHY
DEGRADED
UNAVAILABLE
```

---

# 96. Store readiness

Le worker est non-ready si un store critique nécessaire au workload est indisponible.

---

# 97. Critical stores

Typiquement :

```text
RunStore
EffectStore
LeaseStore
CheckpointStore
```

---

# 98. Optional stores

Selon feature :

```text
MemoryStore
ArtifactStore
ConversationStore
```

peuvent être optionnels.

---

# 99. Safe degradation

Exemple :

```text
ArtifactStore unavailable
```

peut permettre de continuer si aucun artifact critique n’est requis.

Mais :

```text
LeaseStore unavailable
```

bloque les nouveaux effets protégés.

---

# 100. Connection pooling

Le PostgreSQL adapter doit utiliser un pool borné.

À surveiller :

```text
pool size
queue time
transaction duration
connection leaks
```

---

# 101. Long transactions

À éviter.

Une transaction longue autour d’un LLM ou d’un appel réseau externe est interdite.

---

# 102. Transaction rule

```text
open DB transaction
↓
perform local DB work
↓
commit
```

et non :

```text
open transaction
↓
call LLM
↓
call external API
↓
wait human approval
↓
commit
```

---

# 103. External effects outside DB transaction

L’Effect Safety Model gère la cohérence avec les systèmes externes.

---

# 104. Isolation levels

Le niveau par défaut peut rester :

```text
READ COMMITTED
```

si les invariants sont renforcés par :

```text
constraints
CAS
row locks where needed
```

---

# 105. SERIALIZABLE

À utiliser uniquement dans les opérations où le bénéfice justifie le coût.

---

# 106. Deadlocks

Le code doit traiter :

```text
deadlock detected
serialization failure
```

comme erreurs retriables au niveau transactionnel local lorsque sûr.

---

# 107. Database retry

Retry acceptable pour :

```text
transaction aborted before commit
deadlock retry
serialization retry
read-only query
```

---

# 108. Database retry vs Effect retry

Ne jamais confondre :

```text
retry local transaction
```

avec :

```text
retry external business effect
```

---

# 109. Lock timeout

Configurer des timeouts bornés :

```text
lock_timeout
statement_timeout
transaction_timeout where available
```

selon backend.

---

# 110. Store operation timeout

Chaque port devrait accepter une stratégie de timeout raisonnable.

---

# 111. Backpressure

Si PostgreSQL sature :

```text
admission reduce
effect throughput reduce
reconciliation bounded
```

---

# 112. Query patterns

Éviter les scans globaux fréquents.

Exemples d’index utiles :

```text
runs(status)
effects(status)
approvals(status)
leases(resource_type, resource_id)
messages(conversation_id, sequence)
audit_events(run_id, created_at)
```

---

# 113. Recoverable runs query

Candidat :

```text
WHERE status IN ('RUNNING','WAITING','PAUSED')
```

avec conditions supplémentaires.

---

# 114. Unresolved effects query

```text
WHERE status IN ('STARTED','UNKNOWN','RECONCILIATION_REQUIRED')
```

---

# 115. Pending approvals query

```text
WHERE status = 'PENDING'
AND expires_at > now()
```

---

# 116. Lease expiry query

```text
WHERE status = 'ACTIVE'
AND expires_at <= database_now()
```

---

# 117. Audit timeline query

Index :

```text
(object_type, object_id, created_at)
```

ou :

```text
run_id, created_at
```

---

# 118. Data ownership

Chaque store doit clairement définir qui peut écrire ses données.

Exemple :

```text
LeaseStore
→ LeaseCoordinator

EffectStore
→ EffectExecutionService / Reconciler
```

---

# 119. Avoid random writes

Un composant ne doit pas pouvoir muter arbitrairement toutes les tables.

---

# 120. Repository boundaries

Ports ciblés permettent de garder :

```text
least privilege
domain clarity
testability
```

---

# 121. Persistence events

Événements techniques possibles :

```text
StoreUnavailable
StoreRecovered
MigrationStarted
MigrationCompleted
MigrationFailed
OutboxPublishFailed
```

Ils ne sont pas nécessairement des DomainEvents.

---

# 122. Observability

Métriques :

```text
store_operation_latency
store_errors_total
db_pool_in_use
db_pool_wait_seconds
transaction_retries_total
outbox_pending
inbox_duplicates_total
```

---

# 123. PostgreSQL metrics

À surveiller :

```text
connections
locks
deadlocks
long transactions
vacuum lag
table bloat
replication lag
disk
CPU
IO
```

---

# 124. Tracing

Spans :

```text
db.run.get
db.run.transition
db.effect.reserve
db.lease.acquire
db.lease.renew
db.approval.decide
db.checkpoint.append
```

---

# 125. Logging

Ne pas loguer :

```text
full secrets
large payloads
sensitive message content by default
```

---

# 126. Store exceptions

Taxonomie candidate :

```text
StoreError
StoreUnavailable
StoreTimeout
ConcurrencyConflict
UniqueConstraintConflict
MigrationRequired
SchemaIncompatible
SerializationConflict
```

---

# 127. ConcurrencyConflict

Erreur métier/technique permettant au caller de :

```text
reload
re-evaluate
retry safe local transition
```

---

# 128. SchemaIncompatible

Un worker détectant un schéma incompatible doit :

```text
fail readiness
```

plutôt que continuer.

---

# 129. Migration compatibility check

Au démarrage :

```text
expected schema version
vs
actual schema version
```

---

# 130. Rolling compatibility

Le système doit permettre une fenêtre où :

```text
worker vN
worker vN+1
```

coexistent si le déploiement rolling l’exige.

---

# 131. Backup

PostgreSQL doit bénéficier d’une stratégie :

```text
backup
restore
PITR
```

selon niveau de production.

---

# 132. Restore testing

Un backup non testé n’est pas une garantie.

Inclure :

```text
restore drills
```

dans la qualification production.

---

# 133. Disaster recovery

À documenter :

```text
RPO
RTO
backup location
restore procedure
credential recovery
```

---

# 134. Replication

Une réplication PostgreSQL peut améliorer disponibilité.

Mais :

```text
replica lag
```

doit être pris en compte pour les lectures autoritatives.

---

# 135. Authoritative reads

Pour :

```text
lease validation
fencing
effect state
approval decision
```

éviter une replica potentiellement en retard si cela compromet la sûreté.

---

# 136. Read replicas

Peuvent servir pour :

```text
reporting
audit views
history
analytics
```

selon tolérance.

---

# 137. Cache

Un cache peut optimiser :

```text
runtime descriptor
static policy
read-heavy metadata
```

mais ne doit pas devenir source de vérité pour :

```text
Lease
Effect
Approval
Run state
```

---

# 138. Cache invalidation

La correctness ne doit pas dépendre d’une invalidation parfaite.

---

# 139. Store adapters and async

Les adapters de production doivent être :

```text
async-compatible
```

pour éviter de bloquer le worker.

---

# 140. Sync façade

Une façade sync peut exister pour des applications simples, sans dupliquer la sémantique.

---

# 141. Connection ownership

Les transactions et connexions doivent être gérées par :

```text
adapter / UnitOfWork
```

pas par les entités métier.

---

# 142. Testing — unit

Les ports peuvent être testés avec :

```text
fake stores
in-memory stores
```

pour les règles métier.

---

# 143. Testing — contract

Chaque implémentation doit passer une même suite de conformité.

Exemples :

```text
RunStoreContractTests
EffectStoreContractTests
LeaseStoreContractTests
```

---

# 144. Testing — PostgreSQL

Utiliser un vrai PostgreSQL pour :

```text
transactions
constraints
row locks
partial indexes
concurrency
```

---

# 145. Testing — concurrency

Scénarios :

```text
two concurrent run transitions
two effect reservations
two lease acquisitions
two approval decisions
```

---

# 146. Testing — crash

Tester crash autour de :

```text
commit
effect reservation
checkpoint append
outbox creation
lease takeover
```

---

# 147. Testing — migration

Vérifier :

```text
fresh install
upgrade from previous schema
rollback strategy
mixed-version workers
```

---

# 148. Testing — SQLite/Postgres parity

Les stores SQLite peuvent partager la sémantique fonctionnelle, mais les tests doivent documenter les différences de concurrence et de SQL.

---

# 149. Migration SQLite → PostgreSQL

Processus possible :

```text
export state
validate
transform
import
verify counts
verify checksums
verify foreign keys
```

---

# 150. Migration safety

Une migration de state store ne doit jamais :

```text
silently drop unresolved effects
lose approvals
reset fencing tokens
rewrite audit history without trace
```

---

# 151. Fencing migration rule

Les générations de fencing doivent rester monotones après migration.

---

# 152. Effect migration rule

Conserver :

```text
effect_id
idempotency key
input fingerprint
status
external references
```

---

# 153. Approval migration rule

Conserver :

```text
decision
actor
scope
timestamps
```

---

# 154. Audit migration rule

Conserver l’ordre temporel autant que possible et tracer la migration elle-même.

---

# 155. Production store package layout

Exemple :

```text
pyagentskit/
├── ports/
│   └── stores/
├── adapters/
│   ├── postgres/
│   │   ├── run_store.py
│   │   ├── effect_store.py
│   │   ├── lease_store.py
│   │   ├── approval_store.py
│   │   └── migrations/
│   ├── sqlite/
│   └── blob/
```

---

# 156. Store configuration

Exemple conceptuel :

```text
database_url
pool_size
pool_timeout
statement_timeout
migration_mode
schema
application_name
```

---

# 157. Multiple schemas

PostgreSQL peut utiliser :

```text
single schema
```

au départ.

Des schémas séparés peuvent être envisagés pour :

```text
coordination
audit
core
```

si cela apporte une valeur opérationnelle réelle.

---

# 158. Avoid schema over-segmentation

Ne pas créer un schéma DB par bounded context sans besoin concret.

---

# 159. Database naming

Convention recommandée :

```text
snake_case
plural table names
explicit foreign keys
explicit timestamps
```

---

# 160. Primary keys

Préférence :

```text
UUID / ULID / sortable opaque IDs
```

selon ADR final.

---

# 161. ID generation

L’identité métier peut être générée :

```text
application side
```

pour permettre création avant persistence.

---

# 162. Timestamps

Préférence :

```text
UTC
timezone-aware
```

---

# 163. Database defaults

Les defaults critiques ne doivent pas cacher une règle métier.

Exemple :

```text
status default
```

doit rester cohérent avec le domaine.

---

# 164. Serialization

Les Value Objects doivent avoir une représentation stable.

Exemple :

```text
FencingToken → BIGINT
EffectStatus → text/enum
CorrelationContext → JSONB
ExternalReference → structured columns/JSONB
```

---

# 165. Enum DB vs text

Les enums PostgreSQL peuvent rigidifier les migrations.

Option souvent plus souple :

```text
VARCHAR + CHECK constraint
```

selon besoins.

---

# 166. Store schema versioning

Chaque release doit connaître :

```text
minimum supported schema version
maximum compatible schema version
```

si mixed-version operation est supportée.

---

# 167. Data corruption

Le système doit détecter :

```text
impossible state
missing foreign key
duplicate active lease
effect without run
checkpoint sequence gap where forbidden
```

---

# 168. Repair tooling

Les corrections manuelles doivent passer par :

```text
explicit admin command
audit
validation
```

et non par des updates SQL non tracés en exploitation normale.

---

# 169. Admin CLI candidates

```text
pyagentskit db status
pyagentskit db migrate
pyagentskit db verify
pyagentskit store inspect
pyagentskit store repair --plan
```

---

# 170. Verification command

Peut vérifier :

```text
foreign keys
active lease uniqueness
orphan artifacts
unknown effects
pending approvals
checkpoint ordering
schema version
```

---

# 171. Read models

Des vues ou projections peuvent être créées pour :

```text
operator dashboard
audit timeline
run summary
```

sans devenir source de vérité.

---

# 172. CQRS

PyAgentsKit n’impose pas CQRS complet.

Mais peut distinguer :

```text
write model
read projections
```

quand utile.

---

# 173. Event sourcing

Non requis.

Le système peut conserver un historique riche sans reconstruire tout l’état exclusivement depuis les événements.

---

# 174. Snapshotting

Peut être utilisé pour :

```text
long histories
read optimization
recovery optimization
```

mais ne remplace pas les stores autoritatifs.

---

# 175. Persistence invariants

```text
PERSIST-INV-01
Le domaine ne dépend pas d’un backend concret.

PERSIST-INV-02
Chaque store a une responsabilité explicite.

PERSIST-INV-03
Les transitions critiques utilisent transactions ou CAS appropriés.

PERSIST-INV-04
Les effets externes ne sont pas inclus dans une transaction DB longue.

PERSIST-INV-05
Une idempotency key logique ne peut être réservée deux fois dans le même scope.

PERSIST-INV-06
Les fencing tokens restent monotones.

PERSIST-INV-07
Les checkpoints validés sont immuables.

PERSIST-INV-08
Les audit events sont append-oriented.

PERSIST-INV-09
Un backend de test ne doit pas être présenté comme production-safe sans qualification.

PERSIST-INV-10
Les secrets ne sont pas persistés en clair dans les stores métier par défaut.
```

---

# 176. Anti-patterns

À éviter :

```text
one GenericRepository for everything
ORM models == domain entities
long DB transaction around network calls
JSONB for all domain fields
cache as source of truth
SQLite marketed as distributed backend
blind DB retry around side effects
manual SQL mutation without audit
store implementation imported into domain
```

---

# 177. Qualification production

La persistence est qualifiée si :

```text
real PostgreSQL
multiple worker processes
concurrent writes
crash tests
migration tests
backup/restore tests
load tests
```

---

# 178. Load tests

Mesurer :

```text
run writes/sec
checkpoint append latency
effect reservation throughput
lease renew throughput
audit append throughput
outbox publishing throughput
```

---

# 179. Contention tests

Cibler :

```text
same run
same idempotency key
same lease resource
same approval
```

---

# 180. Failure injection

Simuler :

```text
DB restart
connection loss
transaction abort
deadlock
lock timeout
disk pressure
replication lag
```

---

# 181. Recovery tests

Vérifier :

```text
worker reconnects
reloads authoritative state
revalidates lease
does not trust stale cache
```

---

# 182. Backup/restore tests

Après restore :

```text
run states valid
effects preserved
approvals preserved
fencing monotonicity preserved
audit timeline queryable
```

---

# 183. Acceptance criteria

Le modèle Persistence & State Stores est opérationnel si :

1. les stores sont exposés comme ports ;
2. PostgreSQL est backend de référence ;
3. SQLite/InMemory sont explicitement limités au local/test ;
4. Run, Effect, Approval, Lease et Checkpoint disposent de stores distincts ;
5. les transitions critiques sont transactionnelles ;
6. l’optimistic concurrency est supportée ;
7. les idempotency keys sont atomiquement réservées ;
8. le LeaseStore supporte fencing et takeover ;
9. les checkpoints sont immuables et ordonnés ;
10. les audit events sont append-oriented ;
11. l’Outbox peut publier sans perdre un événement après commit ;
12. le BlobStore sépare metadata et contenu ;
13. les migrations sont versionnées ;
14. les mixed-version scenarios sont définis ;
15. les secrets ne sont pas persistés en clair ;
16. les tests utilisent PostgreSQL réel ;
17. les scénarios de crash et contention sont couverts ;
18. backup/restore fait partie de la qualification production.

---

# 184. Architecture cible

```text
                     PyAgentsKit Domain
                            │
            ┌───────────────┼────────────────┐
            ▼               ▼                ▼
         RunStore       EffectStore       LeaseStore
            │               │                │
            ├───────────────┼────────────────┤
            ▼               ▼                ▼
      ApprovalStore   CheckpointStore   RuntimeStore
            │               │                │
            └───────────────┼────────────────┘
                            ▼
                     Unit of Work
                            │
                            ▼
                       PostgreSQL
                            │
              ┌─────────────┴─────────────┐
              ▼                           ▼
           Outbox                     AuditStore
                                          │
                                          ▼
                                     Read Models

                     Artifact metadata
                            │
                            ▼
                      ArtifactStore
                            │
                            ▼
                         BlobStore
                    S3 / Azure / Filesystem
```

---

# 185. Flux Run + Checkpoint

```text
DurableRunner
↓
UnitOfWork
↓
Run transition
+
Checkpoint append
+
AuditEvent
↓
COMMIT
```

---

# 186. Flux Effect reservation

```text
EffectExecutionService
↓
EffectStore.find(idempotency key)
↓
none?
↓
atomic reserve
↓
commit
↓
external effect execution
```

---

# 187. Flux Approval

```text
Human decision
↓
ApprovalService
↓
transaction
├── Approval APPROVED/REJECTED
├── AuditEvent
└── Outbox wake-up
↓
commit
```

---

# 188. Flux Lease

```text
Worker
↓
LeaseStore.acquire(resource)
↓
transaction
├── verify active lease
├── increment fencing generation
└── create/update lease
↓
commit
↓
OwnershipContext
```

---

# 189. Flux Artifact

```text
generate content
↓
BlobStore.put(temp)
↓
checksum
↓
finalize blob
↓
ArtifactStore.persist metadata
↓
Artifact ACTIVE
```

---

# 190. Questions ouvertes

```text
Q-PERSIST-01 SQLAlchemy, SQLModel, psycopg direct ou autre adapter ?
Q-PERSIST-02 RunStore et CheckpointStore partagent-ils un UnitOfWork ?
Q-PERSIST-03 Quelle stratégie d’ID : UUIDv7, ULID, UUID4 ?
Q-PERSIST-04 PostgreSQL ENUM ou VARCHAR + CHECK ?
Q-PERSIST-05 AuditStore dans mêmes tablespace/schema ?
Q-PERSIST-06 Outbox obligatoire dès v1 ?
Q-PERSIST-07 Inbox obligatoire dès v1 ?
Q-PERSIST-08 Conversation messages dans PostgreSQL ou archive externe à terme ?
Q-PERSIST-09 Faut-il RLS pour multi-tenancy ?
Q-PERSIST-10 Quel niveau de compatibilité mixed-version ?
Q-PERSIST-11 Quelle stratégie de backup minimale documenter ?
Q-PERSIST-12 Quelle commande officielle SQLite → PostgreSQL ?
```

---

# 191. ADR induits

```text
ADR-PERSIST-001 PostgreSQL reference backend
ADR-PERSIST-002 Store port boundaries
ADR-PERSIST-003 Unit of Work strategy
ADR-PERSIST-004 Optimistic concurrency
ADR-PERSIST-005 Lease persistence model
ADR-PERSIST-006 Effect idempotency uniqueness
ADR-PERSIST-007 Checkpoint immutability
ADR-PERSIST-008 Audit append model
ADR-PERSIST-009 Outbox strategy
ADR-PERSIST-010 BlobStore separation
ADR-PERSIST-011 Migration strategy
ADR-PERSIST-012 ID generation
ADR-PERSIST-013 Multi-tenancy persistence
ADR-PERSIST-014 SQLite support scope
```

---

# 192. Definition of Done

La couche Persistence & State Stores est mature lorsque :

1. les ports sont stables ;
2. aucune entité métier ne dépend de PostgreSQL ;
3. PostgreSQL implémente tous les stores P0 ;
4. `RunStore`, `EffectStore`, `ApprovalStore`, `LeaseStore` et `CheckpointStore` passent leurs contract tests ;
5. l’optimistic concurrency est vérifiée ;
6. l’idempotency reservation est atomique ;
7. le LeaseStore résiste aux acquisitions concurrentes ;
8. les fencing tokens sont monotones ;
9. les checkpoints sont immuables ;
10. les migrations sont versionnées ;
11. upgrade depuis la version précédente est testé ;
12. SQLite reste limité aux scénarios documentés ;
13. Outbox est disponible pour les événements critiques ;
14. BlobStore possède au moins une implémentation locale et une objet-storage ;
15. PostgreSQL outage produit une safe degradation ;
16. backup/restore est documenté et testé ;
17. métriques, logs et traces sont exposés ;
18. aucune transaction ne reste ouverte pendant un appel LLM ou un effet externe.

---

# 193. Résumé

La persistence cible de PyAgentsKit repose sur :

```text
DOMAIN PORTS
+
SPECIALIZED STORES
+
POSTGRESQL
+
OPTIMISTIC CONCURRENCY
+
TRANSACTIONAL BOUNDARIES
+
OUTBOX / INBOX
+
BLOB STORAGE
+
VERSIONED MIGRATIONS
```

Le principe est :

```text
RunStore ≠ EffectStore ≠ LeaseStore
```

même s’ils partagent :

```text
the same PostgreSQL cluster
```

La séparation recherchée est :

```text
semantic
transactional
testable
replaceable
```

et non une multiplication artificielle de bases physiques.

Le principe fondamental reste :

> **Une exécution durable n’est fiable que si l’état nécessaire à sa reprise est stocké dans des composants dont les garanties sont explicites, testées et indépendantes du processus qui exécute l’agent.**

Le document suivant naturel est :

```text
../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md
```
