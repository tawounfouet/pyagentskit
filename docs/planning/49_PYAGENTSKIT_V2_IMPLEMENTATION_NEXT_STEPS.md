# PyAgentsKit — V2 Implementation Next Steps

**Document :** `49_PYAGENTSKIT_V2_IMPLEMENTATION_NEXT_STEPS.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Implementation Transition Plan  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../specs/strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../specs/architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../specs/strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`
- `../specs/runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../specs/runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../specs/domain/33_PYAGENTSKIT_DOMAIN_EVENTS_AND_OUTBOX_INBOX.md`
- `../specs/runtime/34_PYAGENTSKIT_RUNTIME_REGISTRY_AND_CAPABILITY_NEGOTIATION.md`
- `../specs/runtime/35_PYAGENTSKIT_NATIVE_RUNTIME_ADAPTER.md`
- `../specs/runtime/36_PYAGENTSKIT_RECOVERY_PLANNER_SPECIFICATION.md`
- `../specs/runtime/37_PYAGENTSKIT_RECONCILIATION_MODEL.md`
- `../specs/operations/38_PYAGENTSKIT_TEST_STRATEGY.md`
- `../specs/operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../specs/operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../specs/operations/41_PYAGENTSKIT_DEPLOYMENT_AND_OPERATIONS.md`
- `../specs/operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md`
- `../specs/operations/43_PYAGENTSKIT_PERFORMANCE_AND_CAPACITY_MODEL.md`
- `../specs/strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`
- `../specs/architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`
- `../specs/strategy/PYAGENTSKIT_EXISTING_VS_TARGET_GAP_ANALYSIS_2026-10-21.md`

---

# 1. Objet

Ce document définit les **next steps d’implémentation de PyAgentsKit V2** après finalisation du corpus d’architecture.

La phase documentaire est désormais suffisamment mature pour passer au code.

L’objectif n’est plus :

```text
invent architecture
```

mais :

```text
translate architecture into executable software
```

Le principe directeur est :

> **Stop expanding the design. Start proving it in code.**

---

# 2. Point de départ

PyAgentsKit V1.6 dispose déjà d’un socle important :

```text
Runner
DurableRunner
DistributedDurableRunner
Model providers
Tool system
Approvals
Sessions
Memory
Artifacts
Blobs
Leases
Fencing
PostgreSQL stores
Observability
Telemetry
Qualification infrastructure
```

La V2 ne doit donc pas être traitée comme un greenfield.

La stratégie est :

```text
preserve
reclassify
extract
adapt
replace only where semantics require it
```

---

# 3. Conclusion architecturale

Le changement principal est :

```text
V1
PyAgentsKit = Agent Runtime

V2
PyAgentsKit = Agent Reliability Layer
```

Ce changement implique :

```text
Runner
→ Native Runtime

Durability
→ Reliability Core

Effect semantics
→ first-class bounded context

Recovery
→ explicit Planner

Runtime integration
→ Adapter contract

Persistence
→ Ports + normalized stores

Governance
→ Approval + Authorization separation
```

---

# 4. Règle de transition

> **Ne pas réécrire V1.6 ; l’encercler progressivement avec le modèle V2 et déplacer les responsabilités au bon endroit.**

Le pattern cible est :

```text
Strangler Migration
```

---

# 5. Release Path

La roadmap d’implémentation reste :

```text
1.6.x      V1 maintenance / freeze
2.0.0a1    Domain Foundations
2.0.0a2    Runtime Abstraction
2.0.0a3    Effects & Recovery Core
2.0.0a4    Persistence V2
2.0.0b1    Governance, Security & Audit
2.0.0b2    External Runtimes & Connectors
2.0.0rc1   Public Contracts & Migration
2.0.0      Production Qualified
```

---

# 6. Critical Path

```text
V1.6 FREEZE
    │
    ▼
V2 SKELETON
    │
    ▼
2.0.0a1
DOMAIN FOUNDATIONS
    │
    ▼
2.0.0a2
RUNTIME ABSTRACTION
    │
    ▼
2.0.0a3
EFFECTS + RECONCILIATION + RECOVERY
    │
    ▼
2.0.0a4
PERSISTENCE V2
    │
    ▼
2.0.0b1
GOVERNANCE + SECURITY + AUDIT
    │
    ▼
2.0.0b2
EXTERNAL RUNTIMES + CONNECTORS
    │
    ▼
2.0.0rc1
MIGRATION + PUBLIC CONTRACTS + QUALIFICATION
    │
    ▼
2.0.0
PRODUCTION QUALIFIED
```

---

# 7. Phase 0 — Freeze PyAgentsKit V1.6

Avant le premier commit V2 structurel, figer clairement V1.

Objectifs :

```text
preserve behavior
preserve public API
preserve existing qualification
avoid accidental semantic drift
```

---

# 8. Actions V1.6

Créer ou vérifier :

