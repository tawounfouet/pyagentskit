# PyAgentsKit — Architecture Decision Records Index

**Document :** `../architecture/46_PYAGENTSKIT_ARCHITECTURE_DECISION_RECORDS_INDEX.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Registre maître des décisions architecturales  
**Projet :** PyAgentsKit  

---

# 1. Objet

Ce document constitue l’**index canonique des Architecture Decision Records (ADR)** de PyAgentsKit.

Il ne remplace pas les ADR individuels.

Il sert à :

- inventorier les décisions structurantes ;
- distinguer décisions actées, proposées, dépréciées ou remplacées ;
- relier les ADR aux documents d’architecture ;
- éviter que la même question soit redécidée plusieurs fois ;
- rendre les dépendances entre décisions explicites ;
- préparer les futures évolutions V2 sans perte de contexte ;
- fournir une base auditable pour les changements majeurs.

Le principe directeur est :

> **Une décision architecturale importante doit être retrouvable, datée, motivée, reliée à ses conséquences et révisable sans effacer son historique.**

---

# 2. Pourquoi des ADR

PyAgentsKit V2 introduit des décisions dont les conséquences dépassent un fichier ou un module :

```text
V1 compatibility
DDD boundaries
Run semantics
Effect semantics
Runtime abstraction
Lease / Fencing
PostgreSQL model
Recovery
Approvals
Connectors
Public API
Migration
```

Ces décisions doivent rester compréhensibles plusieurs mois ou années après leur adoption.

---

# 3. Rôle de l’ADR

Un ADR répond à :

```text
What problem are we deciding?
What alternatives were considered?
What was decided?
Why?
What are the consequences?
What would trigger reconsideration?
```

---

# 4. Ce qui mérite un ADR

Créer un ADR lorsqu’une décision :

```text
changes dependency direction
changes domain semantics
changes public contract
changes persistence model
changes failure/recovery semantics
introduces a major technology dependency
introduces a trust boundary
affects backward compatibility
is difficult or expensive to reverse
```

---

# 5. Ce qui ne mérite pas forcément un ADR

Éviter les ADR pour :

```text
minor refactor
variable naming
private helper extraction
small test organization choice
routine bug fix
```

---

# 6. Statuts ADR

Statuts recommandés :

```text
PROPOSED
ACCEPTED
SUPERSEDED
DEPRECATED
REJECTED
EXPERIMENTAL
```

---

# 7. Signification des statuts

## PROPOSED

Décision formulée mais non encore validée.

## ACCEPTED

Décision de référence actuelle.

## SUPERSEDED

Décision remplacée par un ADR ultérieur.

## DEPRECATED

Décision encore présente pour compatibilité mais plus recommandée.

## REJECTED

Option étudiée mais non retenue.

## EXPERIMENTAL

Décision volontairement temporaire et réévaluable.

---

# 8. Convention de nommage

Format :

```text
ADR-XXXX_<SHORT_TITLE>.md
```

Exemple :

```text
ADR-0001_PYAGENTSKIT_V2_PRODUCT_BOUNDARY.md
```

---

# 9. Emplacement recommandé

```text
docs/adr/
```

Arborescence :

```text
docs/adr/
├── README.md
├── ADR-0001_PYAGENTSKIT_V2_PRODUCT_BOUNDARY.md
├── ADR-0002_DDD_HEXAGONAL_ARCHITECTURE.md
├── ADR-0003_BOUNDED_CONTEXTS.md
└── ...
```

---

# 10. Template ADR recommandé

```markdown
# ADR-XXXX — Title

Status: PROPOSED | ACCEPTED | SUPERSEDED | ...
Date:
Owners:
Related documents:
Supersedes:
Superseded by:

## Context

## Problem

## Decision

## Alternatives considered

## Consequences

### Positive

### Negative

### Risks

## Compatibility impact

## Security impact

## Operational impact

## Migration impact

## Testing / qualification

