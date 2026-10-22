# PyAgentsKit — Objets métier

**Document :** `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`  
**Version :** 1.1  
**Date :** 19 octobre 2026  
**Statut :** Modèle métier du domaine  
**Projet :** PyAgentsKit  
**Révision 1.1 :** ajout du domaine conversationnel avec `Conversation`, `Message`, `Actor/Participant`, `MessageContent`, `MessageType` et `MessageReference`, et clarification de la séparation entre message, runtime event, approval et audit event.  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/02_PYAGENTSKIT_PARTIES_PRENANTES_ET_CAS_D_USAGE.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`

---

# 1. Objet du document

Ce document définit les **objets métier** de PyAgentsKit.

Il décrit les concepts manipulés par le domaine indépendamment :

- de PostgreSQL ;
- de S3 ;
- de Kubernetes ;
- d’un framework agentique particulier ;
- d’un fournisseur LLM ;
- d’une implémentation technique précise.

L’objectif est de construire un **langage métier commun** pour :

- le code ;
- la documentation ;
- les APIs ;
- les tests ;
- les ADR ;
- les stores ;
- les adapters ;
- les événements d’audit.

---

# 2. Principe de modélisation

PyAgentsKit manipule des objets qui représentent :

```text
exécution
état
effets
gouvernance
coordination
runtime
audit
```

Le modèle métier doit rester stable même si les implémentations changent.

Exemple :

```text
Run
```

reste un `Run` que sa persistence soit assurée par :

```text
SQLite
PostgreSQL
Temporal
DBOS
autre backend
```

---

# 3. Vue d’ensemble des objets métier

Les objets sont regroupés en neuf domaines.

```text
A. Exécution
B. Contexte et état
C. Conversations et interactions
D. Effets externes
E. Gouvernance humaine
F. Coordination distribuée
G. Runtime agentique
H. Audit et événements
I. Politiques et sécurité
```

Vue synthétique :

```text
Session
   │
   ├── Conversation
   │      │
   │      └── Message
   │             ├── sender: Actor
   │             └── recipients: Actor[]
   │
   ├── Run
   │    │
   │    ├── Checkpoint
   │    ├── Approval
   │    ├── Effect
   │    │    └── ReconciliationCase
   │    ├── Artifact
   │    ├── RuntimeInvocation
   │    └── AuditEvent
   │
   └── Memory

Run
 │
 └── Lease
      ├── Worker
      └── FencingToken
```

---

# 4. A — Exécution

# 4.1 Run

## Définition

Un **Run** représente une exécution durable d’un agent ou d’un runtime agentique.

C’est l’objet central de PyAgentsKit.

## Responsabilités

Le `Run` porte :

- son identité ;
- son état courant ;
- sa session éventuelle ;
- son runtime ;
- son historique ;
- ses checkpoints ;
- ses approvals ;
- ses effects ;
- son ownership courant ;
- son résultat final.

## Attributs métier conceptuels

```text
run_id
session_id
runtime_id
status
created_at
started_at
updated_at
completed_at
metadata
result_reference
error_reference
```

## États possibles

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

## Invariants

```text
RUN-INV-01
Un run possède un identifiant stable.

RUN-INV-02
Un run terminal ne redevient pas actif implicitement.

RUN-INV-03
Une transition d’état doit être valide.

RUN-INV-04
Un run ne peut pas être SUCCEEDED et FAILED simultanément.

RUN-INV-05
Toute reprise doit partir d’un état connu.
```

---

# 4.2 RunState

## Définition

`RunState` représente l’état métier courant d’un run.

Il peut être modélisé comme value object ou enum.

## Valeurs

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

## Rôle

Éviter les booléens ambigus comme :

```text
is_done
is_running
is_waiting
```

qui deviennent incohérents entre eux.

---

# 4.3 RunResult

## Définition

Résultat final logique d’un run.

Il peut contenir :

- une valeur sérialisable ;
- une référence vers un artifact ;
- une référence métier externe ;
- des metadata.

## Principe

Le résultat lourd ne doit pas nécessairement être stocké directement dans le `Run`.

---

# 4.4 Checkpoint

## Définition

Un **Checkpoint** représente un état durable à partir duquel un run peut être repris.

## Responsabilités

- figer un état cohérent ;
- permettre une reprise ;
- conserver la position logique du run ;
- référencer éventuellement des artifacts.

## Attributs conceptuels

```text
checkpoint_id
run_id
sequence
created_at
state_payload
runtime_state_reference
metadata
```

## Invariants

```text
CHK-INV-01
Les checkpoints d’un run sont ordonnés.

CHK-INV-02
Un checkpoint validé est immuable.

