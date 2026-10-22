# PyAgentsKit — Gap Closure & V2 Implementation Plan

**Document :** `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Plan directeur d’implémentation V1.6 → V2  
**Projet :** PyAgentsKit  

**Sources de conception :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../architecture/08_PYAGENTSKIT_ERD.md`
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
- `../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../strategy/PYAGENTSKIT_EXISTING_VS_TARGET_GAP_ANALYSIS_2026-10-21.md`
- `../architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`

---

# 1. Objet

Ce document transforme la cible PyAgentsKit V2 en **plan d’exécution concret**.

Il répond à quatre questions :

```text
1. Qu’est-ce qui doit être conservé ?
2. Qu’est-ce qui doit être refactoré ?
3. Qu’est-ce qui doit être créé ?
4. Dans quel ordre faut-il le faire sans casser la V1.6 ?
```

Le principe directeur est :

> **La V2 doit émerger par convergence progressive de la V1.6, et non par réécriture brutale.**

---

# 2. Point de départ

PyAgentsKit 1.6.0 dispose déjà de fondations solides :

```text
Runner
DurableRunner
Effects
UNKNOWN effect handling
Approvals
Sessions / Memory
Artifacts
Blob stores
Lease
Fencing
DistributedDurableRunner
DistributedWorkerController
PostgreSQL stores
OpenTelemetry
Failure tests
SIGTERM / SIGKILL / SIGSTOP qualification
```

La V2 élève le niveau d’abstraction vers :

```text
Agent Reliability Layer
```

avec :

```text
DDD
Hexagonal Architecture
Ports & Adapters
framework-neutral runtime integration
runtime-independent durable execution
generalized Effects
reconciliation
normalized PostgreSQL
connectors
coding agents
public application API
```

---

# 3. Nature du gap

Le gap n’est pas principalement technique.

Il est architectural.

## V1.6

```text
PyAgentsKit owns the agent loop
↓
Model
↓
ToolCall
↓
ToolExecutor
```

## V2

```text
PyAgentsKit owns reliability semantics
↓
AgentRuntimeAdapter
↓
Native Runner / LangGraph / PydanticAI / Codex / Claude Code / ...
```

Le cœur du chantier est donc :

```text
Runtime ownership
→
Reliability orchestration
```

---

# 4. Stratégie globale

La stratégie recommandée est un :

```text
STRANGLER MIGRATION
```

La V1 reste fonctionnelle pendant que la V2 se construit à côté.

```text
V1.6
 │
 ├── remains stable
 │
 └── wrapped behind V2 ports
        │
        ▼
V2 Reliability Core
```

---

# 5. Règles non négociables

Pendant toute la migration :

```text
RULE-01
No V1 public contract break in 1.6.x.

RULE-02
New V2 semantics must not be hidden in V1 types.

RULE-03
No big-bang repository rewrite.

RULE-04
Domain first, infrastructure second.

RULE-05
No provider/runtime specific type in Domain.

RULE-06
No PostgreSQL-specific object in Domain/Application.

RULE-07
Every new adapter must have contract tests.

RULE-08
Every safety-critical migration must preserve existing qualification tests.

RULE-09
Effects must never be implicitly replayed.

RULE-10
UNKNOWN must never silently become FAILED.
```

---

# 6. Architecture cible de migration

```text
                         V2 API
                           │
                           ▼
                    Application Layer
                           │
                           ▼
                        Domain
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
 Runtime Adapter      Persistence       Connector
      Ports              Ports            Ports
          │                │                │
          ▼                ▼                ▼
 Native V1 Runner      PostgreSQL       GitHub/etc.
 LangGraph             SQLite
 Codex                  Memory
```

---

# 7. Macro-roadmap

Le programme V2 est découpé en 15 Epics :

```text
Epic 0  — Freeze V1 compatibility boundary
Epic 1  — Domain Core V2
Epic 2  — Agent Runtime Adapter
Epic 3  — Native Runtime Adapter
Epic 4  — Effect & Reconciliation V2
Epic 5  — RecoveryPlanner V2
Epic 6  — Persistence Ports V2
Epic 7  — PostgreSQL Normalized Model
Epic 8  — Governance & Security
Epic 9  — Audit / Outbox / Inbox
Epic 10 — Coding Agent Integration
Epic 11 — External Connectors
Epic 12 — Public API V2
Epic 13 — V1 → V2 Migration
Epic 14 — Production Qualification
```

---

# 8. Dependency graph