## Reconsideration triggers
```

---

# 11. Classification des ADR

Catégories proposées :

```text
STRATEGY
DOMAIN
APPLICATION
RUNTIME
EFFECTS
GOVERNANCE
COORDINATION
PERSISTENCE
SECURITY
OBSERVABILITY
CONNECTORS
CODING_AGENTS
API
MIGRATION
OPERATIONS
TESTING
```

---

# 12. Registre global

Les ADR ci-dessous constituent la cible recommandée.

---

# 13. ADR-0001 — PyAgentsKit V2 Product Boundary

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

## Décision

PyAgentsKit V2 est une :

```text
Agent Reliability Layer
```

et non :

```text
another agent framework
another LLM SDK
another workflow engine
```

## Source

```text
00
01
11
26
45
```

## Conséquence

PyAgentsKit construit les sémantiques de fiabilité et intègre les runtimes.

---

# 14. ADR-0002 — DDD + Hexagonal Architecture

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

## Décision

Architecture cible :

```text
DDD
+
Hexagonal Architecture
+
Ports & Adapters
+
Application Services
+
Explicit Composition Root
```

## Sources

```text
05
11
27
28
29
```

---

# 15. ADR-0003 — Dependency Direction

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

## Décision

```text
Bootstrap
↓
API / Adapters
↓
Application
↓
Domain
```

Le Domain ne dépend d’aucune infrastructure.

---

# 16. ADR-0004 — Bounded Context Map

**Catégorie :** DOMAIN  
**Statut recommandé :** ACCEPTED  

## Décision

Huit Bounded Contexts principaux :

```text
Execution
Effects
Governance
Coordination
Conversations
Runtime Integration
Artifacts
Audit
```

## Source

```text
27
```

---

# 17. ADR-0005 — Minimal Shared Kernel

**Catégorie :** DOMAIN  
**Statut recommandé :** ACCEPTED  

## Décision

Le Shared Kernel reste limité à :

```text
typed IDs
TenantId
CorrelationContext
Version
base DomainEvent
clock abstraction
```

Pas d’aggregate métier.

---

# 18. ADR-0006 — Run vs RuntimeInvocation

**Catégorie :** DOMAIN  
**Statut recommandé :** ACCEPTED  

## Décision

```text
Run
!=
RuntimeInvocation
```

Le Run représente l’intention durable.

RuntimeInvocation représente une tentative concrète d’exécution.

---

# 19. ADR-0007 — Session vs Conversation

**Catégorie :** DOMAIN  
**Statut recommandé :** ACCEPTED  

## Décision

```text
Session
!=
Conversation
```

Session :

```text
durable global context
```

Conversation :

```text
communication thread
```

---

# 20. ADR-0008 — RuntimeMessage vs ConversationMessage

**Catégorie :** DOMAIN  
**Statut recommandé :** ACCEPTED  

## Décision

Le Message de transport/runtime V1 n’est pas le Message métier durable V2.

---

# 21. ADR-0009 — Effect vs ToolCall

**Catégorie :** EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

```text
ToolCall
!=
Effect
```

Un Effect représente une conséquence durable réelle.

---

# 22. ADR-0010 — Effect State Machine

**Catégorie :** EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

États canoniques :

```text
NOT_STARTED
STARTED
SUCCEEDED
FAILED
UNKNOWN
RECONCILIATION_REQUIRED
```

---

# 23. ADR-0011 — UNKNOWN Is Not FAILED

**Catégorie :** EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

```text
UNKNOWN
!=
FAILED
```

Aucun retry aveugle n’est autorisé.

---

# 24. ADR-0012 — No Implicit Replay of Successful Effects

**Catégorie :** EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

Un Effect `SUCCEEDED` n’est jamais implicitement rejoué.

---

# 25. ADR-0013 — Durable Intent Before External Effect

**Catégorie :** EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

L’intention doit être persistée avant l’appel externe critique.

---

# 26. ADR-0014 — Effect Idempotency Model

**Catégorie :** EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

Idempotency basée sur :

```text
IdempotencyKey
IdempotencyScope
InputFingerprint
```

Même clé + fingerprint différent :

```text
conflict
```

---

# 27. ADR-0015 — Reconciliation as First-Class Domain Capability

**Catégorie :** EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

Créer :

```text
ReconciliationCase
ReconciliationPort
ReconciliationResult
```

et ne pas réduire la reconciliation à un retry.

---

# 28. ADR-0016 — RecoveryPlanner

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

## Décision

La reprise passe par un :

```text
RecoveryPlanner
```

produisant :

```text
RecoveryPlan
RecoveryBlocker
NextAction
```

---

# 29. ADR-0017 — Recovery Order

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

## Décision

Ordre de reprise :

```text
authoritative durable state
→ ownership
→ security
→ Effects
→ Approvals
→ runtime inspection
→ next action
```

---

# 30. ADR-0018 — WAITING Is Non-Terminal

**Catégorie :** DOMAIN  
**Statut recommandé :** ACCEPTED  

## Décision

`WAITING` est un état durable non terminal.

---

# 31. ADR-0019 — PAUSED Is Explicit

**Catégorie :** DOMAIN  
**Statut recommandé :** ACCEPTED  

## Décision

`PAUSED` est une suspension volontaire explicite.

Il ne doit pas être confondu avec `WAITING`.

---

# 32. ADR-0020 — Cancellation Is Not Rollback

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

## Décision

Annuler un Run n’annule pas automatiquement les Effects déjà produits.

---

# 33. ADR-0021 — AgentRuntimeAdapter as Runtime Boundary

**Catégorie :** RUNTIME  
**Statut recommandé :** ACCEPTED  

## Décision

Tout runtime agentique est intégré via :

```text
AgentRuntimeAdapter
```

---

# 34. ADR-0022 — Native Runner Becomes an Adapter

**Catégorie :** RUNTIME  
**Statut recommandé :** ACCEPTED  

## Décision

Le Runner V1 devient :

```text
NativeRuntimeAdapter
```

Il n’est plus le cœur conceptuel V2.

---

# 35. ADR-0023 — RuntimeHandle Is Opaque

**Catégorie :** RUNTIME  
**Statut recommandé :** ACCEPTED  

## Décision

Les handles provider/runtime restent opaques au core.

---

# 36. ADR-0024 — Runtime Capability Negotiation

**Catégorie :** RUNTIME  
**Statut recommandé :** ACCEPTED  

## Décision

Les capacités sont explicites :

```text
START
RESUME
CANCEL
STATUS
EVENT_STREAM
NATIVE_CHECKPOINT
TOOL_INTERCEPTION
...
```

---

# 37. ADR-0025 — No Runtime-Specific Conditionals in Core

**Catégorie :** RUNTIME  
**Statut recommandé :** ACCEPTED  

## Décision

Interdit :

```python
if runtime == "codex":
```

dans Domain/Application.

---

# 38. ADR-0026 — Runtime Adapter vs Model Adapter

**Catégorie :** RUNTIME  
**Statut recommandé :** ACCEPTED  

## Décision

```text
Model Adapter
!=
Agent Runtime Adapter
```

---

# 39. ADR-0027 — Runtime Adapter vs Connector

**Catégorie :** RUNTIME / CONNECTORS  
**Statut recommandé :** ACCEPTED  

## Décision

```text
RuntimeAdapter
controls an agent runtime

Connector
talks to an external business system
```

---

# 40. ADR-0028 — Provider Types Confined to Anti-Corruption Layers

**Catégorie :** RUNTIME / CONNECTORS  
**Statut recommandé :** ACCEPTED  

## Décision

Aucun type SDK provider ne franchit l’ACL vers le core.

---

# 41. ADR-0029 — Lease as Distributed Ownership Primitive

**Catégorie :** COORDINATION  
**Statut recommandé :** ACCEPTED  

## Décision

L’autorité de progression distribuée est portée par un Lease durable.

---

# 42. ADR-0030 — Fencing Tokens

**Catégorie :** COORDINATION  
**Statut recommandé :** ACCEPTED  

## Décision

Chaque takeover produit un fencing token strictement supérieur.

---

# 43. ADR-0031 — Queue Delivery Is Not Ownership

**Catégorie :** COORDINATION  
**Statut recommandé :** ACCEPTED  

## Décision

Recevoir un message de queue ne donne pas l’autorité sur le Run.

---

# 44. ADR-0032 — Heartbeat Is Not Ownership

**Catégorie :** COORDINATION  
**Statut recommandé :** ACCEPTED  

---

# 45. ADR-0033 — Safety Independent from Graceful Cleanup

**Catégorie :** COORDINATION  
**Statut recommandé :** ACCEPTED  

## Décision

La sûreté ne dépend pas d’un `release()` réussi ou d’un shutdown gracieux.

---

# 46. ADR-0034 — Database Time for Lease Expiry

**Catégorie :** COORDINATION / PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

La DB de référence fournit l’autorité temporelle pour les leases distribués.

---

# 47. ADR-0035 — PostgreSQL as Production Reference Backend

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

PostgreSQL est le backend de production de référence.

Memory/SQLite servent d’autres profils.

---

# 48. ADR-0036 — Repository vs Store

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

```text
Repository
= aggregate persistence

