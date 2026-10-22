# PyAgentsKit — API & Public Contracts

**Document :** `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Spécification métier et technique — API & Public Contracts  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`

---

# 1. Objet

Ce document définit la **surface API publique et les contrats stables** de PyAgentsKit.

Il précise :

- ce qui appartient à l’API publique ;
- ce qui reste interne ;
- les conventions Python ;
- l’API async ;
- la façade sync ;
- les modèles d’entrée/sortie ;
- les erreurs publiques ;
- les IDs et références ;
- les commandes et queries ;
- les events ;
- la sérialisation ;
- le versioning ;
- la compatibilité ;
- la dépréciation ;
- la stabilité des ports ;
- l’API REST éventuelle ;
- les webhooks ;
- la pagination ;
- l’idempotency ;
- les timeouts ;
- la cancellation ;
- les extensions ;
- les garanties de backward compatibility.

Le principe directeur est :

> **Une API publique doit exposer la sémantique durable de PyAgentsKit, pas sa plomberie interne.**

---

# 2. Objectifs

La surface publique doit être :

```text
small
explicit
typed
stable
composable
async-first
framework-neutral
backend-neutral
versioned
observable
```

---

# 3. Non-objectifs

L’API publique ne doit pas exposer directement :

```text
SQLAlchemy models
PostgreSQL rows
internal transaction objects
provider SDK objects
runtime-specific implementation details
ORM sessions
raw database connections
internal queues
worker internals
```

---

# 4. Public vs Internal

Convention de package :

```text
pyagentskit.api
pyagentskit.models
pyagentskit.errors
pyagentskit.ports
pyagentskit.runtime
pyagentskit.effects
pyagentskit.approvals
```

Interne :

```text
pyagentskit._internal
```

---

# 5. Règle d’import public

L’utilisateur doit pouvoir dépendre de :

```python
from pyagentskit import ...
```

ou de namespaces explicitement publics.

Il ne doit pas avoir besoin de :

```python
from pyagentskit._internal.foo.bar import ...
```

---

# 6. Stable Import Paths

Les chemins publics deviennent un contrat.

Exemple :

```python
from pyagentskit import PyAgentsKit
from pyagentskit import RunState
from pyagentskit import EffectStatus
from pyagentskit import ApprovalStatus
```

---

# 7. Internal Imports

Tout namespace préfixé :

```text
_internal
```

est :

```text
unstable
not covered by compatibility guarantee
```

---

# 8. API Layers

Surface publique candidate :

```text
High-level Client
Application Services
Domain Value Objects
Ports / Protocols
Configuration
Events
Errors
```

---

# 9. High-Level Client

Façade principale candidate :

```python
class PyAgentsKit:
    ...
```

Responsabilités :

```text
create/run/resume/cancel
inspect
approvals
effects
artifacts
health
```

---

# 10. Async First

La surface de référence est :

```text
async
```

car :

```text
LLMs
stores
connectors
messaging
runtime adapters
```

sont naturellement I/O-bound.

---

# 11. Sync Facade

Une façade sync peut être fournie :

```python
from pyagentskit.sync import PyAgentsKit
```

Elle ne doit pas avoir une sémantique différente.

---

# 12. No Async Leakage in Sync API

L’utilisateur sync ne doit pas gérer manuellement :

```text
event loop
await
asyncio.run
```

---

# 13. Sync Limitations

La documentation doit préciser les limitations en environnement déjà async :

```text
Jupyter
FastAPI
async frameworks
```

---

# 14. High-level Configuration

Exemple conceptuel :

```python
kit = PyAgentsKit(
    stores=...,
    runtimes=...,
    policy=...,
    telemetry=...,
)
```

---

# 15. Builder / Factory

Une factory peut simplifier les profils :

```python
PyAgentsKit.from_sqlite(...)
PyAgentsKit.from_postgres(...)
```

sans masquer les garanties différentes.

---

# 16. Production Factory

Un helper ne doit jamais faire croire que :

```text
SQLite == PostgreSQL distributed guarantees
```

---

# 17. Dependency Injection

Les ports doivent être injectables :

```text
RunStore
EffectStore
ApprovalStore
LeaseStore
RuntimeAdapterRegistry
SecretProvider
AuthorizationPort
```

---

# 18. Public Configuration Model

Configuration publique typée :

```text
StorageConfig
RuntimeConfig
SecurityConfig
ObservabilityConfig
WorkerConfig
```

---

# 19. Immutable Configuration

Préférence :

```text
validated once
immutable/frozen where possible
```

---

# 20. Environment Variables

Peuvent alimenter la config mais ne doivent pas devenir la seule API de configuration.

---

# 21. Configuration Precedence

Ordre à documenter :

```text
explicit arguments
config object
environment
defaults
```

---

# 22. Secrets in Config

La config publique doit accepter :

```text
SecretReference
```

plutôt que forcer les valeurs de secrets.

---

# 23. Public IDs

Types candidats :