```text
Epic 0
  ↓
Epic 1
  ↓
Epic 2
  ↓
Epic 3
  ↓
Epic 4
  ↓
Epic 5
  ↓
Epic 6
  ↓
Epic 7
  ├───────────────┐
  ↓               ↓
Epic 8          Epic 9
  │               │
  └───────┬───────┘
          ↓
       Epic 10
          ↓
       Epic 11
          ↓
       Epic 12
          ↓
       Epic 13
          ↓
       Epic 14
```

Certaines branches pourront être parallélisées après stabilisation des contrats.

---

# 9. Epic 0 — Freeze V1 Compatibility Boundary

## Objectif

Figer définitivement ce qui appartient à la V1 et définir la frontière avec la V2.

## Livrables

```text
V1 compatibility manifest
V1 public import inventory
V1 serialization inventory
V1 status inventory
V1 provider signatures
V1 migration boundary ADR
```

## PRs

```text
PR-0001 — Add V1 compatibility inventory
PR-0002 — Add import architecture rules
PR-0003 — Add V2 namespace skeleton
PR-0004 — Add compatibility CI gate
```

## Fichiers cibles

```text
src/pyagentskit/compat/v1/
tests/compatibility/v1/
docs/migration/
```

## Acceptance Criteria

```text
AC-0.1
All current V1 tests remain green.

AC-0.2
All 155 root exports remain unchanged in 1.6.x.

AC-0.3
V2 packages can be imported without modifying V1 behavior.

AC-0.4
CI rejects illegal imports from V2 domain to adapters.

AC-0.5
A V1 compatibility ADR exists.
```

---

# 10. Epic 1 — Domain Core V2

## Objectif

Créer le langage métier canonique de la V2 indépendamment des technologies.

## Bounded Contexts

```text
execution
effects
governance
coordination
conversations
runtime_integration
artifacts
audit
```

## Livrables principaux

### Execution

```text
Run
RunState
Checkpoint
RuntimeInvocation
RuntimeInvocationStatus
```

### Effects

```text
Effect
EffectStatus
EffectRiskLevel
IdempotencyKey
InputFingerprint
ExternalReference
```

### Governance

```text
Approval
ApprovalStatus
ApprovalScope
Principal
PolicyDecision
```

### Coordination

```text
Lease
FencingToken
OwnershipContext
ResourceIdentity
Worker
```

### Conversations

```text
Session
Conversation
Message
Actor
Participant
MemoryEntry
```

### Runtime Integration

```text
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeStatus
RuntimeEvent
```

## PRs

```text
PR-0101 — Shared kernel and typed IDs
PR-0102 — Execution domain
PR-0103 — Effects domain
PR-0104 — Governance domain
PR-0105 — Coordination domain
PR-0106 — Conversations domain
PR-0107 — Runtime integration domain
PR-0108 — Artifact domain
PR-0109 — Audit domain
```

## Acceptance Criteria

```text
AC-1.1
Domain imports no adapters.

AC-1.2
Session != Conversation.

AC-1.3
Run != RuntimeInvocation.

AC-1.4
ToolCall != Effect.

AC-1.5
WAITING is non-terminal.

AC-1.6
UNKNOWN exists only as Effect ambiguity, not generic failure.

AC-1.7
Domain entities have no ORM/runtime-provider fields.

AC-1.8
Each aggregate has explicit invariants and tests.
```

---

# 11. Epic 2 — Agent Runtime Adapter

## Objectif

Créer le port qui rend PyAgentsKit réellement framework-neutral.

## Port

```text
AgentRuntimeAdapter
```

## Contrat minimum

```text
start
resume
cancel
inspect
events
checkpoint
close
```

## Capabilities

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

## Livrables

```text
AgentRuntimeAdapter Protocol
RuntimeAdapterRegistry
RuntimeCapability negotiation
RuntimeHandle
RuntimeError taxonomy
RuntimeAdapterContract test suite
```

## PRs

```text
PR-0201 — AgentRuntimeAdapter port
PR-0202 — Runtime capability model
PR-0203 — Runtime registry
PR-0204 — Runtime adapter contract tests
PR-0205 — FakeRuntimeAdapter for testing
```

## Acceptance Criteria

```text
AC-2.1
No runtime-specific conditional exists in application core.

AC-2.2
A fake runtime passes the full adapter contract suite.

AC-2.3
Capabilities are explicit.

AC-2.4
RuntimeHandle remains opaque.

AC-2.5
Adapter errors are normalized.
```

---

# 12. Epic 3 — Native Runtime Adapter

## Objectif

Encapsuler le `Runner` V1 derrière `AgentRuntimeAdapter`.

## Principe

```text
Current V1 Runner
↓
NativeRuntimeAdapter
↓
AgentRuntimeAdapter
```