Store
= technical persistence
```

---

# 49. ADR-0037 — Unit of Work

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

Le Unit of Work définit la transaction locale applicative.

---

# 50. ADR-0038 — Domain Model Separate from Persistence Model

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

ORM row != Domain aggregate.

---

# 51. ADR-0039 — Optimistic Concurrency

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

Les aggregates mutables critiques utilisent une version/CAS explicite.

---

# 52. ADR-0040 — PostgreSQL Normalized V2 Model

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

La V2 sort du stockage agrégé JSONB V1 pour les états critiques et introduit des tables sémantiques normalisées.

---

# 53. ADR-0041 — JSONB Policy

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

JSONB pour :

```text
metadata
extensions
non-critical flexible payloads
```

Pas pour les états critiques structurants.

---

# 54. ADR-0042 — Effect Idempotency Enforced Physically

**Catégorie :** PERSISTENCE / EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

La DB protège l’unicité logique des Effects.

---

# 55. ADR-0043 — Lease Resource + Lease History Model

**Catégorie :** PERSISTENCE / COORDINATION  
**Statut recommandé :** ACCEPTED  

## Décision

Utiliser :

```text
lease_resources
+
leases
```

pour fencing monotone et historique.

---

# 56. ADR-0044 — Primary Reads for Safety-Critical State

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

Pas de replica laggée pour :

```text
Effect authority
Approval authority
Lease authority
Fencing
```

---

# 57. ADR-0045 — External Effects Outside DB Transactions

**Catégorie :** PERSISTENCE / EFFECTS  
**Statut recommandé :** ACCEPTED  

## Décision

Aucun appel externe critique ne doit être exécuté à l’intérieur d’une longue transaction DB.

---

# 58. ADR-0046 — Transaction Is Not Distributed Transaction

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

PostgreSQL ne garantit pas atomicité avec :

```text
GitHub
S3
runtime
payment
deployment API
```

---

# 59. ADR-0047 — Outbox Pattern

**Catégorie :** PERSISTENCE / MESSAGING  
**Statut recommandé :** ACCEPTED  

## Décision

Utiliser Outbox pour publier durablement les Integration Events.

---

# 60. ADR-0048 — Inbox Pattern

**Catégorie :** PERSISTENCE / MESSAGING  
**Statut recommandé :** ACCEPTED  

## Décision

Inbox protège les consommateurs contre redelivery/duplicate events.

---

# 61. ADR-0049 — DomainEvent vs IntegrationEvent

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

## Décision

```text
DomainEvent
!=
IntegrationEvent
```

---

# 62. ADR-0050 — DomainEvent vs RuntimeEvent vs AuditEvent

**Catégorie :** OBSERVABILITY  
**Statut recommandé :** ACCEPTED  

## Décision

```text
DomainEvent
RuntimeEvent
AuditEvent
Telemetry event
```

ont des sémantiques distinctes.

---

# 63. ADR-0051 — Audit Is Durable and Append-Oriented

**Catégorie :** OBSERVABILITY  
**Statut recommandé :** ACCEPTED  

---

# 64. ADR-0052 — Audit Is Not Telemetry

**Catégorie :** OBSERVABILITY  
**Statut recommandé :** ACCEPTED  

---

# 65. ADR-0053 — OpenTelemetry as Integration Standard

**Catégorie :** OBSERVABILITY  
**Statut recommandé :** ACCEPTED  

## Décision

Adopter OpenTelemetry derrière un port/adaptor.

---

# 66. ADR-0054 — Health vs Readiness

**Catégorie :** OPERATIONS  
**Statut recommandé :** ACCEPTED  

## Décision

```text
liveness
!=
readiness
```

---

# 67. ADR-0055 — Fail-Closed Protected Effects

**Catégorie :** SECURITY  
**Statut recommandé :** ACCEPTED  

## Décision

Si l’autorité nécessaire ne peut pas être prouvée :

```text
do not execute Protected Effect
```

---

# 68. ADR-0056 — Authentication vs Authorization vs Approval

**Catégorie :** SECURITY / GOVERNANCE  
**Statut recommandé :** ACCEPTED  

## Décision

Trois concepts distincts.

---

# 69. ADR-0057 — Principal vs Actor

**Catégorie :** SECURITY / DOMAIN  
**Statut recommandé :** ACCEPTED  

## Décision

```text
Actor
= interaction identity

