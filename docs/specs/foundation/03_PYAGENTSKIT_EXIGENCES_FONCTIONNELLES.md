# PyAgentsKit — Exigences fonctionnelles

**Document :** `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`  
**Version :** 1.0  
**Date :** 19 octobre 2026  
**Statut :** Spécification fonctionnelle  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/02_PYAGENTSKIT_PARTIES_PRENANTES_ET_CAS_D_USAGE.md`

---

# 1. Objet du document

Ce document spécifie les **exigences fonctionnelles** de PyAgentsKit.

Il transforme les besoins, cas d’usage et invariants précédemment identifiés en exigences :

- numérotées ;
- traçables ;
- testables ;
- priorisées ;
- indépendantes autant que possible de l’implémentation.

Le document ne décrit pas encore les choix techniques détaillés.

Il définit **ce que PyAgentsKit doit faire**.

---

# 2. Convention de lecture

Chaque exigence suit le format :

```text
ID
Titre
Priorité
Description
Règles fonctionnelles
Critères d’acceptation
Traçabilité
```

Priorités utilisées :

```text
MUST    indispensable au cœur produit
SHOULD  fortement recommandé
COULD   extension utile
WON'T   explicitement hors périmètre immédiat
```

---

# 3. Domaines fonctionnels

Les exigences sont regroupées en 15 domaines :

```text
A. Runtime adapters
B. Runs
C. Sessions
D. Memory
E. Checkpoints & durable execution
F. Approvals
G. Effects
H. Idempotency & reconciliation
I. Distributed coordination
J. Artifacts
K. Audit & event model
L. Observability & inspection
M. External integrations
N. Coding-agent integration
O. Administration & lifecycle
```

---

# 4. A — Runtime adapters

## FR-001 — Support d’un contrat de runtime agentique

**Priorité : MUST**

### Description

PyAgentsKit doit exposer un contrat standard permettant d’intégrer un runtime agentique externe.

### Règles fonctionnelles

Le runtime doit pouvoir au minimum être :

- démarré ;
- repris ;
- arrêté ;
- interrogé sur son état ;
- observé via des événements ou résultats.

### Critères d’acceptation

- un runtime custom peut être branché sans modifier le cœur ;
- un adapter peut être remplacé par un autre ;
- les stores PyAgentsKit restent inchangés.

### Traçabilité

- UC13
- UC19

---

## FR-002 — Neutralité vis-à-vis du fournisseur LLM

**Priorité : MUST**

PyAgentsKit ne doit pas imposer de fournisseur LLM particulier.

Critère :

```text
OpenAI != dépendance obligatoire
Anthropic != dépendance obligatoire
Google != dépendance obligatoire
```

---

## FR-003 — Neutralité vis-à-vis du framework agentique

**Priorité : MUST**

PyAgentsKit doit pouvoir fonctionner au-dessus de runtimes tels que :

- LangGraph ;
- PydanticAI ;
- OpenAI Agents SDK ;
- Claude Agent SDK ;
- AutoGen ;
- CrewAI ;
- runtime propriétaire.

---

## FR-004 — Support des coding-agent runtimes

**Priorité : COULD**

PyAgentsKit doit permettre l’ajout d’adapters pour :

- Codex ;
- Claude Code ;
- OpenCode ;
- Antigravity CLI (`agy`) ;
- autres coding agents.

Le cœur ne doit cependant dépendre d’aucun de ces produits.

### Traçabilité

- UC14
- UC15
- UC16
- UC17
- UC18

---

# 5. B — Runs

## FR-010 — Création d’un run

**Priorité : MUST**

Le système doit permettre de créer un run avec :

- identifiant stable ;
- runtime associé ;
- statut initial ;
- metadata ;
- timestamps.

---

## FR-011 — Cycle de vie explicite d’un run

**Priorité : MUST**

Un run doit disposer d’un état explicite.

États minimaux :

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

---

## FR-012 — Transition contrôlée des états

**Priorité : MUST**

Toute transition d’état doit respecter une machine à états définie.

Exemple :

```text
CREATED
  ↓
READY
  ↓
RUNNING
  ↓
WAITING
  ↓
RUNNING
  ↓
