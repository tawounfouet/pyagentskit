# PyAgentsKit — V1 to V2 Migration Strategy

**Document :** `../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Migration Architecture — V1.6 → V2  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../strategy/PYAGENTSKIT_EXISTING_VS_TARGET_GAP_ANALYSIS_2026-10-21.md`
- `../architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`

---

# 1. Objet

Ce document définit la stratégie de migration de PyAgentsKit V1.6 vers PyAgentsKit V2.

L’objectif n’est pas de réécrire le projet.

L’objectif est de **transformer progressivement un runtime agentique provider-neutral en Agent Reliability Layer framework-neutral**, tout en conservant les garanties déjà acquises.

Le principe directeur est :

> **La V1 reste stable pendant que la V2 se construit autour d’elle, puis derrière elle, puis à sa place là où cela apporte une vraie valeur.**

---

# 2. Pourquoi une stratégie dédiée

La V1.6 possède déjà des garanties importantes :

```text
bounded mono-agent execution
provider-neutral Model abstraction
Tool execution policies
durable Runs
Effects
UNKNOWN effect handling
Approvals
Sessions
Memory
Artifacts
Lease
Fencing
DistributedDurableRunner
PostgreSQL stores
OpenTelemetry
failure qualification
```

La V2 change plusieurs significations fondamentales :

```text
Run != RuntimeInvocation
Session != Conversation
ToolCall != Effect
Runtime Adapter != Model Adapter
Approval != Authorization
AuditEvent != RuntimeEvent
WAITING != terminal
```

Une migration naïve casserait donc des contrats sémantiques, même si les signatures Python restaient identiques.

---

# 3. Nature de la migration

La migration est de type :

```text
STRANGLER FIG PATTERN
```

et non :

```text
BIG BANG REWRITE
```

---

# 4. Vue générale

```text
Phase 0
V1.6 stable

Phase 1
V2 packages appear beside V1

Phase 2
V1 Runner wrapped by NativeRuntimeAdapter

Phase 3
V2 domain/application starts owning new workflows

Phase 4
Persistence V2 introduced

Phase 5
V1 data migrated

Phase 6
Public V2 API becomes primary

Phase 7
Legacy V1 internals progressively deprecated
```

---

# 5. Objectifs de migration

```text
MIG-OBJ-01
Preserve V1.6 public compatibility during 1.6.x.

MIG-OBJ-02
Avoid semantic overloading of V1 types.

MIG-OBJ-03
Allow V1 and V2 to coexist.

MIG-OBJ-04
Allow incremental data migration.

MIG-OBJ-05
Preserve Effect safety.

MIG-OBJ-06
Preserve Approval decisions.

MIG-OBJ-07
Preserve Lease/Fencing correctness.

MIG-OBJ-08
Keep main branch releasable.

MIG-OBJ-09
Enable rollback/forward-fix.

MIG-OBJ-10
Make each migration step independently testable.
```

---

# 6. Non-objectifs

Cette stratégie ne cherche pas à :

```text
maintain V1 internals forever
preserve every private module path
reproduce all V1 semantics inside V2
ship all V2 features in one release
support downgrade after irreversible data migration without constraints
```

---

# 7. Principle — Compatibility boundary

La compatibilité est une frontière.

Elle ne doit pas devenir une contrainte de design permanente.

```text
V1 compatibility
= adapter boundary

not

V2 semantic model
```

---

# 8. Principle — No semantic smuggling

Ne pas cacher la V2 dans les objets V1 via :

```text
metadata["v2_runtime"]
metadata["conversation_id"]
metadata["effect_kind"]
metadata["ownership_context"]
```

Les concepts structurants méritent des types V2 explicites.

---

# 9. Principle — No dual meaning

Interdit qu’une même classe signifie deux choses selon le contexte.

Exemple :

```text
Session V1 = conversation identity
Session V2 = durable global context
```

Donc elles doivent coexister temporairement comme types distincts.

---

# 10. Migration layers

La migration se fait sur cinq axes :

```text
A. Code topology
B. Domain model
C. Public API
D. Persistence/data
E. Operations/deployment
```

---

# 11. Migration roadmap

```text
Stage A — Freeze V1
Stage B — Create V2 skeleton
Stage C — Wrap V1 runtime
Stage D — Introduce V2 semantics
Stage E — Introduce V2 persistence
Stage F — Dual-read / controlled-write migration
Stage G — Public V2 adoption
Stage H — V1 deprecation
Stage I — Legacy removal
```

---

# 12. Stage A — Freeze V1

## Objectif

Définir exactement ce qui doit rester compatible.

## À figer

```text
root exports
public class names
public method signatures
RunStatus V1
Message V1 schema
Session V1 schema
Approval V1 schema
provider constructors
serialized contracts
```

## Evidence

```text
../compatibility/V1_API_STABILITY.md
compatibility tests
API snapshots
serialization golden files
```

---

# 13. V1 compatibility manifest

Créer un manifest machine-readable si utile :

```text
public exports
enum values
schema hashes
signature hashes
```