## Ce qui reste V1

```text
Model
ToolRegistry
ToolExecutor
provider adapters
guardrails
context policy
```

## Livrables

```text
NativeRuntimeAdapter
RunnerBridge
NativeRuntimeEventMapper
NativeCheckpointMapper
V1 RunResult → RuntimeStatus mapping
```

## PRs

```text
PR-0301 — Native runtime bridge
PR-0302 — Native runtime lifecycle mapping
PR-0303 — Native events mapping
PR-0304 — Native checkpoint mapping
PR-0305 — Native adapter compatibility tests
```

## Acceptance Criteria

```text
AC-3.1
All V1 Runner examples still work.

AC-3.2
The same Runner can be driven through AgentRuntimeAdapter.

AC-3.3
No behavior difference for V1 callers.

AC-3.4
V2 can start, inspect and resume a Native runtime invocation.

AC-3.5
V1 tool approval remains compatible during transition.
```

---

# 13. Epic 4 — Effect & Reconciliation V2

## Objectif

Généraliser la logique actuelle d’Effect au-delà du ToolCall.

## Nouveau modèle

```text
Effect
├── intent
├── risk
├── idempotency
├── fingerprint
├── status
├── external_reference
└── reconciliation
```

## States

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

## Livrables

```text
EffectRepository port
EffectExecutionService
ReconciliationCase
ReconciliationRepository
ReconciliationPort
ManualResolution
EffectGateway
```

## PRs

```text
PR-0401 — Effect V2 lifecycle
PR-0402 — Effect repository contract
PR-0403 — ExternalReference
PR-0404 — ReconciliationCase
PR-0405 — ReconciliationPort
PR-0406 — EffectGateway
PR-0407 — V1 EffectRecord compatibility bridge
```

## Acceptance Criteria

```text
AC-4.1
Effect no longer embeds mandatory ToolCall semantics.

AC-4.2
SUCCEEDED effects cannot be re-executed implicitly.

AC-4.3
UNKNOWN never transitions to FAILED without evidence.

AC-4.4
Reconciliation can be automatic or manual.

AC-4.5
Manual resolution records evidence and actor.

AC-4.6
V1 effect journals can be interpreted through compatibility mapping.
```

---

# 14. Epic 5 — RecoveryPlanner V2

## Objectif

Transformer la reprise V1 en moteur de décision explicite.

## Objets

```text
RecoveryPlan
RecoveryBlocker
NextAction
RecoveryPolicy
```

## NextAction

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

## Livrables

```text
RecoveryPlanner
RecoverRun use case
Recovery decision audit
Recovery policy versioning
```

## PRs

```text
PR-0501 — RecoveryPlan V2
PR-0502 — RecoveryPlanner
PR-0503 — Effect-aware recovery
PR-0504 — Approval-aware recovery
PR-0505 — Runtime-aware recovery
PR-0506 — Lease-aware recovery
PR-0507 — Recovery observability
```

## Acceptance Criteria

```text
AC-5.1
Recovery is deterministic for equivalent durable state.

AC-5.2
Runtime replay never occurs before Effect inspection.

AC-5.3
Approval is revalidated after takeover.

AC-5.4
Manual intervention is an explicit safe outcome.

AC-5.5
RecoveryPlan is testable without concrete infrastructure.
```

---

# 15. Epic 6 — Persistence Ports V2

## Objectif

Définir des persistence contracts cohérents avec les aggregates V2.

## Repository Ports

```text
RunRepository
SessionRepository
ConversationRepository
MessageRepository
EffectRepository
ReconciliationRepository
ApprovalRepository
LeaseRepository
WorkerRepository
```

## Store Ports

```text
ArtifactStore
BlobStore
AuditStore
OutboxStore
InboxStore
```

## Unit of Work

```text
UnitOfWork
```

## PRs

```text
PR-0601 — Repository contracts
PR-0602 — Store contracts
PR-0603 — UnitOfWork port
PR-0604 — Memory V2 repositories
PR-0605 — Repository contract test suite
PR-0606 — Store contract test suite
```

## Acceptance Criteria

```text
AC-6.1
Repositories manipulate domain objects, not ORM models.

AC-6.2
Stores remain technical where appropriate.

AC-6.3
UnitOfWork exposes no DB-specific connection.

AC-6.4
Memory adapters pass all contracts.

AC-6.5
Application services depend only on ports.
```

---

# 16. Epic 7 — PostgreSQL Normalized Model

## Objectif

Implémenter le modèle relationnel cible du document 24.

