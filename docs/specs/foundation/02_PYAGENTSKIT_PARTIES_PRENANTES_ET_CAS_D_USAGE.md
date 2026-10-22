# PyAgentsKit — Parties prenantes et cas d’usage

**Document :** `../foundation/02_PYAGENTSKIT_PARTIES_PRENANTES_ET_CAS_D_USAGE.md`  
**Version :** 1.0  
**Date :** 19 octobre 2026  
**Statut :** Cadrage fonctionnel détaillé  
**Projet :** PyAgentsKit  
**Documents de référence :**  
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`  
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`

---

# 1. Objet du document

Ce document identifie les **parties prenantes** de PyAgentsKit et formalise les **cas d’usage** que la plateforme doit supporter.

L’objectif est de répondre précisément à trois questions :

1. **Qui utilise, exploite, contrôle ou subit les effets d’un agent exécuté via PyAgentsKit ?**
2. **Quelles interactions ces acteurs ont-ils avec le runtime ?**
3. **Quels scénarios concrets justifient les capacités du framework ?**

PyAgentsKit est ici considéré comme :

> **une couche de fiabilité indépendante des frameworks, destinée aux runtimes d’agents IA pilotables programmatiquement, fournissant état durable, effets protégés, validations humaines, coordination distribuée, reprise et observabilité opérationnelle.**

---

# 2. Vue d’ensemble des parties prenantes

Les parties prenantes sont regroupées en huit familles :

```text
1. Utilisateurs métiers
2. Développeurs d’agents
3. Développeurs / exploitants de coding agents
4. AI / Data Engineers
5. Platform Engineers / DevOps
6. SRE / Exploitants
7. Responsables sécurité / conformité / audit
8. Administrateurs et systèmes externes
```

---

# 3. Cartographie des acteurs

## 3.1 Utilisateur métier

### Rôle

L’utilisateur métier déclenche ou consomme une action réalisée par un agent.

Exemples :

- acheteur ;
- RH ;
- gestionnaire ;
- analyste ;
- support ;
- finance ;
- opérations ;
- juriste ;
- responsable métier.

### Objectifs

- automatiser des tâches répétitives ;
- obtenir des résultats rapides ;
- conserver un contrôle sur les actions sensibles ;
- bénéficier d’une traçabilité claire ;
- éviter les doubles traitements.

### Attentes vis-à-vis de PyAgentsKit

- fiabilité ;
- reprise après incident ;
- absence de duplication ;
- validations humaines ;
- audit ;
- transparence sur l’état d’une exécution.

### Risques perçus

- action effectuée deux fois ;
- action incorrecte ;
- résultat perdu ;
- absence de visibilité ;
- automatisation sans contrôle.

---

## 3.2 Développeur d’agents

### Rôle

Il construit l’agent lui-même ou son orchestration.

Exemples de runtimes :

- LangGraph ;
- PydanticAI ;
- OpenAI Agents SDK ;
- Claude Agent SDK ;
- AutoGen ;
- CrewAI ;
- runtime propriétaire.

### Objectifs

- se concentrer sur la logique agentique ;
- déléguer les problèmes de durabilité ;
- disposer d’un runtime fiable ;
- éviter de réimplémenter le même socle dans chaque projet.

### Attentes

- API claire ;
- adapters stables ;
- stores substituables ;
- reprise explicite ;
- intégration simple des tools ;
- faible couplage.

### Risques

- abstraction trop complexe ;
- vendor lock-in ;
- comportements implicites ;
- manque de contrôle sur la reprise.

---

## 3.3 Développeur / exploitant de coding agents

### Rôle

Il utilise ou orchestre un agent spécialisé dans le développement logiciel.

Exemples :

```text
Codex
Claude Code
OpenCode
Antigravity CLI (agy)
autres coding agents
```

### Objectifs

- automatiser la maintenance ;
- corriger des bugs ;
- modifier du code ;
- exécuter des tests ;
- créer des commits ;
- créer des PR ;
- publier ;
- déployer.

### Attentes

- contrôle des actions sensibles ;
- isolation des workspaces ;
- reprise après crash ;
- audit des opérations ;
- approvals avant push, merge, publication ou déploiement.

### Risques

- modification concurrente du même repository ;
- push répété ;
- PR dupliquée ;
- publication répétée ;
- déploiement accidentel ;
- perte du contexte après interruption.

---

## 3.4 AI / Data Engineer

### Rôle

Il connecte l’agent aux systèmes métier et aux données.

### Objectifs

