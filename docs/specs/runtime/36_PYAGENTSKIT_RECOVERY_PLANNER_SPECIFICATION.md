# PyAgentsKit — Recovery Planner Specification

**Document :** `../runtime/36_PYAGENTSKIT_RECOVERY_PLANNER_SPECIFICATION.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Domain & Application Specification  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../runtime/37_PYAGENTSKIT_RECONCILIATION_MODEL.md`
- `../operations/38_PYAGENTSKIT_TEST_STRATEGY.md`
- `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md`
- `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`

---

# 1. Objet

Ce document définit la spécification du **Recovery Planner** de PyAgentsKit V2.

Le Recovery Planner est le composant qui répond à la question :

> **Compte tenu de l’état durable actuel d’un Run, quelle est la prochaine action sûre à entreprendre ?**

Il ne cherche pas à “redémarrer ce qui s’est arrêté”.

Il cherche à déterminer :

```text
what may safely happen next
```

en tenant compte de :

- l’état du Run ;
- les checkpoints ;
- les Effects ;
- les `UNKNOWN` ;
- les Approvals ;
- les Leases ;
- les fencing tokens ;
- les RuntimeInvocations ;
- les RuntimeCapabilities ;
- la SecurityContext ;
- la Reconciliation ;
- les Artifacts nécessaires ;
- les blockers opérationnels ;
- l’état de migration/restore si pertinent.

Le principe directeur est :

> **Recovery is a decision problem before it is an execution problem.**

---

# 2. Positionnement

Le Recovery Planner appartient principalement au bounded context :

```text
Execution
```

Il collabore avec :

```text
Effects
Governance
Coordination
Runtime Integration
Audit
Persistence
```

Il ne doit pas devenir un orchestrateur universel.

---

# 3. Responsabilité exacte

Le Recovery Planner :

```text
reads authoritative durable state
evaluates blockers
determines safe NextAction
produces RecoveryPlan
```

Il ne :

```text
executes connector calls
mutates external systems
acquires leases directly
resumes runtime directly
approves actions
```

---

# 4. Separation of Decision and Execution

Architecture :

```text
Durable State
    │
    ▼
Recovery Planner
    │
    ▼
RecoveryPlan
    │
    ▼
Application Service
    │
    ▼
Ports / Adapters
```

---

# 5. Pourquoi cette séparation

Elle permet de tester la logique de reprise comme fonction déterministe :

```text
state
→
decision
```

sans dépendre immédiatement de :

```text
PostgreSQL
network
runtime provider
connector provider
```

---

# 6. Problème principal

Après un crash, PyAgentsKit peut retrouver :

```text
Run RUNNING
worker gone
lease expired
runtime handle present
Effect STARTED
Approval still valid
checkpoint available
```

ou une combinaison beaucoup plus ambiguë.

Le système ne peut pas simplement :

```text
resume runtime
```

car l’ordre de reprise est critique.

---

# 7. Ordre conceptuel de reprise

Le Recovery Planner doit raisonner dans l’ordre :

```text
1. Is Run already terminal?
2. Is durable authority available?
3. Is ownership valid?
4. Are security constraints valid?
5. Are approvals satisfied?
6. Are there unresolved Effects?
7. Is reconciliation required?
8. Is runtime resumable?
9. Can runtime restart safely?
10. Can Run complete?
11. Must operator intervene?
```

---

# 8. Core Invariant RP-INV-01

```text
No runtime resume may occur before unresolved critical Effects have been handled.
```

---

# 9. RP-INV-02

```text
A stale worker may never use a RecoveryPlan produced under previous ownership.
```

---

# 10. RP-INV-03

```text
A pending or invalid Approval blocks the protected action it governs.
```

---

# 11. RP-INV-04

```text
UNKNOWN Effect blocks dangerous replay.
```

---

# 12. RP-INV-05

```text
Runtime completion does not imply Run success.
```

---

# 13. RP-INV-06

```text
Recovery may select MANUAL_INTERVENTION as a valid safe outcome.
```

---

# 14. RP-INV-07

```text
Checkpoint cannot override authoritative Effect or Approval state.
```

---

# 15. RP-INV-08

```text
Restore/PITR invalidates assumptions derived only from pre-restore history.
```

---

# 16. RP-INV-09

```text
Authorization is revalidated when required before new protected progress.
```

---

# 17. RP-INV-10

```text
Recovery never invents external reality.
```

---

# 18. Core Objects

Le modèle cible comprend :

```text
RecoveryPlanner
RecoveryPlan
RecoveryContext
RecoveryBlocker
NextAction
RecoveryReason
RecoveryEvidence
```

---

# 19. RecoveryPlanner

Conceptuellement :

```python
class RecoveryPlanner:
    def plan(
        self,
        context: RecoveryContext,
    ) -> RecoveryPlan:
        ...
```

---

# 20. Pure vs Impure Planner

Le coeur du Planner doit idéalement être :

```text
pure / deterministic
```

Les lectures de repositories sont faites avant par l’Application Service.

Ainsi :

```text
repositories
→ RecoveryContext
→ Planner
→ RecoveryPlan
```

---

# 21. RecoveryContext

Le `RecoveryContext` contient les éléments nécessaires à la décision.

Proposition :

```text
run
session
runtime_binding
latest_runtime_invocation
latest_checkpoint
effects
approvals
lease
worker
security_context
reconciliation_cases
artifact_requirements
policy_snapshot
restore_context
```

---

# 22. Minimal Context

Le Planner doit pouvoir fonctionner avec :

```text
only necessary authoritative state
```

Il ne doit pas charger tout l’historique complet si inutile.

---

# 23. RecoveryPlan

Proposition :

```text
run_id
decision_id
next_action
reason
blockers[]
required_capabilities[]
required_authority
target_runtime_invocation_id
target_effect_id
target_approval_id
target_reconciliation_case_id
checkpoint_ref
generated_at
valid_until
ownership_generation
security_policy_version
```

---

# 24. Why `decision_id`

Pour audit :

```text
which plan was executed?
```

---

# 25. Why `valid_until`

Certaines décisions expirent.

Exemple :

```text
Approval nearing expiry
Lease nearing expiry
```

---

# 26. Ownership Generation Binding

Un RecoveryPlan doit être lié à :

```text
lease_id
fencing_token
```

ou génération d’ownership équivalente.

---

# 27. Stale Plan Protection

Si ownership change entre :

```text
plan
and
execute
```

le plan doit être revalidé ou recalculé.

---

# 28. NextAction

Enum cible :

```text
ACQUIRE_LEASE
WAIT_FOR_APPROVAL
RECONCILE_EFFECT
RESUME_RUNTIME
RESTART_RUNTIME
COMPLETE_RUN
FAIL_RUN
MANUAL_INTERVENTION
```