CHK-INV-03
La reprise utilise un checkpoint cohérent avec l’état du run.
```

---

# 5. B — Contexte et état

# 5.1 Session

## Définition

Une **Session** représente un contexte durable pouvant regrouper plusieurs runs.

## Exemples

```text
conversation
dossier métier
ticket support
processus utilisateur
mission agentique longue
```

## Responsabilités

- regrouper plusieurs runs ;
- porter un contexte partagé ;
- survivre aux workers ;
- servir de point d’ancrage à la mémoire.

## Attributs conceptuels

```text
session_id
status
created_at
updated_at
metadata
```

---

# 5.2 SessionState

## Définition

État partagé à l’échelle de la session.

Il est différent du `RunState`.

Exemple :

```text
Session
  ├── Run 1
  ├── Run 2
  └── Run 3
```

Chaque run possède son état propre, mais partage le contexte de session.

---

# 5.3 Memory

## Définition

La **Memory** représente des informations persistantes destinées à être réutilisées au-delà d’un run.

## Responsabilités

- stocker du contexte durable ;
- être indépendante du cycle de vie immédiat d’un run ;
- être consultable par plusieurs runs autorisés.

## Principe

```text
RunState
!=
SessionState
!=
Memory
```

---

# 5.4 MemoryEntry

## Définition

Une unité logique de mémoire.

## Attributs possibles

```text
memory_id
scope
key
value
created_at
updated_at
version
metadata
```

## Scopes possibles

```text
session
agent
tenant
workspace
custom
```

---

# 5.5 Artifact

## Définition

Un **Artifact** représente un résultat ou document associé à une exécution.

## Exemples

```text
PDF
CSV
image
archive ZIP
rapport
notebook
log export
diff
build package
```

## Attributs conceptuels

```text
artifact_id
run_id
type
uri
content_type
size
checksum
created_at
metadata
```

## Principe

Les metadata appartiennent au domaine.

Le contenu binaire peut être déporté vers :

```text
S3
Azure Blob
filesystem
autre BlobStore
```

---

# 6. C — Conversations et interactions

# 6.1 Conversation

## Définition

Une **Conversation** représente un fil durable d’échanges entre un ou plusieurs participants.

Elle peut contenir des échanges :

```text
Human → Agent
Agent → Human
Agent → Agent
System → Agent
Agent → plusieurs agents
```

## Responsabilités

- regrouper des messages appartenant au même fil logique ;
- relier les échanges à une `Session` ;
- permettre la reprise d’une interaction ;
- conserver les participants ;
- fournir un contexte conversationnel durable ;
- rester indépendante du transport physique des messages.

## Attributs conceptuels

```text
conversation_id
session_id
status
created_at
updated_at
metadata
```

## États possibles

```text
OPEN
PAUSED
CLOSED
ARCHIVED
```

## Invariants

```text
CONV-INV-01
Une conversation possède un identifiant stable.

CONV-INV-02
Une conversation appartient à une session ou à un contexte explicite.

CONV-INV-03
Une conversation fermée ne reçoit pas de nouveau message sans réouverture explicite.

CONV-INV-04
Le transport du message ne fait pas partie de l’identité métier de la conversation.
```

---

# 6.2 ConversationStatus

## Définition

Value object représentant l’état d’une conversation.

## Valeurs

```text
OPEN
PAUSED
CLOSED
ARCHIVED
```

---

# 6.3 Message

## Définition

Un **Message** représente une unité durable d’échange entre participants.

C’est l’objet métier central des interactions conversationnelles.

## Responsabilités

- identifier qui parle ;
- identifier les destinataires ;
- conserver le contenu ;
- relier le message à une conversation ;
- corréler le message avec un run lorsque nécessaire ;
- permettre la reconstruction d’une interaction multi-agent.

## Attributs conceptuels

```text
message_id
conversation_id
session_id
run_id?
sender
recipients
message_type
content
parent_message_id?
correlation_id
created_at
metadata
attachments
```

## Exemples

```text
Human → Agent
"Peux-tu vérifier cette facture ?"

Agent Finance → Agent SupplierCheck
"Vérifie si le fournisseur est actif."

Agent SupplierCheck → Agent Finance
"Le fournisseur est actif."
```

## Invariants

```text
MSG-INV-01
Un message possède un identifiant stable.

MSG-INV-02
Un message appartient à une conversation.

MSG-INV-03
Un message possède exactement un sender logique.

MSG-INV-04
Un message possède au moins un destinataire logique ou une portée explicite.

MSG-INV-05
Un message déjà persisté ne doit pas être modifié silencieusement.

