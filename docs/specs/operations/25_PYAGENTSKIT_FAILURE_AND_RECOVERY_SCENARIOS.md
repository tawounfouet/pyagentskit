# PyAgentsKit — Failure & Recovery Scenarios

**Document :** `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Spécification de sûreté — Failure & Recovery  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`

---

# 1. Objet

Ce document formalise les **scénarios de panne et de reprise** que PyAgentsKit doit traiter de manière sûre.

L’objectif n’est pas seulement de savoir si un Run redémarre, mais de garantir qu’il reprend :

- sans répéter un effet métier déjà réussi ;
- sans transformer un état ambigu en échec certain ;
- sans perdre une décision humaine ;
- sans laisser un stale worker agir après takeover ;
- sans considérer un checkpoint comme plus autoritatif que l’EffectStore ;
- sans dépendre d’un graceful shutdown ;
- sans reconstruire une autorité absente.

> **La reprise n’est correcte que si elle restaure la progression sans dégrader les invariants de sûreté.**

---

# 2. Définitions

```text
Failure
= événement empêchant le chemin nominal

Recovery
= reconstruction de la prochaine action sûre

Retry
= nouvelle exécution d’une opération considérée rejouable

Reconciliation
= détermination de ce qui s’est réellement passé sur un système externe

Takeover
= acquisition légitime de la ressource par un nouveau worker
```

---

# 3. Retry ≠ Recovery ≠ Reconciliation

```text
Retry
= refaire

Recovery
= décider quoi faire ensuite

Reconciliation
= découvrir la réalité externe
```

Un generic retry middleware ne doit jamais décider seul de rejouer un Protected Effect.

---

# 4. RecoveryPlanner

Le composant central est :

```text
RecoveryPlanner
```

Entrées :

```text
Run
latest valid Checkpoint
Effects
Approvals
Lease
Worker state
Runtime state
Policy
SecurityContext
External references
```

Sortie :

```text
RecoveryPlan
```

---

# 5. NextAction

Valeurs candidates :

```text
ACQUIRE_LEASE
WAIT_FOR_APPROVAL
RECONCILE_EFFECT
RESUME_RUNTIME
RESTART_RUNTIME
COMPLETE_RUN
FAIL_RUN
CANCEL_RUN
MANUAL_INTERVENTION
```

---

# 6. RecoveryBlocker

```text
UNKNOWN_EFFECT
MISSING_APPROVAL
LEASE_CONFLICT
CHECKPOINT_CORRUPT
RUNTIME_UNAVAILABLE
STORE_UNAVAILABLE
SECRET_PROVIDER_UNAVAILABLE
AUTHORIZATION_UNAVAILABLE
MANUAL_REVIEW_REQUIRED
```

---

# 7. Ordre général de reprise

```text
load durable Run
↓
terminal?
↓
load valid Checkpoint
↓
validate/acquire Lease
↓
revalidate SecurityContext
↓
load Approvals
↓
inspect Effects
↓
reconcile UNKNOWN/stale STARTED
↓
inspect Runtime
↓
compute RecoveryPlan
↓
resume / restart / wait / stop / manual
```

---

# 8. Invariants globaux

```text
REC-INV-01  SUCCEEDED Effect is never implicitly replayed.
REC-INV-02  UNKNOWN is never treated as FAILED.
REC-INV-03  Stale workers cannot create new Protected Effects.
REC-INV-04  Recovery never forges Approval.
REC-INV-05  Missing external response never proves failure.
REC-INV-06  Recovery can move to another worker.
REC-INV-07  Critical decisions use durable state.
REC-INV-08  Checkpoint never overrides authoritative Effect state.
REC-INV-09  Recovery revalidates security.
REC-INV-10  Manual intervention is valid when safety cannot be proven.
```

---

# 9. Niveaux de reprise

```text
R0 — transparent
R1 — automatic recovery
R2 — reconciliation required
R3 — manual intervention may be required
R4 — safety incident / stop-the-world
```

---

# 10. Taxonomie des pannes

```text
F-PROC    Process / OS
F-WORKER  Worker lifecycle
F-LEASE   Distributed coordination
F-DB      PostgreSQL / stores
F-EFFECT  External Effects
F-RUNTIME Agent runtime
F-APP     Human approvals
F-MSG     Messaging / webhooks
F-ART     Artifact storage
F-CONN    External connectors
F-SEC     Security dependencies
F-CHK     Checkpoints
F-MIG     Migration / restore
F-CODE    Coding agents
```

---

# 11. F-PROC-001 — Crash avant création durable du Run

```text
request received
↓
process crashes
↓
no Run COMMIT
```

État durable :

```text
Run absent
```

Recovery :

```text
client retry with same idempotency key
```

---

# 12. F-PROC-002 — Crash après création du Run, avant réponse client

Le Run existe mais le client ne le sait pas.

Attendu :

```text
same Idempotency-Key
→ same logical Run
```

---

# 13. F-PROC-003 — Crash avant runtime start

État :

```text
Run = READY
no active RuntimeInvocation
```

Recovery :

