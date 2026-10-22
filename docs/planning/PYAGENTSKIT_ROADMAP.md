# PyAgentsKit Roadmap

> **Agent Reliability Layer for Real-World AI Applications**

This roadmap tracks the transition of PyAgentsKit from the V1.6 native mono-agent runtime to the V2 framework-neutral reliability layer.

The guiding principle is:

> **Build semantics. Integrate infrastructure and runtimes. Qualify failures.**

---

## Current Baseline

### PyAgentsKit 1.6.x — V1 Maintenance

Status: **Released / Maintenance**

PyAgentsKit 1.6 is the production baseline for the current architecture.

It already provides:

- typed mono-agent execution;
- durable runs;
- sessions and memory;
- tool execution;
- approvals;
- checkpoints;
- durable recovery;
- SQLite and PostgreSQL persistence;
- leases;
- fencing tokens;
- distributed durable execution;
- object/blob stores;
- OpenTelemetry integration;
- production qualification infrastructure.

V1 is now considered feature-frozen except for:

- bug fixes;
- security fixes;
- compatibility fixes;
- critical production hardening.

No new V2 architectural responsibilities should be added directly to the V1 core.

---

# V2 Direction

PyAgentsKit V2 changes the level of abstraction.

```text
V1
PyAgentsKit = Agent Runtime

V2
PyAgentsKit = Agent Reliability Layer
```

The V2 core must remain independent from:

- LangGraph;
- PydanticAI;
- OpenAI Agents SDK;
- Claude Agent SDK;
- AutoGen;
- CrewAI;
- Codex;
- Claude Code;
- OpenCode;
- GitHub;
- PostgreSQL;
- Kubernetes;
- any single model provider.

The target execution model is:

```text
AI Application
      │
      ▼
PyAgentsKit Reliability Core
      │
      ├── Durable Runs
      ├── Effects
      ├── Reconciliation
      ├── Recovery
      ├── Approvals
      ├── Authorization
      ├── Leases / Fencing
      ├── Audit
      └── Artifacts
      │
      ▼
AgentRuntimeAdapter
      │
      ├── Native Runtime
      ├── LangGraph
      ├── PydanticAI
      ├── OpenAI Agents
      ├── Coding Agents
      └── Custom Runtimes
```

---

# Release Roadmap

Detailed milestone specifications:

- [V2 implementation next steps](49_PYAGENTSKIT_V2_IMPLEMENTATION_NEXT_STEPS.md)

- [2.0.0a1 — Domain Foundations](../specs/milestones/50_PYAGENTSKIT_MILESTONE_2_0_0A1_DOMAIN_FOUNDATIONS_SPEC.md)
- [2.0.0a2 — Runtime Abstraction](../specs/milestones/51_PYAGENTSKIT_MILESTONE_2_0_0A2_RUNTIME_ABSTRACTION_SPEC.md)
- [2.0.0a3 — Effects & Recovery Core](../specs/milestones/52_PYAGENTSKIT_MILESTONE_2_0_0A3_EFFECTS_RECOVERY_CORE_SPEC.md)
- [2.0.0a4 — Persistence V2](../specs/milestones/53_PYAGENTSKIT_MILESTONE_2_0_0A4_PERSISTENCE_V2_SPEC.md)
- [2.0.0b1 — Governance, Security & Audit](../specs/milestones/54_PYAGENTSKIT_MILESTONE_2_0_0B1_GOVERNANCE_SECURITY_AUDIT_SPEC.md)
- [2.0.0b2 — External Runtimes & Connectors](../specs/milestones/55_PYAGENTSKIT_MILESTONE_2_0_0B2_EXTERNAL_RUNTIMES_CONNECTORS_SPEC.md)
- [2.0.0rc1 — Public Contracts & Migration](../specs/milestones/56_PYAGENTSKIT_MILESTONE_2_0_0RC1_PUBLIC_CONTRACTS_MIGRATION_QUALIFICATION_SPEC.md)
- [2.0.0 — Production Qualified](../specs/milestones/57_PYAGENTSKIT_MILESTONE_2_0_0_PRODUCTION_QUALIFIED_SPEC.md)

```text
1.6.x
  │
  ▼
2.0.0a1  Domain Foundations
  │
  ▼
2.0.0a2  Runtime Abstraction
  │
  ▼
2.0.0a3  Effects & Recovery Core
  │
  ▼
2.0.0a4  Persistence V2
  │
  ▼
2.0.0b1  Governance, Security & Audit
  │
  ▼
2.0.0b2  External Runtimes & Connectors
  │
  ▼
2.0.0rc1 Public Contracts & Migration
  │
  ▼
2.0.0    Production Qualified
```

