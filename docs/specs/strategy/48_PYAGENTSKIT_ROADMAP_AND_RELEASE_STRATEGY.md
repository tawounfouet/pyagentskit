# PyAgentsKit — Roadmap & Release Strategy

**Document :** `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Roadmap canonique V2 & Release Strategy  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
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
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../strategy/45_PYAGENTSKIT_BUILD_VS_BUY_VS_INTEGRATE.md`
- `../architecture/46_PYAGENTSKIT_ARCHITECTURE_DECISION_RECORDS_INDEX.md`
- `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`
- `../strategy/PYAGENTSKIT_EXISTING_VS_TARGET_GAP_ANALYSIS_2026-10-21.md`
- `../architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`

---

# 1. Objet

Ce document définit la **roadmap canonique et la stratégie de release** de PyAgentsKit après la stabilisation de la V1.6 et la formalisation de la cible V2.

Il répond aux questions suivantes :

```text
1. Quelle trajectoire suivre de V1.6.x à V2.0.0 ?
2. Quelles capacités appartiennent à chaque release ?
3. Quelles dépendances existent entre les chantiers ?
4. Quels critères doivent être satisfaits pour passer alpha → beta → RC → stable ?
5. Quelles garanties doivent rester vraies à chaque étape ?
6. Comment maintenir la V1 pendant la construction de la V2 ?
7. Quand une feature est-elle "implémentée", "qualifiée" puis "stable" ?
```

Le principe directeur est :

> **Chaque release doit augmenter la portée de PyAgentsKit sans réduire les garanties de sûreté déjà obtenues.**

---

# 2. Point de départ — PyAgentsKit 1.6.0

La V1.6 constitue une base déjà mature.

Capacités existantes importantes :

```text
typed mono-agent execution
provider-neutral Model abstraction
ToolRegistry / ToolExecutor
guardrails
durable Runs
Effects
UNKNOWN effect handling
Approvals
Sessions / Memory
Artifacts / Blob stores
Lease
Fencing
DistributedDurableRunner
DistributedWorkerController
PostgreSQL stores
OpenTelemetry
multi-process qualification
SIGTERM / SIGKILL / SIGSTOP tests
```

Les preuves existantes de V1.6 doivent être considérées comme un capital à préserver.

---

# 3. Changement de positionnement

## V1

```text
Provider-neutral Python agent runtime
```

## V2

```text
Framework-neutral Agent Reliability Layer
for real-world AI applications
```

La V2 élève le niveau d’abstraction :

```text
Model
→ Runtime

ToolCall
→ Effect

Runner lifecycle
→ Durable Run lifecycle

single runtime implementation
→ runtime adapter ecosystem
```

---

# 4. North Star

La promesse cible est :

> **Build agents with any runtime. Run them with PyAgentsKit reliability.**

Cette promesse n’est considérée réellement atteinte que lorsqu’au moins :

```text
Native Runtime
+
one external general-purpose runtime
+
one coding runtime
```

partagent les mêmes garanties de :

```text
Run durability
Effect safety
Approval governance
Lease/Fencing
Recovery
Audit
```

---

# 5. Release families

La trajectoire proposée est :

```text
1.6.x      V1 maintenance line

2.0.0a1    Domain Foundations
2.0.0a2    Runtime Abstraction
2.0.0a3    Effects & Recovery
2.0.0a4    Persistence V2

2.0.0b1    Governance, Security & Audit
2.0.0b2    External Runtimes & Connectors

2.0.0rc1   Public Contracts, Migration & Qualification Candidate

2.0.0      Production Qualified V2
```

---

# 6. Semantic Versioning

PyAgentsKit suit une politique compatible avec SemVer :

```text
MAJOR.MINOR.PATCH
```

## MAJOR

Breaking change sur les contrats stables.

## MINOR

Feature additive compatible.

## PATCH

Bug fix / security fix / internal hardening compatible.

---

# 7. Pre-release semantics

```text
aN   alpha
bN   beta
rcN  release candidate
```

Les contrats marqués `EXPERIMENTAL` ou `BETA` peuvent évoluer pendant les pré-releases.

Les contrats `STABLE` ne doivent pas être cassés sans décision explicite.

---

# 8. V1.6.x policy

Pendant le développement V2, la branche V1 stable reçoit uniquement :

```text
security fixes
critical bug fixes
production reliability fixes
compatibility fixes
documentation corrections
```

Elle ne reçoit plus de grandes abstractions V2.

---

# 9. V1 compatibility promise

Les garanties V1.6.x doivent inclure :

```text
root import compatibility
frozen public exports
frozen public enum values
serialized contract compatibility
behavioral regression tests
```

---

# 10. V2 roadmap — vue globale

```text
                    V1.6.x Maintenance
                           │
                           ▼
                    ┌─────────────┐
                    │ 2.0.0a1     │
                    │ Domain Core │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ 2.0.0a2     │
                    │ Runtime ACL │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ 2.0.0a3     │
                    │ Effects +   │
                    │ Recovery    │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ 2.0.0a4     │
                    │ Persistence │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ 2.0.0b1     │
                    │ Governance  │
                    │ Audit       │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ 2.0.0b2     │
                    │ Ecosystem   │
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ 2.0.0rc1    │
                    │ Migration + │
                    │ Qualification│
                    └──────┬──────┘
                           ▼
                    ┌─────────────┐
                    │ 2.0.0       │
                    │ Stable      │
                    └─────────────┘
```

---

# 11. Epic mapping

La roadmap reprend les Epics du document 26 :

```text
Epic 0  Freeze V1 compatibility boundary
Epic 1  Domain Core V2
Epic 2  Agent Runtime Adapter
Epic 3  Native Runtime Adapter
Epic 4  Effect & Reconciliation V2
Epic 5  RecoveryPlanner V2
Epic 6  Persistence Ports V2
Epic 7  PostgreSQL Normalized Model
Epic 8  Governance & Security
Epic 9  Audit / Outbox / Inbox
Epic 10 Coding Agent Integration
Epic 11 External Connectors
Epic 12 Public API V2
Epic 13 V1 → V2 Migration
Epic 14 Production Qualification
```

