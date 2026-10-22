# PyAgentsKit — Principes architecturaux

**Document :** `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`  
**Version :** 1.0  
**Date :** 19 octobre 2026  
**Statut :** Référentiel d’architecture  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/02_PYAGENTSKIT_PARTIES_PRENANTES_ET_CAS_D_USAGE.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`

---

# 1. Objet du document

Ce document définit les **principes architecturaux structurants** de PyAgentsKit.

Ces principes ont pour rôle de guider :

- les choix de conception ;
- les APIs publiques ;
- les boundaries du domaine ;
- les adapters ;
- les stores ;
- la coordination distribuée ;
- la gestion des effets ;
- l’évolution de la roadmap ;
- les revues de code ;
- les ADR ;
- les décisions de build vs integrate.

L’objectif n’est pas de décrire toute l’architecture technique.

L’objectif est de préciser les règles qui doivent rester vraies même lorsque l’implémentation évolue.

---

# 2. Vision architecturale

PyAgentsKit doit être conçu comme une **reliability layer indépendante du runtime agentique**.

La vision cible est :

```text
        Agent Runtime
              │
              ▼
     AgentRuntimeAdapter
              │
              ▼
       PyAgentsKit Core
              │
   ┌──────────┼───────────┐
   ▼          ▼           ▼
 State      Effects    Coordination
   │          │           │
   ▼          ▼           ▼
 Stores     Tools       Leases
             │          Fencing
             ▼
      External systems
```

Le framework ne doit pas devenir :

```text
un LLM framework
un coding agent
un workflow engine généraliste
un scheduler
un observability backend
un cloud platform
```

Sa responsabilité est :

> **garantir la fiabilité de l’exécution d’un agent qui agit réellement sur des systèmes.**

---

# 3. Les principes fondateurs

Les principes sont regroupés en 18 règles :

```text
AP-01  Framework-neutral by design
AP-02  Runtime through adapters
AP-03  Ports and adapters
AP-04  Domain before infrastructure
AP-05  Explicit state
AP-06  Effects are first-class citizens
AP-07  No implicit effect replay
AP-08  Reconciliation over blind retry
AP-09  Explicit ownership
AP-10  Fencing over trust
AP-11  Safe degradation
AP-12  Deterministic recovery
AP-13  Human control as a domain concept
AP-14  Observability by design
AP-15  Audit by design
AP-16  Build semantics, integrate infrastructure
AP-17  Progressive extensibility
AP-18  Complexity must earn its place
```

---

# 4. AP-01 — Framework-neutral by design

## Principe

PyAgentsKit ne doit dépendre conceptuellement d’aucun framework agentique particulier.

Il doit pouvoir fonctionner avec :

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
Antigravity CLI (agy)
runtime propriétaire
application Python custom
```

sans modifier son domaine central.

## Motivation

Les runtimes agentiques évoluent rapidement.

Un couplage fort créerait :

- vendor lock-in ;
- coût de migration ;
- obsolescence rapide ;
- fragmentation du core.

## Règle

Le core ne doit jamais contenir :

```text
if runtime == "langgraph"
if runtime == "claude_code"
if runtime == "codex"
```

hors logique d’adapter ou de plugin.

## Conséquence

Les spécificités runtime doivent être encapsulées dans :

```text
AgentRuntimeAdapter
```

ou une extension spécialisée.

---

# 5. AP-02 — Runtime through adapters

## Principe

Tout runtime externe doit être traité comme un système intégré via un adapter.

## Contrat conceptuel

```python
class AgentRuntimeAdapter(Protocol):
    async def start(...): ...
    async def resume(...): ...
    async def cancel(...): ...
    async def status(...): ...
    async def events(...): ...
```

Le contrat réel pourra évoluer, mais le principe reste :

```text
PyAgentsKit knows the contract
PyAgentsKit does not know the runtime internals
```

## Interdiction

Le core ne doit pas supposer :

- graph DSL ;
- conversation model ;
- prompt format ;
- tool registry spécifique ;
- repository semantics ;
- CLI spécifique.

---

# 6. AP-03 — Ports and adapters

## Principe

Les dépendances externes doivent être accessibles via des ports.

Exemples :

```text
RunStore
SessionStore
MemoryStore
ApprovalStore
EffectStore
LeaseStore
ArtifactStore
AgentRuntimeAdapter
TelemetrySink
```

Les implémentations concrètes deviennent des adapters.