---

# 14. V1 maintenance policy

Pendant migration :

```text
1.6.x
```

reçoit :

```text
security fixes
bug fixes
critical production fixes
compatibility fixes
```

Pas de nouvelles features structurelles.

---

# 15. Stage B — V2 skeleton

Créer sans modifier V1 :

```text
src/pyagentskit/domain/
src/pyagentskit/application/
src/pyagentskit/adapters/
src/pyagentskit/api/
src/pyagentskit/bootstrap/
src/pyagentskit/compat/
```

---

# 16. V2 namespace strategy

Option recommandée :

```text
internal topology V2
```

dans les nouveaux packages, tout en gardant les imports publics V1 existants.

---

# 17. No root export explosion

Ne pas réexporter immédiatement tous les types V2 dans :

```text
pyagentskit.__init__
```

Privilégier :

```text
pyagentskit.api
pyagentskit.contracts
```

---

# 18. Stage C — Wrap V1 Runner

Créer :

```text
NativeRuntimeAdapter
```

qui encapsule :

```text
current Runner
```

---

# 19. NativeRuntimeAdapter goal

Prouver que :

```text
V2 Application
can drive
V1 Runner
through
AgentRuntimeAdapter
```

sans modifier le comportement V1.

---

# 20. Native Runtime ACL

Le mapping doit traduire :

```text
V1 Runner result
→ RuntimeStatus

V1 session/run handles
→ RuntimeHandle

V1 events
→ RuntimeEvent

V1 checkpoint
→ RuntimeCheckpoint
```

---

# 21. Compatibility invariant

```text
MIG-INV-01
V1 caller behavior remains unchanged when NativeRuntimeAdapter is introduced.
```

---

# 22. Stage D — Introduce V2 domain semantics

Créer les nouveaux types :

```text
Run V2
RuntimeInvocation
Session V2
Conversation
ConversationMessage
Effect V2
Approval V2
OwnershipContext
RuntimeDescriptor
```

---

# 23. V1/V2 type coexistence

Pendant transition :

```text
V1 RunStatus
!=
V2 RunState
```

```text
V1 Message
!=
V2 ConversationMessage
```

```text
V1 Session
!=
V2 Session
```

si nécessaire, utiliser des namespaces explicites.

---

# 24. V1 RunStatus mapping

Mapping recommandé :

| V1 | V2 |
|---|---|
| CREATED | CREATED |
| RUNNING | RUNNING |
| WAITING_APPROVAL | WAITING + blocker APPROVAL_REQUIRED |
| COMPLETED | SUCCEEDED |
| FAILED | FAILED |
| CANCELLED | CANCELLED |
| LIMIT_EXCEEDED | FAILED or policy-specific terminal reason |
| UNKNOWN_EFFECT | WAITING + Effect.UNKNOWN |

---

# 25. WAITING_APPROVAL migration

Ne pas conserver :

```text
WAITING_APPROVAL
```

comme état métier V2.

Représenter :

```text
RunState.WAITING
+
RecoveryBlocker.APPROVAL_REQUIRED
```

---

# 26. UNKNOWN_EFFECT migration

Ne pas conserver :

```text
UNKNOWN_EFFECT
```

comme état métier du Run.

Représenter :

```text
RunState.WAITING
+
EffectStatus.UNKNOWN
+
RecoveryBlocker.UNKNOWN_EFFECT
```

---

# 27. LIMIT_EXCEEDED migration

Doit être requalifié.

Possibilités :

```text
Run FAILED with reason LIMIT_EXCEEDED
```

ou un `TerminationReason`.

Ne pas multiplier les RunState pour chaque cause.

---

# 28. Run vs RuntimeInvocation migration

V1 mélange partiellement :

```text
logical run
process/runtime invocation
```

V2 sépare :

```text
Run
RuntimeInvocation
```

Migration :

```text
existing V1 run
→ one V2 Run
→ one initial RuntimeInvocation
```

si aucune reprise historique détaillée n’est disponible.

---

# 29. Session migration

V1 Session peut contenir des éléments conversationnels.

Migration doit déterminer :

```text
session identity
conversation thread
message history
memory
```

et les répartir.

---

# 30. Session migration policy

Si V1 n’a qu’un thread logique :

```text
1 V1 Session
→ 1 V2 Session
→ 1 default Conversation
```

---

# 31. Multiple conversation inference

Ne pas inventer artificiellement plusieurs Conversations si la V1 ne fournit pas de preuve.

---

# 32. Message migration

V1 Message :

```text
SYSTEM
USER
ASSISTANT
TOOL
```

peut être classé :

```text
RuntimeMessage
```

et éventuellement projeté vers :

```text
ConversationMessage
```

selon sémantique.

---

# 33. Tool messages

Les messages de rôle `TOOL` ne doivent pas automatiquement devenir des messages humains/agents durables.

---

# 34. Actor migration

V1 identités éventuelles :

```text
user
agent
system
```

peuvent être converties en `ActorReference`.

---

# 35. Approval migration