MSG-INV-06
Un message ne constitue pas automatiquement une approval.
```

---

# 6.4 Actor

## Définition

Un **Actor** représente l’émetteur, le destinataire ou le déclencheur logique d’une action.

## Types possibles

```text
HUMAN
AGENT
SYSTEM
SERVICE
WORKER
SCHEDULER
ADMINISTRATOR
```

## Attributs conceptuels

```text
actor_id
actor_type
display_name
metadata
```

## Utilisation

`Actor` peut être utilisé par :

- `Message` ;
- `ApprovalDecision` ;
- `AuditEvent` ;
- `PolicyDecision` ;
- événements métier.

---

# 6.5 Participant

## Définition

Un **Participant** représente la participation d’un `Actor` à une `Conversation`.

## Attributs conceptuels

```text
participant_id
conversation_id
actor_id
role
joined_at
left_at
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

## Principe

`Actor` représente l’identité logique.

`Participant` représente cette identité dans une conversation donnée.

---

# 6.6 MessageType

## Définition

Value object décrivant la nature fonctionnelle du message.

## Valeurs indicatives

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

## Principe

Le type d’un message ne doit pas être confondu avec son transport.

---

# 6.7 MessageContent

## Définition

Value object représentant le contenu logique d’un message.

## Formes possibles

```text
text
structured payload
references
attachments
mixed content
```

## Principe

Le domaine doit pouvoir manipuler un contenu sans dépendre d’un format fournisseur spécifique.

---

# 6.8 MessageReference

## Définition

Référence vers un autre objet cité ou lié dans un message.

## Exemples

```text
Artifact
Effect
Approval
Run
external document
previous Message
```

---

# 6.9 ConversationContext

## Définition

Value object regroupant le contexte conversationnel utile à un runtime.

## Contenu potentiel

```text
conversation_id
session_id
participants
recent_message_ids
metadata
```

## Principe

PyAgentsKit peut fournir le contexte durable sans imposer comment le runtime construit son prompt.

---

# 6.10 Séparation Message / RuntimeEvent / AuditEvent

Ces objets répondent à trois besoins différents.

```text
Message
= ce que les participants se disent

RuntimeEvent
= ce que le runtime est en train de faire

AuditEvent
= ce que PyAgentsKit conserve comme fait traçable
```

Ils peuvent être corrélés mais ne doivent pas être fusionnés.

---

# 6.11 Séparation Message / Approval

Un message humain comme :

```text
"ça me semble bon"
```

ne doit pas être assimilé automatiquement à :

```text
ApprovalDecision(APPROVED)
```

Une approval exige un acte métier explicite et traçable.

---

# 6.12 Séparation Message / ToolInvocation / Effect

Un message conversationnel est distinct d’un appel d’outil.

La chaîne peut être :

```text
Message
   ↓
RuntimeEvent
   ↓
ToolInvocation
   ↓
Effect
```

Tous les tool calls ne deviennent pas nécessairement des `Effect`.

---

# 6.13 ConversationStore

## Définition

Port de persistence destiné aux conversations.

Responsabilités possibles :

```text
create conversation
get conversation
update status
list conversations by session
```

---

# 6.14 MessageStore

## Définition

Port de persistence destiné aux messages.

Responsabilités possibles :

```text
append message
get message
list messages
list messages by conversation
find by correlation
```

## Principe

L’écriture doit tendre vers un modèle append-oriented.

---

# 6.15 Transport de messages

PyAgentsKit ne doit pas devenir un message broker généraliste.

Le transport réel peut être fourni par :

```text
in-process
HTTP
WebSocket
Redis
Kafka
NATS
runtime-native messaging
other transport
```

Le domaine PyAgentsKit doit seulement garantir :

```text
identity
conversation membership
correlation
persistence
audit
recovery semantics
```

---

# 7. D — Effets externes

# 6.1 Effect

## Définition

Un **Effect** représente une action produisant une conséquence observable en dehors du calcul interne du run.

C’est l’un des objets métier les plus importants de PyAgentsKit.

## Exemples

```text
send_email
create_invoice
transfer_money
update_erp
git_push
create_pull_request
merge_pull_request
publish_package
deploy
terraform_apply
```

## Responsabilités

- identifier l’effet ;
- suivre son cycle de vie ;
- empêcher le replay implicite ;
- supporter idempotence ;
- supporter reconciliation ;
- porter le fencing token si nécessaire ;
- conserver une référence externe.

## Attributs conceptuels

```text
effect_id
run_id
kind
status
idempotency_key
input_fingerprint
external_reference
fencing_token
created_at
started_at
completed_at
metadata
```

---

# 6.2 EffectStatus

## Valeurs minimales

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

## Principe fondamental

```text
UNKNOWN != FAILED
```

Un résultat inconnu doit rester inconnu jusqu’à reconciliation.

---

# 6.3 EffectIntent

## Définition

