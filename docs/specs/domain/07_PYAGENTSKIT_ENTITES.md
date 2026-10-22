# PyAgentsKit — Entités du domaine

**Document :** `../domain/07_PYAGENTSKIT_ENTITES.md`  
**Version :** 1.0  
**Date :** 19 octobre 2026  
**Statut :** Modèle métier — Entités  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/02_PYAGENTSKIT_PARTIES_PRENANTES_ET_CAS_D_USAGE.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`

---

# 1. Objet du document

Ce document formalise les **entités métier** de PyAgentsKit.

Une entité est ici un objet du domaine qui :

- possède une identité stable ;
- conserve cette identité au cours du temps ;
- dispose éventuellement d’un cycle de vie ;
- peut changer d’état sans cesser d’être la même entité ;
- peut être référencée par d’autres objets du domaine.

Exemple :

```text
Run R-123
```

reste le même `Run` lorsqu’il passe de :

```text
CREATED
→ RUNNING
→ WAITING
→ RUNNING
→ SUCCEEDED
```

Le présent document distingue volontairement :

```text
ENTITÉS
= identité + cycle de vie

VALUE OBJECTS
= définis essentiellement par leur valeur

SERVICES MÉTIER
= comportements ne relevant pas naturellement d’une entité
```

---

# 2. Principes de modélisation des entités

## 2.1 Identité stable

Toute entité doit disposer d’un identifiant métier ou technique stable.

Exemples :

```text
run_id
session_id
conversation_id
message_id
effect_id
approval_id
lease_id
artifact_id
worker_id
```

## 2.2 Identité différente de l’état

L’identité ne doit pas dépendre du statut courant.

## 2.3 Cycle de vie explicite

Lorsqu’une entité possède plusieurs états métier, ils doivent être représentés explicitement.

## 2.4 Invariants protégés

Une entité ne doit pas pouvoir entrer dans un état métier invalide.

## 2.5 Indépendance de la persistence

Une entité n’est pas une ligne PostgreSQL, un objet S3 ou un document technique. La persistence est externe au domaine.

---

# 3. Vue d’ensemble des entités

Les entités candidates de PyAgentsKit sont regroupées en huit domaines :

```text
A. Exécution
B. Conversation & contexte
C. Effets
D. Gouvernance
E. Coordination distribuée
F. Runtime agentique
G. Audit & observabilité métier
H. Extensions spécialisées
```

Vue synthétique :

```text
Session
 ├── Conversation
 │    ├── Participant
 │    └── Message
 ├── Run
 │    ├── Checkpoint
 │    ├── Effect
 │    │    └── ReconciliationCase
 │    ├── Approval
 │    ├── Artifact
 │    ├── RuntimeInvocation
 │    └── AuditEvent
 └── MemoryEntry

Run
 └── Lease
      └── Worker

Run
 └── RuntimeBinding
```

---

# 4. Classification des entités

## 4.1 Entités cœur P0

```text
Run
Checkpoint
Effect
Approval
Lease
Worker
AuditEvent
```

## 4.2 Entités cœur P1

```text
Session
Conversation
Message
Participant
MemoryEntry
Artifact
RuntimeBinding
RuntimeInvocation
ReconciliationCase
```

## 4.3 Entités d’extension P2

```text
CodingWorkspace
CodeChange
RepositoryResource
```

---

# 5. Entité `Run`

## Définition

Un `Run` représente une exécution durable d’un agent ou d’un runtime agentique.

## Identité

```text
run_id
```

## Attributs conceptuels

```text
run_id
session_id?
runtime_binding_id
status
created_at
started_at?
updated_at
completed_at?
metadata
result_reference?
error_reference?
```

## États

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

## Relations

```text
Run
 ├── 0..N Checkpoint
 ├── 0..N Effect
 ├── 0..N Approval
 ├── 0..N Artifact
 ├── 0..N RuntimeInvocation
 ├── 0..N AuditEvent
 └── 0..1 active Lease
```

## Invariants

```text
RUN-ENT-INV-01
run_id est stable.

RUN-ENT-INV-02
un état terminal ne redevient pas actif implicitement.

RUN-ENT-INV-03
toute transition doit être valide.

RUN-ENT-INV-04
un run ne peut posséder qu’un seul état courant.

