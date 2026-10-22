# PyAgentsKit — PostgreSQL Data Model

**Document :** `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Spécification technique — PostgreSQL Reference Data Model  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../architecture/08_PYAGENTSKIT_ERD.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`

---

# 1. Objet

Ce document définit le **modèle PostgreSQL de référence** de PyAgentsKit.

Il traduit les invariants métier en structures physiques :

- tables ;
- clés primaires ;
- clés étrangères ;
- indexes ;
- contraintes ;
- colonnes versionnées ;
- timestamps ;
- JSONB ;
- règles de multi-tenancy ;
- transactional boundaries ;
- idempotency ;
- leases ;
- fencing tokens ;
- checkpoints ;
- approvals ;
- Effects ;
- audit ;
- Outbox / Inbox ;
- workers ;
- runtime bindings/invocations ;
- artifacts ;
- conversations/messages/memory.

Le principe directeur est :

> **PostgreSQL doit matérialiser les invariants critiques de PyAgentsKit sans absorber la logique métier dans la base.**

---

# 2. Positionnement

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
Artifact metadata
AuditStore
OutboxStore
InboxStore
```

---

# 3. Objectifs

Le modèle doit garantir :

```text
ACID persistence
concurrency safety
strong constraints
recoverability
efficient queries
auditability
multi-worker correctness
migration safety
tenant isolation
```

---

# 4. Non-objectifs

Le modèle PostgreSQL ne doit pas :

```text
replace domain services
encode every business rule in triggers
become event-sourced by default
store large binaries unnecessarily
contain provider SDK objects
hide core invariants in JSONB
```

---

# 5. Principes de modélisation

```text
typed columns for critical invariants
JSONB for extensible metadata
foreign keys for ownership relationships
unique constraints for logical uniqueness
version columns for optimistic concurrency
database time for lease expiry
append-oriented tables for audit/checkpoints
```

---

# 6. Schéma physique

Option initiale recommandée :

```text
schema = pyagentskit
```

Tables :

```text
sessions
runs
conversations
participants
messages
message_recipients
memory_entries
checkpoints
effects
reconciliation_cases
approvals
workers
leases
runtime_bindings
runtime_invocations
artifacts
audit_events
outbox_events
inbox_events
```

---

# 7. Séparation par schémas

Option future :

```text
pyagentskit_core
pyagentskit_audit
pyagentskit_coordination
```

À n’introduire que si cela apporte une valeur opérationnelle réelle.

---

# 8. Types d’identifiants

Recommandation :

```text
UUID
```

avec possibilité future :

```text
UUIDv7
```

pour localité temporelle.

---

# 9. Alternative ULID

Possible si besoin, mais doit être tranché par ADR.

---

# 10. Timestamps

Toutes les colonnes temporelles :

```text
TIMESTAMPTZ
```

---

# 11. Source temporelle

Pour coordination critique :

```text
now()
```

PostgreSQL est autoritatif.

---

# 12. Version columns

Pour optimistic concurrency :

```text
version BIGINT NOT NULL DEFAULT 0
```

---

# 13. Tenant ID

Pour objets tenant-scoped :

```text
tenant_id UUID NULL/NOT NULL
```

selon mode multi-tenant.

---

# 14. Soft delete

Éviter un `deleted_at` générique partout.

Préférer des états explicites.

---

# 15. JSONB

Utilisé pour :

```text
metadata
adapter-specific details
correlation context
extensible payloads
```

---

# 16. JSONB Anti-pattern

Ne pas stocker uniquement en JSONB :

```text
status
fencing_token
version
idempotency_key
tenant_id
run_id
approval decision
```

---

# 17. Table `sessions`

Colonnes candidates :

```sql
session_id UUID PRIMARY KEY,
tenant_id UUID,
status VARCHAR(32) NOT NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
version BIGINT NOT NULL DEFAULT 0,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 18. Session indexes

```sql
CREATE INDEX idx_sessions_tenant_status
ON sessions (tenant_id, status);
```

---

# 19. Table `runs`

Colonnes :

```sql
run_id UUID PRIMARY KEY,
tenant_id UUID,
session_id UUID NULL,
runtime_binding_id UUID NULL,
state VARCHAR(32) NOT NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
started_at TIMESTAMPTZ NULL,
completed_at TIMESTAMPTZ NULL,
version BIGINT NOT NULL DEFAULT 0,
correlation_id VARCHAR(128) NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 20. Run foreign keys

```sql
session_id → sessions.session_id
runtime_binding_id → runtime_bindings.runtime_binding_id
```

---

# 21. Run state constraint

```sql
CHECK (
  state IN (
    'CREATED',
    'READY',
    'RUNNING',
    'WAITING',
    'PAUSED',
    'SUCCEEDED',
    'FAILED',
    'CANCELLED'
  )
)
```

---

# 22. Run indexes

```sql
CREATE INDEX idx_runs_state
ON runs (state);

CREATE INDEX idx_runs_tenant_state
ON runs (tenant_id, state);

CREATE INDEX idx_runs_session
ON runs (session_id);

CREATE INDEX idx_runs_updated
ON runs (updated_at DESC);
```

---

# 23. Recoverable Runs index

Possible partial index :

```sql
CREATE INDEX idx_runs_recoverable
ON runs (updated_at)
WHERE state IN ('RUNNING', 'WAITING', 'PAUSED');
```

---

# 24. Run optimistic concurrency

Pattern :

```sql
UPDATE runs
SET state = $1,
    version = version + 1,
    updated_at = now()
WHERE run_id = $2
  AND version = $3
  AND state = $4;
```

---

# 25. Table `conversations`

```sql
conversation_id UUID PRIMARY KEY,
tenant_id UUID,
session_id UUID NOT NULL,
status VARCHAR(32) NOT NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
version BIGINT NOT NULL DEFAULT 0,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 26. Conversation status

```text
OPEN
PAUSED
CLOSED
ARCHIVED
```

---

# 27. Conversation indexes

```sql
CREATE INDEX idx_conversations_session
ON conversations (session_id);

CREATE INDEX idx_conversations_tenant_status
ON conversations (tenant_id, status);
```

---

# 28. Table `participants`

```sql
participant_id UUID PRIMARY KEY,
conversation_id UUID NOT NULL,
actor_id UUID NOT NULL,
role VARCHAR(64) NOT NULL,
joined_at TIMESTAMPTZ NOT NULL,
left_at TIMESTAMPTZ NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 29. Participant uniqueness

```sql
UNIQUE(conversation_id, actor_id, role)
```

selon besoin exact.

---

# 30. Table `messages`

```sql
message_id UUID PRIMARY KEY,
tenant_id UUID,
conversation_id UUID NOT NULL,
sender_actor_id UUID NULL,
message_type VARCHAR(64) NOT NULL,
sequence BIGINT NOT NULL,
content JSONB NOT NULL,
created_at TIMESTAMPTZ NOT NULL,
persisted_at TIMESTAMPTZ NOT NULL,
redacted_at TIMESTAMPTZ NULL,
archived_at TIMESTAMPTZ NULL,
deduplication_key VARCHAR(255) NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 31. Message ordering

```sql
UNIQUE(conversation_id, sequence)
```

---

# 32. Message deduplication

Candidate :

```sql
CREATE UNIQUE INDEX uq_messages_dedup
ON messages (tenant_id, conversation_id, deduplication_key)
WHERE deduplication_key IS NOT NULL;
```