L’**EffectIntent** représente l’intention persistée d’exécuter un effet avant que l’appel externe ne soit effectué.

## Utilité

Permet de savoir :

```text
"nous avions prévu d’exécuter cet effet"
```

même si le worker tombe juste après.

## Exemples

```text
publier package X version Y
créer facture F123
push commit abc123
```

---

# 6.4 EffectOutcome

## Définition

Résultat confirmé ou observé d’un effet.

## Valeurs possibles

```text
success
failure
unknown
reconciled_success
reconciled_failure
manual_resolution
```

---

# 6.5 ExternalReference

## Définition

Référence stable fournie par le système externe.

## Exemples

```text
invoice_id
payment_id
commit_sha
pull_request_number
deployment_id
package_version
message_id
```

## Utilité

Permet :

- reconciliation ;
- audit ;
- déduplication ;
- diagnostic.

---

# 6.6 IdempotencyKey

## Définition

Value object représentant l’identité logique d’un effet idempotent.

## Principe

Même effet logique :

```text
same idempotency key
```

Effet différent :

```text
different idempotency key
```

---

# 6.7 InputFingerprint

## Définition

Empreinte des inputs d’un effet.

## Utilité

Détecter une anomalie telle que :

```text
same idempotency key
+
different input
```

---

# 6.8 ReconciliationCase

## Définition

Un **ReconciliationCase** représente la nécessité de déterminer l’état réel d’un effet ambigu.

## Création

Typiquement lorsqu’un effet est :

```text
STARTED
```

mais que le résultat local n’est pas connu.

## Attributs conceptuels

```text
reconciliation_id
effect_id
status
strategy
attempt_count
created_at
resolved_at
resolution
metadata
```

## États possibles

```text
PENDING
RUNNING
RESOLVED_SUCCESS
RESOLVED_FAILURE
MANUAL_REVIEW
FAILED
```

---

# 6.9 EffectReconciler

## Définition

Service métier chargé de résoudre un `ReconciliationCase`.

## Principe

PyAgentsKit définit le contrat.

La logique spécifique appartient à l’intégration.

Exemples :

```text
PaymentReconciler
GitPushReconciler
DeploymentReconciler
InvoiceReconciler
```

---

# 8. E — Gouvernance humaine

# 7.1 Approval

## Définition

Une **Approval** représente une décision humaine requise avant que le run puisse continuer.

## Responsabilités

- bloquer le run ;
- conserver la décision ;
- enregistrer l’identité du décideur ;
- permettre reprise ou arrêt.

## Attributs conceptuels

```text
approval_id
run_id
action
status
requested_by
requested_at
expires_at
decided_by
decided_at
reason
metadata
```

---

# 7.2 ApprovalStatus

## Valeurs

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

---

# 7.3 ApprovalDecision

## Définition

Value object représentant la décision prise.

## Contenu

```text
decision
actor
reason
timestamp
```

---

# 7.4 ApprovalPolicy

## Définition

Règle qui détermine si une action exige une approval.

## Exemple

```text
read_file
→ no approval

git_push
→ optional

merge_pull_request
→ approval required

deploy_production
→ mandatory approval
```

---

# 9. F — Coordination distribuée

# 8.1 Worker

## Définition

Un **Worker** représente une instance d’exécution capable de prendre en charge des runs.

## Attributs conceptuels

```text
worker_id
status
started_at
last_seen_at
capabilities
metadata
```

## Rôle

Le worker exécute.

Il ne possède pas automatiquement un run.

L’ownership est matérialisé par un `Lease`.

---

# 8.2 WorkerStatus

## Valeurs possibles

```text
STARTING
READY
BUSY
DRAINING
UNHEALTHY
STOPPED
```

---

# 8.3 Lease

## Définition

Un **Lease** représente un droit temporaire d’exécution sur une ressource.

## Ressources possibles

```text
Run
repository
branch
workspace
external job
custom resource
```

## Attributs conceptuels

```text
lease_id
resource_type
resource_id
owner_worker_id
fencing_token
acquired_at
expires_at
renewed_at
status
```

## Responsabilités

- ownership ;
- exclusivité ;
- expiration ;
- takeover ;
- fencing.

---

# 8.4 LeaseStatus

## Valeurs

```text
ACQUIRED
ACTIVE
LOST
EXPIRED
RELEASED
TAKEN_OVER
```

---

# 8.5 FencingToken

## Définition

Value object monotone attaché à une nouvelle ownership.

## Exemple

```text
Worker A
token 41

Worker B takes over
token 42

Worker A returns
token 41 → stale
```

## Invariant

```text
new ownership
→ fencing token > previous fencing token
```

---

# 8.6 ProtectedResource

## Définition