V1 Approval statuses :

```text
PENDING
APPROVED
REJECTED
CANCELLED
CLAIMED
EXECUTED
EXPIRED
```

V2 décision :

```text
PENDING
APPROVED
REJECTED
CANCELLED
EXPIRED
```

---

# 36. Approval CLAIMED mapping

`CLAIMED` doit être interprété comme :

```text
decision APPROVED
+
consumption/execution state elsewhere
```

selon données disponibles.

---

# 37. Approval EXECUTED mapping

Même principe :

```text
Approval decision
+
Effect/Execution evidence
```

---

# 38. Approval safety invariant

```text
MIG-INV-02
Migration never creates an Approval that did not durably exist in V1.
```

---

# 39. Effect migration

V1 :

```text
PLANNED
STARTED
COMPLETED
FAILED
UNKNOWN
```

V2 :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

# 40. Effect status mapping

| V1 | V2 |
|---|---|
| PLANNED | NOT_STARTED or STARTED depending durable-send semantics |
| STARTED | STARTED |
| COMPLETED | SUCCEEDED |
| FAILED | FAILED |
| UNKNOWN | UNKNOWN |

---

# 41. PLANNED ambiguity

Le mapping de `PLANNED` doit être décidé selon la sémantique V1 réelle :

```text
intent durable but not sent
→ NOT_STARTED

request potentially initiated
→ STARTED
```

---

# 42. Effect success invariant

```text
MIG-INV-03
A V1 COMPLETED Effect migrated to V2 SUCCEEDED must never be replayed.
```

---

# 43. Effect UNKNOWN invariant

```text
MIG-INV-04
A V1 UNKNOWN Effect remains unresolved after migration until reconciliation.
```

---

# 44. Idempotency migration

Conserver :

```text
idempotency_key
fingerprint
```

sans régénération arbitraire.

---

# 45. ExternalReference migration

Si V1 stocke provider IDs dans metadata/tool result :

```text
extract only when semantically reliable
```

Sinon :

```text
leave ExternalReference absent
```

et ne pas inventer.

---

# 46. Checkpoint migration

V1 checkpoints doivent être conservés comme :

```text
legacy/native checkpoint
```

ou transformés si mapping fiable.

---

# 47. Checkpoint versioning

Ajouter :

```text
checkpoint_format
checkpoint_version
runtime_type
```

si nécessaire.

---

# 48. Checkpoint safety rule

Un checkpoint migré ne doit jamais écraser :

```text
Effect truth
Approval truth
Lease/fencing truth
```

---

# 49. Lease migration

La coordination V1 est déjà proche de la cible.

Conserver :

```text
resource_id
owner_id
lease_id
fencing_token
expires_at
```

---

# 50. Fencing migration

Règle critique :

```text
new fencing generation
must never reuse
an already-issued token
```

---

# 51. Fencing epoch migration

Si nouveau schéma :

```text
initialize new counter >= max historical token
```

pour chaque resource identity.

---

# 52. Worker migration

V1 worker state peut être projeté vers V2.

Historique incomplet acceptable si audit clair.

---

# 53. Artifact migration

Séparer :

```text
artifact metadata
blob content
```

si V1 ne le faisait pas déjà complètement.

---

# 54. Audit migration

Les anciens JSONL/telemetry events ne doivent pas être requalifiés automatiquement comme AuditEvents autoritatifs.

---

# 55. Audit bootstrap rule

On peut importer des événements historiques comme :

```text
legacy evidence
```

mais avec provenance explicite.

---

# 56. Stage E — V2 persistence

Introduire le schéma normalisé.

Tables cibles :

```text
sessions
runs
conversations
participants
messages
memory_entries
checkpoints
effects
reconciliation_cases
approvals
workers
lease_resources
leases
runtime_bindings
runtime_invocations
artifacts
audit_events
outbox_events
inbox_events
```

---

# 57. Persistence migration approach

Utiliser :

```text
expand
backfill
verify
switch
contract
```

---

# 58. Expand

Créer les nouvelles tables sans supprimer les anciennes.

---

# 59. Backfill

Copier/transformer les données V1 vers V2.

Le backfill doit être :

```text
restartable
idempotent
chunked
observable
```

---

# 60. Verify

Comparer :

```text
row counts
logical counts
status distributions
effect fingerprints
approval decisions
fencing maxima
artifact checksums
```

---

# 61. Switch

Basculer progressivement les reads/writes.

---

# 62. Contract

Supprimer les anciennes structures uniquement après période de stabilité.

---

# 63. Dual-write policy

Par défaut :

```text
avoid long-lived dual writes
```

car ils créent :

```text
consistency risk
failure ambiguity
complex rollback
```

---

# 64. Controlled dual-write

Si nécessaire temporairement :

```text
one authoritative write
+
derived projection/write
```

avec Outbox/reconciliation.

---

# 65. Source of truth during migration

À chaque phase, une source de vérité doit être explicitement définie.

Jamais :

```text
both V1 and V2 equally authoritative
```

---

# 66. Phase source-of-truth table