---

# 12. Release 2.0.0a1 — Domain Foundations

## Objectif

Créer le **socle sémantique V2** sans dépendance aux infrastructures.

## Epics

```text
Epic 0
Epic 1
```

---

# 13. 2.0.0a1 — Scope

Inclut :

```text
V1 compatibility inventory
V2 package skeleton
Domain shared kernel
Execution domain
Effects domain
Governance domain
Coordination domain
Conversations domain
Runtime Integration canonical model
Artifacts domain
Audit domain
architecture dependency rules
```

---

# 14. 2.0.0a1 — Critical semantic decisions

Doivent être verrouillées :

```text
Run != RuntimeInvocation
Session != Conversation
RuntimeMessage != ConversationMessage
ToolCall != Effect
Approval != Authorization
Lease != Run
AuditEvent != RuntimeEvent
WAITING != terminal
UNKNOWN != FAILED
```

---

# 15. 2.0.0a1 — Deliverables

```text
domain/*
contracts/*
compatibility manifest
architecture CI baseline
P0 ADR batch
domain tests
```

---

# 16. 2.0.0a1 — Exit Criteria

```text
[ ] V1 tests green
[ ] V1 public surface unchanged
[ ] Domain imports no adapters
[ ] Bounded Contexts represented in code
[ ] Shared Kernel minimal
[ ] Core domain invariants unit tested
[ ] Run/Effect/Approval/Lease state models explicit
[ ] import architecture checks active
```

---

# 17. 2.0.0a1 — Not Included

Pas encore :

```text
external runtime
PostgreSQL V2
connectors
public HTTP API
coding agent integration
production qualification
```

---

# 18. Release 2.0.0a2 — Runtime Abstraction

## Objectif

Faire de PyAgentsKit une architecture **runtime-neutral**.

## Epics

```text
Epic 2
Epic 3
```

---

# 19. 2.0.0a2 — Scope

```text
AgentRuntimeAdapter
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeRegistry
RuntimeAdapter errors
FakeRuntimeAdapter
NativeRuntimeAdapter
V1 Runner ACL
runtime adapter contract suite
```

---

# 20. 2.0.0a2 — Proof Point

Le Runner V1 doit être utilisable comme :

```text
NativeRuntimeAdapter
```

sans changement comportemental pour les consommateurs V1.

---

# 21. 2.0.0a2 — Exit Criteria

```text
[ ] FakeRuntimeAdapter passes contract suite
[ ] NativeRuntimeAdapter passes contract suite
[ ] V1 Runner still works directly
[ ] V2 Application can start Native runtime
[ ] RuntimeHandle opaque
[ ] capabilities explicit and truthful
[ ] no runtime-specific conditional in core
```

---

# 22. 2.0.0a2 — Architecture Proof

Le flow suivant doit fonctionner :

```text
Create V2 Run
↓
select NativeRuntimeAdapter
↓
start RuntimeInvocation
↓
observe runtime completion
↓
complete V2 Run
```

---

# 23. Release 2.0.0a3 — Effects & Recovery Core

## Objectif

Faire converger les garanties V1 de durability/effects vers le modèle générique V2.

## Epics

```text
Epic 4
Epic 5
```

---

# 24. 2.0.0a3 — Scope

```text
Effect V2
EffectGateway
EffectRepository contract
Idempotency model
ReconciliationCase
ReconciliationPort
ReconciliationResult
RecoveryPlanner
RecoveryPlan
RecoveryBlocker
NextAction
V1 Effect compatibility bridge
```

---

# 25. 2.0.0a3 — Safety Guarantees

Obligatoires :

```text
SUCCEEDED not replayed
UNKNOWN not converted to FAILED
blind retry forbidden
idempotency conflict explicit
manual intervention supported
recovery deterministic
```

---

# 26. 2.0.0a3 — Required crash scenarios

```text
W1 before intent
W2 after intent before send
W3 after send before response
W4 after response before durable result
W5 after durable result before Run progression
```

---

# 27. 2.0.0a3 — Exit Criteria

```text
[ ] Effect state machine tested
[ ] ReconciliationCase implemented
[ ] EffectGateway used for protected actions
[ ] RecoveryPlanner deterministic
[ ] UNKNOWN recovery tested
[ ] V1 EffectRecord mapping tested
[ ] successful Effect cannot be implicitly replayed
```

---

# 28. 2.0.0a3 — Architecture Proof

```text
Run
↓
EffectGateway
↓
external timeout after send
↓
Effect.UNKNOWN
↓
RecoveryPlanner
↓
Reconciliation
↓
safe continuation
```

---

# 29. Release 2.0.0a4 — Persistence V2

## Objectif

Introduire la persistance normalisée compatible avec le nouveau Domain.

## Epics

```text
Epic 6
Epic 7
```

---

# 30. 2.0.0a4 — Scope

```text
Repository ports
UnitOfWork
Memory repositories
SQLite local repositories
PostgreSQL V2
normalized schema
migrations
effect uniqueness
optimistic concurrency
lease_resources
lease history
runtime_invocations
```

---

# 31. 2.0.0a4 — PostgreSQL Tables

Minimum :

```text
sessions
runs
conversations
participants
messages
memory_entries
checkpoints
effects
reconciliation_cases
approvals
workers
lease_resources
leases
runtime_bindings
runtime_invocations
artifacts
```

`audit_events`, `outbox_events`, `inbox_events` peuvent être finalisés en b1.

---

# 32. 2.0.0a4 — Exit Criteria

```text
[ ] Memory repository contracts green
[ ] SQLite relevant contracts green
[ ] PostgreSQL contracts green
[ ] optimistic concurrency working
[ ] idempotency physically enforced
[ ] fencing monotonic
[ ] primary reads used for safety
[ ] schema migrations versioned
[ ] V1 and V2 persistence can coexist
```

---

# 33. 2.0.0a4 — Production Boundary

Cette release peut être techniquement solide mais reste alpha.

Pourquoi ?

Parce que :

```text
governance
audit
external runtime ecosystem
migration
full qualification
```

ne sont pas encore complets.

