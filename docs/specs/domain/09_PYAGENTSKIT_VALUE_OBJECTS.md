# PyAgentsKit — Value Objects

**Document :** `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Modèle métier — Value Objects  
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
- `../domain/PYAGENTSKIT_MODELE_CONCEPTUEL_DU_DOMAINE.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`

---

# 1. Objet du document

Ce document formalise les **Value Objects** du domaine PyAgentsKit.

Un Value Object est un objet métier :

- sans identité propre durable ;
- défini par sa valeur ;
- généralement immuable ;
- comparable par contenu ;
- remplaçable par une valeur équivalente ;
- utilisé pour renforcer la sémantique du domaine.

Exemple :

```text
FencingToken(42)
```

n’est pas une entité. Ce qui importe est sa valeur et les règles associées.

---

# 2. Distinction Entité / Value Object

## Entité

```text
Run
Effect
Approval
Lease
Message
```

possède une identité stable.

## Value Object

```text
RunState
EffectStatus
FencingToken
IdempotencyKey
ExternalReference
```

est défini par sa valeur.

---

# 3. Principes de conception

Les Value Objects de PyAgentsKit doivent tendre vers :

```text
immutability
explicit validation
semantic typing
serialization stability
small scope
no infrastructure dependency
```

---

# 4. Pourquoi éviter les primitives nues

Mauvais :

```python
fencing_token: int
```

Meilleur :

```python
fencing_token: FencingToken
```

Mauvais :

```python
status: str
```

Meilleur :

```python
status: EffectStatus
```

Mauvais :

```python
idempotency_key: str
```

Meilleur :

```python
idempotency_key: IdempotencyKey
```

---

# 5. Vue d’ensemble

Les Value Objects sont regroupés en huit familles :

```text
A. Lifecycle & Status
B. Identity & References
C. Effect Safety
D. Coordination
E. Conversation
F. Governance
G. Runtime & Recovery
H. Correlation & Observability
```

---

# 6. A — Lifecycle & Status

## 6.1 `RunState`

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

Les transitions sont validées par le domaine, pas par le Value Object seul.

## 6.2 `ConversationStatus`

```text
OPEN
PAUSED
CLOSED
ARCHIVED
```

## 6.3 `EffectStatus`

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

Principe fondamental :

```text
UNKNOWN != FAILED
```

## 6.4 `ApprovalStatus`

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

## 6.5 `LeaseStatus`

```text
ACQUIRED
ACTIVE
LOST
EXPIRED
RELEASED
TAKEN_OVER
```

## 6.6 `WorkerStatus`

```text
STARTING
READY
BUSY
DRAINING
UNHEALTHY
STOPPED
```

## 6.7 `RuntimeInvocationStatus`

```text
CREATED
STARTED
WAITING
COMPLETED
FAILED
CANCELLED
```

## 6.8 `ReconciliationStatus`

```text
PENDING
RUNNING
RESOLVED_SUCCESS
RESOLVED_FAILURE
MANUAL_REVIEW
FAILED
```

---

# 7. B — Identity & References

## 7.1 `ExternalReference`

Référence stable provenant d’un système externe.

```text
system
kind
value
```

Exemples :

```text
github / pull_request / 742
stripe / payment / pi_123
registry / package_version / pyagentskit:1.0.0
```

Invariants :

```text
Une référence externe ne remplace jamais l’identité PyAgentsKit.
Le namespace système doit être explicite.
```

## 7.2 `ResourceIdentity`

Identifie une ressource coordonnée ou protégée.

```text
resource_type
resource_id
namespace?
```

Exemples :

```text
run / run_123
repository_branch / org/repo:main
workspace / ws_42
deployment_environment / prod-eu
```

## 7.3 `RuntimeHandle`

Référence opaque vers une exécution runtime externe.

```text
adapter_name
external_id
metadata
```

Principe :

```text
opaque to core
```

## 7.4 `RuntimeCheckpointReference`

Référence opaque vers un checkpoint natif du runtime.

## 7.5 `ArtifactReference`

```text
artifact_id
uri?
checksum?
```

## 7.6 `ActorReference`

```text
actor_id
actor_type
external_identity_reference?
```

---

# 8. C — Effect Safety

## 8.1 `IdempotencyKey`

Identifie une intention logique unique.

```text
namespace
key
```

Exemple :

```text
tenant-42 / run123:send_invoice:customer42
```

Invariants :

```text
La clé est stable pour le même effet logique.
Deux effets différents ne partagent pas la même clé dans le même scope.
```

## 8.2 `IdempotencyScope`

```text
GLOBAL
TENANT
RUN
TOOL
EXTERNAL_SYSTEM
CUSTOM
```

## 8.3 `InputFingerprint`

Empreinte canonique des inputs significatifs d’un effet.

Elle sert à détecter :

```text
same idempotency key
+
different logical payload
```

## 8.4 `EffectRiskLevel`

```text
LOW
MEDIUM
HIGH
CRITICAL
```

## 8.5 `EffectKind`

Nom logique extensible d’un type d’effet.

Exemples :

```text
github.git_push
github.merge_pull_request
registry.publish_package
cloud.deploy
erp.create_invoice
```

## 8.6 `EffectOutcome`

```text
SUCCESS
FAILURE
UNKNOWN
RECONCILED_SUCCESS
RECONCILED_FAILURE
MANUAL_RESOLUTION
```

## 8.7 `SideEffectControlLevel`

```text
OBSERVE_ONLY
LOCAL_CONTROL
FULL_TOOL_CONTROL
```

## 8.8 `FencingGrade`

```text
NONE
LOCAL_GUARD
STORE_GUARD
REMOTE_GUARD
```

## 8.9 `SafetyProfile`

Décrit les garanties disponibles pour une intégration.

```text
idempotency_supported
lookup_supported
external_reference_supported
fencing_grade
compensation_supported
control_level
```

## 8.10 `ReconciliationResult`

```text
CONFIRMED_SUCCESS
CONFIRMED_FAILURE
STILL_UNKNOWN
MANUAL_REVIEW
```

## 8.11 `EffectSource`

```text
RUNTIME_TOOL
HUMAN_COMMAND
SYSTEM_EVENT
RECOVERY
SCHEDULER
CUSTOM
```

## 8.12 `EffectTarget`

```text
system
resource_type
resource_id?
environment?
```

---

# 9. D — Coordination

## 9.1 `FencingToken`

Jeton monotone représentant l’ordre des ownerships successifs.

```text
value: integer
```

Invariants :

```text
Un token plus récent est strictement supérieur au précédent pour une même ressource.
Un token obsolète ne doit pas autoriser un Protected Effect.
```

## 9.2 `OwnershipContext`

```text
worker_id
lease_id
resource_identity
fencing_token
expires_at
```

## 9.3 `LeaseDuration`

Durée de validité logique d’un Lease.

Contraintes :

```text
positive
bounded
explicit unit
```

## 9.4 `HeartbeatInterval`

Intervalle nominal de renouvellement/heartbeat.

Il doit être inférieur au TTL dans une configuration valide.

## 9.5 `ConcurrencyVersion`

Version utilisée pour optimistic concurrency.

```text
integer >= 0
```

## 9.6 `WorkerCapability`

Exemples :

```text
runtime:langgraph
runtime:codex
tool_interception
gpu
workspace
shell
```

---

# 10. E — Conversation

## 10.1 `MessageType`

```text
TEXT
INSTRUCTION
RESPONSE
QUESTION
NOTIFICATION
STATUS
ERROR
SYSTEM
HANDOFF
```

## 10.2 `MessageContent`

Contenu logique d’un message indépendamment du fournisseur.

Formes possibles :

```text
text
structured payload
mixed content
references
attachments
```

Le domaine ne dépend pas directement d’un objet message OpenAI, Anthropic ou runtime-specific.

## 10.3 `MessageReference`

Types possibles :

```text
RUN
EFFECT
APPROVAL
ARTIFACT
MESSAGE
EXTERNAL_DOCUMENT
CUSTOM
```

## 10.4 `ConversationContext`

```text
conversation_id
session_id
participant_references
recent_message_references
metadata
```

## 10.5 `ParticipantRole`

```text
OWNER
MEMBER
OBSERVER
APPROVER
AGENT
SYSTEM
```

## 10.6 `MessageDeduplicationKey`

Clé optionnelle pour protéger contre :

```text
runtime replay
transport redelivery
agent duplicate emission
```

---

# 11. F — Governance

## 11.1 `ApprovalDecision`

```text
decision
actor_reference
reason?
decided_at
```

Valeurs :

```text
APPROVE
REJECT
CANCEL
```

## 11.2 `PolicyDecision`

```text
ALLOW
DENY
REQUIRE_APPROVAL
DEFER
```

## 11.3 `ApprovalScope`

```text
action
resource?
environment?
input_fingerprint?
effect_id?
```

## 11.4 `ApprovalValidity`

```text
valid_from
valid_until?
```

## 11.5 `PrincipalReference`

```text
HUMAN
SERVICE
AGENT
WORKER
SYSTEM
```

---

# 12. G — Runtime & Recovery

## 12.1 `RuntimeCapability`

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

## 12.2 `RuntimeDescriptor`

```text
adapter_name
runtime_family
runtime_name
runtime_version?
adapter_version
capabilities
```

## 12.3 `RuntimeStatus`

```text
CREATED
STARTING
RUNNING
WAITING
COMPLETED
FAILED
CANCELLED
UNKNOWN
```

## 12.4 `RuntimeInvocationType`

```text
START
RESUME
CONTINUE
CANCEL
```

## 12.5 `RuntimeEventType`

```text
RUNTIME_STARTED
RUNTIME_WAITING
RUNTIME_RESUMED
RUNTIME_COMPLETED
RUNTIME_FAILED
MESSAGE_EMITTED
MESSAGE_RECEIVED
TOOL_REQUESTED
TOOL_STARTED
TOOL_COMPLETED
TOOL_FAILED
CHECKPOINT_AVAILABLE
APPROVAL_REQUESTED
SUBAGENT_STARTED
SUBAGENT_COMPLETED
STDOUT
STDERR
DIAGNOSTIC
```

## 12.6 `NextAction`

```text
ACQUIRE_LEASE
WAIT_FOR_APPROVAL
RECONCILE_EFFECT
RESUME_RUNTIME
COMPLETE_RUN
FAIL_RUN
MANUAL_INTERVENTION
```

## 12.7 `RecoveryPlan`

Statut : Value Object calculé ou objet métier éphémère.

```text
run_id
checkpoint_reference?
next_action
unresolved_effect_ids
pending_approval_ids
lease_required
blockers
metadata
```

## 12.8 `RecoveryBlocker`

```text
PENDING_APPROVAL
UNKNOWN_EFFECT
LEASE_UNAVAILABLE
STORE_UNAVAILABLE
RUNTIME_UNAVAILABLE
MANUAL_INTERVENTION
```

---

# 13. H — Correlation & Observability

## 13.1 `CorrelationContext`

```text
trace_id?
correlation_id?
run_id?
session_id?
conversation_id?
message_id?
effect_id?
approval_id?
worker_id?
runtime_invocation_id?
```

Le contexte de corrélation accompagne une opération mais n’est pas une entité.

## 13.2 `TraceContext`

```text
trace_id
span_id?
parent_span_id?
```

## 13.3 `AuditObjectReference`

```text
object_type
object_id
```

## 13.4 `EventName`

Exemples :

```text
run.started
effect.succeeded
approval.approved
lease.taken_over
message.appended
```

## 13.5 `Metadata`

Petit ensemble clé/valeur extensible.

Principe : `Metadata` ne doit pas devenir un substitut au modèle métier.

---

# 14. Value Objects de temps

## 14.1 `TimeWindow`

```text
start
end
```

## 14.2 `Deadline`

```text
timestamp
```

## 14.3 `RetryBudget`

```text
max_attempts
max_elapsed_time?
```

## 14.4 `BackoffPolicy`

```text
initial_delay
max_delay
multiplier
jitter
```

## 14.5 `RetentionPolicy`

```text
retention_duration
archive_after?
delete_after?
```

---

# 15. Value Objects d’erreur

## 15.1 `FailureDescriptor`

```text
error_type
message
retryable
category
details_reference?
```

## 15.2 `FailureCategory`

```text
DOMAIN
VALIDATION
CONCURRENCY
RUNTIME
EXTERNAL_SYSTEM
SECURITY
PERSISTENCE
TIMEOUT
UNKNOWN
```

## 15.3 `Retryability`

```text
RETRYABLE
NON_RETRYABLE
UNKNOWN
```

---

# 16. Value Objects de sécurité

## 16.1 `AuthorizationDecision`

```text
ALLOW
DENY
```

## 16.2 `Permission`

Exemples :

```text
run.cancel
effect.execute
approval.decide
lease.takeover
artifact.read
```

## 16.3 `SecretReference`

Référence vers un secret externalisé.

Exemple :

```text
vault://prod/github/token
```

Le secret lui-même ne fait pas partie du Value Object.

---

# 17. Value Objects de storage

## 17.1 `StorageUri`

```text
s3://bucket/key
az://container/blob
file:///path
```

## 17.2 `Checksum`

```text
algorithm
value
```

## 17.3 `ContentType`

Exemples :

```text
application/json
text/markdown
application/pdf
```

---

# 18. Immutabilité

Les Value Objects doivent être immuables lorsque possible.

```python
@dataclass(frozen=True)
class FencingToken:
    value: int
