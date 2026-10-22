# PyAgentsKit — Test Strategy

**Document :** `../operations/38_PYAGENTSKIT_TEST_STRATEGY.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Master Test Strategy  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
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
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../operations/41_PYAGENTSKIT_DEPLOYMENT_AND_OPERATIONS.md`
- `../operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md`
- `../operations/43_PYAGENTSKIT_PERFORMANCE_AND_CAPACITY_MODEL.md`
- `../architecture/46_PYAGENTSKIT_ARCHITECTURE_DECISION_RECORDS_INDEX.md`
- `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`
- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`

---

# 1. Objet

Ce document définit la **stratégie globale de test de PyAgentsKit V2**.

Il répond à la question :

> **Comment prouver, de façon progressive et reproductible, que PyAgentsKit respecte ses invariants de sûreté, de durabilité, de gouvernance et de récupération dans les scénarios nominaux comme dans les scénarios de panne ?**

La stratégie couvre :

- tests unitaires ;
- tests de state machines ;
- property-based testing ;
- model-based testing ;
- tests contractuels ;
- tests d’intégration ;
- tests PostgreSQL réels ;
- tests multi-processus ;
- tests de concurrence ;
- fault injection ;
- chaos tests ;
- tests runtime/connectors ;
- sécurité ;
- migration ;
- package/API compatibility ;
- performance ;
- soak ;
- game days ;
- production qualification.

Le principe directeur est :

> **PyAgentsKit ne doit pas seulement tester que ses fonctions répondent correctement ; il doit tester que ses garanties restent vraies quand l’environnement devient hostile.**

---

# 2. Objectifs de la stratégie

La stratégie de test poursuit six objectifs.

```text
TST-GOAL-01 Correctness
TST-GOAL-02 Semantic Safety
TST-GOAL-03 Failure Resilience
TST-GOAL-04 Portability
TST-GOAL-05 Operability
TST-GOAL-06 Regression Resistance
```

---

# 3. TST-GOAL-01 — Correctness

Prouver que :

```text
commands
state transitions
repositories
application services
```

produisent les résultats attendus.

---

# 4. TST-GOAL-02 — Semantic Safety

Prouver notamment :

```text
UNKNOWN != FAILED
SUCCEEDED Effect is not replayed
Approval != Authorization
Lease != Liveness
Runtime completion != Run success
```

---

# 5. TST-GOAL-03 — Failure Resilience

Prouver que :

```text
crash
timeout
network cut
provider failure
worker takeover
restore
```

ne détruisent pas les invariants critiques.

---

# 6. TST-GOAL-04 — Portability

Prouver que plusieurs adapters respectent :

```text
same Port
same behavioral contract
```

---

# 7. TST-GOAL-05 — Operability

Prouver :

```text
health
readiness
drain
kill switch
migration
recovery tooling
```

---

# 8. TST-GOAL-06 — Regression Resistance

Chaque bug significatif doit devenir :

```text
a permanent regression test
```

---

# 9. Testing Philosophy

La confiance doit être construite par couches :

```text
Fast Tests
   ↓
Behavioral Contracts
   ↓
Real Infrastructure
   ↓
Concurrency
   ↓
Failure Injection
   ↓
Distributed Qualification
   ↓
Production-Like Validation
```

---

# 10. Test Pyramid

```text
                    ┌──────────────────────┐
                    │ Production-like /    │
                    │ Game Days / Chaos    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Distributed /        │
                    │ Failure Integration  │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Contract /           │
                    │ Integration Tests    │
                    └──────────┬───────────┘
                               │
                    ┌──────────▼───────────┐
                    │ Unit / Property /    │
                    │ State Machine Tests  │
                    └──────────────────────┘