---

# 34. Release 2.0.0b1 — Governance, Security & Audit

## Objectif

Rendre les garanties de confiance explicites et durables.

## Epics

```text
Epic 8
Epic 9
```

---

# 35. 2.0.0b1 — Scope

```text
Principal
SecurityContext
AuthorizationPort
IdentityProviderPort
PolicyEvaluator
Approval V2
ApprovalScope
Approval revalidation
SoD foundations
AuditEvent
AuditStore
OutboxStore
InboxStore
integration event envelopes
```

---

# 36. 2.0.0b1 — Core Trust Distinctions

```text
Authentication != Authorization
Authorization != Approval
Actor != Principal
Runtime output != authority
Telemetry != Audit
```

---

# 37. 2.0.0b1 — Exit Criteria

```text
[ ] Protected Effect fails closed
[ ] Approval scope fingerprint-bound
[ ] expired approval rejected
[ ] takeover revalidates approval
[ ] SoD baseline implemented
[ ] durable AuditStore available
[ ] Outbox atomic with relevant local transactions
[ ] Inbox deduplicates external delivery
[ ] security contract tests green
```

---

# 38. 2.0.0b1 — Beta Meaning

À partir de b1 :

- la sémantique centrale doit être considérée presque stabilisée ;
- les changements destructifs doivent devenir rares ;
- les migrations internes doivent être explicites ;
- les premières expérimentations externes peuvent commencer.

---

# 39. Release 2.0.0b2 — External Runtime & Connector Ecosystem

## Objectif

Prouver que le modèle fonctionne au-delà du Native Runtime.

## Epics

```text
Epic 10
Epic 11
```

---

# 40. 2.0.0b2 — Required Runtime Set

Minimum :

```text
NativeRuntimeAdapter
one external general-purpose runtime
one coding runtime
```

---

# 41. First general-purpose runtime

Candidat à sélectionner par ADR parmi :

```text
LangGraph
PydanticAI
OpenAI Agents SDK
```

Le choix doit privilégier :

```text
control surface
resume semantics
tool interception
checkpoint/event visibility
real-world adoption
```

---

# 42. First coding runtime

Candidat à sélectionner par ADR parmi :

```text
Codex
Claude Code
OpenCode
```

---

# 43. 2.0.0b2 — Required Connector Set

Minimum :

```text
GitHub
Generic HTTP
```

Pourquoi GitHub ?

Parce qu’il permet de qualifier des Effects réels tels que :

```text
PR creation
merge
remote ref inspection
reconciliation
```

---

# 44. 2.0.0b2 — Coding concepts

```text
Workspace
CommandExecution
RepositoryReference
BranchReference
CommitReference
PatchArtifact
```

---

# 45. 2.0.0b2 — Protected Coding Effects

```text
git push
PR creation
PR merge
package publish
deploy
terraform apply
```

---

# 46. 2.0.0b2 — Exit Criteria

```text
[ ] one external general-purpose runtime passes L2+
[ ] one coding runtime passes L2+
[ ] GitHub connector passes contract suite
[ ] ambiguous external write becomes UNKNOWN
[ ] provider reconciliation works
[ ] coding workspace isolated
[ ] approval bound to relevant SHA/fingerprint
[ ] no runtime SDK object leaks to core
[ ] no connector SDK object leaks to core
```

---

# 47. 2.0.0b2 — Architecture Proof

Le même pattern doit fonctionner pour au moins deux runtime families :

```text
Run
↓
AgentRuntimeAdapter
↓
EffectGateway
↓
Governance
↓
Coordination
↓
Recovery
```

---

# 48. Release 2.0.0rc1 — Public Contracts & Migration

## Objectif

Geler l’expérience V2 publique et prouver la migration depuis V1.6.x.

## Epics

```text
Epic 12
Epic 13
```

---

# 49. 2.0.0rc1 — Scope

```text
async-first Python API
sync facade
public read models
stable error taxonomy
pagination
event cursors
optional HTTP adapter
OpenAPI if retained
migration CLI
migration dry-run
migration verification
V1→V2 guides
deprecation policy
```

---

# 50. 2.0.0rc1 — Public API candidate

Exemple :

```python
from pyagentskit.api import PyAgentsKit

kit = PyAgentsKit(...)
run = await kit.runs.create(...)
await kit.runs.start(run.run_id)
```

---

# 51. Public API domains

```text
kit.runs
kit.sessions
kit.conversations
kit.effects
kit.approvals
kit.artifacts
kit.runtimes
kit.audit
kit.health
```

---

# 52. 2.0.0rc1 — Migration requirements

Support minimum :

```text
latest 1.6.x
→
2.0.0rc1 / 2.0.0
```

---

# 53. Migration command set

Candidate :

```text
pyagentskit migrate inspect
pyagentskit migrate dry-run
pyagentskit migrate apply
pyagentskit migrate verify
pyagentskit migrate status
```

---

# 54. 2.0.0rc1 — Exit Criteria

```text
[ ] public API frozen candidate
[ ] public error codes frozen candidate
[ ] V1→V2 migration works on real dataset
[ ] migration restartable
[ ] migration idempotent
[ ] Effect success preserved
[ ] UNKNOWN preserved
[ ] approval authority preserved
[ ] fencing monotonicity preserved
[ ] docs complete
[ ] deprecated V1 surface documented
```

---

# 55. Release 2.0.0 — Production Qualified

## Objectif

Passer de :

```text
feature complete
```

à :

```text
qualified for real production use
```

## Epic

```text
Epic 14
```

---

# 56. 2.0.0 — Qualification Matrix

Obligatoire :

```text
real PostgreSQL
two independent workers
multi-process
SIGTERM
SIGKILL
SIGSTOP
database outage
runtime outage
connector outage
ambiguous Effect
approval recovery
lease expiry
takeover
split-brain attempt
restore
PITR
migration cutover
coding remote Effect
load
security failure
```

---

# 57. 2.0.0 — Release Gates