SUCCEEDED
```

Une transition incohérente doit être rejetée.

---

## FR-013 — Persistance du run

**Priorité : MUST**

L’état d’un run doit survivre :

- au redémarrage du processus ;
- au changement de worker ;
- à une indisponibilité temporaire du runtime agentique.

---

## FR-014 — Annulation d’un run

**Priorité : MUST**

Le système doit permettre l’annulation explicite d’un run.

La politique d’annulation doit distinguer :

- arrêt immédiat ;
- arrêt après checkpoint ;
- arrêt après fin de l’effet courant.

---

## FR-015 — Consultation d’un run

**Priorité : MUST**

Il doit être possible de consulter :

- statut ;
- runtime ;
- owner ;
- lease ;
- dernier checkpoint ;
- approval en attente ;
- dernier effet ;
- dernière erreur.

### Traçabilité

- UC11

---

# 6. C — Sessions

## FR-020 — Création d’une session

**Priorité : MUST**

Une session doit pouvoir regrouper plusieurs runs.

---

## FR-021 — Persistance d’une session

**Priorité : MUST**

Une session doit survivre aux redémarrages.

---

## FR-022 — Association session / runs

**Priorité : MUST**

Un run doit pouvoir référencer une session.

Une session doit permettre de retrouver ses runs.

---

## FR-023 — Metadata de session

**Priorité : SHOULD**

Une session doit pouvoir contenir des metadata extensibles.

---

# 7. D — Memory

## FR-030 — Séparation memory / session / run

**Priorité : MUST**

PyAgentsKit doit distinguer :

```text
Run State
Session State
Long-term Memory
```

---

## FR-031 — Lecture de mémoire

**Priorité : MUST**

Un agent doit pouvoir consulter sa mémoire persistante.

---

## FR-032 — Écriture de mémoire

**Priorité : MUST**

Un agent doit pouvoir enrichir ou modifier sa mémoire.

---

## FR-033 — Versionnement ou contrôle concurrent de mémoire

**Priorité : SHOULD**

Le framework doit pouvoir éviter les écrasements concurrents.

---

# 8. E — Checkpoints & durable execution

## FR-040 — Création de checkpoint

**Priorité : MUST**

Un run doit pouvoir produire un checkpoint durable.

---

## FR-041 — Reprise depuis checkpoint

**Priorité : MUST**

Un run doit pouvoir être repris depuis le dernier checkpoint valide.

### Traçabilité

- UC02

---

## FR-042 — Reprise par un autre worker

**Priorité : MUST**

Un nouveau worker doit pouvoir reprendre un run interrompu.

---

## FR-043 — Suspension longue

**Priorité : MUST**

Un run doit pouvoir rester suspendu pendant :

- plusieurs minutes ;
- plusieurs heures ;
- plusieurs jours ;

sans processus actif permanent.

### Traçabilité

- UC20

---

## FR-044 — Reprise contrôlée après incident

**Priorité : MUST**

La reprise doit revalider :

- état du run ;
- ownership ;
- lease ;
- effets en cours ;
- approvals.

---

## FR-045 — Absence de replay implicite

**Priorité : MUST**

La reprise d’un run ne doit pas provoquer automatiquement le replay d’un effet déjà terminé ou ambigu.

---

# 9. F — Approvals

## FR-050 — Création d’une approval

**Priorité : MUST**

Le système doit permettre de créer une demande d’approbation.

Champs minimaux :

```text
approval_id
run_id
action
requested_by
requested_at
status
```

---

## FR-051 — Suspension sur approval

**Priorité : MUST**

Un run doit pouvoir passer en état `WAITING`.

---

## FR-052 — Décision d’approval

**Priorité : MUST**

Une approval doit pouvoir être :

```text
APPROVED
REJECTED
EXPIRED
CANCELLED
```

---

## FR-053 — Reprise après approval

**Priorité : MUST**

Le run doit pouvoir reprendre après validation.

### Traçabilité

- UC03
- UC18

---

## FR-054 — Identité du décideur

**Priorité : MUST**

L’identité de l’auteur de la décision doit être conservée.

---

## FR-055 — Expiration d’une approval

**Priorité : SHOULD**

Une approval peut avoir une durée de validité.

---

## FR-056 — Approval policy

**Priorité : SHOULD**

Il doit être possible d’associer une policy à certaines catégories d’actions.

Exemple :

```text
git push        → optional
merge PR        → required
publish package → required
prod deploy     → required
```

---

# 10. G — Effects

## FR-060 — Modèle d’effet de premier niveau

**Priorité : MUST**

Un effet externe doit être représenté explicitement.

---

## FR-061 — Identifiant stable d’effet

**Priorité : MUST**

Chaque effet doit disposer d’un identifiant stable.

---

## FR-062 — État d’un effet

**Priorité : MUST**

États minimaux :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

## FR-063 — Persistance de l’intention d’effet

**Priorité : MUST**

L’intention doit être persistée avant l’exécution de l’effet lorsque le scénario l’exige.

---

## FR-064 — Persistance du résultat d’effet

**Priorité : MUST**

Le résultat doit être persisté après confirmation.

---

## FR-065 — Référence externe

**Priorité : MUST**

Un effet doit pouvoir conserver une référence externe :

```text
invoice_id
payment_id
commit_sha
pull_request_id
deployment_id
package_version
```

---

## FR-066 — Classification de criticité

**Priorité : SHOULD**

Un effet doit pouvoir être classé selon son niveau de risque.

Exemple :

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 11. H — Idempotency & reconciliation

## FR-070 — Clé d’idempotence

**Priorité : MUST**

Un effet doit pouvoir disposer d’une clé d’idempotence stable.

---

## FR-071 — Déduplication

**Priorité : MUST**

Une même clé ne doit pas entraîner la création de plusieurs effets lorsque le backend permet l’idempotence.

### Traçabilité

- UC04

---

## FR-072 — Détection d’un effet déjà réussi

**Priorité : MUST**

Lors d’une reprise, PyAgentsKit doit détecter les effets déjà terminés.

### Traçabilité

- UC06

---

## FR-073 — Détection d’un résultat ambigu

**Priorité : MUST**

Un timeout ou une interruption après lancement d’un effet doit pouvoir placer celui-ci en état `UNKNOWN`.

---

## FR-074 — Reconciliation

**Priorité : MUST**

Un `EffectReconciler` doit permettre de déterminer l’état réel externe.

### Traçabilité

- UC05
- UC15

---

## FR-075 — Revue manuelle

**Priorité : SHOULD**

Lorsque l’état ne peut pas être réconcilié automatiquement, le système doit pouvoir demander une intervention humaine.

---

# 12. I — Distributed coordination

## FR-080 — Acquisition de lease

**Priorité : MUST**

Un worker doit acquérir un lease avant d’exécuter un run protégé.

---

## FR-081 — Exclusivité de lease

**Priorité : MUST**

Un seul worker doit détenir le lease valide d’un run donné.

### Traçabilité

- UC07

---

## FR-082 — Renouvellement de lease

**Priorité : MUST**

Un worker doit pouvoir renouveler son lease.

---

## FR-083 — Expiration de lease

**Priorité : MUST**

Un lease doit expirer après une durée définie.

---

## FR-084 — Takeover

**Priorité : MUST**

Un autre worker doit pouvoir reprendre un run après expiration du lease.

### Traçabilité

- UC08

---

## FR-085 — Fencing token

**Priorité : MUST**

Chaque nouvelle ownership doit recevoir un token monotone.

---

## FR-086 — Rejet d’un token obsolète

**Priorité : MUST**

Une ressource protégée doit pouvoir rejeter un ancien token.

### Traçabilité

- UC09

---

## FR-087 — Détection de perte de lease

**Priorité : MUST**

Un worker doit cesser les nouvelles opérations protégées dès qu’il détecte la perte du lease.

---

## FR-088 — Coordination de ressource logique

**Priorité : SHOULD**

PyAgentsKit doit permettre de protéger des ressources autres qu’un run :

```text
repository
branch
workspace
worktree
external job
```

### Traçabilité

- UC16

---

# 13. J — Artifacts

## FR-090 — Création d’un artifact

**Priorité : MUST**

Un run doit pouvoir référencer un artifact.

---

## FR-091 — Metadata d’artifact

**Priorité : MUST**

Un artifact doit contenir au minimum :

- id ;
- run id ;
- type ;
- emplacement ;
- taille éventuelle ;
- checksum éventuel.

---

## FR-092 — Stockage externe

**Priorité : MUST**

Les binaires peuvent être stockés dans un backend objet.

---

## FR-093 — Récupération

**Priorité : MUST**

Un artifact doit pouvoir être retrouvé depuis le run.

---

# 14. K — Audit & event model

## FR-100 — Événements structurés

**Priorité : MUST**

PyAgentsKit doit émettre des événements métier structurés.

Exemples :

```text
run.created
run.started
run.waiting
run.resumed
run.failed
run.completed