```text
V1 public API freeze
V1 regression suite
V1 package build
V1 compatibility reference
```

---

# 9. Freeze Scope

Les zones à ne plus restructurer directement sauf bugfix :

```text
Runner public API
RunStatus V1
Session V1
Message V1
EffectRecord V1
ApprovalStatus V1
```

---

# 10. V1 Maintenance Rule

Après démarrage V2 :

```text
1.6.x
=
maintenance only
```

Pas de nouvelles abstractions V2 injectées dans la surface V1.

---

# 11. V1 Compatibility Boundary

Créer progressivement :

```text
compat/v1/
```

pour isoler les adaptations.

---

# 12. Phase 1 — Resolve Only Blocking ADRs

Le corpus compte déjà un grand nombre d’ADRs identifiés.

Il ne faut pas tous les fermer avant le code.

Résoudre uniquement les décisions qui bloquent `2.0.0a1`.

---

# 13. ADRs P0 à trancher maintenant

Minimum :

```text
ADR — Domain entity modeling style
ADR — Identifier strategy
ADR — Aggregate version / optimistic concurrency semantics
ADR — Canonical error taxonomy
ADR — Public serialization boundary
ADR — Dataclass vs Pydantic boundary
```

---

# 14. ADRs pouvant attendre

Exemples :

```text
multi-region
broker selection
advanced scheduler
plugin marketplace
RLS strategy
full HTTP API
enterprise IAM provider matrix
```

---

# 15. ADR Decision Principle

Une ADR est urgente uniquement si elle empêche :

```text
writing stable Domain code
```

---

# 16. Phase 2 — Create V2 Codebase Skeleton

La topologie cible devient réelle.

```text
src/pyagentskit/
  contracts/
  domain/
  application/
  adapters/
  api/
  bootstrap/
  compat/
  testing/

tests/
docs/
examples/
scripts/
```

---

# 17. Initial Domain Layout

```text
src/pyagentskit/domain/
  shared/
  execution/
  effects/
  governance/
  coordination/
  conversations/
  runtime_integration/
  artifacts/
  audit/
```

---

# 18. Application Layout

```text
src/pyagentskit/application/
  execution/
  effects/
  governance/
  conversations/
  runtime_integration/
  artifacts/
```

---

# 19. Adapter Layout

```text
src/pyagentskit/adapters/
  persistence/
  runtimes/
  connectors/
  models/
  observability/
  identity/
```

---

# 20. Bootstrap Layout

```text
src/pyagentskit/bootstrap/
  container.py
  runtime_registry.py
  settings.py
```

---

# 21. Compatibility Layout

```text
src/pyagentskit/compat/
  v1/
```

---

# 22. Testing Layout

```text
tests/
  unit/
  property/
  contracts/
  integration/
  concurrency/
  failure/
  distributed/
  migration/
  security/
  performance/
  qualification/
```

---

# 23. Phase 3 — Enforce Architecture Before Features

Avant d’écrire trop de code métier, activer les règles de dépendance.

Direction obligatoire :

```text
BOOTSTRAP
   ↓
API / ADAPTERS
   ↓
APPLICATION
   ↓
DOMAIN
```

---

# 24. CI Architecture Checks

Prouver :

```text
Domain imports no Adapter
Domain imports no API
Application imports no concrete Adapter
V2 Domain imports no compat.v1
Runtime adapters do not depend on connectors directly
```

---

# 25. Why Early Enforcement

Une architecture non vérifiée par CI finit rapidement par devenir :

```text
documentation only
```

---

# 26. Milestone 2.0.0a1 — Domain Foundations

C’est le **prochain milestone concret**.

Objectif :

> **Créer un Domain V2 autonome, cohérent, testé et indépendant de l’infrastructure.**

---

# 27. a1 Scope

Implémenter :

```text
Shared Kernel
Run
Session
Conversation
Message
Actor
Participant
Effect
Approval
Lease
Worker
Artifact
RuntimeBinding
RuntimeInvocation
ReconciliationCase
AuditEvent
```

---

# 28. Shared Kernel First

Créer d’abord :

```text
IDs
TenantId
AggregateVersion
Timestamp helpers
Canonical domain errors
Fingerprint
ExternalReference
FencingToken
```

---

# 29. Identifier Types

Exemples :

```text
RunId
SessionId
ConversationId
MessageId
EffectId
ApprovalId
LeaseId
WorkerId
ArtifactId
RuntimeBindingId
RuntimeInvocationId
ReconciliationCaseId
```

---

# 30. Avoid Primitive Obsession

Préférer :

```text
RunId
```

à :

```text
str everywhere
```

pour les identités critiques.

---

# 31. Execution Context

Implémenter :

```text
Run
RunStatus
Session
```

---

# 32. RunStatus V2

Cible :

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

# 33. Critical Run Invariants

```text
WAITING != terminal
PAUSED != WAITING
Runtime completion != Run success
Cancellation != rollback
```