---

# 2.0.0a1 — Domain Foundations

Status: **Qualified — Release pending**

Goal:

> Establish the V2 domain model and encode the core reliability semantics before introducing infrastructure.

## Scope

### Shared Kernel

- typed identifiers;
- `TenantId`;
- aggregate versions;
- canonical timestamps;
- `Fingerprint`;
- `ExternalReference`;
- `FencingToken`;
- canonical domain errors.

### Execution

- `Run`;
- `RunId`;
- `RunStatus`;
- `Session`.

Target `RunStatus`:

```text
CREATED
RUNNING
WAITING
PAUSED
SUCCEEDED
FAILED
CANCELLED
```

### Effects

- `Effect`;
- `EffectId`;
- `EffectStatus`;
- Effect fingerprint;
- idempotency identity;
- external references.

Target `EffectStatus`:

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

### Governance

- `Approval`;
- `ApprovalId`;
- `ApprovalStatus`;
- `ApprovalScope`.

Target `ApprovalStatus`:

```text
PENDING
APPROVED
REJECTED
EXPIRED
CANCELLED
```

### Coordination

- `Lease`;
- `LeaseId`;
- `Worker`;
- `WorkerId`;
- `OwnershipContext`;
- `FencingToken`.

### Conversations

- `Conversation`;
- `ConversationId`;
- `Actor`;
- `Participant`;
- `ConversationMessage`;
- `MessageRecipient`.

### Runtime Integration

- `RuntimeBinding`;
- `RuntimeInvocation`;
- initial `RuntimeCapability`.

### Artifacts

- `Artifact`;
- checksums;
- artifact references.

### Audit

- canonical `AuditEvent`.

### Reconciliation Foundations

- `ReconciliationCase`;
- reconciliation status;
- reconciliation resolution.

## Mandatory Invariants

```text
Run != RuntimeInvocation
Session != Conversation
RuntimeMessage != ConversationMessage
Message != Approval
ToolCall != Effect
UNKNOWN != FAILED
WAITING != PAUSED
Approval != Authorization
Lease != Authorization
Checkpoint != Effect truth
Runtime completion != Run success
Cancellation != rollback
```

## Testing

- unit tests;
- state-machine tests;
- invalid transition tests;
- property-based tests;
- architecture dependency tests;
- package build/install smoke tests.

## Exit Gate

`2.0.0a1` is complete when:

- Domain is infrastructure-independent;
- all P0 state machines are implemented;
- P0 invariants are executable tests;
- package dependency rules are enforced in CI;
- wheel and sdist build successfully;
- fresh-environment import succeeds.

---

# 2.0.0a2 — Runtime Abstraction

Status: **Qualified — Release pending**

Goal:

> Make runtimes interchangeable through an explicit capability-based contract.

## Scope

- `AgentRuntimeAdapter`;
- `RuntimeDescriptor`;
- `RuntimeHandle`;
- `RuntimeCapability`;
- `RuntimeRequirements`;
- `RuntimeRegistry`;
- `CapabilityNegotiator`;
- `RuntimeBinding`;
- `RuntimeInvocation`;
- `SideEffectControlLevel`.

Canonical adapter contract:

```python
class AgentRuntimeAdapter(Protocol):
    async def start(...): ...
    async def resume(...): ...
    async def cancel(...): ...
    async def inspect(...): ...
    async def events(...): ...
    async def checkpoint(...): ...
    async def close(...): ...
```

## Runtime Capabilities

Initial vocabulary:

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

## Side-Effect Control

```text
FULL
BOUNDED
OPAQUE
```

## Native Runtime

Reclassify the V1 Runner:

```text
V1 Runner
→ NativeRuntimeEngine
→ NativeRuntimeAdapter
```

No big-bang rewrite.

Reuse where valid:

- model providers;
- tool definitions;
- tool execution primitives;
- guardrails;
- streaming/event infrastructure.

## Exit Gate

- Native runtime passes the common runtime contract suite;
- capability negotiation is deterministic;
- missing mandatory capabilities fail before execution;
- the Application layer does not branch on runtime brand;
- Native is first-party but not architecturally privileged.

---

# 2.0.0a3 — Effects & Recovery Core

