# PyAgentsKit — Analyse du besoin

**Document :** `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`  
**Version :** 1.1  
**Date :** 19 octobre 2026  
**Statut :** Analyse fonctionnelle et stratégique  
**Projet :** PyAgentsKit  
**Révision 1.1 :** extension de l’analyse aux runtimes d’agents IA pilotables programmatiquement, notamment les coding agents (Codex, Claude Code, OpenCode, Antigravity CLI/`agy`, etc.), et introduction du contrat `AgentRuntimeAdapter` comme point d’extension architectural.  
**Document source :** `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`

---

# 1. Objet du document

Ce document analyse le besoin à l’origine de **PyAgentsKit** afin de déterminer :

- les problèmes réellement à résoudre ;
- les acteurs concernés ;
- les attentes explicites et implicites ;
- les exigences prioritaires ;
- les contraintes ;
- les alternatives existantes ;
- les risques de sur-construction ;
- les critères de différenciation ;
- les limites du périmètre ;
- les capacités minimales nécessaires pour justifier le produit.

L’objectif est de passer de :

> « Nous voulons un framework Python pour agents IA »

à une formulation plus rigoureuse :

> **Nous voulons une couche de fiabilité indépendante des frameworks, capable de rendre l’exécution de runtimes d’agents IA pilotables programmatiquement — généralistes, coding agents ou propriétaires — durable, contrôlée, observable et sûre en environnement distribué.**

---

# 2. Reformulation du besoin

Le besoin initial pourrait sembler être :

> Construire un framework d’agents IA en Python.

Cette formulation est trop large et insuffisamment différenciante.

Le besoin réel est plutôt :

> **Permettre à des agents IA ayant des responsabilités réelles d’être exécutés avec des garanties comparables à celles attendues d’un système métier de production.**

Cela implique que PyAgentsKit doit traiter des problèmes qui dépassent largement :

- le prompt ;
- le modèle ;
- l’appel de tools ;
- la conversation.

Le besoin porte principalement sur :

```text
état
+
durabilité
+
ownership
+
effets externes
+
reprise
+
validation humaine
+
audit
+
observabilité
```

---

# 3. Problématique générale

Un agent IA classique est souvent développé comme une séquence :

```text
Input
  ↓
LLM
  ↓
Decision
  ↓
Tool
  ↓
Output
```

Cette architecture fonctionne correctement tant que :

- le processus ne tombe pas ;
- un seul worker existe ;
- les appels externes sont fiables ;
- les effets peuvent être répétés ;
- aucune intervention humaine n’est nécessaire ;
- l’exécution est courte ;
- aucun audit n’est attendu.

Ces hypothèses deviennent rapidement fausses en production.

L’agent devient alors un système distribué avec état.

Le vrai problème peut donc être formulé ainsi :

> **Comment exécuter un agent non déterministe dans un environnement distribué tout en conservant des garanties fortes sur son état et sur les effets qu’il produit ?**

---

# 4. Analyse des acteurs

## 4.1 Développeur d’agents

### Besoin

Développer la logique métier et agentique sans réimplémenter en permanence :

- persistence ;
- checkpoints ;
- idempotence ;
- reprise ;
- approvals ;
- leases ;
- audit ;
- instrumentation.

### Attente principale

Disposer d’API simples mais s’appuyant sur des mécanismes robustes.

### Risque

Une abstraction trop complexe annulerait l’intérêt du framework.

---

## 4.2 AI Engineer / Data Engineer

### Besoin

Connecter les agents aux systèmes réels :

- API ;
- bases ;
- ERP ;
- CRM ;
- stockage ;
- pipelines ;
- services internes.

### Attente principale

Pouvoir distinguer :

```text
simple computation
```

de :

```text
external business effect
```

### Risque

Un tool mal modélisé peut provoquer :

- doublons ;
- incohérences ;
- effets non réversibles.

---