```text
new worker
→ acquire lease
→ start runtime
```

---

# 14. F-PROC-004 — Crash après runtime start mais avant persistance du handle

Le runtime peut exister sans `RuntimeHandle` durable.

Recovery :

```text
adapter discovery/inspect if possible
```

sinon :

```text
logical restart
```

après inspection de l’historique des Effects.

---

# 15. F-PROC-005 — Crash après handle persisté

```text
new worker
↓
load RuntimeHandle
↓
adapter.inspect()
↓
resume if supported
```

---

# 16. F-PROC-006 — Crash pendant calcul pur

La computation peut être rejouée si elle n’a produit aucun Effect durable.

---

# 17. F-PROC-007 — Crash entre deux checkpoints

Reprendre depuis :

```text
latest valid durable checkpoint
```

Les calculs purs après ce checkpoint peuvent être refaits.

---

# 18. F-PROC-008 — SIGTERM

Séquence cible :

```text
stop admissions
↓
Worker → DRAINING
↓
finish or park at safe boundary
↓
persist state
↓
release/stop renewing as appropriate
↓
bounded telemetry flush
↓
exit
```

---

# 19. F-PROC-009 — SIGTERM pendant Protected Effect

Un graceful shutdown ne doit pas interrompre volontairement l’appel à un point qui rend l’issue ambiguë si cela peut être évité.

Après délai borné :

```text
unknown outcome
→ UNKNOWN / reconciliation
```

---

# 20. F-PROC-010 — SIGKILL

Aucun cleanup n’est garanti.

La sûreté repose sur :

```text
durable intent
lease expiry
fencing
reconciliation
```

---

# 21. F-PROC-011 — OOM Kill

Même traitement qu’un crash brutal.

Aucune garantie ne doit dépendre de :

```text
finally
atexit
cleanup callback
```

---

# 22. F-PROC-012 — Reboot machine

```text
lease expires
↓
another worker takes over
↓
RecoveryPlanner
```

---

# 23. F-WORKER-001 — Freeze / SIGSTOP

Séquence critique :

```text
Worker A token 41
↓
SIGSTOP
↓
lease expires
↓
Worker B takeover token 42
↓
SIGCONT Worker A
```

A est stale.

---

# 24. F-WORKER-002 — Worker reprend après freeze

Il ne doit pas faire confiance à son état mémoire.

Avant tout Protected Effect :

```text
revalidate authoritative ownership
```

---

# 25. F-WORKER-003 — Heartbeat stale, lease valide

```text
heartbeat != ownership
```

Le heartbeat seul ne retire pas l’autorité.

---

# 26. F-WORKER-004 — Heartbeat sain, lease perdu

Même principe :

```text
heartbeat cannot restore ownership
```

---

# 27. F-WORKER-005 — Worker drain

```text
stop new Runs
keep safe renewals
finish/park active work
handoff at recovery boundary
```

---

# 28. F-WORKER-006 — Worker disparaît pendant WAITING

Un Run en attente d’Approval ne nécessite pas de process vivant.

---

# 29. F-LEASE-001 — Renewal timeout ambigu

Le worker ne sait pas si le renewal a été accepté.

Attendu :

```text
stop new Protected Effects
↓
query authoritative LeaseStore
```

---

# 30. F-LEASE-002 — Renewal rejeté

```text
ownership lost
```

Arrêt immédiat de toute progression protégée.

---

# 31. F-LEASE-003 — Lease expiré

Un autre worker peut faire un takeover.

---

# 32. F-LEASE-004 — Acquisitions concurrentes

Deux workers essaient de prendre la même ressource.

PostgreSQL doit assurer :

```text
one authoritative winner
```

---

# 33. F-LEASE-005 — Takeover

Le nouveau token doit vérifier :

```text
new fencing token > previous token
```

---

# 34. F-LEASE-006 — Ancien worker agit après takeover

Le Protected Store/Tool doit rejeter le token obsolète.

---

# 35. F-LEASE-007 — Split-brain

Si deux workers se croient owner :

```text
authoritative LeaseStore + fencing
```

décident.

---

# 36. F-LEASE-008 — Provider sans remote fencing

Risque résiduel.

Compensations :

```text
ownership revalidation immediately before call
short credential lifetime
Effect reservation
idempotency
provider business-key checks
```

---

# 37. F-LEASE-009 — Force takeover

Exige :

```text
admin authorization
reason
new fencing generation
AuditEvent
```

---

# 38. F-LEASE-010 — LeaseStore indisponible

Si l’autorité ne peut pas être prouvée :

```text
Protected Effects blocked
```

---

# 39. F-LEASE-011 — Clock skew worker

Le temps du worker n’est pas autoritatif.

Lease expiry utilise :

```text
PostgreSQL time
```

---

# 40. F-DB-001 — PostgreSQL indisponible avant lecture du Run

Worker :

```text
not ready
cannot safely progress
```

---

# 41. F-DB-002 — DB indisponible pendant calcul pur

Continuation éventuelle uniquement de manière bornée, sans nouvelle décision critique impossible à persister.

