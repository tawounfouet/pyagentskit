# PyAgentsKit — Définition du besoin

**Document :** `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`  
**Version :** 1.2  
**Date :** 19 octobre 2026  
**Statut :** Cadrage fonctionnel et architectural  
**Projet :** PyAgentsKit  
**Révision 1.2 :** extension du besoin aux runtimes d’agents IA pilotables programmatiquement, y compris les coding agents (Codex, Claude Code, OpenCode, Antigravity CLI/`agy`, etc.), sans modifier le rôle central de PyAgentsKit comme reliability layer.  

---

# 1. Objet du document

Ce document formalise le besoin auquel répond **PyAgentsKit**.

L’objectif n’est pas de définir PyAgentsKit comme un énième framework permettant de créer des agents IA, d’appeler un LLM ou d’enchaîner des outils.

Le besoin cible est plus précis :

> **Fournir une couche Python de fiabilité, indépendante des frameworks agentiques, permettant d’exécuter des agents IA avec état de manière durable, contrôlée, traçable et exploitable en production.**

PyAgentsKit se positionne donc comme une **Agent Reliability Layer** située entre :

- les frameworks ou runtimes agentiques ;
- les outils et systèmes métier ;
- les mécanismes de persistance ;
- l’infrastructure d’exécution distribuée ;
- les dispositifs d’observabilité et de contrôle humain.

---

# 2. Contexte

Les frameworks modernes d’agents IA permettent déjà de :

- appeler des modèles de langage ;
- orchestrer des outils ;
- créer des workflows ;
- gérer des conversations ;
- construire des systèmes multi-agents ;
- introduire de la mémoire ;
- gérer certains mécanismes de reprise ou d’interruption.

Le problème apparaît lorsque l’agent ne se limite plus à produire une réponse textuelle, mais doit effectuer des actions réelles sur des systèmes externes.

Exemples :

- envoyer un email ;
- créer une facture ;
- effectuer un paiement ;
- modifier un dossier dans un ERP ;
- déclencher un workflow métier ;
- créer un ticket ;
- appeler une API externe ;
- supprimer ou modifier une ressource ;
- attendre une validation humaine ;
- reprendre une exécution plusieurs heures ou plusieurs jours plus tard.

À partir de ce moment, la question principale n’est plus uniquement :

> « L’agent est-il capable de décider quoi faire ? »

mais :

> **« Peut-on garantir que son exécution reste correcte malgré les pannes, retries, crashs, reprises, exécutions concurrentes et interventions humaines ? »**

---

# 3. Problème à résoudre

Un agent IA utilisé en production est un système distribué avec état.

Il peut être confronté à plusieurs classes de problèmes.

## 3.1 Perte de processus

Un worker peut s’arrêter après avoir effectué une action externe mais avant d’avoir persisté son résultat.

Exemple :

```text
1. l’agent crée une facture dans l’ERP ;
2. l’ERP confirme la création ;
3. le worker crash avant d’enregistrer le succès ;
4. un nouveau worker reprend l’exécution ;
5. il ignore si la facture existe déjà.
```

Un retry naïf peut créer un doublon.

---

## 3.2 Répétition involontaire d’un effet métier

Certains appels sont sans conséquence lorsqu’ils sont répétés.

D’autres ne le sont pas.

Exemples d’effets non triviaux :

- transfert d’argent ;
- création de commande ;
- émission d’une facture ;
- envoi d’un email ;
- suppression de données ;
- validation d’un workflow ;
- appel d’une API facturée ;
- déclenchement d’un processus externe.

La reprise d’un agent ne doit donc jamais impliquer implicitement la répétition d’un effet métier.

---

## 3.3 Exécution concurrente

Deux workers peuvent considérer qu’ils possèdent le même run.

Cela peut provoquer :

- duplication d’actions ;
- corruption d’état ;
- split-brain ;
- écritures concurrentes ;
- comportements non déterministes.

---

## 3.4 Reprise après interruption

Un run peut être suspendu en attente :

- d’un humain ;
- d’un événement externe ;
- d’un délai ;
- d’une donnée manquante ;
- du rétablissement d’un service.

La reprise doit être explicite, cohérente et déterministe.

---

## 3.5 Persistance fragmentée

Un agent dispose généralement de plusieurs formes d’état :