#
## 4.3 Développeur / exploitant de coding agents

### Besoin

Utiliser un agent de code tel que :

- Codex ;
- Claude Code ;
- OpenCode ;
- Antigravity CLI (`agy`) ;
- autre runtime de développement logiciel ;

dans des scénarios allant au-delà de l’assistance interactive locale.

Exemples :

- correction automatique de bugs ;
- maintenance de repository ;
- génération de pull requests ;
- migrations ;
- exécution de tests ;
- publication de packages ;
- déploiement ;
- opérations DevOps.

### Attente principale

Pouvoir distinguer les actions sans effet critique des actions persistantes ou sensibles :

```text
read repository
run tests
edit workspace
git commit
git push
create PR
merge PR
publish package
deploy production
terraform apply
```

### Risque

Traiter toutes ces opérations comme de simples appels de tools peut provoquer :

- duplication ;
- concurrence sur le même workspace ;
- push ou publication répétés ;
- déploiements non contrôlés ;
- reprise incorrecte après crash.

### Réponse attendue

PyAgentsKit doit pouvoir envelopper ces runtimes via un contrat générique, sans réimplémenter leurs capacités de génération de code.

---

# 4.4 Platform Engineer

### Besoin

Déployer le runtime avec :

- plusieurs workers ;
- autoscaling ;
- PostgreSQL ;
- stockage objet ;
- orchestrateurs de conteneurs.

### Attente principale

Le système doit avoir un comportement explicite en cas de :

- crash ;
- restart ;
- réseau dégradé ;
- worker zombie ;
- failover.

---

## 4.5 SRE / Exploitant

### Besoin

Répondre rapidement à :

- pourquoi ce run est bloqué ?
- qui le possède ?
- que s’est-il passé ?
- peut-on le reprendre ?
- a-t-il produit un effet externe ?
- y a-t-il risque de duplication ?

### Attente principale

Observabilité et diagnostic.

---

## 4.6 Responsable métier

### Besoin

Conserver le contrôle humain sur les actions sensibles.

### Attente principale

Possibilité de :

- valider ;
- refuser ;
- suspendre ;
- demander une modification ;
- tracer la décision.

---

## 4.7 Compliance / Audit

### Besoin

Reconstruire l’historique d’une exécution.

### Attente principale

Traçabilité :

```text
qui ?
quoi ?
quand ?
pourquoi ?
avec quelle version ?
avec quel état ?
```

---

# 5. Analyse des problèmes

# 5.1 Problème P1 — État volatil

## Description

L’état conservé uniquement en mémoire est perdu lors du crash du processus.

## Impact

- perte de progression ;
- reprise impossible ;
- duplication ;
- expérience incohérente.

## Priorité

**Critique**

## Réponse attendue

Stores persistants + checkpoints.

---

# 5.2 Problème P2 — Retry naïf

## Description

Une erreur technique ne signifie pas nécessairement que l’action métier n’a pas eu lieu.

Exemple :

```text
POST /payments
↓
serveur réalise le paiement
↓
timeout réseau
↓
client considère l’appel en erreur
```

## Impact

Un retry peut créer un second paiement.

## Priorité

**Critique**

## Réponse attendue

- clés d’idempotence ;
- état des effets ;
- reconciliation ;
- politique de retry explicite.

---

# 5.3 Problème P3 — Exécution concurrente

## Description

Plusieurs workers peuvent tenter de traiter le même run.

## Impact

- doubles écritures ;
- corruption ;
- résultats incohérents.

## Priorité

**Critique**

## Réponse attendue

Lease + ownership explicite.

---

# 5.4 Problème P4 — Worker obsolète

## Description

Un worker peut perdre son lease sans s’en rendre compte immédiatement.

## Impact

Il peut continuer à produire des effets alors qu’un autre worker a repris le run.

## Priorité

**Critique**

## Réponse attendue

Fencing token propagé jusqu’aux écritures protégées.