```text
RunId
SessionId
ConversationId
MessageId
EffectId
ApprovalId
ArtifactId
LeaseId
WorkerId
```

---

# 24. Typed IDs

Préférence :

```text
opaque strongly typed wrappers
```

plutôt que strings indistinctes partout.

---

# 25. ID Serialization

Représentation externe :

```text
string
```

stable et opaque.

---

# 26. ID Generation

Le format interne peut évoluer si :

```text
string contract remains stable
```

---

# 27. Public Value Objects

Exemples :

```text
RunState
EffectStatus
ApprovalStatus
RuntimeCapability
EffectRiskLevel
ExternalReference
CorrelationContext
```

---

# 28. Public Entities

Les objets retournés publiquement doivent être des :

```text
immutable/read models
```

ou DTOs contrôlés,

pas des entités mutables branchées directement au store.

---

# 29. RunView

Exemple :

```python
@dataclass(frozen=True)
class RunView:
    run_id: RunId
    state: RunState
    session_id: SessionId | None
    created_at: datetime
    updated_at: datetime
```

---

# 30. EffectView

Champs candidats :

```text
effect_id
run_id
kind
status
risk_level
external_reference?
created_at
updated_at
```

---

# 31. ApprovalView

Champs :

```text
approval_id
run_id
effect_id?
status
scope
requested_at
decided_at?
```

---

# 32. LeaseView

Surface opérateur :

```text
resource
worker
fencing_token
expires_at
status
```

---

# 33. ArtifactView

Champs :

```text
artifact_id
kind
content_type
size
checksum
created_at
```

---

# 34. Public Domain Enums

Les enums exposés publiquement doivent être stables autant que possible.

---

# 35. Enum Forward Compatibility

Les clients externes doivent éviter les `match` exhaustifs qui cassent sur nouvelle valeur.

Pour API réseau :

```text
unknown enum value
```

doit être tolérable lorsque possible.

---

# 36. Extensible Names

Pour certains concepts, préférer :

```text
namespaced string
```

à enum fermé.

Exemple :

```text
effect kind
runtime event name
connector capability
```

---

# 37. Commands

Les mutations explicites peuvent être modélisées comme commands.

Exemples :

```text
CreateRun
StartRun
ResumeRun
CancelRun
ApproveApproval
RejectApproval
ResolveEffect
```

---

# 38. Queries

Lectures :

```text
GetRun
ListRuns
GetEffect
ListEffects
GetApproval
ListApprovals
GetArtifact
```

---

# 39. Command / Query Separation

Pas nécessairement CQRS complet.

Mais :

```text
read
```

et :

```text
mutation
```

doivent rester sémantiquement distincts.

---

# 40. CreateRunRequest

Structure candidate :

```text
runtime
input
session_id?
tenant_id?
metadata?
idempotency_key?
```

---

# 41. CreateRunResponse

```text
run
created_new: bool
```

utile si création idempotente.

---

# 42. Start vs Create

Deux modèles possibles :

```text
create then start
```

ou :

```text
create_and_start
```

Les deux peuvent être exposés si leurs sémantiques sont claires.

---

# 43. Convenience API

Exemple :

```python
run = await kit.run(...)
```

peut combiner :

```text
create + start + optional wait
```

mais doit documenter ce qu’elle fait.

---

# 44. RunHandle

Un handle public peut simplifier :

```python
run = await kit.runs.create(...)
await run.start()
await run.cancel()
state = await run.inspect()
```

---

# 45. Handle Semantics

Un `RunHandle` public ne doit pas être une référence mémoire autoritative.

Il doit toujours pouvoir recharger l’état durable.

---

# 46. Detached Handles

Un handle peut être sérialisable via :

```text
run_id
```

et reconnecté plus tard.

---

# 47. Runtime Submission

Exemple :

```python
run = await kit.runs.create(
    runtime="langgraph",
    input=...,
)
```

---

# 48. Runtime-specific Config

Doit rester namespacée :

```python
runtime_options={
    "langgraph": {...}
}
```

ou objet spécifique adapter.

---

# 49. Avoid Runtime Conditionals in Core API

Ne pas exposer :

```python
if runtime == "codex":
    ...
```

dans le core.

---

# 50. RuntimeDescriptor Public Model

Champs :

```text
name
version
capabilities
control_level
health
```

---

# 51. Runtime Listing

API candidate :

```python
await kit.runtimes.list()
```

---

# 52. Runtime Capability Query

```python
await kit.runtimes.capabilities("codex")
```

---

# 53. Run Lifecycle API

Exemple :

```python
await kit.runs.start(run_id)
await kit.runs.pause(run_id)
await kit.runs.resume(run_id)
await kit.runs.cancel(run_id)
```

---

# 54. Invalid Transition

Doit produire une erreur publique stable :

```text
InvalidRunTransition
```

---

# 55. Effect API

Exemple :

```python
effect = await kit.effects.get(effect_id)
await kit.effects.reconcile(effect_id)
```