| Phase | Source of truth |
|---|---|
| Pre-V2 | V1 |
| V2 shadow/read | V1 |
| Backfill | V1 |
| V2 validation | V1 + comparison |
| V2 cutover | V2 |
| Post-cutover | V2 |

---

# 67. Shadow read

Avant cutover :

```text
read V1
read V2
compare
serve V1
```

sur échantillon ou environnement qualification.

---

# 68. Shadow write

À éviter pour protected business semantics sauf design explicite.

---

# 69. Migration metadata

Chaque objet migré peut porter :

```text
migrated_from_version
migration_batch_id
migration_timestamp
legacy_id
```

si utile.

---

# 70. Legacy IDs

Préserver les IDs historiques lorsque possible.

Sinon conserver mapping :

```text
legacy_id ↔ v2_id
```

---

# 71. ID migration rule

Ne pas régénérer des IDs sans besoin.

Cela complique :

```text
audit
correlation
support
reconciliation
```

---

# 72. Stage F — Dual-read / controlled-write

Le but est de prouver que V2 représente correctement le monde V1 avant bascule.

---

# 73. Comparison suite

Comparer :

```text
Run status
Effect status
Approval state
Lease owner
Fencing token
Session identity
Artifact references
```

---

# 74. Mismatch classification

```text
EXPECTED_MAPPING_DIFFERENCE
MIGRATION_BUG
LEGACY_AMBIGUITY
DATA_CORRUPTION
UNSUPPORTED_CASE
```

---

# 75. No silent mismatch

Tout mismatch non attendu doit être visible.

---

# 76. Migration report

Chaque batch produit :

```text
records scanned
records migrated
records skipped
records ambiguous
records failed
checksums
duration
```

---

# 77. Migration dry-run

Supporter :

```text
--dry-run
```

qui :

```text
reads
maps
validates
reports
```

sans commit.

---

# 78. Migration resume

Supporter reprise après crash.

---

# 79. Migration checkpoint

Conserver :

```text
last processed cursor
batch id
version
```

---

# 80. Migration locking

Éviter deux migrations concurrentes non coordonnées.

---

# 81. Migration lease

Utiliser éventuellement un lease administratif :

```text
migration resource
```

pour éviter concurrence.

---

# 82. Online vs offline migration

Certaines migrations peuvent être online.

D’autres nécessitent :

```text
maintenance window
```

notamment si fencing/source of truth change.

---

# 83. Protected migration mode

Pour bascule finale :

```text
stop new admissions
drain workers
freeze protected effects
snapshot
migrate
verify
switch
resume
```

---

# 84. Migration ordering

Ordre recommandé des données :

```text
1. Sessions
2. Runs
3. Conversations/Messages
4. Checkpoints
5. Effects
6. Approvals
7. Workers/Leases
8. Runtime bindings/invocations
9. Artifacts
10. Audit
11. Outbox/Inbox initialization
```

---

# 85. Why Effects before resume

Aucun Run migré ne doit être repris avant que ses Effects soient migrés et vérifiés.

---

# 86. Why Approvals before resume

Même principe.

---

# 87. Why Fencing before workers

Les workers V2 ne démarrent qu’après validation de l’autorité de fencing.

---

# 88. Stage G — Public V2 adoption

Introduire :

```text
pyagentskit.api
```

comme surface V2.

---

# 89. V2 API strategy

Exemple :

```python
from pyagentskit.api import PyAgentsKit
```

et non remplacement immédiat de tous les imports V1.

---

# 90. Coexistence imports

Pendant migration :

```text
V1 imports
continue to work

V2 imports
explicitly namespaced
```

---

# 91. Public migration guide

Pour chaque API V1 :

```text
old usage
new usage
semantic difference
migration risk
```

---

# 92. Example — Runner migration

V1 :

```python
runner = Runner(...)
result = await runner.run(...)
```

V2 :

```python
kit = PyAgentsKit(...)
run = await kit.runs.create(...)
await kit.runs.start(run.run_id)
```

---

# 93. Example — approval migration

V1 :

```text
resume_approval(...)
```

V2 :

```text
approvals.approve(...)
runs.resume(...)
```

selon API finale.

---

# 94. Example — distributed migration

V1 :

```text
DistributedDurableRunner
```

V2 :

```text
Application + LeaseRepository + AgentRuntimeAdapter
```

---

# 95. Stage H — V1 deprecation

La dépréciation commence uniquement quand :

```text
V2 replacement exists
migration path documented
qualification green
```

---

# 96. Deprecation levels

```text
D0 — supported
D1 — discouraged
D2 — deprecated
D3 — compatibility-only
D4 — removed
```

---

# 97. Deprecation communication

Chaque élément deprecated doit indiquer :

```text
replacement
since version
planned removal
migration doc
```

---

# 98. Stage I — Legacy removal

Possible seulement en major release après période annoncée.

---

# 99. What may remain forever

Certains composants V1 peuvent survivre durablement comme runtime natif :

```text
Runner
Model adapters
Tool executor
Guardrails
```