- état de run ;
- session ;
- mémoire ;
- approvals ;
- checkpoints ;
- artefacts ;
- historique des effets ;
- ownership distribué ;
- journal d’audit.

Ces informations doivent pouvoir être stockées de manière persistante et remplacées par différents backends.

---

## 3.6 Manque de visibilité opérationnelle

En production, il doit être possible de répondre à des questions telles que :

- quel worker possède ce run ?
- quel effet métier a été exécuté ?
- avec quel fencing token ?
- pourquoi le run est-il suspendu ?
- qui a approuvé l’action ?
- combien de reprises ont eu lieu ?
- quel worker a perdu son lease ?
- quels appels externes ont échoué ?
- quel est l’état de santé du runtime ?

---

# 4. Besoin métier

Le besoin consiste à disposer d’un runtime agentique capable d’offrir des **garanties d’exécution explicites**.

PyAgentsKit doit permettre de passer de :

```text
Agent qui fonctionne lorsque tout va bien
```

à :

```text
Agent exploitable malgré les pannes,
les interruptions,
les reprises,
les validations humaines
et l’exécution distribuée.
```

---

# 5. Vision produit

PyAgentsKit doit devenir :

> **Une couche Python de fiabilité pour agents IA avec état, indépendante du modèle LLM et du framework agentique utilisé.**

La bibliothèque doit pouvoir fournir ses garanties à tout **runtime d’agent IA pilotable programmatiquement**, sans imposer un moteur agentique unique.

Les runtimes cibles se répartissent en trois familles :

```text
General-purpose agent runtimes
──────────────────────────────
LangGraph
PydanticAI
OpenAI Agents SDK
Claude Agent SDK
AutoGen
CrewAI

Coding-agent runtimes
─────────────────────
Codex
Claude Code
OpenCode
Antigravity CLI (agy)
autres coding agents

Custom runtimes
───────────────
runtime propriétaire
application Python custom
future agent runtimes
```

Ces produits sont des **runtimes compatibles ou intégrables**, pas des dépendances obligatoires de PyAgentsKit.

Le besoin cible n’est donc pas limité aux frameworks agentiques généralistes : PyAgentsKit doit pouvoir fiabiliser tout runtime agentique exposant une surface de contrôle exploitable (SDK, CLI, API, protocole ou adapter).

### Clarification — runtimes généralistes et coding agents

Dans ce document, **Claude Agent SDK** désigne le SDK agentique d’Anthropic permettant de construire et d’exécuter des agents avec outils, sessions, permissions, hooks, intégrations MCP et sous-agents.

Il doit être distingué du simple SDK client de l’API Anthropic (`anthropic`), qui sert principalement à appeler les modèles Claude et ne constitue pas, à lui seul, un runtime agentique.

Dans l’architecture PyAgentsKit, **Claude Agent SDK est donc considéré au même niveau conceptuel que OpenAI Agents SDK, LangGraph, PydanticAI, AutoGen ou CrewAI**.

Les outils spécialisés de développement logiciel tels que **Codex, Claude Code, OpenCode ou Antigravity CLI (`agy`)** constituent une seconde famille : les **coding-agent runtimes**.

PyAgentsKit ne cherche pas à reproduire leur logique de génération ou de modification de code. Il doit pouvoir leur ajouter des garanties transversales telles que :

- persistance du run ;
- reprise après panne ;
- approvals ;
- protection des effets ;
- audit ;
- coordination distribuée ;
- fencing ;
- observabilité.

La distinction structurante devient donc :

```text
agent logic / coding capability
            ↓
     external runtime
            ↓
        PyAgentsKit
            ↓
 reliability guarantees
```

---

# 6. Positionnement

## 6.1 Ce que PyAgentsKit est

PyAgentsKit est une infrastructure de fiabilité pour des runtimes d’agents IA pilotables programmatiquement, qu’ils soient généralistes, spécialisés ou propriétaires, couvrant notamment :

- l’exécution durable ;
- la gestion du cycle de vie des runs ;
- la persistance d’état ;
- les validations humaines ;
- les effets métier protégés ;
- la coordination distribuée ;
- la reprise après incident ;
- l’observabilité ;
- l’auditabilité.

---

## 6.2 Ce que PyAgentsKit n’est pas

PyAgentsKit ne doit pas devenir :