---

# 5.5 Problème P5 — Suspension humaine

## Description

Certaines décisions ne peuvent pas être totalement automatisées.

## Impact

Sans modèle explicite :

- polling artisanal ;
- état perdu ;
- logique spécifique par projet.

## Priorité

**Élevée**

## Réponse attendue

Approval lifecycle persistant.

---

# 5.6 Problème P6 — Manque d’audit

## Description

Les logs seuls ne permettent pas toujours de reconstruire précisément l’état métier d’un run.

## Impact

- debugging lent ;
- faible confiance ;
- difficulté réglementaire.

## Priorité

**Élevée**

## Réponse attendue

Audit events structurés.

---

# 5.7 Problème P7 — Couplage au framework agentique

## Description

Une application peut devenir dépendante :

- d’un modèle ;
- d’un framework ;
- d’un graph DSL ;
- d’un runtime spécifique.

## Impact

Migration difficile.

## Priorité

**Élevée**

## Réponse attendue

Adapter layer indépendante.

---


# 5.8 Problème P8 — Coding agents capables de produire des effets persistants

## Description

Les coding agents modernes peuvent dépasser la simple génération de code et agir sur des environnements réels :

```text
workspace
repository
git remote
CI/CD
package registry
cloud
infrastructure
```

Un agent peut par exemple :

- modifier des fichiers ;
- créer un commit ;
- pousser une branche ;
- ouvrir une pull request ;
- déclencher une CI ;
- publier un package ;
- déployer ;
- appliquer une modification d’infrastructure.

## Impact

Ces opérations deviennent des **effets métier ou techniques réels**.

Elles nécessitent donc :

- ownership ;
- policy ;
- approval ;
- idempotency ;
- reconciliation ;
- audit.

## Priorité

**Élevée comme extension stratégique**, mais non bloquante pour le cœur initial.

## Réponse attendue

Un contrat `AgentRuntimeAdapter` générique permettant d’intégrer les coding agents sans introduire leurs concepts spécifiques dans le cœur de PyAgentsKit.

---

# 6. Besoins fonctionnels analysés

# 6.1 Cycle de vie des runs

Le besoin n’est pas uniquement d’exécuter une fonction.

Il faut modéliser explicitement :

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

Une machine à états doit empêcher les transitions incohérentes.

---

# 6.2 Sessions

Une session doit pouvoir :

- survivre à plusieurs runs ;
- porter du contexte ;
- être restaurée ;
- être indépendante du worker.

Le besoin est donc un `SessionStore` durable.

---

# 6.3 Memory

La mémoire doit être séparée du simple état du run.

Cela permet :

```text
Run state != Session state != Long-term memory
```

Cette séparation évite de transformer un store unique en structure difficile à maintenir.

---

# 6.4 Approvals

Une validation doit être une ressource métier persistante.

Elle doit contenir au minimum :

- `approval_id` ;
- `run_id` ;
- demande ;
- décision ;
- auteur ;
- timestamps ;
- statut.

---

# 6.5 Artifacts

Les artefacts volumineux ne doivent pas nécessairement être stockés dans la base principale.

Le besoin implique une séparation :

```text
metadata → database
binary payload → blob/object storage
```

---

# 6.6 Effects

L’effet doit devenir un concept de premier niveau.

Modèle minimal :

```text
Effect
├── effect_id
├── run_id
├── type
├── idempotency_key
├── status
├── input_hash
├── external_reference
├── fencing_token
├── created_at
├── started_at
├── completed_at
└── reconciliation_state
```

---

# 6.7 Reconciliation

La réconciliation est nécessaire lorsqu’on se trouve dans l’état :

```text
action probablement lancée
+
résultat inconnu
```

Le framework ne peut pas décider génériquement si l’effet a réellement réussi.

Il doit donc fournir :

```python
EffectReconciler
```

plutôt qu’un comportement automatique opaque.

