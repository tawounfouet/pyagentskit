# PyAgentsKit — Competitive & Ecosystem Analysis

**Document :** `../strategy/44_PYAGENTSKIT_COMPETITIVE_AND_ECOSYSTEM_ANALYSIS.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Strategic Market & Architecture Analysis  
**Projet :** PyAgentsKit  

---

# 1. Objet

Ce document analyse le positionnement compétitif et l’écosystème de PyAgentsKit V2.

Il ne cherche pas seulement à répondre à :

```text
Who are the competitors?
```

mais surtout à :

```text
Which layers of the agent stack are already crowded?
Which capabilities are becoming commodities?
Which products are converging toward PyAgentsKit?
Where does PyAgentsKit have a defensible semantic position?
Which projects should be competitors, partners, adapters, or dependencies?
What must PyAgentsKit absolutely not become?
```

Le principe directeur est :

> **PyAgentsKit ne doit pas se différencier par une liste de features ; il doit se différencier par la précision de ses garanties de fiabilité et par sa capacité à appliquer ces garanties à plusieurs runtimes et systèmes externes.**

---

# 2. Executive Summary

Le marché 2026 est en convergence rapide.

Plusieurs familles de produits autrefois distinctes commencent à se rapprocher :

```text
Agent Frameworks
        ↓
Persistence / HITL / Runtime

Durable Execution Platforms
        ↓
AI Agent integrations

AI Gateways / Observability
        ↓
Agent governance

Coding Agents
        ↓