Status: **Qualified — Release pending**

Goal:

> Make real-world side effects explicit, recoverable and safe under ambiguity.

## Scope

- Effect lifecycle V2;
- idempotency;
- external references;
- Effect fingerprints;
- `ReconciliationCase`;
- `ReconciliationEvidence`;
- `ReconciliationPort`;
- reconciliation policies;
- `RecoveryPlanner`;
- `RecoveryContext`;
- `RecoveryPlan`;
- `RecoveryBlocker`;
- `NextAction`.

Canonical recovery actions:

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

## Crash Windows

Mandatory qualification:

```text
W1 — before durable intent
W2 — after durable intent, before send
W3 — after send, before response
W4 — after response, before durable outcome
W5 — after durable outcome, before next Run progress
```

Critical rule:

```text
W3/W4
→ UNKNOWN
→ Reconciliation
```

Never:

```text
UNKNOWN
→ blind retry
```

## Recovery Ordering

```text
authority
→ security
→ unresolved Effects
→ Approvals
→ runtime recovery
→ completion
```

## Exit Gate

- W1–W5 covered;
- `UNKNOWN` never collapsed into `FAILED`;
- `SUCCEEDED` Effects are never implicitly replayed;
- all canonical `NextAction` values are tested;
- manual intervention is a supported safe outcome.

---

# 2.0.0a4 — Persistence V2

Status: **Next**

Goal:

> Persist V2 semantics using explicit ports, normalized state and production-grade concurrency guarantees.

## Repository Ports

- `RunRepository`;
- `SessionRepository`;
- `ConversationRepository`;
- `MessageRepository`;
- `MemoryRepository`;
- `EffectRepository`;
- `ReconciliationRepository`;
- `ApprovalRepository`;
- `LeaseRepository`;
- `WorkerRepository`;
- `ArtifactRepository`.

## Stores

- `BlobStore`;
- `AuditStore`;
- `OutboxStore`;
- `InboxStore`.

## Unit of Work

Introduce explicit local transactional boundaries.

No external call is allowed inside a long-running DB transaction.

## PostgreSQL Target Model

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

## Messaging Reliability

Introduce:

```text
DomainEvent
IntegrationEvent
Outbox
Inbox
```

Maintain:

```text
DomainEvent != IntegrationEvent
RuntimeEvent != DomainEvent
AuditEvent != DomainEvent
Queue delivery != ownership
Inbox dedup != Effect idempotency
```

## Exit Gate

- Memory, SQLite where retained, and PostgreSQL pass repository contracts;
- optimistic concurrency is enforced;
- fencing remains monotonic;
- Outbox/Inbox are transactional;
- multi-process PostgreSQL tests pass.

---

# 2.0.0b1 — Governance, Security & Audit

Status: **Planned**

Goal:

> Make authority, identity, approvals and accountability explicit.

## Scope

- `Principal`;
- `SecurityContext`;
- `AuthorizationPort`;
- `IdentityProviderPort`;
- `PolicyEvaluator`;
- Approval V2;
- policy versioning;
- tenant isolation;
- `AuditStore`;
- `AuditEvent`;
- `SecretReference`.

Critical distinction:

```text
Authentication
!=
Authorization
!=
Approval
```

## Approval Semantics

Approvals must be bound to the exact action they authorize.

Examples:

```text
Effect ID
fingerprint
commit SHA
artifact digest
deployment target
```

Free-text conversation messages never count as Approvals.

## Exit Gate

- tenant isolation verified;
- Approval scope drift is rejected;
- authorization is revalidated where required;
- critical administrative actions are audited;
- secrets do not leak into durable state/logs/events.

---

# 2.0.0b2 — External Runtimes & Connectors

Status: **Planned**

Goal:

> Demonstrate framework neutrality and real-world Effect safety with external runtimes and systems.

## Runtime Targets

At least:

- one external general-purpose runtime;
- one coding-agent runtime.

Candidate families:

```text
LangGraph
PydanticAI
OpenAI Agents
Codex
Claude Code
OpenCode
```

Final choices must be based on actual adapter feasibility and contract support.

## Connector Targets

Prioritize connectors with meaningful write/reconciliation semantics.

Recommended first connector:

```text
GitHub
```

## Flagship Coding-Agent Scenario

```text
agent edits code
→ commit SHA A
→ Approval bound to SHA A
→ git push
→ response lost
→ Effect UNKNOWN
→ worker crash
→ another worker takeover
→ remote SHA reconciliation
→ CONFIRMED_SUCCESS
→ no duplicate push
→ runtime resumes
```