---


# 6.8 AgentRuntimeAdapter

Le besoin d’intégration ne doit pas être implémenté par une collection de dépendances directes au cœur.

PyAgentsKit doit définir un contrat générique de runtime :

```python
class AgentRuntimeAdapter(Protocol):

    async def start(...): ...
    async def resume(...): ...
    async def cancel(...): ...
    async def events(...): ...
```

Ce contrat doit permettre de brancher plusieurs familles :

```text
General-purpose runtimes
────────────────────────
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

Custom runtimes
───────────────
runtime propriétaire
application Python custom
```

Le contrat doit rester centré sur le cycle de vie et les garanties d’exécution.

Il ne doit pas imposer au cœur :

```text
repository
diff
patch
IDE
terminal
prompt spécifique au code
```

Ces notions peuvent appartenir à des adapters spécialisés.

---

# 7. Analyse des exigences non fonctionnelles

# 7.1 Fiabilité

Le framework doit privilégier :

```text
correctness > convenience
```

Une API plus explicite est acceptable si elle évite une duplication d’effet métier.

---

# 7.2 Disponibilité

La défaillance d’un worker ne doit pas rendre le run définitivement inutilisable.

---

# 7.3 Scalabilité

L’architecture doit accepter :

```text
1 worker
→ N workers
```

sans changer le modèle conceptuel.

---

# 7.4 Portabilité

Le cœur doit pouvoir fonctionner sans dépendance obligatoire à :

- Kubernetes ;
- AWS ;
- Azure ;
- Temporal ;
- LangGraph ;
- OpenAI.

---

# 7.5 Observabilité

Les métriques minimales doivent couvrir :

- runs actifs ;
- runs en attente ;
- failures ;
- retries ;
- lease acquisitions ;
- lease renewals ;
- lease losses ;
- conflicts ;
- takeovers ;
- effects ;
- reconciliations ;
- approval latency.

---

# 7.6 Sécurité

Le besoin inclut indirectement :

- limitation des tools ;
- séparation des responsabilités ;
- validation avant effets sensibles ;
- conservation de l’identité de l’appelant ;
- secrets hors état durable.

---

# 8. Analyse des alternatives

Plusieurs familles d’outils existent déjà.

## 8.1 Frameworks et runtimes agentiques

### Runtimes généralistes

Exemples :

```text
LangGraph
CrewAI
AutoGen
OpenAI Agents SDK
Claude Agent SDK
PydanticAI
```

Ils répondent principalement à :

```text
comment représenter, piloter ou orchestrer un agent ?
```

### Coding-agent runtimes

Exemples :

```text
Codex
Claude Code
OpenCode
Antigravity CLI (agy)
```

Ils répondent principalement à :

```text
comment permettre à un agent de comprendre,
modifier, tester et faire évoluer du code ?
```

PyAgentsKit doit répondre à une autre question :

```text
comment garantir leur exécution,
leurs effets,
leur reprise
et leur contrôle en production ?
```

Ces outils ne doivent donc pas être considérés comme des concurrents directs de PyAgentsKit, mais comme des runtimes que la reliability layer peut encadrer.

---

## 8.2 Workflow engines

Exemples :

```text
Temporal
DBOS
Prefect
Airflow
Restate
```

Ils proposent déjà des mécanismes avancés de durability.

Il serait contre-productif de recréer toutes leurs capacités.

PyAgentsKit doit pouvoir utiliser ces moteurs comme backends ou inspirations sans devenir lui-même un orchestrateur universel.

---

## 8.3 Infrastructure distribuée

Exemples de briques existantes :

```text
PostgreSQL
Redis
Kubernetes
OpenTelemetry
S3
```

PyAgentsKit doit les intégrer au lieu de les remplacer.

---

# 9. Analyse Build vs Integrate

Le projet doit appliquer la règle :

> **Build semantics, integrate infrastructure.**

## À construire