---

# 33. Message indexes

```sql
CREATE INDEX idx_messages_conversation_sequence
ON messages (conversation_id, sequence);

CREATE INDEX idx_messages_created
ON messages (created_at);
```

---

# 34. Table `message_recipients`

```sql
message_id UUID NOT NULL,
actor_id UUID NOT NULL,
PRIMARY KEY (message_id, actor_id)
```

---

# 35. Table `memory_entries`

```sql
memory_entry_id UUID PRIMARY KEY,
tenant_id UUID,
session_id UUID NULL,
scope VARCHAR(32) NOT NULL,
scope_id UUID NULL,
key VARCHAR(255) NOT NULL,
value JSONB NOT NULL,
version BIGINT NOT NULL DEFAULT 0,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
expires_at TIMESTAMPTZ NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 36. Memory uniqueness

```sql
UNIQUE(tenant_id, scope, scope_id, key)
```

selon null semantics à gérer explicitement.

---

# 37. Memory indexes

```sql
CREATE INDEX idx_memory_scope
ON memory_entries (tenant_id, scope, scope_id);

CREATE INDEX idx_memory_expiry
ON memory_entries (expires_at)
WHERE expires_at IS NOT NULL;
```

---

# 38. Table `checkpoints`

```sql
checkpoint_id UUID PRIMARY KEY,
tenant_id UUID,
run_id UUID NOT NULL,
sequence BIGINT NOT NULL,
checkpoint_type VARCHAR(64) NOT NULL,
schema_version VARCHAR(32) NOT NULL,
state_payload JSONB NOT NULL,
runtime_checkpoint_ref JSONB NULL,
checksum VARCHAR(128) NULL,
created_at TIMESTAMPTZ NOT NULL,
created_by_worker_id UUID NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 39. Checkpoint ordering

```sql
UNIQUE(run_id, sequence)
```

---

# 40. Checkpoint immutability

Le modèle applicatif interdit :

```text
UPDATE
```

sur un checkpoint finalisé.

Option DB :

```text
restricted UPDATE permissions
```

---

# 41. Checkpoint indexes

```sql
CREATE INDEX idx_checkpoints_run_sequence
ON checkpoints (run_id, sequence DESC);
```

---

# 42. Latest checkpoint query

```sql
SELECT *
FROM checkpoints
WHERE run_id = $1
ORDER BY sequence DESC
LIMIT 1;
```

---

# 43. Table `effects`

Colonnes principales :

```sql
effect_id UUID PRIMARY KEY,
tenant_id UUID,
run_id UUID NOT NULL,
effect_kind VARCHAR(255) NOT NULL,
status VARCHAR(64) NOT NULL,
risk_level VARCHAR(32) NOT NULL,
idempotency_scope VARCHAR(255) NOT NULL,
idempotency_key VARCHAR(255) NOT NULL,
input_fingerprint VARCHAR(128) NOT NULL,
external_system VARCHAR(128) NULL,
external_reference_kind VARCHAR(128) NULL,
external_reference_value VARCHAR(512) NULL,
started_at TIMESTAMPTZ NULL,
completed_at TIMESTAMPTZ NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
version BIGINT NOT NULL DEFAULT 0,
ownership_context JSONB NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 44. Effect status

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

# 45. Effect status constraint

À matérialiser via :

```text
VARCHAR + CHECK
```

ou type enum si ADR futur.

---

# 46. Effect idempotency uniqueness

```sql
UNIQUE(
  tenant_id,
  idempotency_scope,
  idempotency_key
)
```

---

# 47. Null tenant semantics

En single-tenant mode, préférer :

```text
tenant_id fixed sentinel
```

ou une stratégie explicite pour éviter l’unicité PostgreSQL avec `NULL`.

---

# 48. Effect fingerprint rule

Même clé mais fingerprint différent :

```text
IdempotencyConflict
```

au niveau service.

---

# 49. Effect indexes

```sql
CREATE INDEX idx_effects_run
ON effects (run_id);

CREATE INDEX idx_effects_status
ON effects (status);

CREATE INDEX idx_effects_external_ref
ON effects (
  external_system,
  external_reference_kind,
  external_reference_value
);
```

---

# 50. Unresolved Effect index

```sql
CREATE INDEX idx_effects_unresolved
ON effects (updated_at)
WHERE status IN (
  'STARTED',
  'UNKNOWN',
  'RECONCILIATION_REQUIRED'
);
```

---

# 51. Effect reserve transaction

Pseudo-SQL :

```sql
INSERT INTO effects (...)
VALUES (...)
ON CONFLICT (...) DO NOTHING;
```

Puis :

```text
if existing:
compare fingerprint
```

---

# 52. Effect transition CAS

```sql
UPDATE effects
SET status = $new,
    version = version + 1,
    updated_at = now()
WHERE effect_id = $id
  AND status = $expected_status
  AND version = $expected_version;
```

---

# 53. ExternalReference columns

Préférence :

```text
structured columns
```

plutôt que JSONB uniquement.

---

# 54. Table `reconciliation_cases`

```sql
reconciliation_case_id UUID PRIMARY KEY,
tenant_id UUID,
effect_id UUID NOT NULL,
status VARCHAR(64) NOT NULL,
strategy VARCHAR(128) NOT NULL,
attempt_count INTEGER NOT NULL DEFAULT 0,
last_attempt_at TIMESTAMPTZ NULL,
next_attempt_at TIMESTAMPTZ NULL,
resolution JSONB NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
version BIGINT NOT NULL DEFAULT 0,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 55. Reconciliation status

Candidate :

```text
OPEN
IN_PROGRESS
RESOLVED
MANUAL_REVIEW
FAILED
CANCELLED
```

---

# 56. Reconciliation indexes

```sql
CREATE INDEX idx_reconciliation_effect
ON reconciliation_cases (effect_id);

CREATE INDEX idx_reconciliation_due
ON reconciliation_cases (next_attempt_at)
WHERE status IN ('OPEN', 'IN_PROGRESS');
```

---

# 57. Table `approvals`

```sql
approval_id UUID PRIMARY KEY,
tenant_id UUID,
run_id UUID NOT NULL,
effect_id UUID NULL,
status VARCHAR(32) NOT NULL,
scope JSONB NOT NULL,
scope_fingerprint VARCHAR(128) NULL,
requested_by_actor_id UUID NULL,
requested_by_principal JSONB NULL,
decision VARCHAR(32) NULL,
decided_by_actor_id UUID NULL,
decided_by_principal JSONB NULL,
reason TEXT NULL,
policy_id VARCHAR(255) NULL,
policy_version VARCHAR(64) NULL,
requested_at TIMESTAMPTZ NOT NULL,
decided_at TIMESTAMPTZ NULL,
expires_at TIMESTAMPTZ NULL,
cancelled_at TIMESTAMPTZ NULL,
version BIGINT NOT NULL DEFAULT 0,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 58. Approval status

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

---

# 59. Approval terminal immutability

Le service n’autorise aucune transition depuis :

```text
APPROVED
REJECTED
EXPIRED
CANCELLED
```

vers un autre état.

---

# 60. Approval indexes

```sql
CREATE INDEX idx_approvals_run
ON approvals (run_id);

CREATE INDEX idx_approvals_effect
ON approvals (effect_id);