Possibles extensions :

```text
REFRESH_AUTHORIZATION
WAIT_FOR_DEPENDENCY
REBUILD_RUNTIME_CONTEXT
```

à introduire seulement si nécessaires.

---

# 29. ACQUIRE_LEASE

Signifie :

> **No further authoritative execution may proceed until ownership is acquired.**

---

# 30. WAIT_FOR_APPROVAL

Signifie :

```text
required Approval missing / pending / invalid
```

Le Run reste :

```text
WAITING
```

---

# 31. RECONCILE_EFFECT

Signifie :

```text
external outcome ambiguous
```

et reconciliation doit précéder toute reprise risquée.

---

# 32. RESUME_RUNTIME

Signifie :

```text
runtime can safely continue existing invocation
```

---

# 33. RESTART_RUNTIME

Signifie :

```text
existing invocation cannot resume
but recreating runtime execution is safe
```

---

# 34. COMPLETE_RUN

Signifie :

```text
all completion conditions satisfied
```

---

# 35. FAIL_RUN

Signifie :

```text
irrecoverable known failure
```

et non simple ambiguïté.

---

# 36. MANUAL_INTERVENTION

Signifie :

```text
automation cannot establish safe next step
```

---

# 37. RecoveryBlocker

Objet expliquant pourquoi certaines actions sont interdites.

---

# 38. Blocker Types

Proposition :

```text
NO_VALID_LEASE
PENDING_APPROVAL
EXPIRED_APPROVAL
UNAUTHORIZED
UNKNOWN_EFFECT
RECONCILIATION_PENDING
RUNTIME_NOT_RESUMABLE
RUNTIME_STATE_UNKNOWN
MISSING_CHECKPOINT
MISSING_ARTIFACT
SCHEMA_INCOMPATIBLE
RESTORE_SAFETY_GATE
DEPENDENCY_UNAVAILABLE
MANUAL_POLICY_BLOCK
```

---

# 39. Multiple Blockers

Un Run peut avoir plusieurs blockers.

Le Planner doit choisir :

```text
highest-priority blocker
```

sans perdre les autres.

---

# 40. Blocker Priority

Ordre recommandé :

```text
1. safety/authority
2. security
3. unresolved external reality
4. approval
5. runtime recovery
6. completion
```

---

# 41. Example Priority

Si :

```text
Approval pending
AND
Effect UNKNOWN
```

la reconciliation de l’Effect déjà tenté peut être plus prioritaire que l’Approval d’une prochaine action.

---

# 42. RecoveryReason

Permet une explication humaine.

Exemple :

```text
"Effect eff_123 has UNKNOWN outcome after W3 crash window."
```

---

# 43. Machine + Human Explanation

Le plan doit fournir :

```text
reason_code
reason_text
```

---

# 44. Recovery Evidence

Le Planner peut référencer :

```text
latest checkpoint
effect states
approval decision
lease state
runtime inspect snapshot
```

mais ne doit pas dupliquer tout le payload.

---

# 45. Recovery Plan Generation Flow

```text
load Run
   │
   ▼
terminal?
 ┌─┴─┐
Yes No
 │    │
 ▼    ▼
No-op check authority
         │
         ▼
      lease valid?
       ┌─┴─┐
      No  Yes
      │    │
      ▼    ▼
 ACQUIRE  security valid?
 LEASE       │
             ▼
        approvals/effects
             │
             ▼
        runtime recoverability
             │
             ▼
           NextAction
```

---

# 46. Terminal Run Rule

Si Run est :

```text
SUCCEEDED
FAILED
CANCELLED
```

aucun runtime resume ne doit être produit.

---

# 47. Terminal with Open Reconciliation

Important :

Un Run terminal peut encore avoir :

```text
open external reconciliation
```

selon politique.

Dans ce cas :

```text
Run recovery
```

et :

```text
Effect reconciliation
```

doivent rester des préoccupations distinctes.

---

# 48. Cancelled Run Rule

`CANCELLED` :

```text
does not imply
all external Effects resolved
```

---

# 49. Lease Evaluation

Le Planner évalue :

```text
lease exists?
lease active?
owned by current worker?
fencing generation current?
```

---

# 50. No Lease

Si aucune ownership requise n’est détenue :

```text
ACQUIRE_LEASE
```

---

# 51. Lease Owned by Another Worker

Le Planner ne recommande pas takeover immédiat si lease encore valide.

Résultat :

```text
WAIT / no local action
```

Selon API, cela peut être représenté par :

```text
MANUAL_INTERVENTION
or
WAIT_FOR_DEPENDENCY
```

Mais une action `WAIT` générique pourrait être ajoutée si besoin.

---

# 52. Expired Lease

Si lease expiré :

```text
ACQUIRE_LEASE
```

peut déclencher normal takeover.

---

# 53. Lease Near Expiry

Un plan nécessitant long external Effect peut être refusé si :

```text
remaining lease time < safety threshold
```

---

# 54. Lease Renewal Before Action

L’Application Service peut :

```text
renew
then execute
```

si planner indique authority valid but near deadline.

---

# 55. Security Evaluation

Le RecoveryContext doit indiquer si :

```text
SecurityContext valid
Principal active
tenant scope correct
policy decision still valid
```

---

# 56. Revoked Permission

Si permission supprimée après crash :

```text
do not resume protected action
```

---

# 57. Authorization Revalidation

Avant :

```text
RESUME_RUNTIME
```

si runtime peut provoquer des Effects, la policy peut imposer revalidation.

---

# 58. Runtime Read-Only Resume

Si runtime segment restant est pure computation :

```text
authorization requirements may differ
```

---

# 59. Approval Evaluation

Pour chaque action protégée en attente :

```text
Approval exists?
status?
scope?
fingerprint?
expiry?
principal?
```

---

# 60. Pending Approval

```text
WAIT_FOR_APPROVAL
```

---

# 61. Expired Approval

Le Planner doit éviter :

```text
resume with old approval
```

---

# 62. Scope Drift

Si Effect fingerprint a changé :

```text
WAIT_FOR_APPROVAL
```

pour une nouvelle approval.

---

# 63. Approval After Takeover

Revalidation doit s’assurer que :

```text
approval still applies
```

indépendamment du worker.

---

# 64. Effects Evaluation

Le Planner doit inspecter les Effects pertinents.

Priorité :

```text
UNKNOWN
STARTED stale
RECONCILIATION_REQUIRED
FAILED retryable
SUCCEEDED
```

---

# 65. SUCCEEDED Effect

Jamais replayé.

---

# 66. FAILED Effect

Si failure connue :

```text
policy decides
retry / fail run / alternate path
```