```text
GATE-01 Public contracts
GATE-02 Domain invariants
GATE-03 Runtime adapters
GATE-04 Effect safety
GATE-05 Recovery
GATE-06 Coordination
GATE-07 Persistence
GATE-08 Governance
GATE-09 Audit
GATE-10 Security
GATE-11 Migration
GATE-12 Operations
GATE-13 Performance
GATE-14 Documentation
```

---

# 58. GATE-01 — Public Contracts

```text
[ ] stable surface explicitly listed
[ ] API snapshot test
[ ] error codes stable
[ ] serialization schemas stable
[ ] deprecation policy documented
```

---

# 59. GATE-02 — Domain Invariants

```text
[ ] Run != RuntimeInvocation
[ ] Session != Conversation
[ ] ToolCall != Effect
[ ] WAITING non-terminal
[ ] UNKNOWN != FAILED
[ ] Approval != Authorization
```

---

# 60. GATE-03 — Runtime Adapters

```text
[ ] Native L4 candidate
[ ] external general runtime >= L3
[ ] coding runtime >= L3
[ ] capability truthfulness tested
[ ] runtime loss recovery tested
```

---

# 61. GATE-04 — Effect Safety

```text
[ ] W1–W5 tested
[ ] no implicit replay of SUCCEEDED
[ ] UNKNOWN preserved
[ ] idempotency conflict tested
[ ] provider reconciliation tested
```

---

# 62. GATE-05 — Recovery

```text
[ ] deterministic RecoveryPlanner
[ ] approval-aware
[ ] effect-aware
[ ] lease-aware
[ ] runtime-aware
[ ] manual intervention supported
```

---

# 63. GATE-06 — Coordination

```text
[ ] lease acquire/renew/release
[ ] DB-time expiry
[ ] monotonic fencing
[ ] stale worker rejected
[ ] takeover tested
[ ] graceful shutdown not required for safety
```

---

# 64. GATE-07 — Persistence

```text
[ ] real PostgreSQL
[ ] normalized model
[ ] repository contracts
[ ] optimistic concurrency
[ ] outbox/inbox
[ ] uncertain commit handling
[ ] backup/restore qualification
```

---

# 65. GATE-08 — Governance

```text
[ ] durable approvals
[ ] immutable scope
[ ] expiry
[ ] revalidation
[ ] SoD baseline
[ ] authorization separated
```

---

# 66. GATE-09 — Audit

```text
[ ] append-oriented AuditStore
[ ] critical decisions reconstructible
[ ] payload minimization
[ ] audit independent from telemetry
```

---

# 67. GATE-10 — Security

```text
[ ] fail closed protected actions
[ ] tenant isolation
[ ] secret externalization
[ ] untrusted runtime/provider payload validation
[ ] command execution boundaries
[ ] dependency/supply-chain review
```

---

# 68. GATE-11 — Migration

```text
[ ] 1.6.x supported
[ ] dry-run
[ ] preflight
[ ] resumable migration
[ ] cutover
[ ] verification
[ ] forward-fix runbook
```

---

# 69. GATE-12 — Operations

```text
[ ] readiness
[ ] liveness
[ ] drain
[ ] kill switch
[ ] incident runbooks
[ ] dashboards
```

---

# 70. GATE-13 — Performance

Qualification minimale sur :

```text
lease renewals
Effect reservations
audit append
Outbox publishing
recovery scanning
runtime event throughput
```

---

# 71. GATE-14 — Documentation

```text
[ ] architecture docs
[ ] API docs
[ ] migration guide
[ ] deployment guide
[ ] operator runbooks
[ ] examples
[ ] ADR index
[ ] glossary
```

---

# 72. Stability Levels

Chaque public contract doit être classifié :

```text
EXPERIMENTAL
BETA
STABLE
DEPRECATED
```

---

# 73. Alpha policy

Pendant alpha :

```text
breaking internal/public experimental changes allowed
```

mais :

```text
core safety invariants should already be protected
```

---

# 74. Beta policy

Pendant beta :

```text
semantic model largely frozen
```

Breaking changes doivent être exceptionnels et documentés.

---

# 75. RC policy

À RC :

```text
no known intentional breaking change before stable
```

sauf bug/safety critique.

---

# 76. Stable policy

Après `2.0.0` :

```text
SemVer applies to STABLE contracts
```

---

# 77. Patch release strategy after 2.0

Exemples :

```text
2.0.1
2.0.2
```

Pour :

```text
bug fix
security fix
adapter compatibility fix
performance fix
```

sans casser les contrats stables.

---

# 78. Minor release strategy after 2.0

Exemples :

```text
2.1.0
2.2.0
```

Pour extensions compatibles.

---

# 79. Candidate 2.1.0

Thèmes possibles :

```text
additional runtime adapters
additional connectors
advanced approval policies
operator tooling
```

---

# 80. Candidate 2.2.0

Thèmes possibles :

```text
multi-agent coordination extensions
advanced runtime routing
richer policy integrations
```

uniquement si le core reste stable.

---

# 81. Candidate 2.3.0+

Possibilités :

```text
multi-region coordination
advanced tenancy isolation
adapter marketplace/plugin ecosystem
```

mais non nécessaires à V2 initiale.

---

# 82. Feature maturity pipeline

Toute nouvelle feature suit idéalement :

```text
EXPERIMENTAL
↓
BETA
↓
STABLE
```

---

# 83. Adapter maturity pipeline

```text
L0 Fake
↓
L1 Contract
↓
L2 Integration
↓
L3 Failure
↓
L4 Production Qualified
```

---

# 84. Official Adapter policy

Un adapter peut être livré avant L4.

Mais son niveau doit être visible.

---

# 85. Stable Adapter requirement

Pour être présenté comme production-ready :

```text
L4
```

ou un niveau explicitement équivalent.

---

# 86. Core vs Adapter release cadence

Le core et les adapters peuvent évoluer à des cadences différentes.

---

# 87. Separate adapter packages

À envisager :

```text
pyagentskit-langgraph
pyagentskit-codex
pyagentskit-github
```

si :

```text
dependency weight
release cadence
provider volatility
```

le justifient.

---

# 88. Core dependency policy

Le core doit rester léger.

Ne pas rendre obligatoires :