- un wrapper générique de LLM ;
- un framework de prompting ;
- un moteur RAG générique ;
- un moteur de chat multi-agent ;
- un clone de LangGraph ;
- un clone de CrewAI ;
- un coding agent ;
- un moteur de génération de code ;
- un éditeur de fichiers agentique ;
- un moteur de génération de patchs ;
- un IDE agentique ;
- un moteur d’analyse sémantique de repository ;
- un remplaçant de Codex, Claude Code, OpenCode ou Antigravity CLI (`agy`) ;
- un moteur de workflow généraliste ;
- un remplacement de Temporal ;
- une plateforme générique de tracing ;
- une plateforme complète de scheduling.

Ces briques peuvent être intégrées lorsqu’elles existent déjà.

---

# 7. Utilisateurs cibles

## 7.1 Développeur d’agents IA

Il souhaite disposer de garanties d’exécution sans implémenter lui-même :

- checkpointing ;
- persistence ;
- approvals ;
- idempotence ;
- leases ;
- fencing ;
- reprise ;
- audit.

---

## 7.2 Data / AI Engineer

Il souhaite brancher l’agent sur :

- bases de données ;
- API métier ;
- services cloud ;
- pipelines ;
- systèmes internes.

Il doit pouvoir contrôler la façon dont les effets sont exécutés.

---

## 7.3 Platform Engineer / SRE

Il souhaite :

- plusieurs workers ;
- des health checks ;
- de la readiness ;
- des métriques ;
- du tracing ;
- des logs ;
- des runbooks ;
- des garanties de reprise.

---

## 7.4 Responsable métier / Compliance

Il souhaite disposer de :

- validations humaines ;
- historique d’exécution ;
- audit trail ;
- séparation entre décision et effet ;
- traçabilité des actions.

---

# 8. Concepts fondamentaux

## 8.1 Agent

Composant responsable de la prise de décision.

PyAgentsKit ne doit pas imposer son implémentation.

---

## 8.2 Run

Instance d’exécution d’un agent.

Un run possède notamment :

- un identifiant ;
- un état ;
- un propriétaire éventuel ;
- des checkpoints ;
- des effets ;
- une timeline ;
- un statut.

---

## 8.3 Session

Contexte persistant pouvant regrouper plusieurs runs.

---

## 8.4 Memory

Informations conservées au-delà d’un run.

---

## 8.5 Tool

Capacité appelée par l’agent.

---

## 8.6 Effect

Conséquence externe produite par l’exécution d’un tool.

Exemples :

```text
send_email
create_invoice
transfer_money
update_erp
delete_resource
```

Un effet est différent d’un simple appel de fonction.

---

## 8.7 Approval

Décision humaine requise avant la poursuite du run.

---

## 8.8 Lease

Droit temporaire détenu par un worker sur un run.

---

## 8.9 Fencing Token

Jeton monotone permettant d’empêcher un ancien propriétaire du run de continuer à produire des effets.

---

# 9. Exigences fonctionnelles

## F01 — Création et gestion des runs

Le runtime doit permettre :

- création ;
- démarrage ;
- pause ;
- reprise ;
- succès ;
- échec ;
- annulation.

---

## F02 — Persistance de l’état

Le framework doit proposer des interfaces pour :

- `RunStore` ;
- `SessionStore` ;
- `MemoryStore` ;
- `ApprovalStore` ;
- `ArtifactStore` ;
- `LeaseStore`.

---

## F03 — Checkpointing

Une exécution doit pouvoir persister suffisamment d’état pour reprendre après interruption.

---

## F04 — Durable execution

Un run doit pouvoir survivre :

- au redémarrage du processus ;
- à la perte du worker ;
- à une suspension longue ;
- à une indisponibilité temporaire de l’infrastructure.

---

## F05 — Human-in-the-loop

Le runtime doit pouvoir :

- demander une validation ;
- suspendre le run ;
- conserver l’état ;
- accepter une décision ;
- reprendre l’exécution.

---

## F06 — Protected Effects

Chaque effet métier doit pouvoir être identifié par une clé stable.

Le framework doit permettre de connaître son état :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

## F07 — Idempotence

PyAgentsKit doit permettre de protéger les opérations pouvant être répétées.

L’idempotence ne doit cependant pas être supposée par défaut.

---

## F08 — Reconciliation

Lorsqu’un effet externe a été lancé mais que son résultat n’est pas connu, le runtime doit permettre une phase de réconciliation.

Exemple :