- contrats agent-specific ;
- `AgentRuntimeAdapter` ;
- modèle Run ;
- modèle Approval ;
- modèle Effect ;
- lifecycle ;
- reconciliation ;
- protected tools ;
- fencing-aware semantics ;
- adapters de runtimes généralistes ;
- adapters de coding agents ;
- audit domain events.

## À intégrer

- PostgreSQL ;
- object storage ;
- tracing ;
- metrics ;
- orchestration de conteneurs ;
- moteurs de durable execution externes ;
- runtimes agentiques existants ;
- coding agents existants.

Le principe devient :

> **Build semantics, integrate runtimes and infrastructure.**

---

# 10. Besoin différenciant

Le principal élément différenciant potentiel est le modèle :

```text
Agent decision
      ↓
Tool request
      ↓
Effect contract
      ↓
Safety checks
      ↓
Ownership / fencing
      ↓
Execution
      ↓
Persist outcome
```

Le framework ne doit pas considérer :

```python
tool()
```

comme un simple appel Python.

La même logique doit s’appliquer à un coding agent.

Exemple :

```text
git push
merge PR
publish package
deploy
terraform apply
```

ne doivent pas être traités comme de simples commandes techniques, mais comme des **effets externes** pouvant nécessiter protection, approval, idempotence, fencing et audit.

Il doit pouvoir considérer cet appel comme :

```text
une intention d’effet métier
```

soumise à des règles de sécurité et de reprise.

---

# 11. Priorisation MoSCoW

## MUST

- durable runs ;
- persistent stores ;
- session persistence ;
- approvals ;
- protected effects ;
- idempotency ;
- reconciliation ;
- leases ;
- fencing ;
- multi-worker recovery ;
- audit trail ;
- metrics ;
- tracing ;
- health/readiness.

---

## SHOULD

- object storage adapters ;
- `AgentRuntimeAdapter` ;
- framework/runtime adapters ;
- graceful shutdown ;
- migration tooling ;
- CLI diagnostics ;
- run inspection ;
- replay-safe events.

---

## COULD

- adapters Codex ;
- adapters Claude Code ;
- adapters OpenCode ;
- adapter Antigravity CLI (`agy`) ;
- Temporal backend ;
- DBOS backend ;
- Azure Blob backend ;
- dashboard ;
- admin UI ;
- advanced policy engine ;
- quotas.

---

## WON'T — cœur immédiat

- prompt management ;
- RAG engine ;
- vector database ;
- model router ;
- multi-agent DSL ;
- moteur de génération de code ;
- édition de repository ;
- génération de patchs ;
- IDE agentique ;
- terminal agentique ;
- remplacement de Codex, Claude Code, OpenCode ou `agy` ;
- scheduler généraliste ;
- chat frontend ;
- Kubernetes operator.

---

# 12. Contraintes

# 12.1 Contraintes techniques

- Python ;
- APIs stables ;
- async compatible ;
- tests multi-processus ;
- stockage durable ;
- tolérance aux crashs ;
- compatibilité PostgreSQL réelle.

---

# 12.2 Contraintes architecturales

Le framework doit éviter le couplage entre :

```text
agent logic
business effects
durability
storage
infrastructure
```

---

# 12.3 Contraintes produit

Une nouvelle bibliothèque n’a de valeur que si elle réduit réellement :

- la complexité ;
- le risque ;
- le code infrastructurel dupliqué.

---

# 13. Risques produit

# R1 — Construire un énième framework agentique

## Probabilité

Élevée si le périmètre dérive.

## Réponse

Interdire au cœur :

- orchestration LLM propriétaire ;
- DSL graph généraliste.

---

# R2 — Recréer Temporal

## Probabilité

Moyenne.

## Réponse

Définir `DurableExecutionBackend` plutôt que reconstruire toutes les primitives.

---

# R3 — API trop abstraite

## Impact