---

# 34. Conversation Context

Implémenter :

```text
Conversation
Actor
Participant
ConversationMessage
MessageRecipient
```

---

# 35. Critical Conversation Invariants

```text
Session != Conversation
ConversationMessage != RuntimeMessage
Message != Approval
```

---

# 36. Effects Context

Implémenter :

```text
Effect
EffectStatus
EffectFingerprint
ExternalReference
```

---

# 37. EffectStatus V2

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

# 38. Critical Effect Invariants

```text
UNKNOWN != FAILED
SUCCEEDED is never replayable
ToolCall != Effect
Retry != Reconciliation
```

---

# 39. Governance Context

Implémenter :

```text
Approval
ApprovalStatus
ApprovalScope
```

---

# 40. ApprovalStatus V2

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

---

# 41. Governance Invariants

```text
Approval != Authorization
Approval scope is exact
Approval can expire
free text != Approval
```

---

# 42. Coordination Context

Implémenter :

```text
Lease
OwnershipContext
FencingToken
Worker
```

---

# 43. Coordination Invariants

```text
Lease != Lock
Lease != Authorization
FencingToken != Credential
Heartbeat != Ownership
```

---

# 44. Runtime Integration Domain

Implémenter au niveau Domain :

```text
RuntimeBinding
RuntimeInvocation
RuntimeCapability
RuntimeDescriptor snapshots
```

---

# 45. Critical Runtime Invariants

```text
Run != RuntimeInvocation
Binding != Invocation
Runtime output != Authority
```

---

# 46. Artifact Context

Implémenter :

```text
Artifact
ArtifactId
ArtifactChecksum
ArtifactReference
```

---

# 47. Audit Context

Implémenter :

```text
AuditEvent
```

sans dépendre d’un backend observability.

---

# 48. Reconciliation Foundation

Implémenter au minimum :

```text
ReconciliationCase
ReconciliationStatus
ReconciliationResolution
```

sans encore construire toutes les integrations providers.

---

# 49. a1 Tests

Obligatoires dès le milestone :

```text
state-machine tests
invalid transition tests
property-based tests
serialization tests
architecture dependency tests
```

---

# 50. a1 No Infrastructure Rule

`2.0.0a1` ne doit pas nécessiter :

```text
PostgreSQL
LangGraph
Codex
GitHub
Kubernetes
```

pour démontrer sa valeur.

---

# 51. a1 Exit Criteria

`2.0.0a1` est prêt lorsque :

1. Domain package existe ;
2. IDs sont typés ;
3. state machines sont stabilisées ;
4. invariants P0 ont des tests ;
5. architecture checks sont actifs ;
6. aucune dépendance infra dans Domain ;
7. package build/install fonctionne ;
8. API alpha minimale est documentée ;
9. changelog existe ;
10. tag/release alpha peut être produit.

---

# 52. Milestone 2.0.0a2 — Runtime Abstraction

Après le Domain, implémenter la neutralité runtime.

---

# 53. a2 Core Components

```text
AgentRuntimeAdapter
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeRequirements
RuntimeRegistry
CapabilityNegotiator
```

---

# 54. AgentRuntimeAdapter

Contract :

```text
start
resume
cancel
inspect
events
checkpoint
close
```

---

# 55. Runtime Registry

Créer :

```text
InMemoryRuntimeRegistry
```

d’abord.

Pas besoin de service externe.

---

# 56. Capability Negotiation

Implémenter :

```text
required capabilities
preferred capabilities
minimum control level
minimum qualification
```

---

# 57. SideEffectControlLevel

Stabiliser :

```text
FULL
BOUNDED
OPAQUE
```

---

# 58. NativeRuntimeAdapter

Transformer progressivement le Runner V1.

---

# 59. a2 Migration Rule

```text
Runner V1
→ NativeRuntimeEngine
→ NativeRuntimeAdapter
```

---

# 60. No Big-Bang Rewrite

Utiliser :

```text
characterization tests
wrapper
responsibility extraction
```

---

# 61. Native Runtime First Contracts

Tester :

```text
start
inspect
events
cancel
checkpoint
resume
```

selon capabilities effectivement garanties.

---

# 62. a2 Exit Criteria

1. `AgentRuntimeAdapter` stable alpha ;
2. Native adapter passe Contract Suite ;
3. RuntimeRegistry fonctionne ;
4. CapabilityNegotiator fonctionne ;
5. `RuntimeBinding` durable conceptuellement ;
6. Runner V1 reste compatible ;
7. aucune branche `if native` dans Application ;
8. Native n’est pas privilégié architecturalement.

---

# 63. Milestone 2.0.0a3 — Effects & Recovery Core

Après abstraction runtime, construire la couche de reliability la plus différenciante.

---

# 64. a3 Components

```text
Effect V2
EffectRepository Port
ReconciliationCase
ReconciliationPort
ReconciliationDecisionService
RecoveryPlanner
RecoveryContext
RecoveryPlan
RecoveryBlocker
NextAction
```