```text
psycopg
boto3
azure-storage
langgraph
OpenTelemetry SDK
GitHub SDK
```

si inutilisés.

---

# 89. Extras strategy

Exemples :

```text
pyagentskit[postgres]
pyagentskit[s3]
pyagentskit[azure]
pyagentskit[langgraph]
pyagentskit[codex]
pyagentskit[opentelemetry]
```

---

# 90. Release artifact policy

Chaque release publique doit fournir :

```text
wheel
sdist
checksums
release notes
compatibility notes
```

---

# 91. Reproducible build

Maintenir la discipline introduite en V1.6.

---

# 92. Release notes structure

Chaque release note doit contenir :

```text
Highlights
Added
Changed
Deprecated
Fixed
Security
Migration
Known limitations
Qualification evidence
```

---

# 93. Changelog policy

Changelog orienté utilisateur.

Ne pas l’utiliser comme dump de commits.

---

# 94. Breaking change policy

Une breaking change V2 stable nécessite :

```text
ADR
major version or explicitly experimental contract
migration path
release notes
```

---

# 95. Security release policy

Vulnérabilité critique :

```text
patch immediately
```

même si roadmap en cours.

---

# 96. Reliability regression policy

Toute régression pouvant :

```text
duplicate Effect
accept stale fencing
forge authority
lose approval
```

bloque une release.

---

# 97. Release blockers P0

```text
implicit Effect replay
UNKNOWN treated as failure
stale worker can mutate
cross-tenant authority leak
approval bypass
migration loses successful Effect
```

---

# 98. Release blockers P1

```text
missing operational visibility
incomplete connector reconciliation
runtime capability misreporting
migration non-resumable
```

---

# 99. Release blockers P2

```text
documentation polish
non-critical performance optimization
secondary adapters
```

---

# 100. Branching strategy

Recommandation :

```text
main always releasable
```

Utiliser des branches de feature courtes.

Éviter :

```text
long-lived v2 branch
```

---

# 101. Integration strategy

Chaque PR doit idéalement :

```text
compile
test
preserve V1
move one V2 capability forward
```

---

# 102. Feature branch naming

Exemples :

```text
feat/v2-domain-run
feat/runtime-adapter-native
feat/effect-reconciliation
feat/postgres-v2
```

---

# 103. PR sizing

Préférer :

```text
small architectural slices
```

plutôt que :

```text
massive repository reorganization
```

---

# 104. First implementation PRs

Ordre recommandé :

```text
PR-0001 Freeze V1 compatibility inventory
PR-0002 Introduce V2 package skeleton
PR-0003 Add dependency rules
PR-0101 Add V2 shared kernel
PR-0102 Add Execution domain
PR-0103 Add Effects domain
PR-0104 Add Governance domain
PR-0105 Add Coordination domain
PR-0201 Add AgentRuntimeAdapter
PR-0301 Add NativeRuntimeAdapter
```

---

# 105. First vertical slice

```text
CreateRun
→ NativeRuntimeAdapter
→ RuntimeInvocation
→ Memory repositories
→ Run completed
```

---

# 106. Second vertical slice

```text
Effect intent
→ EffectGateway
→ ambiguous outcome
→ UNKNOWN
→ RecoveryPlanner
→ reconciliation
```

---

# 107. Third vertical slice

```text
Approval required
→ WAITING
→ Approval decided
→ revalidation
→ ResumeRun
```

---

# 108. Fourth vertical slice

```text
Worker A
→ lease
→ crash
→ expiry
→ Worker B takeover
→ resume
```

---

# 109. Fifth vertical slice

```text
same flow
+
PostgreSQL V2
```

---

# 110. Sixth vertical slice

```text
external runtime
→ same V2 reliability semantics
```

---

# 111. Seventh vertical slice

```text
coding runtime
→ git push Effect
→ timeout
→ UNKNOWN
→ GitHub reconciliation
```

---

# 112. Why vertical slices

Ils réduisent le risque de construire :

```text
many abstractions
without proving composition
```

---

# 113. Documentation roadmap relationship

Les docs 00→48 doivent servir :

```text
requirements
→ domain
→ architecture
→ implementation
→ migration
→ qualification
```

---

# 114. Documentation freeze levels

Pendant alpha :

```text
living architecture
```

À beta :

```text
semantic docs freeze candidate
```

À RC :

```text
public docs freeze candidate
```

---

# 115. ADR roadmap

Avant chaque milestone, les ADR correspondants doivent être acceptés.

---

# 116. ADR gate a1

Minimum :

```text
Product Boundary
DDD/Hexagonal
Dependency Direction
Bounded Contexts
Run vs RuntimeInvocation
Session vs Conversation
Effect vs ToolCall
Effect state machine
```

---

# 117. ADR gate a2

```text
AgentRuntimeAdapter
NativeRuntimeAdapter
Runtime capabilities
```

---

# 118. ADR gate a3

```text
Reconciliation
RecoveryPlanner
Effect idempotency
```

---

# 119. ADR gate a4

```text
Repository vs Store
UnitOfWork
PostgreSQL normalized model
Lease/Fencing physical model
```

---

# 120. ADR gate b1

```text
Approval V2
AuthN/AuthZ/Approval
Audit
Outbox/Inbox
```

---

# 121. ADR gate b2

```text
first external runtime
first coding runtime
Connector model
GitHub connector
```

---

# 122. ADR gate RC

```text
public API
migration
deprecation
packaging
```

---

# 123. Testing pyramid

```text
unit
contract
integration
multi-process
failure injection
production qualification
```

---

# 124. Unit test role

Prouver :

```text
domain invariants
pure planners
mappers
policy decisions
```

---

# 125. Contract test role

Prouver :

```text
all implementations respect same port
```

---

# 126. Integration test role

Prouver :

```text
real adapter works
```

---

# 127. Multi-process role

Prouver :

```text
lease
fencing
takeover
worker safety
```

---

# 128. Failure injection role

Prouver :

```text
crash windows
unknown outcomes
recovery behavior
```

---

# 129. Production qualification role

Prouver que l’ensemble tient :