Une ressource dont les mutations doivent vérifier l’ownership.

## Exemples

```text
Run
PostgreSQL row
repository branch
deployment environment
external job
```

---

# 8.7 ResourceIdentity

## Définition

Value object permettant de nommer une ressource coordonnée.

## Exemple

```text
type = "repository_branch"
id   = "org/repo:feature/auth"
```

---

# 10. G — Runtime agentique

# 9.1 AgentRuntime

## Définition

Un **AgentRuntime** représente le moteur externe qui exécute la logique agentique.

## Exemples

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
Antigravity CLI
runtime propriétaire
```

## Principe

PyAgentsKit ne doit pas dépendre de son implémentation interne.

---

# 9.2 AgentRuntimeAdapter

## Définition

Un **AgentRuntimeAdapter** traduit les concepts d’un runtime externe vers les contrats PyAgentsKit.

## Responsabilités

- start ;
- resume ;
- cancel ;
- status ;
- event translation ;
- context propagation ;
- éventuellement tool/effect interception.

## Principe

```text
runtime-specific logic
stays in adapter
```

---

# 9.3 RuntimeBinding

## Définition

Association entre un run et une instance/configuration de runtime.

## Attributs conceptuels

```text
runtime_binding_id
runtime_type
runtime_version
configuration_reference
capabilities
metadata
```

---

# 9.4 RuntimeInvocation

## Définition

Une invocation donnée du runtime dans le contexte d’un run.

## Exemples

```text
start
resume
continue
cancel
```

## Attributs possibles

```text
invocation_id
run_id
runtime_binding_id
type
status
started_at
completed_at
metadata
```

---

# 9.5 RuntimeEvent

## Définition

Événement produit par un runtime externe puis normalisé pour PyAgentsKit.

## Exemples

```text
message
tool_requested
tool_completed
runtime_waiting
runtime_completed
runtime_failed
```

## Principe

Un `RuntimeEvent` n’est pas nécessairement un `AuditEvent`.

---

# 9.6 RuntimeCapability

## Définition

Capacité déclarée par un adapter.

Exemples :

```text
supports_resume
supports_cancel
supports_streaming
supports_tool_interception
supports_native_checkpoint
supports_events
supports_subagents
```

---

# 11. H — Audit et événements

# 10.1 DomainEvent

## Définition

Événement représentant un fait métier qui s’est produit.

## Exemples

```text
RunCreated
RunStarted
RunPaused
RunResumed
EffectStarted
EffectSucceeded
ApprovalRequested
LeaseLost
```

## Principe

Un `DomainEvent` décrit un fait.

Il ne décrit pas une intention future.

---

# 10.2 AuditEvent

## Définition

Événement durable destiné à reconstruire l’histoire d’une exécution.

## Attributs conceptuels

```text
audit_event_id
event_type
run_id
session_id
actor
timestamp
payload
correlation_id
trace_id
```

---

# 10.3 Actor

## Définition

Entité logique ayant réalisé ou déclenché une action.

## Types possibles

```text
human
worker
agent
system
service
scheduler
administrator
```

---

# 10.4 CorrelationContext

## Définition

Value object regroupant les identifiants de corrélation.

Exemple :

```text
run_id
session_id
effect_id
approval_id
worker_id
trace_id
```

---

# 12. I — Politiques et sécurité

# 11.1 Policy

## Définition

Une **Policy** représente une règle qui influence l’autorisation ou le comportement d’une action.

## Exemples

```text
approval required
effect forbidden
allowed runtime
max concurrency
production deployment restricted
```

---

# 11.2 PolicyDecision

## Définition

Résultat de l’évaluation d’une policy.

## Valeurs possibles

```text
ALLOW
DENY
REQUIRE_APPROVAL
DEFER
```

---

# 11.3 EffectRiskLevel

## Définition

Classification de criticité d’un effet.

## Valeurs indicatives

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 11.4 Principal

## Définition

Sujet identifié auquel des permissions peuvent être associées.

Exemples :

```text
human user
worker
service
agent
runtime
```

---

# 13. Objets spécifiques aux coding agents

Les coding agents ne doivent pas polluer le core.

Ils peuvent toutefois introduire des objets spécialisés dans un module adapter.

---

# 12.1 CodingWorkspace

## Définition

Environnement isolé dans lequel un coding agent travaille.

## Exemples

```text
directory
container
sandbox
worktree
remote workspace
```

---

# 12.2 RepositoryResource

## Définition

Ressource logique représentant un repository ou sous-ensemble de repository.

Exemples :

```text
repository
branch
worktree
```

Peut être mappée vers `ProtectedResource`.

---

# 12.3 CodeChange

## Définition

Objet représentant un ensemble de modifications proposées par le coding agent.

Peut référencer :

```text
diff
patch
commit
artifact
```

Le core PyAgentsKit n’a pas à comprendre le contenu du diff.

---

# 12.4 CodingEffect

## Définition

Spécialisation logique d’un `Effect`.

Exemples :

```text
git_push
create_pull_request
merge_pull_request
publish_package
deploy
terraform_apply
```

---

# 14. Objets qui ne doivent pas appartenir au core

Les objets suivants ne doivent pas être intégrés au domaine central :

```text
PromptTemplate
LLMModel
Embedding
VectorIndex
GitCommitParser
PatchGenerator
RepositoryIndexer
IDEWorkspace
ChatMessageUI
KubernetesPod
S3Bucket
PostgresConnection
```

Ils appartiennent :

- aux runtimes ;
- aux adapters ;
- à l’infrastructure ;
- aux applications consommatrices.

---

# 15. Relations métier principales

```text
Session
  1
  ├── 0..N Conversation
  ├── 0..N Run
  └── 0..N MemoryEntry