Exemples :

```text
PostgresRunStore
PostgresSessionStore
S3ArtifactStore
AzureBlobArtifactStore
LangGraphAdapter
CodexAdapter
ClaudeAgentAdapter
```

## Motivation

Le domaine doit rester testable sans dépendance aux technologies concrètes.

## Architecture

```text
        Domain / Core
             │
      abstract contracts
             │
   ┌─────────┼─────────┐
   ▼         ▼         ▼
Postgres    S3      Runtime SDK
```

---

# 7. AP-04 — Domain before infrastructure

## Principe

Les concepts fonctionnels doivent être définis avant les backends.

Le domaine doit contenir des concepts comme :

```text
Run
Session
Effect
Approval
Lease
Checkpoint
Artifact
Worker
FencingToken
AuditEvent
```

et non directement :

```text
PostgreSQL row
Redis lock
S3 object
Kubernetes pod
```

## Motivation

Le stockage et l’orchestration sont des moyens, pas le modèle métier.

## Exemple

Mauvais :

```python
class PostgresAgentExecution:
    ...
```

Meilleur :

```python
class Run:
    ...
```

avec :

```python
class PostgresRunStore(RunStore):
    ...
```

---

# 8. AP-05 — Explicit state

## Principe

Tout état important doit être représenté explicitement.

## Exemples

### Run

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

### Effect

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

### Approval

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

### Lease

```text
ACQUIRED
ACTIVE
LOST
EXPIRED
RELEASED
TAKEN_OVER
```

## Règle

Éviter les états implicites dérivés de :

```text
absence de ligne
None
booléen ambigu
exception non typée
timestamp manquant
```

lorsqu’un état métier explicite existe.

---

# 9. AP-06 — Effects are first-class citizens

## Principe

Un effet externe doit être représenté comme une entité du domaine.

Un tool call n’est pas toujours un simple appel Python.

Exemples :

```text
create_invoice
send_email
transfer_money
git_push
merge_pull_request
publish_package
deploy
terraform_apply
```

doivent pouvoir devenir des `Effect`.

## Modèle conceptuel minimal

```text
Effect
├── effect_id
├── run_id
├── kind
├── status
├── idempotency_key
├── input_fingerprint
├── external_reference
├── fencing_token
├── created_at
├── started_at
├── completed_at
└── reconciliation_state
```

## Motivation

Une action réelle possède un cycle de vie différent d’un simple calcul interne.

---

# 10. AP-07 — No implicit effect replay

## Principe

> **Une reprise de run ne doit jamais rejouer implicitement un effet métier.**

## Règle

Avant toute reprise :

```text
check effect state
```

Si :

```text
SUCCEEDED
```

alors :

```text
reuse outcome
```

Si :

```text
UNKNOWN
```

alors :

```text
reconcile
```

Pas :

```text
retry blindly
```

## Motivation

Le replay peut produire :

- double paiement ;
- double facture ;
- double email ;
- double publication ;
- double déploiement.

---

# 11. AP-08 — Reconciliation over blind retry

## Principe

Lorsqu’un résultat externe est ambigu, la priorité est donnée à la réconciliation.

## Exemple

```text
POST /payment
↓
external service processes payment
↓
network timeout
↓
local result unknown
```

La réponse correcte n’est pas :

```text
retry()
```

mais :

```text
query external state
↓
determine actual result
↓
continue safely
```

## Architecture

```text
Effect
  │
  ├── SUCCEEDED
  ├── FAILED
  └── UNKNOWN
        │
        ▼
 EffectReconciler
        │
        ├── success
        ├── failure
        └── manual review
```

---

# 12. AP-09 — Explicit ownership

## Principe

Dans un système distribué, un worker doit prouver qu’il possède le droit d’exécuter un run.

## Modèle

```text
Run
 │
 ▼
Lease
 │
 ├── owner
 ├── expires_at
 └── fencing_token
```

## Règle

Pas d’effet protégé sans ownership valide.

## Motivation

Éviter :

- double exécution ;
- concurrence incohérente ;
- workers zombies ;
- split-brain.

---

# 13. AP-10 — Fencing over trust

## Principe

Un worker expiré ne doit pas seulement recevoir l’instruction de s’arrêter.

Il doit devenir **incapable** de produire certains effets protégés.

## Exemple

```text
Worker A
token 41

lease expires

Worker B
token 42

Worker A returns
tries token 41

protected system
→ REJECT
```