CREATE INDEX idx_approvals_pending
ON approvals (expires_at)
WHERE status = 'PENDING';
```

---

# 61. Approval decision CAS

```sql
UPDATE approvals
SET status = 'APPROVED',
    decision = 'APPROVE',
    decided_at = now(),
    version = version + 1
WHERE approval_id = $1
  AND status = 'PENDING'
  AND version = $2
  AND (expires_at IS NULL OR expires_at > now());
```

---

# 62. Approval expiry race

La base décide via :

```text
now()
```

et update conditionnel.

---

# 63. Approval + Audit + Outbox transaction

Transaction locale recommandée :

```text
update Approval
insert AuditEvent
insert OutboxEvent
COMMIT
```

---

# 64. Table `workers`

```sql
worker_id UUID PRIMARY KEY,
status VARCHAR(32) NOT NULL,
started_at TIMESTAMPTZ NOT NULL,
last_heartbeat_at TIMESTAMPTZ NULL,
stopped_at TIMESTAMPTZ NULL,
hostname VARCHAR(255) NULL,
process_id INTEGER NULL,
instance_id VARCHAR(255) NULL,
capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 65. Worker status

```text
STARTING
READY
BUSY
DRAINING
UNHEALTHY
STOPPED
```

---

# 66. Worker indexes

```sql
CREATE INDEX idx_workers_status
ON workers (status);

CREATE INDEX idx_workers_heartbeat
ON workers (last_heartbeat_at);
```

---

# 67. Table `leases`

```sql
lease_id UUID PRIMARY KEY,
tenant_id UUID,
resource_type VARCHAR(128) NOT NULL,
resource_id VARCHAR(512) NOT NULL,
owner_worker_id UUID NOT NULL,
status VARCHAR(32) NOT NULL,
fencing_token BIGINT NOT NULL,
acquired_at TIMESTAMPTZ NOT NULL,
renewed_at TIMESTAMPTZ NOT NULL,
expires_at TIMESTAMPTZ NOT NULL,
released_at TIMESTAMPTZ NULL,
version BIGINT NOT NULL DEFAULT 0,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 68. Lease status

```text
ACTIVE
LOST
EXPIRED
RELEASED
TAKEN_OVER
```

---

# 69. Active lease uniqueness

Contrainte logique :

```text
at most one authoritative ACTIVE lease
per resource identity
```

---

# 70. Partial unique index Lease

```sql
CREATE UNIQUE INDEX uq_leases_active_resource
ON leases (tenant_id, resource_type, resource_id)
WHERE status = 'ACTIVE';
```

---

# 71. Null tenant issue Lease

Même règle :

```text
tenant_id must be normalized
```

si unicité cross-tenant critique.

---

# 72. Lease fencing uniqueness

Un même token ne doit pas apparaître deux fois pour une même ressource.

Candidate :

```sql
UNIQUE(
  tenant_id,
  resource_type,
  resource_id,
  fencing_token
)
```

---

# 73. Fencing monotonicity

La monotonie nécessite une stratégie transactionnelle.

---

# 74. Option A — token in leases history

Lors takeover :

```text
SELECT max(fencing_token)
FOR UPDATE / serialized context
```

puis `+1`.

---

# 75. Option B — resource counters

Table dédiée :

```text
lease_resources
```

---

# 76. Table `lease_resources`

Candidate :

```sql
tenant_id UUID,
resource_type VARCHAR(128),
resource_id VARCHAR(512),
current_fencing_token BIGINT NOT NULL,
version BIGINT NOT NULL DEFAULT 0,
PRIMARY KEY (tenant_id, resource_type, resource_id)
```

---

# 77. Fencing counter acquisition

Transaction :

```text
lock resource row
increment token
expire old active lease if needed
insert new active lease
commit
```

---

# 78. Recommandation

Pour forte clarté :

```text
lease_resources
+
leases history
```

est préférable à `MAX()` concurrent.

---

# 79. Lease acquire transaction

Pseudo-flux :

```sql
BEGIN;

SELECT *
FROM lease_resources
WHERE ...
FOR UPDATE;

SELECT active lease ...

if active and expires_at > now():
    conflict

else:
    increment fencing token
    mark old active lease expired/taken_over
    insert new active lease
COMMIT;
```

---

# 80. Lease renew CAS

```sql
UPDATE leases
SET renewed_at = now(),
    expires_at = now() + $ttl,
    version = version + 1
WHERE lease_id = $lease_id
  AND owner_worker_id = $worker_id
  AND fencing_token = $token
  AND status = 'ACTIVE'
  AND expires_at > now();
```

---

# 81. Lease release

```sql
UPDATE leases
SET status = 'RELEASED',
    released_at = now(),
    version = version + 1
WHERE lease_id = $1
  AND status = 'ACTIVE'
  AND owner_worker_id = $2
  AND fencing_token = $3;
```

---

# 82. Lease expiry

Pas besoin d’un job pour que l’expiration soit effective.

La validité se teste par :

```text
expires_at > now()
```

---

# 83. Lease sweeper

Peut matérialiser :

```text
ACTIVE → EXPIRED
```

pour audit/metrics, mais ne définit pas la vérité temporelle.

---

# 84. Lease indexes

```sql
CREATE INDEX idx_leases_owner
ON leases (owner_worker_id, status);

CREATE INDEX idx_leases_expiry
ON leases (expires_at)
WHERE status = 'ACTIVE';

CREATE INDEX idx_leases_resource_history
ON leases (
  tenant_id,
  resource_type,
  resource_id,
  fencing_token DESC
);
```

---

# 85. Table `runtime_bindings`

```sql
runtime_binding_id UUID PRIMARY KEY,
tenant_id UUID,
runtime_name VARCHAR(128) NOT NULL,
runtime_version VARCHAR(128) NULL,
adapter_name VARCHAR(128) NOT NULL,
adapter_version VARCHAR(128) NULL,
capabilities JSONB NOT NULL DEFAULT '[]'::jsonb,
configuration_reference JSONB NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 86. Runtime binding uniqueness

Peut être :

```text
not globally unique
```

car plusieurs configurations du même runtime peuvent exister.

---

# 87. Table `runtime_invocations`

```sql
runtime_invocation_id UUID PRIMARY KEY,
tenant_id UUID,
run_id UUID NOT NULL,
runtime_binding_id UUID NOT NULL,
worker_id UUID NULL,
lease_id UUID NULL,
fencing_token BIGINT NULL,
invocation_type VARCHAR(64) NOT NULL,
status VARCHAR(32) NOT NULL,
runtime_handle JSONB NULL,
runtime_checkpoint_ref JSONB NULL,
started_at TIMESTAMPTZ NULL,
completed_at TIMESTAMPTZ NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
version BIGINT NOT NULL DEFAULT 0,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 88. Runtime invocation status

```text
CREATED
STARTED
WAITING
COMPLETED
FAILED
CANCELLED
```

---

# 89. Runtime invocation indexes

```sql
CREATE INDEX idx_runtime_invocations_run
ON runtime_invocations (run_id, created_at);