---

# 42. F-DB-003 — DB indisponible avant réservation d’Effect

Résultat obligatoire :

```text
do not execute Effect
```

---

# 43. F-DB-004 — DB outage après réservation, avant appel externe

État :

```text
Effect = STARTED
```

Si l’implémentation peut prouver que rien n’a été envoyé, retry possible.

Sinon :

```text
conservative reconciliation
```

---

# 44. F-DB-005 — Provider réussit, DB indisponible au retour

L’Effect reste durablement :

```text
STARTED
```

Recovery :

```text
STARTED stale
→ UNKNOWN
→ reconcile
```

---

# 45. F-DB-006 — COMMIT incertain

Après erreur de connexion pendant COMMIT :

```text
re-read authoritative state
```

Ne pas répéter la mutation associée par supposition.

---

# 46. F-DB-007 — Deadlock

Si aucune mutation externe n’a été déclenchée :

```text
retry local DB transaction
```

---

# 47. F-DB-008 — Serialization failure

Même règle.

---

# 48. F-DB-009 — Pool épuisé

Réactions :

```text
backpressure
reduce admissions
readiness degraded
alert
```

---

# 49. F-DB-010 — Failover primary

Après reconnexion :

```text
revalidate active leases
reload current durable state
```

---

# 50. F-DB-011 — Replica lag

Interdit pour décisions autoritatives de :

```text
Lease
Effect
Approval
Run transition
```

---

# 51. F-DB-012 — Idempotency conflict, même fingerprint

```text
same key
same fingerprint
→ deduplicate
```

---

# 52. F-DB-013 — Idempotency conflict, fingerprint différent

```text
IdempotencyConflict
```

Jamais écraser le premier intent.

---

# 53. F-EFFECT-001 — Crash avant envoi externe

Si l’absence d’envoi est prouvable :

```text
safe retry
```

---

# 54. F-EFFECT-002 — Crash après envoi, avant réponse

```text
UNKNOWN
```

puis :

```text
RECONCILE_EFFECT
```

---

# 55. F-EFFECT-003 — Timeout après acceptation possible

Même règle :

```text
timeout != failure
```

---

# 56. F-EFFECT-004 — Succès externe explicite

Persister :

```text
SUCCEEDED
ExternalReference
```

avant d’avancer.

---

# 57. F-EFFECT-005 — Échec métier explicite

`FAILED` seulement si le provider permet de conclure que l’action n’a pas été produite ou qu’elle a échoué de façon certaine.

---

# 58. F-EFFECT-006 — HTTP 500 après commit possible

Peut être :

```text
UNKNOWN
```

et non automatiquement `FAILED`.

---

# 59. F-EFFECT-007 — Connection reset

Pour un write :

```text
UNKNOWN unless provider semantics prove failure
```

---

# 60. F-EFFECT-008 — Retry avec idempotency native

Le provider doit retourner le même résultat logique si sa garantie le permet.

---

# 61. F-EFFECT-009 — Provider sans idempotency

Utiliser :

```text
business key
lookup
reconciliation
manual review
```

---

# 62. F-EFFECT-010 — Effect SUCCEEDED au recovery

```text
never execute again
continue after Effect
```

---

# 63. F-EFFECT-011 — Effect FAILED au recovery

Actions possibles :

```text
retry if explicitly safe
fail Run
manual intervention
```

---

# 64. F-EFFECT-012 — Effect UNKNOWN au recovery

Action obligatoire :

```text
RECONCILE_EFFECT
```

---

# 65. F-EFFECT-013 — Reconciliation confirme succès

```text
UNKNOWN → SUCCEEDED
```

---

# 66. F-EFFECT-014 — Reconciliation confirme échec

```text
UNKNOWN → FAILED
```

---

# 67. F-EFFECT-015 — Reconciliation ambiguë

```text
RECONCILIATION_REQUIRED
→ MANUAL_REVIEW
```

si aucune preuve supplémentaire n’est disponible.

---

# 68. F-EFFECT-016 — Provider de reconciliation indisponible

Le Run peut rester :

```text
WAITING
```

avec plan de retry borné.

---

# 69. F-EFFECT-017 — Résolution manuelle

Exige :

```text
authorized actor
reason
evidence
AuditEvent
```

---

# 70. F-EFFECT-018 — Compensation échoue

Une compensation est elle-même un Effect :

```text
idempotency
status
reconciliation
audit
```

---

# 71. F-EFFECT-019 — Outbox publish échoue

La transaction métier reste commitée.

L’Outbox reste :

```text
PENDING / FAILED
```

et le publisher retente.

---

# 72. F-EFFECT-020 — Publication Outbox dupliquée

Le consumer doit utiliser :

```text
event_id / Inbox dedup
```

---

# 73. F-RUNTIME-001 — Process runtime crash

Recovery :

```text
adapter.inspect(RuntimeHandle)
```

ou logical restart si la session est perdue.

---

# 74. F-RUNTIME-002 — Session distante survit au worker

Le nouveau worker :

```text
loads handle
reattaches
resumes
```