RUN-ENT-INV-05
une reprise doit tenir compte des effects, approvals et checkpoints existants.
```

## Port potentiel

```text
RunStore
```

---

# 6. Entité `Session`

## Définition

Une `Session` représente un contexte durable regroupant plusieurs runs, conversations et éléments de mémoire.

## Identité

```text
session_id
```

## Attributs

```text
session_id
status
created_at
updated_at
metadata
```

## Relations

```text
Session
 ├── 0..N Run
 ├── 0..N Conversation
 └── 0..N MemoryEntry
```

## Invariants

```text
SESSION-INV-01
session_id est stable.

SESSION-INV-02
les runs appartenant à la session conservent leur identité propre.

SESSION-INV-03
la session ne remplace pas le cycle de vie d’un run.
```

## Port

```text
SessionStore
```

---

# 7. Entité `Conversation`

## Définition

Une `Conversation` représente un fil durable d’échanges entre humains, agents, systèmes ou services.

## Identité

```text
conversation_id
```

## Attributs

```text
conversation_id
session_id
status
created_at
updated_at
metadata
```

## États

```text
OPEN
PAUSED
CLOSED
ARCHIVED
```

## Relations

```text
Conversation
 ├── 1..N Participant
 └── 0..N Message
```

## Invariants

```text
CONV-ENT-INV-01
une conversation possède une identité stable.

CONV-ENT-INV-02
elle appartient à une session ou à un contexte explicitement défini.

CONV-ENT-INV-03
un message appartient exactement à une conversation.

CONV-ENT-INV-04
le transport physique ne définit pas l’identité de la conversation.
```

## Port

```text
ConversationStore
```

---

# 8. Entité `Message`

## Définition

Un `Message` représente une unité durable d’échange entre participants.

## Identité

```text
message_id
```

## Attributs

```text
message_id
conversation_id
session_id
run_id?
sender_actor_id
message_type
content
parent_message_id?
correlation_id?
created_at
metadata
```

## Relations

```text
Message
 ├── 1 sender Actor
 ├── 1..N recipient Actor
 ├── 0..1 parent Message
 ├── 0..N MessageReference
 └── 0..N Artifact
```

## Invariants

```text
MSG-ENT-INV-01
message_id est stable.

MSG-ENT-INV-02
un message appartient à une conversation.

MSG-ENT-INV-03
un message possède un seul sender logique.

MSG-ENT-INV-04
un message durable ne doit pas être modifié silencieusement.

MSG-ENT-INV-05
un message n’est pas automatiquement une ApprovalDecision.

MSG-ENT-INV-06
un message n’est pas automatiquement un RuntimeEvent.

MSG-ENT-INV-07
le replay technique ne doit pas produire un nouveau message logique sans intention explicite.
```

## Port

```text
MessageStore
```

---

# 9. Entité `Participant`

## Définition

Un `Participant` représente la présence d’un `Actor` dans une conversation donnée.

## Identité

```text
participant_id
```

## Attributs

```text
participant_id
conversation_id
actor_id
role
joined_at
left_at?
metadata
```

## Rôles possibles

```text
OWNER
MEMBER
OBSERVER
APPROVER
AGENT
SYSTEM
```

## Invariants

```text
PART-INV-01
un participant référence un Actor identifiable.

PART-INV-02
un même Actor peut participer à plusieurs conversations.

PART-INV-03
la participation ne modifie pas l’identité de l’Actor.
```

---

# 10. Entité `MemoryEntry`

## Définition

Une `MemoryEntry` représente une unité persistante de mémoire réutilisable au-delà d’un run.

## Identité

```text
memory_id
```

## Attributs

```text
memory_id
scope
scope_id
key
value
version
created_at
updated_at
metadata
```

## Invariants

```text
MEM-INV-01
une entrée possède un scope explicite.

MEM-INV-02
les mises à jour concurrentes ne doivent pas s’écraser silencieusement.

MEM-INV-03
MemoryEntry != RunState.
```

## Port

```text
MemoryStore
```

---

# 11. Entité `Checkpoint`

## Définition

Un `Checkpoint` représente un état durable validé permettant la reprise d’un run.

## Identité

```text
checkpoint_id
```

## Attributs

```text
checkpoint_id
run_id
sequence
created_at
state_payload
runtime_state_reference?
metadata
```

## Invariants

```text
CHK-ENT-INV-01
un checkpoint appartient à un run.

CHK-ENT-INV-02
les checkpoints d’un run sont ordonnés.

CHK-ENT-INV-03
un checkpoint validé est immuable.