CREATE INDEX idx_runtime_invocations_status
ON runtime_invocations (status);
```

---

# 90. Runtime handle

Conservé comme :

```text
opaque JSONB
```

mais versionné et namespacé si nécessaire.

---

# 91. Table `artifacts`

```sql
artifact_id UUID PRIMARY KEY,
tenant_id UUID,
run_id UUID NULL,
effect_id UUID NULL,
kind VARCHAR(128) NOT NULL,
status VARCHAR(32) NOT NULL,
storage_uri TEXT NOT NULL,
content_type VARCHAR(255) NULL,
size_bytes BIGINT NULL,
checksum_algorithm VARCHAR(32) NULL,
checksum_value VARCHAR(256) NULL,
created_at TIMESTAMPTZ NOT NULL,
activated_at TIMESTAMPTZ NULL,
deleted_at TIMESTAMPTZ NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 92. Artifact status

```text
CREATED
STORED
ACTIVE
FAILED
DELETED
```

---

# 93. Artifact checksum index

Option :

```sql
CREATE INDEX idx_artifacts_checksum
ON artifacts (checksum_algorithm, checksum_value);
```

---

# 94. Artifact storage URI

Ne doit pas contenir :

```text
secret query parameters
signed URLs long-lived
```

Préférer une référence interne durable.

---

# 95. Table `audit_events`

```sql
audit_event_id UUID PRIMARY KEY,
tenant_id UUID,
event_name VARCHAR(255) NOT NULL,
object_type VARCHAR(128) NOT NULL,
object_id VARCHAR(512) NOT NULL,
run_id UUID NULL,
effect_id UUID NULL,
approval_id UUID NULL,
lease_id UUID NULL,
worker_id UUID NULL,
actor_reference JSONB NULL,
principal_reference JSONB NULL,
correlation_id VARCHAR(128) NULL,
trace_id VARCHAR(64) NULL,
reason TEXT NULL,
before_state JSONB NULL,
after_state JSONB NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
created_at TIMESTAMPTZ NOT NULL
```

---

# 96. Audit append-only

Application role :

```text
INSERT + SELECT
```

idéalement sans :

```text
UPDATE / DELETE
```

---

# 97. Audit indexes

```sql
CREATE INDEX idx_audit_object
ON audit_events (object_type, object_id, created_at);

CREATE INDEX idx_audit_run
ON audit_events (run_id, created_at);

CREATE INDEX idx_audit_effect
ON audit_events (effect_id, created_at);

CREATE INDEX idx_audit_created
ON audit_events (created_at);
```

---

# 98. Audit partitioning

À envisager si volume important :

```text
range partition by created_at
```

---

# 99. Audit retention

Partitioning peut simplifier :

```text
archival
retention
```

---

# 100. Tamper-evident extension

Colonnes futures :

```text
previous_hash
event_hash
signature
```

---

# 101. Table `outbox_events`

```sql
outbox_event_id UUID PRIMARY KEY,
tenant_id UUID,
event_name VARCHAR(255) NOT NULL,
aggregate_type VARCHAR(128) NULL,
aggregate_id VARCHAR(512) NULL,
payload JSONB NOT NULL,
status VARCHAR(32) NOT NULL,
attempt_count INTEGER NOT NULL DEFAULT 0,
next_attempt_at TIMESTAMPTZ NULL,
created_at TIMESTAMPTZ NOT NULL,
published_at TIMESTAMPTZ NULL,
last_error JSONB NULL
```

---

# 102. Outbox status

```text
PENDING
PUBLISHED
FAILED
DEAD_LETTER
```

---

# 103. Outbox index

```sql
CREATE INDEX idx_outbox_pending
ON outbox_events (next_attempt_at, created_at)
WHERE status IN ('PENDING', 'FAILED');
```

---

# 104. Outbox worker claim

Utiliser :

```sql
FOR UPDATE SKIP LOCKED
```

pour paralléliser des publishers.

---

# 105. Outbox query

```sql
SELECT *
FROM outbox_events
WHERE status IN ('PENDING', 'FAILED')
  AND (next_attempt_at IS NULL OR next_attempt_at <= now())
ORDER BY created_at
FOR UPDATE SKIP LOCKED
LIMIT $1;
```

---

# 106. Table `inbox_events`

```sql
inbox_event_id UUID PRIMARY KEY,
tenant_id UUID,
source VARCHAR(128) NOT NULL,
external_event_id VARCHAR(512) NOT NULL,
event_name VARCHAR(255) NULL,
payload_hash VARCHAR(128) NULL,
status VARCHAR(32) NOT NULL,
received_at TIMESTAMPTZ NOT NULL,
processed_at TIMESTAMPTZ NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 107. Inbox uniqueness

```sql
UNIQUE(tenant_id, source, external_event_id)
```

---

# 108. Inbox status

```text
RECEIVED
PROCESSING
PROCESSED
FAILED
```

---

# 109. Inbox indexes

```sql
CREATE INDEX idx_inbox_status
ON inbox_events (status, received_at);
```

---

# 110. Actor storage

Le modèle peut choisir :

```text
actors
```

comme table dédiée.

---

# 111. Table `actors`

Candidate :

```sql
actor_id UUID PRIMARY KEY,
tenant_id UUID,
actor_type VARCHAR(32) NOT NULL,
display_name VARCHAR(255) NULL,
external_reference JSONB NULL,
created_at TIMESTAMPTZ NOT NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 112. Principal storage

Optionnel :

```text
principal identity
```

peut rester externe et être stockée comme référence JSONB dans Audit/Approval.

---

# 113. Table `approval_votes`

À introduire seulement si multi-approval/quorum devient requis.

Candidate :

```sql
approval_vote_id UUID PRIMARY KEY,
approval_id UUID NOT NULL,
actor_id UUID NOT NULL,
decision VARCHAR(32) NOT NULL,
reason TEXT NULL,
decided_at TIMESTAMPTZ NOT NULL,
UNIQUE(approval_id, actor_id)
```

---

# 114. Quorum state

Le calcul du quorum reste service métier.

---

# 115. Table `connector_configs`

Option future si connectors configurés durablement :

```sql
connector_config_id UUID PRIMARY KEY,
tenant_id UUID,
connector_name VARCHAR(128) NOT NULL,
provider VARCHAR(128) NOT NULL,
status VARCHAR(32) NOT NULL,
settings JSONB NOT NULL,
secret_references JSONB NOT NULL,
created_at TIMESTAMPTZ NOT NULL,
updated_at TIMESTAMPTZ NOT NULL,
version BIGINT NOT NULL DEFAULT 0
```

---

# 116. Connector secrets

`secret_references` seulement.

Jamais les valeurs résolues.

---

# 117. Table `coding_workspaces`

Option extension coding-agent :

```sql
workspace_id UUID PRIMARY KEY,
tenant_id UUID,
run_id UUID NOT NULL,
repository_reference JSONB NULL,
branch_reference JSONB NULL,
status VARCHAR(32) NOT NULL,
isolation_level VARCHAR(32) NOT NULL,
workspace_reference JSONB NOT NULL,
created_at TIMESTAMPTZ NOT NULL,
expires_at TIMESTAMPTZ NULL,
metadata JSONB NOT NULL DEFAULT '{}'::jsonb
```

---

# 118. Core vs extension tables

Les tables coding/connectors peuvent rester dans packages d’extension.

---

# 119. Foreign key strategy

Utiliser des FK pour les relations internes fortes.

Exemples :

```text
runs.session_id
effects.run_id
approvals.run_id
checkpoints.run_id
runtime_invocations.run_id
```

---

# 120. ON DELETE policy

Préférence :