Le RecoveryPlanner peut recommander `FAIL_RUN` si irrécoverable.

---

# 67. UNKNOWN Effect

Toujours :

```text
RECONCILE_EFFECT
```

avant replay dangereux.

---

# 68. STARTED Effect

Un Effect `STARTED` après crash doit être évalué.

Questions :

```text
was send attempted?
is outcome known?
is operation idempotent?
is external ref available?
```

---

# 69. STARTED Without Send Evidence

Peut être assimilé à :

```text
safe-to-evaluate retry
```

mais uniquement si le modèle prouve que send n’a pas eu lieu.

---

# 70. STARTED With Possible Send

Devient :

```text
UNKNOWN
```

ou reconciliation required.

---

# 71. ReconciliationCase Present

Si case ouvert :

```text
RECONCILE_EFFECT
```

ou wait si un autre worker traite le case.

---

# 72. Reconciliation Resolved Success

Effect doit être mis à jour vers :

```text
SUCCEEDED
```

avant le prochain plan.

---

# 73. Reconciliation Resolved Failure

Effect devient :

```text
FAILED
```

puis nouveau plan calculé.

---

# 74. Runtime Evaluation

Le Planner doit connaître :

```text
RuntimeDescriptor
RuntimeCapabilities
RuntimeInvocation state
RuntimeHandle availability
Checkpoint availability
```

---

# 75. RuntimeInvocation States

Candidats :

```text
CREATED
STARTING
RUNNING
WAITING
COMPLETED
FAILED
CANCELLED
UNKNOWN
```

---

# 76. Runtime State UNKNOWN

Si runtime provider ne peut être inspecté :

```text
do not blindly restart
```

si restart pourrait dupliquer Effects.

---

# 77. Runtime Handle Present + RESUME

Si :

```text
handle valid
capability RESUME
no blockers
```

alors :

```text
RESUME_RUNTIME
```

---

# 78. Runtime Handle Missing

Si restart depuis checkpoint/prompt state est safe :

```text
RESTART_RUNTIME
```

---

# 79. Runtime Restart Safety

Le Planner doit vérifier :

```text
all prior Effects authoritative
no unresolved tool invocation
checkpoint consistency
```

---

# 80. Checkpoint Role

Checkpoint sert à :

```text
reconstruct computational context
```

Il ne prouve pas :

```text
external Effect outcome
```

---

# 81. Missing Checkpoint

N’empêche pas forcément restart si :

```text
full state reconstructible from canonical sources
```

---

# 82. Native Runtime

Peut être restartable depuis :

```text
Session
Messages
Memory
Effect state
```

---

# 83. External Runtime

Peut nécessiter :

```text
provider session/thread handle
```

---

# 84. Capability Negotiation

Le Planner ne recommande `RESUME_RUNTIME` que si :

```text
RESUME in adapter capabilities
```

---

# 85. Native Checkpoint Capability

Si disponible :

```text
NATIVE_CHECKPOINT
```

peut améliorer recovery.

Mais :

```text
checkpoint != source of truth
```

---

# 86. Runtime Completion

Si RuntimeInvocation `COMPLETED` :

Le Planner vérifie encore :

```text
Effects
Approvals
Artifacts
Run completion conditions
```

---

# 87. Completion Preconditions

Exemple :

```text
no unresolved blocking Effect
required artifact registered
no pending mandatory Approval
runtime complete
```

---

# 88. COMPLETE_RUN

Seulement quand toutes les invariants sont satisfaites.

---

# 89. FAIL_RUN

Uniquement pour failure connue, irrécoverable selon policy.

---

# 90. MANUAL_INTERVENTION Cases

Exemples :

```text
conflicting external evidence
runtime state unrecoverable
missing critical artifact
restore ambiguity
policy ambiguity
corrupt durable state
```

---

# 91. Manual Intervention Is Not Failure

Le Run peut rester :

```text
WAITING
```

avec blocker manuel.

---

# 92. RecoveryPlan Determinism

À contexte identique :

```text
same plan
```

doit être produit, hors champ dépendant explicitement de time.

---

# 93. Time Dependence

Le Planner reçoit :

```text
now
```

via ClockPort/RecoveryContext.

Pas d’accès direct à wall clock.

---

# 94. Policy Versioning

Les décisions doivent référencer :

```text
policy_version
```

si policy dynamique.

---

# 95. Plan Explainability

Chaque plan doit pouvoir expliquer :

```text
why this action
why alternatives were rejected
```

---

# 96. RecoveryDecisionTrace

Objet optionnel :

```text
evaluated_rules[]
selected_rule
blockers[]
```

utile pour debug.

---

# 97. Rule Evaluation Model

Les règles peuvent être ordonnées.

Exemple :

```text
R-001 terminal?
R-010 authority?
R-020 security?
R-030 unresolved Effects?
R-040 approvals?
R-050 runtime resumability?
R-060 completion?
```

---

# 98. Rule Priority

La première règle de priorité critique peut arrêter la décision.

---

# 99. Example Rule Table

| Rule | Condition | NextAction |
|---|---|---|
| RP-R01 | Run terminal | none/no-op |
| RP-R02 | no valid ownership | ACQUIRE_LEASE |
| RP-R03 | security invalid | MANUAL_INTERVENTION / deny |
| RP-R04 | UNKNOWN Effect | RECONCILE_EFFECT |
| RP-R05 | pending Approval | WAIT_FOR_APPROVAL |
| RP-R06 | runtime resumable | RESUME_RUNTIME |
| RP-R07 | runtime restart safe | RESTART_RUNTIME |
| RP-R08 | completion conditions met | COMPLETE_RUN |
| RP-R09 | known irrecoverable failure | FAIL_RUN |
| RP-R10 | no safe automatic step | MANUAL_INTERVENTION |

---

# 100. Why Effects Before Approval Sometimes

Si Approval concerne une future action mais un ancien Effect est déjà UNKNOWN :

```text
reconcile old Effect first
```

car l’external reality doit être connue avant de planifier la suite.

---

# 101. Why Security Before Runtime

Runtime peut être capable de générer de nouvelles tool calls.

Donc :

```text
authorization
before
resume
```

selon policy.

---

# 102. RecoveryPlan Validity

Un plan est valide tant que ses assumptions restent vraies.

---

# 103. Plan Preconditions

Exemple :

```text
run_version == X
effect_version == Y
lease_token == Z
approval_version == A
```

---

# 104. Execute With Preconditions

L’Application Service doit vérifier ces versions avant action.

---

# 105. Compare-and-Swap

Pour éviter race :

```text
plan
→ state changes
→ stale execution
```

utiliser :

```text
version/CAS
```

---

# 106. Replan on Conflict

Si précondition échoue :

