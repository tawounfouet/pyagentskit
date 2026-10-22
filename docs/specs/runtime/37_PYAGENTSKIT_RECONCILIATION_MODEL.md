# PyAgentsKit — Reconciliation Model

**Document :** `../runtime/37_PYAGENTSKIT_RECONCILIATION_MODEL.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Domain & Reliability Specification  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../runtime/36_PYAGENTSKIT_RECOVERY_PLANNER_SPECIFICATION.md`
- `../operations/38_PYAGENTSKIT_TEST_STRATEGY.md`
- `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`

---

# 1. Objet

Ce document définit le **modèle canonique de reconciliation de PyAgentsKit V2**.

La reconciliation répond au problème suivant :

> **Que doit faire PyAgentsKit lorsqu’une action externe a peut-être été appliquée, mais que le système ne possède pas encore de preuve durable suffisante pour affirmer son succès ou son échec ?**

Exemple classique :

```text
PyAgentsKit
   │
   ├── POST external API
   │
   ├── request reaches provider
   │
   ├── provider commits action
   │
   └── connection dies before response
```

Le système interne sait qu’une action a été tentée.

Il ne sait pas avec certitude :

```text
whether external reality changed
```

Cette situation ne doit jamais être aplatie en :

```text
FAILED
```

ni automatiquement relancée.

---

# 2. Principe fondamental

> **Reconciliation is the process of re-establishing external truth after internal certainty has been lost.**

La reconciliation n’est pas un retry.

```text
Retry
=
attempt action again

Reconciliation
=
inspect reality before deciding whether another action is safe
```

---

# 3. Reconciliation != Retry

La distinction est centrale.

```text
UNKNOWN
→ Retry
```

peut produire :

```text
duplicate payment
duplicate PR
double deployment
duplicate message
duplicate provisioning
```

La chaîne correcte est :

```text
UNKNOWN
→ Reconciliation
→ Evidence
→ Resolution
→ Optional Retry
```

---

# 4. Reconciliation != Compensation

```text
Reconciliation
=
discover what happened

Compensation
=
create a new Effect intended to counteract a confirmed prior Effect
```

Une compensation ne doit jamais être utilisée pour “annuler une ambiguïté”.

---

# 5. Reconciliation != Rollback

Une transaction DB peut rollback.

Le monde externe :

```text
GitHub
AWS
ERP
payment provider
email provider
```

ne rollback pas avec la transaction PostgreSQL locale.

---

# 6. Reconciliation != Polling

Polling est un mécanisme possible.

Reconciliation est le modèle métier.

```text
polling
query by key
webhook
operator evidence
```

peuvent tous contribuer à la reconciliation.

---

# 7. Pourquoi le modèle est nécessaire

Dans un système distribué :

```text
request
response
state
```

ne sont pas atomiques.

Les principaux crash windows sont :

```text
W1 — before durable intent
W2 — after durable intent, before send
W3 — after send, before response
W4 — after response, before durable outcome
W5 — after durable outcome, before Run progress
```

La reconciliation est principalement requise pour :

```text
W3
W4
```

---

# 8. W3

```text
send happened
response missing
```

Le provider peut avoir :

```text
applied
rejected
ignored
partially applied
```

---

# 9. W4

```text
provider response received
local process crashes
before durable outcome commit
```

L’action a potentiellement réussi mais PyAgentsKit ne possède pas encore la preuve durable.

---

# 10. Canonical Effect States

Le modèle cible utilise :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

# 11. UNKNOWN

`UNKNOWN` signifie :

> **The external outcome cannot currently be established with sufficient confidence.**

Ce n’est ni succès ni échec.

---

# 12. RECONCILIATION_REQUIRED

`RECONCILIATION_REQUIRED` signifie :

> **Normal execution cannot safely proceed until a reconciliation decision has been attempted or completed.**

Selon l’implémentation finale, ce statut peut être :

```text
Effect state
or
explicit blocker/case state
```

mais la sémantique reste distincte.

---

# 13. Reconciliation Aggregate

Objet central :

```text
ReconciliationCase
```

Il représente un dossier durable de recherche de vérité externe.

---

# 14. ReconciliationCase Identity

```text
reconciliation_case_id
effect_id
tenant_id
```

---

# 15. ReconciliationCase Core Fields

Proposition :

```text
id
tenant_id
effect_id
status
strategy
attempt_count
next_check_at
opened_at
updated_at
resolved_at
resolution
confidence
manual_reason
version
```

---

# 16. ReconciliationCase Status

États proposés :

```text
OPEN
CHECKING
WAITING_RETRY
MANUAL_REVIEW
RESOLVED
CANCELLED
```

---

# 17. OPEN

Le dossier existe, aucune vérification active en cours.

---

# 18. CHECKING

Une tentative de vérification externe est active.

---

# 19. WAITING_RETRY

La dernière vérification n’est pas concluante mais un nouveau check ultérieur est autorisé.

---

# 20. MANUAL_REVIEW

L’automatisation ne peut pas déterminer le résultat avec suffisamment de confiance.

---

# 21. RESOLVED

La réalité externe a été établie selon le niveau de preuve requis.

---

# 22. CANCELLED

Le dossier est explicitement abandonné, généralement parce qu’un autre mécanisme a rendu la reconciliation sans objet.

Doit rester exceptionnel.

---

# 23. Reconciliation Resolution

Valeurs canoniques :

```text
CONFIRMED_SUCCESS
CONFIRMED_FAILURE
STILL_UNKNOWN
NOT_FOUND
MANUAL_REQUIRED
```

---

# 24. CONFIRMED_SUCCESS

Preuve suffisante que l’Effect a été appliqué.

Conséquence typique :

```text
Effect → SUCCEEDED
```

---

# 25. CONFIRMED_FAILURE

Preuve suffisante que l’Effect n’a pas été appliqué ou que le provider l’a rejeté de manière définitive.

Conséquence typique :

```text
Effect → FAILED
```

---

# 26. STILL_UNKNOWN

L’investigation automatique n’a pas réduit l’ambiguïté.

---

# 27. NOT_FOUND

Le système externe ne trouve pas l’objet attendu.

Attention :

```text
NOT_FOUND
!=
CONFIRMED_FAILURE
```