---

# 56. Effect Manual Resolution

Action sensible :

```python
await kit.effects.resolve_manually(
    effect_id,
    resolution=...,
    reason=...,
)
```

---

# 57. Approval API

```python
await kit.approvals.list_pending()
await kit.approvals.approve(...)
await kit.approvals.reject(...)
```

---

# 58. Approval Decision Idempotency

La même décision répétée peut retourner le même état si identique.

---

# 59. Conflicting Approval Decision

Doit produire :

```text
ApprovalAlreadyDecided
```

ou équivalent stable.

---

# 60. Artifact API

```python
await kit.artifacts.get(...)
await kit.artifacts.open(...)
await kit.artifacts.list_for_run(...)
```

---

# 61. Artifact Streaming

Pour gros fichiers :

```text
streaming
```

préférable au chargement complet en mémoire.

---

# 62. Conversation API

Si exposée :

```python
await kit.conversations.create(...)
await kit.messages.append(...)
await kit.messages.list(...)
```

---

# 63. Message Append Contract

Doit supporter :

```text
deduplication key?
actor reference
message type
content
```

---

# 64. Memory API

Surface candidate :

```python
await kit.memory.get(...)
await kit.memory.put(...)
await kit.memory.list(...)
```

avec scopes explicites.

---

# 65. Security-sensitive Memory

Les APIs doivent faire respecter AuthZ/tenant boundaries.

---

# 66. Worker API

Principalement opérateur/admin :

```python
await kit.workers.list()
await kit.workers.inspect(...)
```

---

# 67. Lease API

Par défaut lecture opérateur.

Mutation forcée :

```text
admin-only
```

---

# 68. Force Takeover API

Doit exiger :

```text
reason
authorization
audit
```

---

# 69. Public Error Hierarchy

Base :

```python
class PyAgentsKitError(Exception):
    ...
```

---

# 70. Error Families

```text
ValidationError
NotFoundError
ConflictError
AuthorizationError
PolicyDeniedError
ApprovalError
EffectError
RuntimeError
StoreError
CoordinationError
ConnectorError
SecurityError
ConfigurationError
```

---

# 71. ValidationError

Entrée invalide.

---

# 72. NotFoundError

Objet absent.

Sous-types possibles :

```text
RunNotFound
EffectNotFound
ApprovalNotFound
ArtifactNotFound
```

---

# 73. ConflictError

Conflit logique/concurrent.

Exemples :

```text
ConcurrencyConflict
IdempotencyConflict
AlreadyExists
```

---

# 74. AuthorizationError

Action non autorisée.

---

# 75. PolicyDeniedError

La policy refuse explicitement.

À distinguer de :

```text
AuthZ failure
```

---

# 76. ApprovalRequired

Selon style API, peut être :

```text
result state
```

plutôt qu’exception.

Préférence :

```text
not an exceptional error
```

---

# 77. Run Waiting

Un Run en `WAITING` n’est pas une erreur.

---

# 78. EffectUnknown

Un `EffectStatus.UNKNOWN` est un état métier, pas nécessairement une exception Python.

---

# 79. RuntimeUnavailable

Erreur si runtime requis indisponible.

---

# 80. StoreUnavailable

Erreur publique retriable selon contexte.

---

# 81. CoordinationLost

Erreur quand ownership est perdu.

---

# 82. StaleOwnership

Erreur explicite :

```text
stale fencing token / lease
```

---

# 83. ConnectorUnavailable

Provider ou connector indisponible.

---

# 84. AmbiguousOutcome

Pour write externe ambigu :

```text
Effect state should become UNKNOWN
```

L’exception peut être interne au service mais le contrat public retourne l’état durable.

---

# 85. Error Metadata

Une erreur publique peut exposer :

```text
code
message
retryable
correlation_id
details?
```

---

# 86. Stable Error Codes

Exemples :

```text
RUN_NOT_FOUND
INVALID_RUN_TRANSITION
APPROVAL_ALREADY_DECIDED
IDEMPOTENCY_CONFLICT
STALE_OWNERSHIP
POLICY_DENIED
```

---

# 87. Error Message Stability

Le texte humain :

```text
not stable contract
```

Le code d’erreur :

```text
stable contract
```

---

# 88. Exceptions and Secrets

Les exceptions ne doivent pas contenir :

```text
credentials
full payloads
sensitive prompts
```

---

# 89. Cancellation

Les méthodes longues doivent supporter cancellation.

---

# 90. Python Cancellation

En async :

```text
CancelledError
```

doit être respectée.

---

# 91. Cancellation Semantics

Annuler l’attente Python ne signifie pas automatiquement :

```text
cancel Run
```

---

# 92. Explicit Run Cancellation

Doit être une commande distincte.

---

# 93. Timeout

Le timeout client ne signifie pas que l’opération distante a échoué.

---

# 94. Timeout + Effect

Pour un Effect externe :

```text
timeout
→ possibly UNKNOWN
```