```text
RESTRICT
```

ou :

```text
NO ACTION
```

sur objets critiques.

---

# 121. Cascading delete

À éviter pour :

```text
Run
Effect
Approval
Audit
Lease
```

---

# 122. Artifact cascade

Même principe :

```text
metadata should not vanish silently
```

---

# 123. Retention deletion

Doit passer par processus explicite, pas cascade accidentelle.

---

# 124. Index naming

Convention :

```text
idx_<table>_<columns>
uq_<table>_<purpose>
fk_<table>_<target>
```

---

# 125. Constraint naming

Toujours nommer les contraintes critiques.

---

# 126. Check constraints

Exemples :

```text
status values
risk values
non-negative attempt_count
size_bytes >= 0
expires_at > acquired_at
```

---

# 127. Lease temporal check

Candidate :

```sql
CHECK (expires_at > acquired_at)
```

---

# 128. Outbox attempt check

```sql
CHECK (attempt_count >= 0)
```

---

# 129. Artifact size check

```sql
CHECK (size_bytes IS NULL OR size_bytes >= 0)
```

---

# 130. Effect timing consistency

Exemples :

```text
completed_at >= started_at
```

si les deux sont non-null.

---

# 131. Partial constraints vs service rules

Certaines règles sont trop complexes pour CHECK.

Exemple :

```text
Approval scope matches Effect fingerprint
```

reste dans domaine/service.

---

# 132. Domain Rule vs DB Constraint

Règle :

```text
DB protects impossible physical states
Domain protects semantic transitions
```

---

# 133. Enum strategy

Préférence initiale :

```text
VARCHAR + CHECK
```

plutôt que PostgreSQL ENUM.

---

# 134. Pourquoi pas DB ENUM partout

Parce que :

```text
schema evolution harder
rolling upgrades harder
```

---

# 135. Enum migrations

Avec CHECK :

```text
expand allowed values
deploy code
contract if needed
```

---

# 136. Transaction boundaries

Transactions locales importantes :

```text
Run transition + Checkpoint
Approval decision + Audit + Outbox
Effect state + ExternalReference
Lease takeover + Fencing generation
Inbox claim + command creation
```

---

# 137. Never hold transaction around LLM

Interdit :

```text
BEGIN
call LLM
COMMIT
```

---

# 138. Never hold transaction around external Effect

Interdit :

```text
BEGIN
call external API
COMMIT
```

---

# 139. Effect transaction pattern

```text
transaction 1:
reserve Effect
commit

external call

transaction 2:
persist outcome
commit
```

---

# 140. Unknown outcome pattern

Si crash/timeout après external call :

```text
Effect remains STARTED
```

puis recovery peut passer :

```text
UNKNOWN / RECONCILIATION_REQUIRED
```

---

# 141. Run + Checkpoint transaction

Possible :

```text
update Run
insert Checkpoint
insert AuditEvent
commit
```

---

# 142. Approval decision transaction

Possible :

```text
update Approval
insert AuditEvent
insert OutboxEvent
commit
```

---

# 143. Lease takeover transaction

Doit être unique et sérialisée sur la ressource.

---

# 144. Isolation level

Recommandation par défaut :

```text
READ COMMITTED
```

---

# 145. SERIALIZABLE

Réservé si vraiment nécessaire.

---

# 146. Row locks

Utiliser :

```text
SELECT ... FOR UPDATE
```

pour coordination ciblée.

---

# 147. SKIP LOCKED

Utiliser pour :

```text
outbox workers
work queues
reconciliation workers
```

si pertinent.

---

# 148. NOWAIT

Peut être utile pour éviter attente de lock non bornée.

---

# 149. Lock timeout

Configurer :

```text
lock_timeout
```

---

# 150. Statement timeout

Configurer :

```text
statement_timeout
```

selon workload.

---

# 151. Deadlock handling

Une transaction abortée avant commit peut être retriée si sûre.

---

# 152. Serialization retry

Même principe.

---

# 153. DB retry boundary

Retry local DB :

```text
safe
```

tant qu’aucun external Effect n’est rejoué.

---

# 154. Connection pooling

Pool borné :

```text
min size
max size
timeout
```

---

# 155. Pool metrics

```text
in_use
idle
waiters
wait_time
```

---

# 156. Application name

Configurer :

```text
application_name = 'pyagentskit-worker'
```

ou nom de composant.

---

# 157. Multi-tenant strategy

Trois options :

```text
shared tables + tenant_id
RLS
separate databases
```

---

# 158. MVP multi-tenant

Recommandation :

```text
shared tables + tenant_id
```

avec application-level filters.

---

# 159. RLS option

Peut renforcer la sécurité.

---

# 160. RLS example

```sql
CREATE POLICY tenant_isolation
ON runs
USING (
  tenant_id = current_setting('app.tenant_id')::uuid
);
```

---

# 161. RLS caveat

La connexion doit définir :

```text
app.tenant_id
```

de façon sûre.

---

# 162. RLS bypass role

Admin/migration peut avoir rôle distinct.

---

# 163. Tenant id NOT NULL

En mode multi-tenant production :

```text
tenant_id NOT NULL
```

préférable pour objets tenant-scoped.

---

# 164. Single-tenant mode

Peut utiliser :

```text
default tenant UUID
```

pour conserver les mêmes contraintes.

---

# 165. Unique constraints and tenant

Toutes les contraintes logiques tenant-scoped doivent inclure :

```text
tenant_id
```

---

# 166. Example idempotency uniqueness

```sql
UNIQUE (
  tenant_id,
  idempotency_scope,
  idempotency_key
)
```

---

# 167. Example inbox uniqueness

```sql
UNIQUE (
  tenant_id,
  source,
  external_event_id
)
```

---

# 168. Example active lease uniqueness

```sql
UNIQUE (
  tenant_id,
  resource_type,
  resource_id
)
WHERE status='ACTIVE'
```

---

# 169. Data encryption

PostgreSQL peut s’appuyer sur :

```text
disk encryption
managed database encryption
TLS
```

---

# 170. Column-level encryption

Réservée aux champs vraiment sensibles.

---

# 171. No secrets

Les tables métier ne stockent pas de credentials résolus.

---

# 172. Audit role

Rôle DB recommandé :

```text
pyagentskit_app
pyagentskit_migrator
pyagentskit_audit_writer
pyagentskit_readonly
```

selon maturité.

---

# 173. Least privilege DB

`pyagentskit_app` ne doit pas avoir :

```text
SUPERUSER
CREATEDB
CREATEROLE
```

---

# 174. Migration role

Peut avoir DDL privileges nécessaires.

---

# 175. Read-only operator role

Peut lire :

```text
Run
Effect
Approval
Lease
Audit
```

sans mutation.

---

# 176. Migration table

Utiliser l’outil choisi :

```text
alembic_version
```

ou équivalent.

---

# 177. Migration strategy

```text
expand
migrate
backfill
switch
contract
```

---

# 178. Rolling deployment compatibility

Les migrations doivent permettre une période :

```text
worker vN
worker vN+1
```

si rolling update.

---

# 179. Backfill

Les backfills lourds doivent être :

```text
bounded
observable
restartable
```

---

# 180. Migration lock

Utiliser un advisory lock ou mécanisme migration tool pour empêcher deux migrations concurrentes.

---

# 181. Migration observability

Audit/log :

```text
migration id
from
to
duration
result
```