dans tous les connectors.

---

# 28. MANUAL_REQUIRED

Le système reconnaît explicitement :

```text
automation cannot safely decide
```

---

# 29. Evidence Model

Objet :

```text
ReconciliationEvidence
```

---

# 30. Evidence Fields

Proposition :

```text
evidence_id
case_id
source
kind
observed_at
provider_timestamp
external_reference
payload_digest
summary
confidence
raw_artifact_ref
```

---

# 31. Evidence Source

Exemples :

```text
PROVIDER_API
WEBHOOK
AUDIT_LOG
REMOTE_REF
BUSINESS_KEY_LOOKUP
OPERATOR
SECONDARY_SYSTEM
```

---

# 32. Evidence Kind

Exemples :

```text
OBJECT_EXISTS
OBJECT_ABSENT
STATUS_MATCH
STATUS_CONFLICT
SHA_MATCH
IDEMPOTENCY_MATCH
PROVIDER_EVENT
MANUAL_DOCUMENT
```

---

# 33. Evidence Is Immutable

Une evidence persistée est :

```text
append-oriented
```

Elle n’est pas modifiée pour “corriger l’histoire”.

---

# 34. Evidence Confidence

Le modèle peut porter un niveau qualitatif :

```text
WEAK
MEDIUM
STRONG
AUTHORITATIVE
```

---

# 35. AUTHORITATIVE Evidence

Exemples :

```text
provider exact operation ID
remote git ref == expected SHA
payment transaction ID confirmed settled
deployment ID exact status
```

---

# 36. STRONG Evidence

Exemple :

```text
unique business key match
```

avec faible risque de collision.

---

# 37. MEDIUM Evidence

Exemple :

```text
matching payload + approximate timestamp
```

mais sans identifiant unique.

---

# 38. WEAK Evidence

Exemple :

```text
human assumption
log line
approximate text match
```

Ne devrait pas suffire seul pour des Effects critiques.

---

# 39. Evidence Policy

Chaque Effect type / Connector peut définir :

```text
minimum confidence required
```

pour une résolution automatique.

---

# 40. Evidence Hierarchy

Préférence :

```text
provider authoritative identifier
>
idempotency/business key
>
immutable external state
>
provider event
>
logs
>
operator assumption
```

---

# 41. Reconciliation Strategy

Value Object / enum :

```text
ReconciliationStrategy
```

---

# 42. Strategy Types

```text
BY_EXTERNAL_ID
BY_IDEMPOTENCY_KEY
BY_BUSINESS_KEY
BY_REMOTE_STATE
BY_PROVIDER_EVENT
BY_COMPOSITE_EVIDENCE
MANUAL_ONLY
```

---

# 43. BY_EXTERNAL_ID

Le meilleur cas.

Exemple :

```text
deployment_id
payment_id
pr_number
message_id
```

---

# 44. BY_IDEMPOTENCY_KEY

Le provider permet de retrouver une opération via la même clé.

---

# 45. BY_BUSINESS_KEY

Exemples :

```text
invoice reference
order number
version tag
```

---

# 46. BY_REMOTE_STATE

Exemple Git :

```text
remote branch SHA
```

---

# 47. BY_PROVIDER_EVENT

Un webhook/event log du provider peut confirmer l’action.

---

# 48. BY_COMPOSITE_EVIDENCE

Plusieurs preuves faibles/moyennes combinées.

À utiliser prudemment.

---

# 49. MANUAL_ONLY

Le provider ne permet pas de vérifier automatiquement.

Dans ce cas :

```text
manual intervention is first-class
```

---

# 50. ReconciliationPort

Port canonique :

```python
class ReconciliationPort(Protocol):
    async def reconcile(
        self,
        effect: Effect,
        context: ReconciliationContext,
    ) -> ReconciliationResult:
        ...
```

---

# 51. ReconciliationContext

Peut inclure :

```text
tenant
connector descriptor
effect fingerprint
external reference
idempotency key
attempt history
deadline
security context
```

---

# 52. ReconciliationResult

Proposition :

```text
resolution
evidence[]
external_reference
provider_status
confidence
retry_after
reason
```

---

# 53. ReconciliationPort Rule

Le Port :

```text
does not mutate Effect
```

Il rapporte la réalité observée.

L’Application Service décide ensuite la transition durable.

---

# 54. Why This Separation

Cela sépare :

```text
observation
from
decision
```

et facilite :

```text
testing
audit
manual override review
```

---

# 55. Application Service

Use case :

```text
ReconcileEffect
```

---

# 56. ReconcileEffect Flow

```text
load Effect
load/open ReconciliationCase
verify authority
select strategy
invoke ReconciliationPort
persist evidence
evaluate resolution
transition Effect if justified
update case
audit
unblock Run if possible
```

---

# 57. Authority Before Reconciliation

Une reconciliation automatique peut nécessiter :

```text
valid Lease
```

selon qu’elle est purement read-only ou qu’elle modifie des systèmes.

---

# 58. Read-Only Reconciliation

Si seulement :

```text
GET provider status
```

un fencing token peut ne pas être requis côté provider.

Mais l’écriture du résultat durable reste protégée par concurrency/versioning.

---

# 59. Reconciliation with Side Effects

Si la reconciliation doit :

```text
repair
tag
finalize
cancel
```

alors cette action est un nouvel :

```text
Effect
```

---

# 60. Reconciliation Must Not Hide Effects

Toute action externe de “réparation” doit avoir :

```text
its own Effect identity
approval
idempotency
audit
```

si applicable.

---

# 61. Reconciliation Decision Table

| Observed Reality | Resolution | Effect |
|---|---|---|
| exact external object exists and matches | CONFIRMED_SUCCESS | SUCCEEDED |
| provider definitively rejected/not applied | CONFIRMED_FAILURE | FAILED |
| no object found but eventual consistency possible | STILL_UNKNOWN | UNKNOWN |
| conflicting evidence | MANUAL_REQUIRED | UNKNOWN/blocked |
| provider unavailable | STILL_UNKNOWN | UNKNOWN |
| external object exists but payload differs | MANUAL_REQUIRED | UNKNOWN |

---

# 62. NOT_FOUND Semantics

`NOT_FOUND` doit être interprété par Connector.