---

# 95. Client-side Timeout

Doit être distingué de :

```text
business operation timeout
```

---

# 96. Wait APIs

Exemple :

```python
await kit.runs.wait(
    run_id,
    until=...,
    timeout=...
)
```

---

# 97. Wait Does Not Own

Une attente côté client ne doit pas conserver un worker artificiellement.

---

# 98. Streaming APIs

Candidates :

```python
async for event in kit.runs.events(run_id):
    ...
```

---

# 99. Event Stream Semantics

Préciser :

```text
ordering
resume cursor
dedup
disconnect behavior
```

---

# 100. Event Cursor

Value Object candidat :

```text
EventCursor
```

---

# 101. Event Delivery

Le flux client peut être :

```text
at-least-once
```

avec event IDs pour dedup.

---

# 102. Public Event Envelope

Structure candidate :

```text
event_id
event_name
version
occurred_at
object_type
object_id
correlation_id
tenant_id?
payload
```

---

# 103. Event Version

Chaque event public possède :

```text
schema_version
```

---

# 104. Event Names

Convention :

```text
run.started
effect.succeeded
approval.approved
lease.taken_over
```

---

# 105. Event Compatibility

Ajouter un champ optionnel :

```text
backward-compatible
```

Retirer/renommer :

```text
breaking
```

---

# 106. Event Payload

Doit éviter :

```text
internal DB columns
provider SDK objects
secrets
```

---

# 107. Event Ordering

Aucun ordre global distribué n’est garanti.

---

# 108. Aggregate Ordering

Peut être aidé par :

```text
sequence
version
```

si exposé.

---

# 109. Webhook API

PyAgentsKit peut produire des webhooks sortants.

---

# 110. Outbound Webhook Contract

Doit inclure :

```text
signature
event id
timestamp
schema version
retry semantics
```

---

# 111. Webhook Signature

Algorithme/version doit être documenté.

---

# 112. Webhook Retry

Les consumers doivent supposer :

```text
at-least-once delivery
```

---

# 113. Webhook Idempotency

Le consumer peut dedup sur :

```text
event_id
```

---

# 114. REST API

Une API HTTP peut être fournie comme couche optionnelle au-dessus des mêmes services applicatifs.

---

# 115. REST Versioning

Préférence :

```text
/api/v1
```

ou stratégie équivalente stable.

---

# 116. REST Resources

Exemples :

```text
/runs
/effects
/approvals
/artifacts
/workers
/audit
```

---

# 117. REST Run Create

```text
POST /v1/runs
```

---

# 118. REST Run Inspect

```text
GET /v1/runs/{run_id}
```

---

# 119. REST Run Cancel

```text
POST /v1/runs/{run_id}:cancel
```

ou convention REST documentée.

---

# 120. REST Approval Decide

```text
POST /v1/approvals/{approval_id}:approve
POST /v1/approvals/{approval_id}:reject
```

---

# 121. HTTP Statuses

Mapping candidat :

```text
200 success
201 created
202 accepted
400 validation
401 unauthenticated
403 unauthorized
404 not found
409 conflict
422 semantic validation
429 rate limited
503 dependency unavailable
```

---

# 122. 202 Accepted

Approprié pour :

```text
long-running Run creation
async operation
```

---

# 123. HTTP Error Envelope

```json
{
  "error": {
    "code": "IDEMPOTENCY_CONFLICT",
    "message": "...",
    "correlation_id": "...",
    "details": {}
  }
}
```

---

# 124. REST Authentication

API server peut supporter :

```text
OIDC
OAuth2
mTLS
API tokens
```

selon deployment.

---

# 125. REST Authorization

Toujours appliquée côté serveur.

---

# 126. API Rate Limiting

Peut protéger :

```text
run creation
approval decisions
webhooks
admin actions
```

---

# 127. Pagination

List APIs doivent être paginées.

---

# 128. Cursor Pagination

Préférence :

```text
cursor-based
```

pour grandes tables et ordre stable.

---

# 129. Pagination Contract

Request :

```text
limit
cursor
```

Response :

```text
items
next_cursor
has_more
```

---

# 130. Offset Pagination

Peut être supportée pour petites listes, mais moins robuste sous mutations.

---

# 131. Limit Bounds

Exemple :

```text
default=50
max=500
```

configurable.

---

# 132. Sorting

Champs autorisés explicitement.

---

# 133. Filtering

Filtres typés :

```text
status
created_after
created_before
runtime
risk_level
tenant
```

selon permission.

---

# 134. Search

Ne pas surcharger une API de liste avec une recherche full-text générique non définie.

---

# 135. Idempotency Header

Pour API HTTP :

```text
Idempotency-Key
```

peut être supporté.

---

# 136. Idempotency Scope

Doit inclure :

```text
principal/tenant
operation
resource scope
```

---

# 137. Idempotency Response

Rejouer la même requête compatible peut retourner :

```text
same logical result
```

---