```text
under realistic dependencies and failure conditions
```

---

# 130. Coverage policy

Conserver au minimum :

```text
branch coverage >= 90%
```

si ce seuil reste le standard projet.

---

# 131. Coverage caveat

Coverage seule ne prouve pas la sûreté.

---

# 132. CI pipeline target

```text
lint
typecheck
architecture
unit
contracts
integration
multi-process
migration
security
package
```

Les jobs coûteux peuvent être répartis entre PR et nightly/release.

---

# 133. PR gates

Minimum quotidien :

```text
lint
mypy strict
architecture rules
unit
contract tests
V1 compatibility
```

---

# 134. Nightly gates

```text
PostgreSQL
multi-process
external adapter integration
failure scenarios
migration
```

---

# 135. Release gates

Tout le matrix L4 pertinent.

---

# 136. Toolchain policy

Maintenir :

```text
Ruff
strict mypy
pytest
branch coverage
reproducible package
```

et ajouter :

```text
import-linter or equivalent
schema migration tests
contract test suites
```

---

# 137. Performance qualification

Avant stable, établir un baseline pour :

```text
Run creation
Effect reservation
Lease acquire/renew
Audit append
Outbox throughput
Recovery scan
```

---

# 138. Capacity guidance

Documenter :

```text
lease TTL
heartbeat interval
renewal interval
worker concurrency
DB pool sizing
```

dans les docs opérationnels.

---

# 139. Observability release gates

Chaque capability majeure doit exposer :

```text
metrics
traces
structured logs
audit when relevant
```

---

# 140. Runbook release gates

Pas de stable sans runbooks pour :

```text
PostgreSQL unavailable
unknown Effect
stale worker
lease conflict
approval stuck
runtime outage
migration failure
restore/PITR
```

---

# 141. Compatibility strategy

Pendant pré-release :

```text
V1 stable
V2 evolving
```

Après V2 stable :

```text
V1 compatibility policy explicitly time-bounded or maintained
```

---

# 142. V1 deprecation start

Seulement lorsque :

```text
V2 replacement exists
migration works
docs exist
qualification green
```

---

# 143. V1 deprecation phases

```text
D0 supported
D1 discouraged
D2 deprecated
D3 compatibility-only
D4 removed in future major
```

---

# 144. No forced V1 removal at 2.0

La sortie de V2 ne nécessite pas nécessairement de supprimer immédiatement le Native/V1 surface.

---

# 145. Long-term Native Runtime

Le Native Runtime peut rester une capability officielle :

```text
V1 Runner internals
behind
NativeRuntimeAdapter
```

---

# 146. Product roadmap principles

Ne pas ajouter une feature parce qu’un concurrent l’a.

Ajouter si elle améliore :

```text
reliability
runtime neutrality
governance
operability
integration
```

---

# 147. Scope control

PyAgentsKit ne doit pas devenir :

```text
generic scheduler
workflow engine
IAM
message broker
vector DB
observability backend
Git engine
cloud platform
```

---

# 148. Build / Buy / Integrate roadmap use

Avant tout nouveau chantier :

```text
BUILD?
BUY/USE?
INTEGRATE?
```

---

# 149. Build only differentiated semantics

Construire :

```text
Effect safety
Recovery
Approval semantics
Lease/Fencing semantics
Runtime abstraction
```

---

# 150. Integrate commodities

Intégrer :

```text
PostgreSQL
S3
OIDC
OpenTelemetry
runtime frameworks
GitHub
```

---

# 151. Ecosystem strategy

V2 stable doit fournir :

```text
clear adapter contracts
qualification levels
plugin path
examples
```

afin que l’écosystème puisse croître sans contaminer le core.

---

# 152. Plugin stability

Un plugin tiers ne doit pas être considéré production-safe uniquement parce qu’il s’importe.

Il doit publier :

```text
compatibility
capabilities
qualification level
known limitations
```

---

# 153. Public API evolution

Après stable :

```text
additive first
deprecate before remove
document semantic impact
```

---

# 154. Public event evolution

Événements publics versionnés.

---

# 155. DB migration evolution

Toujours :

```text
forward compatible deployment plan
```

---

# 156. Migration support window

À définir avant V2 GA.

Recommandation initiale :

```text
latest 1.6.x → 2.x direct
older versions → upgrade to latest 1.6.x first
```

---

# 157. Security support window

Les fixes sécurité critiques peuvent nécessiter support sur :

```text
current V2 minor
+
supported V1 maintenance line
```

selon politique publiée.

---

# 158. Known limitations policy

Chaque pré-release doit publier ses limitations.

---

# 159. Alpha limitations example

```text
not for production
schema unstable
adapter ecosystem incomplete
migration incomplete
```

---

# 160. Beta limitations example

```text
public API may still change
limited adapter L4 qualification
migration still being qualified
```

---

# 161. RC limitations

Uniquement problèmes connus non bloquants.

---

# 162. Stable definition

`2.0.0` signifie :

```text
core semantics stable
public API stable
migration supported
production gates passed
runbooks available
```

Pas :

```text
every imaginable adapter implemented
```

---

# 163. Success Metrics — Architecture

```text
0 forbidden dependency cycles
0 provider SDK leakage into core
100% P0 ports contract-tested
```

---

# 164. Success Metrics — Reliability

```text
0 implicit replay in qualification
0 stale fencing acceptance
0 forged Approval
0 silent UNKNOWN→FAILED transition
```

---

# 165. Success Metrics — Runtime Neutrality

Minimum :

```text
Native + external general runtime + coding runtime
```

sur même Application semantics.

---

# 166. Success Metrics — Migration

```text
real V1 dataset migrated
restartable
idempotent
verified
```

---

# 167. Success Metrics — Operations

```text
readiness
drain
kill switch
audit
incident runbooks
```

fonctionnels.

---

# 168. Success Metrics — Developer Experience

```text
simple local profile
clear installation extras
runtime adapter example
connector example
migration guide
```

---

# 169. Release readiness board

Chaque milestone peut être suivi avec colonnes :

```text
ADR
Implementation
Unit Tests
Contract Tests
Integration
Failure Tests
Docs
Qualification
```