CHK-ENT-INV-04
un checkpoint ne peut pas référencer un état futur du run.
```

## Port

```text
CheckpointStore
```

ou `RunStore` selon la décision d’architecture.

---

# 12. Entité `Effect`

## Définition

Un `Effect` représente une action provoquant une conséquence observable à l’extérieur de l’exécution interne.

## Identité

```text
effect_id
```

## Attributs

```text
effect_id
run_id
kind
status
idempotency_key?
input_fingerprint?
external_reference?
fencing_token?
created_at
started_at?
completed_at?
metadata
```

## États

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

## Relations

```text
Effect
 ├── 1 Run
 ├── 0..1 Approval
 ├── 0..1 ExternalReference
 └── 0..N ReconciliationCase
```

## Invariants

```text
EFFECT-ENT-INV-01
effect_id est stable.

EFFECT-ENT-INV-02
un effet appartient à un run.

EFFECT-ENT-INV-03
SUCCEEDED ne doit pas être rejoué implicitement.

EFFECT-ENT-INV-04
UNKNOWN != FAILED.

EFFECT-ENT-INV-05
une même idempotency key ne doit pas représenter deux intentions incompatibles.

EFFECT-ENT-INV-06
si fencing est requis, un token obsolète doit être rejeté.
```

## Port

```text
EffectStore
```

---

# 13. Entité `ReconciliationCase`

## Définition

Un `ReconciliationCase` représente le traitement nécessaire pour déterminer l’état réel d’un effet ambigu.

## Identité

```text
reconciliation_id
```

## Attributs

```text
reconciliation_id
effect_id
status
strategy
attempt_count
created_at
resolved_at?
resolution?
metadata
```

## États

```text
PENDING
RUNNING
RESOLVED_SUCCESS
RESOLVED_FAILURE
MANUAL_REVIEW
FAILED
```

## Invariants

```text
REC-INV-01
un cas appartient à un Effect.

REC-INV-02
une résolution finale doit être traçable.

REC-INV-03
un effet UNKNOWN ne doit pas être relancé avant décision de reconciliation si la policy l’interdit.
```

---

# 14. Entité `Approval`

## Définition

Une `Approval` représente une décision humaine explicitement requise.

## Identité

```text
approval_id
```

## Attributs

```text
approval_id
run_id
effect_id?
action
status
requested_by
requested_at
expires_at?
decided_by?
decided_at?
reason?
metadata
```

## États

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

## Invariants

```text
APP-INV-01
une approval possède une identité stable.

APP-INV-02
un acteur non autorisé ne peut pas valider une approval protégée.

APP-INV-03
une approval terminale ne change pas silencieusement de décision.

APP-INV-04
un message libre ne vaut pas ApprovalDecision sans conversion explicite.
```

## Port

```text
ApprovalStore
```

---

# 15. Entité `Artifact`

## Définition

Un `Artifact` représente un résultat ou fichier produit, consommé ou référencé par un run.

## Identité

```text
artifact_id
```

## Attributs

```text
artifact_id
run_id
type
uri
content_type?
size?
checksum?
created_at
metadata
```

## Exemples

```text
PDF
CSV
image
ZIP
notebook
report
diff
build package
```

## Port

```text
ArtifactStore
```

---

# 16. Entité `Lease`

## Définition

Un `Lease` représente un droit temporaire d’exécution sur une ressource logique.

## Identité

```text
lease_id
```

## Attributs

```text
lease_id
resource_type
resource_id
owner_worker_id
fencing_token
acquired_at
renewed_at?
expires_at
status
```

## États

```text
ACQUIRED
ACTIVE
LOST
EXPIRED
RELEASED
TAKEN_OVER
```

## Invariants

```text
LEASE-INV-01
un lease cible exactement une ressource logique.

LEASE-INV-02
un seul lease actif valide est accepté pour une ressource protégée.

LEASE-INV-03
un takeover produit un nouveau fencing token.

LEASE-INV-04
un worker ayant perdu son lease ne peut pas continuer les effets protégés.
```

## Port

```text
LeaseStore
```

---

# 17. Entité `Worker`

## Définition

Un `Worker` représente une instance d’exécution capable de prendre en charge des runs.

## Identité

```text
worker_id
```

## Attributs

```text
worker_id
status
started_at
last_seen_at?
capabilities
metadata
```

## États

```text
STARTING
READY
BUSY
DRAINING
UNHEALTHY
STOPPED
```

## Invariants

```text
WORKER-INV-01
être vivant ne signifie pas posséder un run.

WORKER-INV-02
l’ownership est matérialisé par Lease.