effect.started
effect.succeeded
effect.failed
effect.unknown

approval.requested
approval.approved
approval.rejected

lease.acquired
lease.renewed
lease.lost
lease.taken_over
```

---

## FR-101 — Journal d’audit

**Priorité : MUST**

Les événements critiques doivent pouvoir être persistés.

---

## FR-102 — Reconstruction chronologique

**Priorité : MUST**

L’historique doit permettre de reconstituer le déroulement d’un run.

### Traçabilité

- UC12

---

## FR-103 — Corrélation

**Priorité : MUST**

Les événements doivent pouvoir être corrélés à :

- run ;
- session ;
- worker ;
- effect ;
- approval ;
- lease.

---

# 15. L — Observability & inspection

## FR-110 — Logs structurés

**Priorité : MUST**

Les opérations importantes doivent produire des logs structurés.

---

## FR-111 — Métriques

**Priorité : MUST**

Le runtime doit produire au minimum des métriques pour :

```text
runs
failures
approvals
effects
leases
takeovers
reconciliations
```

---

## FR-112 — Tracing

**Priorité : SHOULD**

Les runs et effects doivent pouvoir être intégrés à un système de tracing distribué.

---

## FR-113 — Health endpoint

**Priorité : MUST**

Le worker doit exposer son état de santé.

---

## FR-114 — Readiness endpoint

**Priorité : MUST**

Le worker doit indiquer s’il peut accepter de nouveaux runs.

---

## FR-115 — Inspection opérationnelle

**Priorité : MUST**

Un exploitant doit pouvoir inspecter l’état d’un run.

### Traçabilité

- UC11

---

# 16. M — External integrations

## FR-120 — Déclenchement externe

**Priorité : SHOULD**

Un système externe doit pouvoir créer un run.

### Traçabilité

- UC23

---

## FR-121 — Publication d’événements

**Priorité : SHOULD**

Les événements PyAgentsKit doivent pouvoir être consommés par :

- webhook ;
- bus ;
- UI ;
- monitoring ;
- audit.

### Traçabilité

- UC25

---

## FR-122 — Scheduler externe

**Priorité : SHOULD**

PyAgentsKit doit accepter des déclenchements planifiés venant d’un scheduler externe.

### Traçabilité

- UC24

---

## FR-123 — Connecteurs métier

**Priorité : SHOULD**

Les tools doivent pouvoir appeler :

- APIs ;
- DB ;
- ERP ;
- CRM ;
- cloud ;
- Git ;
- CI/CD ;
- notifications.

---

# 17. N — Coding-agent integration

## FR-130 — Exécution contrôlée d’un coding agent

**Priorité : COULD**

Un coding agent doit pouvoir être encapsulé dans un run PyAgentsKit.

---

## FR-131 — Actions de coding agent comme effets

**Priorité : COULD**

Certaines actions doivent pouvoir être traitées comme effets protégés :

```text
git push
create PR
merge PR
publish package
deploy
terraform apply
```

---

## FR-132 — Approval avant action sensible

**Priorité : COULD**

Le framework doit pouvoir demander une approval avant :

- merge ;
- publication ;
- prod deployment ;
- infra apply.

---

## FR-133 — Reconciliation Git

**Priorité : COULD**

Après crash ou timeout, un adapter doit pouvoir vérifier :

- commit présent ?
- branche poussée ?
- PR créée ?
- merge effectué ?

### Traçabilité

- UC15

---

## FR-134 — Coordination repository / branch / worktree

**Priorité : COULD**

Le framework doit permettre de coordonner plusieurs agents sur une ressource de code logique.

### Traçabilité

- UC16

---

# 18. O — Administration & lifecycle

## FR-140 — Graceful shutdown

**Priorité : MUST**

Lors d’un arrêt propre, le worker doit :

1. arrêter les nouvelles admissions ;
2. traiter ou checkpoint les runs actifs ;
3. gérer les leases ;
4. terminer proprement.

### Traçabilité

- UC10

---

## FR-141 — Safe mode en cas de perte du store

**Priorité : MUST**

Si le runtime ne peut plus :

- persister ;
- renouveler un lease ;
- vérifier l’état d’un effet ;

il doit empêcher les nouveaux effets protégés.

### Traçabilité

- UC21

---

## FR-142 — Reprise après restauration

**Priorité : MUST**

Après restauration de l’infrastructure, les runs éligibles doivent pouvoir être repris.

### Traçabilité

- UC22

---

## FR-143 — Migration de stores

**Priorité : SHOULD**

Le framework doit permettre l’évolution des schémas de persistence.

---

## FR-144 — Diagnostics

**Priorité : SHOULD**

Le système doit exposer des informations permettant de diagnostiquer :

- stores ;
- workers ;
- leases ;
- versions ;
- migrations.

---

# 19. Exigences transverses

## FR-150 — Identifiants stables

**Priorité : MUST**

Toutes les entités importantes doivent disposer d’identifiants stables.

---

## FR-151 — Horodatage

**Priorité : MUST**

Les changements critiques doivent être horodatés.

---

## FR-152 — Metadata extensibles

**Priorité : SHOULD**

Les entités principales doivent pouvoir porter des metadata sans modifier le schéma fonctionnel de base.

---

## FR-153 — Corrélation globale

**Priorité : MUST**

Les interactions doivent pouvoir être suivies via des IDs de corrélation.

---

# 20. Invariants fonctionnels

Les invariants suivants sont obligatoires.

## INV-F01

Un run ne peut pas être dans deux états terminaux simultanément.

## INV-F02

Un effet `SUCCEEDED` ne doit pas être rejoué implicitement.

## INV-F03

Un effet `UNKNOWN` ne doit pas être considéré comme `FAILED`.

## INV-F04

Un worker sans lease valide ne doit pas produire d’effet protégé.

## INV-F05

Un token obsolète ne doit pas être accepté par une ressource protégée.

## INV-F06

Une approval requise doit bloquer la progression tant qu’aucune décision valide n’existe.

## INV-F07

Un changement de propriétaire doit être auditable.

## INV-F08

La reprise ne doit pas supprimer l’historique précédent.

## INV-F09

Le changement de runtime adapter ne doit pas nécessiter de remplacer la persistence principale.

## INV-F10

Les coding-agent adapters ne doivent pas imposer leurs concepts au cœur PyAgentsKit.

---

# 21. Traçabilité exigences ↔ cas d’usage

| Exigence | Cas d’usage |
|---|---|
| FR-001 | UC13, UC19 |
| FR-010 à FR-015 | UC01, UC11 |
| FR-040 à FR-045 | UC02, UC20, UC22 |
| FR-050 à FR-056 | UC03, UC18 |
| FR-060 à FR-066 | UC04, UC05, UC06 |
| FR-070 à FR-075 | UC04, UC05, UC06, UC15 |
| FR-080 à FR-088 | UC07, UC08, UC09, UC16 |
| FR-090 à FR-093 | UC01, UC17 |
| FR-100 à FR-103 | UC12, UC25 |
| FR-110 à FR-115 | UC11, UC12 |
| FR-120 à FR-123 | UC23, UC24, UC25 |
| FR-130 à FR-134 | UC14, UC15, UC16, UC17, UC18 |
| FR-140 à FR-144 | UC10, UC21, UC22 |

---

# 22. MVP fonctionnel minimal

Le MVP différenciant de PyAgentsKit doit couvrir au minimum :

```text
Run lifecycle
RunStore
SessionStore
ApprovalStore
EffectStore
LeaseStore

