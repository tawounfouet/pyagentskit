# PyAgentsKit — Performance & Capacity Model

**Document :** `../operations/43_PYAGENTSKIT_PERFORMANCE_AND_CAPACITY_MODEL.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Performance Engineering & Capacity Planning  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../operations/41_PYAGENTSKIT_DEPLOYMENT_AND_OPERATIONS.md`
- `../operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md`
- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`

---

# 1. Objet

Ce document définit le **modèle de performance et de capacité** de PyAgentsKit V2.

Il formalise :

- les dimensions de charge ;
- les budgets de latence ;
- les unités de capacité ;
- les paramètres de concurrence ;
- le dimensionnement des workers ;
- le dimensionnement PostgreSQL ;
- le dimensionnement des leases et heartbeats ;
- les limites des stores et queues ;
- la backpressure ;
- les quotas et fairness ;
- les scénarios de saturation ;
- les tests de charge ;
- les critères de qualification ;
- les règles de tuning ;
- les anti-patterns de performance.

Le principe directeur est :

> **La performance de PyAgentsKit ne se mesure pas seulement en requêtes par seconde ; elle se mesure dans sa capacité à rester sûre, prévisible et récupérable sous charge.**

---

# 2. Principes fondamentaux

PyAgentsKit ne doit jamais optimiser au prix de :

```text
duplicate Effect
lost Approval
stale fencing acceptance
unknown outcome hidden
cross-tenant starvation
unbounded recovery storm
```

La hiérarchie est :

```text
1. Safety
2. Correctness
3. Recoverability
4. Predictability
5. Throughput
6. Latency optimization
```

---

# 3. Performance != Throughput Only

Les dimensions principales sont :

```text
Latency
Throughput
Concurrency
Queue depth
Database load
Lease renewal load
Recovery load
External dependency latency
Artifact volume
Audit volume
Memory footprint
CPU utilization
I/O pressure
```

---

# 4. Capacity Unit

Une unité de capacité doit être exprimée en termes de :

```text
active Runs
active RuntimeInvocations
Effects/sec
Approvals/sec
Lease renewals/sec
messages/sec
audit events/sec
artifact bytes/sec
recovery scans/sec
```

---

# 5. Workload classes

PyAgentsKit doit distinguer plusieurs classes de charge.

## WLC-01 — Short interactive Run

```text
duration: seconds
few tool calls
low state volume
human-visible latency important
```

## WLC-02 — Long-running autonomous Run

```text
duration: minutes/hours
many events
checkpointing
external dependencies
```

## WLC-03 — Effect-heavy Run

```text
many external writes
high audit volume
high idempotency pressure
```

## WLC-04 — Approval-heavy Run

```text
frequent WAITING states
long idle durations
low CPU, high durable state count
```

## WLC-05 — Coding Agent Run

```text
workspace
commands
large artifacts
long runtimes
git Effects
```

## WLC-06 — Recovery Storm

```text
many Runs recovering simultaneously
lease takeover
runtime inspection
effect reconciliation
```

---

# 6. Performance objectives

Les objectifs doivent être exprimés comme :

```text
SLO
not
single benchmark number
```

Exemples :

```text
p95 Run command latency
p99 Effect reservation latency
max lease renewal delay
max recovery detection time
max outbox lag
max audit append delay
```

---

# 7. Core Latency Budget

Pour un use case sans appel externe :

```text
Inbound Adapter
→ Application
→ Repository
→ Domain
→ Commit
→ Response
```

Le budget doit rester dominé par :

```text
database round trips
```

et non par surcharge framework interne.

---

# 8. Latency categories

```text
L0 In-process pure domain
L1 local persistence
L2 PostgreSQL transaction
L3 runtime call
L4 external connector
L5 human approval
```

---

# 9. L0 target

Les opérations purement Domain/Application doivent rester :

```text
sub-millisecond to low-millisecond
```

dans la majorité des cas.

Leur coût ne doit pas devenir visible devant I/O.

---

# 10. L1 target

Memory/SQLite local operations :

```text
single-digit milliseconds typical
```

hors contention/disque lent.

---

# 11. L2 target

PostgreSQL critical transactions :

```text
low tens of milliseconds target
```

en conditions normales.

---

# 12. L3/L4 rule

Runtime ou Connector latency domine souvent.

PyAgentsKit doit :

```text
measure
bound
timeout
classify outcome
```

mais ne pas prétendre contrôler la latence du provider.

---

# 13. L5 rule

Human approval peut durer :

```text
minutes
hours
days
```

Le système doit rester peu coûteux lorsqu’un Run attend.

---

# 14. Idle Runs

Un Run `WAITING` doit consommer :

```text
durable storage
almost zero active CPU
no long-lived Python task
```

---

# 15. No thread-per-run

Interdit comme modèle de scale principal :

```text
one OS thread per durable Run
```

---

# 16. No process-per-run requirement

Un Run durable ne doit pas nécessiter un process dédié lorsqu’il est inactif.

---

# 17. Active vs Durable Population

Distinguer :

```text
N_durable_runs
N_active_runs
```

Typiquement :

```text
N_durable_runs >> N_active_runs
```

---

# 18. Fundamental concurrency formula

Approximation :

```text
required_active_slots
≈
arrival_rate × average_active_service_time
```

Little’s Law :

```text
L = λW
```

---

# 19. Worker capacity

Pour un worker :

```text
C_worker
=
min(
    runtime_concurrency_limit,
    DB_safe_concurrency,
    connector_safe_concurrency,
    CPU_limit,
    memory_limit
)
```

---

# 20. Cluster capacity

Approximation :

```text
C_cluster
=
Σ C_worker
```

moins réserve pour :

```text
recovery
maintenance
headroom
```

---

# 21. Capacity headroom

Production ne doit pas tourner à 100 %.

Recommandation initiale :

```text
steady-state target <= 60–70% of proven safe capacity
```

à ajuster après qualification.

---

# 22. Why headroom

Pour absorber :

```text
traffic spikes
worker loss
recovery storms
provider slowdown
maintenance
```

---

# 23. Worker concurrency

Le nombre de Runs actifs par worker dépend du workload.

I/O-heavy :

```text
high async concurrency possible
```

CPU-heavy :

```text
lower concurrency
```

coding agent :

```text
often resource-heavy workspace/process
```

---

# 24. Runtime-specific concurrency

Chaque Runtime Adapter doit déclarer ou documenter :

```text
recommended concurrency
hard limit
memory cost
provider rate limits
```

---

# 25. Connector-specific concurrency

Même règle.

---

# 26. Global vs per-adapter limits

Préférer plusieurs budgets :

```text
global worker concurrency
runtime concurrency
connector concurrency
tenant concurrency
protected Effect concurrency
```

---

# 27. Backpressure

Le système doit ralentir les admissions avant saturation complète.

---

# 28. Backpressure signals

Exemples :

```text
DB pool saturation
outbox lag
lease renewal delay
worker active slots
connector 429
runtime throttling
memory pressure
```

---

# 29. Admission control

Un worker peut refuser de nouveaux Runs si :

```text
not ready
draining
capacity exhausted
critical dependency degraded
```

---

# 30. Queue depth

Queue depth doit être observable.

Mais :

```text
queue depth != ownership
```

---

# 31. Queue wait SLO

Mesurer :

```text
time from ready-to-run
to
worker admission
```

---

# 32. Fairness

Un tenant ne doit pas monopoliser toute la capacité si multi-tenant.

---

# 33. Tenant quotas

Candidats :

```text
max active Runs
max Effects/sec
max runtime concurrency
max connector concurrency
max artifact bytes
```

---

# 34. Burst allowance

Quota peut avoir :

```text
steady rate
burst
```

selon stratégie.

---

# 35. Worker sizing dimensions

Pour chaque worker :

```text
CPU
RAM
file descriptors
network sockets
DB connections
workspace disk
subprocess limit
```

---

# 36. Memory model

Approximation :

```text
RAM_worker
=
base_process
+
Σ active_runtime_state
+
Σ connector buffers
+
workspace overhead
+
safety margin
```

---

# 37. Avoid keeping full history in RAM

Conserver en mémoire uniquement :

```text
working set
```

Le reste vit dans persistence.

---

# 38. Large conversation histories

Runtime adapters doivent pouvoir :

```text
stream
paginate
summarize
or retrieve selectively
```

selon runtime.

---

# 39. Artifact memory rule

Ne pas charger des gros Artifacts entièrement en RAM sans nécessité.

---

# 40. Streaming artifacts

Préférer :

```text
streaming I/O
```

pour gros blobs.

---

# 41. PostgreSQL role

PostgreSQL porte notamment :

```text
Run state
Effect state
Approvals
Leases
RuntimeInvocations
Outbox/Inbox
Audit metadata
```

---

# 42. DB capacity dimensions

```text
transactions/sec
connections
active queries
lock contention
WAL volume
table growth
index size
vacuum load
```

---

# 43. Connection pool model

Approximation cluster :

```text
DB_connections
=
workers × pool_size
+
API_instances × api_pool
+
ops/migration reserve
```

---

# 44. Pool sizing warning

Un pool plus grand n’augmente pas nécessairement le throughput.

Il peut augmenter :

```text
contention
context switching
DB memory use
```

---

# 45. Initial pool heuristic

Commencer petit :

```text
5–10 connections per process
```

pour workloads async typiques, puis benchmarker.

Pas une constante normative.

---

# 46. Pool pressure metric

Mesurer :

```text
pool_wait_seconds
```

et saturation.

---

# 47. DB transaction duration

Transactions critiques doivent être :

```text
short
```

---

# 48. No remote call in open transaction

Déjà invariant architectural et performance.

---

# 49. Query N+1

Read Models et timelines doivent éviter :

```text
N+1 repository queries
```

---

# 50. Batch reads

Utiliser :

```text
bulk queries
joins
read projections
```

sur query side.

---

# 51. Write amplification

Surveiller :

```text
Run update
Effect update
Audit append
Outbox append
```

par action logique.

---

# 52. Audit volume

Approximation :

```text
audit_events_per_run
×
runs_per_day
```

---

# 53. Audit storage

```text
daily_audit_bytes
=
events/day × avg_event_size
```

---

# 54. Audit partitioning trigger

À envisager si :

```text
table/index size
retention
vacuum/query cost
```

le justifient.

Pas avant.

---

# 55. Outbox throughput

L’Outbox doit supporter le pic de :

```text
domain state transitions producing integration events
```

---

# 56. Outbox lag

Metric clé :

```text
now - oldest_unpublished_event.created_at
```

---

# 57. Outbox SLO

Doit être inférieur à un seuil défini par environnement.

---

# 58. Inbox throughput

Dimensionnée sur :

```text
external event deliveries
+
redeliveries
```

---

# 59. Inbox duplicate rate

Doit être mesuré pour comprendre le broker/provider.

---

# 60. Lease model

Les Leases créent une charge périodique.

---

# 61. Lease variables

```text
TTL
heartbeat/renew interval
worker count
active leased resources
```

---

# 62. Renewal rate

Approximation :

```text
renewals_per_second
=
active_leases / renewal_interval_seconds
```

---

# 63. Example

Si :

```text
10,000 active leases
renew every 10s
```

alors :

```text
~1,000 renewals/sec
```

---

# 64. Capacity consequence

Le choix TTL/heartbeat est un paramètre de performance majeur.

---

# 65. TTL trade-off

TTL court :

```text
faster failure detection
higher DB load
more false expiry risk under pauses
```

TTL long :

```text
lower DB load
slower takeover
longer stale-worker window before fencing generation changes
```

---

# 66. Renewal interval rule

Recommandation initiale :

```text
renewal_interval
≈
TTL / 3
```

comme point de départ.

À qualifier.

---

# 67. Lease jitter

Ajouter un léger jitter peut éviter :

```text
synchronized renewal spikes
```

---

# 68. Renewal deadline

Le worker doit considérer un lease en danger bien avant l’expiration réelle.

---

# 69. Lease loss handling

Si renouvellement échoue de manière critique :

```text
stop admitting protected Effects
```

avant expiration supposée si l’autorité ne peut plus être prouvée.

---

# 70. Heartbeat vs lease renewal

Ne pas forcément utiliser la même cadence.

---

# 71. Worker heartbeat purpose

```text
operational visibility
```

Lease renewal purpose :

```text
authority
```

---

# 72. Fencing capacity

La génération du token doit être :

```text
serialized per resource
```

mais pas globalement.

---

# 73. Hot resource risk

Une ressource avec takeovers fréquents peut devenir hot row.

---

# 74. Hot resource mitigation

```text
reduce unnecessary takeover
improve worker stability
partition resource identities naturally
```

---

# 75. Effect reservation load

Protected Effects créent des transactions de réservation.

---

# 76. Effect write path

Typiquement :

```text
reserve
mark STARTED
mark outcome
audit
outbox
```

Plusieurs writes par Effect.

---

# 77. Effect throughput model

Approximation DB writes :

```text
DB_writes_per_effect
≈
2–5+
```

selon audit/outbox.

---

# 78. Effect throughput capacity

Doit être benchmarkée indépendamment du runtime.

---

# 79. External Effect rate limits

Le provider peut être la limite réelle.

---

# 80. Rate limit model

Par Connector :

```text
requests/sec
concurrency
burst
daily quota
```

---

# 81. 429 behavior

Les 429 peuvent autoriser retry selon méthode/provider.

Mais retry safe doit rester explicite.

---

# 82. Retry amplification

Sous panne, retries peuvent multiplier la charge.

---

# 83. Retry budget

Définir :

```text
max attempts
backoff
jitter
deadline
```

par catégorie.

---

# 84. No retry storm

Appliquer :

```text
exponential backoff
jitter
circuit breaker if appropriate
```

pour transports sûrs.

---

# 85. Recovery storm

Un restart cluster peut rendre des milliers de Runs récupérables.

---

# 86. Recovery admission control

Recovery doit avoir :

```text
bounded concurrency
batch scanning
priorities
```

---

# 87. Recovery priority

Exemple :

```text
P0 active protected Effects
P1 Runs holding expired ownership
P2 ordinary resumable Runs
P3 background cleanup
```

---

# 88. Recovery scanner

Ne pas scanner toute la table :

```text
SELECT * FROM runs
```

à haute fréquence.

---

# 89. Recovery indexes

Candidats :

```text
runs(state, updated_at)
effects(status, updated_at)
leases(expires_at)
approvals(status, expires_at)
```

---

# 90. Recovery scan batching

Utiliser :

```text
LIMIT
cursor
SKIP LOCKED where appropriate
```

---

# 91. Recovery throughput

Metric :

```text
runs_recovered/sec
```

---

# 92. Recovery backlog

Metric :

```text
recoverable_runs_pending
```

---

# 93. Recovery lag

```text
now - recovery_eligible_at
```

---

# 94. Runtime call capacity

Chaque runtime a :

```text
latency distribution
rate limits
session limits
token limits
cost limits
```

---

# 95. Runtime adapter metrics

```text
start_latency
resume_latency
inspect_latency
runtime_errors
runtime_throttles
active_invocations
```

---

# 96. Streaming runtimes

Streaming réduit time-to-first-output mais peut augmenter :

```text
connection duration
socket count
memory buffers
```

---

# 97. Streaming capacity

Dimensionner :

```text
concurrent streams
```

séparément.

---

# 98. Human approval capacity

Le volume durable peut être important même avec faible throughput.

---

# 99. Pending approvals

Metric :

```text
pending_approvals_total
```

---

# 100. Approval age

Distribution :

```text
approval_wait_seconds
```

---

# 101. Approval expiry sweeper

Doit être batché et indexé.

---

# 102. Conversations capacity

Dimensions :

```text
messages/sec
messages/conversation
bytes/message
conversation age
```

---

# 103. Large message risk

Limiter ou externaliser :

```text
attachments
huge tool outputs
```

---

# 104. Message payload policy

Ne pas stocker duplique :

```text
large artifacts
```

dans Messages si ArtifactReference suffit.

---

# 105. Artifacts capacity

Dimensions :

```text
artifact count
average size
max size
throughput
retention
```

---

# 106. Blob throughput

Object storage scale est souvent supérieur à DB.

La DB ne doit contenir que metadata/reference.

---

# 107. Artifact upload pattern

```text
stream upload
checksum
register metadata
```

---

# 108. Artifact reconciliation

En cas de partial failure :

```text
orphan blob
orphan metadata
```

cleanup/reconciliation périodique.

---

# 109. Disk capacity for coding agents

Workspace-heavy workloads peuvent dominer.

---

# 110. Workspace quota

Définir :

```text
max bytes/workspace
max files
max command duration
```

---

# 111. Subprocess capacity

Coding runtime :

```text
max concurrent subprocesses
```

par worker.

---

# 112. File descriptor capacity

Streaming + subprocess + DB + HTTP utilisent des FDs.

Surveiller :

```text
open_fds / limit
```

---

# 113. Network capacity

Metrics :

```text
bytes in/out
connection count
external latency
TLS setup cost
```

---

# 114. DNS dependency

Sous scale, DNS failures peuvent amplifier les erreurs.

---

# 115. Connection reuse

HTTP clients doivent utiliser :

```text
connection pooling
keep-alive
```

lorsque provider compatible.

---

# 116. Timeout hierarchy

Définir :

```text
connect timeout
read timeout
operation timeout
use-case deadline
```

---

# 117. Deadline propagation

Propager les deadlines sans confondre expiration caller et vérité externe.

---

# 118. Time budget

Un use case peut décomposer :

```text
T_total
=
T_db
+
T_runtime
+
T_connector
+
T_queue
+
T_internal
```

---

# 119. SLO proposal — command plane

Première cible de qualification, à ajuster :

```text
p95 simple durable command < 100 ms
p99 < 250 ms
```

hors external runtime/provider.

Ce sont des objectifs de départ, pas promesses finales.

---

# 120. SLO proposal — Effect reservation

```text
p95 < 50 ms
p99 < 150 ms
```

sur PostgreSQL sain et localement proche.

À benchmarker.

---

# 121. SLO proposal — Lease renew

Le critère important est :

```text
renew complete well before expiry
```

plus qu’une latence utilisateur.

---

# 122. Renewal SLO

Exemple :

```text
p99 renewal latency < 10% of TTL
```

comme principe de sécurité.

---

# 123. Recovery detection SLO

Exemple :

```text
eligible Run discovered within one scan interval + bounded DB delay
```

---

# 124. Recovery completion SLO

Dépend du type de blocker.

Séparer :

```text
automatic recovery
reconciliation
human intervention
```

---

# 125. Outbox SLO

Exemple :

```text
p99 publish lag < 5s
```

selon use case.

---

# 126. Read API SLO

Read models :

```text
p95 < 200 ms
```

pour vues simples peut être un objectif initial.

---

# 127. SLO warning

Les chiffres ci-dessus doivent être remplacés par des mesures réelles avant GA.

---

# 128. Capacity testing levels

```text
PERF-L0 microbenchmark
PERF-L1 component load
PERF-L2 integration load
PERF-L3 distributed load
PERF-L4 failure-under-load
```

---

# 129. PERF-L0

Benchmarker :

```text
state transitions
serialization
fingerprint computation
policy evaluation
```

---

# 130. PERF-L1

Benchmarker :

```text
RunRepository
EffectRepository
LeaseRepository
Outbox
AuditStore
```

---

# 131. PERF-L2

Benchmarker :

```text
Application use case + PostgreSQL
```

---

# 132. PERF-L3

Benchmarker :

```text
multiple workers
real DB
concurrent leases
real adapters
```

---

# 133. PERF-L4

Benchmarker sous :

```text
worker kill
DB slowdown
connector latency
provider throttling
recovery storm
```

---

# 134. Benchmark reproducibility

Chaque benchmark doit enregistrer :

```text
commit SHA
Python version
DB version
machine
CPU
RAM
network
dataset size
concurrency
configuration
```

---

# 135. Benchmark warmup

Séparer :

```text
cold start
warm steady-state
```

---

# 136. Benchmark duration

Tests de quelques secondes ne suffisent pas pour :

```text
vacuum
pool saturation
memory leak
lease drift
```

---

# 137. Soak tests

Durée recommandée :

```text
hours
```

pour qualification finale.

---

# 138. Load test scenarios

## LT-01 — Run creation burst

```text
many CreateRun
```

## LT-02 — Effect reservation burst

```text
same/different idempotency keys
```

## LT-03 — Lease renew pressure

```text
many active leases
```

## LT-04 — Takeover burst

```text
worker cohort dies
```

## LT-05 — Approval backlog

```text
many WAITING Runs
```

## LT-06 — Outbox spike

```text
many events published
```

## LT-07 — Recovery storm

```text
DB or worker outage recovery
```

## LT-08 — Coding workloads

```text
workspace + subprocess + artifacts
```

---

# 139. Saturation test

Augmenter la charge jusqu’à :

```text
latency cliff
error growth
renewal risk
```

---

# 140. Safe capacity

Définie avant le point de saturation.

---

# 141. Capacity envelope

Pour chaque profile :

```text
recommended
tested max
unsafe/unqualified
```

---

# 142. Example capacity card

```text
Profile: Distributed PostgreSQL
Workers: 4
Worker concurrency: 50
DB pool: 10/worker
Lease TTL: 30s
Renew: 10s
Qualified active leases: X
Qualified Effects/sec: Y
Qualified Runs/sec: Z
```

Les valeurs X/Y/Z viennent des benchmarks, jamais de suppositions.

---

# 143. Capacity profiles

Publier au moins :

```text
Local Dev
Small Production
Medium Production
High-Concurrency Production
Coding-Agent Heavy
```

---

# 144. Local Dev

Priorité :

```text
simplicity
```

Pas performance maximale.

---

# 145. Small Production

Exemple de profil conceptuel :

```text
2 workers
PostgreSQL
moderate concurrency
```

afin de tester takeover réel.

---

# 146. Medium Production

Plusieurs workers, DB dédiée, external storage.

---

# 147. High-Concurrency

Nécessite qualification spécifique :

```text
DB sizing
renewal load
outbox
rate limits
```

---

# 148. Coding-Agent Heavy

Nécessite :

```text
more CPU/RAM/disk
lower worker concurrency
```

---

# 149. Capacity planning formula — arrivals

Si :

```text
λ = new Runs/sec
W_active = average active runtime seconds
```

alors :

```text
concurrent active Runs ≈ λ × W_active
```

---

# 150. Example

```text
2 Runs/sec
average active time 30s
```

donne environ :

```text
60 active Runs
```

hors waiting durable.

---

# 151. Waiting population

Si Approval wait moyen = 4h :

```text
waiting population
=
approval arrival rate × 4h
```

Storage, pas worker slots.

---

# 152. Database storage model

Approximation :

```text
storage/day
=
Run rows
+
Effect rows
+
Messages
+
Audit
+
Outbox/Inbox
+
Artifact metadata
```

---

# 153. Blob storage model

```text
blob_storage/day
=
artifact_count × avg_artifact_size
```

---

# 154. Retention model

```text
retained_storage
=
daily_growth × retention_days
```

ajusté par purge/archive.

---

# 155. WAL growth

Élevé avec :

```text
frequent renewals
audit append
effect updates
```

Doit être benchmarké.

---

# 156. Lease renewal write amplification

Un design écrivant chaque renewal peut devenir coûteux à très grande échelle.

---

# 157. Future optimization candidates

Uniquement si besoin démontré :

```text
batched heartbeat
separate operational heartbeat store
reduced audit on renew
partitioning
```

sans affaiblir l’autorité.

---

# 158. No premature optimization

Le modèle initial doit privilégier :

```text
correctness
simplicity
observability
```

---

# 159. Capacity alert thresholds

Candidats :

```text
DB pool > 80%
worker slots > 80%
renewal p99 > TTL/10
outbox lag > SLO
recoverable backlog increasing
memory > 80%
disk > 80%
```

---

# 160. Early warning

Alerter avant saturation, pas après.

---

# 161. Autoscaling inputs

Candidats :

```text
ready Run backlog
active slots utilization
CPU
runtime concurrency
```

---

# 162. Autoscaling caveat

Ne pas scaler uniquement sur CPU pour workloads I/O-heavy.

---

# 163. Scale-out limit

PostgreSQL ou provider quotas peuvent devenir bottleneck avant workers.

---

# 164. Scale-in safety

Avant suppression worker :

```text
drain
stop admissions
allow bounded completion
```

mais safety ne doit pas dépendre du drain.

---

# 165. Worker startup storm

Nouveaux workers ne doivent pas tous scanner les mêmes Runs agressivement.

---

# 166. Startup jitter

Utiliser jitter/backoff sur scanners si nécessaire.

---

# 167. Cache strategy

Cache seulement pour :

```text
non-authoritative reads
configuration
static descriptors
```

---

# 168. Never cache authority blindly

Ne pas utiliser cache stale pour :

```text
current Lease
Effect status
Approval decision
fencing token
```

---

# 169. Read Model cache

Possible avec TTL si cohérence éventuelle acceptable.

---

# 170. Serialization cost

Surveiller payloads JSON lourds.

---

# 171. Avoid giant JSONB aggregates

Déjà règle persistence.

Améliore aussi performance et concurrency.

---

# 172. Index cost

Chaque index accélère reads mais coûte writes/storage.

---

# 173. Index review

Basé sur :

```text
actual query plans
```

---

# 174. EXPLAIN ANALYZE

Obligatoire pour queries critiques avant optimisation.

---

# 175. Slow query budget

Définir seuils par environnement.

---

# 176. Vacuum / autovacuum

Surveiller particulièrement :

```text
leases
workers
effects
outbox
```

---

# 177. Hot update tables

Éviter payload large sur tables mises à jour fréquemment.

---

# 178. Audit append table

Peut être optimisée différemment.

---

# 179. Time-series metrics

Ne jamais stocker toutes les métriques dans PostgreSQL applicatif par défaut.

Utiliser observability backend.

---

# 180. Cardinality control

Metrics labels interdits :

```text
run_id
effect_id
conversation_id
```

dans les séries générales.

---

# 181. Trace sampling

Sous forte charge :

```text
sampling
```

possible pour traces ordinaires.

Mais critical Audit reste durable.

---

# 182. Logging volume

Limiter logs par événement répétitif.

---

# 183. Lease log storm

Ne pas loguer chaque renew en INFO à très grand volume.

---

# 184. Audit vs Log

Les actions critiques restent auditées même si logs échantillonnés.

---

# 185. Cost model

Performance doit inclure coûts :

```text
DB
runtime provider
LLM tokens
object storage
egress
observability
```

---

# 186. Cost per Run

Candidat :

```text
C_run
=
C_runtime
+
C_llm
+
C_db
+
C_effects
+
C_storage
+
C_observability
```

---

# 187. Cost budget

Peut être policy/application-level pour certains usages.

---

# 188. LLM token capacity

Si Native Runtime utilise LLM :

```text
tokens/sec
requests/min
provider quota
```

peut dominer.

---

# 189. Provider budget exhaustion

Doit devenir :

```text
WAITING / provider unavailable / policy outcome
```

selon modèle, pas crash anarchique.

---

# 190. Backpressure to runtime

Si connector saturated :

```text
do not continue generating unlimited pending Effects
```

---

# 191. Pending Effect bound

Définir une limite ou policy sur :

```text
unexecuted pending Effects per Run
```

---

# 192. Event buffer bound

Runtime events en mémoire doivent être bornés.

---

# 193. Slow consumer

Appliquer backpressure ou spill durable.

---

# 194. Stream disconnect

Ne pas perdre la vérité durable.

---

# 195. Capacity under outage

Le système doit définir :

```text
what continues
what waits
what rejects
```

---

# 196. DB outage

En général :

```text
new protected actions stop
```

car durable authority indisponible.

---

# 197. Telemetry outage

Peut continuer selon profile.

---

# 198. Audit outage

En High Assurance :

```text
may fail closed
```

si audit critique obligatoire.

---

# 199. Runtime outage

Runs concernés :

```text
WAITING
```

ou retry safe suivant policy.

---

# 200. Connector outage

Protected Effects non envoyés restent :

```text
NOT_STARTED
```

si absence de send.

---

# 201. Capacity during partial outage

Réduire admissions pour éviter backlog incontrôlé.

---

# 202. Brownout mode

Option :

```text
disable expensive non-critical features
```

tout en conservant safety.

---

# 203. Circuit breakers

Peuvent protéger dependencies.

Ne doivent pas transformer UNKNOWN en FAILED.

---

# 204. Bulkheads

Séparer pools/concurrency entre :

```text
runtime providers
connectors
tenants
```

pour limiter blast radius.

---

# 205. Tenant noisy-neighbor protection

Utiliser :

```text
quotas
fair queues
per-tenant concurrency
```

---

# 206. Priority classes

Exemple :

```text
CRITICAL_RECOVERY
INTERACTIVE
STANDARD
BACKGROUND
```

---

# 207. Priority inversion

Éviter qu’un gros batch background bloque recovery critique.

---

# 208. Capacity reservations

Réserver une fraction pour :

```text
recovery
ops
critical Effects
```

si nécessaire.

---

# 209. Performance test data

Doit refléter :

```text
realistic message sizes
effect counts
approval waits
artifact sizes
```

---

# 210. Synthetic-only risk

Des payloads minuscules donnent des résultats trompeurs.

---

# 211. Production telemetry feedback

Après GA, recalibrer le modèle avec observations réelles.

---

# 212. Performance regression CI

Microbenchmarks stables peuvent détecter :

```text
large regressions
```

mais ne doivent pas être trop bruités.

---

# 213. Regression threshold

Exemple :

```text
>20% regression
```

déclenche review, selon benchmark variance.

---

# 214. Load test automation

Prévoir scripts reproductibles dans :

```text
tests/performance/
```

ou :

```text
benchmarks/
```

---

# 215. Suggested benchmark topology

```text
benchmarks/
├── domain/
├── repositories/
├── leases/
├── effects/
├── outbox/
├── recovery/
└── end_to_end/
```

---

# 216. Test harness

Doit pouvoir paramétrer :

```text
workers
concurrency
duration
DB size
lease TTL
failure injection
```

---

# 217. Qualification report

Chaque run produit :

```text
throughput
latency percentiles
errors
DB load
pool waits
lease delays
recovery lag
resource usage
```

---

# 218. Percentiles

Toujours publier :

```text
p50
p95
p99
max
```

---

# 219. Average is insufficient

Les distributed systems failures apparaissent souvent dans les tails.

---

# 220. Tail latency

Très importante pour :

```text
lease renew
commit
recovery
```

---

# 221. Coordinated omission

Le benchmark doit éviter de masquer la dégradation quand le système ralentit.

---

# 222. Open-loop vs closed-loop testing

Utiliser les deux selon scénario.

---

# 223. Closed-loop

Mesure capacité sous clients attendant réponse.

---

# 224. Open-loop

Mesure réaction à un arrival rate externe constant.

---

# 225. Soak memory leak check

Suivre :

```text
RSS
objects
FDs
connections
threads/tasks
```

---

# 226. Python async task leak

Surveiller tâches non terminées après Run completion/cancellation.

---

# 227. GC pressure

Gros payloads/messages peuvent créer pression GC.

---

# 228. CPU profiling

Avant optimisation, profiler.

---

# 229. I/O profiling

Beaucoup de workloads PyAgentsKit seront I/O-bound.

---

# 230. Capacity documentation

Publier des recommandations sous forme :

```text
tested profile
not theoretical claim
```

---

# 231. Sizing worksheet

Pour un deployment :

```text
expected Runs/day
peak Runs/sec
avg active time
peak active Runs
effects/run
messages/run
artifact MB/run
approval wait
active leases
```

---

# 232. Derived metrics

Calculer :

```text
active slots
renewals/sec
DB writes/sec
audit events/sec
storage/day
```

---

# 233. Example sizing flow

```text
Workload inputs
↓
Concurrency estimate
↓
Worker count
↓
Lease load
↓
DB write load
↓
Storage growth
↓
Headroom
```

---

# 234. Capacity planner future

Un CLI/calculator peut être ajouté plus tard.

Pas nécessaire au core V2.

---

# 235. Performance anti-pattern — optimize average latency only

Interdit.

---

# 236. Anti-pattern — ignore waiting population

Un million de WAITING Runs peut être peu coûteux CPU mais lourd en storage/indexing.

---

# 237. Anti-pattern — oversize connection pools

Déjà établi.

---

# 238. Anti-pattern — unbounded async concurrency

Peut provoquer :

```text
memory explosion
provider throttling
socket exhaustion
```

---

# 239. Anti-pattern — retry storm

Déjà établi.

---

# 240. Anti-pattern — lease renewal synchronized

Utiliser jitter.

---

# 241. Anti-pattern — recovery all-at-once

Batcher.

---

# 242. Anti-pattern — log every heartbeat

Réduit signal et augmente coût.

---

# 243. Anti-pattern — preload all messages

Paginer/streamer.

---

# 244. Anti-pattern — large DB transactions

Dégrade locks, recovery et latency.

---

# 245. Anti-pattern — giant audit payloads

Audit minimal, evidence référencée si volumineuse.

---

# 246. Anti-pattern — one worker pool for everything

Des workloads lourds peuvent affamer les tâches critiques.

---

# 247. Workload isolation

Possibilité de pools spécialisés :

```text
general
coding
recovery
connector-heavy
```

---

# 248. Specialized workers

Seulement si nécessaire.

Le modèle de Run reste commun.

---

# 249. Capacity invariants

```text
PERF-INV-01
Safety-critical state is never served from stale cache for performance.