---

# 75. F-RUNTIME-003 — Session runtime expirée

```text
RESTART_RUNTIME
```

avec contexte durable.

---

# 76. F-RUNTIME-004 — Runtime status UNKNOWN

Ne pas le transformer en `FAILED`.

Faire :

```text
inspect
query provider
reconnect event stream
```

---

# 77. F-RUNTIME-005 — Event stream disconnect

Le runtime peut toujours tourner.

```text
reconnect / resume cursor / inspect
```

---

# 78. F-RUNTIME-006 — Event dupliqué

Dédupliquer par :

```text
event_id
```

ou garde d’état.

---

# 79. F-RUNTIME-007 — Events hors ordre

Utiliser sequence/provider state quand disponibles.

---

# 80. F-RUNTIME-008 — Event inconnu

Conserver comme événement opaque/unknown si possible.

Ne pas casser le core.

---

# 81. F-RUNTIME-009 — Adapter exception

Normaliser l’erreur et appliquer une policy de recovery explicite.

---

# 82. F-RUNTIME-010 — Adapter indisponible après déploiement

Le Run peut rester `WAITING` jusqu’au retour d’une version compatible.

---

# 83. F-RUNTIME-011 — Incompatibilité handle/checkpoint

Options :

```text
pinned old adapter
handle migration
logical restart
manual intervention
```

---

# 84. F-RUNTIME-012 — Checkpoint runtime natif corrompu

Fallback possible vers :

```text
PyAgentsKit durable checkpoint
```

si safety prouvable.

---

# 85. F-APP-001 — Worker crash pendant attente Approval

Aucun problème sémantique.

```text
Approval = PENDING
```

reste durable.

---

# 86. F-APP-002 — Approval arrive sans owner actif

La décision est persistée puis :

```text
Outbox wake-up
```

Un futur worker reprend.

---

# 87. F-APP-003 — Notification Approval perdue

La vérité reste :

```text
ApprovalStore
```

La notification peut être retentée.

---

# 88. F-APP-004 — Décision dupliquée

Même décision :

```text
idempotent
```

---

# 89. F-APP-005 — Décisions concurrentes incompatibles

CAS sur `PENDING`.

Une seule transition terminale gagne.

---

# 90. F-APP-006 — Expiration pendant décision

Le temps DB tranche.

---

# 91. F-APP-007 — Approval expire pendant outage

Au recovery :

```text
EXPIRED
```

si deadline dépassée.

---

# 92. F-APP-008 — Scope modifié avant exécution

Exemple :

```text
approved checksum A
current checksum B
```

Résultat :

```text
BLOCK
new approval
```

---

# 93. F-APP-009 — Permission approver révoquée

La policy définit si l’ancienne décision reste valide.

Le recovery doit appliquer cette policy courante.

---

# 94. F-APP-010 — ApprovalStore indisponible

Pour action nécessitant Approval :

```text
fail closed
```

---

# 95. F-MSG-001 — Webhook dupliqué

```text
same external_event_id
→ one logical processing
```

---

# 96. F-MSG-002 — Webhook hors ordre

Relecture du provider si l’ordre a une importance métier.

---

# 97. F-MSG-003 — Crash après Inbox insert

La ligne Inbox permet de reprendre sans créer un second traitement logique.

---

# 98. F-MSG-004 — Queue redelivery

At-least-once expected.

```text
Inbox dedup
```

---

# 99. F-MSG-005 — Ack perdu

Le message peut revenir.

Aucune duplication métier.

---

# 100. F-MSG-006 — Delivery sur Run déjà possédé

```text
queue delivery != ownership
```

Le lease reste requis.

---

# 101. F-MSG-007 — DLQ

Doit être :

```text
observable
audited when critical
replay-controlled
```

---

# 102. F-MSG-008 — Wake-up perdu

Un scanner/polling retrouve éventuellement le Run exécutable.

La notification n’est pas la source de vérité.

---

# 103. F-ART-001 — BlobStore down avant upload

Artifact ne devient pas `ACTIVE`.

---

# 104. F-ART-002 — Upload réussi, metadata commit échoue

Possibilité d’orphan blob.

Recovery :

```text
reconcile object existence
repair metadata
or garbage collect
```

---

# 105. F-ART-003 — Metadata existe, upload échoue

Artifact :

```text
FAILED / non ACTIVE
```

---

# 106. F-ART-004 — Checksum mismatch

```text
quarantine / fail
```

---

# 107. F-ART-005 — Artifact supprimé hors PyAgentsKit

Détecter au read/reconciliation.

Selon reproductibilité :

```text
rebuild
or manual
```

---

# 108. F-CONN-001 — Provider down avant read

Retry/backoff possible selon budget.

---

# 109. F-CONN-002 — Provider down avant write envoyé

Safe si request prouvée non envoyée.

---

# 110. F-CONN-003 — Provider down après write envoyé

```text
UNKNOWN
```

---

# 111. F-CONN-004 — HTTP 429

Respecter :

```text
Retry-After
bounded retry budget
```

---