## Règle

Lorsque c’est techniquement possible, le fencing token doit être vérifié par :

- store ;
- service ;
- tool wrapper ;
- resource guard.

## Motivation

La confiance dans un worker obsolète n’est pas suffisante dans un système distribué.

---

# 14. AP-11 — Safe degradation

## Principe

Lorsque PyAgentsKit ne peut plus garantir la cohérence, il doit réduire ses capacités plutôt que continuer normalement.

## Exemple

PostgreSQL indisponible :

```text
cannot persist
cannot renew lease
cannot verify effect state
```

Réaction :

```text
stop new protected effects
stop admissions if required
mark worker not ready
preserve current context if possible
```

## Principe directeur

> **Fail safe, not open.**

---

# 15. AP-12 — Deterministic recovery

## Principe

La reprise doit suivre une procédure déterministe.

## Ordre logique recommandé

```text
1. load run state
2. load checkpoint
3. validate terminal state
4. validate lease / ownership
5. inspect pending approvals
6. inspect unfinished effects
7. reconcile ambiguous effects
8. determine next executable step
9. resume
```

## Interdiction

Ne pas simplement :

```text
restart agent from beginning
```

si des effets ou états ont déjà été persistés.

---

# 16. AP-13 — Human control as a domain concept

## Principe

Les approvals ne sont pas une feature UI.

Elles sont des objets du domaine.

## Modèle

```text
Approval
├── approval_id
├── run_id
├── requested_action
├── requested_by
├── status
├── decided_by
├── decided_at
└── reason
```

## Conséquence

Une approval doit :

- survivre à un restart ;
- être auditable ;
- pouvoir expirer ;
- bloquer un run ;
- permettre la reprise.

---

# 17. AP-14 — Observability by design

## Principe

Logs, métriques et traces sont définis avec le modèle d’exécution, pas ajoutés après.

## Chaque composant critique doit exposer :

```text
logs
metrics
events
trace context
```

## Corrélation

Les identifiants suivants doivent pouvoir circuler :

```text
run_id
session_id
effect_id
approval_id
worker_id
lease_id
trace_id
```

## Motivation

Un runtime distribué non observable est difficilement exploitable.

---

# 18. AP-15 — Audit by design

## Principe

Tout changement critique doit pouvoir être historisé.

## Événements minimum

```text
run.created
run.started
run.waiting
run.resumed
run.completed

approval.requested
approval.approved
approval.rejected

effect.started
effect.succeeded
effect.failed
effect.unknown

lease.acquired
lease.renewed
lease.lost
lease.taken_over
```

## Distinction

```text
log
!=
audit event
```

Un log aide au diagnostic.

Un audit event permet de reconstruire l’histoire métier.

---

# 19. AP-16 — Build semantics, integrate infrastructure

## Principe

PyAgentsKit doit construire les concepts qui font sa valeur et intégrer les briques d’infrastructure existantes.

## À construire

```text
Run semantics
Effect semantics
Approval semantics
Recovery semantics
Lease semantics
Fencing semantics
AgentRuntimeAdapter
Audit domain events
```

## À intégrer

```text
PostgreSQL
S3
Azure Blob
OpenTelemetry
Kubernetes
Temporal
DBOS
Codex
Claude Code
OpenCode
external agent runtimes
```

## Motivation

Éviter de reconstruire :

```text
database
scheduler
workflow engine
tracing backend
coding agent
cloud orchestrator
```

---

# 20. AP-17 — Progressive extensibility

## Principe

Le framework doit permettre d’ajouter progressivement :

```text
new store
new runtime adapter
new artifact backend
new reconciler
new effect policy
new telemetry exporter
```

sans modification du core dans le cas nominal.

## Mécanismes privilégiés

```text
Protocols
interfaces
dependency injection
plugins
adapters
extension points
```

## Interdiction

Éviter les registries globaux opaques ou les imports magiques lorsqu’ils rendent le comportement imprévisible.

---

# 21. AP-18 — Complexity must earn its place

## Principe

Toute nouvelle abstraction doit justifier son coût.

Question obligatoire :

> **Quel problème concret cette abstraction résout-elle que les concepts existants ne résolvent pas ?**

## Exemple

Avant d’ajouter :

```text
CodingAgentWorkspaceCoordinator
```

vérifier si :

```text
ResourceLease
```

suffit.

## Motivation

Éviter :