```text
discard plan
reload
replan
```

---

# 107. Recovery Loop

Concept :

```text
while not terminal:
    context = load_authoritative_state()
    plan = planner.plan(context)
    result = execute(plan)
    persist(result)
```

---

# 108. Recovery Loop Boundaries

Ne pas faire boucle infinie.

---

# 109. Progress Detection

Chaque itération doit :

```text
change durable state
or
enter WAITING/manual state
```

---

# 110. Loop Protection

Candidat :

```text
max automatic recovery steps
```

avant escalation.

---

# 111. RecoveryAttempt

Objet possible :

```text
recovery_attempt_id
run_id
worker_id
started_at
plan_count
outcome
```

---

# 112. RecoveryAttempt Use

Audit/observability, pas forcément aggregate Domain.

---

# 113. Recovery Planner Inputs from Repositories

L’Application Service peut charger :

```text
RunRepository
EffectRepository
ApprovalRepository
LeaseRepository
ReconciliationRepository
RuntimeInvocationRepository
ArtifactRepository
```

---

# 114. UnitOfWork

Lecture puis transition critique doivent être protégées par :

```text
short local transaction
```

quand nécessaire.

---

# 115. No External Call During Planning

Le Planner pur :

```text
does not call provider
```

---

# 116. Runtime Inspect Placement

`runtime.inspect()` est un external call.

Donc :

```text
Application Service
→ inspect
→ durable normalized snapshot
→ RecoveryContext
→ Planner
```

---

# 117. Freshness of Runtime Inspect

Le snapshot doit être timestampé.

Le Planner peut refuser de l’utiliser s’il est trop ancien.

---

# 118. Connector State Placement

Même principe pour provider evidence.

---

# 119. Restore/PITR Recovery

Restore introduit un contexte spécial.

---

# 120. RestoreContext

Peut contenir :

```text
restored_from_timestamp
restore_generation
safety_gate_status
known_external_gap
```

---

# 121. Restore Safety Gate

Si restore non réconcilié :

```text
MANUAL_INTERVENTION
or
RECONCILE_EFFECT
```

avant `RESUME_RUNTIME`.

---

# 122. Fencing After Restore

Si fencing generation pourrait avoir régressé :

```text
no protected execution
```

---

# 123. Migration Context

Pendant V1→V2 :

```text
source-of-truth phase
```

peut influencer recovery.

---

# 124. Mixed V1/V2

Le Planner V2 ne doit pas opérer si authority source est encore V1, sauf explicit migration adapter.

---

# 125. Compatibility Layer

`compat.v1` traduit les états.

Il ne contourne pas Planner V2.

---

# 126. V1 UNKNOWN_EFFECT

Devient :

```text
Run WAITING
Effect UNKNOWN
NextAction RECONCILE_EFFECT
```

---

# 127. V1 WAITING_APPROVAL

Devient :

```text
Run WAITING
Approval PENDING
NextAction WAIT_FOR_APPROVAL
```

---

# 128. Effect Retry Decision

Le Planner peut distinguer :

```text
retryable known failure
```

de :

```text
unknown outcome
```

---

# 129. Retryable Failure

Si Effect `FAILED` et policy autorise retry :

Possibles choix :

```text
RESTART_RUNTIME
or
new Effect attempt
```

selon orchestration.

---

# 130. Unknown Outcome

Jamais directement :

```text
RESTART_RUNTIME
```

si runtime peut répéter l’Effect.

---

# 131. Runtime Tool Interception

Si adapter possède :

```text
TOOL_INTERCEPTION
```

recovery peut être plus précis.

---

# 132. No Tool Interception

Si runtime peut agir directement sans interception complète :

```text
side-effect control level
```

doit être considéré.

---

# 133. Runtime Control Level

Candidat :

```text
FULL
PARTIAL
OBSERVATIONAL
```

---

# 134. Recovery Safety by Control Level

`FULL` :

```text
can resume with protected gates
```

`PARTIAL` :

```text
may require stricter checkpoints/manual review
```

`OBSERVATIONAL` :

```text
no claim of strong Effect guarantees
```

---

# 135. Recovery Plan and SideEffectControlLevel

Le plan doit inclure :

```text
control_level
```

ou dériver sa décision de cette information.

---

# 136. Coding Agent Recovery

Scénario :

```text
agent edited files
committed SHA A
Approval for SHA A
git push attempted
response lost
worker dies
```

Planner :

```text
UNKNOWN push
→ RECONCILE_EFFECT
```

pas :

```text
restart coding runtime
```

---

# 137. After Git Reconciliation Success

```text
Effect SUCCEEDED
```

Nouveau plan :

```text
RESUME_RUNTIME
or
COMPLETE_RUN
```

---

# 138. After Git Reconciliation Failure

Si push non appliqué et retry autorisé :

```text
new safe push attempt
```

---

# 139. Approval Expired During Recovery

Si prochain Effect nécessite Approval :

```text
WAIT_FOR_APPROVAL
```

---

# 140. Deployment Recovery

Un deployment Effect `UNKNOWN` :

```text
RECONCILE_EFFECT
```

avant tout second deploy.

---

# 141. Terraform Recovery

Interruption pendant apply :

```text
MANUAL_INTERVENTION
```

peut être préférable si provider/state divergence complexe.

---

# 142. Payment Recovery

UNKNOWN payment :

```text
RECONCILE_EFFECT
```

par provider transaction/idempotency key.

---

# 143. Human Governance Recovery

Si Approval store disponible mais approver disabled :

```text
revalidate
```

et potentiellement demande nouvelle Approval.

---

# 144. Missing Security Context

Si SecurityContext ne peut pas être reconstruit :

```text
MANUAL_INTERVENTION
```

pour actions protégées.

---

# 145. Dependency Outage

Si runtime/connector indisponible mais état sûr :

```text
WAITING
```

peut être préférable à failure.

---

# 146. Optional NextAction WAIT_FOR_DEPENDENCY

Peut être ajouté si besoin d’expression explicite.

Sinon blocker + current Run WAITING suffit.

---

# 147. Why Keep NextAction Small

Un enum trop large devient :

```text
workflow DSL
```

à éviter.

---

# 148. Planner Extensibility

Nouvelles règles via :

```text
policy
bounded decision services
```

plutôt qu’un moteur générique.

---

# 149. Recovery Policy

Objet possible :

```text
RecoveryPolicy
```

avec :

```text
max_auto_steps
allow_runtime_restart
require_reauth
manual_after
```

---

# 150. Policy Per Risk Class

```text
LOW
MEDIUM
HIGH
CRITICAL
```

---

# 151. High Risk

Peut imposer :

```text
no automatic restart after ambiguous external interaction
```

---

# 152. Low Risk