Exemple GitHub :

```text
PR not found
```

peut signifier :

```text
never created
deleted
wrong repository
eventual consistency
```

---

# 63. Provider Eventual Consistency

Un provider peut répondre temporairement :

```text
404
```

après une création réellement acceptée.

Le modèle doit pouvoir :

```text
wait
recheck
```

sans conclure trop vite.

---

# 64. Reconciliation Retry

Le check lui-même peut être répété.

Ceci est différent du retry de l’Effect.

---

# 65. Reconciliation Backoff

Peut utiliser :

```text
exponential backoff
jitter
provider Retry-After
```

---

# 66. Reconciliation Attempt Budget

Chaque stratégie doit définir :

```text
max attempts
max elapsed time
```

---

# 67. After Attempt Budget Exhausted

Le case passe typiquement à :

```text
MANUAL_REVIEW
```

---

# 68. Reconciliation Deadline

Un business deadline peut forcer :

```text
manual escalation
```

avant exhaustion technique.

---

# 69. Polling Safety

Polling doit être :

```text
read-only
bounded
rate-limit aware
```

---

# 70. Polling Capacity

Le system doit éviter :

```text
reconciliation storm
```

après incident majeur.

---

# 71. Reconciliation Queue

Peut être priorisée séparément des nouveaux Runs.

---

# 72. Priority Classes

Exemples :

```text
P0 high-risk irreversible Effect
P1 user-blocking
P2 ordinary
P3 background verification
```

---

# 73. Reconciliation and RecoveryPlanner

`RecoveryPlanner` doit détecter :

```text
Effect.UNKNOWN
```

et retourner :

```text
RECONCILE_EFFECT
```

avant :

```text
RESUME_RUNTIME
```

si l’Effect bloque la sécurité.

---

# 74. Recovery Ordering

Ordre :

```text
authority
→ approvals
→ unresolved Effects
→ runtime
```

---

# 75. Why Reconcile Before Resume

Sinon le runtime pourrait :

```text
reissue tool call
```

sans savoir qu’il a déjà réussi.

---

# 76. Run Blocking

Un Run avec Effect UNKNOWN critique est généralement :

```text
WAITING
```

---

# 77. WAITING Reason

Exemple :

```text
WAITING
reason = EFFECT_RECONCILIATION
```

---

# 78. ReconciliationCase and Run

Un Run peut avoir :

```text
multiple ReconciliationCases
```

mais seuls certains peuvent bloquer progression.

---

# 79. Blocking vs Non-Blocking Reconciliation

Certaines reconciliations sont :

```text
blocking
```

d’autres :

```text
background verification
```

selon risque.

---

# 80. Risk-Based Reconciliation

Critères :

```text
irreversibility
financial impact
security impact
external visibility
legal impact
duplication cost
```

---

# 81. Low-Risk Example

Envoi analytics non critique.

Peut tolérer :

```text
eventual resolution
```

---

# 82. High-Risk Example

```text
payment
git push to protected branch
production deployment
terraform apply
user deletion
```

Doit bloquer progression tant que vérité externe non établie.

---

# 83. Manual Resolution

Objet possible :

```text
ManualReconciliationDecision
```

---

# 84. Manual Resolution Fields

```text
decision
actor/principal
reason
evidence_refs
decided_at
policy_version
```

---

# 85. Manual Resolution Security

Une résolution manuelle doit exiger :

```text
authorization
```

et potentiellement :

```text
two-person rule
```

en High Assurance.

---

# 86. Manual Resolution != Approval

Une Approval autorise une action.

Une ManualReconciliationDecision détermine ce qui s’est déjà passé.

Ce sont deux actes distincts.

---

# 87. Manual Resolution Audit

Obligatoire.

---

# 88. Manual CONFIRMED_SUCCESS

Ne doit être autorisé que si l’opérateur fournit :

```text
evidence
```

suffisante selon policy.

---

# 89. Manual CONFIRMED_FAILURE

Même exigence.

---

# 90. Manual STILL_UNKNOWN

Valide si la réalité reste impossible à établir.

Le Run peut rester bloqué ou être annulé selon business policy.

---

# 91. Cancellation and UNKNOWN

Annuler le Run :

```text
does not resolve Effect UNKNOWN
```

Le dossier de reconciliation peut rester ouvert.

---

# 92. Why

La réalité externe existe indépendamment du cycle de vie du Run.

---

# 93. Retention

Les ReconciliationCases doivent être retenus au moins aussi longtemps que :

```text
associated Effect audit requirements
```

---

# 94. Persistence Model

Table cible possible :

```text
reconciliation_cases
```

---

# 95. Table Fields

Conceptuellement :

```text
id
tenant_id
effect_id
status
strategy
attempt_count
next_check_at
resolution
confidence
opened_at
resolved_at
version
```

---

# 96. Evidence Persistence

Deux options :

```text
reconciliation_evidence table
or
append-only evidence JSON/document refs
```

Préférence pour modèle explicitement auditable si volume raisonnable.

---

# 97. Unique Constraints

Candidat :

```text
one active reconciliation case per Effect
```

si le modèle métier le permet.

---

# 98. Optimistic Concurrency

ReconciliationCase doit posséder :

```text
version
```

pour éviter double résolution.

---

# 99. Resolution Race

Deux workers peuvent réconcilier en parallèle.

Un seul commit terminal doit gagner.

---

# 100. Reconciliation Lease

Option :

```text
reconciliation resource lease
```

pour limiter travail concurrent.

Mais correctness ne doit pas dépendre uniquement de l’absence de concurrence.

---

# 101. Idempotent Resolution

Appliquer deux fois la même résolution ne doit pas créer deux nouveaux Effects ni doubler l’audit logique.

---

# 102. External Reference Evolution

La reconciliation peut découvrir un :

```text
external_reference
```

qui n’était pas connu initialement.

Il peut alors être attaché durablement à l’Effect.

---

# 103. External Reference Conflict

Si une autre external reference est déjà stockée :

```text
conflict
```

nécessitant review.

---

# 104. Fingerprint Matching

Le provider object retrouvé doit être comparé au :

```text
Effect fingerprint
```

lorsque possible.

---

# 105. Exact Match