Les développeurs ne comprennent plus les garanties réelles.

## Réponse

Conserver une sémantique explicite.

---

# R4 — Fausses garanties d’exactly-once

## Impact

Très élevé.

L’exactly-once absolu est souvent impossible avec des systèmes externes.

## Réponse

Parler plutôt de :

```text
at-most-once protected effect
idempotency
deduplication
reconciliation
```

selon le cas.

---

# R5 — Fencing incomplet

## Description

Un fencing token stocké uniquement dans le runtime ne suffit pas.

## Réponse

Le token doit être vérifié au niveau des ressources critiques lorsque cela est possible.

---

# R6 — Explosion du nombre de stores

## Réponse

Normaliser les contrats et mutualiser l’infrastructure sans mélanger les responsabilités.

---


# R7 — Dériver vers un framework de coding agents

## Description

L’intégration de Codex, Claude Code, OpenCode ou `agy` pourrait conduire à ajouter progressivement dans PyAgentsKit :

- logique d’édition de fichiers ;
- génération de patchs ;
- analyse de repository ;
- terminal interactif ;
- prompts spécialisés ;
- gestion d’IDE.

## Impact

Le projet perdrait son positionnement de reliability layer et entrerait en concurrence avec des produits spécialisés.

## Réponse

PyAgentsKit doit fournir :

```text
control
reliability
state
effects
approvals
recovery
audit
```

et déléguer :

```text
code understanding
code generation
patching
repository intelligence
```

au runtime de coding agent.

---

# 14. Hypothèses

Le besoin repose sur plusieurs hypothèses.

## H1

Les agents seront utilisés pour produire des effets externes.

## H2

Certaines exécutions seront longues.

## H3

Plusieurs workers seront nécessaires.

## H4

Les erreurs réseau sont normales.

## H5

Les services externes peuvent répondre de manière ambiguë.

## H6

L’humain restera nécessaire pour certaines décisions.

## H7

Les frameworks agentiques continueront d’évoluer rapidement.

La neutralité du runtime protège contre cette évolution.

## H8

Les coding agents continueront à gagner en autonomie et à produire davantage d’effets persistants sur :

- repositories ;
- pipelines CI/CD ;
- registries ;
- environnements cloud ;
- infrastructures.

La reliability layer doit donc pouvoir les encadrer sans devenir elle-même un coding agent.

---

# 15. Invariants métier à préserver

Les invariants suivants doivent guider toute l’architecture.

## I1

Un run possède un identifiant stable.

## I2

Un changement d’état critique est persisté.

## I3

Un worker doit prouver qu’il possède le run.

## I4

Un worker obsolète ne doit plus pouvoir produire d’effet protégé.

## I5

Un effet réussi ne doit pas être rejoué implicitement.

## I6

Un effet ambigu doit être réconcilié.

## I7

Une approval suspend la progression de manière persistante.

## I8

Toute reprise doit être auditable.

---

# 16. Scénarios critiques

# SC01 — Crash avant l’effet

```text
persist checkpoint
↓
crash
↓
new worker
↓
resume
↓
execute effect
```

Résultat attendu : fonctionnement normal.

---

# SC02 — Crash après effet confirmé

```text
execute effect
↓
external success
↓
persist effect success
↓
crash
↓
resume
```

Résultat attendu :

```text
reuse previous outcome
```

---

# SC03 — Crash après effet mais avant confirmation locale

```text
execute effect
↓
external success
↓
worker crash
↓
local status = STARTED
```

Résultat attendu :

```text
RECONCILIATION_REQUIRED
```

et non retry automatique.

---

# SC04 — Split brain

```text
Worker A token 10
↓
pause

Worker B token 11
↓
takes ownership

Worker A returns
```

Résultat attendu :

```text
token 10 rejected
```

---

# SC05 — Human approval

```text
run
↓
sensitive action
↓
approval requested
↓
WAITING
↓
human approves
↓
resume
```