- exposer des outils métier ;
- protéger les actions externes ;
- garantir la cohérence des données ;
- gérer les erreurs réseau ;
- exploiter des systèmes persistants.

### Attentes

- protected effects ;
- idempotence ;
- reconciliation ;
- stores persistants ;
- connecteurs standardisés.

### Risques

- doublons ;
- corruption ;
- timeout ambigu ;
- écriture partielle ;
- manque de traçabilité.

---

## 3.5 Platform Engineer / DevOps

### Rôle

Il industrialise et déploie PyAgentsKit.

### Objectifs

- déploiement multi-worker ;
- scalabilité ;
- intégration PostgreSQL ;
- déploiement conteneurisé ;
- CI/CD ;
- observabilité.

### Attentes

- health checks ;
- readiness ;
- graceful shutdown ;
- configuration explicite ;
- métriques ;
- runbooks.

### Risques

- split-brain ;
- mauvaise reprise ;
- dépendance à un composant unique ;
- explosion des coûts opérationnels.

---

## 3.6 SRE / Exploitant

### Rôle

Il maintient le système en conditions opérationnelles.

### Objectifs

Répondre rapidement à :

```text
quel run est bloqué ?
qui le possède ?
quel worker est actif ?
quel effet a été exécuté ?
quel approval manque ?
quel lease a expiré ?
```

### Attentes

- logs structurés ;
- métriques ;
- traces ;
- audit ;
- inspection des runs ;
- alerting.

### Risques

- incident non diagnostiquable ;
- reprise non maîtrisée ;
- absence de visibilité sur les ownerships.

---

## 3.7 Responsable sécurité / conformité / audit

### Rôle

Il définit les règles de contrôle et vérifie leur respect.

### Objectifs

- gouvernance ;
- moindre privilège ;
- séparation des rôles ;
- approvals ;
- audit ;
- traçabilité ;
- preuve d’exécution.

### Attentes

- journal d’audit ;
- identité des acteurs ;
- justification des décisions ;
- contrôle des actions critiques.

### Risques

- action non autorisée ;
- approbation falsifiée ;
- secrets exposés ;
- replay malveillant ;
- audit incomplet.

---

## 3.8 Administrateur système

### Rôle

Il configure l’environnement et les dépendances.

### Objectifs

- gérer les credentials ;
- paramétrer les stores ;
- configurer les workers ;
- maintenir PostgreSQL ;
- gérer les backends de stockage.

### Attentes

- configuration standardisée ;
- migrations ;
- diagnostics ;
- compatibilité cloud/on-premise.

---

## 3.9 Systèmes externes

### Rôle

Ils reçoivent ou exposent les effets produits par les agents.

Exemples :

```text
ERP
CRM
P2P
ATS
bases de données
Git
GitHub / GitLab
CI/CD
cloud providers
package registries
email
Slack
stockage objet
APIs métier
```

### Attentes implicites

- appels cohérents ;
- idempotence lorsque disponible ;
- authentification valide ;
- respect des contrats ;
- absence de duplication.

---

# 4. Matrice parties prenantes / responsabilités

| Partie prenante | Déclenche | Décide | Exécute | Contrôle | Exploite | Audite |
|---|---:|---:|---:|---:|---:|---:|
| Utilisateur métier | Oui | Oui | Non | Oui | Non | Partiel |
| Développeur d’agents | Non | Non | Oui | Oui | Partiel | Non |
| Coding-agent operator | Oui | Partiel | Oui | Oui | Partiel | Non |
| AI / Data Engineer | Non | Non | Oui | Oui | Partiel | Non |
| Platform / DevOps | Non | Non | Non | Oui | Oui | Non |
| SRE | Non | Non | Non | Oui | Oui | Partiel |
| Sécurité / conformité | Non | Oui | Non | Oui | Non | Oui |
| Administrateur | Non | Non | Non | Oui | Oui | Non |
| Système externe | Non | Non | Oui | Non | Non | Non |

---

# 5. Catégories de cas d’usage

Les cas d’usage PyAgentsKit se répartissent en six familles :

```text
A. Exécution agentique durable
B. Gouvernance humaine
C. Protection des effets
D. Coordination distribuée
E. Exploitation & observabilité
F. Coding agents
```

---

# 6. Cas d’usage UC01 — Exécuter un agent métier avec état persistant

## Acteurs

- utilisateur métier ;
- agent runtime ;
- PyAgentsKit ;
- PostgreSQL ;
- systèmes externes.

## Préconditions

- agent configuré ;
- runtime adapter disponible ;
- stores accessibles ;
- run créé.

## Flux nominal