# 138. Idempotency Conflict

Même clé, payload différent :

```text
409 IDEMPOTENCY_CONFLICT
```

---

# 139. Request Fingerprint

Canonicalisation documentée.

---

# 140. Idempotency Retention

Durée de conservation à documenter par opération.

---

# 141. API Timeouts

Les timeouts réseau ne doivent pas être interprétés automatiquement comme échec métier.

---

# 142. Request Size Limits

Doivent être bornées.

---

# 143. Large Inputs

Utiliser :

```text
Artifact
BlobStore
reference
```

pour gros payloads.

---

# 144. Large Outputs

Utiliser streaming ou artifacts.

---

# 145. Serialization Format

JSON est le format réseau de référence.

---

# 146. Datetime Format

ISO 8601 avec timezone.

Exemple :

```text
2026-10-20T18:30:00+02:00
```

Interne recommandé :

```text
UTC
```

---

# 147. Duration Format

Préférer :

```text
seconds numeric
```

ou ISO duration si besoin.

Éviter formats ambigus.

---

# 148. Decimal Values

Pour finance :

```text
string decimal
```

ou type explicitement documenté.

Éviter float binaire si précision critique.

---

# 149. Binary Data

Ne pas mettre de gros blobs en base64 dans API standard.

Utiliser Artifact/BlobStore.

---

# 150. Metadata

Type candidat :

```text
Mapping[str, JSONValue]
```

---

# 151. Metadata Rules

Metadata :

```text
not authoritative for core invariants
```

---

# 152. Reserved Metadata Keys

Namespace :

```text
pyagentskit.*
```

réservé au framework.

---

# 153. User Metadata Namespace

Peut être libre ou namespacé :

```text
app.*
```

---

# 154. Schema Validation

Tous les modèles publics doivent valider :

```text
types
required fields
ranges
formats
```

---

# 155. Unknown Fields

API réseau :

```text
ignore/preserve according to versioning policy
```

mais ne pas accepter silencieusement des champs sensibles inconnus sur commands critiques.

---

# 156. Public Python Models

Peuvent être basés sur :

```text
dataclasses
Pydantic
attrs
```

mais la dépendance concrete doit être un ADR.

---

# 157. ORM Independence

Jamais exposer des ORM models comme API publique.

---

# 158. Serialization Stability

Un modèle public sérialisable doit avoir :

```text
stable field names
stable meaning
versioning rules
```

---

# 159. Semantic Versioning

PyAgentsKit doit suivre SemVer après stabilisation :

```text
MAJOR.MINOR.PATCH
```

---

# 160. Pre-1.0

Avant 1.0 :

```text
breaking changes still possible
```

mais doivent rester documentées.

---

# 161. 1.0 Contract

À partir de 1.0 :

```text
public API compatibility commitment
```

---

# 162. Breaking Change

Exemples :

```text
remove public method
rename required field
change semantic meaning
change error code
change default safety behavior
```

---

# 163. Non-breaking Change

Exemples :

```text
new optional field
new method
new enum/extensible value if clients are forward compatible
performance improvement
new adapter
```

---

# 164. Behavioral Compatibility

La compatibilité ne concerne pas seulement signatures.

Exemple breaking :

```text
previously approval required
now auto-allowed
```

si safety contract change.

---

# 165. Security Defaults Compatibility

Une sécurité plus stricte peut casser des usages.

Doit être documentée comme :

```text
behavioral breaking or security hardening
```

selon impact.

---

# 166. Deprecation

Cycle recommandé :

```text
announce
warn
document replacement
keep for defined period
remove in major release
```

---

# 167. DeprecationWarning

Python :

```text
DeprecationWarning
```

ou mécanisme approprié.

---

# 168. Deprecation Metadata

Documenter :

```text
deprecated_since
replacement
planned_removal
```

---

# 169. Compatibility Matrix

Publier :

```text
PyAgentsKit version
Python versions
PostgreSQL versions
runtime adapter versions
connector versions
```

---

# 170. Python Support Policy

Exemple :

```text
current stable + recent supported versions
```

à formaliser dans release strategy.

---

# 171. Backend Compatibility

Chaque release doit annoncer :

```text
minimum PostgreSQL
SQLite compatibility
object storage support
```

---

# 172. Runtime Adapter Compatibility

Adapter peut déclarer :

```text
min_core_version
max_core_version?
runtime_version_range
```

---

# 173. Connector Compatibility

Même principe.

---

# 174. Protocol Versioning

Les Ports publics Python peuvent évoluer via :

```text
new optional capabilities
new protocols
adapter version gates
```

---

# 175. Protocol Runtime Checking

Optionnel.

Les Protocols servent principalement au typing et aux contract tests.

---

# 176. Port Stability Levels

Niveaux candidats :

```text
EXPERIMENTAL
BETA
STABLE
DEPRECATED
```

---

# 177. Public API Stability Levels

Même classification pour features.

---

# 178. Experimental Namespace

Option :