Conversation
  1
  ├── 1..N Participant
  └── 0..N Message

Message
  N
  ├── 1 sender Actor
  ├── 1..N recipient Actor
  ├── 0..1 parent Message
  └── 0..N MessageReference

Run
  1
  ├── 0..N Checkpoint
  ├── 0..N Effect
  ├── 0..N Approval
  ├── 0..N Artifact
  ├── 0..N AuditEvent
  └── 0..1 active Lease

Lease
  N
  └── 1 Worker

Effect
  1
  ├── 0..1 ExternalReference
  └── 0..N ReconciliationCase

Run
  N
  └── 1 RuntimeBinding

RuntimeBinding
  N
  └── 1 AgentRuntimeAdapter
```

---

# 16. Agrégats candidats

Cette section propose une première lecture DDD.

Elle devra être confirmée dans le modèle conceptuel détaillé.

---

## 16.1 Conversation Aggregate

Root potentiel :

```text
Conversation
```

Contient ou référence :

```text
Participant
Message
MessageReference
```

`Actor` peut rester une entité partagée hors agrégat.

La persistence des messages peut être append-oriented afin d’éviter de charger toute la conversation pour chaque écriture.

---

## 16.2 Run Aggregate

Root potentiel :

```text
Run
```

Contient ou référence :

```text
RunState
Checkpoint
RuntimeBinding
```

Les `Effect`, `Approval` et `Lease` peuvent être agrégats indépendants afin de limiter les transactions trop larges.

---

## 16.3 Effect Aggregate

Root :

```text
Effect
```

Sous-objets :

```text
EffectIntent
EffectOutcome
ExternalReference
IdempotencyKey
InputFingerprint
```

---

## 16.4 Approval Aggregate

Root :

```text
Approval
```

Sous-objets :

```text
ApprovalDecision
```

---

## 16.5 Lease Aggregate

Root :

```text
Lease
```

Sous-objets :

```text
FencingToken
ResourceIdentity
```

---

## 16.6 Session Aggregate

Root :

```text
Session
```

Référence :

```text
Memory
Runs
```

---

# 17. Entités vs Value Objects

Première classification indicative.

## Entités

Possèdent une identité stable :

```text
Run
Session
Conversation
Message
Actor
Participant
Checkpoint
Effect
Approval
Worker
Lease
Artifact
RuntimeBinding
RuntimeInvocation
ReconciliationCase
AuditEvent
MemoryEntry
```

---

## Value Objects

Définis principalement par leur valeur :

```text
RunState
ConversationStatus
MessageType
MessageContent
MessageReference
EffectStatus
ApprovalStatus
LeaseStatus
FencingToken
IdempotencyKey
InputFingerprint
ExternalReference
ResourceIdentity
EffectRiskLevel
CorrelationContext
ConversationContext
PolicyDecision
```

---

# 18. Services métier candidats

Certains comportements ne correspondent pas naturellement à une seule entité.

Services candidats :

```text
RunTransitionService
ConversationService
MessageService
RecoveryPlanner
EffectExecutionService
EffectReconciler
ApprovalService
LeaseCoordinator
FencingValidator
PolicyEvaluator
RuntimeAdapterRegistry
AuditPublisher
```

---

# 19. RecoveryPlan

## Définition

Objet métier représentant la décision de reprise d’un run.

## Exemple

```text
RecoveryPlan
├── checkpoint_to_restore
├── pending_approval
├── unresolved_effects
├── lease_required
├── next_action
└── blockers
```

## Intérêt

La reprise devient une décision explicite plutôt qu’une suite de conditions dispersées.

---

# 20. NextAction

## Définition

Value object indiquant l’action métier suivante à exécuter après évaluation de l’état.

Valeurs possibles :

```text
RESUME_RUNTIME
WAIT_FOR_APPROVAL
RECONCILE_EFFECT
ACQUIRE_LEASE
COMPLETE_RUN
FAIL_RUN
MANUAL_INTERVENTION
```

---

# 21. OwnershipContext

## Définition

Contexte prouvant l’ownership courant lors d’une action protégée.

## Contenu possible

```text
worker_id
lease_id
resource_id
fencing_token
expires_at
```

## Utilité

Éviter de passer séparément plusieurs paramètres de coordination.

---

# 22. ProtectedEffectContext

## Définition

Contexte transmis lors de l’exécution d’un effet protégé.

## Contenu

```text
run_id
effect_id
idempotency_key
ownership_context
correlation_context
approval_reference
```

---

# 23. Business invariants globaux

## OBJ-INV-01

Chaque `Run` possède une identité stable.

## OBJ-INV-02

Chaque `Effect` appartient à un run.

## OBJ-INV-03

Un `Effect` réussi ne doit pas être rejoué implicitement.

## OBJ-INV-04

Un `Effect UNKNOWN` doit être réconcilié ou résolu manuellement.

## OBJ-INV-05

Un `Lease` identifie exactement une ressource logique protégée.

## OBJ-INV-06

Un `FencingToken` obsolète ne doit pas être accepté.

## OBJ-INV-07

Une `Approval` obligatoire bloque le run tant qu’elle n’est pas résolue.

## OBJ-INV-08

Un `Checkpoint` validé ne doit pas être modifié silencieusement.

## OBJ-INV-09

Un `RuntimeAdapter` ne devient pas propriétaire de l’état métier PyAgentsKit.

## OBJ-INV-10

Les événements d’audit déjà persistés ne doivent pas être réécrits silencieusement.

## OBJ-INV-11

Un `Message` appartient à une `Conversation`.

## OBJ-INV-12

Un `Message` humain ne devient pas automatiquement une `ApprovalDecision`.

## OBJ-INV-13

Un `Message`, un `RuntimeEvent` et un `AuditEvent` restent des objets distincts.

## OBJ-INV-14

La persistence d’un message ne dépend pas du mécanisme de transport utilisé.

## OBJ-INV-15

La reprise d’une conversation ne doit pas entraîner le replay implicite d’un message déjà durablement persisté.

---

# 24. Frontières du domaine

```text
┌─────────────────────────────────────────────┐
│              PyAgentsKit Domain             │
│                                             │
│ Run                                         │
│ Session                                     │
│ Conversation                                │
│ Message                                     │
│ Actor / Participant                         │
│ Memory                                      │
│ Checkpoint                                  │
│ Effect                                      │
│ Approval                                    │
│ Lease                                       │
│ FencingToken                                │
│ Artifact                                    │
│ AuditEvent                                  │
│ Policy                                      │
│ RecoveryPlan                                │
└──────────────────────┬──────────────────────┘
                       │ ports
                       ▼