- architecture astronaut ;
- explosion des concepts ;
- duplication ;
- maintenance inutile.

---

# 22. Principes complémentaires

## AP-19 — Composition over inheritance

Favoriser :

```text
composants indépendants
+
contrats explicites
```

plutôt que de grandes hiérarchies de classes.

---

## AP-20 — Prefer immutable events

Les événements persistés doivent idéalement être append-only.

Une correction produit un nouvel événement plutôt qu’une modification silencieuse.

---

## AP-21 — State transitions are domain operations

Une transition comme :

```text
RUNNING → SUCCEEDED
```

ne doit pas être un simple :

```python
run.status = "SUCCEEDED"
```

sans validation.

Elle doit passer par une opération contrôlée.

---

## AP-22 — Explicit errors

Les erreurs importantes doivent être typées.

Exemples :

```text
LeaseLostError
InvalidStateTransition
EffectAlreadyCompleted
EffectNeedsReconciliation
ApprovalRequired
FencingRejected
StoreUnavailable
```

---

## AP-23 — Infrastructure failure is expected

Les pannes ne doivent pas être traitées comme des cas impossibles.

Sont normales :

```text
network timeout
worker crash
database restart
lease expiry
duplicate delivery
partial outage
```

---

## AP-24 — Async-first, sync-friendly

Le cœur doit être compatible avec les workloads asynchrones.

Une API sync peut être fournie comme façade lorsque pertinent.

---

# 23. Principes spécifiques aux stores

## SP-01 — Store contracts independent

Chaque store doit avoir une responsabilité claire.

Exemple :

```text
RunStore ≠ EffectStore
```

sauf si une implémentation concrète les regroupe physiquement.

---

## SP-02 — Storage implementation may share transactions

Deux ports distincts peuvent partager le même backend PostgreSQL et la même transaction.

Séparation logique ≠ séparation physique obligatoire.

---

## SP-03 — Concurrency semantics documented

Chaque store doit documenter :

- optimistic concurrency ;
- locking ;
- atomicity ;
- transaction boundaries.

---

## SP-04 — No hidden side effects in reads

Une opération de lecture ne doit pas modifier silencieusement le domaine.

---

# 24. Principes spécifiques aux effects

## EP-01 — Persist intent before dangerous effect

Pour les effets critiques, l’intention doit pouvoir être persistée avant l’appel externe.

---

## EP-02 — External reference preferred

Lorsqu’un système externe fournit une référence stable, elle doit être conservée.

---

## EP-03 — Effect input fingerprint

Un effet doit pouvoir conserver une empreinte de ses inputs afin de détecter une collision d’idempotence.

---

## EP-04 — Reconciliation is domain-specific

PyAgentsKit fournit le protocole de reconciliation.

L’application ou l’adapter fournit la logique spécifique.

Exemple :

```text
payment
→ query payment API

git push
→ inspect remote branch

deploy
→ query deployment platform
```

---

# 25. Principes spécifiques aux adapters runtime

## RP-01 — Adapter minimal

L’adapter doit traduire le runtime vers PyAgentsKit sans reproduire tout son modèle interne.

---

## RP-02 — Adapter does not own durability

La durabilité doit rester pilotée par PyAgentsKit.

L’adapter peut exposer une capacité native, mais le core doit garder une sémantique cohérente.

---

## RP-03 — Adapter events normalized

Les événements externes doivent être normalisés vers des événements PyAgentsKit.

---

## RP-04 — Coding specifics outside core

Les notions :

```text
repository
branch
worktree
diff
patch
```

restent dans les adapters de coding agents ou modules dédiés.

---

# 26. Principes spécifiques à la coordination distribuée

## DP-01 — Database is the source of truth for ownership

Lorsque PostgreSQL est utilisé comme backend de référence, la décision d’ownership doit être persistée de manière transactionnelle.

---

## DP-02 — Heartbeat is evidence, not authority

Le heartbeat indique qu’un worker est vivant.

Il ne suffit pas à lui seul à prouver l’ownership.

---

## DP-03 — Lease expiry does not kill a process

L’expiration retire le droit logique d’agir.

Le processus peut continuer à vivre, d’où la nécessité du fencing.

---

## DP-04 — Fencing token monotonicity

Le token doit permettre d’établir l’ordre des ownerships.

---

# 27. Principes d’observabilité

## OP-01 — Metrics must reflect domain events

Exemples :