```text
external object payload
≈
effect intended payload
```

---

# 106. Partial Match

Si certains champs sont mutable externally :

```text
canonical matching fields
```

doivent être définis par Connector.

---

# 107. Connector-Specific Matcher

Concept :

```text
EffectEvidenceMatcher
```

ou logique interne Connector.

---

# 108. Generic HTTP Limitation

Un generic HTTP Connector peut ne pas être capable de réconcilier automatiquement une POST arbitraire.

Il doit donc annoncer :

```text
reconciliation capability = limited / none
```

---

# 109. Connector Capability

Candidat :

```text
RECONCILIATION
```

ou granularité :

```text
RECONCILE_BY_ID
RECONCILE_BY_IDEMPOTENCY
```

---

# 110. Runtime Reconciliation

Un Runtime Adapter peut également aider à inspecter :

```text
runtime tool invocation history
```

mais cette information n’est pas nécessairement authoritative pour le monde externe.

---

# 111. Runtime Evidence

Peut être :

```text
supporting evidence
```

pas automatiquement :

```text
external truth
```

---

# 112. Audit Evidence

Audit PyAgentsKit indique :

```text
what PyAgentsKit attempted
```

pas forcément :

```text
what provider committed
```

---

# 113. Logs Evidence

Même distinction.

---

# 114. Provider Audit Trail

Si provider fournit un audit log avec operation ID :

```text
strong evidence
```

---

# 115. Webhook Evidence

Un webhook signé peut être :

```text
strong evidence
```

selon provider.

---

# 116. External Consistency Window

Chaque Connector peut définir :

```text
consistency_window
```

avant qu’un `NOT_FOUND` soit considéré plus fort.

---

# 117. Reconciliation Scheduler

Peut fonctionner via :

```text
background worker
external scheduler
queue
```

mais ne doit pas devenir un scheduler généraliste.

---

# 118. Scheduling Fields

```text
next_check_at
attempt_count
last_checked_at
```

---

# 119. Reconciliation Backlog Metrics

```text
reconciliation_open_total
reconciliation_manual_total
reconciliation_oldest_age_seconds
reconciliation_attempts_total
reconciliation_resolved_total
```

---

# 120. Resolution Metrics

```text
confirmed_success_total
confirmed_failure_total
still_unknown_total
manual_required_total
```

---

# 121. Time-to-Reconcile

Metric :

```text
resolved_at - opened_at
```

---

# 122. High UNKNOWN Rate

Peut signaler :

```text
provider instability
timeouts too aggressive
adapter bug
network issue
```

---

# 123. High NOT_FOUND Rate

Peut signaler :

```text
bad lookup key
eventual consistency
wrong tenant/account
provider behavior change
```

---

# 124. Reconciliation SLO

Par risk class.

Exemple :

```text
critical unresolved Effects
must be surfaced immediately
```

mais résolution dépend du provider.

---

# 125. No False SLO

Ne pas promettre :

```text
all UNKNOWN resolved in N seconds
```

si provider ne permet pas de l’établir.

---

# 126. Git Push Reconciliation

Intent :

```text
push commit SHA X to ref Y
```

Evidence :

```text
remote ref Y points to SHA X
```

Résolution :

```text
CONFIRMED_SUCCESS
```

---

# 127. Git Push Failure Evidence

Si remote ref reste à old SHA et provider confirme rejection :

```text
CONFIRMED_FAILURE
```

---

# 128. Git Push Conflict

Si remote ref pointe sur SHA Z :

```text
MANUAL_REQUIRED
```

ou connector-specific conflict.

---

# 129. PR Creation Reconciliation

Chercher par :

```text
head SHA
base branch
repository
provider idempotency metadata
```

---

# 130. PR Match

Si une PR unique correspond exactement :

```text
CONFIRMED_SUCCESS
```

---

# 131. PR Ambiguity

Deux PRs possibles :

```text
MANUAL_REQUIRED
```

---

# 132. Deployment Reconciliation

Chercher par :

```text
deployment id
release version
artifact digest
environment
```

---

# 133. Package Publish Reconciliation

Chercher :

```text
package
version
digest
```

---

# 134. Terraform Reconciliation

Très complexe.

Sources :

```text
Terraform state
cloud provider state
plan/apply metadata
```

Souvent :

```text
MANUAL_REQUIRED
```

si apply interrompu.

---

# 135. Payment Reconciliation

Chercher :

```text
provider transaction id
idempotency key
merchant reference
amount/currency
```

---

# 136. Messaging Reconciliation

Email/SMS providers peuvent fournir :

```text
message id
delivery status
```

---

# 137. Reconciliation by Fingerprint

Une fingerprint seule ne suffit pas toujours si plusieurs opérations identiques sont légitimes.

---

# 138. Business Key Uniqueness

Le Connector doit connaître si le business key est :

```text
globally unique
tenant unique
not unique
```

---

# 139. Temporal Correlation

Timestamp peut aider mais ne doit pas être unique preuve pour high-risk Effects.

---

# 140. Reconciliation Policy

Objet conceptuel :

```text
ReconciliationPolicy
```

---

# 141. Policy Fields

```text
strategy
automatic
max_attempts
max_elapsed
min_confidence
manual_after
blocking
```

---

# 142. Policy by Effect Type

Exemple :

```text
GitPush
→ BY_REMOTE_STATE

Payment
→ BY_IDEMPOTENCY_KEY

GenericHTTPPost
→ MANUAL_ONLY unless configured
```

---

# 143. Policy Versioning

La policy utilisée doit être traçable.

---

# 144. Changing Policy Mid-Case

Le case doit enregistrer :

```text
policy version at each decision
```

si policy dynamique.

---

# 145. Security Context Revalidation

Avant une résolution manuelle ou réparation :

```text
revalidate authorization
```

---

# 146. Approval Revalidation

La reconciliation elle-même ne nécessite pas forcément l’Approval initiale.

Mais toute nouvelle action externe peut en nécessiter une nouvelle.

---

# 147. Reconciliation and Authorization

Observer un système externe :

```text
requires connector credentials
```

mais ne signifie pas automatiquement qu’un humain est autorisé à résoudre le case.

---

# 148. Reconciliation and Fencing

Le résultat durable doit être écrit par un actor/worker autorisé.