```text
pyagentskit.experimental
```

sans promesse forte de compatibilité.

---

# 179. Beta Contract

Peut changer avec :

```text
minor release
```

avant 1.0 ou politique spécifique.

---

# 180. Stable Contract

Breaking only in major version.

---

# 181. Feature Flags

Peuvent activer des fonctions expérimentales.

---

# 182. Feature Flag Safety

Un flag ne doit pas désactiver silencieusement un invariant de safety sans avertissement explicite.

---

# 183. Extension Points

Extensions prévues :

```text
RuntimeAdapter
Connector
Store
PolicyProvider
AuthorizationPort
SecretProvider
TelemetryExporter
ArtifactBackend
```

---

# 184. Extension Registration

Doit être explicite.

---

# 185. Plugin Discovery

Si auto-discovery via entry points :

```text
opt-in
```

préférable en production.

---

# 186. Extension Namespace

Les packages externes peuvent utiliser :

```text
pyagentskit-<name>
```

comme convention de distribution.

---

# 187. Extension Metadata

Déclarer :

```text
name
version
core compatibility
capabilities
security/control level
```

---

# 188. Extension Trust

Installer une extension signifie exécuter du code.

La documentation doit l’indiquer clairement.

---

# 189. Public Hooks

Éviter les hooks arbitraires partout.

Préférer des ports explicites.

---

# 190. Lifecycle Hooks

Si nécessaires :

```text
before_run
after_run
before_effect
after_effect
```

doivent avoir des garanties définies.

---

# 191. Hook Safety

Un hook ne doit pas pouvoir contourner :

```text
Effect safety
Authorization
Approval
Fencing
```

sans être explicitement un composant trusted.

---

# 192. Event Subscribers

Les subscribers publics peuvent observer :

```text
events
```

mais ne deviennent pas automatiquement autoritaires.

---

# 193. Event Handler Failure

Ne doit pas nécessairement faire échouer le Run, selon catégorie.

---

# 194. Critical Subscribers

Pour mécanismes critiques, préférer :

```text
transactional Outbox
```

plutôt qu’un callback volatile.

---

# 195. Public Context Managers

Exemple :

```python
async with PyAgentsKit(...) as kit:
    ...
```

peut gérer :

```text
connections
workers
telemetry flush
```

---

# 196. Close Semantics

`close()` :

```text
stops local client resources
```

et ne signifie pas :

```text
cancel all durable Runs
```

---

# 197. Client Reconnect

Un nouveau client doit pouvoir reprendre l’inspection via IDs durables.

---

# 198. Thread Safety

La documentation doit préciser si le client sync est thread-safe.

---

# 199. Async Concurrency Safety

Le client async doit être sûr pour appels concurrents documentés.

---

# 200. Fork Safety

Ne pas supposer qu’un pool DB/client peut être forké en sécurité.

---

# 201. Worker API Separation

Le SDK utilisateur et le runtime worker peuvent être packages/modules distincts.

---

# 202. Worker Entrypoint

Candidate :

```text
pyagentskit worker run
```

---

# 203. Worker Config Contract

Champs :

```text
worker_id
capacity
runtime capabilities
store config
heartbeat interval
lease TTL
```

---

# 204. Worker Health API

Expose :

```text
live
ready
capabilities
```

sans détails sensibles.

---

# 205. Admin API Separation

Opérations admin :

```text
migration
repair
force takeover
kill switch
security status
```

doivent être distinctes des APIs métier normales.

---

# 206. Admin Client

Option :

```python
kit.admin....
```

---

# 207. Admin Reason Requirement

Actions sensibles peuvent exiger :

```text
reason
```

dans la signature publique.

---

# 208. Audit Query Contract

Exemple :

```python
await kit.audit.list_for_run(run_id)
```

---

# 209. Timeline API

Candidate :

```python
await kit.runs.timeline(run_id)
await kit.effects.timeline(effect_id)
```

---

# 210. Health API

```python
await kit.health.live()
await kit.health.ready()
```

---

# 211. Security Status API

```python
await kit.security.status()
```

---

# 212. Capability Reporting

Doit pouvoir indiquer :

```text
runtime capabilities
connector capabilities
store capabilities
security profile
```

---

# 213. Capability Truthfulness

L’API ne doit pas annoncer une garantie non réellement fournie.

---

# 214. Serialization of Capabilities

Préférer namespaced strings extensibles.

---

# 215. Public Contract Testing

Chaque release doit exécuter :

```text
API signature tests
serialization tests
error-code tests
backward compatibility tests
adapter contract tests
```

---

# 216. Golden Serialization Tests

Conserver des exemples JSON versionnés.

---

# 217. Import Compatibility Tests

Vérifier les imports publics documentés.

---

# 218. Type Compatibility Tests

Utiliser :

```text
mypy / pyright
```

ou équivalent pour exemples publics.

---

# 219. Documentation Tests

Les snippets API publics doivent être exécutables en CI autant que possible.

---

