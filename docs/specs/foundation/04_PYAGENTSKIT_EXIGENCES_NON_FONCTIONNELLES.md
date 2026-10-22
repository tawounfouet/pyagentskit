# PyAgentsKit — Exigences non fonctionnelles

**Document :** `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`  
**Version :** 1.0  
**Date :** 19 octobre 2026  
**Statut :** Spécification non fonctionnelle / Production Readiness  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/02_PYAGENTSKIT_PARTIES_PRENANTES_ET_CAS_D_USAGE.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`

---

# 1. Objet du document

Ce document formalise les **exigences non fonctionnelles** de PyAgentsKit.

Il décrit les qualités attendues du framework au-delà de ses fonctionnalités métier :

- fiabilité ;
- résilience ;
- disponibilité ;
- performance ;
- scalabilité ;
- sécurité ;
- observabilité ;
- portabilité ;
- maintenabilité ;
- testabilité ;
- compatibilité ;
- exploitabilité ;
- gouvernance ;
- coûts opérationnels ;
- contraintes de production.

L’objectif est de préciser **dans quelles conditions PyAgentsKit doit fonctionner correctement**.

---

# 2. Convention de lecture

Chaque exigence suit le format :

```text
ID
Titre
Priorité
Objectif
Exigence
Critères d’acceptation
Mesure / preuve
Traçabilité
```

Priorités :

```text
MUST    indispensable pour considérer le framework fiable
SHOULD  fortement recommandé pour production
COULD   amélioration ou extension
```

Les objectifs chiffrés de ce document constituent des **cibles initiales de qualification**.

Ils devront être ajustés par benchmark et retour d’expérience.

---

# 3. Domaines non fonctionnels

Les exigences sont regroupées en 16 domaines :

```text
A. Fiabilité
B. Résilience
C. Cohérence et sûreté des effets
D. Disponibilité
E. Performance
F. Scalabilité
G. Concurrence distribuée
H. Sécurité
I. Confidentialité et protection des données
J. Observabilité
K. Auditabilité
L. Portabilité et interopérabilité
M. Maintenabilité et évolutivité
N. Testabilité et qualification
O. Exploitabilité
P. Efficience et maîtrise des coûts
```

---

# 4. A — Fiabilité

## NFR-001 — Priorité à la correction

**Priorité : MUST**

### Objectif

Garantir la cohérence des exécutions avant d’optimiser leur vitesse.

### Exigence

En cas d’arbitrage entre :

```text
performance
vs
correctness
```

PyAgentsKit doit privilégier la correction.

### Critères d’acceptation

- aucune optimisation ne doit contourner les contrôles d’ownership ;
- aucun retry ne doit contourner la logique d’effet ;
- aucune reprise ne doit ignorer un état ambigu.

### Traçabilité

- FR-045
- FR-073
- FR-087

---

## NFR-002 — Persistance avant progression critique

**Priorité : MUST**

Un état nécessaire à la reprise doit être persisté avant toute transition irréversible.

---

## NFR-003 — Aucune perte silencieuse d’état critique

**Priorité : MUST**

Une erreur de persistance doit être visible et empêcher la progression lorsque la sûreté dépend de cette persistance.

---

## NFR-004 — Comportement déterministe des transitions

**Priorité : MUST**

À état identique et événement identique, la machine à états doit produire la même transition.

---

## NFR-005 — États terminaux immuables

**Priorité : MUST**

Un run ou un effet terminé ne doit pas revenir silencieusement dans un état actif.

---

# 5. B — Résilience

## NFR-010 — Tolérance au crash d’un worker

**Priorité : MUST**

### Objectif

Un crash process ne doit pas rendre un run irrécupérable.

### Critères

Après :

```text
SIGKILL
process crash
container restart
machine loss
```

un run éligible doit pouvoir être repris.

### Traçabilité

- FR-041
- FR-042

---

## NFR-011 — Tolérance au SIGTERM

**Priorité : MUST**

Le runtime doit supporter un arrêt propre avec :

- arrêt des admissions ;
- checkpoint ;
- traitement des leases ;
- terminaison contrôlée.

---

## NFR-012 — Tolérance aux pauses longues

**Priorité : MUST**

Un worker suspendu suffisamment longtemps pour perdre son lease doit être considéré obsolète.

---

## NFR-013 — Reprise après indisponibilité PostgreSQL

**Priorité : MUST**

Une panne temporaire de PostgreSQL doit entraîner :

```text
safe degradation
→ recovery
→ controlled resume
```

et non une progression non contrôlée.

---

## NFR-014 — Tolérance aux erreurs réseau transitoires

**Priorité : MUST**

Le framework doit différencier :

- erreur avant envoi ;
- erreur pendant appel ;
- résultat ambigu ;
- erreur confirmée.

---

## NFR-015 — Backoff borné

**Priorité : SHOULD**

Les mécanismes de retry techniques doivent supporter :

- backoff ;
- jitter ;
- nombre maximal de tentatives ;
- budget temporel.

---

## NFR-016 — Pas de retry infini par défaut

**Priorité : MUST**

Un mécanisme de retry ne doit pas tourner indéfiniment sans politique explicite.

---

# 6. C — Cohérence et sûreté des effets

## NFR-020 — Pas de promesse d’exactly-once absolu

**Priorité : MUST**

PyAgentsKit ne doit pas présenter une garantie d’`exactly-once` universelle sur des systèmes externes qui ne la supportent pas.

### Terminologie autorisée

Selon le scénario :

```text
idempotent execution
deduplication
at-most-once protected effect
reconciliation
fencing-aware execution
```

---

## NFR-021 — Effet ambigu traité comme ambigu

**Priorité : MUST**

Un effet dont le résultat n’est pas connu ne doit pas être converti automatiquement en succès ou échec.

---

## NFR-022 — Protection contre le replay implicite

**Priorité : MUST**

Un effet terminé ne doit jamais être rejoué implicitement lors d’une reprise.

---

## NFR-023 — Intégrité de la clé d’idempotence

**Priorité : MUST**

Une clé d’idempotence doit rester stable pour un même effet logique.

---

## NFR-024 — Détection des collisions d’idempotence

**Priorité : SHOULD**

Le système doit détecter les cas où une même clé est utilisée avec des inputs incompatibles.

---

## NFR-025 — Réconciliation explicite

**Priorité : MUST**

Tout effet `UNKNOWN` doit disposer :

- d’une stratégie de reconciliation ;
- ou d’une sortie explicite vers revue manuelle.

---

# 7. D — Disponibilité

## NFR-030 — Absence de dépendance à un worker unique

**Priorité : MUST**

Le design doit permettre à un autre worker de reprendre un run.

---

## NFR-031 — Dégradation contrôlée

**Priorité : MUST**

La perte d’une dépendance critique doit produire un état dégradé explicite.

---

## NFR-032 — Readiness indépendante de liveness

**Priorité : MUST**

Le framework doit distinguer :

```text
alive
ready
```

Un worker vivant mais incapable d’accéder à ses stores ne doit pas être considéré prêt.

---

## NFR-033 — Objectif de reprise initial

**Priorité : SHOULD**

Pour une qualification locale/cluster de référence, la reprise d’un run après expiration de lease devrait pouvoir intervenir dans une fenêtre cible de :

```text
TTL du lease
+
délai de détection
+
temps d’acquisition
```

sans intervention humaine.

Aucune valeur universelle n’est imposée au cœur.

---

# 8. E — Performance

## NFR-040 — Overhead du cœur borné

**Priorité : SHOULD**

Le runtime PyAgentsKit ne doit pas ajouter une latence disproportionnée aux opérations hors appels externes.

### Cible initiale

Les opérations purement locales du cœur doivent être mesurables séparément des appels LLM et systèmes externes.

---

## NFR-041 — Mesure des latences critiques

**Priorité : MUST**

Le framework doit mesurer séparément :

```text
run transition latency
store latency
lease acquisition latency
lease renewal latency
effect persistence latency
approval transition latency
adapter latency
```

---

## NFR-042 — Pas de blocage global

**Priorité : MUST**

Une opération lente sur un run ne doit pas bloquer tous les autres runs.

---

## NFR-043 — Async compatible

**Priorité : MUST**

Le cœur doit être compatible avec les workflows asynchrones Python.

---

## NFR-044 — Backpressure

**Priorité : SHOULD**

Le runtime doit pouvoir limiter les admissions lorsque :

- stores saturés ;
- workers surchargés ;
- dépendances critiques dégradées.

---

# 9. F — Scalabilité

## NFR-050 — Scalabilité horizontale

**Priorité : MUST**

Le nombre de workers doit pouvoir évoluer de :

```text
1 → N
```

sans changement du modèle fonctionnel.

---

## NFR-051 — Absence d’état critique uniquement local

**Priorité : MUST**

Un état nécessaire à la reprise distribuée ne doit pas exister uniquement en mémoire locale.

---

## NFR-052 — Partitionnement logique

**Priorité : SHOULD**

Les modèles doivent permettre un futur partitionnement par :

- tenant ;
- workload ;
- namespace ;
- type de run ;
- queue logique.

---

## NFR-053 — Scalabilité des stores

**Priorité : SHOULD**

Les interfaces de persistence ne doivent pas empêcher :

- pooling ;
- indexation ;
- réplication ;
- partitionnement backend.

---

## NFR-054 — Tests de charge concurrents

**Priorité : MUST**

La qualification production doit couvrir :

- acquisitions concurrentes ;
- renewals concurrents ;
- takeovers ;
- effets concurrents ;
- contention PostgreSQL.

---

# 10. G — Concurrence distribuée

## NFR-060 — Ownership atomique

**Priorité : MUST**

L’acquisition d’un lease doit être atomique.

---

## NFR-061 — Fencing monotone

**Priorité : MUST**

Les fencing tokens doivent augmenter de manière monotone par ressource protégée.

---

## NFR-062 — Aucune dépendance à l’horloge parfaite

**Priorité : MUST**

La sûreté ne doit pas dépendre d’une synchronisation parfaite des horloges des workers.

---

## NFR-063 — Détection de split-brain

**Priorité : MUST**

Les scénarios de split-brain doivent être détectables ou rendus inoffensifs par fencing.

---

## NFR-064 — Renouvellement borné

**Priorité : MUST**

Un worker ne doit pas pouvoir renouveler indéfiniment un lease qu’il ne possède plus.

---

## NFR-065 — Reprise sûre après suspension

**Priorité : MUST**

Un worker revenant après une longue suspension doit revalider son ownership.

---

## NFR-066 — Dimensionnement TTL documenté

**Priorité : SHOULD**

La documentation doit fournir une méthode pour dimensionner :

```text
TTL
heartbeat interval
renewal deadline
takeover delay
```

---

# 11. H — Sécurité

## NFR-070 — Principe du moindre privilège

**Priorité : MUST**

Chaque worker et adapter ne doit disposer que des permissions nécessaires.

---

## NFR-071 — Secrets hors état métier

**Priorité : MUST**

Les secrets ne doivent pas être stockés dans :

- run state ;
- session state ;
- memory ;
- audit events ;
- logs.

---

## NFR-072 — Redaction des données sensibles

**Priorité : MUST**

Les logs et événements doivent supporter la redaction de champs sensibles.

---

## NFR-073 — Contrôle d’accès sur les approvals

**Priorité : MUST**

Une décision humaine sensible doit être associée à une identité autorisée.

---

## NFR-074 — Authentification des systèmes externes

**Priorité : MUST**

Les connecteurs doivent supporter des mécanismes d’authentification externes sans stocker leurs secrets en clair.

---

## NFR-075 — Protection des actions critiques

**Priorité : MUST**

Les actions classées critiques doivent pouvoir imposer :

- policy ;
- approval ;
- fencing ;
- audit.

---

## NFR-076 — Isolation des adapters

**Priorité : SHOULD**

Une erreur ou un comportement fautif d’un adapter ne doit pas compromettre l’état global du runtime.

---

## NFR-077 — Dépendances auditées

**Priorité : SHOULD**

Les dépendances critiques doivent pouvoir être analysées pour :

- CVE ;
- vulnérabilités ;
- supply-chain risk.

---

# 12. I — Confidentialité et protection des données

## NFR-080 — Minimisation

**Priorité : MUST**

PyAgentsKit ne doit conserver que les données nécessaires à la reprise, l’audit et l’exploitation.

---

## NFR-081 — Séparation metadata / binary

**Priorité : SHOULD**

Les binaires volumineux doivent pouvoir être séparés des stores transactionnels.

---

## NFR-082 — Rétention configurable

**Priorité : SHOULD**

Les historiques doivent pouvoir disposer de politiques de rétention configurables.

---

## NFR-083 — Suppression maîtrisée

**Priorité : SHOULD**

La suppression d’un run, artifact ou historique doit respecter les contraintes d’audit et de rétention applicables.

---

## NFR-084 — Chiffrement backend

**Priorité : SHOULD**

Les backends de production devraient permettre le chiffrement :

- en transit ;
- au repos.

PyAgentsKit ne doit pas réimplémenter les mécanismes cryptographiques des infrastructures sous-jacentes.

---

# 13. J — Observabilité

## NFR-090 — Logs structurés

**Priorité : MUST**

Les logs doivent être exploitables par machine.

Format recommandé :

```text
JSON structured logs
```

---

## NFR-091 — Identifiants de corrélation

**Priorité : MUST**

Chaque log critique doit pouvoir inclure selon contexte :

```text
run_id
session_id
effect_id
approval_id
worker_id
lease_id
trace_id
```

---

## NFR-092 — OpenTelemetry compatible

**Priorité : SHOULD**

Le framework doit pouvoir exporter traces et métriques selon les standards OpenTelemetry.

---

## NFR-093 — Métriques de runs

**Priorité : MUST**

Au minimum :

```text
created
running
waiting
succeeded
failed
cancelled
resumed
```

---

## NFR-094 — Métriques de leases

**Priorité : MUST**

Au minimum :

```text
acquisition
renewal
loss
conflict
expiration
takeover
```

---

## NFR-095 — Métriques d’effets

**Priorité : MUST**

Au minimum :

```text
started
succeeded
failed
unknown
reconciled
manual_review
```

---

## NFR-096 — Métriques d’approvals

**Priorité : SHOULD**

Au minimum :

```text
requested
approved
rejected
expired
latency
```

---

## NFR-097 — Traces distribuées

**Priorité : SHOULD**

Les traces doivent pouvoir relier :

```text
agent runtime
PyAgentsKit
store
tool
external system
```

---

# 14. K — Auditabilité

## NFR-100 — Append-oriented audit

**Priorité : MUST**

Les événements d’audit doivent être orientés append plutôt que modification silencieuse.

---

## NFR-101 — Reconstruction historique

**Priorité : MUST**

Un auditeur doit pouvoir reconstruire :

```text
qui
quoi
quand
avec quel état
avec quel ownership
avec quelle approval
```

---

## NFR-102 — Audit de takeover

**Priorité : MUST**

Chaque changement de propriétaire doit être historisé.

---

## NFR-103 — Audit de fencing

**Priorité : MUST**

Les tokens attribués aux ownerships critiques doivent être auditables.

---

## NFR-104 — Audit des effets

**Priorité : MUST**

Les états et références externes des effets doivent être historisables.

---

## NFR-105 — Audit de configuration critique

**Priorité : SHOULD**

Les changements importants de configuration opérationnelle devraient être traçables.

---

# 15. L — Portabilité et interopérabilité

## NFR-110 — Python-first

**Priorité : MUST**

Le framework doit être utilisable naturellement depuis Python.

---

## NFR-111 — Python versions supportées

**Priorité : SHOULD**

La matrice de versions Python supportées doit être explicite dans chaque release.

---

## NFR-112 — Pas de dépendance obligatoire à Kubernetes

**Priorité : MUST**

PyAgentsKit doit fonctionner :

- localement ;
- en VM ;
- en conteneur ;
- dans Kubernetes.

---

## NFR-113 — Pas de dépendance obligatoire à un cloud

**Priorité : MUST**

Le cœur ne doit imposer ni AWS, ni Azure, ni GCP.

---

## NFR-114 — Backends substituables

**Priorité : MUST**

Les contrats doivent permettre plusieurs implémentations de :

```text
RunStore
SessionStore
MemoryStore
ApprovalStore
EffectStore
LeaseStore
ArtifactStore
AgentRuntimeAdapter
```

---

## NFR-115 — PostgreSQL comme backend de référence production

**Priorité : MUST**

La qualification principale du stockage transactionnel doit inclure PostgreSQL réel.

---

## NFR-116 — Standards avant formats propriétaires

**Priorité : SHOULD**

Lorsque pertinent, préférer :

```text
OpenTelemetry
JSON
SQL
HTTP
standard object storage semantics
```

à des formats fermés.

---

# 16. M — Maintenabilité et évolutivité

## NFR-120 — Architecture modulaire

**Priorité : MUST**

Les responsabilités principales doivent rester séparées.

---

## NFR-121 — Core indépendant des adapters

**Priorité : MUST**

L’ajout d’un nouvel adapter ne doit pas nécessiter de modifier le cœur dans le cas normal.

---

## NFR-122 — API publique identifiée

**Priorité : MUST**

La surface publique doit être clairement séparée des APIs internes.

---

## NFR-123 — Compatibilité ascendante

**Priorité : SHOULD**

Les releases mineures doivent éviter de casser les contrats publics stables.

---

## NFR-124 — Dépréciation explicite

**Priorité : SHOULD**

Toute suppression future d’API publique doit passer par une période de dépréciation documentée.

---

## NFR-125 — Migrations versionnées

**Priorité : MUST**

Les schémas persistants doivent évoluer via migrations versionnées.

---

## NFR-126 — Complexité maîtrisée

**Priorité : MUST**

Une nouvelle abstraction ne doit être ajoutée que si elle répond à un besoin identifié ou à une extension justifiée.

---

## NFR-127 — Documentation proche du code

**Priorité : SHOULD**

Les contrats publics doivent disposer de documentation et exemples synchronisés avec le code.

---

# 17. N — Testabilité et qualification

## NFR-130 — Unit tests

**Priorité : MUST**

Les machines à états, policies et contrats doivent disposer de tests unitaires.

---

## NFR-131 — Contract tests

**Priorité : MUST**

Les implémentations de stores et adapters doivent pouvoir être soumises à des suites contractuelles communes.

---

## NFR-132 — Integration tests PostgreSQL réel

**Priorité : MUST**

Le backend PostgreSQL doit être testé contre une instance réelle, pas uniquement mockée.

---

## NFR-133 — Multi-process tests

**Priorité : MUST**

Les scénarios distribués doivent inclure plusieurs processus indépendants.

---

## NFR-134 — Fault injection

**Priorité : MUST**

La qualification doit couvrir :

```text
SIGTERM
SIGKILL
process freeze
network failure
database outage
timeout
lease expiry
```

---

## NFR-135 — Split-brain tests

**Priorité : MUST**

Le framework doit disposer de scénarios de qualification où deux workers se croient successivement propriétaires.

---

## NFR-136 — Effect ambiguity tests

**Priorité : MUST**

La suite doit tester :

```text
external success
+
lost local confirmation
```

---

## NFR-137 — Load tests

**Priorité : SHOULD**

Des tests de charge doivent mesurer :

- lease contention ;
- renewal throughput ;
- store latency ;
- run transitions ;
- event throughput.

---

## NFR-138 — Adapter compatibility suite

**Priorité : SHOULD**

Un adapter externe doit pouvoir prouver sa compatibilité via une suite standard.

---

## NFR-139 — Reproductibilité des tests

**Priorité : MUST**

Les tests critiques doivent être reproductibles en environnement CI.

---

# 18. O — Exploitabilité

## NFR-140 — Configuration externe

**Priorité : MUST**

La configuration d’environnement doit pouvoir être fournie sans modifier le code.

---

## NFR-141 — Health checks

**Priorité : MUST**

Le service doit exposer des signaux de santé compréhensibles par un orchestrateur.

---

## NFR-142 — Readiness checks

**Priorité : MUST**

La readiness doit refléter :

- état du store ;
- capacité d’admission ;
- état du worker.

---

## NFR-143 — Graceful shutdown documenté

**Priorité : MUST**

Le comportement d’arrêt doit être décrit dans un runbook.

---

## NFR-144 — Runbooks d’incident

**Priorité : MUST**

Au minimum :

```text
PostgreSQL unavailable
stuck run
lease storm
lost worker
reconciliation backlog
duplicate-effect suspicion
telemetry outage
```

---

## NFR-145 — Diagnostic CLI/API

**Priorité : SHOULD**

Le framework devrait permettre d’inspecter :

- version ;
- stores ;
- migrations ;
- workers ;
- leases ;
- runs ;
- health.

---

## NFR-146 — Déploiement progressif

**Priorité : SHOULD**

Le design doit permettre des rolling upgrades lorsqu’ils respectent les compatibilités de schema et protocole.

---

## NFR-147 — Rollback documenté

**Priorité : SHOULD**

Une release de production doit documenter les contraintes de rollback.

---

# 19. P — Efficience et maîtrise des coûts

## NFR-150 — Absence de dépendance SaaS obligatoire

**Priorité : MUST**

Le cœur doit pouvoir être exploité sans service SaaS propriétaire obligatoire.

---

## NFR-151 — Coût observable

**Priorité : SHOULD**

Les ressources consommées par les workers doivent être mesurables :

```text
CPU
RAM
DB connections
storage
network
external calls
```

---

## NFR-152 — Polling limité

**Priorité : SHOULD**

Les mécanismes de polling doivent être configurables et éviter les fréquences inutiles.

---

## NFR-153 — Artifact lifecycle

**Priorité : SHOULD**

Les artifacts volumineux doivent supporter une politique de rétention externe.

---

## NFR-154 — Scaling proportionnel

**Priorité : SHOULD**

L’ajout de workers ne doit pas provoquer une augmentation non maîtrisée de contention ou de renewals.

---

# 20. Exigences spécifiques aux coding agents

## NFR-160 — Isolation workspace

**Priorité : COULD**

Plusieurs coding agents doivent pouvoir être isolés via :

```text
workspace
worktree
branch
container
```

selon l’adapter.

---

## NFR-161 — Pas de dépendance Git dans le core

**Priorité : MUST**

Les concepts Git ne doivent pas devenir des dépendances du domaine central.

---

## NFR-162 — Actions critiques explicitement classables

**Priorité : COULD**

Les adapters doivent pouvoir classer :

```text
git push
merge
publish
deploy
infra apply
```

comme effets protégés.

---

## NFR-163 — Reconciliation externe

**Priorité : COULD**

Un coding-agent adapter doit pouvoir vérifier l’état réel du système distant après ambiguïté.

---

## NFR-164 — Compatibilité avec CLI / SDK / API

**Priorité : COULD**

Le modèle d’adapter ne doit pas supposer qu’un coding agent expose nécessairement un SDK Python.

Il doit pouvoir encapsuler :

```text
SDK
CLI
API
protocol
subprocess
```

selon le runtime.

---

# 21. SLO et objectifs de qualification initiaux

Les valeurs suivantes sont des **cibles de laboratoire**, pas des garanties contractuelles universelles.

## 21.1 Correctness

```text
duplicate protected effect due to internal recovery logic = 0
stale fenced write accepted by reference protected store = 0
invalid run transition accepted = 0
```

---

## 21.2 Recovery

Scénarios de qualification :

```text
worker SIGKILL
worker SIGTERM
worker freeze > lease TTL
PostgreSQL unavailable
PostgreSQL restored
network timeout during effect
```

Tous doivent produire un état explicite et récupérable.

---

## 21.3 Observability

Cible :

```text
100 % des changements critiques de run
100 % des changements d’ownership
100 % des effects protégés
100 % des approvals
```

doivent pouvoir produire un événement observable/auditable.

---

## 21.4 Concurrency

Aucun test multi-worker ne doit produire deux ownerships actifs acceptés simultanément pour la même ressource protégée.

---

# 22. Matrice de traçabilité NFR ↔ domaines fonctionnels

| Domaine NFR | Exigences fonctionnelles principalement concernées |
|---|---|
| Fiabilité | FR-010 à FR-075 |
| Résilience | FR-040 à FR-045, FR-140 à FR-142 |
| Effect safety | FR-060 à FR-075 |
| Disponibilité | FR-040 à FR-045, FR-080 à FR-087 |
| Performance | toutes |
| Scalabilité | FR-080 à FR-088 |
| Coordination | FR-080 à FR-088 |
| Sécurité | FR-050 à FR-075, FR-120 à FR-134 |
| Observabilité | FR-100 à FR-115 |
| Audit | FR-100 à FR-103 |
| Portabilité | FR-001 à FR-004, FR-120 à FR-134 |
| Maintenabilité | toutes |
| Testabilité | toutes |
| Exploitabilité | FR-110 à FR-115, FR-140 à FR-144 |
| Coding agents | FR-130 à FR-134 |

---

# 23. Critères bloquants avant qualification production

PyAgentsKit ne doit pas être considéré prêt pour une exploitation production si l’un des points suivants reste non démontré :

```text
1. reprise réelle après crash
2. takeover multi-worker
3. fencing effectif
4. absence de replay implicite
5. reconciliation d’un effet ambigu
6. PostgreSQL réel
7. graceful shutdown
8. safe degradation sur perte DB
9. métriques de leases
10. audit des changements d’ownership
11. tests multi-processus
12. tests SIGTERM/SIGKILL
13. health/readiness
14. runbooks minimum
```

---

# 24. Non-objectifs non fonctionnels

PyAgentsKit ne cherche pas à garantir universellement :

```text
zero downtime absolu
exactly-once absolu sur tout système externe
latence temps réel stricte
absence totale de panne
disaster recovery d’un cloud complet
HA du PostgreSQL lui-même
sécurité de l’infrastructure sous-jacente
qualité des décisions du LLM
correction du code généré par un coding agent
```

Ces responsabilités appartiennent soit au système externe, soit à l’infrastructure, soit à l’application.

---

# 25. Definition of Done non fonctionnelle

La baseline non fonctionnelle est considérée satisfaite lorsque :

1. les invariants de cohérence résistent aux tests de crash ;
2. l’exécution distribuée résiste aux scénarios de concurrence ;
3. les workers obsolètes sont rendus inoffensifs par fencing ;
4. les effets ambigus sont réconciliables ;
5. le backend PostgreSQL est qualifié en conditions réelles ;
6. l’état critique n’est pas uniquement local ;
7. health et readiness sont exploitables ;
8. métriques, logs, traces et audit sont disponibles ;
9. les migrations sont versionnées ;
10. les suites de tests incluent multi-processus et fault injection ;
11. le core reste indépendant des frameworks et coding agents ;
12. le framework peut être exploité sans dépendance SaaS obligatoire ;
13. les choix de TTL/heartbeat sont documentés ;
14. les incidents principaux disposent d’un runbook.

---

# 26. Résumé

Les exigences non fonctionnelles définissent la qualité que PyAgentsKit doit apporter aux runtimes d’agents.

Le principe directeur est :

> **PyAgentsKit doit échouer de manière explicite et sûre plutôt que continuer dans un état dont il ne peut plus garantir la cohérence.**

La production readiness repose donc sur :

```text
CORRECTNESS
RESILIENCE
EFFECT SAFETY
DISTRIBUTED COORDINATION
SECURITY
OBSERVABILITY
AUDITABILITY
PORTABILITY
TESTABILITY
OPERABILITY
```

Le document suivant devra fixer les règles qui structurent tous les choix de conception :

```text
../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md
```