Un stale worker ne doit pas pouvoir modifier l’Effect après takeover.

---

# 149. Stale Reconciliation Result

Si un worker termine un check après avoir perdu ownership :

```text
result may be recorded as evidence only if safe
```

mais transition d’autorité doit être protégée.

---

# 150. Compare-and-Swap

Utiliser version/CAS pour :

```text
Effect
ReconciliationCase
```

lors de résolution concurrente.

---

# 151. External Evidence Staleness

Une evidence peut devenir obsolète.

Exemple :

```text
deployment existed
then rolled back externally
```

La question de reconciliation porte sur :

```text
did the Effect apply?
```

pas forcément sur l’état actuel permanent.

---

# 152. Historical vs Current Truth

Distinguer :

```text
historical outcome
current external state
```

---

# 153. Example

Un PR a été créé puis supprimé.

Current lookup :

```text
NOT_FOUND
```

mais historical provider audit peut prouver :

```text
CONFIRMED_SUCCESS
```

---

# 154. Reconciliation Must Ask Correct Question

Pas :

```text
"Does object exist now?"
```

mais :

```text
"Did the intended Effect occur?"
```

---

# 155. Event-Sourced Providers

Provider event logs peuvent être particulièrement utiles pour vérité historique.

---

# 156. Provider Data Retention

Reconciliation doit tenir compte de la durée de rétention provider.

---

# 157. Late Reconciliation

Après expiration des données provider :

```text
manual evidence
```

peut être la seule option.

---

# 158. Reconciliation Escalation

Escalation stages :

```text
automatic check
repeated check
connector-specific advanced lookup
manual review
incident escalation
```

---

# 159. Incident Escalation

Si Effect à fort impact reste ambigu au-delà du seuil :

```text
incident
```

peut être ouvert.

---

# 160. Reconciliation and Incident Response

Document 42 couvre :

```text
RB-005 Effect UNKNOWN
```

Le modèle ici fournit les primitives métier utilisées par ce runbook.

---

# 161. Reconciliation and Production Qualification

Document 40 doit qualifier :

```text
timeout-after-send
provider contradictions
manual resolution
connector-specific evidence
```

---

# 162. Contract Testing

Le document 39 impose aux ReconciliationPorts :

```text
same canonical resolution semantics
```

---

# 163. ReconciliationPort Contract Scenarios

```text
RC-01 success confirmed
RC-02 failure confirmed
RC-03 still unknown
RC-04 not found
RC-05 provider unavailable
RC-06 contradictory evidence
RC-07 repeat same reconciliation
```

---

# 164. Idempotent Reconciliation Check

Même check répété ne doit pas :

```text
create duplicate case
duplicate evidence logically
duplicate Effect
```

---

# 165. Evidence Deduplication

Evidence peut avoir :

```text
source key
provider event id
digest
```

pour dedup.

---

# 166. Manual Evidence Upload

Si opérateur ajoute un document :

```text
store as Artifact
reference from Evidence
```

plutôt que gros blob dans DB.

---

# 167. Audit Model

Chaque action importante génère :

```text
AuditEvent
```

Exemples :

```text
case opened
check started
evidence added
resolution proposed
manual decision
Effect transitioned
case resolved
```

---

# 168. Audit vs Reconciliation Evidence

Audit :

```text
what PyAgentsKit did
```

Evidence :

```text
what supports conclusion about external reality
```

---

# 169. Data Minimization

Ne pas stocker plus de provider payload que nécessaire.

---

# 170. Sensitive Evidence

Peut contenir :

```text
PII
financial metadata
repository details
```

Doit suivre DataPolicy.

---

# 171. Encryption / Redaction

Appliquer selon storage/profile.

---

# 172. Reconciliation Read Model

Pour opérateurs :

```text
case id
Effect
risk
age
strategy
attempts
latest evidence
current resolution
blocking Run
```

---

# 173. Operator Timeline

Afficher :

```text
Effect intent
send attempt
failure
checks
evidence
manual actions
resolution
Run resume
```

---

# 174. Bulk Reconciliation

Possible après incident provider.

Mais doit être :

```text
bounded
prioritized
rate-limit aware
```

---

# 175. Bulk Safety

Ne pas lancer :

```text
unbounded parallel provider lookups
```

---

# 176. Recovery Storm Interaction

Après DB/provider outage :

```text
RecoveryPlanner
```

peut produire de nombreux `RECONCILE_EFFECT`.

Scheduler doit protéger le provider.

---

# 177. Reconciliation Worker Pool

Peut être spécialisé pour éviter d’affamer les Runs ordinaires.

---

# 178. Retry-After

Le provider peut fournir :

```text
Retry-After
```

qui alimente `next_check_at`.

---

# 179. Circuit Breaker

Peut protéger un provider indisponible.

Mais :

```text
circuit open
!=
Effect failure
```

---

# 180. Cancellation of Reconciliation

Un case peut être cancelled si :

```text
Effect superseded by authoritative manual determination
```

mais l’historique reste conservé.

---

# 181. Superseding Evidence

Nouvelle evidence peut contredire une ancienne.

Ne pas supprimer l’ancienne.

---

# 182. Contradictory Evidence

Doit généralement conduire à :

```text
MANUAL_REVIEW
```

---

# 183. Confidence Aggregation

Éviter un score magique global sans modèle clair.

Préférer :

```text
explicit evidence rules
```

par Connector/Effect type.

---

# 184. Deterministic Resolution Rules

Pour production, une même collection d’evidence + même policy devrait produire :

```text
same resolution
```

---

# 185. Reconciliation Domain Service

Possible :

```text
ReconciliationDecisionService
```

qui transforme :

```text
Evidence + Policy
→ ResolutionDecision
```

---

# 186. Port vs Domain Service

Le Port observe.

Le Domain Service décide.

---

# 187. Connector Adapter

Le Connector fournit les connaissances provider :

```text
lookup
matching
status mapping
```

---

# 188. Application Service

Orchestre :

```text
load
observe
decide
persist
audit
unblock
```

---

# 189. Separation of Concerns

```text
Connector
→ provider semantics

ReconciliationPort
→ observation interface

Domain Service
→ canonical decision

Application
→ orchestration

Repository
→ durability
```