---

# 65. W1–W5

Implémenter explicitement les crash windows :

```text
W1 before durable intent
W2 after durable intent, before send
W3 after send, before response
W4 after response, before durable outcome
W5 after durable outcome, before next Run progress
```

---

# 66. a3 Critical Rule

```text
W3/W4
→ UNKNOWN
→ Reconciliation
```

jamais :

```text
UNKNOWN
→ automatic retry
```

---

# 67. NextAction

Stabiliser :

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

# 68. RecoveryPlanner First Principle

```text
state
→ decision
```

Le Planner ne doit pas appeler directement les providers.

---

# 69. a3 Flagship Test

Scénario Git-like :

```text
Effect sent
response lost
worker crash
takeover
reconciliation confirms success
no replay
Run continues
```

---

# 70. a3 Exit Criteria

1. Effect V2 stable alpha ;
2. UNKNOWN distinct de FAILED ;
3. Reconciliation model implémenté ;
4. RecoveryPlanner couvre tous NextAction ;
5. W1–W5 testés ;
6. manual intervention first-class ;
7. Native runtime respecte Effect gates ;
8. aucun replay implicite de SUCCEEDED.

---

# 71. Milestone 2.0.0a4 — Persistence V2

Après les semantics, seulement ensuite normaliser la persistance.

---

# 72. a4 Repository Ports

Implémenter :

```text
RunRepository
SessionRepository
ConversationRepository
MessageRepository
MemoryRepository
EffectRepository
ReconciliationRepository
ApprovalRepository
LeaseRepository
WorkerRepository
ArtifactRepository
```

---

# 73. Stores

```text
BlobStore
AuditStore
OutboxStore
InboxStore
```

---

# 74. UnitOfWork

Implémenter un UnitOfWork local explicite.

---

# 75. PostgreSQL V2 Tables

Cible :

```text
sessions
runs
conversations
participants
messages
message_recipients
memory_entries
checkpoints
effects
reconciliation_cases
approvals
workers
leases
runtime_bindings
runtime_invocations
artifacts
audit_events
outbox_events
inbox_events
```

---

# 76. DB Invariants

Notamment :

```text
FK relationships
tenant-scoped uniqueness
Effect idempotency unique
fencing monotonic
one active lease
append-oriented checkpoints
append-oriented audit
```

---

# 77. Contract Testing

Le même Repository Contract doit passer sur :

```text
Memory
SQLite
PostgreSQL
```

---

# 78. a4 Exit Criteria

1. Ports stabilisés ;
2. Memory implementations ;
3. SQLite support si conservé ;
4. PostgreSQL V2 normalisé ;
5. UoW fonctionnel ;
6. Outbox/Inbox présents ;
7. optimistic concurrency ;
8. multi-process tests ;
9. migrations versionnées ;
10. restore baseline.

---

# 79. Milestone 2.0.0b1 — Governance, Security & Audit

Construire ensuite les garanties de contrôle.

---

# 80. b1 Components

```text
Principal
SecurityContext
AuthorizationPort
IdentityProviderPort
PolicyEvaluator
Approval V2
AuditStore
AuditEvent
SecretReference
```

---

# 81. Critical Separation

```text
Authentication
!=
Authorization
!=
Approval
```

---

# 82. Tenant Isolation

Doit être testée à travers :

```text
Run
Effect
Approval
Conversation
Artifact
```

---

# 83. b1 Exit Criteria

1. AuthN/AuthZ/Approval séparés ;
2. tenant isolation ;
3. Approval fingerprint-bound ;
4. audit critical paths ;
5. secret handling ;
6. security tests ;
7. fail-closed profile.

---

# 84. Milestone 2.0.0b2 — External Runtimes & Connectors

Seulement après Core fiable.

---

# 85. First External Runtime

Choisir un runtime généraliste réellement utile.

Critères :

```text
good contract fit
resume/inspect support
tool interception
community relevance
```

---

# 86. First Coding Runtime

Choisir :

```text
Codex
Claude Code
or equivalent
```

selon meilleure surface d’intégration réelle.

---

# 87. First Connector

Un très bon premier Connector est :

```text
GitHub
```

car il permet :

```text
PR
push
merge
SHA reconciliation
approvals
coding-agent demo
```

---

# 88. b2 Flagship Demo

```text
coding agent
→ edit
→ commit SHA
→ request Approval
→ push
→ timeout
→ UNKNOWN
→ crash
→ takeover
→ reconcile remote SHA
→ no duplicate push
→ resume
```

---

# 89. Why This Demo Matters

Il prouve simultanément :

```text
runtime neutrality
Effect safety
Approval scope
Recovery
Reconciliation
Fencing
Distributed execution
Audit
```

---

# 90. b2 Exit Criteria