Principal
= security authority identity
```

---

# 70. ADR-0058 — Runtime Output Cannot Grant Authority

**Catégorie :** SECURITY  
**Statut recommandé :** ACCEPTED  

---

# 71. ADR-0059 — Secret Externalization

**Catégorie :** SECURITY  
**Statut recommandé :** ACCEPTED  

## Décision

Le core manipule des `SecretReference`, pas des secrets persistés dans le Domain.

---

# 72. ADR-0060 — Tenant Isolation

**Catégorie :** SECURITY / PERSISTENCE  
**Statut recommandé :** ACCEPTED  

## Décision

Tenant scoping explicite dans les contrats et contraintes.

---

# 73. ADR-0061 — Approval as Durable Aggregate

**Catégorie :** GOVERNANCE  
**Statut recommandé :** ACCEPTED  

---

# 74. ADR-0062 — Approval Scope Bound to Fingerprint

**Catégorie :** GOVERNANCE  
**Statut recommandé :** ACCEPTED  

---

# 75. ADR-0063 — Approval Decision vs Consumption

**Catégorie :** GOVERNANCE  
**Statut recommandé :** ACCEPTED  

## Décision

`CLAIMED` / `EXECUTED` ne doivent pas faire partie du cœur du lifecycle de décision V2.

---

# 76. ADR-0064 — Approval Revalidation after Recovery

**Catégorie :** GOVERNANCE  
**Statut recommandé :** ACCEPTED  

---

# 77. ADR-0065 — Conversation Message Does Not Imply Approval

**Catégorie :** GOVERNANCE / CONVERSATIONS  
**Statut recommandé :** ACCEPTED  

---

# 78. ADR-0066 — Connector Model

**Catégorie :** CONNECTORS  
**Statut recommandé :** ACCEPTED  

## Décision

Les external systems sont intégrés par :

```text
Connector
ConnectorDescriptor
ConnectorRegistry
```

---

# 79. ADR-0067 — Connector Capability Negotiation

**Catégorie :** CONNECTORS  
**Statut recommandé :** ACCEPTED  

---

# 80. ADR-0068 — Connector-Specific Reconciliation

**Catégorie :** CONNECTORS  
**Statut recommandé :** ACCEPTED  

---

# 81. ADR-0069 — Generic HTTP Does Not Define Provider Semantics

**Catégorie :** CONNECTORS  
**Statut recommandé :** ACCEPTED  

---

# 82. ADR-0070 — No Silent Provider Fallback

**Catégorie :** CONNECTORS / RUNTIME  
**Statut recommandé :** ACCEPTED  

---

# 83. ADR-0071 — Coding Agents as Runtime Adapters

**Catégorie :** CODING_AGENTS  
**Statut recommandé :** ACCEPTED  

## Décision

Codex, Claude Code, OpenCode sont modélisés comme runtimes agentiques.

---

# 84. ADR-0072 — Local Work vs Remote Persistent Effects

**Catégorie :** CODING_AGENTS  
**Statut recommandé :** ACCEPTED  

## Décision

```text
local edit
!=
remote mutation
```

---

# 85. ADR-0073 — Git Push / PR / Deploy as Effects

**Catégorie :** CODING_AGENTS / EFFECTS  
**Statut recommandé :** ACCEPTED  

---

# 86. ADR-0074 — Workspace Isolation

**Catégorie :** CODING_AGENTS / SECURITY  
**Statut recommandé :** ACCEPTED  

---

# 87. ADR-0075 — Repository Content Is Untrusted

**Catégorie :** CODING_AGENTS / SECURITY  
**Statut recommandé :** ACCEPTED  

---

# 88. ADR-0076 — Command Execution Is a Security Boundary

**Catégorie :** CODING_AGENTS / SECURITY  
**Statut recommandé :** ACCEPTED  

---

# 89. ADR-0077 — Public API Uses Views, Not ORM/Domain Internals

**Catégorie :** API  
**Statut recommandé :** ACCEPTED  

---

# 90. ADR-0078 — Async-First API

**Catégorie :** API  
**Statut recommandé :** ACCEPTED  

## Décision

L’API canonique est async-first.

Une façade sync peut exister sans différence de sémantique.

---

# 91. ADR-0079 — Opaque Public IDs

**Catégorie :** API  
**Statut recommandé :** ACCEPTED  

---

# 92. ADR-0080 — Stable Error Codes

**Catégorie :** API  
**Statut recommandé :** ACCEPTED  

---

# 93. ADR-0081 — Public Events Are Versioned

**Catégorie :** API  
**Statut recommandé :** ACCEPTED  

---

# 94. ADR-0082 — Client Timeout Is Not Operation Failure

**Catégorie :** API / EFFECTS  
**Statut recommandé :** ACCEPTED  

---

# 95. ADR-0083 — Safety Semantics Are Public Contract

**Catégorie :** API  
**Statut recommandé :** ACCEPTED  

---

# 96. ADR-0084 — V1 Compatibility Boundary

**Catégorie :** MIGRATION  
**Statut recommandé :** ACCEPTED  

## Décision

La V1 est encapsulée derrière une boundary de compatibilité.

La V2 ne reproduit pas nécessairement ses internals.

---

# 97. ADR-0085 — Strangler Migration V1 → V2

**Catégorie :** MIGRATION  
**Statut recommandé :** ACCEPTED  

---

# 98. ADR-0086 — No Big-Bang Rewrite

**Catégorie :** MIGRATION  
**Statut recommandé :** ACCEPTED  

---

# 99. ADR-0087 — V1 and V2 Types May Coexist

**Catégorie :** MIGRATION  
**Statut recommandé :** ACCEPTED  

## Décision

Les types V1 et V2 portant des significations différentes peuvent coexister temporairement.

---

# 100. ADR-0088 — Preserve Ambiguity During Migration

**Catégorie :** MIGRATION  
**Statut recommandé :** ACCEPTED  

## Décision

Une donnée V1 ambiguë reste ambiguë en V2.

---

# 101. ADR-0089 — Expand / Backfill / Verify / Switch / Contract

**Catégorie :** MIGRATION / PERSISTENCE  
**Statut recommandé :** ACCEPTED  

---

# 102. ADR-0090 — Forward-Fix Preferred after Cutover

**Catégorie :** MIGRATION  
**Statut recommandé :** ACCEPTED  

---

# 103. ADR-0091 — Fencing Migration Must Preserve Monotonicity

**Catégorie :** MIGRATION / COORDINATION  
**Statut recommandé :** ACCEPTED  

---

# 104. ADR-0092 — V1 Runner Maintained as Native Runtime

**Catégorie :** MIGRATION / RUNTIME  
**Statut recommandé :** ACCEPTED  

---

# 105. ADR-0093 — Build Semantics, Integrate Infrastructure

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

## Décision

```text
Build semantics.
Integrate infrastructure.
```

---

# 106. ADR-0094 — PostgreSQL, Object Storage, IAM, Broker Are Commodities

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

## Décision

PyAgentsKit n’implémente pas ces systèmes ; il les consomme derrière des ports.

---

# 107. ADR-0095 — Do Not Build Generic Scheduler

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

---

# 108. ADR-0096 — Do Not Build Generic Workflow Engine

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

---

# 109. ADR-0097 — Do Not Build IAM

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

---

# 110. ADR-0098 — Do Not Build Observability Backend

**Catégorie :** STRATEGY  
**Statut recommandé :** ACCEPTED  

---

# 111. ADR-0099 — Core Install Remains Lightweight

**Catégorie :** STRATEGY / PACKAGING  
**Statut recommandé :** ACCEPTED  

## Décision

Les infrastructures lourdes restent dans des extras optionnels.

---

# 112. ADR-0100 — Adapter Plugins Are Explicitly Registered

**Catégorie :** RUNTIME / CONNECTORS  
**Statut recommandé :** ACCEPTED  

---

# 113. ADR-0101 — No Hidden Global Registries

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

---

# 114. ADR-0102 — Bootstrap Is the Composition Root

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

---

# 115. ADR-0103 — Commands vs Queries

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

---

# 116. ADR-0104 — Lightweight CQRS

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

## Décision

Commands sur domaine autoritatif.

Queries via read models optimisés.

Pas de full event sourcing imposé.

---

# 117. ADR-0105 — No Generic Command Bus Initially

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

---

# 118. ADR-0106 — Explicit Use-Case Orchestration over Generic Workflow Engine

**Catégorie :** APPLICATION  
**Statut recommandé :** ACCEPTED  

---

# 119. ADR-0107 — Repository per Aggregate

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

---

# 120. ADR-0108 — No Generic CRUD Repository as Primary Contract

**Catégorie :** PERSISTENCE  
**Statut recommandé :** ACCEPTED  

---

# 121. ADR-0109 — Contract Tests for Ports

**Catégorie :** TESTING  
**Statut recommandé :** ACCEPTED  

---

# 122. ADR-0110 — Real PostgreSQL Required for Production Qualification

**Catégorie :** TESTING / PERSISTENCE  
**Statut recommandé :** ACCEPTED  

---

# 123. ADR-0111 — Multi-Process Required for Lease/Fencing Qualification

**Catégorie :** TESTING / COORDINATION  
**Statut recommandé :** ACCEPTED  

---

# 124. ADR-0112 — Fault Injection for Effect Crash Windows

**Catégorie :** TESTING / EFFECTS  
**Statut recommandé :** ACCEPTED  

---

# 125. ADR-0113 — Restore/PITR Requires Safety Re-entry Gate

**Catégorie :** OPERATIONS / PERSISTENCE  
**Statut recommandé :** ACCEPTED  

---

# 126. ADR-0114 — Graceful Shutdown Is Optimization, Not Safety Primitive

**Catégorie :** OPERATIONS  
**Statut recommandé :** ACCEPTED  

---

# 127. ADR-0115 — Protected Effects Freeze / Kill Switch

**Catégorie :** OPERATIONS / SECURITY  
**Statut recommandé :** ACCEPTED  

---

# 128. ADR-0116 — Manual Intervention Is a Valid Recovery Outcome

**Catégorie :** OPERATIONS / RECOVERY  
**Statut recommandé :** ACCEPTED  

---

# 129. ADR-0117 — Operational Read Models Are Non-Authoritative

**Catégorie :** OPERATIONS / APPLICATION  
**Statut recommandé :** ACCEPTED  

---

# 130. ADR-0118 — No Safety Claim Based Only on Mocks

**Catégorie :** TESTING  
**Statut recommandé :** ACCEPTED  

---

# 131. ADR-0119 — Architecture Rules Are CI-Enforced

**Catégorie :** TESTING / ARCHITECTURE  
**Statut recommandé :** ACCEPTED  

---

# 132. ADR-0120 — import-linter or Equivalent

**Catégorie :** ARCHITECTURE  
**Statut recommandé :** PROPOSED / ACCEPTED after tool choice  

## Décision

Utiliser un contrôle statique de dépendances.

L’outil précis peut évoluer.

---

# 133. ADR groups

Pour faciliter la lecture :

```text
0001–0019  Product / Domain
0020–0028  Application / Runtime
0029–0034  Coordination
0035–0048  Persistence
0049–0054  Events / Observability / Ops
0055–0065  Security / Governance
0066–0070  Connectors
0071–0076  Coding Agents
0077–0083  Public API
0084–0092  Migration
0093–0100  Build vs Buy / Packaging
0101–0108  Application / Repository patterns
0109–0120  Testing / Operations / Enforcement
```

---

# 134. ADR priority levels

## P0 — Must exist before implementation

```text
ADR-0001
ADR-0002
ADR-0003
ADR-0004
ADR-0006
ADR-0007
ADR-0009
ADR-0010
ADR-0011
ADR-0016
ADR-0021
ADR-0022
ADR-0029
ADR-0030
ADR-0035
ADR-0036
ADR-0037
ADR-0040
ADR-0056
ADR-0084
ADR-0085
```

---

# 135. P1 — Before V2 beta

```text
Approval family
Connector family
Audit/Event family
Coding agent family
Public API family
Outbox/Inbox
Security
```

---

# 136. P2 — Before V2 stable

```text
operations
qualification
restore
packaging
plugin ecosystem
advanced policies
```

---

# 137. Recommended first ADR batch

Créer en premier :

```text
ADR-0001 V2 Product Boundary
ADR-0002 DDD + Hexagonal Architecture
ADR-0003 Dependency Direction
ADR-0004 Bounded Context Map
ADR-0006 Run vs RuntimeInvocation
ADR-0007 Session vs Conversation
ADR-0009 Effect vs ToolCall
ADR-0010 Effect State Machine
ADR-0021 AgentRuntimeAdapter
ADR-0022 Native Runner Adapter
ADR-0029 Lease
ADR-0030 Fencing
```

---

# 138. Second ADR batch

```text
ADR-0035 PostgreSQL reference
ADR-0036 Repository vs Store
ADR-0037 UnitOfWork
ADR-0040 Normalized V2 model
ADR-0047 Outbox
ADR-0048 Inbox
ADR-0056 AuthN/AuthZ/Approval
ADR-0061 Approval Aggregate
ADR-0084 V1 compatibility
ADR-0085 Strangler migration
```

---

# 139. Third ADR batch

```text
Runtime capabilities
Connectors
Coding agents
Public API
Audit/Telemetry
Testing/qualification
```

---

# 140. ADR dependency graph

```text
ADR-0001 Product Boundary
        │
        ▼