Long-running autonomous execution
```

Cette convergence crée une pression forte sur toute proposition générique du type :

```text
"production-ready agents"
"durable agents"
"reliable agents"
```

Ces formulations ne sont plus suffisamment différenciantes.

La fenêtre stratégique de PyAgentsKit est plus spécifique :

```text
Framework-neutral reliability semantics
+
first-class Effect safety
+
explicit ambiguity
+
reconciliation
+
durable approvals
+
distributed ownership/fencing
+
runtime and connector anti-corruption layers
```

---

# 3. Conclusion stratégique principale

Le concurrent le plus dangereux pour PyAgentsKit n’est pas nécessairement LangGraph.

Le risque principal vient de la combinaison :

```text
Agent Framework
+
Durable Execution Engine
+
Governance / Observability
```

Par exemple :

```text
OpenAI Agents + Temporal
PydanticAI + Temporal
PydanticAI + DBOS
PydanticAI + Restate
LangGraph + LangSmith
Coding Agent + Restate
Coding Agent + Temporal
```

Ces combinaisons peuvent couvrir une partie croissante du problème que PyAgentsKit cherche à résoudre.

La réponse stratégique n’est pas de reconstruire leurs couches.

Elle est de concentrer PyAgentsKit sur les garanties qu’elles ne standardisent pas encore uniformément :

```text
Effect != ToolCall
UNKNOWN != FAILED
Retry != Reconciliation
Approval != Authorization
Lease != Queue claim
Runtime completion != Run success
Fencing across protected Effects
Connector-specific reconciliation
```

---

# 4. Le marché n’est pas une seule catégorie

L’écosystème doit être séparé en plusieurs catégories.

```text
A. Agent Frameworks / SDKs
B. Durable Execution Platforms
C. Agent Runtime / Deployment Platforms
D. AI Gateways / Governance / Security
E. Observability / Evals
F. Human-in-the-loop systems
G. Coding Agents
H. Infrastructure commodities
```

PyAgentsKit croise plusieurs catégories sans devoir les remplacer.

---

# 5. Category A — Agent Frameworks / SDKs

Acteurs représentatifs :

```text
LangGraph / LangChain
PydanticAI
OpenAI Agents SDK
AutoGen
CrewAI
Google ADK
LlamaIndex
```

Leur objectif principal est généralement :

```text
build agents
orchestrate model/tool interactions
manage context
compose agent behavior
```

PyAgentsKit ne doit pas entrer dans une compétition frontale sur :

```text
prompt abstractions
agent construction DSL
model routing syntax
multi-agent topology
tool declaration UX
```

---

# 6. LangGraph / LangChain

## Position

LangGraph fournit une architecture d’agents/workflows basée sur graphes avec :

```text
state
nodes
persistence/checkpoints
interrupts
human-in-the-loop
resume
streaming
subgraphs
```

Les docs LangGraph décrivent explicitement des workflows capables de s’interrompre, persister leur état via checkpointer et reprendre plus tard.

LangGraph présente également le checkpoint comme frontière de durable execution au niveau des nodes.

## Forces

```text
large ecosystem
strong mindshare
rich agent abstractions
HITL
persistence
LangSmith integration
deployment platform
tool ecosystem
```

## Recouvrement avec PyAgentsKit

```text
state persistence
resume
HITL
runs/threads
deployment
observability
```

## Différence potentielle PyAgentsKit

PyAgentsKit doit éviter de vendre simplement :

```text
checkpointing
pause/resume
HITL
```

car LangGraph couvre déjà ces concepts.

La différenciation doit porter sur :

```text
generic Effect model
ambiguous outcome semantics
provider reconciliation
distributed fencing
runtime-neutral contracts
separation Run / RuntimeInvocation
security authority independent from runtime
```

## Relation recommandée

```text
INTEGRATE
not compete as graph framework
```

Créer à terme :

```text
LangGraphRuntimeAdapter
```

---

# 7. LangSmith

LangSmith étend l’écosystème LangChain avec :

```text
tracing
evaluation
deployment
Agent Server
runs
threads
persistent infrastructure
```

La documentation de son data plane montre une architecture utilisant notamment PostgreSQL pour les runs/memory et Redis pour la communication workers.

## Risque de chevauchement

Fort sur :

```text
Agent operations
deployment
observability
run management
```

Faible à moyen sur :

```text
generic side-effect safety
fencing semantics
external effect reconciliation
```

## Relation recommandée

```text
OBSERVABILITY / DEPLOYMENT ADJACENT
```

PyAgentsKit ne doit pas reconstruire LangSmith.

---

# 8. PydanticAI

## Position

PydanticAI est devenu beaucoup plus qu’un simple typed agent SDK.

Il propose notamment :

```text
typed agent framework
deferred tools
human approval
external tool execution
durable execution integrations
```

En 2026, sa documentation présente plusieurs moteurs de durable execution supportés, notamment :

```text
Temporal
DBOS
Prefect
Restate
AWS Lambda
and additional engines
```

## Signal stratégique

PydanticAI reconnaît explicitement la séparation :

```text
agent framework
vs
durable engine
```

et fournit une couche d’intégration entre les deux.

C’est très proche de l’intuition architecturale :

```text
Runtime
+
Reliability infrastructure
```

## Deferred Tools

PydanticAI supporte :

```text
approval-required tools
externally executed tools
deferred results
resume through follow-up run/conversation
```

Sa documentation avertit également que :

```text
approval != authorization boundary
```

ce qui converge fortement avec le modèle Governance de PyAgentsKit.

## Risque compétitif

Élevé si PyAgentsKit se positionne comme :

```text
"typed production agent framework"
```

Moyen si PyAgentsKit reste :

```text
runtime-neutral reliability semantics
```

## Relation recommandée

```text
PydanticAI = runtime/framework to integrate
+
important architectural benchmark
```

---

# 9. OpenAI Agents SDK

## Position

L’OpenAI Agents SDK propose notamment :

```text
agents
tools
handoffs
sessions
run state
human-in-the-loop approvals
streaming
```

Sa documentation HITL permet de :

```text
pause a run
surface interruptions
approve/reject tool calls
serialize RunState
resume
```

Des protections contre certains replays incertains sont également documentées dans les flows de reprise.

## Recouvrement

```text
run state
session
approval
tool execution
resume
```

## Limite stratégique pour PyAgentsKit

PyAgentsKit ne doit pas imiter l’API agentique de l’OpenAI SDK.

Il doit pouvoir placer ce SDK derrière :

```text
OpenAIAgentsRuntimeAdapter
```

## Opportunité

Le partenariat OpenAI Agents SDK + Temporal prouve que :

```text
agent SDK
+
durable execution
```

est une architecture validée dans l’écosystème.

PyAgentsKit peut se positionner comme une couche de fiabilité plus spécialisée et indépendante du moteur durable choisi.

---

# 10. AutoGen

AutoGen reste fortement orienté :

```text
agents
teams
multi-agent interaction
state save/load
human interaction
```

Sa documentation souligne que certains patterns HITL bloquants pendant un run rendent l’état difficile à sauver/reprendre, tandis que les patterns de feedback entre runs s’appuient sur persistence explicite.

## Positionnement

AutoGen est principalement :

```text
Agent framework / multi-agent framework
```

et non un concurrent direct de la reliability layer.

## Relation recommandée

```text
future Runtime Adapter
```

si demande utilisateur suffisante.

---

# 11. CrewAI

CrewAI appartient principalement à la catégorie :

```text
agent orchestration / crews / flows
```

PyAgentsKit ne doit pas concurrencer ses abstractions de composition.

Relation cible :

```text
optional runtime integration
```

---

# 12. Category B — Durable Execution Platforms

Acteurs majeurs :

```text
Temporal
Restate
DBOS
Inngest
Prefect
```

Cette catégorie constitue le voisinage stratégique le plus important.

---

# 13. Temporal

## Position

Temporal est un moteur généraliste de Durable Execution extrêmement mature.

En 2026, Temporal positionne explicitement ses capabilities sur les AI agents et affirme que les agents sont des systèmes distribués nécessitant :

```text
durability
crash recovery
long-running workflows
human input
observability
```

Temporal fournit :

```text
Workflows
Activities
durable timers
signals
queries
retries
worker recovery
versioning primitives
human interaction patterns
```

## Mouvement 2026

Temporal pousse fortement les usages agents :

```text
OpenAI Agents integration GA
AI agent tutorials
sandbox orchestration patterns
coding-agent durability examples
```

Il a notamment documenté en octobre 2026 l’exécution durable d’un coding agent Pi avec worker handover sans répétition automatique d’un tool call interrompu.

## Menace stratégique

**Très élevée** si PyAgentsKit veut devenir un moteur générique de durable execution.

Temporal est plus mature, plus général, plus déployé et bénéficie d’un écosystème considérable.

## Zone où PyAgentsKit peut rester différent

PyAgentsKit peut posséder une couche métier spécialisée au-dessus ou à côté de Temporal :

```text
Effect semantics
approval scope semantics
connector reconciliation
runtime adapter model
agent-specific ownership
security model
canonical Run model
```

## Relation recommandée

Long terme :

```text
TemporalDurabilityAdapter
or
Temporal-backed execution profile
```

sans faire de Temporal une dépendance obligatoire.

---

# 14. Restate

## Position

Restate se présente comme :

```text
The Durable Runtime for your Agents and Backends
```

Il se positionne clairement sur :

```text
durable execution
stateful orchestration
agent reliability
pause/resume/restart
long-running services
```

En 2026, Restate publie plusieurs contenus explicitement centrés agents :

```text
OpenAI SDK integration
PydanticAI integration
Google ADK integration
coding agent
agent resiliency
checkpointing limitations
versioning long-running agents
```

## Signal compétitif

Restate attaque exactement l’idée :

> checkpointing alone is insufficient for production-grade agents.

Ce framing rejoint directement PyAgentsKit.

## Force

Restate offre le moteur durable lui-même.

PyAgentsKit ne doit donc pas tenter de battre Restate sur :

```text
low-level durable runtime
distributed log
queue/runtime performance
serverless execution engine
```

## Différenciation PyAgentsKit

Rester au-dessus du moteur :

```text
explicit external Effect semantics
approval domain
connector reconciliation
runtime-neutral ACL
ownership/fencing contract
audit semantics
```

## Relation recommandée

```text
potential durable backend integration
+
important direct adjacent competitor
```

---

# 15. DBOS

## Position

DBOS fournit de la durable execution directement dans Python/TypeScript avec :

```text
workflows
steps
recovery
database-backed state
queues
```

Il dispose d’intégrations agents avec notamment :

```text
OpenAI Agents SDK
PydanticAI
Google ADK
LlamaIndex
```

## Architecture

Les workflows sont checkpointés et reprennent depuis le dernier step terminé.

## Forces

```text
simple developer model
Python-friendly
Postgres-centric
strong integration story
agent integrations
```

## Risque compétitif

Élevé auprès des développeurs Python recherchant :

```text
"make my agent durable"
```

avec très peu de code.

## Différenciation PyAgentsKit

PyAgentsKit doit offrir autre chose que :

```text
workflow checkpointing
```

Il doit capitaliser sur :

```text
side-effect ambiguity model
reconciliation
fencing
approval authority
runtime/connector neutrality
```

## Relation recommandée

```text
possible durability backend
+
adjacent competitor
```

---

# 16. Inngest

## Position

Inngest propose une plateforme de durable workflows et durable agents avec :

```text
steps
checkpointing
retries
waits
events
concurrency
flow control
observability
human-in-the-loop
```

En 2026, Inngest positionne explicitement :

```text
durable agent
=
durable workflow whose next step is chosen by a model
```

## Forces

```text
developer experience
serverless-friendly
queue/flow control
durable execution
observability
AI agent patterns
```

## Menace

Moyenne à forte selon segment.

Un développeur recherchant :

```text
durable functions for agents
```

peut préférer Inngest.

## Différenciation PyAgentsKit

Encore une fois :

```text
PyAgentsKit should not compete on generic durable steps.
```

Il doit se concentrer sur la fiabilité métier des actions et l’intégration multi-runtime.

---

# 17. Prefect

Prefect est historiquement centré sur workflow orchestration/data workflows.

Il peut servir de moteur durable sous certaines architectures agentiques.

PydanticAI le supporte parmi ses moteurs de durable execution.

## Relation recommandée

```text
potential integration
not a primary direct competitor
```

---

# 18. Category C — Agent Deployment / Runtime Platforms

Exemples :

```text
LangSmith Agent Server
managed agent platforms
cloud agent runtimes
provider-specific deployment systems
```

Ces plateformes peuvent offrir :

```text
worker management
runs
threads
scaling
deployment
persistence
```

PyAgentsKit ne doit pas devenir une PaaS complète.

---

# 19. Category D — AI Gateways / Governance / Security

Acteurs représentatifs :

```text
Portkey / Prisma AIRS AI Gateway
MCP gateways
policy/security gateways
```

---

# 20. Portkey / Prisma AIRS AI Gateway

## Position 2026

Portkey s’est déplacé d’un simple LLM gateway vers une couche plus large :

```text
Agent Gateway
governance
access control
agent registry
observability
guardrails
routing
MCP gateway
```

Le produit se présente comme compatible avec plusieurs frameworks.

## Recouvrement PyAgentsKit

```text
governance
security
agent registry
observability
reliability terminology
```

## Différence fondamentale

Portkey agit principalement comme :

```text
network/gateway control plane
```

PyAgentsKit vise :

```text
execution semantic control plane
```

## Position recommandée

Ne pas concurrencer Portkey sur :

```text
LLM routing
gateway
central proxy
model catalog
PII guardrails platform
```

PyAgentsKit peut l’intégrer comme :

```text
external Authorization/Policy/Telemetry capability
```

---

# 21. Category E — Observability & Evals

Acteurs :

```text
LangSmith
Arize Phoenix
Langfuse
MLflow
Portkey
```

Ils couvrent :

```text
tracing
evaluation
quality monitoring
cost
latency
datasets
debugging
```

PyAgentsKit doit produire les bons événements/metrics/traces mais ne doit pas devenir une plateforme d’observabilité.

---

# 22. Observability distinction

```text
Observability platform
answers:
"What happened technically?"