# 112. F-CONN-005 — OAuth access token expiré

Refresh si possible, sans exposer de credential au runtime.

---

# 113. F-CONN-006 — Secret rotaté

Recovery résout de nouveau :

```text
SecretReference
```

---

# 114. F-CONN-007 — Schema provider change

Validation fail-safe.

Pas de mapping silencieux dangereux.

---

# 115. F-CONN-008 — Provider status inconnu

Mapper vers un état externe inconnu sûr, pas vers succès/échec arbitraire.

---

# 116. F-CONN-009 — Eventual consistency

Après create :

```text
lookup may temporarily return NOT_FOUND
```

La reconciliation doit disposer d’une observation window bornée.

---

# 117. F-SEC-001 — Authorization provider indisponible

Pour opération sensible :

```text
BLOCK
```

---

# 118. F-SEC-002 — SecretProvider indisponible

```text
do not execute tool
```

---

# 119. F-SEC-003 — Policy engine indisponible

Pour CRITICAL Effect :

```text
fail closed
```

---

# 120. F-SEC-004 — AuditStore indisponible

```text
STANDARD → configurable degradation
HIGH_ASSURANCE → critical actions blocked
```

---

# 121. F-SEC-005 — Tenant suspendu pendant WAITING

Au resume :

```text
tenant revalidation
```

avant progression.

---

# 122. F-SEC-006 — Credential révoqué mid-run

Réauthentifier/résoudre nouveau credential.

Pas de retry infini avec credential mort.

---

# 123. F-SEC-007 — Kill switch activé

```text
Protected Effects stop
Runs may become WAITING
```

---

# 124. F-CHK-001 — Latest checkpoint illisible

Essayer le checkpoint précédent.

---

# 125. F-CHK-002 — Checksum checkpoint invalide

Le checkpoint est rejeté.

---

# 126. F-CHK-003 — Tous checkpoints corrompus

Options :

```text
logical restart from durable state
MANUAL_INTERVENTION
```

---

# 127. Checkpoint safety invariant

Le checkpoint ne peut jamais écraser :

```text
SUCCEEDED Effect
terminal Approval
current Lease/Fencing state
```

---

# 128. F-CHK-004 — Version checkpoint non supportée

Options :

```text
migration
pinned compatible code
manual intervention
```

---

# 129. F-MIG-001 — Migration échoue avant commit

Rollback transactionnel si supporté.

---

# 130. F-MIG-002 — Migration partiellement appliquée

Nécessite :

```text
forward fix / repair plan
```

---

# 131. F-MIG-003 — Mixed workers vN / vN+1

Seulement si schéma expand/contract compatible.

---

# 132. F-MIG-004 — Worker incompatible avec schema

```text
readiness = false
```

---

# 133. F-MIG-005 — Backfill interrompu

Le backfill doit être :

```text
restartable
idempotent
observable
```

---

# 134. F-MIG-006 — Restore backup ancien

Danger majeur :

```text
database says past
external world may be future
```

---

# 135. Post-restore safety gate

Avant reprise :

```text
stop admissions
invalidate old workers
verify schema
repair fencing generation
reconcile external Effects
revalidate Approvals
inspect Outbox/Inbox
```

---

# 136. F-MIG-007 — Fencing counter restauré trop bas

Incident R4.

Aucun worker ne doit reprendre tant qu’une génération sûre n’a pas été rétablie.

---

# 137. F-MIG-008 — PITR avant un Effect externe

Le provider peut avoir une action que PostgreSQL a “oubliée”.

Donc :

```text
mandatory reconciliation campaign
```

---

# 138. F-CODE-001 — Crash pendant éditions locales

Si workspace durable :

```text
resume
```

Sinon, si patch durable :

```text
reconstruct
```

---

# 139. F-CODE-002 — Workspace éphémère perdu

Reconstruire à partir de :

```text
base commit
patch/diff artifact
generated artifacts
```

---

# 140. F-CODE-003 — Workspace perdu sans patch

Le travail local peut être refait.

Vérifier d’abord les Effects distants déjà produits.

---

# 141. F-CODE-004 — Crash après commit local

Pas nécessairement d’Effect externe.

Le commit peut être repris si workspace/repository durable.

---

# 142. F-CODE-005 — git push timeout

```text
push may have succeeded
↓
Effect UNKNOWN
↓
fetch remote
↓
compare expected SHA
```

---

# 143. F-CODE-006 — PR creation timeout

Reconcile par :

```text
repository + head + base
```

---

# 144. F-CODE-007 — Merge timeout

Interroger :

```text
PR state
merge commit SHA
```

---

# 145. F-CODE-008 — Package publish timeout

Interroger :

```text
package
version
checksum
```

---

# 146. F-CODE-009 — Deployment timeout

Query deployment platform.

Jamais redéployer à l’aveugle.

---

# 147. F-CODE-010 — Terraform apply interrompu

Inspecter :

```text
remote state
cloud resources
plan reference
```

avant toute nouvelle exécution.

---

# 148. F-CODE-011 — Branch remote drift

```text
expected SHA mismatch
```