1. un runtime externe general-purpose ;
2. un coding runtime ;
3. un Connector write critique ;
4. contract tests ;
5. failure tests ;
6. reconciliation ;
7. documentation des limitations.

---

# 91. Milestone 2.0.0rc1 — Public Contracts & Migration

Le RC doit transformer l’architecture interne en produit consommable.

---

# 92. RC Scope

```text
public API freeze
serialization freeze
error taxonomy
migration V1→V2
compatibility facade
deployment
operations
performance
restore
qualification
```

---

# 93. Public Contracts

Geler :

```text
imports
enums
IDs
errors
runtime contracts
event envelopes
```

---

# 94. V1→V2 Migration

Exécuter :

```text
preflight
expand
backfill
verify
switch
contract later
```

---

# 95. Critical Migration Mappings

```text
WAITING_APPROVAL
→ WAITING + Approval blocker

UNKNOWN_EFFECT
→ WAITING + Effect.UNKNOWN

Effect COMPLETED
→ SUCCEEDED
```

---

# 96. Migration Invariants

```text
no successful Effect lost
no Approval fabricated
no UNKNOWN collapsed
no fencing regression
one authoritative writer per phase
```

---

# 97. RC Production Qualification

Doit couvrir :

```text
SIGTERM
SIGKILL
SIGSTOP
PostgreSQL outage
W1–W5
restore/PITR
rolling upgrade
recovery storm
load
soak
```

---

# 98. Milestone 2.0.0 — Production Qualified

La stable ne doit pas être seulement :

```text
API stable
```

mais :

```text
reliability guarantees qualified
```

---

# 99. No-Waiver Areas

Pas de waiver pour :

```text
Effect safety
Fencing
Tenant isolation
Approval integrity
Restore safety
Migration integrity
```

---

# 100. Immediate Implementation Order

L’ordre de travail recommandé à partir de maintenant est :

```text
1. Freeze V1.6
2. Resolve blocking ADRs
3. Create V2 skeleton
4. Add architecture CI rules
5. Build Shared Kernel
6. Build Domain state machines
7. Add domain/property tests
8. Release 2.0.0a1
9. Build AgentRuntimeAdapter
10. Build Registry/Negotiation
11. Build NativeRuntimeAdapter
12. Release 2.0.0a2
13. Build Effect/Reconciliation/Recovery
14. Release 2.0.0a3
15. Build persistence V2
16. Release 2.0.0a4
```

---

# 101. First Concrete Coding Sprint

Le premier sprint doit rester focalisé.

---

# 102. Sprint Goal

> **Create a production-quality V2 Domain skeleton with enforceable architecture rules.**

---

# 103. Sprint Tasks — Repository Structure

```text
[ ] create contracts/
[ ] create domain/
[ ] create application/
[ ] create adapters/
[ ] create api/
[ ] create bootstrap/
[ ] create compat/v1/
[ ] create testing/
[ ] mirror tests structure
```

---

# 104. Sprint Tasks — Shared Kernel

```text
[ ] base IDs
[ ] TenantId
[ ] AggregateVersion
[ ] Fingerprint
[ ] FencingToken
[ ] ExternalReference
[ ] canonical DomainError base
```

---

# 105. Sprint Tasks — Run

```text
[ ] Run entity
[ ] RunStatus enum
[ ] transitions
[ ] terminality
[ ] WAITING semantics
[ ] PAUSED semantics
[ ] tests
```

---

# 106. Sprint Tasks — Effect

```text
[ ] Effect entity
[ ] EffectStatus enum
[ ] fingerprint
[ ] idempotency identity
[ ] external reference
[ ] transition rules
[ ] tests
```

---

# 107. Sprint Tasks — Approval

```text
[ ] Approval entity
[ ] ApprovalStatus enum
[ ] scope
[ ] expiry
[ ] transition rules
[ ] tests
```

---

# 108. Sprint Tasks — Coordination

```text
[ ] Lease entity
[ ] OwnershipContext
[ ] FencingToken
[ ] Worker identity
[ ] tests
```

---

# 109. Sprint Tasks — Conversations

```text
[ ] Session
[ ] Conversation
[ ] Actor
[ ] Participant
[ ] ConversationMessage
[ ] tests
```

---

# 110. Sprint Tasks — Runtime Integration Foundations

```text
[ ] RuntimeBinding
[ ] RuntimeInvocation
[ ] RuntimeCapability enum
[ ] tests
```

---

# 111. Sprint Tasks — Artifacts & Audit

```text
[ ] Artifact
[ ] ArtifactChecksum
[ ] AuditEvent
[ ] tests
```

---

# 112. Sprint Tasks — Architecture Enforcement

```text
[ ] import-linter or equivalent
[ ] forbidden dependency rules
[ ] CI job
[ ] test rule violations
```

---

# 113. Sprint Tasks — Package

```text
[ ] pyproject version 2.0.0a1
[ ] build wheel
[ ] build sdist
[ ] fresh venv install
[ ] import smoke test
```