PyAgentsKit Audit
answers:
"Who was authorized to do what, why, and what external effect resulted?"
```

Cette distinction doit être conservée.

---

# 23. Category F — Human-in-the-Loop

Aujourd’hui HITL est déjà disponible dans plusieurs frameworks :

```text
LangGraph interrupts
OpenAI Agents approvals
PydanticAI deferred tools
DBOS durable HITL
Temporal signals/workflows
```

Donc :

```text
human approval
```

à lui seul n’est plus un différenciateur.

---

# 24. PyAgentsKit Governance differentiation

La différence doit être :

```text
Approval as durable aggregate
+
scope fingerprint
+
authorization separation
+
SoD
+
revalidation after recovery
+
audit evidence
```

et non simplement :

```text
pause and ask user yes/no
```

---

# 25. Category G — Coding Agents

Exemples :

```text
Codex
Claude Code
OpenCode
Pi
Cursor-like agents
```

Ces outils deviennent de plus en plus :

```text
long-running
tool-using
autonomous
workspace-aware
remote-action capable
```

Ils constituent un marché particulièrement intéressant pour PyAgentsKit.

---

# 26. Coding-agent opportunity

Coding agents exécutent des actions à fort impact :

```text
file edit
shell command
git commit
git push
PR creation
PR merge
package publish
deployment
terraform apply
```

La distinction :

```text
local computation
vs
persistent external effect
```

est particulièrement importante ici.

---

# 27. Competitive signal — durable coding agents

Temporal documente en 2026 un coding agent durable.

Restate a également publié des architectures de coding agents durables.

Cela valide la demande mais réduit la nouveauté du message :

```text
"durable coding agent"
```

PyAgentsKit doit aller plus loin :

```text
safe coding Effects
+
fencing
+
approval bound to exact SHA/fingerprint
+
external reconciliation
+
runtime-neutral coding-agent adapters
```

---

# 28. Competitive Landscape Map

```text
                         AGENT CREATION
                              ▲
                              │
        LangGraph ────────────┼──────── PydanticAI
        OpenAI Agents         │         AutoGen
                              │
                              │
                              │
GENERAL DURABILITY ◄──────────┼──────────► AGENT GOVERNANCE
                              │
 Temporal                     │          Portkey
 Restate                      │          LangSmith
 DBOS                         │
 Inngest                      │
                              │
                              ▼
                    EFFECT-SAFETY SEMANTICS
                         PyAgentsKit