## Tables P0

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
audit_events
outbox_events
inbox_events
```

## Livrables

```text
schema migrations
Postgres UnitOfWork
repositories
indexes
constraints
migration tooling
V1 data migration path
```

## PRs

```text
PR-0701 — PostgreSQL schema bootstrap
PR-0702 — Run/Session repositories
PR-0703 — Conversation/Message repositories
PR-0704 — Effect/Reconciliation repositories
PR-0705 — Approval repository
PR-0706 — Lease/Worker repositories
PR-0707 — RuntimeInvocation repositories
PR-0708 — Audit/Outbox/Inbox
PR-0709 — Migration tooling V1 → V2
PR-0710 — Query/index qualification
```

## Acceptance Criteria

```text
AC-7.1
Critical relationships use FK.

AC-7.2
Effect idempotency uses unique constraints.

AC-7.3
One active authoritative lease per resource.

AC-7.4
Fencing is monotonic.

AC-7.5
Authoritative safety reads use primary.

AC-7.6
PostgreSQL passes all repository contract tests.

AC-7.7
Migration from a V1 dataset is repeatable and verified.
```

---

# 17. Epic 8 — Governance & Security

## Objectif

Passer de security features dispersées à un véritable trust model.

## Concepts

```text
Principal
SecurityContext
AuthorizationPort
PolicyEvaluator
SecretReference
ApprovalScope
ApprovalValidity
SegregationOfDuties
```

## Livrables

```text
AuthorizationPort
PolicyEvaluator
IdentityProviderPort
SecurityContext
Approval revalidation
SoD support
multi-approval foundations
```

## PRs

```text
PR-0801 — Principal & SecurityContext
PR-0802 — AuthorizationPort
PR-0803 — PolicyEvaluator
PR-0804 — SecretReference
PR-0805 — Approval V2 scope
PR-0806 — Approval revalidation
PR-0807 — SoD rules
PR-0808 — High-assurance policy profile
```

## Acceptance Criteria

```text
AC-8.1
Authentication != Authorization != Approval.

AC-8.2
Runtime output cannot grant authority.

AC-8.3
Protected actions fail closed when required authority is unavailable.

AC-8.4
Approval scope is immutable and fingerprint-bound.

AC-8.5
Tenant isolation is enforced.
```

---

# 18. Epic 9 — Audit / Outbox / Inbox

## Objectif

Séparer clairement observability, domain events, integration events et audit.

## Livrables

```text
AuditEvent
AuditStore
DomainEventPublisher
OutboxStore
InboxStore
integration event envelope
event deduplication
```

## PRs

```text
PR-0901 — Audit domain
PR-0902 — AuditStore port
PR-0903 — PostgreSQL AuditStore
PR-0904 — OutboxStore
PR-0905 — InboxStore
PR-0906 — DomainEvent → Outbox projection
PR-0907 — webhook/event dedup
PR-0908 — audit query/timeline views
```

## Acceptance Criteria

```text
AC-9.1
AuditEvent != DomainEvent != RuntimeEvent != Log.

AC-9.2
Audit is append-oriented.

AC-9.3
Outbox publication survives process crash.

AC-9.4
Inbox deduplicates duplicate external delivery.

AC-9.5
Audit can reconstruct a critical decision timeline.
```

---

# 19. Epic 10 — Coding Agent Integration

## Objectif

Ajouter le premier grand runtime family externe spécialisé.

## Architecture

```text
adapters/outbound/runtimes/coding/
├── common/
├── codex/
├── claude_code/
└── opencode/
```

## Common concepts

```text
Workspace
RepositoryReference
BranchReference
CommitReference
PatchArtifact
CommandExecution
BuildEvidence
TestEvidence
```

## Protected Effects

```text
git push
PR creation
PR merge
package publish
deployment
terraform apply
```

## PRs

```text
PR-1001 — Coding workspace abstraction
PR-1002 — Command execution boundary
PR-1003 — Git domain mappings
PR-1004 — Coding effect policies
PR-1005 — Codex adapter
PR-1006 — Claude Code adapter
PR-1007 — OpenCode adapter
PR-1008 — Coding recovery tests
```

## Acceptance Criteria

```text
AC-10.1
Local file edits are not confused with remote Effects.

AC-10.2
git push timeout becomes UNKNOWN when ambiguous.

AC-10.3
Approved SHA drift invalidates old approval.

AC-10.4
Workspace can be reconstructed when supported.