---

# 114. Sprint Tasks — Documentation

```text
[ ] changelog entry
[ ] migration note: alpha only
[ ] architecture README
[ ] domain package README if useful
```

---

# 115. Sprint Definition of Done

Le premier sprint est terminé si :

```text
V2 package skeleton exists
Domain imports no infrastructure
all Domain P0 tests pass
architecture checks pass
wheel builds
sdist builds
fresh install works
```

---

# 116. What Not To Do in First Sprint

Ne pas commencer par :

```text
Kubernetes
LangGraph
Codex
GitHub
S3
full PostgreSQL model
HTTP API
```

---

# 117. Why

Ils ajouteraient de l’intégration avant que :

```text
the semantics are stable
```

---

# 118. P0 Invariants to Encode First

Le code doit rendre impossibles ou explicitement invalides :

```text
Run == RuntimeInvocation
Session == Conversation
Message == Approval
ToolCall == Effect
UNKNOWN == FAILED
WAITING == PAUSED
Approval == Authorization
Lease == Authorization
Checkpoint == Effect truth
Runtime completion == Run success
```

---

# 119. Domain API Principle

Préférer :

```text
run.mark_waiting(...)
effect.mark_unknown(...)
approval.approve(...)
lease.takeover(...)
```

à :

```text
object.status = ...
```

---

# 120. Why

Les transitions deviennent :

```text
explicit
validated
testable
auditable
```

---

# 121. Domain Model Style

Les entities doivent protéger leurs invariants.

Éviter :

```text
anemic mutable DTOs
```

pour les aggregates critiques.

---

# 122. Serialization Boundary

Le Domain ne doit pas être conçu uniquement autour de :

```text
JSON convenience
```

Les DTO/contracts peuvent mapper le Domain.

---

# 123. Persistence Boundary

Ne pas introduire ORM annotations directement dans les Domain entities si cela couple le modèle à PostgreSQL.

---

# 124. Test-First Priorities

Commencer par :

```text
state transitions
invalid transitions
terminality
idempotency identity
fencing comparisons
approval scope
```

---

# 125. Characterization Tests V1

En parallèle, capturer les comportements utiles du Runner V1 avant extraction.

---

# 126. Characterization Scenarios

```text
simple model response
tool call
tool failure
approval wait
model failure
cancel
limits
session/message flow
```

---

# 127. Explicit Semantic Break Tests

Créer aussi des tests qui prouvent que V2 est volontairement différent sur :

```text
WAITING_APPROVAL terminality
UNKNOWN_EFFECT treatment
Session/Conversation distinction
Approval status semantics
```

---

# 128. Branching Strategy

Recommandation :

```text
main
+
feature branches per milestone/task
```

Une branche majeure V2 longue peut devenir difficile à intégrer.

---

# 129. Release Tags

```text
v2.0.0a1
v2.0.0a2
v2.0.0a3
v2.0.0a4
v2.0.0b1
v2.0.0b2
v2.0.0rc1
v2.0.0
```

---

# 130. Changelog Discipline

Chaque milestone doit documenter :

```text
Added
Changed
Deprecated
Removed
Fixed
Security
```

selon contenu.

---

# 131. CI Evolution by Milestone

## a1

```text
lint
typecheck
architecture
unit
property
package
```

## a2

Ajouter :

```text
runtime contracts
```

## a3

Ajouter :

```text
failure injection
W1–W5
```

## a4

Ajouter :

```text
PostgreSQL
multi-process
migration
```

---

# 132. b1 CI

Ajouter :

```text
security
tenant isolation
audit
```

---

# 133. b2 CI

Ajouter :

```text
external runtimes
connectors
sandbox qualification
```

---

# 134. RC CI

Ajouter :

```text
restore
performance
soak
distributed qualification
```

---

# 135. Package Compatibility Strategy

Maintenir :

```text
V1 public API tests
```

tant que compat supportée.

---

# 136. Public API Freeze Timing

Ne pas geler toute la V2 en a1.

Le freeze public majeur intervient avant :

```text
2.0.0rc1
```

---

# 137. Alpha Freedom

Les releases alpha peuvent ajuster :

```text
names
module layout
contracts
```

avec discipline.

---

# 138. Avoid Premature Compatibility Burden

Ne pas promettre stabilité de toutes les APIs internes dès a1.

---

# 139. Milestone Review

À la fin de chaque milestone :

```text
architecture review
API review
test review
gap review
```

---

# 140. Update Gap Analysis

Le document de Gap Analysis doit être réévalué après :

```text
a1
a2
a3
a4
```

---

# 141. Coverage of Original Gaps

Objectif :

```text
55.3% target coverage
→ progressively approach full V2 target
```

sans utiliser ce chiffre comme KPI unique.

---

# 142. Better KPI

Mesurer :

```text
P0 invariants implemented
P0 invariants tested
Ports contract-tested
failure scenarios qualified
```