# 220. REST Contract Tests

Si REST :

```text
OpenAPI schema tests
status code tests
error envelope tests
pagination tests
idempotency tests
```

---

# 221. OpenAPI

La REST API doit pouvoir publier :

```text
OpenAPI
```

si elle devient officielle.

---

# 222. Generated Clients

Optionnel.

Ne pas faire dépendre le modèle Python interne d’un client généré.

---

# 223. API Changelog

Chaque release doit indiquer :

```text
added
changed
deprecated
removed
security changes
```

---

# 224. Migration Guide

Pour breaking releases :

```text
old API
new API
before/after examples
```

---

# 225. Example — Minimal Run

```python
async with PyAgentsKit(...) as kit:
    run = await kit.runs.create(
        runtime="custom",
        input={"task": "summarize"},
    )
    await kit.runs.start(run.run_id)
```

---

# 226. Example — Approval

```python
pending = await kit.approvals.list_pending()

await kit.approvals.approve(
    pending[0].approval_id,
    reason="Reviewed deployment plan",
)
```

---

# 227. Example — Reconcile Effect

```python
effect = await kit.effects.get(effect_id)

if effect.status is EffectStatus.UNKNOWN:
    result = await kit.effects.reconcile(effect.effect_id)
```

---

# 228. Example — Runtime Capability

```python
descriptor = await kit.runtimes.get("codex")

if RuntimeCapability.COMMAND_EXECUTION in descriptor.capabilities:
    ...
```

---

# 229. Example — Event Stream

```python
async for event in kit.runs.events(run_id):
    print(event.event_name)
```

---

# 230. Example — Artifact Stream

```python
async with kit.artifacts.open(artifact_id) as stream:
    async for chunk in stream:
        ...
```

---

# 231. Public API Invariants

```text
API-INV-01
Public API never exposes ORM entities.

API-INV-02
Public IDs are opaque.

API-INV-03
WAITING is not an error.

API-INV-04
Effect UNKNOWN is a durable state, not silently mapped to FAILED.

API-INV-05
Client timeout never implies external failure.

API-INV-06
Sync API preserves async semantics.

API-INV-07
Error codes are more stable than human messages.

API-INV-08
Internal namespaces have no compatibility guarantee.

API-INV-09
Public events are versioned.

API-INV-10
Safety semantics are part of the public contract.
```

---

# 232. Anti-patterns

À éviter :

```text
return raw SQLAlchemy model
public API importing _internal
one giant generic execute() method
boolean success for ambiguous Effect
timeout == failure
stringly typed all IDs
provider SDK objects in public models
breaking enum changes without strategy
silent behavioral safety change
callbacks as durable contracts
```

---

# 233. Acceptance Criteria

Le modèle API & Public Contracts est opérationnel si :

1. les namespaces publics sont définis ;
2. la distinction public/internal est claire ;
3. une façade async stable existe ;
4. une façade sync éventuelle conserve la même sémantique ;
5. les IDs sont opaques et sérialisables ;
6. les read models sont séparés des entités persistence ;
7. les erreurs publiques ont des codes stables ;
8. `WAITING` et `UNKNOWN` restent des états métier ;
9. pagination et idempotency sont définies ;
10. les events sont versionnés ;
11. la REST API éventuelle réutilise les mêmes services applicatifs ;
12. SemVer et dépréciation sont définis ;
13. les extensions ont des contrats explicites ;
14. les safety semantics font partie de la compatibilité ;
15. des contract tests protègent l’API.

---

# 234. Architecture publique cible

```text
                 User Application
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
     Python Async   Python Sync    REST API
          │            │            │
          └────────────┼────────────┘
                       ▼
               Application Services
                       │
            ┌──────────┼───────────┐
            ▼          ▼           ▼
          Runs      Effects     Approvals
            │          │           │
            └──────────┼───────────┘
                       ▼
                  Domain / Ports
                       │
                Internal Adapters
```

---

# 235. Surface publique candidate

```text
PyAgentsKit
├── runs
├── sessions
├── conversations
├── messages
├── effects
├── approvals
├── artifacts
├── runtimes
├── audit
├── health
├── security
└── admin
```

---

# 236. Stable Core Imports Candidate

```python
from pyagentskit import (
    PyAgentsKit,
    RunState,
    EffectStatus,
    ApprovalStatus,
    EffectRiskLevel,
    RuntimeCapability,
    PyAgentsKitError,
)
```

---

# 237. Version Negotiation REST

Le serveur peut exposer :

```text
API version
core version
capabilities
```

---

# 238. Client / Server Compatibility

Un client doit pouvoir détecter une incompatibilité majeure.

---

# 239. Server Capability Endpoint

Candidate :

```text
GET /v1/capabilities
```

---

# 240. Backward-compatible Server Additions

Le client doit ignorer les champs optionnels inconnus lorsque la policy le permet.

---

# 241. Public Security Contract

L’API doit toujours documenter :