Peut autoriser davantage de replay de pure computation.

---

# 153. Pure Compute Replay

Si aucun Effect externe n’est impliqué :

```text
replay/restart is generally safe
```

---

# 154. Pure vs Effectful Segment

Le Planner peut utiliser :

```text
checkpoint metadata
```

pour savoir si la dernière zone était pure ou effectful.

---

# 155. CheckpointKind

Concept potentiel :

```text
PURE
PRE_EFFECT
POST_EFFECT
RUNTIME_NATIVE
```

---

# 156. Checkpoint After Effect

Un checkpoint après Effect ne remplace toujours pas :

```text
Effect durable outcome
```

---

# 157. Recovery with Missing Artifact

Si runtime nécessite un Artifact manquant :

```text
MANUAL_INTERVENTION
```

ou re-materialization si deterministic/safe.

---

# 158. Artifact Integrity Failure

Checksum mismatch :

```text
MANUAL_INTERVENTION
```

pour critical state.

---

# 159. Recovery with Outbox Lag

Outbox lag ne bloque pas forcément Run progress.

---

# 160. Recovery with Audit Failure

Selon profile :

```text
standard → degrade
high assurance → block protected progress
```

---

# 161. Recovery with Telemetry Failure

Normalement :

```text
does not block
```

---

# 162. Recovery with IdP Failure

Protected actions peuvent :

```text
WAIT
```

si reauthorization obligatoire.

---

# 163. Recovery with Policy Engine Failure

High-risk :

```text
fail closed
```

---

# 164. Planner Error Model

Le Planner ne doit pas lever des exceptions pour cas métier normaux.

Exemples :

```text
pending approval
unknown effect
no lease
```

sont des plans/blockers, pas des exceptions.

---

# 165. Planner Exceptions

Réservées à :

```text
corrupt input
impossible invariant
unsupported schema
programmer error
```

---

# 166. Corrupt Durable State

Exemple :

```text
Run SUCCEEDED
but required Effect UNKNOWN
```

peut être traité comme :

```text
MANUAL_INTERVENTION
```

+ incident.

---

# 167. Invariant Violation

Le Planner doit produire :

```text
explicit diagnostic
```

et ne pas deviner.

---

# 168. RecoveryPlan Serialization

Peut être sérialisable pour :

```text
audit
ops UI
dry-run
```

---

# 169. Recovery Dry Run

Commande possible :

```text
plan_recovery(run_id)
```

sans exécuter.

---

# 170. Dry-Run Value

Permet à l’opérateur de voir :

```text
NextAction
blockers
reason
dependencies
```

---

# 171. Ops UI

Vue cible :

```text
Run
Current state
Ownership
Blocking Effect
Approval
Runtime
Recommended NextAction
Why
```

---

# 172. Audit Events

À générer :

```text
RecoveryPlanned
RecoveryActionStarted
RecoveryActionCompleted
RecoveryBlocked
ManualInterventionRequired
```

---

# 173. Audit Payload

Inclure :

```text
run_id
decision_id
next_action
reason_code
worker_id
ownership token
```

sans secret.

---

# 174. Metrics

```text
recovery_plans_total
recovery_actions_total
recovery_manual_total
recovery_blocked_total
recovery_replans_total
```

---

# 175. Metrics by NextAction

Labels faibles cardinalité :

```text
next_action
reason_code
runtime_type
```

---

# 176. Avoid High Cardinality

Pas :

```text
run_id
effect_id
```

dans labels globaux.

---

# 177. Recovery Latency

Mesurer :

```text
time from eligible
to first valid plan
```

---

# 178. Recovery Completion Time

Mesurer :

```text
time from recovery start
to stable state
```

---

# 179. Manual Intervention Rate

Un taux élevé peut signaler :

```text
poor runtime capabilities
weak reconciliation
bad connector design
```

---

# 180. Replan Rate

Un taux élevé peut signaler :

```text
contention
stale plans
overly long execution windows
```

---

# 181. Planner Performance

Le Planner pur doit être rapide.

Complexité principalement :

```text
number of relevant Effects/Approvals
```

---

# 182. Limit Context Size

Ne pas passer :

```text
entire audit history
all messages
```

si non nécessaire.

---

# 183. Relevant Effect Selection

Application Query peut sélectionner :

```text
blocking
recent
unresolved
```

Effects.

---

# 184. Relevant Approval Selection

Seulement approvals liées aux actions qui pourraient être reprises.

---

# 185. Planner Caching

Éviter cache autoritatif.

Le plan dépend de state versions.

---

# 186. Plan Memoization

Possible uniquement à contexte/version strictement identique.

Peu utile initialement.

---

# 187. Concurrency

Deux workers peuvent produire un plan en parallèle.

Correctness repose sur :

```text
lease/fencing
CAS/version
```

pas sur l’unicité du calcul.

---

# 188. Concurrent Plan Execution

Un seul doit pouvoir appliquer les mutations protégées.

---

# 189. Stale Plan Example

Worker A planifie `RESUME_RUNTIME`.

Worker B prend ownership.

A exécute plus tard.

Attendu :

```text
authority check fails
```

---

# 190. Recovery Worker Pool

Peut être :

```text
same worker fleet
or
specialized recovery workers
```

---

# 191. Specialized Recovery Workers

Utile pour :

```text
recovery storms
```

mais pas obligatoire.

---

# 192. Recovery Admission Control

Batcher :

```text
eligible Runs
```

pour éviter storm.

---

# 193. Priority

Exemple :

```text
critical UNKNOWN Effects
expired leases
interactive Runs
background Runs
```

---

# 194. Scheduler Interaction

Un scheduler externe peut déclencher :

```text
RecoverRun
```

mais Planner reste autoritatif sur la décision.

---

# 195. Event-Driven Recovery

Possible via :

```text
lease expired event
runtime failed event
approval completed event
reconciliation resolved event
```

---

# 196. Polling Recovery

Possible fallback.

---

# 197. Hybrid Recovery

Recommandé :

```text
events for responsiveness
periodic scan for missed events
```

---

# 198. Recovery Scanner

Query :

```text
non-terminal Runs
with recovery-eligible conditions
```

---

# 199. Scanner Is Not Planner

Scanner trouve les candidats.

Planner décide.

---

# 200. Candidate Selection

Exemples :

```text
RUNNING with expired lease
WAITING with completed Approval
WAITING with resolved reconciliation
RUNNING with stale runtime invocation
```

---

# 201. Recovery Eligibility

Un Run terminal n’est pas candidat à runtime recovery.

---

# 202. Recovery Trigger — Approval Completed

Nouvel Approval peut débloquer :

```text
WAIT_FOR_APPROVAL
→ next plan
```

---