PERF-INV-02
External Effects are never moved inside long DB transactions to reduce latency.

PERF-INV-03
Lease renewal load is bounded and observable.

PERF-INV-04
Recovery concurrency is bounded.

PERF-INV-05
Retries are bounded and jittered where applicable.

PERF-INV-06
WAITING Runs do not consume active worker slots.

PERF-INV-07
Large Artifacts are streamed or externally stored.

PERF-INV-08
Provider rate limits are explicit capacity constraints.

PERF-INV-09
Performance optimizations cannot weaken fencing/idempotency.

PERF-INV-10
Capacity claims are backed by reproducible tests.
```

---

# 250. Performance metrics catalog

## Run

```text
runs_created_total
runs_active
runs_waiting
run_command_latency_seconds
run_queue_wait_seconds
```

## Effects

```text
effects_reserved_total
effects_started_total
effects_succeeded_total
effects_unknown_total
effect_reservation_latency_seconds
effect_execution_latency_seconds
```

## Coordination

```text
leases_active
lease_acquire_latency_seconds
lease_renew_latency_seconds
lease_renew_failures_total
lease_takeovers_total
```

## Recovery

```text
recoverable_runs_pending
recovery_attempts_total
recovery_success_total
recovery_lag_seconds
```

## Persistence

```text
db_pool_in_use
db_pool_wait_seconds
db_transaction_latency_seconds
db_errors_total
```

## Messaging

```text
outbox_pending
outbox_lag_seconds
inbox_duplicates_total
```

---

# 251. Metrics cardinality rule

Pas de labels :

```text
run_id
effect_id
message_id
```

dans métriques agrégées.

---

# 252. Dashboard — Worker Capacity

Afficher :

```text
active slots
max slots
CPU
RAM
FDs
DB pool
runtime concurrency
```

---

# 253. Dashboard — Coordination

Afficher :

```text
active leases
renew p95/p99
renew failures
takeovers
stale operation rejects
```

---

# 254. Dashboard — Effects

Afficher :

```text
Effects/sec
UNKNOWN rate
reconciliation backlog
latency
provider errors
```

---

# 255. Dashboard — Recovery

Afficher :

```text
recovery backlog
oldest recoverable
success rate
manual intervention count
```

---

# 256. Dashboard — Persistence

Afficher :

```text
TPS
connections
pool waits
locks
slow queries
WAL
disk
```

---

# 257. Dashboard — Outbox

Afficher :

```text
pending
oldest age
publish rate
failure rate
```

---

# 258. Performance qualification release gate

Avant 2.0.0 :

```text
[ ] baseline recorded
[ ] saturation point identified
[ ] safe capacity envelope documented
[ ] failure-under-load passed
[ ] lease renew tails safe
[ ] recovery storm bounded
[ ] no memory/FD leak in soak
[ ] DB growth characterized
[ ] artifact path tested
```

---

# 259. Initial qualification scenarios

```text
QPERF-01 1 worker baseline
QPERF-02 2 workers concurrency
QPERF-03 10k active leases
QPERF-04 Effect burst
QPERF-05 approval-heavy durable population
QPERF-06 recovery storm after SIGKILL
QPERF-07 DB latency injection
QPERF-08 connector 429/throttle
QPERF-09 coding-agent resource pressure
QPERF-10 4h soak
```

Les nombres exacts peuvent être adaptés à l’environnement de test.

---

# 260. Scaling strategy

Ordre :

```text
1. optimize obvious bottlenecks
2. scale worker count
3. tune DB/pools/indexes
4. isolate workload classes
5. partition only if proven necessary
```

---

# 261. Scale-up vs scale-out

CPU-heavy coding workload :

```text
scale-up may help
```

I/O-heavy general workload :

```text
scale-out likely effective
```

---

# 262. Database scaling

D’abord :

```text
proper indexes
short transactions
connection discipline
vacuum
hardware
```

avant sharding.

---

# 263. Sharding

Non-goal initial.

---

# 264. Multi-region

Non-goal V2 initial.

---

# 265. Performance and correctness review

Toute optimisation sur :

```text
leases
effects
approval reads
transactions
recovery
```

nécessite review reliability.

---

# 266. Performance ADR candidates

```text
ADR-PERF-001 Lease TTL / renewal policy
ADR-PERF-002 Worker concurrency model
ADR-PERF-003 DB pool strategy
ADR-PERF-004 Recovery scanner strategy
ADR-PERF-005 Backpressure model
ADR-PERF-006 Tenant quota model
ADR-PERF-007 Workload isolation
ADR-PERF-008 Performance SLO baseline
```

---

# 267. Sizing decision record

Chaque production deployment devrait enregistrer :

```text
expected load
tested load
worker count
DB sizing
TTL/heartbeat
headroom
known bottleneck
```

---

# 268. Acceptance Criteria

Le modèle performance/capacity est conforme si :

1. les dimensions de charge sont explicites ;
2. `WAITING` n’occupe pas de slot worker actif ;
3. lease renewal load est calculable ;
4. TTL/renewal sont qualifiés par test ;
5. worker concurrency est bornée ;
6. runtime et connector concurrency sont bornées séparément ;
7. DB pools sont dimensionnés explicitement ;
8. backpressure existe avant saturation ;
9. recovery storms sont batchées ;
10. provider rate limits sont intégrés au capacity planning ;
11. storage growth est mesurable ;
12. p95/p99 sont suivis ;
13. performance tests sont reproductibles ;
14. failure-under-load est testé ;
15. aucune optimisation ne réduit les garanties de safety.

---

# 269. Definition of Done

`../operations/43_PYAGENTSKIT_PERFORMANCE_AND_CAPACITY_MODEL.md` est considéré mature lorsque :

1. les SLO initiaux sont benchmarkés ;
2. les profils de capacité sont publiés ;
3. le safe capacity envelope est connu ;
4. les renouvellements Lease sont qualifiés sous charge ;
5. PostgreSQL est qualifié avec le modèle normalisé ;
6. les Effect bursts sont testés ;
7. recovery storm est testé ;
8. le système applique backpressure ;
9. les dashboards capacity existent ;
10. les quotas tenant sont définis si multi-tenancy active ;
11. les gros Artifacts sont streamés ;
12. les soak tests ne montrent pas de fuite ;
13. les runbooks utilisent les mêmes métriques ;
14. la qualification 2.0 inclut failure-under-load ;
15. les chiffres publiés sont reliés à des rapports reproductibles.

---

# 270. Résumé

Le capacity model cible est :

```text
ARRIVAL RATE
     │
     ▼
ADMISSION CONTROL
     │
     ▼
WORKER ACTIVE SLOTS
     │
     ├────► RUNTIME LIMITS
     ├────► CONNECTOR LIMITS
     ├────► DB POOL
     └────► CPU / RAM / DISK
              │
              ▼
       DURABLE PERSISTENCE
              │
      ┌───────┼────────┐
      ▼       ▼        ▼
    LEASE   EFFECT   AUDIT/OUTBOX
      │       │        │
      └───────┼────────┘
              ▼
       BACKPRESSURE
```

Les paramètres les plus structurants sont :

```text
worker concurrency
active Run service time
Lease TTL
renew interval
DB pool size
Effect rate
recovery batch size
provider quotas
artifact volume
```

La règle essentielle est :

> **PyAgentsKit doit connaître sa capacité sûre, pas seulement sa capacité maximale : le bon dimensionnement est celui qui laisse assez de marge pour perdre un worker, reprendre des Runs, absorber un pic et continuer à renouveler l’autorité sans compromettre les Effects.**