mais derrière la frontière :

```text
NativeRuntimeAdapter
```

---

# 100. What should not remain core

À terme :

```text
V1-specific RunStatus semantics
V1 monolithic RunStore
Session=Conversation assumption
Effect tied to ToolCall
```

ne doivent plus gouverner V2.

---

# 101. Migration package topology

```text
compat/
└── v1/
    ├── runner.py
    ├── run_status.py
    ├── sessions.py
    ├── approvals.py
    ├── effects.py
    └── mappings.py
```

---

# 102. Migration tooling topology

```text
scripts/
└── migration/
    ├── inspect_v1.py
    ├── dry_run_v2.py
    ├── migrate_postgres.py
    ├── verify_migration.py
    └── rollback_cutover.py
```

---

# 103. Data migration service

Possibilité d’un package interne :

```text
pyagentskit.migration
```

mais ne pas l’exposer comme core domain.

---

# 104. Migration mapper responsibilities

```text
V1 object
→ canonical migration DTO
→ V2 aggregate
```

---

# 105. Migration mapper rule

Pas de simple :

```text
dict copy
```

La migration doit être sémantique.

---

# 106. Migration conflict handling

Types :

```text
ID_CONFLICT
STATE_CONFLICT
FINGERPRINT_CONFLICT
MISSING_REFERENCE
INVALID_LEASE
CORRUPT_CHECKPOINT
UNMAPPABLE_APPROVAL
```

---

# 107. Conflict policy

Chaque type :

```text
auto-fix?
skip?
manual?
abort?
```

doit être défini.

---

# 108. Manual review queue

Les cas ambigus peuvent être inscrits dans :

```text
migration_review_cases
```

ou un rapport structuré.

---

# 109. No invented data

Règle absolue :

```text
MIG-INV-05
Migration never invents authority or external success.
```

---

# 110. Missing Approval

Si une action V1 semble avoir attendu approval mais aucune décision durable n’existe :

```text
require new approval
```

plutôt que reconstruire depuis logs.

---

# 111. Missing Effect outcome

Si le provider a peut-être été appelé mais le résultat manque :

```text
Effect UNKNOWN
```

et reconciliation.

---

# 112. Missing Fencing history

Si token maximum impossible à prouver :

```text
stop
manual safety procedure
```

---

# 113. Missing Artifact blob

Metadata migrée avec :

```text
UNAVAILABLE
```

ou statut équivalent.

---

# 114. Legacy corruption handling

Une migration n’est pas un mécanisme de camouflage de corruption historique.

---

# 115. Migration preflight

Avant migration :

```text
schema version
row counts
invalid JSON
duplicate IDs
duplicate idempotency keys
orphan references
fencing maxima
pending approvals
unknown effects
```

---

# 116. Preflight blockers

P0 :

```text
duplicate critical idempotency key with divergent fingerprint
invalid fencing history
cross-tenant reference
corrupt effect success record
```

---

# 117. Preflight warnings

P1/P2 :

```text
missing optional metadata
legacy event gaps
orphan non-critical artifact
```

---

# 118. Migration observability

Metrics :

```text
migration_records_total
migration_success_total
migration_failure_total
migration_manual_review_total
migration_duration_seconds
migration_batch_progress
```

---

# 119. Migration tracing

Spans :

```text
migration.inspect
migration.map
migration.persist
migration.verify
migration.cutover
```

---

# 120. Migration audit

Opérations critiques :

```text
start
cutover
rollback
manual fix
fencing repair
effect manual resolution
```

auditées.

---

# 121. Rollback philosophy

Deux catégories :

```text
pre-cutover rollback
post-cutover forward-fix
```

---

# 122. Pre-cutover rollback

Facile :

```text
V1 still authoritative
drop/rebuild V2 projection
```

---

# 123. Post-cutover rollback

Plus dangereux.

Une fois V2 écrit des données/Effects :

```text
rollback to V1
```

peut perdre des faits.

---

# 124. Forward-fix preferred

Après cutover :

```text
forward-fix
```

est généralement plus sûr que downgrade.

---

# 125. Rollback gate

Rollback post-cutover n’est autorisé que si :

```text
no V2-only irreversible Effects
or
explicit reconciliation/compensation performed
```

---

# 126. Database rollback

Schéma :

```text
expand/contract
```

réduit la nécessité de downgrade destructif.

---

# 127. Feature flags

Utiles pour :

```text
V2 read path
V2 runtime path
V2 persistence path
```

mais ne doivent pas masquer la source de vérité.

---

# 128. Flag naming

Exemples :

```text
PYAGENTSKIT_V2_READS
PYAGENTSKIT_V2_RUNTIME
```

si utilisé temporairement.

---

# 129. No semantic feature flag chaos

Éviter 20 flags qui créent des combinaisons non testables.

---

# 130. Deployment migration stages

```text
Deploy 1
V2 code dormant

Deploy 2
shadow reads

Deploy 3
V2 selected workflows

Deploy 4
V2 persistence active

Deploy 5
V2 default

Deploy 6
V1 compatibility-only
```