AC-10.5
Coding runtime cannot bypass EffectGateway.
```

---

# 20. Epic 11 — External Connectors

## Objectif

Formaliser les intégrations aux systèmes externes métier.

## Contrats

```text
Connector
ConnectorDescriptor
ConnectorCapability
ConnectorRegistry
ReconciliationPort
```

## Capabilities

```text
READ
WRITE
NATIVE_IDEMPOTENCY
RECONCILIATION
WEBHOOKS
POLLING
PAGINATION
BATCHING
```

## Premiers connectors candidats

```text
GitHub
GitLab
Slack
Email
Jira
AWS
Azure
Generic HTTP
```

## PRs

```text
PR-1101 — Connector port
PR-1102 — Connector registry
PR-1103 — Connector capability negotiation
PR-1104 — Generic HTTP connector base
PR-1105 — GitHub connector
PR-1106 — GitHub reconciliation
PR-1107 — webhook ingress
PR-1108 — connector contract tests
```

## Acceptance Criteria

```text
AC-11.1
Connector != RuntimeAdapter.

AC-11.2
Provider SDK objects never leak to core.

AC-11.3
Ambiguous write maps to Effect UNKNOWN.

AC-11.4
Connector-specific reconciliation is supported.

AC-11.5
Credentials remain externally resolved and scoped.
```

---

# 21. Epic 12 — Public API V2

## Objectif

Exposer une API stable sur les Application Services.

## Surface

```text
PyAgentsKit
├── runs
├── sessions
├── conversations
├── effects
├── approvals
├── artifacts
├── runtimes
├── audit
├── health
└── admin
```

## Livrables

```text
async client
sync facade
public views
error hierarchy
pagination
event stream
idempotency
optional HTTP API
OpenAPI
```

## PRs

```text
PR-1201 — Async client facade
PR-1202 — Public read models
PR-1203 — Error codes
PR-1204 — Sync facade
PR-1205 — Event streaming
PR-1206 — Pagination
PR-1207 — HTTP adapter
PR-1208 — OpenAPI contract
```

## Acceptance Criteria

```text
AC-12.1
No ORM object leaks publicly.

AC-12.2
No runtime SDK object leaks publicly.

AC-12.3
WAITING is exposed as non-terminal durable state.

AC-12.4
Client timeout does not imply Effect failure.

AC-12.5
Public safety semantics are compatibility-tested.
```

---

# 22. Epic 13 — V1 → V2 Migration

## Objectif

Permettre aux utilisateurs V1 de migrer progressivement.

## Livrables

```text
V1 compatibility adapters
migration guide
data migration command
API migration examples
deprecation policy
V1/V2 coexistence tests
```

## PRs

```text
PR-1301 — V1 compatibility mapping
PR-1302 — Run status migration rules
PR-1303 — Session → Conversation migration helpers
PR-1304 — Effect migration
PR-1305 — Approval migration
PR-1306 — PostgreSQL V1→V2 migration command
PR-1307 — Documentation migration guide
```

## Acceptance Criteria

```text
AC-13.1
V1.6 data can be migrated without losing Effects or approvals.

AC-13.2
No successful V1 Effect is replayed after migration.

AC-13.3
V1 waiting approval semantics map safely.

AC-13.4
Migration is restartable.

AC-13.5
Rollback/forward-fix procedure exists.
```

---

# 23. Epic 14 — Production Qualification

## Objectif

Prouver que la V2 conserve et étend les garanties de la V1.6.

## Qualification obligatoire

```text
real PostgreSQL
two workers
multi-process
SIGTERM
SIGKILL
SIGSTOP
database outage
runtime crash
ambiguous Effect
approval recovery
connector outage
restore/PITR
coding-agent remote Effect
```

## PRs

```text
PR-1401 — V2 release gates
PR-1402 — Multi-process V2 qualification
PR-1403 — Runtime adapter qualification
PR-1404 — Reconciliation qualification
PR-1405 — PostgreSQL outage tests
PR-1406 — Restore/PITR tests
PR-1407 — Coding-agent failure tests
PR-1408 — Security qualification
PR-1409 — Performance/load qualification
```

## Acceptance Criteria

```text
AC-14.1
0 implicit replay of SUCCEEDED critical Effects.

AC-14.2
0 accepted stale fencing token.

AC-14.3
0 cross-tenant recovery.

AC-14.4
All production blockers from document 25 are green.