```text
Utilisateur
   ↓
création du run
   ↓
AgentRuntimeAdapter
   ↓
Agent
   ↓
PyAgentsKit persiste l’état
   ↓
Tool / System
   ↓
Résultat
   ↓
checkpoint
   ↓
run continue
```

## Résultat attendu

- chaque étape importante est persistée ;
- le run peut être repris ;
- l’historique est consultable.

---

# 7. UC02 — Reprendre un run après crash

## Acteurs

- worker initial ;
- nouveau worker ;
- PyAgentsKit ;
- RunStore.

## Préconditions

- checkpoint existant ;
- run non terminé.

## Flux

```text
Worker A
   ↓
exécution
   ↓
checkpoint
   ↓
CRASH
   ↓
Worker B
   ↓
load checkpoint
   ↓
resume
```

## Résultat attendu

Aucune progression déjà confirmée ne doit être perdue.

---

# 8. UC03 — Suspendre pour validation humaine

## Acteurs

- agent ;
- approbateur humain ;
- ApprovalStore ;
- runtime.

## Flux

```text
Agent
  ↓
action sensible détectée
  ↓
approval requested
  ↓
run = WAITING
  ↓
humain décide
  ↓
approve / reject
  ↓
resume / stop
```

## Critères

- l’approval survit à un restart ;
- la décision est tracée ;
- l’identité du décideur est conservée.

---

# 9. UC04 — Exécuter un effet idempotent

## Exemple

```text
POST /orders
idempotency-key = run123-effect45
```

## Flux

```text
Effect intent
   ↓
idempotency key
   ↓
external call
   ↓
success
   ↓
persist effect outcome
```

## Résultat attendu

Un retry avec la même clé ne crée pas un nouvel effet.

---

# 10. UC05 — Réconcilier un effet au résultat inconnu

## Situation

```text
effect started
↓
external system executes
↓
network timeout
↓
local outcome unknown
```

## Flux

```text
status = UNKNOWN
   ↓
EffectReconciler
   ↓
query external system
   ↓
determine actual state
   ↓
SUCCEEDED / FAILED / MANUAL_REVIEW
```

## Résultat attendu

Pas de retry aveugle.

---

# 11. UC06 — Empêcher le replay d’un effet déjà réussi

## Exemple

```text
send_email
publish_package
create_invoice
merge_pull_request
```

## Flux

```text
effect exists
status = SUCCEEDED
↓
resume run
↓
detect previous outcome
↓
reuse stored result
```

## Résultat attendu

L’effet n’est pas rejoué.

---

# 12. UC07 — Exécution multi-worker

## Acteurs

- Worker A ;
- Worker B ;
- LeaseStore.

## Flux

```text
Run R1
 ↓
Worker A acquires lease
 ↓
Worker B tries lease
 ↓
conflict
 ↓
Worker A continues
```

## Résultat attendu

Un seul worker possède le run.

---

# 13. UC08 — Takeover après expiration de lease

## Flux

```text
Worker A
token = 31
↓
crash
↓
lease expires

Worker B
token = 32
↓
takeover
↓
resume
```

## Résultat attendu

Le run continue sans duplication.

---

# 14. UC09 — Rejeter un worker obsolète

## Flux

```text
Worker A token 31
Worker B token 32
↓
Worker A revient
↓
tentative d’effet protégé
↓
token 31 rejected
```

## Résultat attendu

Protection contre le split-brain.

---

# 15. UC10 — Arrêt propre d’un worker

## Acteurs

- orchestrateur ;
- worker ;
- PyAgentsKit.

## Flux

```text
SIGTERM
  ↓
stop admissions
  ↓
finish / checkpoint active work
  ↓
release or stop lease renewals
  ↓
shutdown
```

## Résultat attendu

Aucune interruption incohérente.

---

# 16. UC11 — Inspecter l’état d’un run

## Acteur

SRE / exploitant.

## Questions supportées

```text
run_id ?
status ?
worker owner ?
lease ?
checkpoint ?
approval pending ?
last effect ?
last error ?
```

## Résultat attendu

Diagnostic rapide.

---

# 17. UC12 — Auditer une exécution

## Acteur

Audit / conformité.

## Événements consultables

- run created ;
- run started ;
- effect requested ;
- approval requested ;
- approval granted ;
- lease acquired ;
- lease lost ;
- takeover ;
- effect succeeded ;
- run completed.

## Résultat attendu

Chronologie reconstruisible.

---

# 18. UC13 — Remplacer un runtime agentique

## Exemple

Passage de :

```text
LangGraph
```