```

La position cible PyAgentsKit est volontairement sous le runtime :

```text
not "how to reason"
but
"how to execute safely"
```

---

# 29. Competitive Capability Matrix

Légende :

```text
● strong/native
◐ partial / pattern-dependent
○ limited / external
— not primary focus
```

| Capability | PyAgentsKit target | LangGraph | PydanticAI | OpenAI Agents | Temporal | Restate | DBOS | Inngest | Portkey |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Agent construction | ○ | ● | ● | ● | — | — | — | ◐ | — |
| Runtime-neutral reliability | ● | ○ | ◐ | ○ | ● | ● | ● | ● | ◐ |
| Durable execution | ● | ● | ● via engines | ◐ / integrations | ● | ● | ● | ● | — |
| HITL pause/resume | ● | ● | ● | ● | ● | ● | ● | ● | — |
| First-class Effect domain | ● | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | ◐ | — |
| Explicit UNKNOWN outcome | ● | ○ | ○/partial | partial | workflow-specific | partial | partial | partial | — |
| ReconciliationCase | ● | — | — | — | application-level | application-level | application-level | application-level | — |
| Idempotency semantics | ● | application | application | tool/provider | ● patterns | ● patterns | ● patterns | ● patterns | gateway-level |
| Lease + fencing contract | ● | — | — | — | engine internal | engine internal | engine internal | engine internal | — |
| Durable approval aggregate | ● | ◐ | ◐ | ◐ | workflow pattern | workflow pattern | workflow pattern | workflow pattern | policy-focused |
| AuthZ != Approval model | ● | app-level | explicitly noted | app-level | app-level | app-level | app-level | app-level | ● |
| Runtime adapter standard | ● | — | durability adapters | — | integrations | integrations | integrations | integrations | framework integrations |
| Connector reconciliation | ● | — | — | — | app-specific | app-specific | app-specific | app-specific | — |
| Audit semantics | ● | tracing | — | tracing | history | history | workflow history | traces | ● |
| Coding-agent Effects | ● target | Deep Agents | possible | possible | emerging | emerging | possible | possible | gateway-level |

Cette matrice décrit le **positionnement conceptuel**, pas une certification exhaustive de chaque produit.

---

# 30. Direct vs Adjacent Competition

## Tier 1 — Strongest strategic overlap

```text
Temporal
Restate
DBOS
Inngest
```

Pourquoi ?

Parce qu’ils revendiquent :

```text
durable execution
crash recovery
long-running agents
HITL
production reliability
```

---

# 31. Tier 2 — Framework overlap

```text
LangGraph
PydanticAI
OpenAI Agents SDK
```

Ils se rapprochent de la reliability layer mais restent d’abord des frameworks/SDKs agents.

---

# 32. Tier 3 — Governance/operations overlap

```text
Portkey
LangSmith
Langfuse
Arize
```

Ils couvrent une partie du control plane mais pas le même niveau sémantique.

---

# 33. Tier 4 — Ecosystem partners

```text
PostgreSQL
OpenTelemetry
S3-compatible storage
OIDC/IAM providers
GitHub/GitLab
Kubernetes
```

Ce sont principalement des dépendances ou integrations.

---

# 34. PyAgentsKit competitive wedge

La wedge la plus crédible est :

> **The reliability control layer for agent side effects.**

Décomposition :

```text
Agent runtime
can think and request actions.

PyAgentsKit
decides whether those actions may safely become durable external effects.
```

---

# 35. Strong Positioning Statement

```text
PyAgentsKit is a framework-neutral reliability layer
that makes long-running agent execution,
external side effects,
human approvals,
distributed ownership,
and recovery explicit and auditable.
```

---

# 36. Positioning to Avoid

Éviter :

```text
"the best AI agent framework"
```

Trop encombré.

---

# 37. Positioning to Avoid

```text
"durable execution for agents"
```

Trop directement concurrencé par :

```text
Temporal
Restate
DBOS
Inngest
```

---

# 38. Positioning to Avoid

```text
"human-in-the-loop agents"
```

Devenu standard.

---

# 39. Positioning to Avoid

```text
"agent observability"
```

Marché déjà très spécialisé.

---

# 40. Positioning to Prefer

```text
Reliable external effects for autonomous agents
```

ou :

```text
A runtime-neutral reliability and governance layer
for agent actions that matter.
```

---

# 41. Key moat candidate — Effect model

Le meilleur actif conceptuel de PyAgentsKit peut devenir :

```text
Effect
```

si le modèle reste plus précis que :

```text
tool call
workflow step
activity
node
```

---

# 42. Why Effect can be defensible

Un Effect transporte des concepts que les abstractions génériques ne regroupent pas forcément :

```text
durable intent
idempotency
fingerprint
risk
approval scope
ownership/fencing
external reference
provider reconciliation
audit
```

---

# 43. Key moat candidate — UNKNOWN

Beaucoup de systèmes parlent de :

```text
retry
failure
resume
```

PyAgentsKit doit insister sur :

```text
UNKNOWN
```

comme classe métier fondamentale.

---

# 44. Why UNKNOWN matters

Exemple :

```text
POST /payment
request leaves process
network disconnects
response missing
```

La réalité n’est pas :

```text
FAILED
```

mais :

```text
UNKNOWN
```

C’est une distinction centrale pour les agents agissant sur le monde réel.

---

# 45. Key moat candidate — Reconciliation

La reconciliation permet de passer :

```text
UNKNOWN
↓
query external reality
↓
CONFIRMED_SUCCESS / FAILURE / STILL_UNKNOWN
```

Cette logique est plus spécialisée qu’un moteur de retry.

---

# 46. Key moat candidate — OwnershipContext

Le couple :

```text
Lease
+
FencingToken
```

rendu explicite au niveau des Effects peut empêcher des workers zombies de créer de nouveaux effets.

---

# 47. Why engine-internal fencing is insufficient as positioning

Temporal/Restate peuvent protéger leur propre exécution.

PyAgentsKit cherche à transporter l’autorité jusqu’au :

```text
protected external operation
```

lorsque le système cible/adaptor peut valider le token.

C’est une nuance importante.

---

# 48. Key moat candidate — Approval scope

Une Approval PyAgentsKit devrait être attachée à :

```text
exact Effect
exact fingerprint
possibly exact commit SHA
policy version
```

et non à un vague :

```text
"user clicked approve"
```

---

# 49. Key moat candidate — runtime neutrality

Si les mêmes invariants fonctionnent sur :

```text
Native Runner
LangGraph
PydanticAI
OpenAI Agents
Codex
Claude Code
```

PyAgentsKit gagne une valeur indépendante du framework.

---

# 50. Key moat candidate — connector reconciliation

Une reliability layer devient plus utile si elle sait :

```text
how to verify GitHub PR creation
how to verify deployment
how to verify provider operation
```

via adapters spécifiques.

---

# 51. Strategic Flywheel

```text
More Runtime Adapters
        ↓
More Runs governed
        ↓
More Effect patterns
        ↓
Better Connector Reconciliation
        ↓
Stronger reliability semantics
        ↓