DurableRunner
Checkpoints
Resume
ProtectedEffect
Idempotency
Reconciliation

Lease acquisition
Lease renewal
Lease loss
Takeover
Fencing

Audit events
Inspection
Health
Readiness
```

---

# 23. Fonctionnalités différées

Peuvent être livrées après le cœur :

```text
Temporal backend
DBOS backend
advanced policy engine
admin UI
dashboard
advanced coding-agent adapters
marketplace d’adapters
advanced quota management
```

---

# 24. Hors périmètre fonctionnel

PyAgentsKit ne doit pas fournir directement :

```text
prompt management
model routing
fine-tuning
RAG engine
vector database
generic BPM engine
generic scheduler
IDE agentique
code generation engine
patch generation engine
repository semantic indexing
chat frontend
```

---

# 25. Definition of Done fonctionnelle

Le périmètre fonctionnel est considéré comme couvert lorsque :

1. un run peut être créé, exécuté, suspendu et terminé ;
2. l’état survit à un redémarrage ;
3. un run peut être repris par un autre worker ;
4. une approval peut bloquer puis relancer un run ;
5. un effet externe peut être enregistré avant/après exécution ;
6. un effet ambigu peut être réconcilié ;
7. un effet réussi n’est pas rejoué implicitement ;
8. plusieurs workers peuvent fonctionner sans split-brain ;
9. un fencing token obsolète peut être rejeté ;
10. l’exécution est inspectable et auditable ;
11. un runtime agentique peut être remplacé via adapter ;
12. l’infrastructure peut fonctionner avec PostgreSQL réel ;
13. les coding-agent adapters peuvent être ajoutés sans modifier le core.

---

# 26. Résumé

Les exigences fonctionnelles confirment que la valeur de PyAgentsKit ne repose pas sur la création de l’agent lui-même.

Elle repose sur les garanties autour de son exécution :

```text
RUN LIFECYCLE
STATE
DURABILITY
APPROVALS
EFFECT SAFETY
RECONCILIATION
LEASES
FENCING
AUDIT
OBSERVABILITY
RUNTIME ADAPTERS
```

Le document suivant devra formaliser les contraintes de qualité et de production :

```text
../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md
```