---

# 182. Migration failure

Ne pas laisser :

```text
half-applied semantic state
```

sans procédure.

---

# 183. Schema compatibility check

Worker startup :

```text
expected schema version
vs actual schema
```

---

# 184. Incompatible schema

Résultat :

```text
readiness false
```

---

# 185. Backup

PostgreSQL production doit avoir :

```text
backup
restore
PITR
```

selon niveau de service.

---

# 186. Backup content

Inclut :

```text
Effects
Approvals
Fencing state
Audit
Outbox
```

---

# 187. Restore danger

Restaurer un snapshot ancien peut réintroduire :

```text
stale fencing tokens
stale Effect states
stale approvals
```

---

# 188. Post-restore safety gate

Avant reprise :

```text
pause admissions
validate fencing generations
reconcile external Effects
validate approvals
inspect Outbox
```

---

# 189. Fencing after restore

Critique :

```text
restored fencing token must not become lower than external/current authority
```

---

# 190. Restore procedure

Peut nécessiter :

```text
bump fencing generation epoch
```

ou autre stratégie d’ADR.

---

# 191. Point-in-time recovery

Même enjeu.

---

# 192. Read replicas

Utiles pour :

```text
audit queries
reporting
dashboards
```

---

# 193. Read replica restrictions

Ne pas utiliser réplica laggée pour :

```text
lease validation
effect safety
approval finality
```

---

# 194. Authoritative reads

Toujours primary pour :

```text
Lease
Fencing
Effect current state
Approval current state
Run transition
```

---

# 195. Partitioning candidates

Tables susceptibles de forte volumétrie :

```text
audit_events
messages
outbox_events
inbox_events
runtime_invocations
```

---

# 196. Partitioning by time

Option :

```text
monthly range partitions
```

---

# 197. Partitioning caveat

Ne pas complexifier le MVP prématurément.

---

# 198. Vacuum

Surveiller :

```text
autovacuum
bloat
dead tuples
```

---

# 199. HOT updates

Les tables fréquemment mises à jour comme `leases` et `workers` doivent être observées.

---

# 200. Lease write amplification

Les renewals fréquents peuvent générer :

```text
high update volume
```

---

# 201. Lease optimization

Possibilités futures :

```text
separate current lease table
append-only history table
lower index count
fillfactor tuning
```

---

# 202. Worker heartbeat amplification

Même vigilance.

---

# 203. Index discipline

Chaque index :

```text
costs writes
```

Ne pas indexer chaque colonne.

---

# 204. Query-driven indexing

Les indexes doivent être justifiés par :

```text
known query patterns
```

---

# 205. EXPLAIN

Utiliser :

```text
EXPLAIN ANALYZE
```

pour qualification.

---

# 206. Slow query monitoring

Seuil à définir.

---

# 207. Query patterns P0

```text
get Run by id
latest Checkpoint
find Effect by idempotency key
list unresolved Effects
get pending Approvals
acquire/renew Lease
claim Outbox
append AuditEvent
```

---

# 208. Query performance targets

À qualifier avec volumes réalistes.

---

# 209. Table growth projections

À estimer pour :

```text
runs/day
effects/run
audit events/run
messages/conversation
lease renewals/minute
```

---

# 210. Audit volume

Souvent la plus grosse table à long terme.

---

# 211. Audit archival

Peut déplacer vieilles partitions vers stockage moins coûteux.

---

# 212. Artifact metadata volume

Faible par rapport aux blobs eux-mêmes.

---

# 213. Outbox retention

Une fois publié :

```text
retain short-to-medium
```

selon audit/debug.

---

# 214. Inbox retention

Peut être plus courte selon fenêtre de replay provider.

---

# 215. Message retention

Configurable selon tenant/compliance.

---

# 216. GDPR/privacy considerations

Le data model doit permettre :

```text
redaction
pseudonymization
retention
```

sans casser l’audit indispensable.

---

# 217. Actor pseudonymization

Peut remplacer display data tout en conservant un identifiant durable.

---

# 218. Message redaction

Utiliser :

```text
redacted_at
```

et éventuellement contenu remplacé/pseudonymisé selon policy.

---

# 219. Audit privacy

Ne pas stocker des payloads complets par défaut.

---

# 220. Database triggers

À utiliser avec parcimonie.

---

# 221. Good trigger use

Exemple potentiel :

```text
updated_at maintenance
```

mais même cela peut rester applicatif.

---

# 222. Avoid business triggers

Éviter :

```text
trigger automatically approves
trigger automatically creates Effects
trigger runs recovery logic
```

---

# 223. Stored procedures

Pas nécessaires au core initial.

---

# 224. Advisory locks

Utiles pour :

```text
migration lock
rare coordination helpers
```

pas comme substitut universel au LeaseStore.

---

# 225. LISTEN/NOTIFY

Peut servir comme optimisation wake-up.

---

# 226. LISTEN/NOTIFY limitation

Ne doit pas être source de vérité.

---

# 227. Wake-up pattern

```text
persist state
commit
notify
```

Si notification perdue :

```text
polling recovers
```

---

# 228. Outbox + NOTIFY

Peut accélérer les consumers.

---

# 229. Materialized views

Possibles pour :

```text
dashboards
reporting
```

mais pas autoritatives.

---

# 230. Views

Exemples :

```text
v_run_summary
v_unresolved_effects
v_active_leases
v_pending_approvals
```

---

# 231. `v_run_summary`

Peut joindre :

```text
Run
latest Checkpoint
active Lease
pending Approval count
unknown Effect count
```

---

# 232. Read model caveat

Les vues opérateur ne doivent pas être utilisées pour mutations critiques.

---

# 233. Data model invariants

```text
DB-INV-01
Critical relationships are protected by FK.

DB-INV-02
Logical idempotency is protected by unique constraint.

DB-INV-03
At most one authoritative ACTIVE lease per resource.

DB-INV-04
Fencing generation is monotonic.

DB-INV-05
Checkpoints are append-oriented and ordered.

DB-INV-06
AuditEvents are append-oriented.

DB-INV-07
External Effects are never executed inside a DB transaction.

DB-INV-08
Tenant-scoped uniqueness includes tenant_id.

DB-INV-09
Critical reads use authoritative primary state.

DB-INV-10
Secrets are not stored as resolved values.
```

---

# 234. Anti-patterns

À éviter :

```text
one generic table for all objects
all domain state in JSONB
no foreign keys
no unique idempotency constraint
lease without active uniqueness
fencing token generated in worker memory
cascade delete of audit/effects
long DB transaction around LLM/API calls
read replica for lease validation
manual production SQL mutation without audit
```

---

# 235. Contract Tests

Chaque Postgres store doit passer :

```text
RunStoreContract
EffectStoreContract
ApprovalStoreContract
LeaseStoreContract
CheckpointStoreContract
AuditStoreContract
OutboxStoreContract
InboxStoreContract
```

---

# 236. Concurrency Tests

Scénarios :

```text
two Run transitions
two Effect reservations
two Approval decisions
two Lease acquisitions
multiple Outbox workers
```

---

# 237. Crash Tests

Crash autour de :

```text
Effect reserve commit
Approval commit
Lease takeover
Outbox claim
Checkpoint append
```

---

# 238. PostgreSQL Restart Tests

Vérifier :

```text
pool recovery
transaction failure handling
worker readiness
lease revalidation
```