à :

```text
PydanticAI
```

ou :

```text
OpenAI Agents SDK
```

## Précondition

Chaque runtime respecte le contrat `AgentRuntimeAdapter`.

## Résultat attendu

Les stores et garanties PyAgentsKit restent inchangés.

---

# 19. UC14 — Exécuter un coding agent en mode contrôlé

## Acteurs

- développeur ;
- coding agent ;
- PyAgentsKit ;
- Git ;
- CI/CD.

## Flux nominal

```text
Issue / Task
    ↓
Coding Agent
    ↓
read repository
    ↓
modify files
    ↓
run tests
    ↓
create commit
    ↓
approval / policy
    ↓
git push
    ↓
create PR
    ↓
CI
    ↓
approval
    ↓
merge
```

## Résultat attendu

Les actions sensibles sont contrôlées sans empêcher l’autonomie sur les opérations à faible risque.

---

# 20. UC15 — Crash après git push

## Situation

```text
git push
↓
remote accepted
↓
worker crashes
↓
local confirmation missing
```

## Flux

```text
status = UNKNOWN
↓
inspect remote
↓
commit/branch exists ?
↓
yes → reconcile success
no  → safe retry / approval
```

## Résultat attendu

Pas de push aveugle.

---

# 21. UC16 — Plusieurs coding agents sur un même repository

## Acteurs

```text
Codex
Claude Code
OpenCode
agy
```

## Risque

Modification concurrente.

## Approche

PyAgentsKit peut protéger une ressource logique :

```text
repository
branch
worktree
workspace
```

via :

```text
lease
ownership
fencing
```

## Résultat attendu

Pas de collision incontrôlée.

---

# 22. UC17 — Publier un package avec approval

## Flux

```text
coding agent
↓
build package
↓
tests
↓
propose publish
↓
approval
↓
publish
↓
persist external reference
```

## Résultat attendu

La publication est traçable et non rejouée implicitement.

---

# 23. UC18 — Déployer en production

## Flux

```text
agent
↓
prepare deployment
↓
policy check
↓
human approval
↓
deploy
↓
health validation
↓
record outcome
```

## Résultat attendu

Contrôle fort sur les effets critiques.

---

# 24. UC19 — Utiliser un runtime propriétaire

## Situation

Une entreprise dispose d’un agent interne.

## Approche

Créer :

```python
class InternalAgentAdapter(AgentRuntimeAdapter):
    ...
```

## Résultat attendu

Le runtime propriétaire bénéficie :

- durable state ;
- approvals ;
- effects ;
- leases ;
- audit.

---

# 25. UC20 — Exécuter un workflow long

## Exemple

```text
Day 1  : ingestion
Day 2  : validation
Day 3  : approval
Day 4  : external action
```

## Résultat attendu

Le run peut rester suspendu durablement sans processus actif permanent.

---

# 26. UC21 — Indisponibilité PostgreSQL

## Flux

```text
worker running
↓
PostgreSQL unavailable
↓
cannot persist / renew ownership
↓
runtime enters safe mode
↓
stop new protected effects
```

## Résultat attendu

La perte de persistance entraîne un comportement conservateur.

---

# 27. UC22 — Reprise après restauration de l’infrastructure

## Flux

```text
DB restored
↓
worker restarts
↓
load runs
↓
validate leases
↓
resume eligible runs
```

## Résultat attendu

Reprise contrôlée.

---

# 28. UC23 — Déclencher un run depuis une API externe

## Acteurs

- service métier ;
- API PyAgentsKit ;
- agent runtime.

## Flux

```text
external service
↓
create run
↓
AgentRuntimeAdapter
↓
execution
```

## Résultat attendu

Découplage entre déclencheur et runtime.

---

# 29. UC24 — Déclencher un run planifié

PyAgentsKit peut recevoir un déclenchement d’un système de scheduling externe.

Exemple :

```text
PyScheduleKit
      ↓
create run
      ↓
PyAgentsKit
```

PyAgentsKit ne doit pas devenir lui-même un scheduler généraliste.

---

# 30. UC25 — Exposer des événements de run

## Acteurs

- UI ;
- webhook ;
- monitoring ;
- audit service.

## Événements

```text
run.created
run.started
run.waiting
run.resumed
effect.started
effect.succeeded
effect.unknown
approval.requested
approval.granted
lease.lost
run.completed
```

## Résultat attendu

Intégration avec les systèmes externes sans couplage fort.

---

# 31. Matrice cas d’usage / capacités PyAgentsKit