More Runtime value
```

---

# 52. Ecosystem strategy

Le projet doit traiter l’écosystème comme :

```text
integration surface
```

et non comme :

```text
replacement targets
```

---

# 53. Runtime Ecosystem

P0 :

```text
NativeRuntimeAdapter
```

P1 :

```text
one general-purpose runtime
one coding runtime
```

P2 :

```text
broader adapter ecosystem
```

---

# 54. General-Purpose Runtime shortlist

Candidats principaux :

```text
LangGraph
PydanticAI
OpenAI Agents SDK
```

---

# 55. Recommended first external runtime criteria

Choisir selon :

```text
tool interception capability
resume capability
runtime state access
checkpoint support
event stream
community adoption
Python quality
integration stability
```

---

# 56. PydanticAI as particularly interesting adapter target

Raisons :

```text
Python-first
typed
approval/deferred-tool model
explicit durable-engine integrations
good conceptual fit
```

Mais il possède déjà sa propre abstraction de durable execution.

L’intégration PyAgentsKit doit donc démontrer une valeur supplémentaire.

---

# 57. LangGraph as particularly important market benchmark

Raisons :

```text
large ecosystem
deep production adoption
strong persistence/HITL
LangSmith deployment stack
```

Une intégration réussie montrerait la neutralité face à un runtime déjà riche.

---

# 58. OpenAI Agents as ecosystem signal

Une intégration montrerait que PyAgentsKit peut gouverner un SDK agentique fournisseur sans dépendre de son backend.

---

# 59. Coding Runtime shortlist

```text
Codex
Claude Code
OpenCode
```

---

# 60. Coding Agent integration acceptance test

Exemple de scénario cible :

```text
coding runtime edits repository
↓
runs tests
↓
requests git push
↓
PyAgentsKit creates Effect
↓
approval bound to commit SHA
↓
worker loses lease
↓
new worker takes over
↓
Effect state checked
↓
push not duplicated
```

---

# 61. Connector ecosystem

P0/P1 :

```text
GitHub
Generic HTTP
```

Puis :

```text
GitLab
Azure DevOps
Slack
Jira
cloud providers
```

---

# 62. Why GitHub is strategic

GitHub combine :

```text
read operations
writes
immutable-ish references
external IDs
idempotency challenges
reconciliation opportunities
coding-agent workflows
```

---

# 63. Durable Engine Ecosystem

PyAgentsKit doit garder une porte ouverte à :

```text
Temporal
Restate
DBOS
```

comme backends potentiels ou integrations futures.

---

# 64. Critical strategic question

À long terme, PyAgentsKit doit choisir entre :

```text
A. own durable execution engine
B. delegate durable execution to engines
C. support both profiles
```

La recommandation V2 actuelle est :

```text
C
```

avec :

```text
native lightweight execution
+
optional external durable backends
```

à condition que les sémantiques PyAgentsKit restent autoritatives.

---

# 65. Why not Temporal-only

Cela transformerait PyAgentsKit en :

```text
Temporal agent library
```

et réduirait sa neutralité.

---

# 66. Why not reinvent Temporal

Cela créerait une compétition disproportionnée sur :

```text
distributed workflow engine
history service
task queues
operational platform
```

qui n’est pas le différenciateur.

---

# 67. Why keep Native durability

Avantages :

```text
lightweight installation
local usage
lower dependency burden
reference semantics
testability
independent core
```

---

# 68. Why external durable backends still matter

Ils offrent :

```text
scale
maturity
operational tooling
ecosystem
managed services
```

---

# 69. Product architecture implication

Séparer :

```text
Reliability Semantics
```

de :

```text
Durability Mechanism
```

---

# 70. Reliability Semantics

Appartiennent à PyAgentsKit :

```text
Effect
Approval
Recovery decision
Ownership
Audit
```

---

# 71. Durability Mechanism

Peut être implémenté par :

```text
native PostgreSQL
Temporal
Restate
DBOS
```

selon profil futur.

---

# 72. Competitive risk R1 — Durable execution commoditization

Probabilité :

```text
HIGH
```

Impact :

```text
HIGH
```

Durable execution devient rapidement disponible dans plusieurs frameworks.

## Réponse

Ne pas positionner PyAgentsKit uniquement sur durability.

---

# 73. Risk R2 — Agent frameworks absorb reliability

LangGraph/Pydantic/OpenAI ajoutent :

```text
HITL
persistence
resume
approvals
```

## Réponse

Accentuer les sémantiques cross-runtime et cross-system.

---

# 74. Risk R3 — Durable engines absorb agent features

Temporal/Restate/DBOS/Inngest ajoutent :

```text
agent integrations
coding agent examples
HITL
observability
```

## Réponse

Ne pas devenir durable engine généraliste.

---

# 75. Risk R4 — Gateway vendors absorb governance

Portkey et autres ajoutent :

```text
RBAC
agent registry
policy
guardrails
MCP governance
```

## Réponse

Conserver Governance au niveau :

```text
durable action authority
```

et intégrer les gateways comme policy sources.

---

# 76. Risk R5 — Too broad scope

Si PyAgentsKit ajoute :

```text
agents
RAG
scheduling
prompt management
gateway
observability backend
```

il perdra sa différenciation.

---

# 77. Risk R6 — Too narrow runtime compatibility

Si seul le Native Runner fonctionne réellement :

```text
framework-neutral claim is not proven
```

---

# 78. Risk R7 — Abstract architecture without adoption

Un design très rigoureux ne suffit pas.

Il faut des scénarios concrets.

---

# 79. Required flagship scenarios

Au minimum :

```text
financial/external write with UNKNOWN + reconciliation
human-approved destructive action
distributed worker takeover
coding agent git push/PR
external runtime integration
```

---

# 80. Risk R8 — Reliability semantics too hard to use

Une API trop complexe peut pousser les développeurs vers :

```text
Temporal directly
DBOS directly
PydanticAI durability
```

---

# 81. Developer experience requirement

Le chemin simple doit rester simple :

```python
kit = PyAgentsKit(...)
run = await kit.runs.create(...)
await kit.runs.start(run.run_id)
```

Les garanties avancées doivent être progressivement exposées.

---

# 82. Risk R9 — Overclaiming

Éviter :

```text
exactly once
crash proof
never duplicates
```

sans conditions.

Préférer :

```text
explicit ambiguity
idempotency
deduplication
fencing
reconciliation
```

---

# 83. Risk R10 — Missing operational story

Les concurrents durables disposent de fortes histoires opérations.

PyAgentsKit doit fournir :

```text
readiness
drain
metrics
audit
runbooks
migration
recovery tooling
```

---

# 84. Competitive advantage — transparency

PyAgentsKit peut se distinguer en rendant les limites explicites.

Exemple :

```text
SideEffectControlLevel
RuntimeControlLevel
AdapterQualificationLevel
```

---

# 85. Adapter capability truthfulness

Un adapter doit dire :

```text
what it can guarantee
what it cannot intercept
what it cannot reconcile
```

Cette honnêteté est une caractéristique produit.

---

# 86. Ecosystem compatibility strategy

Chaque adapter doit être :

```text
small
replaceable
optional
contract-tested
capability-aware
```

---

# 87. Adapter qualification

Niveaux :

```text
L0 Fake
L1 Contract
L2 Integration
L3 Failure
L4 Production Qualified
```

---

# 88. Competitive message

Un message crédible pourrait être :

> **PyAgentsKit does not replace your agent framework or durable workflow engine. It defines and enforces the reliability contract around what your agents are allowed to do in the real world.**

---

# 89. Alternate concise message

> **Reliable effects for autonomous agents.**

---

# 90. Developer-oriented message

> **Use LangGraph, PydanticAI, OpenAI Agents, Codex or your own runtime. PyAgentsKit makes approvals, external effects, recovery and distributed ownership explicit.**

---

# 91. Enterprise-oriented message

> **A framework-neutral control layer for governing and recovering autonomous agent actions across systems.**

---

# 92. What PyAgentsKit should benchmark against

## Reliability

```text
Temporal
Restate
DBOS
Inngest
```

## Runtime UX

```text
PydanticAI
OpenAI Agents
LangGraph
```

## Governance UX

```text
Portkey
enterprise IAM/policy tools
```

## Observability UX

```text
LangSmith
Langfuse
Arize
```

---

# 93. What PyAgentsKit should not benchmark against directly

Do not optimize toward feature parity with every:

```text
agent framework
workflow engine
gateway
observability product
```

---

# 94. Ecosystem leverage opportunities

PyAgentsKit can use external products to strengthen itself.

Examples :

```text
Temporal / Restate / DBOS
→ optional durability engines