# 203. Recovery Trigger — Reconciliation Resolved

Peut débloquer :

```text
RECONCILE_EFFECT
→ runtime/complete
```

---

# 204. Recovery Trigger — Lease Expired

Peut rendre possible :

```text
ACQUIRE_LEASE
```

---

# 205. Recovery Trigger — Worker Lost

Même logique.

---

# 206. Recovery Trigger — Runtime Event

Runtime remote peut signaler completion/failure.

Doit être normalisé puis replanné.

---

# 207. Recovery Trigger — Dependency Restored

Un Run `WAITING` peut être remis dans queue.

---

# 208. State-Driven Recovery

Le modèle reste :

```text
state
→ plan
```

indépendamment du trigger.

---

# 209. Public API

Use cases possibles :

```text
recover_run(run_id)
plan_recovery(run_id)
```

---

# 210. RecoverRun

Application Service :

```text
load
inspect if needed
plan
execute one safe step
persist
```

---

# 211. One-Step vs Multi-Step Recovery

Préférence :

```text
one authoritative step
then replan
```

---

# 212. Why One-Step

Réduit risque que les assumptions deviennent stale.

---

# 213. Multi-Step Shortcut

Possible seulement pour :

```text
pure local transitions
```

dans même transaction.

---

# 214. Remote Boundary

Toujours :

```text
commit
→ remote action
→ commit
→ replan
```

---

# 215. Recovery and UnitOfWork

Exemple :

```text
load Effect
mark reconciliation pending
commit
call provider
commit evidence
```

---

# 216. No Long DB Transaction

Jamais garder transaction ouverte pendant :

```text
runtime.resume
connector call
provider inspect
```

---

# 217. Recovery of RuntimeInvocation

RuntimeInvocation doit avoir sa propre identity.

---

# 218. Run != RuntimeInvocation

Un Run peut avoir :

```text
multiple RuntimeInvocations
```

sur sa vie.

---

# 219. Restart Creates New Invocation

`RESTART_RUNTIME` crée typiquement :

```text
new RuntimeInvocation
```

lié au même Run.

---

# 220. Resume Reuses Invocation

`RESUME_RUNTIME` continue :

```text
existing RuntimeInvocation
```

---

# 221. Invocation Lineage

Conserver :

```text
parent invocation
restart reason
checkpoint origin
```

---

# 222. Runtime Handle Rotation

Un restart produit nouveau :

```text
RuntimeHandle
```

---

# 223. Run Completion After Multiple Invocations

Le Run reste un seul aggregate logique.

---

# 224. Runtime Invocation Failure

Une invocation peut être :

```text
FAILED
```

sans que Run doive l’être si restart safe.

---

# 225. Recovery Planner Decides

```text
invocation failed
+
safe restart
→ RESTART_RUNTIME
```

---

# 226. Retry vs Restart

`RESTART_RUNTIME` :

```text
new runtime execution context
```

pas forcément :

```text
retry same Effect
```

---

# 227. Replaying Pure Computation

Acceptable.

---

# 228. Replaying Tool Calls

Seulement si :

```text
Effect state permits
```

---

# 229. Runtime Adapter Contract Need

Un Runtime Adapter doit documenter :

```text
what resume replays
what restart replays
how tool calls are surfaced
```

---

# 230. Native Runtime Contract

Le Native Runtime doit être l’implémentation de référence du modèle.

---

# 231. External Runtime Limitations

Si adapter ne permet pas de contrôler replay précisément :

```text
manual or stricter recovery policy
```

---

# 232. SideEffectControlLevel

Proposition :

```text
FULL
BOUNDED
OPAQUE
```

---

# 233. FULL

PyAgentsKit intercepte les actions externes avant exécution.

---

# 234. BOUNDED

Certaines actions seulement sont interceptables.

---

# 235. OPAQUE

Runtime peut avoir des effets invisibles.

PyAgentsKit ne peut pas offrir les mêmes garanties.

---

# 236. Planner Behavior by Control Level

```text
FULL
→ automated recovery possible

BOUNDED
→ recovery constrained

OPAQUE
→ strong guarantees unavailable, often manual
```

---

# 237. Recovery Confidence

Le Planner peut exposer :

```text
AUTOMATIC_SAFE
CONDITIONAL
MANUAL_REQUIRED
```

comme metadata, sans complexifier NextAction.

---

# 238. Planner Version

Le RecoveryPlan doit référencer :

```text
planner_version
```

pour audit/reproducibility.

---

# 239. Rule Version

Option :

```text
recovery_policy_version
```

---

# 240. Replay of Historical Plan

Ops peut vouloir comprendre :

```text
why planner decided X
```

Il faut conserver assez d’evidence/version.

---

# 241. Deterministic Replay

Objectif utile :

```text
same context snapshot + same planner version
→ same plan
```

---

# 242. Snapshot for Audit

Ne pas stocker tous les objets si références/version suffisent.

---

# 243. Testing Strategy

Unit tests :

```text
RecoveryContext
→ NextAction
```

---

# 244. Table-Driven Tests

Très adaptés.

Exemple :

| Condition | Expected |
|---|---|
| no lease | ACQUIRE_LEASE |
| UNKNOWN Effect | RECONCILE_EFFECT |
| pending Approval | WAIT_FOR_APPROVAL |
| resumable runtime | RESUME_RUNTIME |
| restartable runtime | RESTART_RUNTIME |
| all complete | COMPLETE_RUN |
| irrecoverable known failure | FAIL_RUN |
| ambiguous impossible state | MANUAL_INTERVENTION |

---

# 245. Property Tests

Exemples :

```text
terminal Run never plans RESUME_RUNTIME
UNKNOWN Effect never plans direct replay
stale ownership never plans protected execution
```

---

# 246. Model-Based Tests

Peuvent générer séquences :

```text
crash
takeover
approval
reconciliation
resume
```

---

# 247. Integration Tests

Application Service `RecoverRun` avec :

```text
Memory
SQLite
PostgreSQL
```

---

# 248. Distributed Tests

Deux workers :

```text
same Run
different plans
one authority
```

---

# 249. W1–W5 Tests

Le Planner doit produire les actions appropriées pour chaque fenêtre.

---

# 250. W1 Expected

Si aucune intention durable :

```text
restart pure work
```

peut être possible.

---

# 251. W2 Expected

Intent durable, no send :

```text
safe evaluation
```

selon evidence.

---

# 252. W3 Expected

```text
RECONCILE_EFFECT
```

---

# 253. W4 Expected

```text
RECONCILE_EFFECT
```

---

# 254. W5 Expected

```text
continue without replay
```

---

# 255. Restore Tests

Après PITR :

```text
planner must not resume blindly
```

---

# 256. Runtime Capability Tests