AC-14.5
Runbooks exist for all P0 scenarios.
```

---

# 24. Release Mapping

## 2.0.0a1 — Domain Foundations

Inclut :

```text
Epic 0
Epic 1
```

Objectif :

```text
canonical V2 semantics
```

---

# 25. 2.0.0a2 — Runtime Abstraction

Inclut :

```text
Epic 2
Epic 3
```

Objectif :

```text
V1 Runner becomes NativeRuntimeAdapter
```

---

# 26. 2.0.0a3 — Effect & Recovery Core

Inclut :

```text
Epic 4
Epic 5
```

Objectif :

```text
generalized Effect safety
deterministic RecoveryPlanner
```

---

# 27. 2.0.0a4 — Persistence V2

Inclut :

```text
Epic 6
Epic 7
```

Objectif :

```text
normalized durable stores
```

---

# 28. 2.0.0b1 — Governance & Audit

Inclut :

```text
Epic 8
Epic 9
```

---

# 29. 2.0.0b2 — External Runtime & Connector Ecosystem

Inclut :

```text
Epic 10
Epic 11
```

---

# 30. 2.0.0rc1 — Public Contracts & Migration

Inclut :

```text
Epic 12
Epic 13
```

---

# 31. 2.0.0 — Production Qualified

Inclut :

```text
Epic 14
```

et tous les production blockers fermés.

---

# 32. Workstreams parallélisables

Une fois Epic 2 stabilisé :

```text
Runtime adapters
```

peuvent avancer partiellement en parallèle avec :

```text
Persistence
Governance
Audit
```

Mais les contrats de domaine doivent être gelés avant.

---

# 33. Priorité réelle

Ordre strict recommandé :

```text
1. Domain semantics
2. Runtime abstraction
3. Effect semantics
4. Recovery
5. Persistence contracts
6. PostgreSQL
7. Governance
8. Audit/Outbox/Inbox
9. Coding runtimes
10. Connectors
11. Public API
12. Migration
13. Qualification
```

---

# 34. Ce qu’il ne faut pas faire

## Anti-pattern A — commencer par PostgreSQL

Mauvais ordre :

```text
design schema
then infer domain
```

Bon ordre :

```text
design domain
then persistence contracts
then schema
```

---

# 35. Anti-pattern B — déplacer tous les fichiers

Une PR massive de réorganisation rendrait :

```text
review
bisect
rollback
compatibility
```

trop difficiles.

---

# 36. Anti-pattern C — enrichir RunStatus V1

Ne pas injecter la sémantique V2 directement dans :

```text
RunStatus V1
```

Le contrat est gelé.

---

# 37. Anti-pattern D — ajouter `if runtime ==`

Toute logique runtime-specific doit vivre dans l’adapter.

---

# 38. Anti-pattern E — transformer Metadata en extension system

Ne pas cacher la V2 dans :

```text
metadata["runtime_type"]
metadata["conversation_id"]
metadata["effect_kind"]
```

Les concepts centraux méritent des types explicites.

---

# 39. Anti-pattern F — réutiliser `Message` pour tout

Le Message LLM V1 doit rester distinct du Message durable Conversation V2.

---

# 40. Anti-pattern G — remplacer tous les stores V1

Les stores V1 doivent rester compatibles jusqu’à la migration officielle.

---

# 41. Stratégie de test par Epic

Chaque Epic doit contenir :

```text
unit tests
contract tests
integration tests where relevant
compatibility regression
```

Les Epics safety-critical ajoutent aussi :

```text
failure injection
concurrency tests
multi-process tests
```

---

# 42. Definition of Ready d’une PR

Une PR V2 est prête si :

```text
scope explicit
bounded context identified
ports identified
public API impact identified
migration impact identified
failure semantics identified
tests identified
```

---

# 43. Definition of Done d’une PR

```text
code complete
unit tests
typing green
lint green
architecture import rules green
contract tests green where applicable
documentation updated
compatibility reviewed
security reviewed if critical
```

---

# 44. Architecture gates CI

Ajouter :

```text
import-linter
public API snapshot
contract test suites
migration smoke tests
PostgreSQL integration
failure tests
```

---

# 45. Quality Gates V2

Minimum :

```text
mypy strict
Ruff
pytest
branch coverage >= 90%
API contract freeze
schema migration tests
adapter contract tests
```

---

# 46. Compatibility Gates

V1 :

```text
155 root exports unchanged
existing examples green
existing serialization contracts green
```

V2 :

```text
namespaced contracts
independent versioning policy
```

---

# 47. Migration philosophy

Chaque migration doit être :

```text
observable
restartable
idempotent where possible
auditable
```

---

# 48. Data migration principles

Ne jamais reconstruire arbitrairement :

```text
Approval
Effect success
ExternalReference
Fencing authority
```

à partir de logs si la donnée durable manque.

---

# 49. Safety during migration

Avant migration production :

```text
stop admissions
drain workers
snapshot
validate schema
migrate
verify effects
verify approvals
verify fencing
resume
```

---

# 50. V1.6 maintenance during V2

Pendant le développement V2 :

```text
1.6.x receives:
security fixes
bug fixes
critical production fixes
```

Pas de nouvelles features majeures.

---

# 51. Repository branching strategy

Recommandation :

```text
main remains releasable
```

Chaque Epic :

```text
short-lived feature branches
```

Pas de branche V2 longue durée non intégrée.

---

# 52. Feature flags

Les composants V2 peuvent être behind explicit flags ou namespaces jusqu’à maturité.

Mais :

```text
no hidden semantic override
```

de la V1.

---

# 53. Observability during transition

Les deux générations doivent produire suffisamment de contexte pour comparer :

```text
V1 runner result
V2 runtime invocation
Effect mapping
Approval mapping
```

---

# 54. Architecture Decision Records prioritaires

À écrire rapidement :

```text
ADR-V2-001 V2 namespace and compatibility
ADR-V2-002 Domain boundaries
ADR-V2-003 AgentRuntimeAdapter
ADR-V2-004 Native Runner Adapter
ADR-V2-005 Run vs RuntimeInvocation
ADR-V2-006 Session vs Conversation
ADR-V2-007 Effect V2
ADR-V2-008 Reconciliation model
ADR-V2-009 Repository vs Store
ADR-V2-010 UnitOfWork
ADR-V2-011 PostgreSQL normalized schema
ADR-V2-012 Public API V2
```

---

# 55. Delivery risks

## Risk 1 — double domain

Symptôme :

```text
V1 and V2 semantics mixed in same classes
```

Mitigation :

```text
strict namespace boundary
```

---

# 56. Risk 2 — excessive abstraction

Le DDD ne doit pas générer :

```text
hundreds of empty interfaces
```

Chaque abstraction doit protéger :

```text
domain semantics
technology boundary
testability
```

---

# 57. Risk 3 — premature connectors

Ne pas implémenter 10 providers avant de stabiliser :

```text
Connector contract
Reconciliation semantics
```

---

# 58. Risk 4 — over-general RuntimeAdapter

Éviter un port incapable de représenter de vraies différences entre runtimes.

Utiliser :

```text
capability negotiation
```

plutôt que le plus petit dénominateur commun.

---

# 59. Risk 5 — breaking effect safety during migration

V1 effect journal et V2 EffectRepository doivent coexister tant que la migration n’est pas prouvée.

---

# 60. Risk 6 — database redesign too early

Le modèle 24 doit être implémenté après Domain/Repository stabilization.

---

# 61. Risk 7 — compatibility paralysis

Préserver V1 ne signifie pas reproduire toutes ses décisions en V2.

La compatibilité doit être :

```text
boundary
not design constraint
```

---

# 62. Success metrics

Le programme V2 réussit si :

```text
one Native runtime + one external runtime
share the same reliability semantics
```

et si :

```text
the same Run recovery model
works across both.
```

---

# 63. Technical proof points

Avant RC :

```text
Native Runner via adapter
LangGraph or equivalent external adapter
one coding-agent adapter
PostgreSQL normalized
real Effect reconciliation
approval recovery
multi-worker takeover
connector ambiguous write
```

---

# 64. Product proof points

PyAgentsKit V2 doit démontrer :

```text
Build with any runtime
Run with PyAgentsKit reliability
```

---

# 65. Exit criteria V2 alpha

```text
Domain stable
AgentRuntimeAdapter stable
Native adapter working
Effect V2 working
RecoveryPlanner working
```

---

# 66. Exit criteria V2 beta

```text
PostgreSQL normalized
Governance
Audit
Outbox/Inbox
one coding runtime
one connector
```

---

# 67. Exit criteria V2 RC

```text
public API stable
migration verified
all adapter contracts frozen
production tests green
```

---

# 68. Exit criteria V2 stable

```text
failure matrix green
runbooks complete
load qualification complete
security qualification complete
```

---

# 69. First 10 PRs to implement

Ordre exact recommandé :

```text
PR-0001 Freeze V1 compatibility inventory
PR-0002 Introduce V2 package skeleton
PR-0003 Add architecture dependency rules
PR-0101 Add V2 typed IDs/shared kernel
PR-0102 Add Execution domain
PR-0103 Add Effects domain
PR-0104 Add Governance domain
PR-0105 Add Coordination domain
PR-0201 Add AgentRuntimeAdapter
PR-0301 Add NativeRuntimeAdapter
```

---

# 70. First vertical slice

Le premier slice fonctionnel doit être très petit :

```text
Create V2 Run
↓
start through NativeRuntimeAdapter
↓
persist Run in MemoryRepository
↓
inspect RuntimeInvocation
↓
complete Run
```

Pas PostgreSQL au début.

---

# 71. Second vertical slice

```text
Run
↓
Effect
↓
EffectGateway
↓
UNKNOWN simulation
↓
RecoveryPlanner
↓
manual reconciliation
```

---

# 72. Third vertical slice

```text
Run
↓
Lease
↓
worker A
↓ crash
↓
worker B takeover
↓
resume NativeRuntimeAdapter
```

---

# 73. Fourth vertical slice

```text
same scenario
+
PostgreSQL V2
```

---

# 74. Fifth vertical slice

```text
External runtime
↓
AgentRuntimeAdapter
↓
same Effect/Lease/Recovery semantics
```

C’est le proof-of-architecture le plus important.

---

# 75. Sixth vertical slice

```text
Coding agent
↓
workspace
↓
git push Effect
↓
timeout
↓
UNKNOWN
↓
reconciliation
```

---

# 76. Engineering board structure

Epics peuvent être suivis dans GitHub Projects :

```text
EPIC
↓
LOT
↓
PR
↓
Acceptance criteria
↓
Qualification evidence
```

---

# 77. Labeling suggestion

```text
area:domain
area:runtime
area:effects
area:recovery
area:persistence
area:security
area:connector
area:coding
area:api