```text
API appelée
↓
timeout réseau
↓
résultat externe inconnu
↓
ne pas retry automatiquement
↓
interroger le système externe
↓
déterminer l’état réel
```

---

## F09 — Exécution distribuée

Plusieurs workers doivent pouvoir consommer des runs.

Un seul worker doit disposer du droit valide de progression pour un run donné.

---

## F10 — Lease lifecycle

Le runtime doit gérer :

- acquisition ;
- renouvellement ;
- expiration ;
- perte ;
- conflit ;
- takeover.

---

## F11 — Fencing

Les opérations protégées doivent pouvoir vérifier que le worker détient encore un fencing token valide.

---

## F12 — Graceful shutdown

Lors d’un arrêt propre :

- les nouvelles admissions doivent pouvoir être bloquées ;
- les runs actifs doivent être gérés explicitement ;
- les leases doivent être renouvelés ou libérés de manière contrôlée.

---

## F13 — Artifacts

Le framework doit permettre d’attacher aux runs :

- fichiers ;
- documents ;
- exports ;
- payloads ;
- résultats volumineux.

---

## F14 — Audit Trail

Le runtime doit conserver les événements importants :

- création du run ;
- changements d’état ;
- prise de lease ;
- perte de lease ;
- changement de propriétaire ;
- approvals ;
- exécution d’effets ;
- reprise ;
- erreur ;
- takeover.

---

# 10. Exigences non fonctionnelles

## NF01 — Framework neutrality

Le cœur de PyAgentsKit ne doit dépendre d’aucun framework agentique particulier.

---

## NF02 — Provider neutrality

Le runtime ne doit dépendre d’aucun fournisseur LLM.

---

## NF03 — Storage abstraction

Les stores doivent être définis par interfaces ou protocols.

Exemple :

```python
class RunStore(Protocol):
    ...

class SessionStore(Protocol):
    ...

class LeaseStore(Protocol):
    ...

class EffectStore(Protocol):
    ...
```

---

## NF04 — Production readiness

Les composants de production doivent pouvoir fonctionner avec :

- PostgreSQL ;
- stockage objet ;
- plusieurs processus ;
- plusieurs machines.

---

## NF05 — Observability

Le framework doit exposer :

- logs structurés ;
- métriques ;
- traces ;
- health ;
- readiness.

---

## NF06 — Deterministic recovery

Une reprise doit éviter les comportements implicites ou ambigus.

---

## NF07 — Explicit failure semantics

Les états d’échec doivent être représentés explicitement.

---

## NF08 — Backward compatibility

Les évolutions du runtime doivent préserver les contrats publics autant que possible.

---

## NF09 — Testability

Chaque mécanisme critique doit être testable localement.

---

## NF10 — Minimal infrastructure coupling

Le cœur ne doit pas imposer PostgreSQL, S3, Temporal ou Kubernetes.

Ces composants doivent être des implémentations ou adapters.

---

# 11. Principes d’architecture

## P01 — Ports and adapters

Le cœur expose des contrats.

Les implémentations concrètes sont externes au domaine.

```text
               PyAgentsKit Core
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Postgres      S3        adapters
```

---

## P02 — Effects are first-class citizens

Les effets métier doivent être modélisés comme des entités du runtime.

Ils ne doivent pas être réduits à des appels de fonctions.

---

## P03 — No implicit business-effect replay

Principe critique :

> **Une reprise d’exécution ne doit jamais répéter implicitement un effet métier.**

---

## P04 — State before convenience

La cohérence de l’état prime sur la simplicité syntaxique.

---

## P05 — Explicit ownership

Dans un environnement distribué, l’ownership d’un run doit être explicite.

---

## P06 — Fencing over trust

Un worker expiré ne doit pas simplement « savoir » qu’il doit s’arrêter.

Les systèmes protégés doivent pouvoir refuser ses écritures.

---

## P07 — Observability by design

Logs, traces, métriques et audit ne doivent pas être ajoutés après coup.

---

# 12. Architecture cible