---

# 143. Implementation Scorecard

Exemple :

| Area | Spec | Code | Unit | Contract | Failure | Qualified |
|---|---:|---:|---:|---:|---:|---:|
| Domain | ✓ |  |  | n/a | n/a |  |
| Runtime | ✓ |  |  |  |  |  |
| Effects | ✓ |  |  |  |  |  |
| Recovery | ✓ |  |  | n/a |  |  |
| Persistence | ✓ |  |  |  |  |  |
| Governance | ✓ |  |  |  |  |  |
| Connectors | ✓ |  |  |  |  |  |

---

# 144. Architecture Debt Rule

Si une implémentation exige de violer une règle du document 29 :

```text
stop
review architecture
```

plutôt que contourner silencieusement.

---

# 145. Documentation Debt Rule

Le corpus n’a pas besoin d’être étendu à chaque petit détail.

Créer un nouveau document uniquement si :

```text
new stable architectural concept emerges
```

---

# 146. Code Over Documentation From Now On

Priorité :

```text
implementation
tests
qualification
```

avant :

```text
additional conceptual docs
```

---

# 147. First Deliverable After This Document

Le prochain livrable utile n’est donc plus un document d’architecture.

C’est :

```text
PyAgentsKit 2.0.0a1 — Domain Foundations
```

sous forme de code réel.

---

# 148. Recommended First Commit

Exemple :

```text
feat(v2-domain): scaffold DDD/hexagonal package topology
```

---

# 149. Second Commit

```text
feat(v2-domain): add shared identifiers and aggregate primitives
```

---

# 150. Third Commit

```text
feat(v2-domain): add Run and execution state machine
```

---

# 151. Fourth Commit

```text
feat(v2-domain): add Effect and reconciliation foundations
```

---

# 152. Fifth Commit

```text
feat(v2-domain): add Approval and coordination primitives
```

---

# 153. Sixth Commit

```text
feat(v2-domain): add conversations, runtime binding and artifacts
```

---

# 154. Seventh Commit

```text
test(v2-domain): add property and architecture invariant suites
```

---

# 155. Eighth Commit

```text
build(v2): prepare 2.0.0a1 release artifacts
```

---

# 156. a1 Suggested Package Surface

Exemple provisoire :

```python
from pyagentskit.domain import (
    Run,
    RunId,
    RunStatus,
    Effect,
    EffectId,
    EffectStatus,
    Approval,
    ApprovalId,
    ApprovalStatus,
    Lease,
    FencingToken,
    RuntimeBinding,
    RuntimeInvocation,
)
```

À valider avant freeze public.

---

# 157. Alpha API Discipline

Même alpha, éviter de publier :

```text
internal implementation helpers
```

par erreur.

---

# 158. Error Taxonomy Initial Set

Candidats :

```text
DomainError
InvalidTransition
InvariantViolation
ConflictError
NotFoundError
ConcurrencyConflict
IdempotencyConflict
```

---

# 159. Later Error Extensions

a2+ :

```text
RuntimeCapabilityUnsupported
RuntimeUnavailable
```

a3+ :

```text
ReconciliationRequired
EvidenceInsufficient
```

a4+ :

```text
PersistenceConflict
```

---

# 160. Domain Event Integration

Le document 33 devient utile dès a1/a4.

a1 :

```text
DomainEvent primitives
```

a4 :

```text
Outbox/Inbox persistence
```

---

# 161. Testing Package Evolution

Dès a1, commencer :

```text
pyagentskit.testing
```

avec :

```text
builders
assertions
```

Puis a2/a4 :

```text
contracts
fakes
faults
```

---

# 162. Example Test Builders

```text
RunBuilder
EffectBuilder
ApprovalBuilder
LeaseBuilder
```

---

# 163. Architecture Test Examples

Interdire :

```text
pyagentskit.domain.*
→ pyagentskit.adapters.*
```

et :

```text
pyagentskit.domain.*
→ pyagentskit.compat.*
```

---

# 164. First Property-Based Tests

Candidats :

```text
ID round-trip
fingerprint stability
terminal states cannot reopen
fencing token comparison
Approval scope stability
```

---

# 165. First State-Machine Tests

Priorité :

```text
Run
Effect
Approval
Lease
```

---

# 166. First Negative Tests

```text
SUCCEEDED Effect → STARTED forbidden
APPROVED → REJECTED forbidden
Run SUCCEEDED → RUNNING forbidden
stale fencing lower token rejected
```

---

# 167. First Cross-Domain Invariant Tests

Même sans Application layer complet :

```text
RuntimeInvocation completion does not imply Run completion
Message cannot satisfy Approval
Checkpoint does not alter Effect state
```

---

# 168. Release 2.0.0a1 Evidence

Conserver :

```text
test report
coverage
package checksums
public symbols
architecture checks
```

---

# 169. SHA-256

Continuer la discipline déjà utilisée sur les releases existantes.