```

---

# 19. Validation à la construction

Un Value Object invalide ne devrait idéalement jamais exister.

```text
FencingToken(-1)
→ invalide
```

---

# 20. Égalité par valeur

```text
FencingToken(42) == FencingToken(42)
```

Contrairement aux entités, l’égalité repose sur le contenu.

---

# 21. Hashabilité

Les Value Objects immuables peuvent être hashables lorsque leur structure le permet.

---

# 22. Sérialisation

Les Value Objects persistables doivent disposer d’une représentation stable et idéalement JSON-compatible.

Exemple :

```json
{
  "system": "github",
  "kind": "pull_request",
  "value": "742"
}
```

---

# 23. Compatibilité ascendante

Éviter de modifier silencieusement la signification d’une valeur persistée.

---

# 24. Parsing

Les Value Objects exposés aux APIs peuvent offrir :

```text
parse()
from_string()
to_string()
```

sans exposer la persistence interne.

---

# 25. Enums vs classes

## Enum adapté pour

```text
RunState
ApprovalStatus
EffectRiskLevel
PolicyDecision
```

## Classe Value Object adaptée pour

```text
IdempotencyKey
ExternalReference
OwnershipContext
CorrelationContext
Checksum
```

---

# 26. Enums extensibles

Attention aux enums lorsque l’écosystème doit permettre des extensions.

`EffectKind` peut être mieux représenté par une chaîne validée et namespacée qu’un enum fermé.

---

# 27. Namespacing

Pour les valeurs extensibles :

```text
github.merge_pull_request
aws.deploy
erp.create_invoice
```

est préférable à une liste centrale fermée.

---

# 28. Value Objects et persistence

Le store peut sérialiser un Value Object en :

```text
column
JSONB
composite structure
```

sans modifier son sens métier.

---

# 29. Mapping PostgreSQL indicatif

```text
RunState            → VARCHAR / ENUM DB
FencingToken        → BIGINT
CorrelationContext  → JSONB
ExternalReference   → JSONB ou colonnes structurées
IdempotencyKey      → namespace + value
InputFingerprint    → VARCHAR / BYTEA
```

Le choix physique sera défini dans le modèle PostgreSQL.

---

# 30. Value Objects et APIs publiques

Les APIs publiques doivent éviter les strings arbitraires lorsque des règles existent.

```python
effect = await effects.prepare(
    kind=EffectKind("github.git_push"),
    idempotency_key=IdempotencyKey(...),
)
```

---

# 31. Value Objects et Domain Events

Les DomainEvents peuvent embarquer des Value Objects.

```text
EffectStarted(
    effect_id,
    risk_level,
    ownership_context,
    correlation_context
)
```

---

# 32. Value Objects et audit

Les objets sérialisés dans l’audit doivent conserver leur contexte.

Une `ExternalReference` doit conserver :

```text
system
kind
value
```

et non simplement :

```text
742
```

---

# 33. Value Objects et sécurité

Utiliser :

```text
SecretReference
```

plutôt que stocker une valeur secrète dans le domaine.

---

# 34. Value Objects et multi-tenancy

Les identités logiques telles que :

```text
IdempotencyKey
ResourceIdentity
ExternalReference
```

doivent pouvoir être namespacées par tenant ou organisation.

---

# 35. Value Objects spécifiques aux coding agents

Extensions possibles :

```text
RepositoryReference
BranchReference
WorkspaceReference
CommitReference
PullRequestReference
```

Ces objets doivent rester hors du core s’ils sont uniquement utiles aux coding agents.

---

# 36. `RepositoryReference`

```text
provider
owner
repository
```

---

# 37. `BranchReference`

```text
repository_reference
branch_name
```

---

# 38. `CommitReference`

```text
repository_reference
commit_sha
```

---

# 39. `PullRequestReference`

```text
provider
repository_reference
number
```

---

# 40. Quand NE PAS créer un Value Object

Éviter un Value Object si :

```text
la donnée n’a aucune règle métier
la structure n’est utilisée qu’une fois
la primitive est suffisamment claire
l’abstraction n’apporte aucun invariant
```

---

# 41. Anti-pattern — Primitive Obsession

Mauvais :

```python
def execute(status: str, token: int, key: str, reference: str):
    ...