```

La pyramide doit rester :

```text
many fast tests
few expensive high-fidelity tests
```

sans supprimer les couches coûteuses.

---

# 11. Test Levels

```text
TL0 — Static Verification
TL1 — Unit
TL2 — State/Property
TL3 — Contract
TL4 — Integration
TL5 — Concurrency
TL6 — Failure Injection
TL7 — Distributed
TL8 — Performance / Soak
TL9 — Production Qualification
```

---

# 12. TL0 — Static Verification

Inclut :

```text
Ruff
mypy strict
import architecture checks
dependency rules
public API checks
```

---

# 13. Static Architecture Tests

Doivent vérifier :

```text
Domain imports no Adapters
Application imports no concrete adapter
API does not bypass Application
Adapters do not create forbidden coupling
V2 Domain does not import compat.v1
```

---

# 14. TL1 — Unit Tests

Cible :

```text
pure domain
value objects
application decisions
utility logic
```

Caractéristiques :

```text
fast
deterministic
isolated
```

---

# 15. Unit Test Rule

Un test unitaire ne doit pas :

```text
start PostgreSQL
call network
depend on wall clock
```

sauf volontairement via fake Clock.

---

# 16. Domain Unit Tests

Priorités :

```text
Run
Effect
Approval
Lease
RecoveryPlan
OwnershipContext
SecurityContext
```

---

# 17. Value Object Tests

Exemples :

```text
IDs
Fingerprint
FencingToken
ExternalReference
RuntimeCapability set
SecretReference
```

---

# 18. Boundary Tests

Tester systématiquement :

```text
empty
minimum
maximum
invalid
duplicate
expired
stale
```

---

# 19. TL2 — State Machine Tests

Les aggregates à cycle de vie doivent avoir des tests dédiés.

---

# 20. Run State Machine

Couvrir :

```text
CREATED
RUNNING
WAITING
PAUSED
SUCCEEDED
FAILED
CANCELLED
```

---

# 21. Run Invalid Transitions

Exemple :

```text
SUCCEEDED → RUNNING
```

doit être rejeté.

---

# 22. Effect State Machine

Couvrir :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

# 23. Effect Invalid Transitions

Exemples :

```text
SUCCEEDED → STARTED
FAILED → SUCCEEDED
```

sans procédure explicite de reconciliation/résolution.

---

# 24. Approval State Machine

Couvrir :

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

---

# 25. Approval Terminality

Un état terminal ne doit pas être réécrit par une autre décision terminale.

---

# 26. Lease Lifecycle

Tester :

```text
acquire
renew
expire
release
takeover
```

---

# 27. Property-Based Testing

À utiliser lorsque l’espace d’entrées est large.

Candidats :

```text
fingerprints
serialization
state transitions
idempotency keys
tenant-scoped IDs
```

---

# 28. Property Example — Fingerprint

Pour une représentation canonique identique :

```text
fingerprint(x) == fingerprint(x)
```

---

# 29. Property Example — Semantic Stability

Serialization + deserialization :

```text
decode(encode(x))
≈
x
```

sémantiquement.

---

# 30. Property Example — Idempotency

Même logical operation produit :

```text
same idempotency identity
```

selon règles définies.

---

# 31. Model-Based Testing

Particulièrement utile pour :

```text
Effect
Approval
Lease
Run
```

---

# 32. Model-Based Principle

Définir :

```text
reference model
commands
preconditions
postconditions
```

puis générer des séquences d’actions.

---

# 33. Why Model-Based Testing

Permet de découvrir :

```text
unexpected transition sequences
race-related semantic gaps
```

---

# 34. TL3 — Contract Tests

Définis en détail dans le document 39.

Ils valident :

```text
same Port
same observable semantics
```

---

# 35. P0 Contract Suites

```text
RunRepository
EffectRepository
ApprovalRepository
LeaseRepository
UnitOfWork
AgentRuntimeAdapter
Connector
ReconciliationPort
```

---

# 36. TL4 — Integration Tests

Testent une implémentation avec ses dépendances réelles.

---

# 37. PostgreSQL Integration Tests

Obligatoires pour :

```text
repositories
constraints
transactions
locking
fencing
outbox/inbox
```

---

# 38. SQLite Integration Tests

Utiles pour :

```text
local durability
migration
compatibility
```

---

# 39. Object Storage Integration Tests

Pour :

```text
filesystem
S3-compatible
Azure Blob
```

selon adapters officiels.

---

# 40. Runtime Integration Tests

Doivent utiliser le vrai SDK/runtime pour les adapters officiels.

---

# 41. Connector Integration Tests

Doivent utiliser :

```text
sandbox
test repository
non-production account
```

---

# 42. Integration Test Isolation

Chaque test doit créer son propre :

```text
tenant
resource prefix
DB namespace
external resource
```

---

# 43. TL5 — Concurrency Tests

Objectif :

```text
prove race semantics
```

---

# 44. Concurrency Candidates

```text
lease acquire
lease takeover
Effect reservation
Approval decision
optimistic concurrency
Outbox claim
Inbox dedup
```

---

# 45. Real Concurrency Rule

Utiliser :

```text
independent DB connections
threads/processes
async tasks where relevant
```

et pas seulement :

```text
call A then B
```

---

# 46. Lease Race Test

Deux workers tentent :

```text
acquire(resource)
```

Attendu :

```text
one authority
```

---

# 47. Approval Race Test

Deux approvers tentent :

```text
approve
reject
```

simultanément.

Attendu :

```text
one terminal decision
```

---

# 48. Effect Reservation Race

Deux workers tentent même :

```text
idempotency key
```

Attendu :

```text
one logical Effect
```

---

# 49. TL6 — Failure Injection

Objectif :

```text
prove semantics under interruption
```

---

# 50. Failure Injection Points

```text
before DB write
after DB write
before external send
after send
before response
after response
before durable outcome
after durable outcome
```

---

# 51. W1–W5 Coverage

Toute la chaîne Effect doit être testée sur :

```text
W1
W2
W3
W4
W5
```

---

# 52. W1

Crash avant durable intent.

Attendu :

```text
no external consequence
```

---

# 53. W2

Crash après intent, avant send.

Attendu :

```text
recovery knows intent exists
```

---

# 54. W3

Crash après send, avant response.

Attendu :

```text
UNKNOWN
```

---

# 55. W4

Crash après response, avant durable outcome.

Attendu :

```text
reconciliation
```

---

# 56. W5

Crash après durable success, avant Run progress.

Attendu :

```text
no Effect replay
```

---

# 57. Fault Types

Le harness doit pouvoir injecter :

```text
SIGTERM
SIGKILL
SIGSTOP
DB disconnect
network drop
timeout
500
429
connection reset
slow response
```

---

# 58. Failure Hook Design

Les hooks internes de fault injection :

```text
test-only
not public production API
```

---

# 59. TL7 — Distributed Tests

Minimum :

```text
2 real worker processes
real PostgreSQL
```

---

# 60. Distributed Scenarios

```text
worker takeover
stale worker fencing
split-brain attempt
concurrent recovery
lease expiry
runtime continuation on another worker
```

---

# 61. SIGSTOP Scenario

```text
Worker A acquires lease
A is SIGSTOP
TTL expires
Worker B takes over
A resumes
A attempts Effect
```

Attendu :

```text
A rejected by fencing
```

---

# 62. Multi-Process Requirement

Les distributed guarantees ne doivent pas être testées uniquement :

```text
in one Python event loop
```

---

# 63. TL8 — Performance & Soak

Voir document 43.

Doit inclure :

```text
baseline
load
saturation
recovery storm
4h+ soak
```

---

# 64. Performance Test Principle

La performance ne peut jamais invalider :

```text
safety
correctness
```

---

# 65. TL9 — Production Qualification

Voir document 40.

Inclut :

```text
game days
restore
migration rehearsal
release evidence
```

---

# 66. Security Test Strategy

La sécurité doit être testée transversalement.

---

# 67. Authentication Tests

Tester :

```text
missing identity
invalid identity
expired identity
```

selon adapters.

---

# 68. Authorization Tests

Tester :

```text
ALLOW
DENY
revocation
tenant mismatch
provider unavailable
```

---

# 69. Approval Separation Tests

Prouver :

```text
authorized
!=
approved
```

---

# 70. Approval Text Test

```text
conversation message "ok"
```

ne doit jamais produire un Approval.

---

# 71. Tenant Isolation Tests

Couvrir :

```text
read
write
query
artifact
conversation
Effect
Approval
```

---

# 72. Secret Handling Tests

Vérifier absence de secrets dans :

```text
logs
AuditEvents
Run state
Checkpoints
Messages
serialized exceptions
```

---

# 73. Supply-Chain Tests

CI doit au minimum inclure :

```text
dependency vulnerability scanning
package integrity checks
```

---

# 74. Admin Security Tests

Les opérations dangereuses doivent tester :

```text
authorization
audit
reason
```

---

# 75. Recovery Test Strategy

RecoveryPlanner est une cible majeure.

---

# 76. NextAction Coverage

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

---

# 77. Recovery Test Principle

Tester :

```text
input durable state
→
expected NextAction
```

séparément de l’exécution.

---

# 78. Recovery Integration Tests

Ensuite tester :

```text
NextAction
→
actual adapter behavior
```

---

# 79. Manual Intervention Tests

Prouver que le système sait :

```text
stop safely
```

lorsqu’il manque des preuves.

---

# 80. Runtime Adapter Test Strategy

Chaque adapter suit :

```text
structural
behavioral
integration
failure
qualification
```

---

# 81. Runtime Capabilities

Chaque capability déclarée doit avoir au moins un test.

```text
START
RESUME
CANCEL
STATUS
EVENT_STREAM
NATIVE_CHECKPOINT
TOOL_INTERCEPTION
MESSAGE_STREAM
HUMAN_APPROVAL_HOOK
SUBAGENTS
SESSION_RESUME
STRUCTURED_OUTPUT
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
```

---

# 82. Capability Negative Tests

Une capability absente doit :

```text
fail explicitly
```

et non se comporter partiellement.

---

# 83. Runtime Non-Determinism Rule

Ne pas tester :

```text
exact generated natural language
```

pour les contracts.

Tester :

```text
control behavior
```

---

# 84. Runtime Integration Assertions

Exemples :

```text
handle returned
inspect normalized
resume meaningful
cancel acknowledged
events normalized
```

---

# 85. Connector Test Strategy

Chaque Connector doit avoir :

```text
read tests
write tests
timeout tests
auth tests
rate-limit tests
reconciliation tests
```

---

# 86. External Write Safety Tests

Toute opération write critique doit couvrir :

```text
success
known failure
ambiguous failure
reconciliation
```

---

# 87. Generic HTTP Test Matrix

```text
200
201
204
400
401
403
404
409
429
500
timeout before send
timeout after send
```

---

# 88. GitHub Test Matrix

Exemples :

```text
PR create
PR lookup
PR already exists
merge
rate limit
auth failure
remote ref reconciliation
```

---

# 89. Coding Agent Test Strategy

Scénario de référence :

```text
create workspace
edit files
run tests
commit
request push
Approval
push
crash
recover
verify no duplicate
```

---

# 90. Coding Agent Protected Effects

Tester séparément :

```text
git push
PR creation
PR merge
package publish
deploy
terraform apply
```

---

# 91. Approval-SHA Binding Test

```text
approved SHA A
actual SHA B
```

doit être rejeté.

---

# 92. Migration Test Strategy

V1 → V2 doit avoir :

```text
unit mapping tests
fixture migration tests
integration migration tests
interrupted migration tests
cutover tests
post-cutover recovery tests
```

---

# 93. Migration Fixtures

Inclure :

```text
all V1 RunStatus values
all Effect states
all Approval legacy states
lease/fencing states
edge/corrupt states
```

---

# 94. Migration Invariant Tests

Prouver :

```text
successful Effect not lost
UNKNOWN not collapsed
Approval not forged
fencing not regressed
```

---

# 95. Migration Restart Test

Interrompre une migration en cours.

Relancer.

Attendu :

```text
idempotent continuation
```

---

# 96. Cutover Test

Pendant switch :

```text
one authoritative writer
```

---

# 97. Restore / PITR Test Strategy

Critique.

---

# 98. Restore Scenario

```text
Effect succeeded externally
DB backup predates success
restore DB
```

Attendu :

```text
workers remain disabled
reconciliation required
```

---

# 99. Fencing Restore Test

Si restore fait revenir un vieux token :

```text
safe resume blocked
```

---

# 100. Outbox Restore Test

Les événements restaurés ne doivent pas recréer une conséquence déjà consommée.

---

# 101. Package Test Strategy

Tester :

```text
wheel
sdist
fresh install
minimal dependencies
extras
version metadata
checksums
```

---

# 102. Minimal Install Test

Le package core doit fonctionner sans installer :

```text
all runtime SDKs
all connectors
all cloud clients
```

---

# 103. Public API Test Strategy

Maintenir une liste publique attendue.

Tester :

```text
exports
models
enums
errors
serialization
```

---

# 104. SemVer Regression Tests

Un changement breaking doit être détecté avant publication.

---

# 105. Compatibility Test Strategy

Pendant période V1 compatibility :

```text
V1 tests
+
V2 tests
```

mais leurs sémantiques doivent rester séparées.

---

# 106. Observability Test Strategy

Tester que :

```text
critical metrics emitted
trace boundaries correct
audit generated
secrets redacted
```

---

# 107. Audit Test Strategy

Audit n’est pas une simple assertion de log.

Tester :

```text
actor
action
target
reason
evidence
timestamp
```

---

# 108. Outbox/Inbox Test Strategy

Outbox :

```text
atomicity
retry
crash after publish
poison event
```

Inbox :

```text
duplicate
payload conflict
processing failure
```

---

# 109. Artifact Test Strategy

Tester :

```text
checksum
streaming
orphan blob
orphan metadata
large artifact
tampering
```

---

# 110. Conversation Test Strategy

Tester distinctions :

```text
Session != Conversation
Message != RuntimeEvent
Message != Approval
```

---

# 111. Test Data Strategy

Les données doivent être :

```text
small
deterministic
isolated
representative
```

---

# 112. Factory Pattern

Préférer :

```text
domain factories
test builders
```

plutôt que gros fixtures statiques fragiles.

---

# 113. Fixture Naming

Exemples :

```text
make_run()
make_effect()
make_approval()
make_lease()
```

---

# 114. Canonical Edge Fixtures

Maintenir :

```text
unknown_effect
expired_approval
stale_lease
tenant_mismatch
idempotency_conflict
restored_state
```

---

# 115. Test Isolation

Aucun test ne doit dépendre de l’ordre des autres.

---

# 116. Clock Control

Utiliser :

```text
ClockPort
```

pour tests temporels.

---

# 117. Randomness Control

Seed explicite pour property tests et stress tests quand possible.

---

# 118. External Provider Tests

Utiliser ressources dédiées et nettoyables.

---

# 119. Cost Control

Marquer les tests :

```text
external
costly
```

---

# 120. Destructive Tests

Marquer :

```text
destructive
```

et exécuter uniquement dans environnement autorisé.

---

# 121. Test Markers

Proposition :

```text
unit
property
contract
integration
postgres
concurrency
failure
distributed
external
destructive
performance
soak
migration
security
```

---

# 122. Test Directory Layout

```text
tests/
├── unit/
├── property/
├── contracts/
├── integration/
├── concurrency/
├── failure/
├── distributed/
├── migration/
├── security/
├── performance/
└── qualification/
```

---

# 123. Fast Test Suite

Doit pouvoir être exécutée très fréquemment.

Inclut :

```text
unit
property subset
fast contracts
static checks
```

---

# 124. Full CI Suite

Inclut :

```text
fast
PostgreSQL
concurrency
migration
security
package
```

---

# 125. Nightly Suite

Inclut :

```text
external runtimes
external connectors
failure injection
longer stress
```

---

# 126. Release Suite

Inclut :

```text
distributed qualification
restore
performance
soak
game-day evidence
```

---

# 127. CI Stages

Recommandation :

```text
lint
typecheck
architecture
unit
property
contract
integration
concurrency
security
package
```

Puis workflows séparés :

```text
external
performance
qualification
```

---

# 128. Fail-Fast Policy

CI rapide peut s’arrêter tôt sur :

```text
static
unit
contract
```

---

# 129. Safety Test Policy

Les tests P0 sont toujours blocking.

---

# 130. Flaky Test Policy

Un test safety-critical flaky est :

```text
a defect
```

---

# 131. Quarantine

Possible temporairement pour tests non critiques, avec :

```text
owner
issue
deadline
```

---

# 132. Retry in CI

Ne pas masquer un test instable par :

```text
retry until green
```

---

# 133. Repetition for Race Tests

Au contraire, les tests de concurrence doivent volontairement s’exécuter :

```text
many iterations
```

---

# 134. Coverage Strategy

Coverage cible :

```text
high branch coverage
```

mais ne remplace pas :

```text
invariant coverage
failure coverage
```

---

# 135. Critical Coverage Areas

Priorité maximale :

```text
Effect
Recovery
Lease/Fencing
Approval
Authorization
Migration
```

---

# 136. Coverage Exclusions

Limiter aux cas légitimes :

```text
defensive impossible branches
typing-only
platform-specific
```

---

# 137. Mutation Testing

Optionnel mais recommandé pour :

```text
critical domain invariants
```

---

# 138. Why Mutation Testing

Peut révéler des tests qui exécutent le code sans réellement vérifier les garanties.

---

# 139. Assertion Quality

Préférer assertions sémantiques :

```text
effect.status == UNKNOWN
```

plutôt que :

```text
function called once
```

si le comportement métier est la vraie cible.

---

# 140. Mocking Strategy

Mocks utiles pour :

```text
isolation
failure injection
```

mais ne doivent pas remplacer les vrais adapters.

---

# 141. Fake vs Mock

Préférer souvent :

```text
behavioral fake
```

pour Repository/Ports.

---

# 142. In-Memory Fake Rule

Un fake doit respecter :

```text
same Contract Suite
```

---

# 143. Testing Error Taxonomy

Chaque erreur canonique doit avoir au moins :

```text
construction
mapping
serialization/public behavior
```

testé.

---

# 144. Negative Tests

Tester explicitement :

```text
what must never happen
```

---

# 145. P0 Negative Tests

```text
blind UNKNOWN retry
stale fencing accepted
approval bypass
cross-tenant write
runtime self-authorizes
connector bypass
restore auto-resume
```

---

# 146. Reliability Test IDs

Convention :

```text
TST-RUN-xxx
TST-EFF-xxx
TST-APR-xxx
TST-LEASE-xxx
TST-REC-xxx
TST-RT-xxx
TST-CONN-xxx
TST-MIG-xxx
TST-SEC-xxx
```

---

# 147. Test Traceability

Chaque test critique doit référencer :

```text
requirement
invariant
ADR
release gate
```

---

# 148. Traceability Matrix

Exemple :

| Test | Invariant | Document | Gate |
|---|---|---|---|
| TST-EFF-W3 | UNKNOWN != FAILED | 13/25 | GATE-04 |
| TST-LEASE-STALE | stale worker fenced | 15 | GATE-06 |
| TST-APR-SCOPE | exact scope | 17 | GATE-08 |
| TST-MIG-EFFECT | success preserved | 30 | GATE-11 |

---

# 149. Bug-to-Test Rule

Tout bug P0/P1 doit produire :

```text
regression test
```

avant fermeture lorsque techniquement possible.

---

# 150. Incident-to-Test Rule

Tout incident de production ou Game Day important doit alimenter :

```text
failure test
contract test
qualification scenario
```

selon sa nature.

---

# 151. ADR-to-Test Rule

Une décision architecturale safety-critical doit avoir au moins une preuve testable.

---

# 152. Test Ownership

Chaque bounded context possède ses tests.

```text
Execution → Runs/Recovery
Effects → Effects/Reconciliation
Governance → Approval/AuthZ
Coordination → Lease/Fencing
Runtime Integration → Runtime Adapter
Connectors → Connector
```

---

# 153. Cross-Context Tests

Réservés aux vrais use cases d’orchestration.

---

# 154. Application Service Tests

Tester :

```text
port calls
order
transaction boundaries
result
```

sans dupliquer tous les tests Domain.

---

# 155. CreateRun Test

Couvrir :

```text
valid command
tenant context
initial state
audit/outbox if applicable
```

---

# 156. ResumeRun Test

Ne doit pas simplement tester :

```text
runtime.resume()
```

mais :

```text
RecoveryPlanner decision
```

---

# 157. ExecuteEffect Test

Doit couvrir :

```text
authorization
approval
ownership
reservation
external call
outcome persistence
```

---

# 158. ReconcileEffect Test

Doit couvrir :

```text
UNKNOWN
provider evidence
resolution
Run unblocking
```

---

# 159. UnitOfWork Tests

Tester :

```text
commit
rollback
exception
outbox atomicity
```

---

# 160. Transaction Boundary Test

Vérifier qu’aucun remote call n’a lieu dans une transaction longue.

Peut être testé par instrumentation/fake UoW.

---

# 161. DB Constraint Tests

Même si Domain valide déjà :

```text
critical safety constraints
```

doivent être testées physiquement sur PostgreSQL.

---

# 162. Schema Migration Tests

Chaque migration DB doit tester :

```text
upgrade
possibly downgrade if supported
data preservation
```

---

# 163. Query Plan Tests

Pas en unit CI.

Mais pour queries critiques :

```text
EXPLAIN ANALYZE
```

dans performance qualification.

---

# 164. Load Test Scenarios

Minimum :

```text
Run burst
Effect burst
Lease renew pressure
Approval backlog
Recovery storm
Coding workload
```

---

# 165. Soak Tests

Objectifs :

```text
memory leak
FD leak
task leak
connection leak
lease drift
```

---

# 166. Chaos Testing

Scénarios :

```text
worker kill
worker pause
DB outage
object store outage
runtime outage
connector ambiguity
restore
```

---

# 167. Game Days

Utilisent :

```text
real runbooks
real alerts
operator actions
```

---

# 168. Game Day Success

Pas seulement :

```text
system recovered
```

mais :

```text
operators detected
understood
contained
recovered safely
```

---

# 169. Observability Assertions

Dans les tests de qualification :

```text
expected metric exists
expected alert triggers
expected audit event exists
```

---

# 170. Health Endpoint Tests

Tester :

```text
liveness
readiness
protected-effects readiness
```

sous dependency failures.

---

# 171. Kill Switch Tests

Tester :

```text
global
tenant
connector
Effect class
```

---

# 172. Worker Drain Tests

Prouver :

```text
no new admission
bounded in-flight completion
safe termination
```

---

# 173. Rolling Upgrade Tests

Versions N/N+1 doivent coexister si support annoncé.

---

# 174. Version Skew Tests

Prouver :

```text
compatible schema
compatible events
compatible DB writes
```

---

# 175. Deployment Smoke Tests

Après déploiement :

```text
CreateRun
Run query
Lease acquire
safe Effect
Audit
Artifact
```

---

# 176. Test Environments

```text
TE-LOCAL
TE-CI
TE-POSTGRES
TE-DISTRIBUTED
TE-PROVIDER-SANDBOX
TE-PROD-LIKE
```

---

# 177. Environment Reproducibility

Chaque test coûteux doit enregistrer :

```text
commit SHA
Python
DB version
runtime versions
OS
config
```

---

# 178. Test Artifact Retention

Conserver pour release :

```text
JUnit/XML
coverage
logs
failure reports
performance reports
migration reports
```

---

# 179. Evidence Pack Integration

Le document 40 consomme :

```text
test evidence
```

comme preuve de Release Gate.

---

# 180. Test Result Taxonomy

```text
PASS
FAIL
SKIP
XFAIL
BLOCKED
NOT_APPLICABLE
```

---

# 181. Skip Policy

Un skip doit avoir :

```text
reason
```

et ne doit pas masquer une garantie obligatoire.

---

# 182. XFAIL Policy

Seulement pour bug connu non bloquant avec issue associée.

---

# 183. Blocked Test

Utiliser quand :

```text
environment/dependency unavailable
```

plutôt que prétendre PASS.

---

# 184. Test Determinism

Les tests rapides doivent être très déterministes.

Les tests externes peuvent tolérer davantage de variabilité, mais leurs assertions doivent rester robustes.

---

# 185. Timeouts in Tests

Tous les tests async/network doivent avoir un timeout borné.

---

# 186. Test Deadlock Detection

Les suites concurrency doivent avoir watchdog/timeout.

---

# 187. Cleanup Strategy

Toujours prévoir :

```text
try/finally
fixture teardown
external cleanup
```

---

# 188. Cleanup Failure Reporting

Une ressource externe non supprimée doit être référencée dans le rapport.

---

# 189. Production Credentials Rule

Interdit pour tests automatisés destructifs.

---

# 190. Cost Budget

Les suites providers doivent avoir un budget contrôlé.

---

# 191. API Fuzzing

Peut être ajouté pour :

```text
public HTTP API
serialization
invalid payloads
```

si API HTTP introduite.

---

# 192. Security Fuzzing

Peut viser :

```text
tenant IDs
resource references
scope inputs
```

---

# 193. Concurrency Stress

Exécuter certaines races :

```text
100s / 1000s iterations
```

en nightly/qualification.

---

# 194. Race Reproduction

Lorsqu’une race est découverte :

```text
capture seed / scheduling conditions
```

si possible.

---

# 195. Database Fault Injection

Scénarios :

```text
connection killed
transaction aborted
failover
latency
pool starvation
```

---

# 196. External Fault Injection

Scénarios :

```text
DNS fail
connect timeout
read timeout
connection reset
HTTP 500
HTTP 429
partial response
```

---

# 197. Fault Injection Safety

Toujours dans environnement isolé.

---

# 198. Test Harness Reuse

Prévoir package :

```text
pyagentskit.testing
```

avec :

```text
fakes
builders
contracts
faults
assertions
```

---

# 199. Testing Public Surface

Le package de test public doit rester minimal et stable pour auteurs d’adapters.

---

# 200. Test Builders

Exemples :

```text
RunBuilder
EffectBuilder
ApprovalBuilder
LeaseBuilder
```

---

# 201. Domain Assertions

Helpers possibles :

```text
assert_run_waiting()
assert_effect_unknown()
assert_fenced()
```

---

# 202. Fault Helpers

Exemples :

```text
crash_at("after_send")
pause_worker()
drop_db_connection()
```

uniquement test harness.

---

# 203. Testing Anti-Pattern — Overmocking

Danger :

```text
everything green
real system broken
```

---

# 204. Anti-Pattern — Test Through Implementation

Éviter assertions couplées à structures privées.

---

# 205. Anti-Pattern — Coverage Chasing

100 % coverage sans W3/W4 tests donne peu de confiance.

---

# 206. Anti-Pattern — Sequential Concurrency

Déjà interdit.

---

# 207. Anti-Pattern — Retry Flaky Test Until Pass

Interdit.

---

# 208. Anti-Pattern — Use Sleep for Correctness

Préférer :

```text
events
conditions
clock control
```

---

# 209. Anti-Pattern — Assume 2xx Means Safe

Un 2xx perdu avant persistence peut encore produire W4.

---

# 210. Anti-Pattern — Assume Timeout Means Failure

Interdit.

---

# 211. Anti-Pattern — Only Test Happy Path

Incompatible avec la mission du produit.

---

# 212. Anti-Pattern — Only Test Memory Backend

Ne qualifie pas la production.

---

# 213. Anti-Pattern — Only Test One Worker

Ne qualifie pas distributed execution.

---

# 214. Anti-Pattern — Only Test Runtime Mock

Ne qualifie pas adapter réel.

---

# 215. Anti-Pattern — Only Test Migrations Forward Once

Il faut interruption/restart/cutover.

---

# 216. Test Review Checklist

```text
[ ] invariant targeted?
[ ] deterministic?
[ ] correct test level?
[ ] real dependency needed?
[ ] failure mode represented?
[ ] cleanup?
[ ] timeout?
[ ] tenant isolation?
[ ] secrets safe?
[ ] traceability?
```

---

# 217. PR Quality Gate

Minimum :

```text
Ruff
mypy
architecture checks
unit
fast property
fast contracts
```

---

# 218. Main Branch Gate

Ajoute :

```text
PostgreSQL integration
migration
concurrency
package
security
```

---

# 219. Nightly Gate

Ajoute :

```text
external runtimes
connectors
failure injection
stress
```

---

# 220. Release Candidate Gate

Ajoute :

```text
distributed
restore/PITR
performance
soak
game days
evidence pack
```

---

# 221. Test Runtime Budget

Fast PR suite :

```text
minutes, not tens of minutes
```

Les suites longues sont séparées.

---

# 222. Parallelization

Possible pour :

```text
unit
property
contracts
```

avec isolation correcte.

---

# 223. Serial Tests

Certaines suites peuvent rester séquentielles :

```text
migration global
restore
specific provider quotas
```

---

# 224. Test Ownership Review

À chaque release majeure :

```text
remove obsolete tests
promote regressions
review skipped tests
review xfails
```

---

# 225. Documentation Tests

Les exemples publics critiques devraient être exécutables si possible.

---

# 226. README Smoke Test

Les snippets d’installation/usage de base doivent être validés.

---

# 227. Migration Guide Test

Les commandes du guide doivent être exercées dans rehearsal.

---

# 228. Runbook Test

Les procédures du document 42 doivent être testées en Game Day.

---

# 229. Performance Baseline Test

Chaque release importante compare avec baseline précédente.

---

# 230. Regression Thresholds

Une régression significative :

```text
latency
throughput
memory
lease p99
```

doit déclencher review.

---

# 231. Capacity Safety Test

Ne pas seulement mesurer max throughput.

Mesurer :

```text
safe capacity with headroom
```

---

# 232. Test Metrics

Suivre :

```text
test count
duration
flaky count
contract compliance
qualification pass rate
coverage
```

---

# 233. Quality Metrics

Plus importants :

```text
P0 regressions
production incidents
UNKNOWN mishandling
stale fencing rejects
```

---

# 234. Testing Maturity Levels

```text
TST-L0 basic unit tests
TST-L1 domain + integration
TST-L2 contracts + concurrency
TST-L3 failure/distributed
TST-L4 production qualification
```

---

# 235. Target Before V2 Stable

```text
TST-L4
```

pour les surfaces P0.

---

# 236. Release-Specific Testing

## 2.0.0a1

Focus :

```text
Domain
state machines
architecture
```

## 2.0.0a2

Focus :

```text
Runtime contracts
Native adapter
```

## 2.0.0a3

Focus :

```text
Effects
W1–W5
RecoveryPlanner
```

## 2.0.0a4

Focus :

```text
PostgreSQL
UoW
multi-process
```

## 2.0.0b1

Focus :

```text
Governance
Security
Audit
```

## 2.0.0b2

Focus :

```text
External runtime
Coding runtime
Connector
```

## 2.0.0rc1

Focus :

```text
Migration
Public API
Ops
Performance
Restore
```

---

# 237. P0 Test Domains

Avant stable, aucune lacune majeure sur :

```text
Effect safety
Recovery
Lease/Fencing
Approval/AuthZ
Tenant isolation
Migration
Restore
```

---

# 238. No-Waiver Tests

Tests critiques non waivables :

```text
W3/W4
stale fencing rejection
cross-tenant denial
Approval scope drift
restore safety gate
successful Effect migration
```

---

# 239. Test Exit Criteria

Une release candidate peut avancer si :

```text
all blocking suites green
no P0 open
no critical flaky tests
qualification evidence complete
```

---

# 240. Acceptance Criteria

La stratégie de test est conforme si :

1. chaque invariant P0 possède une preuve testable ;
2. Domain est testé sans infrastructure ;
3. state machines ont des tests exhaustifs ;
4. property/model-based tests ciblent les bons objets ;
5. Contract Tests couvrent les Ports critiques ;
6. PostgreSQL réel est utilisé ;
7. concurrency est réellement concurrente ;
8. W1–W5 sont injectables ;
9. multi-worker est testé multi-processus ;
10. security/tenant isolation sont testées ;
11. external adapters ont des tests réels ;
12. migration est interruption-safe ;
13. restore/PITR est testé ;
14. performance inclut soak et failure-under-load ;
15. Game Days exécutent les runbooks ;
16. CI sépare suites rapides et lourdes ;
17. les bugs deviennent des regressions ;
18. les tests critiques sont traçables vers invariants/gates ;
19. les secrets/prod credentials sont exclus ;
20. la qualification production consomme les preuves.

---

# 241. Definition of Done

`../operations/38_PYAGENTSKIT_TEST_STRATEGY.md` est considéré mature lorsque :

1. la structure `tests/` cible est en place ;
2. static architecture checks sont actifs ;
3. Domain tests couvrent les cycles de vie ;
4. property-based testing est utilisé sur les invariants adaptés ;
5. Contract Suites P0 sont exécutables ;
6. PostgreSQL integration est automatisée ;
7. race tests utilisent plusieurs connexions/processus ;
8. fault injection W1–W5 existe ;
9. SIGTERM/SIGKILL/SIGSTOP sont testés ;
10. external runtime adapter tests sont intégrés ;
11. connector/reconciliation tests existent ;
12. security tests incluent cross-tenant et secrets ;
13. migration rehearsal est automatisable ;
14. Restore/PITR est couvert ;
15. performance/soak possède un harness ;
16. les Game Days ont des scénarios définis ;
17. le package/API possède des regression tests ;
18. les test artifacts sont archivables ;
19. les no-waiver tests bloquent la release ;
20. le document 40 peut utiliser cette stratégie comme base de qualification.

---

# 242. Résumé

La stratégie globale est :

```text
STATIC
  │
  ▼
UNIT
  │
  ▼
STATE / PROPERTY
  │
  ▼
CONTRACT
  │
  ▼
INTEGRATION
  │
  ▼
CONCURRENCY
  │
  ▼
FAILURE INJECTION
  │
  ▼
DISTRIBUTED
  │
  ▼
PERFORMANCE / SOAK
  │
  ▼
GAME DAYS / QUALIFICATION
```

Les tests les plus importants ne sont donc pas nécessairement ceux qui vérifient le plus de lignes de code, mais ceux qui prouvent les invariants qui empêchent PyAgentsKit de produire une mauvaise conséquence dans le monde réel.

La règle fondamentale est :

> **PyAgentsKit doit être testé comme une bibliothèque Python, mais qualifié comme un système distribué qui peut commander des actions irréversibles.**