```text
                        Agent Runtimes
                             │
          ┌──────────────────┴──────────────────┐
          │                                     │
          ▼                                     ▼
 General-purpose runtimes                Coding-agent runtimes

 LangGraph                               Codex
 PydanticAI                             Claude Code
 OpenAI Agents SDK                     OpenCode
 Claude Agent SDK                      Antigravity CLI (agy)
 AutoGen                               autres coding agents
 CrewAI
          │                                     │
          └──────────────────┬──────────────────┘
                             │
                    Custom runtimes
                             │
                             ▼
                  AgentRuntimeAdapter
                             │
                             ▼
                    ┌──────────────────┐
                    │   PyAgentsKit    │
                    │ Reliability Core │
                    └────────┬─────────┘
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
       ▼                  ▼                  ▼
 Durable State       Protected Effects    Approvals
       │                  │                  │
       ├───── Runs        ├──── idem key     │
       ├───── Session     ├──── fencing      │
       ├───── Memory      └──── reconcile    │
       └───── Checkpoint
                          │
                          ▼
                Distributed Runtime
                          │
              Leases / Heartbeats
              Fencing / Takeover
                          │
                          ▼
                Infrastructure Layer
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
          PostgreSQL     S3/Blob    Telemetry
```

---

# 13. Cas d’usage de référence

## UC01 — Agent de traitement de facture

```text
Receive invoice
      ↓
Analyze
      ↓
Check ERP
      ↓
Ask approval
      ↓
Create accounting entry
      ↓
Send notification
      ↓
Archive artifact
```

Le runtime doit survivre à une panne entre chaque étape.

---

## UC02 — Worker perdu après effet externe

```text
Worker A
   ↓
Create invoice
   ↓
ERP = success
   ↓
worker crash
```

Le worker B ne doit pas recréer automatiquement la facture.

Il doit :

```text
resume
↓
detect uncertain effect state
↓
reconcile
↓
continue
```

---

## UC03 — Split-brain

```text
Worker A owns token 41
        ↓
network pause
        ↓
lease expires

Worker B owns token 42
        ↓
continues execution

Worker A comes back
        ↓
attempts protected effect
        ↓
REJECT token 41
```

---


## UC04 — Coding agent autonome ou semi-autonome

Un coding agent peut être exécuté sous le contrôle de PyAgentsKit :

```text
Issue / Task
    ↓
Coding Agent
    ↓
Inspect repository
    ↓
Modify files
    ↓
Run tests
    ↓
Create commit
    ↓
Approval / Policy
    ↓
git push
    ↓
Create PR
    ↓
CI validation
    ↓
Human approval
    ↓
Merge / Publish / Deploy
```

Les actions peuvent être classées selon leur criticité :

```text
read repository       → lecture
run tests             → généralement reproductible
edit workspace        → effet local
git commit            → effet persistant
git push              → effet externe
create PR             → effet externe
merge PR              → effet sensible
publish package       → effet critique
deploy production     → effet critique
terraform apply       → effet critique
```

PyAgentsKit doit permettre d’appliquer à ces actions les mêmes garanties que pour les autres agents :

- ownership explicite ;
- approvals ;
- audit ;
- effect protection ;
- reprise après panne ;
- non-répétition implicite ;
- reconciliation si l’état externe est ambigu.

Le runtime de code reste responsable de la génération, compréhension et modification du code ; PyAgentsKit reste responsable des garanties d’exécution.

---

# 14. Différenciation recherchée

La différenciation de PyAgentsKit ne repose pas sur la création d’un nouveau DSL agentique.

Elle repose sur la combinaison suivante :

```text
Framework-neutral
+
Stateful
+
Durable
+
Human-controlled
+
Effect-aware
+
Distributed
+
Auditable
```

Les éléments stratégiquement différenciants sont :

1. effets métier comme concept de premier niveau ;
2. absence de replay implicite des effets ;
3. réconciliation des effets ambigus ;
4. propagation du fencing token jusqu’aux ressources protégées ;
5. séparation agent / runtime de fiabilité ;
6. indépendance vis-à-vis du framework agentique.

---

# 15. Critères de succès

PyAgentsKit répond au besoin si les scénarios suivants fonctionnent.

## S01

Un run survive au redémarrage complet du worker.

## S02

Un run peut être repris par un autre worker.

## S03

Un effet métier déjà confirmé n’est pas rejoué.

## S04

Un effet dont le résultat est inconnu déclenche une réconciliation plutôt qu’un retry aveugle.

## S05

Un ancien worker ne peut pas écrire avec un fencing token expiré.

## S06

Une validation humaine peut suspendre un run pendant plusieurs heures ou jours.

## S07

L’état complet du run peut être inspecté.