---

# 170. Milestone status

États proposés :

```text
NOT_STARTED
IN_PROGRESS
IMPLEMENTED
QUALIFIED
RELEASED
```

---

# 171. Definition — Implemented

Code fonctionnel avec tests de base.

---

# 172. Definition — Qualified

Le composant a passé les tests correspondant à son niveau de risque.

---

# 173. Definition — Released

Intégré à une release publique avec docs et compatibility statement.

---

# 174. Roadmap dependency graph

```text
Domain
  ↓
Runtime Abstraction
  ↓
Effects
  ↓
Recovery
  ↓
Persistence
  ├──────► Governance
  └──────► Audit
              │
              ▼
        External Ecosystem
              │
              ▼
           Public API
              │
              ▼
           Migration
              │
              ▼
        Qualification
```

---

# 175. Parallel work

Après stabilisation des ports/domain :

```text
PostgreSQL
Governance
Audit
```

peuvent partiellement avancer en parallèle.

---

# 176. Work that should not start too early

Éviter de lancer trop tôt :

```text
many connectors
many runtime adapters
HTTP API polish
plugin marketplace
multi-region
```

---

# 177. Why

Parce qu’ils dépendraient de contrats encore mouvants.

---

# 178. Critical Path

Le chemin critique est :

```text
Domain
→ Runtime Adapter
→ Native Runtime
→ Effects
→ Recovery
→ Persistence
→ Governance
→ Migration
→ Qualification
```

---

# 179. Optional Parallel Path

```text
Artifacts
Telemetry
Docs
Developer tooling
```

peuvent progresser en parallèle si les frontières restent respectées.

---

# 180. Release decision authority

Une release majeure doit être décidée sur :

```text
evidence
```

pas sur :

```text
feature checklist alone
```

---

# 181. Evidence package

Pour chaque release candidate :

```text
test report
coverage report
compatibility report
migration report
adapter qualification report
known limitations
```

---

# 182. Release candidate freeze

À `rc1` :

```text
feature freeze
```

sauf corrections nécessaires.

---

# 183. RC iteration

Si problème :

```text
rc2
rc3
...
```

jusqu’à gates verts.

---

# 184. Stable tag

Tag stable uniquement lorsque tous les P0 blockers sont fermés.

---

# 185. Post-GA stabilization

Après `2.0.0` :

```text
2.0.x stabilization window
```

avant d’accélérer les features 2.1.

---

# 186. No immediate feature flood

Les premières semaines post-GA doivent privilégier :

```text
bugs
performance
docs
operational feedback
```

---

# 187. Compatibility telemetry

Observer :

```text
deprecated API usage
migration failures
adapter failures
```

si product telemetry le permet et respecte privacy.

---

# 188. Documentation after GA

Mettre en avant :

```text
Quickstart
Concepts
Architecture
Operations
Migration
Adapters
```

---

# 189. Reference examples after GA

Minimum :

```text
Native local
PostgreSQL distributed
Approval flow
Effect reconciliation
External runtime
Coding agent + GitHub
Migration V1→V2
```

---

# 190. Release ownership

Chaque milestone doit avoir un owner technique explicite.

---

# 191. Architecture review cadence

Avant chaque pre-release majeure :

```text
architecture review
```

avec revue des ADR nouveaux/superseded.

---

# 192. Threat model review cadence

Au minimum avant :

```text
b1
b2
rc1
2.0.0
```

---

# 193. Migration review cadence

Avant chaque changement de schéma V2 significatif.

---

# 194. External adapter review cadence

À chaque montée de qualification :

```text
L1 → L2 → L3 → L4
```

---

# 195. Performance review cadence

Avant RC et stable.

---

# 196. Release rollback philosophy

Avant cutover/migration :

```text
rollback possible
```

Après external Effects / V2 authoritative writes :

```text
forward-fix generally preferred
```

---

# 197. Artifact retention

Conserver les evidence packages des releases importantes.

---

# 198. Version support documentation

Publier une matrice :

```text
Core version
Python version
PostgreSQL versions
Adapter versions
Provider versions
```

---

# 199. Python support

Conserver `>=3.11` tant qu’aucune décision ADR ne modifie cette base.

---

# 200. Python version deprecation

Toute suppression d’une version Python doit être annoncée dans une minor précédente si possible.

---

# 201. Database support

PostgreSQL versions supportées doivent être explicites.

---

# 202. Adapter provider support

Chaque adapter doit déclarer :

```text
tested provider version range
```

---

# 203. Release risk categories

```text
R0 documentation only
R1 internal refactor
R2 additive feature
R3 persistence/runtime change
R4 safety-critical semantic change
```

---

# 204. R4 requirements

Nécessite :

```text
ADR
failure tests
migration impact review
security/reliability review
```

---

# 205. Architecture debt

Aucune release stable ne doit accumuler silencieusement des exceptions aux dependency rules.

---

# 206. Architecture debt register

Créer/maintenir :

```text
docs/architecture/ARCHITECTURE_DEBT.md
```

si des exceptions temporaires apparaissent.

---

# 207. Deprecation debt

Suivre séparément :

```text
deprecated surface
planned removal
replacement status
```

---

# 208. Roadmap anti-pattern — calendar-driven release

Ne pas publier un stable uniquement parce qu’une date a été annoncée.

---

# 209. Roadmap anti-pattern — feature count

Plus de features ne signifie pas meilleure readiness.

---

# 210. Roadmap anti-pattern — adapter explosion

Ne pas implémenter dix runtimes avant de qualifier deux.

---

# 211. Roadmap anti-pattern — infra-first

Ne pas laisser :

```text
PostgreSQL schema
```

dicter le Domain.

---

# 212. Roadmap anti-pattern — API-first

Ne pas figer une belle API avant d’avoir stabilisé les semantics.

---

# 213. Roadmap anti-pattern — production claims from mocks

Interdit.

---

# 214. Roadmap anti-pattern — silent V1 break

Tout écart V1 doit être détecté par CI.

---

# 215. Roadmap anti-pattern — semantic overloading