Chaque capability influence le planner.

---

# 257. Negative Tests

```text
terminal → RESUME forbidden
UNKNOWN → restart forbidden if replay risk
no authority → protected action forbidden
invalid approval → execute forbidden
```

---

# 258. Contract with Application Service

Le Planner produit :

```text
decision
```

L’Application Service est responsable de :

```text
executing exactly one step
```

---

# 259. Application Service Error

Si execution échoue :

```text
persist normalized outcome
replan later
```

---

# 260. Plan Execution Result

Objet possible :

```text
RecoveryActionResult
```

---

# 261. Fields

```text
decision_id
action
status
new_state_refs
error
completed_at
```

---

# 262. Audit Link

Relier :

```text
RecoveryPlan
RecoveryActionResult
```

---

# 263. Recovery Status

Pour UI :

```text
NOT_NEEDED
ELIGIBLE
PLANNED
RUNNING
WAITING
MANUAL
RECOVERED
```

Possible read-model, pas forcément Domain.

---

# 264. Run `WAITING`

Le Planner doit préférer `WAITING` à `FAILED` lorsque le système attend :

```text
Approval
Reconciliation
Dependency
Operator
```

---

# 265. Run `PAUSED`

Ne pas auto-resume un Run explicitement `PAUSED` sans signal utilisateur/policy.

---

# 266. PAUSED vs WAITING

```text
PAUSED
=
explicit suspension

WAITING
=
blocked by external condition
```

---

# 267. Recovery of PAUSED

Default :

```text
no automatic progress
```

---

# 268. Recovery of CANCELLED

Pas de runtime progress.

Mais unresolved Effects peuvent nécessiter reconciliation.

---

# 269. Recovery of FAILED

Par défaut terminal.

Toute réouverture nécessite use case explicite, pas recovery automatique.

---

# 270. Recovery of SUCCEEDED

Aucun runtime progress.

---

# 271. Recovery of CREATED

Peut devenir :

```text
ACQUIRE_LEASE
or
start execution
```

selon workflow.

---

# 272. Start vs Recovery

Un Run jamais démarré n’est pas techniquement recovery.

Mais le Planner peut partager certaines règles.

---

# 273. Separation Recommendation

Conserver :

```text
StartRun
RecoverRun
```

comme use cases distincts.

---

# 274. Recovery Planner Package

Topologie cible :

```text
domain/
  execution/
    recovery/
      planner.py
      plan.py
      blocker.py
      policy.py
```

---

# 275. Application Package

```text
application/
  execution/
    recover_run.py
    plan_recovery.py
```

---

# 276. No Adapter Dependency

`planner.py` n’importe aucun :

```text
PostgreSQL
LangGraph
GitHub
OpenAI SDK
```

---

# 277. DTO Boundary

Application transforme provider states en :

```text
canonical snapshots
```

avant Planner.

---

# 278. Recovery Runtime Snapshot

Objet possible :

```text
RuntimeInspectionSnapshot
```

---

# 279. Fields

```text
invocation_id
status
handle_valid
capabilities
checkpoint_available
observed_at
```

---

# 280. Dependency Health Snapshot

Objet possible :

```text
DependencyAvailability
```

pour indiquer :

```text
runtime available
connector available
policy available
```

---

# 281. Planner Simplicity Principle

Ne pas faire du Planner :

```text
generic rules engine
```

---

# 282. Explicit Code

Préférer des règles Python typées et testables.

---

# 283. Why

Le domaine est critique.

La lisibilité est plus importante qu’un DSL sophistiqué.

---

# 284. Rule Ordering as Code

Exemple :

```python
if run.is_terminal:
    ...
elif not ownership.valid:
    ...
elif effects.has_unknown:
    ...
elif approvals.blocking:
    ...
...
```

---

# 285. Refactoring Threshold

Introduire un rule engine seulement si :

```text
rule count/variation
```

le justifie réellement.

---

# 286. Observability — Planner Span

Trace :

```text
recovery.plan
```

---

# 287. Attributes

```text
run_state
next_action
blocker_type
runtime_type
```

sans IDs high-cardinality en metrics.

---

# 288. Recovery Dashboard

Afficher :

```text
eligible Runs
plans by NextAction
manual cases
recovery lag
replans
```

---

# 289. Alerting

Alertes :

```text
manual intervention spike
recovery backlog growth
repeated replan loop
stale plan rejects
```

---

# 290. Incident Response

Le document 42 doit utiliser le Planner comme source de décision sûre lorsque possible.

---

# 291. Operator Override

Un opérateur ne doit pas pouvoir :

```text
force RESUME_RUNTIME
```

sans passer les mêmes garde-fous ou un use case break-glass audité.

---

# 292. Break-Glass

Si nécessaire :

```text
authorization
reason
audit
two-person rule in high assurance
```

---

# 293. Manual Action Is New Decision

Après intervention manuelle :

```text
reload state
replan
```

---

# 294. No Persistent Manual Override Flag

Éviter :

```text
ignore_safety=true
```

durable et générique.

---

# 295. Recovery Planner and Public API

L’API publique peut exposer :

```text
RecoveryPlanView
```

mais pas forcément toutes les structures internes.

---

# 296. RecoveryPlanView

Champs :

```text
run_id
next_action
reason
blockers
requires_manual_action
```

---

# 297. Security of Recovery Queries

Les plans peuvent exposer :

```text
sensitive external refs
```

donc authorization requise.

---

# 298. Recovery Plan Retention

Pas nécessairement conserver tous les plans indéfiniment.

Conserver :

```text
critical decision/audit refs
```

selon retention.

---

# 299. Planner Evolution

Toute modification de règle P0 doit :

```text
ADR
tests
release note
qualification rerun
```

---

# 300. Semantic Versioning

Un changement majeur de recovery semantics peut être :

```text
breaking
```

même sans changer signature.

---

# 301. Recovery Planner Qualification Levels

Proposition :

```text
RP-L0 unit logic
RP-L1 application integration
RP-L2 persistence integration
RP-L3 failure/distributed
RP-L4 production qualified
```

---

# 302. RP-L0

Tous les NextAction couverts.

---

# 303. RP-L1

`RecoverRun` fonctionne avec fakes.

---

# 304. RP-L2

Fonctionne avec PostgreSQL réel.

---

# 305. RP-L3

SIGKILL/SIGSTOP/W3/W4.

---

# 306. RP-L4

Game Days + real runtime/connector.

---

# 307. P0 Scenarios

Avant V2 stable :

```text
RP-P0-01 UNKNOWN Effect
RP-P0-02 stale worker
RP-P0-03 pending Approval
RP-P0-04 expired Approval
RP-P0-05 runtime resumable
RP-P0-06 runtime non-resumable but safe restart
RP-P0-07 restore safety gate
RP-P0-08 cross-tenant/security invalid
RP-P0-09 terminal Run
RP-P0-10 no safe automatic action
```