```

Préférer :

```python
def execute(
    status: EffectStatus,
    token: FencingToken,
    key: IdempotencyKey,
    reference: ExternalReference,
):
    ...
```

---

# 42. Anti-pattern — Value Object avec identité

Si un objet nécessite :

```text
object_id
lookup indépendant
cycle de vie propre
```

il est probablement une entité.

---

# 43. Anti-pattern — Mutable Value Object

Éviter :

```python
ownership_context.fencing_token = 42
```

Préférer créer un nouvel objet.

---

# 44. Anti-pattern — Metadata Object

Ne pas créer des Value Objects uniquement pour déplacer des dictionnaires arbitraires.

---

# 45. Invariants transverses

```text
VO-INV-01
Un Value Object est défini par sa valeur.

VO-INV-02
Un Value Object ne possède pas d’identité métier propre.

VO-INV-03
Les Value Objects critiques sont validés à la construction.

VO-INV-04
Les Value Objects persistables ont une représentation stable.

VO-INV-05
Les Value Objects ne dépendent pas de l’infrastructure.

VO-INV-06
Les Value Objects sensibles évitent d’embarquer des secrets en clair.
```

---

# 46. Matrice Value Objects ↔ Entités

| Value Object | Entités principales |
|---|---|
| RunState | Run |
| ConversationStatus | Conversation |
| MessageType | Message |
| MessageContent | Message |
| MessageReference | Message |
| EffectStatus | Effect |
| EffectRiskLevel | Effect |
| IdempotencyKey | Effect |
| InputFingerprint | Effect |
| ExternalReference | Effect, Artifact |
| ApprovalStatus | Approval |
| ApprovalDecision | Approval |
| PolicyDecision | Approval / Effect |
| LeaseStatus | Lease |
| FencingToken | Lease / Effect |
| OwnershipContext | Lease / Effect |
| ResourceIdentity | Lease |
| RuntimeHandle | RuntimeInvocation |
| RuntimeStatus | RuntimeInvocation |
| RuntimeCapability | RuntimeBinding / Adapter |
| CorrelationContext | Message / Run / Effect / Audit |
| NextAction | RecoveryPlan |

---

# 47. Matrice Value Objects ↔ Ports

| Value Object | Port principalement concerné |
|---|---|
| IdempotencyKey | EffectStore |
| ExternalReference | EffectStore |
| OwnershipContext | LeaseStore / EffectExecutor |
| FencingToken | LeaseStore / ToolGateway |
| CorrelationContext | TelemetryPort / AuditStore |
| RuntimeHandle | RuntimeStore / AgentRuntimeAdapter |
| MessageContent | MessageStore |
| SecretReference | SecretProviderPort |
| Checksum | ArtifactStore |

---

# 48. Priorités

## P0 — cœur

```text
RunState
EffectStatus
ApprovalStatus
LeaseStatus
FencingToken
IdempotencyKey
InputFingerprint
ExternalReference
OwnershipContext
ResourceIdentity
CorrelationContext
NextAction
```

## P1 — contexte et intégration

```text
ConversationStatus
MessageType
MessageContent
MessageReference
RuntimeCapability
RuntimeDescriptor
RuntimeHandle
RuntimeStatus
ApprovalDecision
PolicyDecision
EffectRiskLevel
SafetyProfile
ReconciliationResult
```

## P2 — extensions

```text
MessageDeduplicationKey
EffectTarget
EffectSource
ApprovalScope
ApprovalValidity
RetryBudget
BackoffPolicy
RetentionPolicy
FailureDescriptor
RepositoryReference
BranchReference
CommitReference
PullRequestReference
```

---

# 49. Exemple Python — `FencingToken`

```python
from dataclasses import dataclass