LangGraph / PydanticAI / OpenAI Agents
→ runtime adapters

Portkey / OIDC / OPA
→ governance/security adapters

LangSmith / OTel
→ telemetry exports

GitHub
→ first reconciliation-rich connector
```

---

# 95. Open standards to leverage

Important standards/ecosystem conventions include :

```text
OpenTelemetry
OIDC
OAuth
MCP where appropriate
HTTP
PostgreSQL
S3-compatible APIs
```

PyAgentsKit should avoid proprietary reinvention where a standard is sufficient.

---

# 96. MCP

MCP is relevant primarily as :

```text
tool/connectivity protocol
```

not as a replacement for :

```text
Effect safety
Authorization
Approval
Reconciliation
```

---

# 97. MCP security implication

A tool being reachable through MCP does not establish :

```text
authority
safe retry
idempotency
business approval
```

PyAgentsKit remains useful around MCP-enabled tools.

---

# 98. Competitive whitespace

The strongest whitespace is the intersection :

```text
             RUNTIME NEUTRAL
                   ▲
                   │
      EFFECT SAFETY│
                   │
  ◄────────────────┼────────────────►
                   │
       GOVERNANCE  │ DISTRIBUTED
                   │ OWNERSHIP
                   ▼
              RECOVERY
```

Few products make all four dimensions one explicit domain model.

---

# 99. Strategic hypothesis H1

Developers will increasingly use several agent runtimes in one organization.

If true :

```text
runtime-neutral governance/reliability
```

gains value.

---

# 100. H2

External tool calls will become more consequential than model outputs.

If true :

```text
Effect-first architecture
```

gains value.

---

# 101. H3

Agent failures will increasingly be distributed-systems failures.

If true :

```text
ownership
fencing
reconciliation
```

become important.

---

# 102. H4

Approvals will need stronger evidence than chat confirmation.

If true :

```text
fingerprint-bound Approval
```

becomes important.

---

# 103. H5

Coding agents are an early high-value vertical.

Because their actions map naturally to :

```text
workspace
command
git
PR
deployment
```

with clear external Effects.

---

# 104. Validation plan for H1

Implement two heterogeneous runtime adapters and measure how much core code remains unchanged.

Success :

```text
>90% reliability semantics shared
```

conceptually.

---

# 105. Validation plan for H2

Build connectors for :

```text
GitHub
generic HTTP write
```

and validate UNKNOWN/reconciliation.

---

# 106. Validation plan for H3

Run :

```text
SIGKILL
lease expiry
takeover
stale worker
split-brain attempts
```

against actual protected Effects.

---

# 107. Validation plan for H4

Approval tests :

```text
same SHA
changed SHA
expired approval
takeover after approval
policy version change
```

---

# 108. Validation plan for H5

Build a coding-agent reference example :

```text
issue
→ code edit
→ tests
→ approval
→ push
→ PR
```

---

# 109. Market signal — durable execution is becoming a category

Temporal, Restate, DBOS and Inngest all explicitly market durable execution for agentic workloads.

This validates the problem.

It also means PyAgentsKit needs a narrower identity.

---

# 110. Market signal — framework/durability composability

PydanticAI supporting several durable engines is particularly important.

It shows that :

```text
agent framework
and
durability engine
```

are becoming independently composable layers.

---

# 111. PyAgentsKit architecture must reflect this

The V2 architecture should therefore avoid coupling :

```text
AgentRuntimeAdapter
```

to :

```text
one durability implementation
```

---

# 112. Future DurabilityBackend concept

Possible future abstraction :

```text
DurabilityBackend
```

or internal execution engine strategy.

But it should not be introduced before a concrete second backend proves the need.

---

# 113. Competitive moat is not code volume

PyAgentsKit cannot out-code all major frameworks/platforms.

Its moat must be :

```text
semantic precision
safety model
interoperability
qualification evidence
```

---

# 114. Qualification as differentiator

Publishing real failure qualification can differentiate more than adding another adapter.

Example evidence :

```text
kill worker during push
takeover
prove no duplicate
```

---

# 115. Documentation as differentiator

The detailed domain model can become a strength if paired with executable proof.

---

# 116. Avoid architecture-only product

Every major architecture concept should map to :

```text
API
test
demo
failure scenario
```

---

# 117. Recommended flagship demo 1

## Financial / Payment-like Effect

```text
Run
→ protected Effect
→ request leaves process
→ timeout
→ UNKNOWN
→ reconciliation
→ confirmed success
→ no replay
```

---

# 118. Flagship demo 2

## Coding Agent

```text
Codex/Claude Code
→ code change
→ commit
→ approval exact SHA
→ push
→ worker crash
→ takeover
→ safe recovery
```

---

# 119. Flagship demo 3

## Multi-runtime

Same business workflow executed with :

```text
Native Runtime
+
LangGraph/PydanticAI
```

through the same PyAgentsKit reliability contract.

---

# 120. Flagship demo 4

## Approval Governance

Show :

```text
free-text "ok"
does not approve