## S08

Chaque changement critique laisse une trace d’audit.

## S09

Les mécanismes fonctionnent avec plusieurs workers réels et PostgreSQL.

## S10

Un utilisateur peut remplacer le moteur agentique sans remplacer la couche de fiabilité.

---

# 16. Non-objectifs

Les sujets suivants sont explicitement hors du cœur de PyAgentsKit :

- benchmark de modèles ;
- gestion de prompts ;
- fine-tuning ;
- vector database générique ;
- RAG généraliste ;
- interface utilisateur de chatbot ;
- marketplace de tools ;
- orchestration multi-agent complète ;
- génération autonome de code ;
- édition de repository ;
- génération de patchs ;
- indexation sémantique de code ;
- IDE ou terminal agentique ;
- remplacement de Codex, Claude Code, OpenCode ou Antigravity CLI (`agy`) ;
- scheduler généraliste ;
- workflow BPM générique ;
- remplacement de Kubernetes ;
- remplacement de PostgreSQL ;
- remplacement de Temporal.

---

# 17. Stratégie d’intégration

PyAgentsKit doit préférer l’intégration à la réinvention.

Exemples :

```text
OpenTelemetry → tracing
PostgreSQL → durable state
S3 / Blob → artifacts
Kubernetes → deployment
Temporal / DBOS → backends possibles de durable execution
```

La valeur de PyAgentsKit réside dans :

```text
contracts
+
semantics
+
agent-specific reliability
```

et non dans la reconstruction de toute l’infrastructure sous-jacente.

---

# 18. Orientation de roadmap

Après la qualification opérationnelle de l’exécution distribuée, la roadmap doit progressivement renforcer le positionnement de PyAgentsKit comme **framework-neutral reliability layer**.

Un jalon logique est :

```text
PyAgentsKit 1.7.0
Framework-Neutral Agent Reliability Layer
```

Il pourrait introduire :

- `AgentRuntimeAdapter` ;
- `DurableExecutionBackend` ;
- `EffectStore` ;
- `EffectReconciler` ;
- `ProtectedTool` ;
- `FencingContext` ;
- adapter LangGraph ;
- adapter PydanticAI ;
- adapter OpenAI Agents SDK ;
- adapter Claude Agent SDK ;
- adapter AutoGen ;
- adapter CrewAI ;
- adapter runtime custom.

Les **coding-agent adapters** constituent une extension stratégique ultérieure du même contrat, sans être une dépendance obligatoire du cœur :

- adapter Codex ;
- adapter Claude Code ;
- adapter OpenCode ;
- adapter Antigravity CLI (`agy`) ;
- adapters futurs pour d’autres coding-agent runtimes.

---

# 19. Proposition de valeur

## Version courte

> **PyAgentsKit rend les agents IA exploitables en production.**

---

## Version produit

> **PyAgentsKit is a framework-neutral Python reliability layer for programmatically controllable AI agent runtimes, providing durable state, protected effects, human approvals, distributed coordination, recoverable execution and operational observability.**

---

## Version française

> **PyAgentsKit est une couche Python de fiabilité indépendante des frameworks destinée aux runtimes d’agents IA pilotables programmatiquement, fournissant état durable, effets protégés, validations humaines, coordination distribuée, reprise et observabilité opérationnelle.**

---

# 20. Résumé

PyAgentsKit ne doit pas chercher à répondre à la question :

> « Comment construire un agent IA ? »

De nombreux frameworks répondent déjà à cette question.

Il doit répondre à une autre :

> **« Comment garantir qu’un agent IA ayant des responsabilités réelles continue à fonctionner correctement lorsqu’il est confronté aux réalités de la production ? »**

Ces réalités incluent :

- crashs ;
- retries ;
- effets externes ;
- duplication ;
- concurrence ;
- split-brain ;
- validation humaine ;
- persistance ;
- reprise ;
- audit ;
- observabilité.

Qu’il s’agisse d’un agent généraliste, d’un coding agent ou d’un runtime propriétaire, le cœur de PyAgentsKit doit donc rester centré sur :

```text
DURABILITY
STATE
EFFECT SAFETY
HUMAN CONTROL
DISTRIBUTED OWNERSHIP
OBSERVABILITY
RECOVERY
```

C’est cette spécialisation qui justifie l’existence du projet au sein d’un écosystème déjà riche en frameworks agentiques.