---

# 131. Canary strategy

Migrer d’abord :

```text
non-critical tenants/workflows
```

si multi-tenant deployment.

---

# 132. Tenant-by-tenant migration

Possible si :

```text
tenant routing explicit
store schema supports it
```

---

# 133. Run-by-run migration

Possible pour Runs non actifs.

---

# 134. Active Run migration

Plus risquée.

Préférer :

```text
finish V1 active Runs
start new Runs in V2
```

quand possible.

---

# 135. Long-running Runs

Si migration nécessaire :

```text
pause at safe recovery boundary
migrate state
acquire V2 ownership
resume
```

---

# 136. Active Effect migration

Ne pas migrer un Effect en cours sans classifier :

```text
sent?
not sent?
unknown?
```

---

# 137. Active Approval migration

Possible si état `PENDING` durable.

Conserver :

```text
scope
fingerprint
expiry
actor constraints
```

---

# 138. Lease migration during live system

Très sensible.

Préférer fenêtre :

```text
workers drained
leases expired/released
```

avant bascule de fencing schema.

---

# 139. Zero-downtime ambition

Possible pour certaines parties.

Pas un objectif absolu au détriment de safety.

---

# 140. Safety over availability

Principe :

> **Une courte fenêtre de maintenance vaut mieux qu’une reprise avec ownership ambigu.**

---

# 141. Release strategy

```text
1.6.x
maintenance

2.0.0a1
Domain foundations

2.0.0a2
Runtime abstraction

2.0.0a3
Effect/Recovery

2.0.0a4
Persistence

2.0.0b1
Governance/Audit

2.0.0b2
External runtimes/connectors

2.0.0rc1
API + migration

2.0.0
qualified stable
```

---

# 142. Migration support matrix

| Source | Target | Support |
|---|---|---|
| 1.6.x | 2.0.0rc1 | Required |
| 1.6.x | 2.0.0 | Required |
| 1.5.x | 2.0.0 | Prefer via 1.6 upgrade |
| <1.5 | 2.0.0 | Not direct initially |

---

# 143. Recommended upgrade path

```text
old V1
→ latest 1.6.x
→ migration preflight
→ V2
```

---

# 144. Migration CLI

Candidate :

```bash
pyagentskit migrate inspect
pyagentskit migrate dry-run
pyagentskit migrate apply
pyagentskit migrate verify
pyagentskit migrate status
```

---

# 145. Migration CLI safety

`apply` nécessite :

```text
explicit target
confirmation
backup/snapshot acknowledgment
```

selon environnement.

---

# 146. Non-interactive automation

Support :

```text
--yes
--json
--batch-size
--resume
```

pour pipelines.

---

# 147. Migration manifest

Chaque exécution peut produire :

```json
{
  "source_version": "1.6.x",
  "target_version": "2.0.0rc1",
  "batch_id": "...",
  "started_at": "...",
  "completed_at": "...",
  "counts": {}
}
```

---

# 148. Checksum verification

Pour artifacts/config/migration data quand possible.

---

# 149. Referential integrity verification

Après backfill :

```text
Run → Session
Effect → Run
Approval → Effect/Run
RuntimeInvocation → Run
Lease → Resource
Message → Conversation
```

---

# 150. Logical integrity verification

Exemples :

```text
SUCCEEDED Effect not unresolved
APPROVED Approval scope present
active lease unique
fencing monotonic
terminal Run no invalid next transition
```

---

# 151. Performance migration testing

Tester :

```text
large Run histories
many Effects
many Messages
large audit volume
```

---

# 152. Migration load control

Utiliser :

```text
batch size
sleep/backoff
transaction limits
```

---

# 153. Lock impact

Éviter migrations longues avec :

```text
ACCESS EXCLUSIVE
```

sur tables critiques si online migration.

---

# 154. Index creation

Utiliser méthodes online/concurrentes lorsque pertinent.

---

# 155. Backfill observability

Progress visible.

---

# 156. Cutover checklist

```text
[ ] backup/snapshot complete
[ ] V1 version supported
[ ] V2 schema ready
[ ] migration dry-run clean
[ ] unknown effects reviewed
[ ] pending approvals reviewed
[ ] workers drained
[ ] leases safe
[ ] fencing max verified
[ ] writes frozen if required
[ ] backfill completed
[ ] verification passed
[ ] V2 readiness green
[ ] cutover authorized
```

---

# 157. Post-cutover checklist

```text
[ ] V2 writes observed
[ ] no duplicate Effects
[ ] no stale fencing
[ ] approval resume works
[ ] runtime adapter works
[ ] audit events persist
[ ] outbox/inbox healthy
[ ] error rates normal
[ ] migration report archived
```

---

# 158. Rollback checklist

```text
[ ] identify V2-only writes
[ ] identify external Effects
[ ] stop admissions
[ ] stop workers
[ ] reconcile external systems
[ ] decide rollback vs forward-fix
[ ] restore routing
[ ] verify V1 state
```

---