@dataclass(frozen=True, order=True)
class FencingToken:
    value: int

    def __post_init__(self) -> None:
        if self.value < 0:
            raise ValueError("fencing token must be >= 0")
```

---

# 50. Exemple Python — `IdempotencyKey`

```python
@dataclass(frozen=True)
class IdempotencyKey:
    namespace: str
    value: str

    def __post_init__(self) -> None:
        if not self.namespace:
            raise ValueError("namespace is required")
        if not self.value:
            raise ValueError("value is required")
```

---

# 51. Exemple Python — `ExternalReference`

```python
@dataclass(frozen=True)
class ExternalReference:
    system: str
    kind: str
    value: str
```

---

# 52. Exemple Python — `OwnershipContext`

```python
@dataclass(frozen=True)
class OwnershipContext:
    worker_id: str
    lease_id: str
    resource: ResourceIdentity
    fencing_token: FencingToken
    expires_at: datetime
```

---

# 53. Exemple Python — `CorrelationContext`

```python
@dataclass(frozen=True)
class CorrelationContext:
    trace_id: str | None = None
    correlation_id: str | None = None
    run_id: str | None = None
    session_id: str | None = None
    conversation_id: str | None = None
    message_id: str | None = None
    effect_id: str | None = None
```

---

# 54. Validation fonctionnelle

Le Value Object valide sa structure ; le Domain Service valide son contexte métier.

Exemple :

```text
FencingToken(42)
```

peut être valide en soi, mais obsolète si la ressource est déjà à `43`.

Cette vérification appartient au `FencingValidator`.

---

# 55. Value Objects et transitions

`RunState` connaît les valeurs possibles.

`RunTransitionService` décide si :

```text
RUNNING → SUCCEEDED
```

est autorisé.

---

# 56. Value Objects et recovery

`RecoveryPlan` compose notamment :

```text
NextAction
RecoveryBlocker
RuntimeCheckpointReference
OwnershipContext
```

pour rendre la reprise explicite.

---

# 57. Value Objects et Side-Effect Safety

Le cœur de la sûreté d’un Effect repose notamment sur :

```text
IdempotencyKey
InputFingerprint
ExternalReference
EffectRiskLevel
OwnershipContext
FencingToken
SafetyProfile
```

---

# 58. Value Objects et runtime adapters

Le contrat adapter s’appuie sur :

```text
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeStatus
RuntimeEventType
CorrelationContext
```

---

# 59. Value Objects et conversation

La couche conversationnelle s’appuie sur :

```text
ConversationStatus
MessageType
MessageContent
MessageReference
ParticipantRole
ConversationContext
```

---

# 60. Value Objects et governance

```text
ApprovalStatus
ApprovalDecision
ApprovalScope
ApprovalValidity
PolicyDecision
AuthorizationDecision
PrincipalReference
```

---

# 61. Value Objects et coordination

```text
LeaseStatus
ResourceIdentity
FencingToken
OwnershipContext
LeaseDuration
HeartbeatInterval
ConcurrencyVersion
```

---

# 62. Value Objects et observabilité

```text
CorrelationContext
TraceContext
AuditObjectReference
EventName
FailureDescriptor
```

---

# 63. Questions ouvertes

```text
Q-VO-01 RuntimeHandle doit-il être dans le core ou le module runtime ?
Q-VO-02 RecoveryPlan est-il réellement un Value Object ?
Q-VO-03 MessageReference doit-il devenir une abstraction générique ?
Q-VO-04 EffectKind : string namespacée ou enum extensible ?
Q-VO-05 EventName : type dédié ou string validée ?
Q-VO-06 SafetyProfile doit-il être exposé dans le core public ?
Q-VO-07 ApprovalScope doit-il inclure systématiquement input_fingerprint ?
Q-VO-08 faut-il introduire TenantReference maintenant ?
Q-VO-09 MessageDeduplicationKey doit-il entrer dans le MVP ?
Q-VO-10 ConcurrencyVersion appartient-il au domaine ou uniquement au store ?
```

---

# 64. ADR induits

```text
ADR-VO-001 Value Object immutability policy
ADR-VO-002 String-backed extensible value types
ADR-VO-003 IdempotencyKey structure
ADR-VO-004 ExternalReference structure
ADR-VO-005 OwnershipContext structure
ADR-VO-006 CorrelationContext schema
ADR-VO-007 RuntimeHandle persistence format
ADR-VO-008 Effect SafetyProfile exposure
ADR-VO-009 MessageContent normalized model
ADR-VO-010 RecoveryPlan classification
```

---

# 65. Definition of Done

Le modèle de Value Objects est considéré mature lorsque :

1. les statuts critiques utilisent des types dédiés ;
2. les idempotency keys ne sont plus des strings arbitraires ;
3. le fencing token est typé explicitement ;
4. les external references sont namespacées ;
5. l’ownership est transporté dans un objet cohérent ;
6. le contexte de corrélation est standardisé ;
7. le contrat runtime utilise des types normalisés ;
8. les messages utilisent un contenu indépendant du fournisseur ;
9. les approvals utilisent une décision structurée ;
10. les Value Objects persistés sont sérialisables de manière stable ;
11. les invariants sont testés ;
12. aucune abstraction n’est ajoutée sans règle métier claire.

---

# 66. Résumé

Les Value Objects de PyAgentsKit transforment des primitives ambiguës en concepts métier explicites.

Le noyau prioritaire est :

```text
RunState
EffectStatus
ApprovalStatus
LeaseStatus

FencingToken
IdempotencyKey
InputFingerprint
ExternalReference
ResourceIdentity
OwnershipContext

CorrelationContext
RuntimeHandle
RuntimeCapability

MessageContent
MessageReference

PolicyDecision
ApprovalDecision
NextAction
```

La règle directrice est :

> **Dès qu’une valeur porte un invariant, une unité, un namespace ou une sémantique importante pour la fiabilité, elle mérite d’être représentée autrement qu’une primitive nue.**

Avec ce document, la séquence documentaire `00 → 13` devient cohérente avant de poursuivre avec :

```text
../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md
```