Ne pas réutiliser V1 classes pour des significations V2 différentes.

---

# 216. Roadmap anti-pattern — every experimental adapter in core

Le core doit rester compact.

---

# 217. Future roadmap beyond 2.0

Après stabilisation, axes possibles :

```text
more runtimes
more connectors
advanced governance
multi-agent reliability
multi-region
policy ecosystem
operator tooling
```

---

# 218. 2.1 candidate theme — Ecosystem Expansion

Possibilités :

```text
LangGraph/PydanticAI/OpenAI Agents trio
GitLab
Slack
Jira
Azure DevOps
```

---

# 219. 2.2 candidate theme — Advanced Governance

Possibilités :

```text
multi-approval
quorum
delegation
advanced SoD
policy engine integrations
```

---

# 220. 2.3 candidate theme — Multi-Agent Reliability

Seulement après que mono-agent/reliability core soit stable.

Concepts éventuels :

```text
parent/child Runs
agent-to-agent communication
cross-run effects
coordination
```

---

# 221. 2.4 candidate theme — Multi-Region Operations

Sujet complexe :

```text
global fencing
latency
regional failover
partition handling
```

À ne pas anticiper dans V2 initiale.

---

# 222. 3.0 trigger

Un futur 3.0 serait justifié par un changement de contrat fondamental, pas par une simple accumulation de features.

---

# 223. Possible 3.0 triggers

Exemples :

```text
new execution authority model
fundamental public API redesign
major multi-region consistency model
major multi-agent domain shift
```

---

# 224. Roadmap governance

Cette roadmap doit être revue :

```text
at every major milestone
```

et mise à jour lorsque :

```text
scope changes
risk discovered
ADR superseded
qualification reveals new work
```

---

# 225. Roadmap change rule

Une modification du chemin critique doit être documentée.

---

# 226. Release checklist template

```text
[ ] Scope frozen
[ ] ADRs accepted
[ ] Code complete
[ ] Unit green
[ ] Contracts green
[ ] Integration green
[ ] Architecture green
[ ] Migration green if relevant
[ ] Failure tests green
[ ] Security review complete
[ ] Docs complete
[ ] Release notes complete
[ ] Known limitations published
```

---

# 227. Release acceptance matrix

| Release | Primary Goal | Key Exit Proof |
|---|---|---|
| 2.0.0a1 | Domain semantics | Contexts/invariants stable |
| 2.0.0a2 | Runtime neutrality | NativeRuntimeAdapter works |
| 2.0.0a3 | Effect safety/recovery | UNKNOWN/reconciliation proven |
| 2.0.0a4 | Persistence V2 | PostgreSQL normalized contracts green |
| 2.0.0b1 | Trust/Audit | fail-closed governance + durable audit |
| 2.0.0b2 | Ecosystem | external runtime + coding runtime + connector |
| 2.0.0rc1 | Public/migration | API candidate + V1 migration |
| 2.0.0 | Production | full qualification gates |

---

# 228. Core invariants across every release

Ces invariants ne doivent jamais régresser :

```text
REL-INV-01
No implicit replay of a confirmed successful critical Effect.

REL-INV-02
UNKNOWN is never silently treated as FAILED.

REL-INV-03
A stale worker cannot gain valid authority.

REL-INV-04
Approval cannot be fabricated from runtime output or free text.

REL-INV-05
Tenant boundaries remain enforced.

REL-INV-06
A client timeout does not redefine external reality.

REL-INV-07
Runtime-specific objects do not become the core model.

REL-INV-08
V1 compatibility is preserved until explicitly deprecated.

REL-INV-09
Recovery uses durable authoritative state.

REL-INV-10
Manual intervention remains acceptable when safety cannot be proven.
```

---

# 229. Definition of Ready — milestone

Un milestone peut démarrer lorsque :

```text
upstream contracts stable enough
ADRs identified
scope bounded
risks known
testing strategy identified
```

---

# 230. Definition of Done — milestone

Un milestone est terminé lorsque :

```text
scope implemented
tests green
docs updated
architecture rules preserved
compatibility assessed
failure semantics covered
evidence archived
```

---

# 231. Definition of Ready — stable release

```text
RC deployed/qualified
no P0 blocker
migration proven
runbooks ready
security review complete
performance baseline acceptable
```

---

# 232. Definition of Done — V2.0.0

PyAgentsKit 2.0.0 est terminé lorsque :

1. V2 Domain est stable ;
2. AgentRuntimeAdapter est stable ;
3. Native Runtime est un adapter ;
4. au moins un runtime externe est qualifié ;
5. au moins un coding runtime est qualifié ;
6. Effect V2 est générique ;
7. Reconciliation est first-class ;
8. RecoveryPlanner est déterministe ;
9. PostgreSQL V2 est normalisé ;
10. Lease/Fencing sont qualifiés multi-processus ;
11. Governance distingue AuthN/AuthZ/Approval ;
12. Audit est durable ;
13. Outbox/Inbox sont opérationnels ;
14. API V2 est stable ;
15. migration 1.6.x→2.0 fonctionne ;
16. W1–W5 sont couverts ;
17. restore/PITR possède un safety gate ;
18. runbooks critiques existent ;
19. aucune régression V1 non annoncée n’existe ;
20. tous les P0 release gates sont verts.

---

# 233. Executive Summary

La stratégie de release V2 est volontairement progressive :

```text
SEMANTICS
    ↓
RUNTIME ABSTRACTION
    ↓
EFFECT SAFETY
    ↓
RECOVERY
    ↓
PERSISTENCE
    ↓
GOVERNANCE
    ↓
ECOSYSTEM
    ↓
PUBLIC API
    ↓
MIGRATION
    ↓
PRODUCTION QUALIFICATION
```

La roadmap ne cherche pas à maximiser le nombre de features.

Elle cherche à maximiser la confiance progressivement.

Le principe fondamental est :

> **Une release PyAgentsKit n’est pas prête lorsqu’elle possède toutes ses classes ; elle est prête lorsque ses garanties peuvent être démontrées sous concurrence, panne, reprise, migration et intégration réelle.**