ADR-0002 DDD/Hexagonal
        │
        ├────────► ADR-0004 Bounded Contexts
        │
        └────────► ADR-0003 Dependency Direction
                         │
                         ▼
                  Ports / Adapters decisions

ADR-0006 Run vs Invocation
        │
        ├────────► Recovery
        └────────► Runtime Adapter

ADR-0009 Effect vs ToolCall
        │
        ├────────► Effect State Machine
        ├────────► Reconciliation
        └────────► Coding Effects

ADR-0029 Lease
        │
        └────────► ADR-0030 Fencing

ADR-0035 PostgreSQL
        │
        ├────────► Repository/UoW
        ├────────► Normalized Model
        └────────► Outbox/Inbox

ADR-0084 V1 Compatibility
        │
        └────────► ADR-0085 Strangler Migration
```

---

# 141. ADR supersession policy

Un ADR n’est jamais supprimé lorsqu’il est remplacé.

Il passe :

```text
SUPERSEDED
```

et référence son successeur.

---

# 142. ADR rejection policy

Une option rejetée peut conserver son ADR si la discussion est structurante.

Statut :

```text
REJECTED
```

---

# 143. ADR reconsideration

Chaque ADR doit contenir :

```text
Reconsideration triggers
```

Exemples :

```text
PostgreSQL no longer meets scale needs
runtime adapters require capabilities not representable
multi-region ownership becomes mandatory
public API constraints evolve
```

---

# 144. ADR and code linkage

Les PRs importantes devraient référencer :

```text
ADR-XXXX
```

dans :

```text
PR description
commit message if useful
docs
tests
```

---

# 145. ADR and test linkage

Pour les décisions safety-critical :

```text
ADR
→ invariant
→ test
```

Exemple :

```text
ADR-0011 UNKNOWN != FAILED
→ EFF-INV-02
→ test_unknown_is_not_retried_as_failed
```

---

# 146. ADR and requirement linkage

Idéalement :

```text
Requirement
→ ADR
→ implementation
→ test
```

---

# 147. ADR and migration linkage

Chaque changement de sémantique V1/V2 doit référencer :

```text
migration rule
compatibility impact
```

---

# 148. ADR and public API linkage

ADR public API doit préciser :

```text
SemVer impact
deprecation
error compatibility
serialization impact
```

---

# 149. ADR and security linkage

Les décisions touchant :

```text
authority
identity
secrets
tenant isolation
remote execution
```

doivent inclure une section Security Impact.

---

# 150. ADR and operational impact

Décisions concernant :

```text
leases
fencing
PostgreSQL
Outbox
worker lifecycle
```

doivent inclure :

```text
monitoring
runbook
failure mode
```

---

# 151. ADR and cost impact

Pour Build vs Buy :

```text
implementation cost
maintenance cost
operational cost
vendor lock-in
```

doivent être explicités.

---

# 152. ADR ownership

Chaque ADR devrait indiquer :

```text
Owner
Reviewers
```

au minimum pour les P0.

---

# 153. ADR review discipline

Une décision P0 ne passe à `ACCEPTED` qu’après :

```text
architecture review
compatibility review
safety review if relevant
```

---

# 154. ADR immutability

Une fois ACCEPTED :

```text
do not silently rewrite history
```

Pour changement de décision :

```text
new ADR
supersedes old ADR
```

---

# 155. ADR versioning

L’ADR lui-même ne nécessite pas forcément SemVer.

L’historique Git suffit si statut/date explicites.

---

# 156. ADR numbering

Les numéros ne sont pas réutilisés.

---

# 157. ADR documentation index

Créer :

```text
docs/adr/README.md
```

contenant :

```text
ID
Title
Status
Date
Category
Superseded by
```

---

# 158. Generated ADR index

Ce document `46` peut servir de source conceptuelle.

Un script pourra générer un index à partir des headers des fichiers ADR.

---

# 159. Candidate tooling

Outils possibles :

```text
simple Markdown
adr-tools
custom Python script
MkDocs integration
```

Aucun tooling lourd requis.

---

# 160. ADR checks in CI

CI peut vérifier :

```text
unique IDs
valid status
required sections
valid supersedes links
filename format
```

---

# 161. ADR link checker

Les références croisées doivent rester valides.

---

# 162. ADR linting

Règles simples :

```text
Status present
Date present
Decision section present
Consequences present
```

---

# 163. ADR architecture impact labels

Option :

```text
BREAKING
NON_BREAKING
INTERNAL
MIGRATION_REQUIRED
SECURITY_CRITICAL
SAFETY_CRITICAL
```

---

# 164. High-risk ADRs

Les ADR les plus critiques sont :

```text
Effect state machine
UNKNOWN semantics
Lease
Fencing
Recovery
Approval
PostgreSQL authority
V1 migration
```

---

# 165. ADR stability

Certains ADR doivent devenir quasi constitutionnels :

```text
UNKNOWN != FAILED
SUCCEEDED Effect not replayed
stale fencing rejected
Approval != Authorization
Run != RuntimeInvocation
```

---

# 166. ADR anti-pattern — decision without alternatives

Un ADR ne doit pas seulement dire :

```text
"We use PostgreSQL."
```

Il doit expliquer :

```text
why
alternatives
consequences
```

---

# 167. ADR anti-pattern — documenting implementation detail

Éviter ADR :

```text
Use variable name foo
```

---

# 168. ADR anti-pattern — no consequences

Toute décision a un coût.

---

# 169. ADR anti-pattern — retroactive fiction

Ne pas prétendre qu’une décision historique a été formellement prise si ce n’était pas le cas.

Marquer :

```text
Retrospective ADR
```

si nécessaire.

---

# 170. Retrospective ADRs

Beaucoup de décisions V1 peuvent être documentées a posteriori.

Exemples :

```text
PostgreSQL production backend
Effect UNKNOWN
Lease/Fencing
V1 API freeze
```

---

# 171. V1 retrospective ADR namespace

Option :

```text
ADR-V1-...
```

mais recommandation :

garder une numérotation unique et indiquer :

```text
Retrospective: yes
```

---

# 172. V2 ADR timeline

Avant `2.0.0a1` :

```text
P0 Domain + Strategy ADRs
```

Avant `2.0.0a2` :

```text
Runtime ADRs
```

Avant `2.0.0a3` :

```text
Effect/Recovery ADRs
```

Avant `2.0.0a4` :

```text
Persistence ADRs
```

Avant beta :

```text
Governance/Audit/Connectors/Coding
```

Avant RC :

```text
API/Migration
```

---

# 173. ADR completeness metric

On peut suivre :

```text
P0 decisions documented / P0 decisions identified
```

Objectif avant alpha :

```text
100 %
```

---

# 174. ADR status dashboard

Exemple :

```text
Accepted
Proposed
Experimental
Superseded
Rejected
```

---

# 175. Initial status recommendation

La majorité des décisions décrites dans les documents 00→32 sont déjà suffisamment consolidées pour être :

```text
ACCEPTED
```

après formalisation individuelle.

Les choix d’outil spécifiques restent :

```text
PROPOSED
```

jusqu’à validation.

---

# 176. Decisions intentionally left open

À ne pas figer prématurément :

```text
exact ORM vs raw SQL choice
exact HTTP framework
exact import-linter equivalent
exact plugin discovery mechanism
exact first external general-purpose runtime
exact broker technology
exact secrets manager
```

---

# 177. Open ADR candidates

Créer des ADR `PROPOSED` pour :

```text
ORM strategy
schema migration tool
first external runtime
plugin packaging
HTTP adapter framework
multi-region strategy
```

---

# 178. ADR-0121 — ORM / SQL Strategy

**Catégorie :** PERSISTENCE  
**Statut recommandé :** PROPOSED  

Options :

```text
raw psycopg
SQLAlchemy Core
SQLAlchemy ORM
hybrid
```

---

# 179. ADR-0122 — Migration Tooling

**Catégorie :** PERSISTENCE  
**Statut recommandé :** PROPOSED  

Options :

```text
Alembic
custom SQL migration runner
other
```

---

# 180. ADR-0123 — First External General-Purpose Runtime

**Catégorie :** RUNTIME  
**Statut recommandé :** PROPOSED  

Candidats :

```text
LangGraph
PydanticAI
OpenAI Agents SDK
```

---

# 181. ADR-0124 — First Coding Runtime

**Catégorie :** CODING_AGENTS  
**Statut recommandé :** PROPOSED  

Candidats :

```text
Codex
Claude Code
OpenCode
```

---

# 182. ADR-0125 — First External Connector

**Catégorie :** CONNECTORS  
**Statut recommandé :** PROPOSED  

Recommandation probable :

```text
GitHub
```

car utile pour coding-agent scenarios.

---

# 183. ADR-0126 — HTTP API Framework

**Catégorie :** API  
**Statut recommandé :** PROPOSED  

Ne pas figer avant besoin.

---

# 184. ADR-0127 — Plugin Discovery

**Catégorie :** PACKAGING  
**Statut recommandé :** PROPOSED  

Options :

```text
explicit registration only
Python entry points
hybrid
```

---

# 185. ADR-0128 — Multi-Region Coordination

**Catégorie :** COORDINATION  
**Statut recommandé :** EXPERIMENTAL / FUTURE  

Non nécessaire pour V2 initiale.

---

# 186. ADR-0129 — Event Broker Reference

**Catégorie :** MESSAGING  
**Statut recommandé :** PROPOSED / FUTURE  

Le core doit rester broker-neutral.

---

# 187. ADR-0130 — Secrets Manager Reference Adapter

**Catégorie :** SECURITY  
**Statut recommandé :** PROPOSED  

---

# 188. ADR-0131 — Policy Engine Reference Adapter

**Catégorie :** SECURITY  
**Statut recommandé :** PROPOSED  

---

# 189. ADR-0132 — RLS as Defense-in-Depth

**Catégorie :** SECURITY / PERSISTENCE  
**Statut recommandé :** PROPOSED  

---

# 190. ADR-0133 — UUID Strategy

**Catégorie :** DOMAIN / PERSISTENCE  
**Statut recommandé :** PROPOSED  

Candidats :

```text
UUID4
UUID7
provider-neutral typed UUID wrapper
```

---

# 191. ADR-0134 — Domain Modeling Library

**Catégorie :** DOMAIN  
**Statut recommandé :** PROPOSED  

Question :

```text
dataclasses
Pydantic
attrs
hybrid
```

Le choix ne doit pas contaminer les frontières.

---

# 192. ADR-0135 — Public Serialization Model

**Catégorie :** API  
**Statut recommandé :** PROPOSED  

---

# 193. ADR-0136 — Packaging Extras

**Catégorie :** PACKAGING  
**Statut recommandé :** PROPOSED  

Exemples :

```text
postgres
s3
azure
langgraph
codex
opentelemetry
```

---

# 194. ADR-0137 — Adapter Qualification Levels

**Catégorie :** TESTING  
**Statut recommandé :** ACCEPTED  

Niveaux :

```text
L0 fake
L1 contract
L2 integration
L3 failure
L4 production qualified
```

---

# 195. ADR-0138 — Public Stability Levels

**Catégorie :** API  
**Statut recommandé :** ACCEPTED  

```text
EXPERIMENTAL
BETA
STABLE
DEPRECATED
```

---

# 196. ADR-0139 — V2 Root Export Policy

**Catégorie :** API / PACKAGING  
**Statut recommandé :** ACCEPTED  

Décision :

```text
keep root package small
prefer namespaced public API
```

---

# 197. ADR-0140 — V1 Public API Freeze

**Catégorie :** MIGRATION / API  
**Statut recommandé :** ACCEPTED  

Maintenir le contrat V1 pendant 1.6.x.

---

# 198. Source documents mapping

| Document | ADR families |
|---|---|
| 00–01 | Product boundary / strategy |
| 05 | Architectural principles |
| 06–10 | Domain semantics |
| 11 | Overall architecture |
| 12 | Runtime adapter |
| 13 | Effects |
| 14 | Durable execution |
| 15 | Coordination |
| 16 | Persistence |
| 17 | Governance |
| 18–19 | Security / threat |
| 20 | Observability / Audit |
| 21 | Coding agents |
| 22 | Connectors |
| 23 | Public API |
| 24 | PostgreSQL |
| 25 | Failure / Recovery |
| 26 | V2 implementation plan |
| 27 | Bounded Contexts |
| 28 | Ports & Adapters |
| 29 | Dependency rules |
| 30 | Migration |
| 31 | Application services |
| 32 | Repositories/UoW |
| 45 | Build vs Buy vs Integrate |

---

# 199. Traceability example

```text
Requirement:
No duplicate critical external effect