---

# SC06 — PostgreSQL indisponible

Le runtime doit éviter de poursuivre aveuglément une exécution dont il ne peut plus garantir :

- ownership ;
- persistence ;
- effect state.

---


# SC07 — Coding agent interrompu après un effet Git externe

```text
coding agent
↓
git push
↓
remote accepted
↓
worker crash
↓
local state uncertain
```

Résultat attendu :

```text
do not push blindly again
↓
inspect remote state
↓
reconcile
↓
continue or request approval
```

Ce scénario doit utiliser les mêmes primitives que les autres effets externes.

---

# SC08 — Plusieurs coding agents sur le même workspace ou repository

```text
Codex worker A
Claude Code worker B
OpenCode worker C
```

Résultat attendu :

- ownership explicite d’une ressource logique ;
- isolation par worktree/branch lorsque nécessaire ;
- protection contre les conflits d’exécution ;
- audit du propriétaire ;
- reprise contrôlée après perte du worker.

---

# 17. Analyse du MVP

Un MVP techniquement crédible ne peut pas être uniquement :

```text
Agent + tools + memory
```

Cela existe déjà.

Le minimum différenciant doit inclure :

```text
RunStore
SessionStore
ApprovalStore
EffectStore
LeaseStore

DurableRunner
ProtectedEffect
EffectReconciler

lease + fencing
audit events
```

Avec au moins un backend de production :

```text
PostgreSQL
```

Le MVP du cœur n’exige pas encore des adapters complets pour Codex, Claude Code, OpenCode ou `agy`.

En revanche, l’architecture doit déjà permettre leur ajout sans modifier les contrats centraux.

---

# 18. Definition of Done du besoin

Le besoin peut être considéré comme correctement couvert lorsque :

1. un run peut être interrompu et repris ;
2. un second worker peut reprendre le run ;
3. les états sont persistants ;
4. une approval survit à un restart ;
5. un effet déjà exécuté n’est pas répété automatiquement ;
6. un effet ambigu peut être réconcilié ;
7. un worker ayant perdu son lease est stoppé ;
8. un fencing token obsolète est rejeté ;
9. l’exécution est observable ;
10. la chronologie est auditable ;
11. le framework agentique utilisé peut être remplacé ;
12. l’infrastructure peut être déployée avec plusieurs workers.

---

# 19. Traçabilité besoins → capacités

| Besoin | Capacité PyAgentsKit |
|---|---|
| Reprise après panne | DurableRunner |
| État durable | RunStore / SessionStore |
| Validation humaine | ApprovalStore |
| Artefacts | ArtifactStore |
| Plusieurs workers | LeaseStore |
| Worker zombie | Fencing tokens |
| Effets non répétables | ProtectedEffect |
| Résultat ambigu | EffectReconciler |
| Diagnostic | metrics / traces / logs |
| Audit | Audit events |
| Portabilité | Protocols / adapters |
| Runtimes hétérogènes | AgentRuntimeAdapter |
| Coding agents | Coding-agent adapters + Protected Effects |

---

# 20. Questions architecturales ouvertes

Les points suivants devront être traités dans les documents d’architecture.

## Q1

Le `EffectStore` doit-il être séparé du `RunStore` ?

## Q2

Quel modèle de transition doit être utilisé pour les runs ?

## Q3

Comment associer fencing token et tools ?

## Q4

Comment représenter les effets composés ?

## Q5

Comment gérer un effet irréversible sans API de reconciliation ?

## Q6

Quelle granularité pour les checkpoints ?

## Q7

Quel niveau de compatibilité avec Temporal / DBOS ?

## Q8

Quels contrats minimaux imposer aux adapters agentiques ?

## Q9

Comment exposer le runtime en sync et async ?

## Q10

Quel modèle de transaction PostgreSQL utiliser pour lease + run state ?

---


## Q11