Résultat :

```text
safe stop / rebase / manual
```

selon policy.

---

# 149. F-CODE-012 — Rebase après Approval

Nouveau SHA :

```text
old Approval scope invalid
```

si bound au précédent.

---

# 150. F-CODE-013 — CI indisponible

Si check obligatoire :

```text
WAIT
```

et non “assume green”.

---

# 151. F-CODE-014 — PR mergée manuellement pendant outage

Recovery détecte l’état distant et marque l’Effect selon preuve externe, avec audit.

---

# 152. Crash windows

```text
W1 — before durable intent
W2 — after durable intent, before external send
W3 — after send, before response
W4 — after response, before durable outcome
W5 — after durable outcome, before next Run progress
```

---

# 153. W1 — Before durable intent

Pas de preuve durable d’intention.

Une nouvelle tentative peut être une première tentative logique.

---

# 154. W2 — Durable intent, no send

Si non-envoi prouvé :

```text
safe execute
```

---

# 155. W3 — Sent, response unknown

Fenêtre la plus dangereuse.

```text
UNKNOWN
```

---

# 156. W4 — Response received, outcome not committed

Après crash :

```text
reconcile
```

car la mémoire du process a disparu.

---

# 157. W5 — Outcome committed

Si `SUCCEEDED` :

```text
continue after Effect
```

---

# 158. Recovery matrix — Run

| Run state | Recovery par défaut |
|---|---|
| CREATED | prepare/admit |
| READY | acquire lease/start |
| RUNNING | inspect lease/runtime/effects |
| WAITING | inspect blocker |
| PAUSED | remain paused |
| SUCCEEDED | none |
| FAILED | none unless explicit restart policy |
| CANCELLED | none |

---

# 159. Recovery matrix — Effect

| Effect | Recovery |
|---|---|
| NOT_STARTED | may execute if authorized |
| STARTED | inspect staleness; reconcile if ambiguous |
| SUCCEEDED | never replay |
| FAILED | retry only if safe |
| UNKNOWN | reconcile |
| RECONCILIATION_REQUIRED | reconcile/manual |

---

# 160. Recovery matrix — Approval

| Approval | Recovery |
|---|---|
| PENDING | wait |
| APPROVED | revalidate scope/policy |
| REJECTED | block |
| EXPIRED | block |
| CANCELLED | block |

---

# 161. Recovery matrix — Lease

| Lease | Recovery |
|---|---|
| ACTIVE owned | continue |
| ACTIVE other owner | stop |
| EXPIRED | acquire/takeover |
| LOST | stop |
| RELEASED | acquire if needed |
| TAKEN_OVER | old worker stale |

---

# 162. Recovery matrix — Runtime

| Runtime | Recovery |
|---|---|
| RUNNING | attach/observe |
| WAITING | recover blocker |
| COMPLETED | persist/finalize |
| FAILED | policy |
| CANCELLED | align Run |
| UNKNOWN | inspect |
| missing | restart if safe |

---

# 163. Recovery priority

```text
1. authoritative stores
2. ownership
3. security
4. Effects/reconciliation
5. Approval validation
6. Runtime inspection
7. resume execution
```

---

# 164. Pourquoi Effects avant replay runtime

Un runtime relancé peut reproposer la même action.

L’Effect history doit donc être chargé avant de laisser le runtime progresser.

---

# 165. Automatic Recovery Rule

Automatiser uniquement si :

```text
safe next action can be proven
```

---

# 166. Manual Intervention Rule

Si la preuve manque :

```text
MANUAL_INTERVENTION
```

est un résultat correct.

---

# 167. Manual Resolution Context

Afficher :

```text
blocker
evidence
external references
possible actions
risk
required permission
```

---

# 168. Manual actions

Exemples :

```text
mark Effect success
mark Effect failure
retry Effect
cancel Run
force takeover
select checkpoint
rebind runtime
```

Toutes doivent être auditées.

---

# 169. Recovery observability

Événements :

```text
recovery.started
recovery.plan_computed
recovery.blocked
recovery.action_started
recovery.action_completed
recovery.completed
```

---

# 170. Recovery metrics

```text
recoveries_total
recovery_success_total
recovery_failures_total
recovery_manual_total
recovery_duration_seconds
```

---

# 171. Effect recovery metrics

```text
unknown_effects
reconciliations_total
reconciliation_success_total
reconciliation_manual_total
```

---

# 172. Coordination recovery metrics

```text
lease_takeovers_total
stale_worker_rejections_total
takeover_duration_seconds
```

---

# 173. Alerts P0

```text
duplicate critical Effect suspicion
stale fencing accepted
multiple authoritative owners
cross-tenant recovery
unsafe post-restore state
```

---

# 174. Alerts P1

```text
unknown Effect backlog
reconciliation backlog
repeated takeovers
checkpoint corruption
runtime resume failures
```

---

# 175. Recovery trace spans

```text
recovery.plan
recovery.acquire_lease
recovery.reconcile_effect
recovery.validate_approval
recovery.inspect_runtime
recovery.resume
```