This scenario should demonstrate:

- runtime integration;
- Effect safety;
- Approval scope;
- reconciliation;
- recovery;
- fencing;
- audit.

## Exit Gate

- external adapters pass contract tests;
- at least one write-capable connector has a documented reconciliation strategy;
- coding-agent protected Effects are governed by PyAgentsKit;
- limitations are explicit.

---

# 2.0.0rc1 — Public Contracts & Migration

Status: **Planned**

Goal:

> Freeze the V2 public contract, migrate safely from V1, and qualify the release candidate under production-like conditions.

## Public Contract Freeze

Freeze:

- public imports;
- IDs;
- enums;
- error taxonomy;
- serialization;
- runtime adapter contract;
- event envelopes;
- migration commands.

## V1 → V2 Migration

Strategy:

```text
preflight
→ expand
→ backfill
→ verify
→ switch
→ contract later
```

Critical mappings:

```text
V1 WAITING_APPROVAL
→ V2 Run WAITING + Approval blocker

V1 UNKNOWN_EFFECT
→ V2 Run WAITING + Effect UNKNOWN

V1 Effect COMPLETED
→ V2 Effect SUCCEEDED
```

Migration invariants:

```text
no successful Effect lost
no Approval fabricated
no UNKNOWN collapsed
no fencing regression
one source of truth per phase
```

## Production Qualification

Mandatory:

- real PostgreSQL;
- 2+ independent workers;
- SIGTERM;
- SIGKILL;
- SIGSTOP;
- stale worker fencing;
- W1–W5;
- connector ambiguity;
- Restore/PITR;
- rolling upgrades;
- recovery storm;
- performance baseline;
- saturation testing;
- soak testing;
- runbook Game Days.

## Exit Gate

All critical release gates are green and no P0 defect remains.

---

# 2.0.0 — Production Qualified

Status: **Future**

Goal:

> Ship the first stable PyAgentsKit release whose reliability claims are backed by executable production qualification.

The stable release requires green gates for:

```text
Public Contracts
Domain Invariants
Runtime Adapters
Effect Safety
Recovery
Coordination
Persistence
Governance
Audit
Security
Migration
Operations
Performance
Documentation
```

No waiver is allowed for:

- Effect safety;
- fencing;
- cross-tenant isolation;
- Approval integrity;
- Restore/PITR safety;
- migration data integrity.

---

# Adapter Qualification Model

Official adapters progress through:

```text
L0 — Fake
L1 — Contract Compliant
L2 — Integration Tested
L3 — Failure Tested
L4 — Production Qualified
```

A capability may only be advertised when its behavior has been demonstrated by the relevant contract tests.

---

# Test Maturity Model

```text
TST-L0 — Basic Unit Tests
TST-L1 — Domain + Integration
TST-L2 — Contract + Concurrency
TST-L3 — Failure + Distributed
TST-L4 — Production Qualification
```

V2 stable targets `TST-L4` for P0 reliability surfaces.

---

# Core Reliability Invariants

The V2 implementation must continuously preserve:

```text
Run != RuntimeInvocation
Session != Conversation
RuntimeMessage != ConversationMessage
ToolCall != Effect
FAILED != UNKNOWN
Retry != Recovery
Retry != Reconciliation
Approval != Authorization
Actor != Principal
Lease != Lock
Heartbeat != Ownership
Queue delivery != Ownership
RuntimeAdapter != ModelAdapter
RuntimeAdapter != Connector
DomainEvent != IntegrationEvent != RuntimeEvent != AuditEvent
Repository != Store
Transaction != Distributed Transaction
Restore != Safe Resume
Runtime completion != Run success
Client timeout != Effect failure
```

---

# Repository Structure Target

```text
src/pyagentskit/
├── contracts/
├── domain/
│   ├── shared/
│   ├── execution/
│   ├── effects/
│   ├── governance/
│   ├── coordination/
│   ├── conversations/
│   ├── runtime_integration/
│   ├── artifacts/
│   └── audit/
├── application/
├── adapters/
├── api/
├── bootstrap/
├── compat/
│   └── v1/
└── testing/

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

docs/
examples/
scripts/
```

Dependency direction:

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

# Immediate Next Steps

The V2 foundation through `2.0.0a3` is now implemented and qualified. The next implementation work is:

```text
1. Merge the qualified 2.0.0a3 branch into main.
2. Create tag v2.0.0a3 and publish the GitHub release.
3. Start 2.0.0a4 — Persistence V2 from the tagged A3 baseline.
4. Define V2 repository contracts for Run / Session / Conversation / Effect / Reconciliation / Approval / Lease / Artifact.
5. Introduce explicit UnitOfWork boundaries for local transactions.
6. Implement in-memory reference repositories for contract qualification.
7. Add SQLite V2 persistence only where it remains useful for local/dev compatibility.
8. Implement PostgreSQL V2 repositories with optimistic concurrency and monotonic fencing.
9. Persist RuntimeBinding / RuntimeInvocation / Reconciliation evidence as first-class V2 records.
10. Add transactional Outbox / Inbox and distinguish messaging dedup from Effect idempotency.
11. Run repository contract tests across supported implementations.
12. Add multi-process PostgreSQL qualification and stale-writer/fencing tests.
13. Build, fresh-install and qualify 2.0.0a4.
```

A3 leaves one explicit capability limitation intentionally unresolved: the Native runtime does not advertise `TOOL_INTERCEPTION`; its V1 tool loop remains `BOUNDED` until a V2 interception contract is implemented and demonstrated.

---

# Next Implementation Sprint — 2.0.0a4 Persistence V2

## Goal

> Persist V2 reliability semantics with explicit repository contracts, local transaction boundaries and production-grade concurrency guarantees.

## Priority tasks

```text
[ ] Define repository protocols from the canonical V2 persistence spec
[ ] Define UnitOfWork
[ ] Implement reference in-memory repositories
[ ] Map Effect + Reconciliation with optimistic concurrency
[ ] Map Run + RuntimeBinding + RuntimeInvocation
[ ] Map Approval + Lease/Fencing
[ ] Map Conversation / Message / Recipient
[ ] Map Artifact / Audit foundations
[ ] Add Outbox / Inbox
[ ] Add repository contract suite
[ ] Add PostgreSQL implementation
[ ] Add PostgreSQL multi-process tests
[ ] Prove fencing monotonicity under concurrent writers
[ ] Prove no external I/O inside long DB transactions
[ ] Build wheel / sdist
[ ] Fresh-install qualification
```

## Definition of Done

```text
[ ] Repository contracts are adapter-neutral
[ ] Optimistic concurrency is enforced
[ ] Fencing is monotonic
[ ] Effect truth survives process crashes
[ ] Reconciliation evidence is durable
[ ] RuntimeBinding is durable and immutable by silent recovery
[ ] Outbox / Inbox are transactional
[ ] PostgreSQL contract tests pass
[ ] Package / fresh install / CI are green
[ ] Version is 2.0.0a4
```

---

# Deferred Until Later Milestones

Do **not** prioritize yet:

- Kubernetes deployment implementation;
- multi-region architecture;
- broker selection;
- broad plugin discovery;
- many external runtime adapters;
- many connectors;
- generic workflow/scheduler features;
- custom IAM implementation;
- generic observability backend;
- generic vector/RAG platform.

These should only be introduced when a V2 milestone requires them.

---

# Product Boundary

PyAgentsKit must not become:

- a coding agent;
- an LLM wrapper;
- a prompt framework;
- a generic workflow engine;
- a generic scheduler;
- a broker;
- an IAM platform;
- a vector database;
- an observability backend;
- a Git engine;
- a cloud platform.

Its core differentiation is:

```text
framework-neutral reliability semantics
+
first-class Effect safety
+
explicit uncertainty
+
reconciliation
+
durable approvals
+
distributed ownership / fencing
+
runtime neutrality
+
auditability
```

The strongest product wedge is:

> **The reliability control layer for agent side effects.**

---

# Definition of V2 Success

PyAgentsKit V2 is successful when an application can:

```text
use any supported runtime
        │
        ▼
execute a long-running Run
        │
        ▼
perform protected real-world Effects
        │
        ▼
crash at an arbitrary boundary
        │
        ▼
move to another worker
        │
        ▼
reconcile ambiguous external state
        │
        ▼
resume without repeating a successful Effect
        │
        ▼
preserve Approval, authority and audit guarantees
```

---

# Final Principle

> **The V2 roadmap is not a race to add more agent features. It is a sequence of increasingly strong proofs that agents can act in the real world without PyAgentsKit losing track of what happened, who was allowed to act, or whether repeating an action is safe.**