---

# 239. Deadlock Tests

Créer contention réelle et vérifier retry local sûr.

---

# 240. Lock Timeout Tests

Vérifier comportement borné.

---

# 241. Backup/Restore Tests

Après restore :

```text
Run consistency
Effect preservation
Approval preservation
Fencing safety
Audit queryability
Outbox consistency
```

---

# 242. Migration Tests

```text
fresh install
upgrade N→N+1
mixed workers
rollback plan
large backfill
```

---

# 243. Load Tests

Mesurer :

```text
Run creates/sec
Effect reservations/sec
Lease renewals/sec
Audit inserts/sec
Outbox throughput
Checkpoint latency
```

---

# 244. Lease Load Test

Particulièrement critique pour 1.6.0 qualification.

---

# 245. Contention Load Test

N workers sur mêmes ressources.

Mesurer :

```text
lock wait
deadlocks
latency
conflicts
```

---

# 246. Multi-process Test

Minimum :

```text
two independent processes
real PostgreSQL
```

---

# 247. Multi-host Test

À ajouter pour qualification production.

---

# 248. Security Tests

Tester :

```text
least-privilege role
tenant isolation
RLS if enabled
audit update denied
secret absence
```

---

# 249. SQL Injection

Les adapters doivent utiliser :

```text
parameterized queries
```

---

# 250. Schema Search Path

Définir explicitement :

```text
search_path
```

pour éviter ambiguïtés.

---

# 251. Migration Search Path

Même règle.

---

# 252. Connection TLS

Production :

```text
TLS required
```

selon deployment.

---

# 253. Certificate Validation

Ne pas désactiver sans justification.

---

# 254. Database credentials

Doivent être fournis via :

```text
SecretReference / workload identity
```

---

# 255. Connection rotation

Le pool doit tolérer rotation de credentials si backend le permet.

---

# 256. Observability DB

Spans :

```text
db.run.transition
db.effect.reserve
db.lease.acquire
db.lease.renew
db.approval.decide
db.audit.append
```

---

# 257. DB Metrics

```text
db_operation_latency
db_errors_total
db_deadlocks_total
db_pool_wait
lease_renew_latency
```

---

# 258. Audit of manual repairs

Toute réparation manuelle doit créer un AuditEvent.

---

# 259. Repair CLI

Candidate :

```text
pyagentskit db verify
pyagentskit store inspect
pyagentskit store repair --plan
```

---

# 260. Verification Rules

`db verify` peut vérifier :

```text
duplicate active leases
fencing monotonicity
orphan Effects
orphan Checkpoints
invalid Approval states
missing external references
outbox backlog
```

---

# 261. Repair plan

Avant mutation :

```text
dry-run
```

obligatoire ou fortement recommandé.

---

# 262. Repair authorization

Admin-only.

---

# 263. Repair audit

Doit enregistrer :

```text
who
what
why
before
after
```

---

# 264. Reference ERD — core

```text
sessions
   │
   ├── runs
   │    ├── checkpoints
   │    ├── effects
   │    │    └── reconciliation_cases
   │    ├── approvals
   │    ├── artifacts
   │    └── runtime_invocations
   │
   ├── conversations
   │    ├── participants
   │    └── messages
   │         └── message_recipients
   │
   └── memory_entries

workers
   └── leases

runtime_bindings
   └── runtime_invocations

audit_events
outbox_events
inbox_events
```

---

# 265. Reference ERD — coordination

```text
lease_resources
   │
   └── leases
        │
        └── workers
```

---

# 266. Reference ERD — Effects

```text
runs
  │
  └── effects
       ├── reconciliation_cases
       ├── approvals
       └── artifacts
```

---

# 267. Reference ERD — conversation

```text
sessions
  │
  └── conversations
       ├── participants
       └── messages
            └── message_recipients
```

---

# 268. Example DDL — Run

```sql
CREATE TABLE runs (
    run_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    session_id UUID NULL,
    runtime_binding_id UUID NULL,
    state VARCHAR(32) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    version BIGINT NOT NULL DEFAULT 0,
    correlation_id VARCHAR(128) NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT ck_runs_state CHECK (
        state IN (
            'CREATED',
            'READY',
            'RUNNING',
            'WAITING',
            'PAUSED',
            'SUCCEEDED',
            'FAILED',
            'CANCELLED'
        )
    )
);
```

---

# 269. Example DDL — Effect

```sql
CREATE TABLE effects (
    effect_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    effect_kind VARCHAR(255) NOT NULL,
    status VARCHAR(64) NOT NULL,
    risk_level VARCHAR(32) NOT NULL,
    idempotency_scope VARCHAR(255) NOT NULL,
    idempotency_key VARCHAR(255) NOT NULL,
    input_fingerprint VARCHAR(128) NOT NULL,
    external_system VARCHAR(128) NULL,
    external_reference_kind VARCHAR(128) NULL,
    external_reference_value VARCHAR(512) NULL,
    started_at TIMESTAMPTZ NULL,
    completed_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    version BIGINT NOT NULL DEFAULT 0,
    ownership_context JSONB NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT uq_effect_idempotency
    UNIQUE (tenant_id, idempotency_scope, idempotency_key)
);
```

---

# 270. Example DDL — Lease Resource

```sql
CREATE TABLE lease_resources (
    tenant_id UUID NOT NULL,
    resource_type VARCHAR(128) NOT NULL,
    resource_id VARCHAR(512) NOT NULL,
    current_fencing_token BIGINT NOT NULL DEFAULT 0,
    version BIGINT NOT NULL DEFAULT 0,

    PRIMARY KEY (tenant_id, resource_type, resource_id)
);
```

---

# 271. Example DDL — Lease

```sql
CREATE TABLE leases (
    lease_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    resource_type VARCHAR(128) NOT NULL,
    resource_id VARCHAR(512) NOT NULL,
    owner_worker_id UUID NOT NULL REFERENCES workers(worker_id),
    status VARCHAR(32) NOT NULL,
    fencing_token BIGINT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL,
    renewed_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    released_at TIMESTAMPTZ NULL,
    version BIGINT NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT ck_lease_expiry
    CHECK (expires_at > acquired_at),

    CONSTRAINT uq_lease_generation
    UNIQUE (
        tenant_id,
        resource_type,
        resource_id,
        fencing_token
    )
);
```

---

# 272. Active Lease Index DDL

```sql
CREATE UNIQUE INDEX uq_leases_active_resource
ON leases (tenant_id, resource_type, resource_id)
WHERE status = 'ACTIVE';
```

---

# 273. Example DDL — Approval

```sql
CREATE TABLE approvals (
    approval_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    effect_id UUID NULL REFERENCES effects(effect_id),
    status VARCHAR(32) NOT NULL,
    scope JSONB NOT NULL,
    scope_fingerprint VARCHAR(128) NULL,
    requested_by_actor_id UUID NULL,
    decided_by_actor_id UUID NULL,
    decision VARCHAR(32) NULL,
    reason TEXT NULL,
    policy_id VARCHAR(255) NULL,
    policy_version VARCHAR(64) NULL,
    requested_at TIMESTAMPTZ NOT NULL,
    decided_at TIMESTAMPTZ NULL,
    expires_at TIMESTAMPTZ NULL,
    cancelled_at TIMESTAMPTZ NULL,
    version BIGINT NOT NULL DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
```