---

# 190. State Transition Rules

### UNKNOWN → SUCCEEDED

Seulement si :

```text
CONFIRMED_SUCCESS
```

avec evidence suffisante.

### UNKNOWN → FAILED

Seulement si :

```text
CONFIRMED_FAILURE
```

avec evidence suffisante.

### UNKNOWN → UNKNOWN

Si :

```text
STILL_UNKNOWN
```

### UNKNOWN → blocked/manual

Si :

```text
MANUAL_REQUIRED
```

---

# 191. No Direct UNKNOWN → NOT_STARTED

Interdit.

---

# 192. No Direct UNKNOWN → STARTED Retry

Interdit sans résolution/policy.

---

# 193. Retry After Confirmed Failure

Si business/policy autorise :

```text
new attempt
```

peut être créé.

---

# 194. Retry Identity

Selon modèle, un retry peut être :

```text
same logical Effect attempt
or
new Effect attempt
```

mais doit rester auditably distinct.

---

# 195. EffectAttempt

Concept futur possible si plusieurs tentatives doivent être modélisées explicitement.

Ne pas introduire prématurément si `Effect` + attempt metadata suffisent.

---

# 196. Reconciliation After Success

Même un Effect `SUCCEEDED` peut parfois être vérifié périodiquement.

Mais cela relève plutôt de :

```text
drift detection
```

pas du recovery path primaire.

---

# 197. Drift Detection

Adjacent mais distinct.

```text
reconciliation
=
what happened?

drift detection
=
is current state still what we expect?
```

---

# 198. Reconciliation and Read Repair

Ne pas modifier le provider pour “aligner” sans créer nouvel Effect.

---

# 199. Example — External User Creation

Intent :

```text
create user email=x
```

Timeout.

Reconciliation :

```text
lookup by external unique email
```

Si exact match créé dans fenêtre et payload compatible :

```text
CONFIRMED_SUCCESS
```

---

# 200. Example — Non-Unique Search

Si plusieurs users match :

```text
MANUAL_REQUIRED
```

---

# 201. Example — Email Send

Intent :

```text
send email message digest X
```

Provider message ID absent.

Si provider search ne supporte pas correlation :

```text
MANUAL_REQUIRED or STILL_UNKNOWN
```

Ne pas renvoyer automatiquement si duplication est problématique.

---

# 202. Example — Slack Message

Si client-generated id supported :

```text
reconcile by client id
```

sinon limitation explicite.

---

# 203. Example — Database Connector

Si operation ciblait un système transactionnel avec request ID :

```text
query request ledger
```

---

# 204. Example — Cloud Resource Provisioning

Chercher :

```text
resource tags
request token
resource ID
desired properties
```

---

# 205. Tags as Reconciliation Aid

PyAgentsKit peut encourager des tags :

```text
pyagentskit_effect_id
run_id
idempotency_key
```

si provider permet metadata.

---

# 206. Metadata Injection

Doit respecter :

```text
privacy
provider limits
security
```

---

# 207. Correlation Metadata as Strategic Capability

Les Connectors devraient exploiter les primitives provider permettant de retrouver facilement un Effect.

---

# 208. Connector Design Rule

Lors de BUILD d’un adapter :

```text
design reconciliation before write API
```

Pas après.

---

# 209. Reconciliation-First Connector Review

Checklist :

```text
Can we retrieve by external ID?
Can we send idempotency key?
Can we attach metadata?
Can we query history?
Can we distinguish rejection from absence?
What is consistency delay?
```

---

# 210. Connector Qualification

Un Connector write critique ne peut pas atteindre niveau production-qualified sans :

```text
documented reconciliation strategy
```

ou limitation MANUAL_ONLY explicite.

---

# 211. Reconciliation Capability Levels

Proposition :

```text
R0 — None
R1 — Manual Only
R2 — Basic Lookup
R3 — Deterministic Automated Reconciliation
R4 — Production Qualified
```

---

# 212. R0

Aucune voie de reconciliation.

Très risqué pour write Effects.

---

# 213. R1

Opérateur peut vérifier manuellement.

---

# 214. R2

Lookup disponible mais ambiguïté possible.

---

# 215. R3

Lookup + strong unique evidence.

---

# 216. R4

R3 + failure/production qualification.

---

# 217. Public Connector Metadata

Exposer :

```text
reconciliation_level
```

dans descriptor.

---

# 218. API Surface

Possibles commandes publiques :

```text
reconcile_effect(effect_id)
get_reconciliation_case(case_id)
resolve_reconciliation_manually(...)
```

---

# 219. Query Surface

```text
list_open_reconciliations()
get_reconciliation_timeline()
```

---

# 220. Admin Surface

Dangerous operation :

```text
manual resolution
```

doit être fortement protégée.

---

# 221. CLI Future

Exemples :

```text
pyagentskit effect reconcile <effect_id>
pyagentskit reconciliation show <case_id>
pyagentskit reconciliation resolve <case_id>
```

---

# 222. Dry-Run Reconciliation

Peut être utile :

```text
query provider
show proposed resolution
do not persist transition
```

---

# 223. Manual Resolve Dry Run

Afficher :

```text
current Effect
evidence
proposed outcome
impacted Run
```

---

# 224. Reconciliation Errors

Canonical errors candidats :

```text
ReconciliationUnavailable
ReconciliationAmbiguous
ReconciliationConflict
EvidenceInsufficient
ManualResolutionRequired
```

---

# 225. Provider Errors

Doivent rester derrière Connector/Port.

---

# 226. Security Threats

Reconciliation peut être attaquée via :

```text
forged provider response
wrong tenant
stale credentials
operator abuse
tampered evidence
```

---

# 227. Signed Webhooks

Si disponible :

```text
signature verification
```

avant d’accepter comme evidence.

---

# 228. Provider Account Binding

Un external reference doit être lié au bon :

```text
tenant
account
connector instance
```

---

# 229. Cross-Tenant Reconciliation

Interdit.

---

# 230. Manual Evidence Tampering

Artifact checksum/provenance peut renforcer la confiance.

---

# 231. Reconciliation and Privacy

Provider payloads ne doivent pas être copiés en entier si un digest/résumé suffit.

---