┌─────────────────────────────────────────────┐
│               External World                │
│                                             │
│ Agent runtimes                              │
│ PostgreSQL                                  │
│ S3 / Blob                                   │
│ Git / GitHub                                │
│ ERP / CRM                                   │
│ CI/CD                                       │
│ Cloud                                       │
│ Email / Slack                               │
└─────────────────────────────────────────────┘
```

---

# 25. Objets métier prioritaires pour le core

## Priorité P0

```text
Run
RunState
Conversation
ConversationStatus
Message
MessageType
Actor
Checkpoint
Effect
EffectStatus
EffectIntent
EffectOutcome
Approval
ApprovalStatus
Lease
FencingToken
Worker
AuditEvent
```

---

## Priorité P1

```text
Session
Participant
MessageContent
MessageReference
ConversationContext
Memory
Artifact
RuntimeBinding
RuntimeInvocation
RuntimeEvent
ReconciliationCase
RecoveryPlan
OwnershipContext
```

---

## Priorité P2

```text
Policy
PolicyDecision
EffectRiskLevel
ProtectedResource
ResourceIdentity
CodingWorkspace
CodeChange
```

---

# 26. Mapping objets ↔ stores

| Objet métier | Port de persistence potentiel |
|---|---|
| Run | RunStore |
| Session | SessionStore |
| Conversation | ConversationStore |
| Message | MessageStore |
| MemoryEntry | MemoryStore |
| Checkpoint | RunStore / CheckpointStore |
| Effect | EffectStore |
| Approval | ApprovalStore |
| Lease | LeaseStore |
| Artifact | ArtifactStore |
| AuditEvent | AuditStore |
| Worker | WorkerRegistry / RuntimeStore |
| ReconciliationCase | EffectStore / ReconciliationStore |

La séparation exacte sera définie plus tard.

---

# 27. Mapping objets ↔ événements

| Objet | Événements principaux |
|---|---|
| Run | created, started, waiting, resumed, completed, failed |
| Conversation | opened, paused, closed, archived |
| Message | created, persisted, referenced |
| Effect | intended, started, succeeded, failed, unknown |
| Approval | requested, approved, rejected, expired |
| Lease | acquired, renewed, lost, expired, taken_over |
| Worker | started, ready, draining, stopped |
| ReconciliationCase | opened, resolved, manual_review |
| Artifact | created, attached, deleted |

---

# 28. Mapping objets ↔ APIs publiques futures

Exemples conceptuels :

```python
conversation = await conversations.create(...)
message = await messages.append(conversation.id, ...)