signed/authorized Approval
does approve exact Effect fingerprint
```

---

# 121. Flagship demo 5

## Stale worker

Worker A loses lease.

Worker B takes over.

Worker A attempts protected write with stale fencing token.

Result :

```text
rejected
```

---

# 122. Competitive differentiation scorecard

| Dimension | PyAgentsKit target strength | Strategic importance |
|---|---:|---:|
| Agent building | Low | Low |
| Model abstraction | Medium | Low |
| Generic durable workflows | Medium | Medium |
| Effect safety | Very High | Very High |
| Ambiguity/reconciliation | Very High | Very High |
| HITL | High | Medium |
| Approval governance | Very High | High |
| Distributed ownership | Very High | High |
| Runtime neutrality | Very High | Very High |
| Connector neutrality | High | High |
| Observability | Medium | Medium |
| Audit | High | High |
| Coding-agent governance | High | High |

---

# 123. Strategic non-goals

PyAgentsKit should explicitly state :

```text
We do not aim to replace agent frameworks.
We do not aim to replace durable workflow engines.
We do not aim to replace IAM.
We do not aim to replace observability platforms.
We do not aim to replace message brokers.
```

---

# 124. Why this strengthens rather than weakens positioning

A narrower product boundary makes the value proposition clearer.

---

# 125. Build / Buy / Integrate consequence

BUILD :

```text
Effect semantics
Recovery
Governance
Ownership
canonical contracts
```

INTEGRATE :

```text
LangGraph
PydanticAI
OpenAI Agents
Temporal
Restate
DBOS
GitHub
OIDC
OpenTelemetry
```

---

# 126. Product packaging implication

Core package :

```text
pyagentskit
```

Optional adapters :

```text
pyagentskit[postgres]
pyagentskit[langgraph]
pyagentskit[pydantic-ai]
pyagentskit[codex]
pyagentskit[opentelemetry]
```

or separate packages later.

---

# 127. Open-source strategy

An open-source core is strategically useful because reliability infrastructure benefits from :

```text
trust
inspectability
adapter ecosystem
self-hosting
```

---

# 128. Managed product possibility

A future commercial/managed layer could focus on :

```text
control plane
operations
audit search
managed PostgreSQL
adapter management
policy management
fleet observability
```

without changing the OSS semantics.

---

# 129. Do not prematurely build SaaS

First establish :

```text
core adoption
runtime integrations
Effect model
qualification evidence
```

---

# 130. Community ecosystem

Useful contributions :

```text
runtime adapters
connector adapters
reconciliation strategies
qualification fixtures
policy adapters
```

---

# 131. Plugin quality challenge

Third-party adapter quality can weaken the brand.

Hence :

```text
qualification levels
```

must be visible.

---

# 132. Ecosystem certification

Potential future labels :

```text
Community
Verified
Production Qualified
```

---

# 133. Competitive monitoring

Watch quarterly :

```text
Temporal AI features
Restate AI features
DBOS integrations
Inngest agent features
LangGraph/LangSmith durability
PydanticAI durable execution
OpenAI Agents persistence/HITL
Portkey agent governance
coding-agent runtime capabilities
```

---

# 134. Signals that require strategy review

Review positioning if a competitor ships all of :

```text
generic Effect domain
UNKNOWN/reconciliation
external fencing propagation
durable approval scope
runtime-neutral adapters
connector reconciliation
```

as a coherent product.

---

# 135. Signals that do not require strategy change

Competitor adds :

```text
another LLM provider
another agent template
new UI
prompt management
basic HITL
```

These are not PyAgentsKit’s primary differentiation.

---

# 136. Competitive ADR candidates

```text
ADR-COMP-001 Product Category Definition
ADR-COMP-002 Runtime-neutral vs Durable-engine-neutral scope
ADR-COMP-003 Temporal integration strategy
ADR-COMP-004 First external runtime
ADR-COMP-005 First coding runtime
ADR-COMP-006 First connector
ADR-COMP-007 Effect model as core differentiation
ADR-COMP-008 Open-core / managed boundary
```

---

# 137. Roadmap implications

## 2.0.0a1–a3

Prioritize :

```text
semantic moat
```

not adapter count.

---

# 138. 2.0.0a4

Prove :

```text
native production-grade persistence
```

without claiming to replace durable engines.

---

# 139. 2.0.0b1

Strengthen :

```text
approval/authz/audit differentiation
```

---

# 140. 2.0.0b2

This is the most important competitive proof release.

It must prove :

```text
runtime neutrality is real
```

---

# 141. b2 minimum

```text
Native
+
general-purpose external runtime
+
coding runtime
+
GitHub connector
```

---

# 142. RC1

Public API should expose the semantic concepts directly.

Do not hide them behind generic :

```text
workflow
task
step
```

---

# 143. V2 stable

The claim should be :

```text
production-qualified reliability semantics
```

not :

```text
more features than every framework
```

---

# 144. Overall competitor classification

| Product | Category | Threat | Partner potential |
|---|---|---:|---:|
| Temporal | Durable execution | Very High adjacent | Very High |
| Restate | Durable runtime | Very High adjacent | High |
| DBOS | Durable execution library | High | High |
| Inngest | Durable workflow platform | High | Medium |
| LangGraph | Agent runtime/framework | High overlap | Very High |
| PydanticAI | Agent framework + durability integrations | High overlap | Very High |
| OpenAI Agents SDK | Agent SDK | Medium/High | Very High |
| AutoGen | Agent/multi-agent framework | Medium | Medium |
| Portkey | Agent/LLM gateway governance | Medium | High |
| LangSmith | Agent ops/observability/deployment | Medium | High |
| GitHub | External system | Low | Very High |

---

# 145. Strategic ranking

## Most important to monitor

```text
1. Temporal
2. Restate
3. PydanticAI
4. LangGraph / LangSmith
5. DBOS
6. Inngest
7. OpenAI Agents SDK
8. Portkey
```

This ranking is based on **strategic overlap with the target architecture**, not company size or product quality.

---

# 146. Why Temporal is #1

Temporal is the strongest reference for :

```text
durable execution
worker recovery
long-running workflows
human interaction
production operations
```

and is actively moving into AI/coding-agent use cases.

---

# 147. Why Restate is #2

Restate explicitly targets :

```text
durable agent runtime
```

and directly argues that checkpointing alone is insufficient.

This overlaps strongly with PyAgentsKit’s reliability narrative.

---

# 148. Why PydanticAI is #3

PydanticAI is moving toward an architecture where the framework can plug into several durable engines.

This creates a powerful compositional alternative.

---

# 149. Why LangGraph is #4

LangGraph already offers :

```text
durable checkpoints
HITL interrupts
resume
state graph
```

and has a major surrounding platform.

---

# 150. Why DBOS/Inngest matter

They optimize developer experience around durable execution.

If PyAgentsKit’s DX is much heavier without clearly stronger guarantees, adoption becomes difficult.

---

# 151. Strategic positioning formula

```text
PyAgentsKit
=
Agent Reliability Semantics
+
Effect Safety
+
Governance
+
Distributed Ownership
+
Runtime/Connector Interoperability
```

not :

```text
Agent Framework
+
Workflow Engine
+
Observability Platform
+
Everything Else
```

---

# 152. Recommended category name

Best candidate :

```text
Agent Reliability Layer
```

Alternative :

```text
Agent Execution Safety Layer
```

Alternative enterprise-oriented :

```text
Agent Reliability & Governance Runtime
```

---

# 153. Category claim requirements

To legitimately claim “Agent Reliability Layer”, PyAgentsKit must prove :

```text
runtime neutrality
effect safety
crash recovery
distributed takeover
governance
reconciliation
audit
```

---

# 154. Competitive differentiation in one table

| Question | Typical agent framework | Durable engine | PyAgentsKit target |
|---|---|---|---|
| How does agent reason? | Core concern | Not primary | Delegated |
| How is workflow resumed? | Checkpoint/runtime | Core concern | Governed/abstracted |
| May this action execute? | Tool policy/HITL | Application concern | Core Governance |
| What if external result is unknown? | App-specific | Activity/workflow-specific | First-class Effect |
| May stale worker act? | Usually external | Engine internal | Explicit ownership/fencing |
| How do we verify external reality? | App-specific | App-specific | ReconciliationPort |
| Which runtime is used? | Framework-specific | Any app | Runtime Adapter |
| Is approval still valid after takeover? | App-specific | Workflow-specific | Core semantic |
| Is audit same as tracing? | Often mixed | history/trace | Explicitly separate |

---

# 155. Key decision

Do not try to beat Temporal at Temporal.

Do not try to beat LangGraph at LangGraph.

Do not try to beat Portkey at gateway operations.

Instead :

```text
make all of them safer to use for real-world agent actions
```

where technically possible.

---

# 156. Competitive strategy statement

> **PyAgentsKit should become the layer an engineering team adds when agent actions are too consequential to be governed only by framework checkpoints, workflow retries, or tool callbacks.**

---

# 157. Source notes

The competitive landscape above was checked against current public documentation available on **21 October 2026**.

Primary official sources consulted include:

## Temporal

- https://temporal.io/pages/durable-ai-agent-bundle
- https://temporal.io/blog/announcing-openai-agents-sdk-integration
- https://temporal.io/blog/temporal-sandbox-orchestration-harness-the-missing-layer-for-running-agents
- https://temporal.io/blog/the-immortal-life-of-pi-running-the-pi-coding-agent-on-temporal
- https://learn.temporal.io/tutorials/ai/durable-ai-agent/

## LangChain / LangGraph / LangSmith

- https://docs.langchain.com/oss/javascript/langgraph/thinking-in-langgraph
- https://docs.langchain.com/oss/python/learn
- https://docs.langchain.com/oss/javascript/deepagents/overview
- https://docs.langchain.com/langsmith/data-plane
- https://docs.langchain.com/langsmith/evaluation-types

## PydanticAI

- https://pydantic.dev/docs/ai/capabilities/durable_execution/overview/
- https://pydantic.dev/docs/ai/tools-toolsets/deferred-tools/
- https://pydantic.dev/docs/ai/api/pydantic-ai/tools/

## OpenAI Agents SDK

- https://openai.github.io/openai-agents-python/human_in_the_loop/
- https://openai.github.io/openai-agents-js/guides/human-in-the-loop/

## AutoGen

- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/human-in-the-loop.html
- https://microsoft.github.io/autogen/stable/user-guide/agentchat-user-guide/tutorial/state.html

## DBOS

- https://docs.dbos.dev/python/tutorials/workflow-tutorial
- https://docs.dbos.dev/ai/ai-quickstart
- https://docs.dbos.dev/integrations/openai-agents
- https://docs.dbos.dev/python/examples/agent-inbox

## Restate

- https://restate.dev/blog
- https://restate.dev/blog/why-checkpointing-is-not-production-grade-durable-execution
- https://restate.dev/blog/dealing-with-versioning-in-long-running-agents
- https://restate.dev/blog/tags/AI

## Inngest

- https://www.inngest.com/docs/patterns/durable
- https://www.inngest.com/docs/durable-execution/durable-agents
- https://www.inngest.com/docs/durable-execution/concepts
- https://www.inngest.com/blog/ai-in-production-report-2026

## Portkey / Prisma AIRS AI Gateway

- https://portkey.ai/features/agents
- https://portkey.ai/blog/agent-gateway/
- https://portkey.ai/features/ai-agent-new

---

# 158. Final Assessment

Le marché confirme que le problème identifié par PyAgentsKit est réel :

```text
agents are long-running distributed systems
```

Mais il confirme aussi que :

```text
durability
checkpointing
HITL
observability
```

se banalisent rapidement.

La stratégie PyAgentsKit doit donc se concentrer sur une couche plus précise :

```text
ACTION REQUEST
      │
      ▼
AUTHORITY
      │
      ▼
APPROVAL
      │
      ▼
OWNERSHIP / FENCING
      │
      ▼
DURABLE EFFECT INTENT
      │
      ▼
EXTERNAL EXECUTION
      │
      ▼
OUTCOME?
  ┌───┼────┐
  ▼   ▼    ▼
SUCCESS FAILURE UNKNOWN
              │
              ▼
        RECONCILIATION
```

C’est cette chaîne complète — et surtout son indépendance vis-à-vis du runtime agentique — qui constitue la meilleure hypothèse de différenciation durable pour PyAgentsKit.

> **PyAgentsKit ne doit pas chercher à être le système qui fait réfléchir l’agent. Il doit chercher à être le système qui sait, avec le plus de précision possible, quand cet agent peut agir, ce qui s’est réellement passé, qui avait l’autorité, et comment reprendre sans répéter une conséquence irréversible.**