WORKER-INV-03
un worker DRAINING ne doit plus accepter de nouveaux runs.
```

---

# 18. Entité `RuntimeBinding`

## Définition

Un `RuntimeBinding` représente l’association durable entre un run et la configuration du runtime agentique qui l’exécute.

## Identité

```text
runtime_binding_id
```

## Attributs

```text
runtime_binding_id
runtime_type
runtime_version?
configuration_reference?
capabilities
created_at
metadata
```

---

# 19. Entité `RuntimeInvocation`

## Définition

Une `RuntimeInvocation` représente un appel concret au runtime agentique.

## Identité

```text
invocation_id
```

## Types

```text
START
RESUME
CONTINUE
CANCEL
```

## Attributs

```text
invocation_id
run_id
runtime_binding_id
type
status
started_at
completed_at?
metadata
```

## Invariants

```text
RI-INV-01
une invocation appartient à un run.

RI-INV-02
l’échec d’une invocation ne signifie pas automatiquement échec du run.

RI-INV-03
une invocation doit être corrélable aux RuntimeEvents associés.
```

---

# 20. Entité `AuditEvent`

## Définition

Un `AuditEvent` représente un fait durable destiné à reconstruire l’historique métier d’une exécution.

## Identité

```text
audit_event_id
```

## Attributs

```text
audit_event_id
event_type
run_id?
session_id?
actor_id?
object_type?
object_id?
timestamp
payload
correlation_id?
trace_id?
```

## Invariants

```text
AUDIT-INV-01
un AuditEvent persisté est append-oriented.

AUDIT-INV-02
il ne doit pas être réécrit silencieusement.

AUDIT-INV-03
un événement doit être corrélable à l’objet métier concerné.

AUDIT-INV-04
AuditEvent != log technique.
```

## Port

```text
AuditStore
```

---

# 21. Entité `Actor`

## Statut de modélisation

`Actor` peut être une entité PyAgentsKit ou une référence externe vers un système IAM.

## Définition

Un `Actor` représente une identité logique pouvant envoyer ou recevoir un message, prendre une décision, déclencher une action ou apparaître dans l’audit.

## Identité

```text
actor_id
```

## Types

```text
HUMAN
AGENT
SYSTEM
SERVICE
WORKER
SCHEDULER
ADMINISTRATOR
```

## Attributs

```text
actor_id
actor_type
display_name?
external_identity_reference?
metadata
```

PyAgentsKit ne doit pas devenir un IAM.

---

# 22. Entités spécifiques aux coding agents

Ces entités doivent rester dans un module spécialisé ou adapter.

## 22.1 `CodingWorkspace`

Environnement isolé de travail d’un coding agent.

```text
workspace_id
runtime_binding_id
resource_reference
status
created_at
metadata
```

## 22.2 `CodeChange`

Ensemble de changements produits ou proposés par un coding agent.

```text
code_change_id
workspace_id
artifact_reference?
external_reference?
status
metadata
```

## 22.3 `RepositoryResource`

Ressource logique représentant :

```text
repository
branch
worktree
```

Peut être utilisée comme cible d’un `Lease`.

---

# 23. Entités candidates mais non confirmées

```text
Policy
ToolInvocation
RuntimeEvent
RecoveryPlan
AgentIdentity
Tenant
Namespace
Task
SubRun
```

Elles ne doivent pas devenir des entités uniquement parce qu’elles peuvent être persistées.

---

# 24. Objets qui ne sont pas des entités

Exemples de Value Objects :

```text
RunState
ConversationStatus
MessageType
MessageContent
MessageReference
EffectStatus
ApprovalStatus
ApprovalDecision
LeaseStatus
FencingToken
IdempotencyKey
InputFingerprint
ExternalReference
ResourceIdentity
EffectRiskLevel
CorrelationContext
OwnershipContext
PolicyDecision
NextAction
```

---

# 25. Entités vs services

```text
Effect
= entité

EffectReconciler
= service métier
```

```text
Lease
= entité

LeaseCoordinator
= service métier
```

```text
Run
= entité