Le contrat `AgentRuntimeAdapter` doit-il exposer uniquement le lifecycle ou également les événements/outcomes du runtime ?

## Q12

Faut-il définir un sous-contrat `CodingAgentAdapter` ou conserver toutes les spécialisations hors du core ?

## Q13

Comment mapper de manière uniforme les événements de Codex, Claude Code, OpenCode et autres runtimes sur les événements PyAgentsKit ?

## Q14

Comment modéliser une ressource de coordination de type :

```text
repository
branch
worktree
workspace
```

sans transformer PyAgentsKit en outil Git ?

---

# 21. Opportunités

Le positionnement ouvre plusieurs possibilités.

## 21.1 Standardiser les effets agentiques

Créer une sémantique commune :

```text
decision
intent
effect
outcome
reconciliation
```

---

## 21.2 Découpler agents et runtime

Un agent devient interchangeable.

```text
LangGraph
   ↓
PyAgentsKit
```

peut devenir :

```text
PydanticAI
   ↓
PyAgentsKit
```

sans refaire la couche production.

---

## 21.3 Servir de couche commune aux autres Py*Kit

À terme, PyAgentsKit pourrait consommer ou s’intégrer avec :

```text
PyScheduleKit
PyWorkflowKit
PyIAMKit
PyMonitorKit
```

sans fusionner leurs responsabilités.

---


## 21.4 Encadrer les coding agents en production

PyAgentsKit peut devenir une couche de contrôle au-dessus de coding agents utilisés pour :

- maintenance autonome ;
- remédiation ;
- correction de bugs ;
- migrations ;
- génération de PR ;
- publication de packages ;
- opérations CI/CD ;
- déploiement.

Le bénéfice ne vient pas de la génération de code, mais de la capacité à appliquer :

```text
approval
effect safety
ownership
recovery
audit
```

aux actions produites par ces agents.

---

# 22. Positionnement recommandé

Le positionnement recommandé est :

> **PyAgentsKit — Reliability infrastructure for programmatically controllable AI agent runtimes.**

Et non :

> Python AI Agent Framework.

La phrase produit centrale peut être :

> **Use any agent runtime. Run it with production-grade guarantees.**

Version française :

> **Utilisez le runtime agentique de votre choix. Exécutez-le avec des garanties de production.**

---

# 23. Décision recommandée

Le besoin justifie la poursuite de PyAgentsKit à condition de respecter trois règles.

## Règle 1

Ne pas concurrencer directement les frameworks d’agents ni les coding agents.

## Règle 2

Ne pas recréer l’infrastructure générique déjà bien résolue.

## Règle 3

Concentrer la valeur sur :

```text
agent runtime semantics
+
safe effects
+
durability
+
distributed ownership
+
auditability
```

---

# 24. Conclusion

L’analyse confirme qu’il existe un besoin réel, mais qu’il ne se situe pas dans la création d’un nouveau framework de génération ou d’orchestration agentique.

Le besoin se situe à l’intersection de :

```text
AI Agent Runtimes
      +
Coding Agents
      +
Distributed Systems
      +
Durable Execution
      +
Business Effects
      +
Human Governance
```

PyAgentsKit est pertinent s’il devient la couche qui permet de transformer :

```text
une décision probabiliste d’agent
```

en :

```text
une exécution métier maîtrisée
```

avec des garanties explicites de :

- persistance ;
- ownership ;
- reprise ;
- non-duplication ;
- réconciliation ;
- contrôle humain ;
- audit ;
- observabilité.

La proposition de valeur n’est donc pas :

> « faire plus facilement des agents ».

Elle devient :

> **« permettre de leur confier des responsabilités réelles sans abandonner les garanties attendues d’un système de production. »**

Cette formulation couvre aussi bien les agents généralistes que les coding agents, dès lors qu’ils sont pilotables programmatiquement et qu’ils produisent des effets dont l’exécution doit être maîtrisée.