# 159. Migration test strategy

Tests :

```text
unit mapping
golden fixtures
property-based where useful
database migration integration
restartable migration
crash injection
partial batch failure
conflict cases
real PostgreSQL
```

---

# 160. Golden fixtures

Créer jeux V1 représentatifs :

```text
simple success
waiting approval
unknown effect
failed effect
cancelled run
distributed run
artifact-rich run
corrupt/legacy edge cases
```

---

# 161. Migration property tests

Exemples :

```text
COMPLETED never maps to non-success
UNKNOWN never maps to FAILED
fencing token never decreases
tenant identity preserved
```

---

# 162. Crash injection

Crash :

```text
after batch read
after V2 insert
before checkpoint update
after checkpoint update
```

Migration doit reprendre proprement.

---

# 163. Idempotent rerun

Rejouer la même migration :

```text
does not duplicate
does not change semantics
```

---

# 164. Migration contract

Le migrator lui-même possède un contrat :

```text
inspect
plan
apply
verify
resume
```

---

# 165. Migration security

Le processus a accès à beaucoup de données.

Exiger :

```text
least privilege
secure logs
no secret dumps
restricted operator role
```

---

# 166. Migration privacy

Les rapports ne doivent pas contenir :

```text
message contents
prompts
secrets
raw payloads
```

sauf option explicitement contrôlée.

---

# 167. Migration authorization

Actions :

```text
apply
cutover
manual repair
```

requièrent rôle approprié.

---

# 168. Migration audit evidence

Conserver :

```text
operator
version
batch
checksum
result
reason
```

---

# 169. API compatibility strategy

V1 API :

```text
stable through 1.6.x
```

V2 API :

```text
new namespaced contracts
```

---

# 170. API deprecation path

Exemple :

```text
Runner V1
→ supported as native runtime facade
→ deprecated only if replacement experience complete
```

---

# 171. Documentation migration

Créer :

```text
docs/migration/v1-to-v2.md
```

avec :

```text
before/after examples
status mapping
API mapping
data migration
operational checklist
```

---

# 172. Cookbook migration

Exemples :

```text
basic run
approval
durable recovery
distributed worker
coding agent
connector
```

---

# 173. User-facing semantic changes

Documenter clairement :

```text
WAITING non-terminal
Run vs RuntimeInvocation
Session vs Conversation
Effect generalized
Approval scope changes
```

---

# 174. V1 serialized data support

Décider combien de temps V2 doit pouvoir lire :

```text
V1 JSON payloads
V1 checkpoints
V1 event files
```

---

# 175. Legacy deserialization boundary

Toute lecture legacy doit rester dans :

```text
compat/v1
migration
native runtime ACL
```

---

# 176. No legacy parser in Domain

Interdit.

---

# 177. V1 PostgreSQL compatibility

Ne pas modifier destructivement les tables V1 pendant les phases initiales.

---

# 178. V2 schema namespace

Option :

```text
pyagentskit_v2 schema
```

pendant migration.

Alternative :

```text
same schema, new tables
```

à décider par ADR.

---

# 179. Schema isolation recommendation

Pour migration complexe, un schema PostgreSQL séparé peut faciliter :

```text
rollback
comparison
cleanup
```

mais augmente la complexité.

À évaluer.

---

# 180. Migration ADR candidates

```text
ADR-MIG-001 Strangler migration
ADR-MIG-002 V1 compatibility boundary
ADR-MIG-003 V1/V2 type coexistence
ADR-MIG-004 RunStatus mapping
ADR-MIG-005 Session/Conversation migration
ADR-MIG-006 Effect status mapping
ADR-MIG-007 Approval lifecycle mapping
ADR-MIG-008 Fencing migration
ADR-MIG-009 PostgreSQL cutover
ADR-MIG-010 Rollback vs forward-fix
ADR-MIG-011 Deprecation schedule
ADR-MIG-012 Legacy data retention
```

---

# 181. Migration risk register

## RISK-MIG-01 — Semantic mismatch

V1 state maps incorrectly to V2.

Mitigation :

```text
golden fixtures
explicit mapping
manual review
```

---

# 182. RISK-MIG-02 — Effect replay

Critique.

Mitigation :

```text
migrate Effects before resume
preserve idempotency
qualification
```

---

# 183. RISK-MIG-03 — Fencing regression

Critique.

Mitigation :

```text
max token verification
workers drained
post-migration fencing tests
```

---

# 184. RISK-MIG-04 — Approval authority loss

Mitigation :

```text
preserve decision
preserve scope
revalidate on resume
```

---

# 185. RISK-MIG-05 — Dual-write divergence

Mitigation :

```text
short dual-write window
single authority
Outbox
comparison
```

---

# 186. RISK-MIG-06 — Long-running migration

Mitigation :

```text
batching
resume cursor
indexes
```

---

# 187. RISK-MIG-07 — Hidden legacy dependency

Mitigation :

```text
import analysis
compat package
architecture CI
```

---

# 188. RISK-MIG-08 — Compatibility paralysis