↓
ADR-0012 No implicit replay
ADR-0014 Effect idempotency
ADR-0042 DB uniqueness

↓
Implementation:
EffectGateway
EffectRepository

↓
Tests:
W1–W5 crash-window tests
idempotency conflict tests
SIGKILL recovery tests
```

---

# 200. Decision review workflow

```text
Issue/problem identified
↓
ADR PROPOSED
↓
Alternatives evaluated
↓
Architecture review
↓
ACCEPTED
↓
Implementation
↓
Qualification
↓
Possible future SUPERSEDED
```

---

# 201. ADR pull request policy

Pour décisions importantes :

```text
ADR PR
before or together with
implementation PR
```

---

# 202. Emergency exception

En incident production :

```text
fix first if necessary
retrospective ADR immediately after
```

si l’impact architectural le justifie.

---

# 203. ADR security review triggers

Revue sécurité obligatoire si décision touche :

```text
credentials
authorization
remote code execution
tenant isolation
external writes
sandbox
supply chain
```

---

# 204. ADR reliability review triggers

Revue reliability obligatoire si décision touche :

```text
Effect states
retry
recovery
lease
fencing
transactions
outbox
migration
```

---

# 205. ADR compatibility review triggers

Revue compatibilité obligatoire si décision touche :

```text
public imports
serialized contracts
events
DB migration
V1 behavior
```

---

# 206. Architecture Constitution

Les ADR suivants peuvent être considérés comme constitutionnels :

```text
ADR-0001 V2 Product Boundary
ADR-0002 DDD + Hexagonal
ADR-0003 Dependency Direction
ADR-0006 Run != RuntimeInvocation
ADR-0007 Session != Conversation
ADR-0009 ToolCall != Effect
ADR-0011 UNKNOWN != FAILED
ADR-0012 No implicit Effect replay
ADR-0030 Fencing tokens
ADR-0056 AuthN != AuthZ != Approval
ADR-0084 V1 compatibility boundary
ADR-0093 Build semantics, integrate infrastructure
```

Toute remise en cause doit être exceptionnelle et explicite.

---

# 207. Reconsideration triggers — product boundary

Réévaluer seulement si :

```text
market proves reliability layer alone insufficient
runtime ecosystem converges drastically
users require first-class agent construction semantics
```

Même dans ce cas, ne pas casser les invariants de reliability.

---

# 208. Reconsideration triggers — PostgreSQL

Réévaluer si :

```text
multi-region latency becomes core requirement
throughput exceeds practical PostgreSQL envelope
tenant isolation mandates physical split
```

---

# 209. Reconsideration triggers — RuntimeAdapter

Réévaluer si :

```text
runtime capabilities cannot be represented honestly
control model differs too much
```

Préférer extension capability-aware à provider conditionals.

---

# 210. Reconsideration triggers — Effect model

Très élevé.

Seulement si :

```text
new evidence shows model cannot represent real ambiguity safely
```

---

# 211. ADR quality criteria

Un bon ADR :

```text
specific
short enough to review
deep enough to explain trade-offs
honest about disadvantages
linked to implementation
```

---

# 212. ADR anti-duplication

Avant nouveau ADR :

```text
search index
check supersession
check open proposed ADRs
```

---

# 213. ADR index ownership

Ce document doit être mis à jour lorsqu’un ADR :

```text
is created
changes status
is superseded
```

---

# 214. Automation candidate

Un script peut scanner :

```text
docs/adr/ADR-*.md
```

et générer :

```text
README index
status summary
broken link report
```

---

# 215. Suggested metadata block

Exemple :

```yaml
adr: ADR-0021
title: AgentRuntimeAdapter as Runtime Boundary
status: ACCEPTED
date: 2026-10-21
category: RUNTIME
owners:
  - architecture