```text
who authenticates
who authorizes
which operations may require Approval
which operations are admin-only
```

---

# 242. Public Safety Contract

Pour chaque mutation externe importante, documenter :

```text
idempotency
reconciliation
UNKNOWN behavior
approval behavior
```

---

# 243. Public Durability Contract

Documenter :

```text
what is persisted before return
what survives client disconnect
what survives worker crash
```

---

# 244. Create Response Durability

Si `create()` retourne un `RunId`, le Run doit déjà être durablement enregistré.

---

# 245. Effect Start Response Durability

Si l’API retourne :

```text
Effect STARTED
```

l’intention doit être durable.

---

# 246. Approval Response Durability

Si `approve()` retourne succès, la décision doit être durable.

---

# 247. Lease/Admin Response Durability

Si force takeover retourne succès, le nouveau fencing state doit être durable.

---

# 248. API Observability

Chaque request/command devrait produire :

```text
correlation_id
trace context
structured logs
```

---

# 249. Correlation ID Exposure

Peut être retourné au client pour support/debug.

---

# 250. Request ID

API HTTP peut distinguer :

```text
request_id
correlation_id
```

---

# 251. Public Performance Expectations

Ne pas promettre des latences fixes non qualifiées.

Documenter plutôt :

```text
blocking vs async
streaming vs materialized
```

---

# 252. Bulk APIs

À introduire seulement si sémantique claire.

---

# 253. Bulk Mutation

Doit préciser :

```text
atomic?
partial success?
per-item errors?
idempotency?
```

---

# 254. Partial Success Envelope

Candidate :

```text
items[]
errors[]
```

---

# 255. API Evolution Discipline

Avant toute nouvelle méthode publique :

```text
is this durable domain semantics?
or implementation convenience?
```

Si seulement plomberie interne :

```text
keep internal
```

---

# 256. Questions ouvertes

```text
Q-API-01 Pydantic ou dataclasses pour modèles publics ?
Q-API-02 Façade sync officielle dès v1 ?
Q-API-03 REST API dans core ou package séparé ?
Q-API-04 RunHandle public ou services uniquement ?
Q-API-05 Cursor event stream standard ?
Q-API-06 Quels ports sont STABLE à 1.0 ?
Q-API-07 Quel policy de compatibilité pre-1.0 ?
Q-API-08 OpenAPI officiel dès 1.0 ?
Q-API-09 Comment exposer experimental features ?
Q-API-10 Quel schéma d’erreur final ?
Q-API-11 Capability endpoint réseau ?
Q-API-12 Quels imports racine garantir à long terme ?
```

---

# 257. ADR induits

```text
ADR-API-001 Public namespace policy
ADR-API-002 Async-first API
ADR-API-003 Sync façade
ADR-API-004 Public model library
ADR-API-005 Typed IDs
ADR-API-006 Error hierarchy and codes
ADR-API-007 Event envelope
ADR-API-008 Pagination strategy
ADR-API-009 Idempotency contract
ADR-API-010 REST versioning
ADR-API-011 SemVer and deprecation
ADR-API-012 Extension registration
ADR-API-013 Stability levels
ADR-API-014 RunHandle design
```

---

# 258. Definition of Done

L’API publique est mature lorsque :

1. tous les imports publics sont identifiés ;
2. les namespaces internes sont isolés ;
3. l’API async est cohérente ;
4. la façade sync éventuelle passe les mêmes contract tests ;
5. les modèles publics sont sérialisables ;
6. les IDs sont typés et opaques ;
7. les erreurs ont des codes stables ;
8. les semantics de timeout/cancellation sont documentées ;
9. idempotency et pagination sont testées ;
10. les events publics sont versionnés ;
11. la compatibilité backward est testée en CI ;
12. les dépréciations sont documentées ;
13. les extensions déclarent compatibilité/capabilities ;
14. aucun type provider/ORM interne ne fuite publiquement ;
15. la documentation contient des snippets testés ;
16. les safety guarantees sont considérées comme contrat public.

---

# 259. Résumé

La surface publique de PyAgentsKit repose sur :

```text
SMALL PUBLIC API
+
ASYNC-FIRST
+
TYPED MODELS
+
OPAQUE IDS
+
STABLE ERROR CODES
+
VERSIONED EVENTS
+
IDEMPOTENCY
+
EXPLICIT COMPATIBILITY
+
SEMVER
+
CONTROLLED EXTENSIONS
```

Les distinctions centrales sont :

```text
PUBLIC API
≠
INTERNAL IMPLEMENTATION

CLIENT TIMEOUT
≠
EFFECT FAILURE

WAITING
≠
ERROR

UNKNOWN
≠
FAILED

SYNC FACADE
≠
DIFFERENT SEMANTICS
```

Le principe fondamental reste :

> **L’API publique doit rendre simples les bons usages sans rendre possibles, par accident, les usages qui contournent les garanties de PyAgentsKit.**

Le document suivant naturel est :

```text
../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md
```