RecoveryPlanner
= service métier
```

---

# 26. Agrégats proposés

## 26.1 Run Aggregate

Root :

```text
Run
```

Références :

```text
Checkpoint
RuntimeBinding
```

`Effect`, `Approval` et `Lease` devraient probablement rester des agrégats indépendants.

## 26.2 Conversation Aggregate

Root :

```text
Conversation
```

Références :

```text
Participant
Message
```

Les messages peuvent être persistés en append sans recharger toute la conversation.

## 26.3 Effect Aggregate

Root :

```text
Effect
```

Value Objects :

```text
IdempotencyKey
InputFingerprint
ExternalReference
EffectStatus
```

## 26.4 Approval Aggregate

Root :

```text
Approval
```

## 26.5 Lease Aggregate

Root :

```text
Lease
```

Value Objects :

```text
ResourceIdentity
FencingToken
```

## 26.6 Session Aggregate

Root :

```text
Session
```

`Run` et `Conversation` sont référencés par identité.

---

# 27. Matrice entités ↔ ports

| Entité | Port potentiel |
|---|---|
| Run | RunStore |
| Session | SessionStore |
| Conversation | ConversationStore |
| Message | MessageStore |
| Participant | ConversationStore |
| MemoryEntry | MemoryStore |
| Checkpoint | CheckpointStore / RunStore |
| Effect | EffectStore |
| ReconciliationCase | EffectStore / ReconciliationStore |
| Approval | ApprovalStore |
| Artifact | ArtifactStore |
| Lease | LeaseStore |
| Worker | WorkerRegistry |
| RuntimeBinding | RuntimeStore |
| RuntimeInvocation | RuntimeStore / AuditStore |
| AuditEvent | AuditStore |

---

# 28. Matrice entités ↔ événements métier

| Entité | Événements principaux |
|---|---|
| Run | created, started, waiting, resumed, succeeded, failed, cancelled |
| Session | created, closed, archived |
| Conversation | opened, paused, closed, archived |
| Message | appended, referenced |
| Effect | intended, started, succeeded, failed, unknown |
| ReconciliationCase | opened, resolved, manual_review |
| Approval | requested, approved, rejected, expired |
| Lease | acquired, renewed, lost, expired, taken_over |
| Worker | started, ready, draining, stopped |
| Artifact | created, attached, deleted |
| RuntimeInvocation | started, completed, failed |
| AuditEvent | appended |

---

# 29. Cardinalités principales

```text
Session        1 ───── 0..N Run
Session        1 ───── 0..N Conversation
Session        1 ───── 0..N MemoryEntry

Conversation   1 ───── 1..N Participant
Conversation   1 ───── 0..N Message

Run            1 ───── 0..N Checkpoint
Run            1 ───── 0..N Effect
Run            1 ───── 0..N Approval
Run            1 ───── 0..N Artifact
Run            1 ───── 0..N RuntimeInvocation
Run            1 ───── 0..N AuditEvent
Run            1 ───── 0..1 active Lease