---

# 308. Contract Testing

`RecoveryPlanner` lui-même n’est pas un adapter.

Mais ses inputs normalisés doivent être stables.

---

# 309. Test Matrix — Effects

| Effect State | Expected Planner Bias |
|---|---|
| NOT_STARTED | normal execution possible |
| STARTED no send | evaluate safe continuation |
| STARTED possible send | reconcile |
| SUCCEEDED | never replay |
| FAILED | policy-dependent fail/retry |
| UNKNOWN | reconcile |
| RECONCILIATION_REQUIRED | reconcile/manual |

---

# 310. Test Matrix — Approval

| Approval | Expected |
|---|---|
| PENDING | WAIT_FOR_APPROVAL |
| APPROVED exact scope | may proceed |
| APPROVED stale scope | WAIT_FOR_APPROVAL |
| REJECTED | fail/alternate path |
| EXPIRED | new Approval required |
| CANCELLED | blocked |

---

# 311. Test Matrix — Lease

| Lease | Expected |
|---|---|
| none | ACQUIRE_LEASE |
| current valid | continue evaluation |
| current near expiry | renew/revalidate |
| other owner active | wait/no progress |
| expired | ACQUIRE_LEASE/takeover |
| stale token | no protected action |

---

# 312. Test Matrix — Runtime

| Runtime | Capability | Expected |
|---|---|---|
| running valid | RESUME | RESUME_RUNTIME |
| failed | restart safe | RESTART_RUNTIME |
| completed | blockers none | COMPLETE_RUN |
| unknown | no safe inspection | MANUAL_INTERVENTION |
| handle lost | restart safe | RESTART_RUNTIME |
| handle lost | restart unsafe | MANUAL_INTERVENTION |

---

# 313. Test Matrix — Restore

| Restore Condition | Expected |
|---|---|
| no external gap | normal evaluation |
| possible external gap | RECONCILE_EFFECT |
| fencing regression risk | MANUAL_INTERVENTION |
| unknown approvals | manual/revalidate |
| unresolved restored outbox | dedup-aware handling |

---

# 314. Anti-Pattern — Resume First, Check Later

Interdit.

---

# 315. Anti-Pattern — Treat Recovery as Retry

Interdit.

---

# 316. Anti-Pattern — Planner Calls Providers

Le coeur ne doit pas devenir impure orchestration.

---

# 317. Anti-Pattern — Trust Checkpoint over Effects

Interdit.

---

# 318. Anti-Pattern — Ignore Ownership

Interdit.

---

# 319. Anti-Pattern — Ignore Approval Scope

Interdit.

---

# 320. Anti-Pattern — Always Restart Runtime

Peut répéter des Effects.

---

# 321. Anti-Pattern — Fail on Every Ambiguity

Transforme uncertainty en faux failure.

---

# 322. Anti-Pattern — Infinite Auto-Recovery

Doit finir par WAITING/manual si aucun progrès.

---

# 323. Anti-Pattern — One Giant Recovery Transaction

Interdit.

---

# 324. Anti-Pattern — Hidden Runtime Replay

Adapter doit documenter resume/restart semantics.

---

# 325. Anti-Pattern — Manual Override Without Audit

Interdit.

---

# 326. Acceptance Criteria

Le Recovery Planner est conforme si :

1. il est séparé de l’exécution ;
2. il consomme uniquement des états canoniques ;
3. il ne dépend d’aucun provider SDK ;
4. `UNKNOWN` produit reconciliation avant replay ;
5. absence de lease bloque le protected progress ;
6. stale ownership invalide le plan ;
7. Approval est revalidée ;
8. security peut bloquer la reprise ;
9. RuntimeCapability influence la décision ;
10. checkpoint ne remplace pas Effect truth ;
11. `RESUME_RUNTIME` et `RESTART_RUNTIME` sont distingués ;
12. `MANUAL_INTERVENTION` est first-class ;
13. plan est explainable ;
14. plan est version/precondition-bound ;
15. concurrent state changes forcent replan ;
16. terminal Run ne reprend jamais ;
17. PAUSED n’est pas auto-repris ;
18. Restore/PITR active un safety gate ;
19. W1–W5 sont couverts ;
20. chaque NextAction est testable indépendamment.

---

# 327. Definition of Done

`../runtime/36_PYAGENTSKIT_RECOVERY_PLANNER_SPECIFICATION.md` est considéré mature lorsque :

1. `RecoveryContext` est implémenté ;
2. `RecoveryPlan` est implémenté ;
3. `RecoveryBlocker` est implémenté ;
4. `NextAction` est stabilisé ;
5. Planner est pur/testable ;
6. les règles de priorité sont codées ;
7. les P0 scenarios ont des unit tests ;
8. Application Service `PlanRecovery` existe ;
9. `RecoverRun` exécute un step puis replan ;
10. CAS/version protège les plans stale ;
11. lease/fencing est intégré ;
12. approvals sont intégrées ;
13. reconciliation est intégrée ;
14. RuntimeCapabilities sont intégrées ;
15. RestoreContext est supporté ;
16. V1 migrated states donnent les bons plans ;
17. métriques recovery existent ;
18. dry-run/ops inspection existe ;
19. Game Days utilisent le Planner ;
20. Production Qualification GATE-05 est satisfaite.

---

# 328. Résumé

Le modèle cible est :

```text
DURABLE RUN STATE
      │
      ▼
OWNERSHIP VALID?
   ┌──┴──┐
  No    Yes
  │      │
  ▼      ▼
ACQUIRE  SECURITY VALID?
LEASE       │
            ▼
       UNRESOLVED EFFECT?
         ┌──┴──┐
        Yes    No
        │      │
        ▼      ▼
   RECONCILE   APPROVAL READY?
                    │
                    ▼
             RUNTIME RECOVERABLE?
                 ┌──┼────────┐
                 ▼  ▼        ▼
              RESUME RESTART MANUAL
                 │      │
                 └──┬───┘
                    ▼
             COMPLETION CHECK
                    │
                ┌───┴───┐
                ▼       ▼
             COMPLETE   CONTINUE
```

La chaîne de récupération correcte est :

```text
read authority
→ identify blockers
→ establish external truth
→ validate governance
→ select runtime action
→ execute one safe step
→ persist
→ replan
```

et jamais :

```text
process died
→ restart everything
```

La règle fondamentale est :

> **Le Recovery Planner n’a pas pour mission de faire repartir un agent ; il a pour mission de prouver quelle prochaine action est encore sûre après que l’exécution normale a été interrompue.**