```text
lease.acquired
→ metric increment

effect.unknown
→ metric increment

run.resumed
→ metric increment
```

---

## OP-02 — No cardinality explosion

Éviter d’utiliser comme labels de métriques :

```text
run_id
effect_id
user_id
```

Les IDs appartiennent aux logs/traces, pas aux labels à forte cardinalité.

---

## OP-03 — Health is local, readiness is dependency-aware

```text
health
→ process alive

readiness
→ process able to serve safely
```

---

# 28. Principes de sécurité

## SEC-01 — Least privilege

Workers, tools et adapters utilisent le minimum de permissions.

---

## SEC-02 — Secrets remain external

Les secrets résident dans :

```text
environment
secret manager
vault
orchestrator secrets
```

et non dans les payloads persistés.

---

## SEC-03 — Approval is not authorization

Une approval humaine ne remplace pas un contrôle d’accès technique.

Les deux peuvent être nécessaires.

---

## SEC-04 — Audit data is sensitive

Les événements d’audit peuvent contenir des metadata sensibles.

Ils doivent respecter les politiques de protection des données.

---

# 29. Architecture logique dérivée

Les principes conduisent à une architecture logique en couches :

```text
┌───────────────────────────────────────┐
│            Agent Applications         │
├───────────────────────────────────────┤
│          Agent Runtime Adapters       │
├───────────────────────────────────────┤
│        Application / Orchestration    │
├───────────────────────────────────────┤
│             Domain Core               │
│ Runs / Effects / Approvals / Leases   │
├───────────────────────────────────────┤
│              Ports                    │
│ Stores / Telemetry / Artifacts        │
├───────────────────────────────────────┤
│             Adapters                  │
│ PostgreSQL / S3 / Runtime SDK / OTel  │
├───────────────────────────────────────┤
│           External Systems            │
└───────────────────────────────────────┘
```

---

# 30. Dépendances autorisées

La direction des dépendances doit tendre vers :

```text
Infrastructure
     ↓
Adapters
     ↓
Application
     ↓
Domain
```

Le domaine ne doit pas dépendre de :

```text
PostgreSQL
Kubernetes
OpenAI
Anthropic
GitHub
S3
```

---

# 31. Anti-patterns explicitement interdits

## APAT-01 — Retry everything

```text
except Exception:
    retry()
```

Interdit sur les effets non garantis idempotents.

---

## APAT-02 — State by exception only

Utiliser uniquement l’absence d’exception comme preuve de succès est insuffisant pour un effet durable.

---

## APAT-03 — Global in-memory ownership

Un dictionnaire Python local ne peut pas être la source de vérité d’ownership distribué.

---

## APAT-04 — Runtime-specific core

Éviter :

```python
if isinstance(agent, LangGraphAgent):
```

dans le domaine.

---

## APAT-05 — Hidden retry in adapters

Un adapter ne doit pas répéter silencieusement un effet critique sans respecter les policies PyAgentsKit.

---

## APAT-06 — Approval implemented as callback only

Une callback mémoire seule ne constitue pas une approval durable.

---

## APAT-07 — Log as audit

Des logs techniques ne remplacent pas un modèle d’audit explicite.

---

## APAT-08 — Infinite lease renewal

Le worker doit perdre son droit lorsqu’il ne satisfait plus les conditions d’ownership.

---

# 32. Règles de décision Build vs Integrate

Une fonctionnalité doit être **construite dans PyAgentsKit** si :

```text
elle définit une sémantique agent-specific
ou
elle protège une garantie centrale
ou
elle doit rester uniforme entre backends
```

Exemples :

```text
Effect lifecycle
Run lifecycle
Approval semantics
Fencing semantics
Recovery decision
```

Une fonctionnalité doit être **intégrée** si :

```text
elle est générique
mature
bien résolue ailleurs
et remplaçable par un port
```

Exemples :

```text
database
object storage
distributed tracing backend
Kubernetes
Temporal
coding agent
```

---

# 33. Règles pour les coding agents

PyAgentsKit peut encadrer :

```text
Codex
Claude Code
OpenCode
agy
future coding agents
```

mais ne doit jamais implémenter :

```text
code understanding
code generation
patch synthesis
repository semantic search
IDE
terminal intelligence
```

Sa valeur est :

```text
ownership
approval
effect safety
recovery
audit
observability
```

---

# 34. Règles pour Temporal / DBOS / autres moteurs durables