---

# 274. Example DDL — Checkpoint

```sql
CREATE TABLE checkpoints (
    checkpoint_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    run_id UUID NOT NULL REFERENCES runs(run_id),
    sequence BIGINT NOT NULL,
    checkpoint_type VARCHAR(64) NOT NULL,
    schema_version VARCHAR(32) NOT NULL,
    state_payload JSONB NOT NULL,
    runtime_checkpoint_ref JSONB NULL,
    checksum VARCHAR(128) NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_worker_id UUID NULL REFERENCES workers(worker_id),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,

    CONSTRAINT uq_checkpoint_sequence
    UNIQUE (run_id, sequence)
);
```

---

# 275. Example DDL — Outbox

```sql
CREATE TABLE outbox_events (
    outbox_event_id UUID PRIMARY KEY,
    tenant_id UUID NOT NULL,
    event_name VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(128) NULL,
    aggregate_id VARCHAR(512) NULL,
    payload JSONB NOT NULL,
    status VARCHAR(32) NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    next_attempt_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    published_at TIMESTAMPTZ NULL,
    last_error JSONB NULL
);
```

---

# 276. Query — pending approvals

```sql
SELECT *
FROM approvals
WHERE tenant_id = $1
  AND status = 'PENDING'
  AND (expires_at IS NULL OR expires_at > now())
ORDER BY requested_at;
```

---

# 277. Query — unresolved Effects

```sql
SELECT *
FROM effects
WHERE tenant_id = $1
  AND status IN ('STARTED', 'UNKNOWN', 'RECONCILIATION_REQUIRED')
ORDER BY updated_at;
```

---

# 278. Query — expired active leases

```sql
SELECT *
FROM leases
WHERE status = 'ACTIVE'
  AND expires_at <= now();
```

---

# 279. Query — latest checkpoint

```sql
SELECT *
FROM checkpoints
WHERE run_id = $1
ORDER BY sequence DESC
LIMIT 1;
```

---

# 280. Query — Run timeline

```sql
SELECT *
FROM audit_events
WHERE run_id = $1
ORDER BY created_at, audit_event_id;
```

---

# 281. Reference transaction — Effect reserve

```text
BEGIN
↓
INSERT effect intent
↓
if conflict:
  load existing
  compare fingerprint
↓
COMMIT
```

---

# 282. Reference transaction — Approval decision

```text
BEGIN
↓
conditional UPDATE Approval
↓
INSERT AuditEvent
↓
INSERT OutboxEvent
↓
COMMIT
```

---

# 283. Reference transaction — Lease takeover

```text
BEGIN
↓
lock lease_resource
↓
validate current lease expiry
↓
increment fencing token
↓
expire/takeover old lease
↓
insert new active lease
↓
INSERT AuditEvent
↓
COMMIT
```

---

# 284. Reference transaction — Run checkpoint

```text
BEGIN
↓
conditional UPDATE Run
↓
INSERT Checkpoint
↓
INSERT AuditEvent
↓
COMMIT
```

---

# 285. Data Model Acceptance Criteria

Le modèle PostgreSQL est opérationnel si :

1. les relations critiques possèdent des FK ;
2. les Effects possèdent une contrainte d’idempotency ;
3. les checkpoints sont ordonnés et append-oriented ;
4. un seul lease ACTIVE existe par ressource ;
5. le fencing token est généré de manière monotone ;
6. les Approval decisions sont concurrency-safe ;
7. AuditEvent est append-oriented ;
8. Outbox/Inbox possèdent des contraintes de déduplication ;
9. le multi-tenancy est inclus dans les contraintes critiques ;
10. les queries P0 sont indexées ;
11. aucun external Effect n’est exécuté dans une transaction DB longue ;
12. les stores passent des contract tests réels PostgreSQL ;
13. les migrations sont versionnées ;
14. le restore safety est documenté ;
15. les authoritative reads sont faites sur primary ;
16. les rôles DB appliquent least privilege.

---

# 286. Questions ouvertes

```text
Q-DB-01 UUIDv7 ou UUID4 ?
Q-DB-02 lease_resources séparée obligatoire ?
Q-DB-03 RLS activée par défaut ?
Q-DB-04 Quels tables partitionner dès v1 ?
Q-DB-05 AuditStore dans même schema ?
Q-DB-06 VARCHAR+CHECK ou ENUM PostgreSQL ?
Q-DB-07 Actor table obligatoire ?
Q-DB-08 ApprovalVote dès v1 ?
Q-DB-09 coding_workspaces dans core ou extension ?
Q-DB-10 stratégie post-restore fencing ?
Q-DB-11 quel outil migration officiel ?
Q-DB-12 quelle politique d’archivage audit ?
```

---

# 287. ADR induits

```text
ADR-DB-001 Primary key strategy
ADR-DB-002 Schema layout
ADR-DB-003 Tenant model
ADR-DB-004 Lease resource counter
ADR-DB-005 Effect idempotency constraint
ADR-DB-006 Checkpoint immutability
ADR-DB-007 Approval persistence
ADR-DB-008 Audit storage
ADR-DB-009 Outbox/Inbox schema
ADR-DB-010 Enum strategy
ADR-DB-011 Partitioning strategy
ADR-DB-012 Backup/restore fencing safety
ADR-DB-013 DB roles and permissions
ADR-DB-014 Migration tool
```

---

# 288. Definition of Done

Le PostgreSQL Data Model est mature lorsque :

1. les migrations créent l’ensemble des tables P0 ;
2. les contraintes d’unicité critiques sont testées ;
3. les transactions de référence sont implémentées ;
4. les CAS transitions sont testées ;
5. le LeaseStore passe des tests concurrentiels réels ;
6. les fencing tokens restent strictement monotones ;
7. l’EffectStore résiste aux réservations concurrentes ;
8. l’ApprovalStore résiste aux décisions concurrentes ;
9. les checkpoints sont immuables ;
10. l’AuditStore est append-oriented ;
11. Outbox utilise `SKIP LOCKED` ou mécanisme équivalent ;
12. Inbox déduplique les événements externes ;
13. les indexes P0 sont validés par `EXPLAIN ANALYZE` ;
14. les rôles DB least-privilege sont documentés ;
15. backup/restore et PITR sont qualifiés ;
16. les migrations mixed-version sont testées ;
17. la safe degradation en panne PostgreSQL est conforme ;
18. la qualification utilise plusieurs processus réels.

---

# 289. Résumé

Le modèle PostgreSQL de PyAgentsKit repose sur :

```text
STRONG RELATIONAL CONSTRAINTS
+
OPTIMISTIC CONCURRENCY
+
TARGETED ROW LOCKS
+
IDEMPOTENCY UNIQUENESS
+
MONOTONIC FENCING
+
APPEND-ORIENTED CHECKPOINTS
+
APPEND-ORIENTED AUDIT
+
OUTBOX / INBOX
+
TENANT-SCOPED INDEXES
```

Les règles structurantes sont :

```text
DB constraint
≠
domain transition logic

PostgreSQL transaction
≠
distributed transaction

active lease
≠
worker heartbeat

restore
≠
safe resume
```

Le principe fondamental est :

> **PostgreSQL doit rendre les états impossibles difficiles à représenter, les races critiques détectables, et la reprise durablement reconstructible.**

Le document suivant naturel est :

```text
../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md
```