---

# 176. Deterministic Recovery

À état durable identique et réponses externes identiques :

```text
RecoveryPlanner
```

doit produire la même décision logique.

---

# 177. Exemple RecoveryPlan

État :

```text
Run = RUNNING
Lease = EXPIRED
Effect E9 = UNKNOWN
Approval A3 = APPROVED
Runtime = UNKNOWN
```

Plan :

```text
1 ACQUIRE_LEASE
2 RECONCILE_EFFECT E9
3 REVALIDATE_APPROVAL A3
4 INSPECT_RUNTIME
5 RESUME_OR_RESTART
```

---

# 178. Fault injection points

```text
after_run_commit
after_checkpoint_commit
after_effect_reserve
before_external_send
after_external_send
before_effect_outcome_commit
after_approval_commit
after_lease_takeover
```

---

# 179. Process fault injection

```text
SIGTERM
SIGKILL
SIGSTOP
OOM
uncaught exception
host reboot
```

---

# 180. Network fault injection

```text
latency
timeout
connection reset
network partition
DNS failure
TLS failure
partial response
```

---

# 181. PostgreSQL fault injection

```text
primary restart
connection drop
deadlock
lock timeout
transaction abort
pool exhaustion
```

---

# 182. Runtime fault injection

```text
runtime crash
session expiry
event stream disconnect
duplicate event
out-of-order event
```

---

# 183. Connector fault injection

```text
HTTP 429
HTTP 500
timeout after accept
schema change
provider eventual consistency
```

---

# 184. Test — Multi-process takeover

```text
Worker A owns Run
↓
SIGKILL A
↓
lease expires
↓
Worker B takeover
↓
resume
```

Assertion :

```text
no duplicate Effect
```

---

# 185. Test — Freeze/zombie

```text
SIGSTOP A
↓
B takeover
↓
SIGCONT A
```

Assertion :

```text
A cannot execute Protected Effect
```

---

# 186. Test — PostgreSQL outage

Pendant Runs actifs :

```text
DB down
```

Assertions :

```text
new Protected Effects stop
readiness false/degraded
no local ownership assumptions
```

---

# 187. Test — Ambiguous Effect

Provider accepte puis coupe la connexion.

Assertions :

```text
UNKNOWN
reconciliation
no blind retry
```

---

# 188. Test — Approval with no worker

```text
Run WAITING
all workers restart
Approval arrives
new worker wakes/resumes
```

---

# 189. Test — Runtime session survives worker

Nouveau worker doit reattacher la session.

---

# 190. Test — Runtime logical restart

Session perdue.

Le nouvel agent reprend sans rejouer les Effects réussis.

---

# 191. Test — Corrupt latest checkpoint

Assertion :

```text
fallback previous checkpoint
EffectStore remains authoritative
```

---

# 192. Test — Duplicate webhook/queue

N livraisons :

```text
one logical processing
```

---

# 193. Test — Restore preceding external Effect

Assertions :

```text
admissions blocked
reconciliation required
fencing repaired
```

---

# 194. Test — Git push crash

```text
remote accepted
worker killed before outcome commit
```

Assertion :

```text
remote SHA reconciliation
no second logical push
```

---

# 195. Test — Deploy crash

Même principe via deployment status/reference.

---

# 196. Load + failure test

Injecter des crashes sous charge concurrente.

Mesurer :

```text
takeover latency
lease conflicts
Effect safety
recovery backlog
```

---

# 197. Soak recovery test

Longue durée avec :

```text
worker restarts
DB failovers
runtime disconnects
provider timeouts
```

---

# 198. Production blockers

PyAgentsKit ne peut pas être qualifié production-ready si échouent :

```text
SIGKILL during Protected Effect
SIGSTOP + takeover + resume
PostgreSQL outage
ambiguous external Effect
duplicate trigger delivery
Approval without worker
runtime crash after successful Effect
backup restore with stale state
```

---

# 199. Safety targets

Ces objectifs sont des invariants, pas des SLO tolérants :

```text
0 implicit replay of SUCCEEDED critical Effects
0 accepted stale fencing token
0 cross-tenant recovery
```

---

# 200. Recovery SLO candidates

À qualifier :

```text
p95 takeover duration
p99 RecoveryPlanner latency
unknown Effect resolution duration
automatic recovery success rate
```

---

# 201. Scenario Template

Pour tout nouveau scénario :

```text
ID
Title
Preconditions
Failure Injection
Durable State Before
External State
Expected RecoveryPlan
Forbidden Behavior
Assertions
Observability
Audit
Severity
Automation Level
```

---

# 202. Forbidden Recovery Behaviors

```text
blind retry UNKNOWN Effect
UNKNOWN → FAILED without proof
silent Approval recreation
fencing token reuse
trust worker-local ownership
trust corrupt checkpoint over EffectStore
generic external write retry
critical repair without audit
```

---

# 203. Runbooks candidats