# 232. Performance Model

Reconciliation est généralement I/O-bound.

Capacité limitée par :

```text
provider rate limits
latency
backlog
```

---

# 233. Database Indexes

Candidats :

```text
reconciliation_cases(status, next_check_at)
reconciliation_cases(effect_id)
reconciliation_cases(tenant_id, status)
```

---

# 234. Scan Pattern

```text
WHERE status IN (OPEN, WAITING_RETRY)
AND next_check_at <= now()
ORDER BY priority, next_check_at
LIMIT N
```

---

# 235. SKIP LOCKED

Peut être utilisé dans worker pool PostgreSQL pour claim work.

Mais :

```text
claim != business authority
```

---

# 236. Case Claiming

Peut éviter travail dupliqué.

La résolution doit malgré tout être concurrency-safe.

---

# 237. Observability

Traces :

```text
reconciliation.case
reconciliation.check
reconciliation.resolve
```

---

# 238. Metrics Labels

Éviter high cardinality :

```text
effect_id
case_id
```

comme labels métriques.

---

# 239. Logging

Logs structurés :

```text
case_id
effect_id
connector
strategy
resolution
```

---

# 240. Alerts

Alertes possibles :

```text
reconciliation backlog spike
old critical case
manual backlog
provider reconciliation error rate
```

---

# 241. Operational Dashboard

Afficher :

```text
open by connector
open by risk
oldest
manual review
resolution rate
mean/p95 resolution time
```

---

# 242. Incident Correlation

Un pic d’UNKNOWN + reconciliation peut révéler un incident provider/network.

---

# 243. Testing Strategy

Unit :

```text
decision rules
evidence policies
```

Contract :

```text
ReconciliationPort
```

Integration :

```text
real provider sandbox
```

Failure :

```text
timeout after send
contradictory evidence
```

---

# 244. P0 Tests

```text
REC-TST-001 timeout-after-send
REC-TST-002 confirmed success no replay
REC-TST-003 confirmed failure allows policy decision
REC-TST-004 NOT_FOUND not auto-failure
REC-TST-005 provider unavailable remains unknown
REC-TST-006 conflicting evidence → manual
REC-TST-007 concurrent resolution one winner
REC-TST-008 stale worker cannot resolve authoritatively
```

---

# 245. Property Tests

Possibles :

```text
resolved case cannot return to OPEN
terminal resolution stable
evidence append-only
```

---

# 246. Contract Tests

Chaque provider-specific adapter doit passer les mêmes canonical result semantics.

---

# 247. Production Qualification

Au moins un vrai Connector à write critique doit démontrer :

```text
W3
W4
provider lookup
resolution
Run resume
```

---

# 248. GitHub Flagship Scenario

```text
Run
→ code edit
→ commit SHA A
→ Approval for SHA A
→ git push
→ response lost
→ Effect UNKNOWN
→ worker crash
→ takeover
→ remote ref lookup
→ SHA A found
→ CONFIRMED_SUCCESS
→ Effect SUCCEEDED
→ Run resumes
→ no second push
```

---

# 249. This Scenario Proves

```text
Effect safety
Approval scope
distributed takeover
fencing
reconciliation
recovery
```

dans un seul use case.

---

# 250. Reconciliation Invariants

```text
REC-INV-01 UNKNOWN is not failure.
REC-INV-02 Reconciliation happens before dangerous retry.
REC-INV-03 Evidence is durable and auditable.
REC-INV-04 No success without sufficient evidence.
REC-INV-05 No failure without sufficient evidence.
REC-INV-06 NOT_FOUND has connector-specific meaning.
REC-INV-07 Manual intervention is a valid terminal operational outcome.
REC-INV-08 Reconciliation does not itself hide new external Effects.
REC-INV-09 Stale workers cannot authoritatively resolve cases.
REC-INV-10 Resolution is concurrency-safe and idempotent.
REC-INV-11 Runtime evidence is not automatically external truth.
REC-INV-12 Provider-specific evidence stays behind canonical semantics.
REC-INV-13 Run cancellation does not erase unresolved external reality.
REC-INV-14 Restore may reopen ambiguity and requires reconciliation.
REC-INV-15 Reconciliation policy is versioned/auditable where dynamic.
```

---

# 251. Anti-Pattern — Timeout Means Failed

Interdit.

---

# 252. Anti-Pattern — Blind Retry

Interdit pour UNKNOWN.

---

# 253. Anti-Pattern — 404 Means Never Happened

Interdit sans connector-specific proof.

---

# 254. Anti-Pattern — Log Means Truth

Logs ne prouvent pas forcément la réalité provider.

---

# 255. Anti-Pattern — Runtime Says Success

Runtime success n’est pas nécessairement external success.

---

# 256. Anti-Pattern — Manual Guess

Une résolution manuelle sans evidence suffisante doit être interdite par policy high assurance.

---

# 257. Anti-Pattern — Compensation Before Reconciliation

Peut doubler l’erreur.

---

# 258. Anti-Pattern — Delete UNKNOWN Record

Interdit.

---

# 259. Anti-Pattern — Reconciliation Without Tenant Scope

Risque cross-tenant.

---

# 260. Anti-Pattern — Provider-Specific State in Domain

Le Domain reçoit :

```text
canonical evidence/resolution
```

pas une classe SDK.

---

# 261. Anti-Pattern — Unlimited Polling

Doit être borné.

---

# 262. Anti-Pattern — Conflate Drift with Reconciliation

Concepts distincts.

---

# 263. Architecture Placement

```text
domain/
  effects/
    reconciliation.py

application/
  effects/
    reconcile_effect.py

adapters/
  connectors/
    ...
```

---

# 264. Domain Objects

Candidats :

```text
ReconciliationCase
ReconciliationEvidence
ReconciliationResolution
ReconciliationStrategy
ReconciliationPolicy
```

---

# 265. Application Use Cases

```text
OpenReconciliationCase
ReconcileEffect
ResolveReconciliationManually
ListPendingReconciliations
```

---

# 266. Outbound Ports

```text
ReconciliationRepository
ReconciliationPort
Connector
AuditStore
ClockPort
UnitOfWork
```

---

# 267. Inbound Ports

```text
EffectCommandPort
EffectQueryPort
Ops/Admin Port
```