---

# 170. Release Notes a1

Expliquer clairement :

```text
what is implemented
what is not
alpha limitations
migration status
```

---

# 171. What a1 Must Not Claim

Ne pas prétendre :

```text
production ready
external runtime support complete
distributed execution V2 complete
```

---

# 172. Product Narrative at a1

Positionnement :

> **The V2 domain foundation of PyAgentsKit’s agent reliability layer.**

---

# 173. Product Narrative at a3

Peut évoluer vers :

> **Framework-neutral Effect safety and recovery semantics for real-world agents.**

---

# 174. Product Narrative at Stable

Cible :

> **Agent Reliability Layer for Real-World AI Applications.**

---

# 175. Risks

Principaux risques d’implémentation :

```text
overengineering Domain
leaking V1 semantics into V2
rewriting too much
premature infrastructure work
runtime-specific coupling
insufficient failure testing
```

---

# 176. Risk Mitigation — Overengineering

Préférer :

```text
explicit simple Python
```

avant frameworks internes génériques.

---

# 177. Risk Mitigation — V1 Leakage

Isoler dans :

```text
compat/v1
native runtime adapter
```

---

# 178. Risk Mitigation — Rewrite

Réutiliser :

```text
providers
tools
guardrails
leases
blobs
observability
qualification infrastructure
```

là où semantics restent valides.

---

# 179. Risk Mitigation — Infra First

Refuser de construire PostgreSQL/Kubernetes avant stabilisation du Domain.

---

# 180. Risk Mitigation — Runtime Coupling

Toutes integrations passent par :

```text
AgentRuntimeAdapter
```

---

# 181. Risk Mitigation — Weak Testing

Tests par invariant, pas seulement par ligne de code.

---

# 182. Success Criteria for Transition

La transition documentaire → implémentation est réussie si :

```text
architecture documents stop growing rapidly
codebase V2 starts growing
tests encode invariants
alpha releases prove milestones
```

---

# 183. Decision Gate Before a1 Release

Avant `2.0.0a1`, répondre oui à :

```text
[ ] Domain independent from infrastructure?
[ ] Run state machine stable?
[ ] Effect UNKNOWN modeled?
[ ] Approval lifecycle clean?
[ ] Lease/Fencing primitives clean?
[ ] Session != Conversation encoded?
[ ] Run != RuntimeInvocation encoded?
[ ] architecture checks active?
[ ] package builds?
[ ] tests green?
```

---

# 184. Decision Gate Before a2 Release

```text
[ ] AgentRuntimeAdapter contract stable?
[ ] NativeRuntimeAdapter passes?
[ ] Registry works?
[ ] Capability negotiation deterministic?
[ ] no runtime-specific branches in Application?
```

---

# 185. Decision Gate Before a3 Release

```text
[ ] W1–W5 modeled?
[ ] ReconciliationCase implemented?
[ ] RecoveryPlanner implemented?
[ ] UNKNOWN never blindly retried?
[ ] manual intervention supported?
```

---

# 186. Decision Gate Before a4 Release

```text
[ ] repositories contract-tested?
[ ] PostgreSQL normalized?
[ ] UoW atomic?
[ ] Outbox/Inbox operational?
[ ] multi-process tests pass?
```

---

# 187. Final Strategic Principle

Tout le travail documentaire converge vers une idée :

```text
Build semantics.
Integrate infrastructure.
Qualify failures.
```

---

# 188. Immediate Next Action

La prochaine action concrète recommandée est :

> **Ouvrir le repository PyAgentsKit, geler la baseline 1.6.x, créer la topologie V2 et commencer `2.0.0a1 — Domain Foundations`.**

---

# 189. Résumé

La séquence opérationnelle est :

```text
DOCUMENTATION COMPLETE
        │
        ▼
FREEZE V1.6
        │
        ▼
RESOLVE BLOCKING ADRs
        │
        ▼
CREATE V2 SKELETON
        │
        ▼
ENFORCE DEPENDENCY RULES
        │
        ▼
IMPLEMENT DOMAIN FOUNDATIONS
        │
        ▼
RELEASE 2.0.0a1
        │
        ▼
RUNTIME ABSTRACTION
        │
        ▼
RELEASE 2.0.0a2
        │
        ▼
EFFECTS + RECOVERY
        │
        ▼
RELEASE 2.0.0a3
        │
        ▼
PERSISTENCE V2
        │
        ▼
RELEASE 2.0.0a4
        │
        ▼
GOVERNANCE / SECURITY
        │
        ▼
EXTERNAL RUNTIMES / CONNECTORS
        │
        ▼
RC QUALIFICATION
        │
        ▼
V2 PRODUCTION QUALIFIED
```

La règle finale est :

> **À partir de maintenant, chaque nouvelle idée architecturale doit justifier sa place par du code, des tests ou une garantie de production mesurable ; PyAgentsKit V2 entre dans sa phase d’implémentation.**