| Cas d’usage | Capacité principale |
|---|---|
| UC01 | RunStore / SessionStore |
| UC02 | DurableRunner |
| UC03 | ApprovalStore |
| UC04 | Idempotency |
| UC05 | EffectReconciler |
| UC06 | EffectStore |
| UC07 | LeaseStore |
| UC08 | Takeover |
| UC09 | Fencing |
| UC10 | Graceful shutdown |
| UC11 | Inspection |
| UC12 | Audit events |
| UC13 | AgentRuntimeAdapter |
| UC14 | Coding-agent adapter |
| UC15 | Reconciliation |
| UC16 | Lease / workspace ownership |
| UC17 | ProtectedEffect |
| UC18 | Approval + policy |
| UC19 | Custom adapter |
| UC20 | Durable execution |
| UC21 | Safe degradation |
| UC22 | Recovery |
| UC23 | API integration |
| UC24 | External scheduling integration |
| UC25 | Event model |

---

# 32. Criticité des cas d’usage

## Critiques

```text
UC01
UC02
UC03
UC04
UC05
UC06
UC07
UC08
UC09
UC21
```

Ils constituent le cœur de la valeur PyAgentsKit.

---

## Élevés

```text
UC10
UC11
UC12
UC13
UC20
UC22
UC25
```

Ils sont indispensables à une exploitation production.

---

## Stratégiques

```text
UC14
UC15
UC16
UC17
UC18
UC19
UC23
UC24
```

Ils élargissent le champ d’application sans modifier le noyau conceptuel.

---

# 33. RACI simplifié

| Activité | Métier | Dev Agent | AI/Data | Platform | SRE | Sécurité |
|---|---|---|---|---|---|---|
| Définir logique agent | C | R/A | C | I | I | C |
| Définir tools | C | R | A | I | I | C |
| Déployer runtime | I | C | C | R/A | C | C |
| Définir approvals | A | C | C | I | I | R |
| Configurer stores | I | C | R | A | C | I |
| Gérer incidents | I | C | C | C | R/A | I |
| Auditer | I | I | I | C | C | R/A |
| Définir politiques | C | C | C | C | I | R/A |

Légende :

```text
R = Responsible
A = Accountable
C = Consulted
I = Informed
```

---

# 34. Besoins transverses issus des cas d’usage

L’analyse des cas d’usage fait émerger les besoins transverses suivants :

```text
1. Run lifecycle explicite
2. État persistant
3. Checkpointing
4. Effect lifecycle
5. Idempotency
6. Reconciliation
7. Approval lifecycle
8. Distributed ownership
9. Fencing
10. Runtime adapters
11. Audit events
12. Observability
13. Safe degradation
14. External integrations
15. Coding-agent support
```

---

# 35. Invariants transverses

## INV-01

Un run dispose d’un identifiant stable.

## INV-02

Un effet externe doit être identifiable.

## INV-03

Un effet réussi ne doit pas être rejoué implicitement.

## INV-04

Un effet ambigu doit être réconcilié.

## INV-05

Un worker doit posséder le run avant toute progression protégée.

## INV-06

Un worker obsolète ne doit plus produire d’effet protégé.

## INV-07

Un approval doit être durable.

## INV-08

Une reprise doit être auditable.

## INV-09

Le runtime agentique doit être remplaçable.

## INV-10

Les coding agents ne doivent pas introduire de dépendance conceptuelle dans le cœur.

---

# 36. Cas d’usage hors périmètre

PyAgentsKit ne doit pas traiter directement :

```text
génération de code
analyse sémantique de repository
édition IDE
prompt engineering
fine-tuning
RAG
vector search
UI de chatbot
gestion de modèles
orchestration BPM générique
scheduling généraliste
```

Ces fonctions peuvent être fournies par d’autres systèmes.

---

# 37. Synthèse

Les parties prenantes attendent de PyAgentsKit des bénéfices différents :

```text
Métier
→ contrôle et fiabilité

Développeur
→ primitives réutilisables

AI/Data Engineer
→ protection des effets

Platform
→ déploiement robuste

SRE
→ observabilité et reprise

Sécurité
→ gouvernance et audit

Coding-agent operator
→ autonomie contrôlée
```

Tous convergent néanmoins vers le même besoin central :

> **Permettre à un runtime agentique de produire des actions réelles tout en conservant les garanties attendues d’un système de production.**

Les cas d’usage détaillés dans ce document serviront directement de base aux documents suivants :

```text
../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md
../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md
../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md
06_PYAGENTSKIT_MODELE_CONCEPTUEL_DU_DOMAINE.md
```