supersedes: []
superseded_by: null
```

YAML frontmatter facultatif mais utile si index auto-généré.

---

# 216. No external database required

Le système ADR doit rester :

```text
Git-native
Markdown-first
reviewable in PR
```

---

# 217. Relation avec le code

Les ADR ne doivent pas devenir une seconde documentation détaillée du code.

Ils décrivent :

```text
why
decision
trade-offs
```

Les documents 00→48 décrivent plus largement :

```text
what
how
target model
```

---

# 218. Relation avec les ADR et les docs d’architecture

```text
Architecture doc
= complete model/specification

ADR
= decision and rationale
```

---

# 219. Relation avec les runbooks

```text
ADR
= why system behaves this way

Runbook
= what operator does during incident
```

---

# 220. Relation avec tests

```text
ADR
= design intent

Tests
= executable evidence
```

---

# 221. Acceptance Criteria

Le système ADR est correctement mis en place si :

1. chaque décision P0 possède un ADR ;
2. chaque ADR a un statut explicite ;
3. aucun ADR accepté n’est supprimé silencieusement ;
4. les ADR superseded pointent vers leur remplaçant ;
5. les PR structurantes référencent leur ADR ;
6. les décisions safety-critical sont reliées à des invariants/tests ;
7. les décisions V1/V2 incluent leur impact migration ;
8. les choix d’outil non encore actés restent `PROPOSED` ;
9. les ADR sont stockés dans Git ;
10. un index est maintenu automatiquement ou semi-automatiquement.

---

# 222. Definition of Done

`../architecture/46_PYAGENTSKIT_ARCHITECTURE_DECISION_RECORDS_INDEX.md` est considéré mature lorsque :

1. les ADR P0 sont créés ;
2. le dossier `docs/adr/` existe ;
3. le template ADR est versionné ;
4. les statuts sont normalisés ;
5. les catégories sont normalisées ;
6. les relations supersedes/superseded-by sont supportées ;
7. les PR templates demandent l’ADR applicable ;
8. les décisions safety-critical ont des liens vers tests ;
9. CI valide les fichiers ADR ;
10. l’index est intégré à la documentation projet.

---

# 223. Priorité immédiate

Le premier lot recommandé est :

```text
ADR-0001 Product Boundary
ADR-0002 DDD + Hexagonal
ADR-0003 Dependency Direction
ADR-0004 Bounded Contexts
ADR-0006 Run vs RuntimeInvocation
ADR-0007 Session vs Conversation
ADR-0009 Effect vs ToolCall
ADR-0010 Effect State Machine
ADR-0021 AgentRuntimeAdapter
ADR-0022 Native Runtime Adapter
ADR-0029 Lease
ADR-0030 Fencing
```

Ce lot verrouille les fondations avant implémentation V2.

---

# 224. Résumé

L’index ADR transforme les décisions PyAgentsKit en une mémoire architecturale durable.

Le modèle est :

```text
PROBLEM
   ↓
ADR
   ↓
DECISION
   ↓
IMPLEMENTATION
   ↓
TEST / QUALIFICATION
   ↓
OPERATIONS
```

Les ADR ne doivent pas enregistrer chaque détail.

Ils doivent protéger les décisions qui seraient coûteuses, risquées ou ambiguës à redécouvrir.

Le principe fondamental est :

> **Le code montre ce que PyAgentsKit fait aujourd’hui ; les ADR expliquent pourquoi il a été conçu ainsi, quelles alternatives ont été rejetées et dans quelles conditions cette décision pourra un jour être remise en cause.**