---

# 268. Bounded Context Ownership

Le concept principal appartient au :

```text
Effects bounded context
```

avec collaboration :

```text
Execution
Governance
Connectors
Audit
Coordination
```

---

# 269. Context Relationships

```text
Execution
→ waits for Effect resolution

Effects
→ owns reconciliation semantics

Connectors
→ provide provider-specific observations

Governance
→ authorizes manual resolution/repair

Coordination
→ ensures authoritative worker action

Audit
→ records evidence and decisions
```

---

# 270. Migration from V1

V1 `UNKNOWN_EFFECT` doit être transformé en :

```text
Run WAITING
+
Effect UNKNOWN
+
possibly ReconciliationCase OPEN
```

---

# 271. Migration Rule

Ne jamais migrer `UNKNOWN_EFFECT` en :

```text
FAILED
```

---

# 272. Existing V1 EffectResolution

Les concepts :

```text
NOT_APPLIED
COMMITTED
```

peuvent fournir de l’historique, mais ne suffisent pas au modèle V2.

---

# 273. V2 Superset

Le modèle V2 ajoute :

```text
explicit evidence
cases
strategies
manual review
confidence
```

---

# 274. Public Documentation

Les utilisateurs doivent comprendre clairement :

```text
when UNKNOWN occurs
why PyAgentsKit refuses retry
how to reconcile
how to resolve manually
```

---

# 275. Developer Experience

Le chemin simple pourrait être :

```python
result = await kit.effects.reconcile(effect_id)
```

mais l’API interne doit conserver toute la rigueur du modèle.

---

# 276. Safe Default

Si aucun ReconciliationPort n’existe :

```text
MANUAL_REQUIRED
```

ou `STILL_UNKNOWN`.

Jamais retry automatique.

---

# 277. Connector Author Checklist

Avant de supporter un write Effect :

```text
[ ] external ID available?
[ ] idempotency key available?
[ ] metadata/correlation tags possible?
[ ] provider history query?
[ ] eventual consistency known?
[ ] deletion behavior known?
[ ] lookup permissions available?
[ ] manual fallback documented?
```

---

# 278. Operator Checklist

Sur case manuel :

```text
[ ] correct tenant?
[ ] exact Effect?
[ ] original intent?
[ ] provider account?
[ ] evidence timestamp?
[ ] external reference?
[ ] payload/fingerprint match?
[ ] competing evidence?
[ ] resolution authorized?
```

---

# 279. Review Checklist

Pour toute nouvelle stratégie :

```text
[ ] deterministic?
[ ] provider-neutral core?
[ ] sufficient evidence?
[ ] safe under retry?
[ ] safe under concurrency?
[ ] tenant-scoped?
[ ] auditable?
[ ] rate-limit aware?
```

---

# 280. Acceptance Criteria

Le modèle est conforme si :

1. `UNKNOWN` est distinct de `FAILED` ;
2. Reconciliation est distincte de Retry ;
3. ReconciliationCase est durable ;
4. Evidence est explicitement représentée ;
5. résultats canoniques sont normalisés ;
6. `NOT_FOUND` reste connector-specific ;
7. ReconciliationPort observe sans décider seul le Domain ;
8. Application orchestre la résolution ;
9. resolution est concurrency-safe ;
10. manual review est first-class ;
11. nouveaux repair writes deviennent des Effects ;
12. sécurité/tenant scope sont respectés ;
13. Run peut rester WAITING ;
14. RecoveryPlanner choisit reconciliation avant resume dangereux ;
15. metrics/backlog sont observables ;
16. stratégies connector-specific sont documentées ;
17. tests W3/W4 existent ;
18. restore/PITR peut rouvrir reconciliation ;
19. migration V1 conserve l’ambiguïté ;
20. aucun retry automatique de UNKNOWN n’existe.

---

# 281. Definition of Done

`../runtime/37_PYAGENTSKIT_RECONCILIATION_MODEL.md` est considéré mature lorsque :

1. `ReconciliationCase` est implémenté ;
2. repository dédié existe ;
3. états et transitions sont testés ;
4. Evidence model est implémenté ;
5. `ReconciliationPort` existe ;
6. un fake contract-compliant existe ;
7. au moins un Connector réel implémente reconciliation ;
8. `ReconcileEffect` existe ;
9. `RecoveryPlanner` l’utilise ;
10. concurrent resolution est testée ;
11. stale worker resolution est bloquée ;
12. manual resolution est autorisée/auditée ;
13. backlog metrics existent ;
14. rate limiting/backoff sont pris en compte ;
15. W3/W4 sont testés avec vrai provider/sandbox ;
16. GitHub push/PR reconciliation est démontrée ;
17. restore/PITR déclenche safety reconciliation ;
18. V1 UNKNOWN migration est testée ;
19. API/CLI ops peut inspecter les cases ;
20. production qualification consomme ces scénarios.

---

# 282. Résumé

Le modèle cible est :

```text
PROTECTED EFFECT
      │
      ▼
    STARTED
      │
      ├───────────────┐
      │               │
      ▼               ▼
  response known   response/outcome uncertain
      │               │
      ▼               ▼
 SUCCEEDED/FAILED    UNKNOWN
                       │
                       ▼
              RECONCILIATION CASE
                       │
                       ▼
                COLLECT EVIDENCE
                       │
              ┌────────┼─────────┐
              ▼        ▼         ▼
           SUCCESS   FAILURE   UNCERTAIN
              │        │         │
              ▼        ▼         ▼
          SUCCEEDED  FAILED   MANUAL/WAIT
              │        │         │
              └────────┼─────────┘
                       ▼
                RECOVERY PLANNER
                       │
                       ▼
                    RUN
```

La chaîne correcte reste :

```text
ambiguity
→ evidence
→ reconciliation
→ resolution
→ optional retry
```

et jamais :

```text
ambiguity
→ retry
```

La règle fondamentale est :

> **Lorsqu’un agent agit sur un système externe, PyAgentsKit ne doit jamais inventer le résultat d’une action absente de sa mémoire locale : il doit retourner vers la réalité externe, collecter des preuves, établir ce qui s’est réellement passé, puis seulement décider s’il est sûr de continuer.**