Effect         1 ───── 0..N ReconciliationCase
Worker         1 ───── 0..N Lease
RuntimeBinding 1 ───── 0..N Run
```

---

# 30. Règles d’identité

## ID-01

Les identifiants internes doivent être opaques.

## ID-02

Un identifiant ne doit pas encoder un état métier susceptible de changer.

## ID-03

Une référence externe ne remplace pas l’identité PyAgentsKit.

## ID-04

Les IDs doivent être sérialisables et transportables entre processus.

---

# 31. Règles de mutation

## MUT-01

Les mutations doivent passer par des opérations métier.

## MUT-02

Les transitions doivent vérifier les invariants.

## MUT-03

Une modification persistée importante doit pouvoir produire un `DomainEvent` ou `AuditEvent`.

## MUT-04

Les entités critiques doivent supporter une stratégie de concurrence explicite.

---

# 32. Entités et concurrence

Les entités les plus sensibles aux accès concurrents sont :

```text
Run
Effect
Approval
Lease
MemoryEntry
Conversation
```

Les stores devront expliciter :

```text
expected_version
atomic transition
locking strategy
transaction boundary
```

---

# 33. Entités et persistence

La persistence ne doit pas dicter le domaine.

Exemple logique :

```python
run.succeed(...)
```

puis :

```text
RunStore.save(run)
```

et non des `UPDATE` dispersés dans le code métier.

---

# 34. Entités et audit

Audit obligatoire :

```text
Run
Effect
Approval
Lease
Message sensible
PolicyDecision
```

Audit conditionnel :

```text
Session
Conversation
Artifact
RuntimeInvocation
MemoryEntry
```

---

# 35. Entités et suppression

Une suppression fonctionnelle peut conserver une trace d’audit.

Exemple :

```text
Artifact binary deleted
```

mais :

```text
ArtifactDeleted audit event retained
```

---

# 36. Entités et multi-tenancy

Les entités doivent permettre l’ajout futur d’un contexte :

```text
tenant_id
namespace_id
organization_id
```

sans casser leurs identités.

---

# 37. Frontière avec les systèmes externes

PyAgentsKit ne recopie pas la modélisation complète des systèmes externes.

Exemple :

```text
ERP Invoice
```

est représentée côté PyAgentsKit par :

```text
Effect
+
ExternalReference(invoice_id)
```

---

# 38. Frontière avec les runtimes agentiques

Les objets internes à :

```text
LangGraph
Claude Agent SDK
OpenAI Agents SDK
Codex
Claude Code
OpenCode
```

ne deviennent pas automatiquement des entités PyAgentsKit.

Seuls les concepts nécessaires aux garanties du framework entrent dans le domaine.

---

# 39. Questions ouvertes

## Q-ENT-01
`Actor` doit-il être persisté ou rester une référence IAM ?

## Q-ENT-02
`Participant` mérite-t-il sa propre identité ou peut-il être un Value Object ?

## Q-ENT-03
`RuntimeInvocation` doit-elle être une entité métier ou uniquement un événement opérationnel ?

## Q-ENT-04
`ReconciliationCase` doit-il être agrégat indépendant ?

## Q-ENT-05
`Checkpoint` doit-il avoir son propre store ?

## Q-ENT-06
`Worker` doit-il être durablement persisté ou enregistré de manière éphémère ?

## Q-ENT-07
`Policy` doit-elle devenir une entité de premier niveau ?

## Q-ENT-08
Faut-il introduire une entité générique `Task` entre `Run` et runtime ?

## Q-ENT-09
Faut-il introduire `SubRun` pour les délégations agent→agent ?

---

# 40. Critères d’introduction d’une nouvelle entité

Un nouvel objet ne doit devenir une entité que si plusieurs critères sont remplis :

1. il possède une identité propre ;
2. cette identité survit à ses changements d’état ;
3. il possède un cycle de vie identifiable ;
4. il est référencé par plusieurs objets ;
5. il possède des invariants ;
6. il doit être retrouvé indépendamment ;
7. il ne peut pas être correctement modélisé comme Value Object ;
8. il n’appartient pas seulement à une technologie externe.

---

# 41. Entités prioritaires pour l’implémentation

## P0 — cœur de fiabilité

```text
Run
Checkpoint
Effect
Approval
Lease
Worker
AuditEvent
```

## P1 — contexte durable

```text
Session
Conversation
Message
MemoryEntry
Artifact
RuntimeBinding
RuntimeInvocation
ReconciliationCase
```

## P2 — extensions

```text
Participant
Actor
CodingWorkspace
CodeChange
RepositoryResource
```

---

# 42. Vue d’ensemble finale

```text
                          Session
                             │
           ┌─────────────────┼──────────────────┐
           ▼                 ▼                  ▼
     Conversation           Run             MemoryEntry
           │                 │
     ┌─────┴─────┐           ├── Checkpoint
     ▼           ▼           ├── Effect
Participant    Message       │     │
     │           │           │     └── ReconciliationCase
     └──── Actor ┘           ├── Approval
                             ├── Artifact
                             ├── RuntimeInvocation
                             └── Lease
                                   │
                                   ▼
                                 Worker

                             Run
                              │
                              ▼
                       RuntimeBinding

Toutes les entités critiques
         │
         ▼
      AuditEvent
```

---

# 43. Résumé

Les entités structurantes de PyAgentsKit sont celles dont l’identité doit survivre aux pannes, reprises, changements de workers et changements de runtime.

Le noyau peut être résumé ainsi :

```text
EXECUTION
Run / Checkpoint

CONTEXT
Session / Conversation / Message / MemoryEntry

EFFECT SAFETY
Effect / ReconciliationCase

HUMAN CONTROL
Approval

DISTRIBUTED OWNERSHIP
Lease / Worker

INTEGRATION
RuntimeBinding / RuntimeInvocation / Artifact

TRACEABILITY
AuditEvent
```

Le principe directeur reste :

> **Une entité PyAgentsKit doit exister parce qu’elle porte une identité, un cycle de vie ou un invariant nécessaire aux garanties du runtime — pas simplement parce qu’elle peut être stockée en base.**

Le document complémentaire naturel suivant pourra formaliser les **Value Objects** :

```text
08_PYAGENTSKIT_VALUE_OBJECTS.md
```