Mitigation :

```text
V1 boundary
not V1 design reproduction
```

---

# 189. RISK-MIG-09 — User confusion

Mitigation :

```text
migration docs
clear versioning
explicit terminology
```

---

# 190. RISK-MIG-10 — Rollback impossible after external writes

Mitigation :

```text
cutover gate
reconciliation
forward-fix
```

---

# 191. Compatibility test matrix

| Area | V1 test | V2 test | Migration test |
|---|---:|---:|---:|
| Public imports | ✓ | ✓ | ✓ |
| Run states | ✓ | ✓ | ✓ |
| Effects | ✓ | ✓ | ✓ |
| Approvals | ✓ | ✓ | ✓ |
| Sessions | ✓ | ✓ | ✓ |
| Leases/Fencing | ✓ | ✓ | ✓ |
| PostgreSQL | ✓ | ✓ | ✓ |
| Runtime | ✓ | ✓ | ✓ |

---

# 192. Production migration qualification

Doit inclure :

```text
real V1 PostgreSQL dataset
real V2 schema
migration
verification
worker startup
resume
effect safety
approval safety
takeover
```

---

# 193. Disaster simulation

Tester :

```text
migration process killed
DB restart during migration
network drop
partial backfill
worker accidentally starts early
```

---

# 194. Early worker start guard

V2 workers doivent refuser de démarrer si :

```text
migration state != READY
```

---

# 195. Migration state table

Option :

```text
migration_state
```

avec :

```text
NOT_STARTED
BACKFILLING
VERIFYING
READY_FOR_CUTOVER
CUTOVER
COMPLETE
FAILED
```

---

# 196. Safety gate table

Peut contenir :

```text
schema_version
migration_version
fencing_epoch
cutover_state
```

---

# 197. Worker readiness integration

Worker readiness lit ce safety gate.

---

# 198. Restore interaction

Restore d’un backup V1/V2 pendant migration est un cas spécial.

---

# 199. Restore rule

Après restore :

```text
migration state cannot be trusted blindly
```

Re-run preflight/verification.

---

# 200. PITR rule

Si PITR revient avant des external Effects :

```text
mandatory reconciliation
```

---

# 201. Legacy cleanup

Après période stable :

```text
archive V1 tables
remove obsolete write paths
remove transitional flags
remove migration-only code
```

---

# 202. Cleanup prerequisites

```text
no active V1 clients
migration support window ended
backups validated
V2 stable
```

---

# 203. Legacy table retention

Possible read-only retention temporaire pour audit/support.

---

# 204. Legacy code retention

`compat/v1` peut survivre plus longtemps que les stores V1.

---

# 205. Migration completion criteria

La migration est terminée lorsque :

1. V2 est la seule source de vérité ;
2. aucun worker V1 n’est actif ;
3. aucun protected write V1 n’est possible ;
4. toutes les Effects critiques sont V2 ;
5. approvals V2 sont autoritatives ;
6. fencing V2 est autoritatif ;
7. API V2 est stable ;
8. migration verification est archivée ;
9. runbooks V2 sont actifs ;
10. compatibility-only V1 boundary est isolée.

---

# 206. Definition of Done

La stratégie V1→V2 est correctement implémentée lorsque :

1. la frontière V1 est gelée et testée ;
2. la V2 peut coexister sans modifier V1 ;
3. NativeRuntimeAdapter encapsule le Runner V1 ;
4. les mappings de statuts sont explicites ;
5. les mappings Session/Conversation sont explicites ;
6. les Effects sont migrés sans replay ;
7. les Approvals sont migrées sans création d’autorité ;
8. les fencing tokens ne régressent jamais ;
9. le migrator est restartable et idempotent ;
10. le dry-run existe ;
11. le preflight détecte les blockers ;
12. la vérification post-migration existe ;
13. le cutover possède un safety gate ;
14. rollback/forward-fix sont documentés ;
15. les active Runs ont une politique dédiée ;
16. les migration tests utilisent PostgreSQL réel ;
17. la documentation utilisateur existe ;
18. les legacy paths peuvent être retirés indépendamment.

---

# 207. Résumé

La migration cible suit cette trajectoire :

```text
V1.6 STABLE
    │
    ▼
V2 SKELETON
    │
    ▼
NATIVE RUNTIME ADAPTER
    │
    ▼
V2 DOMAIN
    │
    ▼
V2 PERSISTENCE
    │
    ▼
BACKFILL + VERIFY
    │
    ▼
CUTOVER
    │
    ▼
V2 PRIMARY
    │
    ▼
V1 COMPATIBILITY-ONLY
```

Les invariants critiques sont :

```text
no implicit Effect replay
no invented Approval
no fencing regression
no ambiguous source of truth
no silent semantic remapping
```

Le principe fondamental est :

> **La migration doit conserver la vérité avant de conserver la forme. Une donnée V1 ambiguë doit rester ambiguë en V2 plutôt que d’être “nettoyée” au prix d’une fausse certitude.**

Le document suivant naturel est :

```text
../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md
```