```text
RUNBOOK_WORKER_CRASH
RUNBOOK_WORKER_FREEZE
RUNBOOK_LEASE_TAKEOVER
RUNBOOK_DB_OUTAGE
RUNBOOK_EFFECT_UNKNOWN
RUNBOOK_RECONCILIATION_STUCK
RUNBOOK_APPROVAL_STUCK
RUNBOOK_RUNTIME_LOST
RUNBOOK_CHECKPOINT_CORRUPT
RUNBOOK_POST_RESTORE
RUNBOOK_GIT_PUSH_UNKNOWN
RUNBOOK_DEPLOYMENT_UNKNOWN
```

---

# 204. Acceptance Criteria

Le système est conforme si :

1. un Run survit à la mort de son worker ;
2. SIGKILL ne nécessite aucune cleanup pour préserver la sûreté ;
3. un worker gelé puis repris est correctement fenced ;
4. `Effect.SUCCEEDED` n’est jamais rejoué implicitement ;
5. `Effect.UNKNOWN` passe par reconciliation ;
6. DB outage bloque les Protected Effects si ownership/authority non prouvable ;
7. Approval survit aux restarts ;
8. takeover produit un token strictement supérieur ;
9. checkpoint corruption ne détruit pas les garanties de safety ;
10. runtime restart respecte l’historique durable des Effects ;
11. duplicate messaging ne produit pas de duplicate business action ;
12. restore/PITR possède un safety gate ;
13. coding-agent remote Effects sont réconciliés ;
14. chaque recovery critique est observable et auditable ;
15. les scénarios impossibles à prouver automatiquement peuvent finir en intervention humaine.

---

# 205. Questions ouvertes

```text
Q-REC-01 Faut-il persister RecoveryPlan ?
Q-REC-02 STARTED devient-il automatiquement UNKNOWN après lease loss ?
Q-REC-03 Quel délai avant classification stale STARTED ?
Q-REC-04 Comment versionner RecoveryPolicy ?
Q-REC-05 Quel modèle générique pour proof-of-send ?
Q-REC-06 Quel comportement runtime exact pendant outage DB ?
Q-REC-07 Quelle stratégie post-restore pour fencing epoch ?
Q-REC-08 Comment représenter un succès externe constaté hors PyAgentsKit ?
Q-REC-09 Faut-il une FaultInjection API officielle ?
Q-REC-10 Quels seuils imposent manual review ?
Q-REC-11 Que faire avec un connector sans lookup/reconciliation ?
Q-REC-12 Quelle durée maximale de graceful shutdown ?
```

---

# 206. ADR induits

```text
ADR-REC-001 RecoveryPlanner contract
ADR-REC-002 STARTED-to-UNKNOWN classification
ADR-REC-003 Lease-loss behavior
ADR-REC-004 Runtime restart policy
ADR-REC-005 Checkpoint fallback
ADR-REC-006 Post-restore safety gate
ADR-REC-007 Manual Effect resolution
ADR-REC-008 Recovery observability
ADR-REC-009 Fault injection points
ADR-REC-010 Coding-agent recovery
ADR-REC-011 PostgreSQL outage behavior
ADR-REC-012 Recovery policy versioning
```

---

# 207. Definition of Done

Le modèle Failure & Recovery est mature lorsque :

1. chaque fenêtre de crash critique possède un test ;
2. SIGTERM, SIGKILL et SIGSTOP sont couverts ;
3. takeover est testé avec plusieurs processus réels ;
4. stale worker est rejeté après reprise ;
5. PostgreSQL outage et restart sont testés ;
6. chaque état Effect possède une règle de recovery ;
7. reconciliation est testée sur de vraies ambiguïtés ;
8. approvals survivent aux restarts ;
9. native resume et logical restart sont testés ;
10. checkpoints corrompus sont couverts ;
11. webhook/queue duplicates sont couverts ;
12. restore/PITR est qualifié ;
13. coding-agent remote writes sont couverts ;
14. audit/traces reconstruisent chaque recovery ;
15. aucun scénario critique ne dépend d’un graceful shutdown ;
16. les cas non prouvables basculent proprement en manual intervention ;
17. les tests sont exécutés avec PostgreSQL réel ;
18. tous les production blockers sont verts.

---

# 208. Résumé

La reprise PyAgentsKit repose sur :

```text
DURABLE STATE
+
AUTHORITATIVE OWNERSHIP
+
FENCING
+
EFFECT SAFETY
+
RECONCILIATION
+
APPROVAL REVALIDATION
+
RUNTIME INSPECTION
+
DETERMINISTIC RECOVERY PLANNING
```

Les distinctions fondamentales sont :

```text
RETRY ≠ RECOVERY ≠ RECONCILIATION
PROCESS ALIVE ≠ OWNER
TIMEOUT ≠ FAILURE
UNKNOWN ≠ FAILED
CHECKPOINT ≠ SOURCE OF TRUTH FOR EFFECTS
```

> **Après une panne, PyAgentsKit ne doit pas chercher à continuer le plus vite possible ; il doit d’abord prouver quelle continuation est sûre.**

Le document suivant naturel est :

```text
26_PYAGENTSKIT_TEST_STRATEGY.md
```