run = await runs.create(...)

await runs.start(run.id)

approval = await approvals.request(...)

effect = await effects.prepare(...)

outcome = await effects.execute(effect.id, ...)

lease = await leases.acquire(...)

plan = await recovery.plan(run.id)
```

Ces APIs sont illustratives.

Elles ne constituent pas encore la spécification publique définitive.

---

# 29. Questions ouvertes

## Q-OBJ-00A

`Conversation` doit-elle obligatoirement appartenir à une `Session`, ou certains scénarios doivent-ils autoriser une conversation autonome ?

## Q-OBJ-00B

`Actor` doit-il être une entité persistée globalement ou une référence fournie par un système IAM externe ?

## Q-OBJ-00C

Les messages doivent-ils être strictement append-only ?

## Q-OBJ-00D

Faut-il un `ConversationStore` et un `MessageStore` séparés ou un port conversationnel unique ?

## Q-OBJ-00E

Un message agent→agent doit-il toujours être persisté, ou la persistence peut-elle être configurable selon criticité ?

## Q-OBJ-01

`Checkpoint` doit-il avoir son propre `CheckpointStore` ou rester dans `RunStore` ?

## Q-OBJ-02

`Worker` doit-il être une entité persistée durablement ou un objet opérationnel éphémère ?

## Q-OBJ-03

`EffectIntent` doit-il être une entité distincte ou une phase du `Effect` ?

## Q-OBJ-04

`ReconciliationCase` doit-il être un agrégat séparé ?

## Q-OBJ-05

Les `Policy` appartiennent-elles au core ou à un module optionnel ?

## Q-OBJ-06

`RuntimeInvocation` doit-il être durable ou uniquement observabilité/audit ?

## Q-OBJ-07

Faut-il un `ResourceLease` générique dont `RunLease` serait une spécialisation ?

## Q-OBJ-08

`Artifact` doit-il être attachable aussi à une `Session` ou seulement à un `Run` ?

---

# 30. Critères de validation d’un nouvel objet métier

Avant d’ajouter un objet au domaine, vérifier :

1. possède-t-il une responsabilité métier claire ?
2. a-t-il un cycle de vie propre ?
3. possède-t-il des invariants ?
4. doit-il être référencé dans plusieurs scénarios ?
5. existe-t-il indépendamment d’une technologie ?
6. ne duplique-t-il pas un objet existant ?
7. appartient-il réellement au core ?
8. peut-il rester dans un adapter ?

Si les réponses sont insuffisantes, l’objet ne doit pas être introduit.

---

# 31. Résumé du modèle métier

Le noyau conceptuel peut être représenté ainsi :

```text
                         Session
                            │
             ┌──────────────┼──────────────┐
             ▼              ▼              ▼
       Conversation         Run          Memory
             │              │
             ▼              ├── Checkpoint
          Message           ├── Approval
        ┌────┴────┐         ├── Effect
        ▼         ▼         │     │
      Actor     Actor       │     ▼
     sender   recipients    │  ReconciliationCase
                            │
                            └── Lease
                                  │
                         ┌────────┴────────┐
                         ▼                 ▼
                      Worker         FencingToken

                            │
                            ▼
                    AgentRuntimeAdapter
                            │
                            ▼
                      AgentRuntime
```

La logique centrale de PyAgentsKit repose désormais sur cinq familles d’objets :

```text
EXECUTION
Run / Checkpoint / Session

CONVERSATION
Conversation / Message / Actor / Participant

CONTROL
Approval / Policy

EFFECT SAFETY
Effect / Reconciliation / Idempotency

DISTRIBUTED OWNERSHIP
Lease / Worker / FencingToken
```

Le document suivant pourra transformer ce vocabulaire en modèle conceptuel complet avec cardinalités, agrégats, états et frontières :

```text
07_PYAGENTSKIT_MODELE_CONCEPTUEL_DU_DOMAINE.md
```