PyAgentsKit ne doit pas supposer que son moteur natif est l’unique backend possible.

Une abstraction future peut être :

```text
DurableExecutionBackend
```

Implémentations :

```text
Native
Temporal
DBOS
Restate
other
```

Le domaine PyAgentsKit reste identique.

---

# 35. Critères de revue architecturale

Toute nouvelle feature doit répondre à ces questions :

1. Quel besoin fonctionnel couvre-t-elle ?
2. Quel principe architectural applique-t-elle ?
3. Introduit-elle un couplage framework ?
4. Introduit-elle un couplage infrastructure ?
5. Ajoute-t-elle un nouvel état métier ?
6. Peut-elle produire un effet externe ?
7. Quel est son comportement en cas de crash ?
8. Quel est son comportement en multi-worker ?
9. Comment est-elle observée ?
10. Comment est-elle auditée ?
11. Comment est-elle testée ?
12. Peut-elle être intégrée plutôt que reconstruite ?

---

# 36. Critères de rejet architectural

Une proposition doit être revue ou rejetée si elle :

```text
couple le core à un runtime spécifique
cache un retry d’effet critique
bypass les stores durables
bypass ownership/fencing
introduit un état implicite ambigu
rend la reprise non déterministe
ne peut pas être testée
duplique une infrastructure existante sans justification
```

---

# 37. Traçabilité principes ↔ exigences

| Principe | Exigences principalement couvertes |
|---|---|
| AP-01 | FR-001 à FR-004, NFR-113 à NFR-121 |
| AP-03 | NFR-114, NFR-120 |
| AP-05 | FR-011, FR-062, FR-052 |
| AP-06 | FR-060 à FR-066 |
| AP-07 | FR-045, FR-072 |
| AP-08 | FR-073 à FR-075 |
| AP-09 | FR-080 à FR-084 |
| AP-10 | FR-085 à FR-087 |
| AP-11 | FR-141, NFR-031 |
| AP-12 | FR-041 à FR-045 |
| AP-13 | FR-050 à FR-056 |
| AP-14 | FR-110 à FR-115 |
| AP-15 | FR-100 à FR-103 |
| AP-16 | NFR-126 |
| AP-17 | NFR-121 |
| AP-18 | NFR-126 |

---

# 38. Architecture decision records à créer

Les principes appellent plusieurs ADR.

Exemples :

```text
ADR-001  Pourquoi PostgreSQL comme backend de référence
ADR-002  Séparation RunStore / EffectStore
ADR-003  Fencing tokens monotones
ADR-004  Effect UNKNOWN + reconciliation
ADR-005  AgentRuntimeAdapter
ADR-006  Native durable execution vs Temporal backend
ADR-007  Audit events append-oriented
ADR-008  Async-first public API
ADR-009  Coding-agent adapters hors core
ADR-010  Health vs readiness
```

---

# 39. Definition of Done architecturale

L’architecture de PyAgentsKit respecte ce document si :

1. le core reste indépendant des runtimes ;
2. les backends sont derrière des ports ;
3. les effets sont modélisés explicitement ;
4. aucun replay implicite n’est possible ;
5. les états ambigus passent par reconciliation ;
6. l’ownership est explicite ;
7. le fencing est propagé lorsque nécessaire ;
8. la reprise suit une logique déterministe ;
9. les approvals sont durables ;
10. observabilité et audit sont intégrés à la conception ;
11. les nouvelles intégrations passent par adapters ;
12. l’infrastructure générique n’est pas réimplémentée sans justification ;
13. les coding agents restent externes au core ;
14. toute nouvelle abstraction répond à un besoin identifié.

---

# 40. Résumé

Les principes architecturaux de PyAgentsKit peuvent être condensés en dix règles essentielles :

```text
1. Framework-neutral
2. Ports & adapters
3. Explicit state
4. Effects are first-class
5. No implicit replay
6. Reconcile before retry
7. Explicit ownership
8. Fencing over trust
9. Fail safe
10. Build semantics, integrate infrastructure
```

La phrase directrice de l’architecture est :

> **PyAgentsKit ne doit pas chercher à savoir comment l’agent pense ; il doit garantir dans quelles conditions son exécution peut être considérée comme sûre, durable, contrôlée et récupérable.**

Le document suivant devra formaliser les objets qui incarnent ces principes :

```text
06_PYAGENTSKIT_MODELE_CONCEPTUEL_DU_DOMAINE.md
```