type:architecture
type:feature
type:migration
type:test
type:docs

risk:p0
risk:p1
risk:p2
```

---

# 78. Milestone suggestion

```text
2.0.0a1
2.0.0a2
2.0.0a3
2.0.0a4
2.0.0b1
2.0.0b2
2.0.0rc1
2.0.0
```

---

# 79. Documentation synchronization

À chaque Epic :

```text
code
+
ADR
+
canonical architecture docs
+
migration notes
```

doivent évoluer ensemble.

---

# 80. Documents à mettre à jour pendant le programme

Priorité élevée :

```text
00
03
05
06
07
08
10
11
12
14
23
24
25
```

---

# 81. Documents suivants à créer

Après ce document :

```text
../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md
../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md
../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md
../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md
../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md
../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md
../domain/33_PYAGENTSKIT_DOMAIN_EVENTS_AND_OUTBOX_INBOX.md
../runtime/34_PYAGENTSKIT_RUNTIME_REGISTRY_AND_CAPABILITY_NEGOTIATION.md
../runtime/35_PYAGENTSKIT_NATIVE_RUNTIME_ADAPTER.md
../runtime/36_PYAGENTSKIT_RECOVERY_PLANNER_SPECIFICATION.md
../runtime/37_PYAGENTSKIT_RECONCILIATION_MODEL.md
../operations/38_PYAGENTSKIT_TEST_STRATEGY.md
```

---

# 82. Definition of Done du programme V2

PyAgentsKit V2 est considéré terminé lorsque :

1. la V1 reste migrable ;
2. le domaine V2 est indépendant des technologies ;
3. AgentRuntimeAdapter supporte au moins deux familles de runtime ;
4. NativeRunner est un adapter, pas le cœur ;
5. Effects sont génériques ;
6. Reconciliation est explicite ;
7. RecoveryPlanner est déterministe ;
8. PostgreSQL est normalisé et transactionnel ;
9. approvals sont indépendantes des workers ;
10. ownership/fencing sont conservés ;
11. audit/outbox/inbox sont durables ;
12. coding-agent remote Effects sont protégés ;
13. connectors sont capability-aware ;
14. API V2 est stable ;
15. migration V1→V2 est prouvée ;
16. production qualification est verte ;
17. crash/recovery ne dépend pas d’un graceful shutdown ;
18. aucun Effect critique réussi n’est implicitement rejoué.

---

# 83. Résumé exécutif

La transformation cible est :

```text
PyAgentsKit V1.6
Provider-neutral agent runtime
        │
        ▼
PyAgentsKit V2
Framework-neutral Agent Reliability Layer
```

Elle ne nécessite pas de jeter les fondations existantes.

Elle nécessite de les repositionner :

```text
Runner
→ NativeRuntimeAdapter

DurableRunner
→ Application durable execution

EffectRecord
→ Generic Effect domain

RecoveryPlan V1
→ RecoveryPlanner V2

PostgreSQL aggregate JSONB
→ normalized repositories

Guardrails + approvals
→ Governance & Security domain

Event sinks
→ Telemetry + durable Audit

Provider adapters
→ Native runtime Model adapters
```

La réussite du programme dépend de l’ordre :

> **Domain first → Ports second → Adapters third → Migration fourth → Qualification last.**

Le prochain document naturel est :

```text
../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md
```
