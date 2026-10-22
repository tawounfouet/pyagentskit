# PyAgentsKit — Build vs Buy vs Integrate

**Document :** `../strategy/45_PYAGENTSKIT_BUILD_VS_BUY_VS_INTEGRATE.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Strategic Architecture Decision Framework  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
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
- `../architecture/46_PYAGENTSKIT_ARCHITECTURE_DECISION_RECORDS_INDEX.md`
- `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`
- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`
- `../strategy/PYAGENTSKIT_EXISTING_VS_TARGET_GAP_ANALYSIS_2026-10-21.md`
- `../architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`

---

# 1. Objet

Ce document définit la stratégie **Build vs Buy vs Integrate** de PyAgentsKit V2.

Il répond à une question structurante :

> **Quelles capacités PyAgentsKit doit-il réellement posséder et implémenter, et quelles capacités doivent rester externes derrière des Ports & Adapters ?**

L’objectif est d’éviter deux dérives opposées :

```text
1. reconstruire des commodités déjà matures ;
2. externaliser les sémantiques qui constituent précisément la valeur de PyAgentsKit.
```

Le principe directeur est :

> **Build the semantics. Integrate the infrastructure. Buy or reuse the commodities.**

---

# 2. Définitions

## BUILD

PyAgentsKit implémente et possède directement la sémantique.

On choisit BUILD lorsqu’une capacité :

```text
définit le produit ;
porte un invariant de sûreté ;
doit rester framework-neutral ;
doit être cohérente entre tous les adapters ;
est impossible à déléguer sans perdre le contrôle du modèle.
```

---

# 3. BUY / USE

PyAgentsKit consomme une technologie existante sans tenter d’en reproduire le moteur.

Exemples :

```text
PostgreSQL
S3
Azure Blob Storage
OpenTelemetry
OIDC provider
```

BUY ne signifie pas nécessairement « logiciel commercial ».

Cela signifie :

```text
use an existing commodity capability
```

---

# 4. INTEGRATE

PyAgentsKit définit son propre contrat puis implémente un adapter vers un système externe.

Pattern :

```text
PyAgentsKit semantic contract
↓
Port
↓
Adapter
↓
External implementation
```

INTEGRATE est le choix privilégié lorsqu’une capacité externe est indispensable mais ne doit pas gouverner le modèle PyAgentsKit.

---

# 5. BUILD + INTEGRATE

Certaines capacités nécessitent les deux.

Exemple :

```text
BUILD
AgentRuntimeAdapter semantics

INTEGRATE
LangGraph / Codex / Claude Code / PydanticAI
```

---

# 6. Question stratégique

PyAgentsKit ne doit pas chercher à devenir :

```text
everything agents need
```

Il doit devenir :

```text
the reliability semantics agents can rely on
```

---

# 7. Différenciateur produit

Le différenciateur cible est :

```text
Durable Run semantics
Effect safety
Recovery
Approval governance
Lease/Fencing
Auditability
Runtime neutrality
Connector safety
```

Ces capacités sont des candidats BUILD.

---

# 8. Commodités

Sont plutôt des commodités :

```text
database engine
object storage
message broker
identity provider
metrics backend
trace backend
secret manager
HTTP transport
container scheduler
```

Ces capacités sont des candidats BUY/INTEGRATE.

---

# 9. Matrice principale

| Capability | BUILD | BUY/USE | INTEGRATE | Decision |
|---|---:|---:|---:|---|
| Run semantics | ✓ |  |  | BUILD |
| RuntimeInvocation model | ✓ |  |  | BUILD |
| RecoveryPlanner | ✓ |  |  | BUILD |
| Effect state machine | ✓ |  |  | BUILD |
| Idempotency semantics | ✓ |  | ✓ | BUILD + INTEGRATE |
| Reconciliation model | ✓ |  | ✓ | BUILD + INTEGRATE |
| Approval model | ✓ |  | ✓ | BUILD + INTEGRATE |
| Lease/Fencing semantics | ✓ |  | ✓ | BUILD + INTEGRATE |
| Runtime adapter contract | ✓ |  | ✓ | BUILD + INTEGRATE |
| PostgreSQL engine |  | ✓ | ✓ | USE + INTEGRATE |
| Object storage |  | ✓ | ✓ | USE + INTEGRATE |
| IAM / OIDC |  | ✓ | ✓ | USE + INTEGRATE |
| Secret management |  | ✓ | ✓ | USE + INTEGRATE |
| OpenTelemetry |  | ✓ | ✓ | USE + INTEGRATE |
| Message broker |  | ✓ | ✓ | USE + INTEGRATE |
| Agent frameworks |  | ✓ | ✓ | USE + INTEGRATE |
| Coding agents |  | ✓ | ✓ | USE + INTEGRATE |
| Git hosting |  | ✓ | ✓ | USE + INTEGRATE |
| Generic scheduler |  | ✓ | ✓ | DO NOT BUILD |
| Workflow engine |  | ✓ | ✓ | DO NOT BUILD |
| IAM product |  | ✓ | ✓ | DO NOT BUILD |
| Metrics backend |  | ✓ | ✓ | DO NOT BUILD |
| Vector database |  | ✓ | ✓ | DO NOT BUILD |
| Container orchestrator |  | ✓ | ✓ | DO NOT BUILD |

---

# 10. Decision Criterion C1 — Product Differentiation

Question :

```text
Would PyAgentsKit lose its identity if this capability were outsourced entirely?
```

Si oui :

```text
BUILD semantic layer
```

---

# 11. C2 — Safety Ownership

Question :

```text
Does this capability define whether an external side effect is safe?
```

Si oui :

```text
BUILD
```

Exemples :

```text
Effect state
idempotency semantics
reconciliation semantics
fencing semantics
approval applicability
```

---

# 12. C3 — Commodity Maturity

Question :

```text
Is there already a mature, standardized ecosystem?
```

Si oui :

```text
BUY/USE
+
INTEGRATE
```

Exemples :

```text
PostgreSQL
S3
OIDC
OpenTelemetry
```

---

# 13. C4 — Replaceability

Question :

```text
Should users be able to replace this technology without changing business semantics?
```

Si oui :

```text
Port + Adapter
```

---

# 14. C5 — Provider Volatility

Si le provider change fréquemment :

```text
keep it outside core
```

---

# 15. C6 — Dependency Weight

Un SDK lourd doit être optionnel si possible.

---

# 16. C7 — Operational Burden

Avant BUILD :

```text
Who patches it?
Who scales it?
Who secures it?
Who runs it at 03:00?
```

Si ces responsabilités ne créent aucune valeur différenciante :

```text
do not build
```

---

# 17. C8 — Data Authority

Question :

```text
Must PyAgentsKit itself remain authoritative for this state?
```

Si oui :

```text
BUILD model
```

Même si la persistence sous-jacente est externalisée.

---

# 18. C9 — Ecosystem Leverage

Si une capability externe possède déjà un écosystème riche :

```text
integrate rather than clone
```

---

# 19. C10 — Lock-In Risk

Un adapter réduit le lock-in.

Un modèle core directement calqué sur un provider l’augmente.

---

# 20. C11 — Semantic Portability

La sémantique core doit pouvoir survivre au remplacement du provider.

---

# 21. C12 — Failure Semantics

Si les comportements de panne doivent être uniformisés entre providers :

```text
BUILD canonical failure model
+
INTEGRATE provider-specific behavior
```

---

# 22. BUILD — Domain Core

PyAgentsKit doit construire :

```text
Run
RunState
RuntimeInvocation
Session
Conversation
Effect
Approval
Lease
Artifact
Audit semantics
```

car ce sont les concepts métier du produit.

---

# 23. BUILD — Run Semantics

Inclut :

```text
Run lifecycle
WAITING semantics
PAUSED semantics
terminality
cancellation
Run vs RuntimeInvocation
```

---

# 24. BUILD — Durable Execution Semantics

Construire :

```text
RecoveryPlan
RecoveryBlocker
NextAction
RecoveryPlanner
```

Ne pas déléguer cette logique au runtime.

---

# 25. BUILD — Effect Safety

Construire :

```text
EffectIntent
EffectStatus
IdempotencyKey
InputFingerprint
ExternalReference
reconciliation lifecycle
```

---

# 26. BUILD — Crash Window Reasoning

Les fenêtres :

```text
W1
W2
W3
W4
W5
```

sont des concepts de fiabilité propres à PyAgentsKit.

---

# 27. BUILD — Approval Semantics

Construire :

```text
Approval
ApprovalScope
ApprovalDecision
Approval applicability
expiry
SoD hooks
```

---

# 28. BUILD — Distributed Ownership Semantics

Construire :

```text
Lease
OwnershipContext
FencingToken
Takeover rules
```

Même si PostgreSQL implémente physiquement les transactions.

---

# 29. BUILD — Runtime Integration Contract

Construire :

```text
AgentRuntimeAdapter
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeEvent
RuntimeCheckpoint
```

---

# 30. BUILD — Connector Contract

Construire :

```text
Connector
ConnectorDescriptor
ConnectorCapability
ConnectorRegistry
ReconciliationPort
```

---

# 31. BUILD — Audit Semantics

Construire le modèle :

```text
AuditEvent
Audit subject/action/evidence
```

Mais pas nécessairement le backend d’analytics.

---

# 32. BUILD — Public Contracts

Construire :

```text
RunView
EffectView
ApprovalView
stable error taxonomy
event envelopes
```

---

# 33. BUILD — Application Services

Construire les use cases :

```text
CreateRun
ResumeRun
ExecuteEffect
ReconcileEffect
Approve
TakeoverLease
```

---

# 34. BUILD — Compatibility Layer

Construire l’ACL :

```text
V1
→
V2
```

car seule PyAgentsKit connaît précisément ses anciennes sémantiques.

---

# 35. USE + INTEGRATE — PostgreSQL

Décision :

```text
Do not build a database.
```

Utiliser PostgreSQL comme backend de référence.

PyAgentsKit construit :

```text
schema
repositories
transactions
constraints
migration semantics
```

mais PostgreSQL fournit :

```text
storage engine
WAL
MVCC
indexes
transactions
replication primitives
```

---

# 36. PostgreSQL Boundary

```text
Domain
↓
Repository Port
↓
Postgres Adapter
↓
PostgreSQL
```

---

# 37. Why PostgreSQL

Il répond naturellement aux besoins :

```text
strong transactional semantics
row locking
unique constraints
JSONB when appropriate
mature operations
multi-process coordination
```

---

# 38. What not to build around PostgreSQL

Ne pas créer un datastore custom pour :

```text
Run
Lease
Approval
Effect
```

sans besoin démontré.

---

# 39. USE + INTEGRATE — SQLite

SQLite est un excellent choix pour :

```text
local development
single-node durability
tests
examples
```

Pas comme autorité distribuée de référence.

---

# 40. USE + INTEGRATE — Object Storage

Utiliser :

```text
S3
Azure Blob
MinIO-compatible
```

derrière :

```text
BlobStore
```

---

# 41. Object Storage Core Ownership

PyAgentsKit construit :

```text
Artifact identity
checksum
provenance
retention semantics
```

Le provider construit :

```text
blob persistence
replication
durability
```

---

# 42. USE + INTEGRATE — IAM

Ne pas construire :

```text
identity directory
password database
OIDC server
SAML engine
MFA product
```

---

# 43. IAM Boundary

```text
Governance
↓
IdentityProviderPort
AuthorizationPort
↓
OIDC/IAM adapter
↓
External IAM
```

---

# 44. BUILD — Governance Semantics

Même si IAM est externe, PyAgentsKit doit construire :

```text
Principal abstraction
Approval semantics
PolicyDecision semantics
SoD hooks
```

---

# 45. USE + INTEGRATE — Secret Manager

Ne pas construire un Vault.

Intégrer :

```text
Environment
HashiCorp Vault
AWS Secrets Manager
Azure Key Vault
other providers
```

via `SecretProvider`.

---

# 46. USE + INTEGRATE — OpenTelemetry

Ne pas reconstruire :

```text
trace protocol
collector
metrics backend
```

Construire :

```text
TelemetryPort
semantic instrumentation
safe payload policy
```

---

# 47. USE + INTEGRATE — Logging

Utiliser :

```text
standard logging
structured logging ecosystem
```

Ne pas créer un backend centralisé spécifique.

---

# 48. USE + INTEGRATE — Metrics Backend

PyAgentsKit expose des metrics.

Il ne devient pas :

```text
Prometheus
Datadog
Grafana
New Relic
```

---

# 49. USE + INTEGRATE — Message Broker

Si nécessaire :

```text
Kafka
RabbitMQ
SQS
Azure Service Bus
NATS
```

derrière des adapters.

---

# 50. Broker Boundary

Broker transporte.

PyAgentsKit gouverne :

```text
Inbox
Outbox
deduplication
ownership semantics
```

---

# 51. Broker Anti-Pattern

Ne jamais dire :

```text
message dequeued
=
Run owned
```

---

# 52. USE + INTEGRATE — Agent Frameworks

Ne pas reconstruire LangGraph/CrewAI/PydanticAI.

Construire :

```text
AgentRuntimeAdapter
```

et intégrer.

---

# 53. Runtime Framework Boundary

```text
PyAgentsKit
↓
AgentRuntimeAdapter
↓
ACL
↓
Agent Framework
```

---

# 54. USE + INTEGRATE — Coding Agents

Ne pas reconstruire :

```text
Codex
Claude Code
OpenCode
```

Construire :

```text
coding runtime adapter
workspace contract
Effect interception/governance
```

---

# 55. Coding Agent Differentiator

La valeur PyAgentsKit n’est pas :

```text
generate code better
```

mais :

```text
make autonomous coding actions safer and recoverable
```

---

# 56. USE + INTEGRATE — Git Hosting

GitHub/GitLab/Azure DevOps restent externes.

PyAgentsKit construit :

```text
canonical references
Effect semantics
reconciliation
approval
audit
```

---

# 57. USE + INTEGRATE — Git

Ne pas reconstruire Git.

On peut utiliser :

```text
git CLI
libgit2
GitPython
dulwich
```

derrière adapter si nécessaire.

---

# 58. USE + INTEGRATE — HTTP Transport

Utiliser une librairie mature.

Le core ne doit pas devenir un HTTP stack.

---

# 59. USE + INTEGRATE — Retry Library

Une librairie générique peut être utilisée pour retries transport safe.

Mais :

```text
business retry semantics
```

restent BUILD.

---

# 60. Retry Boundary

```text
tenacity/backoff/etc.
→ transport mechanics

PyAgentsKit
→ whether retry is safe
```

---

# 61. USE + INTEGRATE — Serialization

Pydantic/dataclasses/etc. peuvent être utilisés.

Mais la sémantique Domain ne doit pas dépendre d’un moteur de serialization particulier.

---

# 62. USE + INTEGRATE — Schema Migration Tool

Utiliser éventuellement :

```text
Alembic
custom SQL runner
```

après ADR.

Ne pas construire un framework de migrations général.

---

# 63. USE + INTEGRATE — CLI Framework

Utiliser :

```text
Typer
Click
argparse
```

selon décision.

Le CLI reste adapter.

---

# 64. USE + INTEGRATE — HTTP Framework

Utiliser :

```text
FastAPI
Starlette
other
```

si HTTP API retenue.

Ne pas laisser ce choix influencer Domain/Application.

---

# 65. DO NOT BUILD — Generic Workflow Engine

PyAgentsKit ne doit pas implémenter :

```text
generic DAG engine
BPMN engine
workflow designer
generic compensation engine
```

---

# 66. Why Not

Cela diluerait le produit et concurrencerait des solutions matures sans avantage distinctif.

---

# 67. DO NOT BUILD — Generic Scheduler

Ne pas implémenter :

```text
cron platform
calendar engine
distributed scheduling platform
```

---

# 68. Scheduler Integration

Un scheduler peut appeler :

```text
CreateRun
StartRun
ResumeRun
```

via inbound port.

---

# 69. DO NOT BUILD — IAM

Déjà établi.

---

# 70. DO NOT BUILD — Message Broker

Déjà établi.

---

# 71. DO NOT BUILD — Vector Database

RAG/vector search n’est pas le cœur de la reliability layer.

---

# 72. Vector Integration

Si un runtime/application en a besoin :

```text
external capability
```

---

# 73. DO NOT BUILD — Observability Backend

Ne pas devenir :

```text
trace database
metrics database
log aggregation platform
```

---

# 74. DO NOT BUILD — Object Storage Engine

Déjà établi.

---

# 75. DO NOT BUILD — Database Engine

Déjà établi.

---

# 76. DO NOT BUILD — Container Orchestrator

Ne pas reconstruire Kubernetes/Nomad.

---

# 77. Container Integration

PyAgentsKit peut fournir :

```text
deployment manifests
health endpoints
runbooks
```

---

# 78. DO NOT BUILD — Git Hosting

Ne pas devenir GitHub/GitLab.

---

# 79. DO NOT BUILD — LLM Provider

PyAgentsKit ne doit pas entraîner ou héberger ses propres modèles comme exigence core.

---

# 80. DO NOT BUILD — Generic RAG Platform

Peut être intégré par applications/runtimes.

---

# 81. DO NOT BUILD — Prompt Management SaaS

Hors cœur.

---

# 82. DO NOT BUILD — Agent Marketplace

Pas avant d’avoir stabilisé le contrat runtime/plugin.

---

# 83. DO NOT BUILD — Generic Policy Engine

PyAgentsKit construit les **contracts** de PolicyDecision.

Il peut intégrer :

```text
OPA
Cedar
custom IAM policy
```

si besoin.

---

# 84. Policy Boundary

```text
PyAgentsKit Governance
↓
PolicyEvaluator
↓
external/custom policy engine
```

---

# 85. DO NOT BUILD — Generic Secrets Platform

Déjà établi.

---

# 86. Hybrid Case — Audit

PyAgentsKit doit construire :

```text
AuditEvent semantics
AuditStore contract
critical audit rules
```

Mais intégrer le stockage/export vers systèmes existants.

---

# 87. Hybrid Case — Artifacts

BUILD :

```text
Artifact semantics
checksum
provenance
```

INTEGRATE :

```text
S3/Azure/FileSystem
```

---

# 88. Hybrid Case — Runtime

BUILD :

```text
runtime-neutral control contract
```

INTEGRATE :

```text
actual agent runtimes
```

---

# 89. Hybrid Case — Effects

BUILD :

```text
state machine
idempotency
reconciliation rules
```

INTEGRATE :

```text
external provider operations
```

---

# 90. Hybrid Case — Approvals

BUILD :

```text
approval domain semantics
```

INTEGRATE :

```text
Slack/UI/email/admin console
```

for notification and interaction.

---

# 91. Hybrid Case — Authorization

BUILD :

```text
AuthorizationDecision contract
SecurityContext semantics
```

INTEGRATE :

```text
OIDC/IAM/policy engine
```

---

# 92. Hybrid Case — Coordination

BUILD :

```text
Lease/Fencing semantics
```

INTEGRATE :

```text
PostgreSQL physical implementation
```

---

# 93. Hybrid Case — Messaging

BUILD :

```text
Outbox/Inbox semantics
deduplication requirements
```

INTEGRATE :

```text
Kafka/SQS/RabbitMQ/etc.
```

---

# 94. Hybrid Case — Telemetry

BUILD :

```text
semantic metrics/events
payload minimization policy
```

INTEGRATE :

```text
OpenTelemetry/backend
```

---

# 95. Decision Scorecard

Score each candidate from 1–5:

```text
Product differentiation
Safety criticality
Need for semantic control
Commodity maturity
Operational cost
Provider volatility
Lock-in risk
Replaceability need
Ecosystem leverage
```

---

# 96. Score Interpretation

High :

```text
differentiation
safety
semantic control
```

→ BUILD.

High :

```text
commodity maturity
operational cost
ecosystem leverage
```

→ BUY/INTEGRATE.

---

# 97. Example — RecoveryPlanner

```text
Differentiation        5
Safety                  5
Semantic control        5
Commodity maturity      1
Operational cost        2
```

Decision :

```text
BUILD
```

---

# 98. Example — PostgreSQL

```text
Differentiation        1
Safety semantics        2
Commodity maturity      5
Operational leverage    5
```

Decision :

```text
USE + INTEGRATE
```

---

# 99. Example — LangGraph

```text
Differentiation        1
Ecosystem leverage      5
Provider volatility     4
Replaceability          5
```

Decision :

```text
INTEGRATE
```

---

# 100. Example — Effect Model

```text
Differentiation        5
Safety                  5
Replaceability          5
```

Decision :

```text
BUILD
```

---

# 101. Example — OpenTelemetry

Decision :

```text
USE + INTEGRATE
```

PyAgentsKit définit les semantic spans/metrics, pas le protocol ecosystem.

---

# 102. Build Trap #1 — NIH Syndrome

```text
Not Invented Here
```

Ne pas reconstruire une capacité uniquement pour garder le contrôle technique.

---

# 103. Build Trap #2 — Infrastructure Fascination

Une technologie intéressante n’est pas forcément un produit à construire.

---

# 104. Build Trap #3 — Owning the Wrong Layer

Exemple :

```text
writing a message broker
```

au lieu de :

```text
defining correct delivery/idempotency semantics
```

---

# 105. Build Trap #4 — Generic Framework Drift

Ajouter des primitives générales qui ne servent pas directement la reliability layer.

---

# 106. Build Trap #5 — Provider Model Leakage

Copier les objets GitHub/LangGraph/Postgres dans le Domain.

---

# 107. Buy Trap #1 — Outsourcing Core Semantics

Exemple dangereux :

```text
"PostgreSQL advisory lock is our ownership model."
```

Non.

Le modèle est :

```text
Lease/Fencing
```

et PostgreSQL est une implémentation.

---

# 108. Buy Trap #2 — Vendor-Specific Domain

Exemple :

```text
GitHubPullRequest
```

comme aggregate core.

Préférer :

```text
ExternalReference
```

---

# 109. Buy Trap #3 — Magical Exactly Once

Ne pas croire qu’un broker/provider résout automatiquement les Effects.

---

# 110. Integrate Trap #1 — Thin Wrapper

Un adapter qui ne fait que renommer des méthodes SDK sans ACL n’apporte pas la neutralité attendue.

---

# 111. Integrate Trap #2 — Fake Capability

Ne pas annoncer :

```text
RESUME
```

si l’adapter redémarre en réalité depuis zéro sans équivalence garantie.

---

# 112. Integrate Trap #3 — Hidden Retry

Un SDK provider peut retry automatiquement.

Il faut connaître cette sémantique avant de déclarer l’Effect safe.

---

# 113. Integrate Trap #4 — Hidden Credentials

L’adapter ne doit pas injecter des secrets dans le runtime/LLM sans besoin explicite.

---

# 114. Runtime Ecosystem Strategy

Ordre recommandé :

```text
1. NativeRuntimeAdapter
2. one general-purpose runtime
3. one coding runtime
4. adapter contract stabilization
5. broader ecosystem
```

---

# 115. Why not many adapters first

Le premier objectif est de prouver :

```text
same reliability semantics
across heterogeneous runtimes
```

et non de maximiser le nombre de logos.

---

# 116. Connector Ecosystem Strategy

Ordre recommandé :

```text
1. Generic HTTP foundations
2. GitHub
3. GitLab / Azure DevOps
4. collaboration systems
5. enterprise business systems
```

---

# 117. Why GitHub First

GitHub fournit un excellent test pour :

```text
external writes
idempotency
reconciliation
approval
SHA binding
coding agents
```

---

# 118. Persistence Ecosystem Strategy

Ordre :

```text
Memory
SQLite
PostgreSQL
Object Storage
```

---

# 119. Memory

BUILD adapter simple pour tests.

---

# 120. SQLite

INTEGRATE pour local durability.

---

# 121. PostgreSQL

INTEGRATE comme reference production backend.

---

# 122. Storage

S3/Azure adapters restent optionnels.

---

# 123. Security Ecosystem Strategy

Ordre :

```text
EnvironmentSecretProvider
OIDC identity adapter
Authorization adapter
Vault-like secret provider
external policy engine if needed
```

---

# 124. Observability Strategy

Construire d’abord :

```text
semantic events
metrics names
trace boundaries
```

Puis intégrer OpenTelemetry.

---

# 125. Build vs Buy — Testing

Ne pas construire un test framework.

Utiliser :

```text
pytest
coverage
mypy
Ruff
property-based library if needed
```

Construire :

```text
contract suites
fault scenarios
qualification harness
```

car ceux-ci expriment les garanties PyAgentsKit.

---

# 126. Build vs Buy — Architecture Enforcement

Utiliser :

```text
import-linter
grimp
or equivalent
```

Construire seulement la configuration/règles propres au projet.

---

# 127. Build vs Buy — Documentation

Utiliser Markdown/MkDocs/Sphinx si besoin.

Construire le contenu, pas un moteur documentaire.

---

# 128. Build vs Buy — Migration

Utiliser un outil de schema migration existant si adapté.

Construire :

```text
semantic migrator
preflight
mapping
verification
cutover safety
```

---

# 129. Build vs Buy — Deployment

Ne pas construire une plateforme de déploiement.

Fournir :

```text
Docker example
Kubernetes manifests/examples
health probes
runbooks
```

---

# 130. Build vs Buy — Configuration

Utiliser des standards existants pour settings/env/config.

Construire seulement le modèle de configuration nécessaire au produit.

---

# 131. Build vs Buy — Cryptography

Ne jamais implémenter ses propres primitives crypto.

---

# 132. Build vs Buy — Authentication

Même règle.

---

# 133. Build vs Buy — Serialization Format

Utiliser :

```text
JSON
standard datetime/UUID encodings
```

sauf besoin démontré.

---

# 134. Build vs Buy — Event Envelope

PyAgentsKit doit construire son envelope sémantique/versioning si nécessaire.

Le transport reste externe.

---

# 135. Build vs Buy — Admin UI

Pas une priorité V2 core.

Un UI peut être :

```text
separate package
example
external product
```

---

# 136. Build vs Buy — Approval UI

Core construit :

```text
Approval API
```

UI/Slack/CLI deviennent inbound adapters.

---

# 137. Build vs Buy — Operator Dashboard

Le core doit exposer les Read Models.

Le dashboard peut être un composant séparé.

---

# 138. Build vs Buy — Search

Ne pas ajouter Elasticsearch/OpenSearch comme dépendance core.

---

# 139. Build vs Buy — Analytics

Hors core.

Audit/read models peuvent être exportés.

---

# 140. Build vs Buy — Policy Language

Ne pas inventer un DSL complexe de policy trop tôt.

---

# 141. Policy Increment

Commencer par :

```text
typed Python policy contracts
```

puis intégrer un moteur externe si besoin.

---

# 142. Build vs Buy — Saga Engine

Ne pas construire un moteur saga général.

Les orchestrations de recovery/effects restent explicites.

---

# 143. Build vs Buy — State Machine Library

Les state machines critiques peuvent être implémentées explicitement.

Une library est acceptable si elle n’obscurcit pas les invariants.

---

# 144. Build vs Buy — Distributed Lock Library

Ne pas baser le modèle sur un package lock générique.

Lease/Fencing reste propre à PyAgentsKit.

---

# 145. Build vs Buy — Redis

Redis peut être utilisé pour certaines optimisations futures.

Pas comme autorité initiale des garanties core si PostgreSQL suffit.

---

# 146. Build vs Buy — Celery/RQ

Peuvent devenir inbound work-dispatch adapters.

Ils ne définissent pas les semantics Run.

---

# 147. Build vs Buy — Temporal

Temporal est un workflow/durable execution engine mature.

PyAgentsKit ne doit pas devenir une thin wrapper de Temporal.

Mais un adapter/integration futur peut être étudié.

---

# 148. Temporal Boundary

Si intégré :

```text
PyAgentsKit semantics
remain authoritative
```

ou l’intégration doit clairement annoncer les garanties déléguées.

---

# 149. Build vs Buy — LangGraph Checkpointing

Utiliser les checkpoints runtime si disponibles.

Mais :

```text
runtime checkpoint
!=
PyAgentsKit durable source of truth
```

---

# 150. Build vs Buy — Provider Idempotency

Utiliser une idempotency provider native lorsqu’elle existe.

Mais PyAgentsKit conserve son propre :

```text
Effect identity
fingerprint
status
```

---

# 151. Build vs Buy — Provider Reconciliation

Utiliser les APIs provider pour inspecter l’état.

Mais PyAgentsKit construit :

```text
ReconciliationCase
decision model
```

---

# 152. Build vs Buy — Approval Workflow SaaS

Peut être intégré comme canal d’approval.

Mais la décision canonique doit être enregistrée dans PyAgentsKit.

---

# 153. Build vs Buy — Human Identity

Une identité externe doit être mappée vers :

```text
PrincipalReference
ActorReference
```

---

# 154. Build vs Buy — Audit Export

On peut exporter vers :

```text
SIEM
Splunk
Datadog
OpenSearch
```

mais `AuditStore` reste un contrat PyAgentsKit.

---

# 155. Build vs Buy — Feature Flags

Utiliser une solution externe si besoin.

Ne pas construire une plateforme de feature flags.

---

# 156. Build vs Buy — Rate Limiting

Utiliser une librairie/provider.

Les semantics métier restent dans Application.

---

# 157. Build vs Buy — Circuit Breaker

Infrastructure pattern réutilisable.

Ne doit pas changer le sens des Effects.

---

# 158. Build vs Buy — Caching

Utiliser une implémentation existante si nécessaire.

Ne jamais cacher l’autorité derrière le cache.

---

# 159. Build vs Buy — Encryption at Rest

Déléguer au DB/cloud/storage.

---

# 160. Build vs Buy — Field Encryption

Introduire uniquement pour besoin explicite.

Utiliser des primitives crypto standards.

---

# 161. Build vs Buy — Multi-Tenancy

BUILD :

```text
Tenant semantics
tenant scope
isolation contracts
```

USE/INTEGRATE :

```text
PostgreSQL schemas/RLS
cloud account isolation
```

---

# 162. Build vs Buy — Multi-Region

Ne pas construire en V2 initiale.

Étudier après preuve du besoin.

---

# 163. Build vs Buy — Distributed Consensus

Ne pas implémenter Raft/Paxos.

Utiliser les garanties du backend choisi.

---

# 164. Build vs Buy — Leader Election

Ne pas créer un système général.

Lease semantics couvrent uniquement les ownership needs de PyAgentsKit.

---

# 165. Build vs Buy — Artifact Diffing

Peut utiliser Git/diff libraries.

La provenance reste core.

---

# 166. Build vs Buy — Sandbox

Ne pas écrire un hyperviseur.

Intégrer :

```text
containers
VMs
provider sandbox
OS controls
```

---

# 167. Build vs Buy — Code Execution Policy

BUILD policy/governance.

INTEGRATE sandbox.

---

# 168. Build vs Buy — CI/CD

Ne pas construire GitHub Actions/GitLab CI.

Intégrer leurs APIs comme Connectors.

---

# 169. Build vs Buy — Cloud APIs

AWS/Azure/GCP sont des Connectors, pas des Domain concepts.

---

# 170. Build vs Buy — Deployment Safety

BUILD :

```text
deployment Effect semantics
approval
reconciliation
audit
```

INTEGRATE deployment system.

---

# 171. Build vs Buy — Terraform

Terraform lui-même reste externe.

`terraform apply` est un Protected Effect.

---

# 172. Build vs Buy — Payment

Ne pas construire PSP.

Un paiement est un excellent cas d’Effect nécessitant idempotency/reconciliation.

---

# 173. Build vs Buy — Email/SMS

Provider externe.

PyAgentsKit construit seulement :

```text
Effect semantics
message reference
reconciliation when possible
```

---

# 174. Build vs Buy — ERP/CRM

Connector-specific.

---

# 175. Product Boundary Summary

BUILD :

```text
meaning
authority
safety
recovery
governance
```

INTEGRATE :

```text
execution engines
providers
storage
identity
observability
external systems
```

DO NOT BUILD :

```text
commodity platforms
generic infrastructure
adjacent products
```

---

# 176. Decision Matrix — Core

| Capability | Decision | Why |
|---|---|---|
| Run model | BUILD | Core product semantics |
| RuntimeInvocation | BUILD | Required for durable runtime separation |
| Effect model | BUILD | Core safety model |
| Reconciliation | BUILD | Required for ambiguity handling |
| Approval | BUILD | Governance semantics |
| Lease/Fencing | BUILD | Distributed authority |
| RecoveryPlanner | BUILD | Core reliable resume |
| AuditEvent | BUILD | Accountability semantics |
| Conversation model | BUILD | Durable interaction semantics |
| Artifact model | BUILD | Provenance/integrity semantics |

---

# 177. Decision Matrix — Infrastructure

| Capability | Decision | Adapter |
|---|---|---|
| PostgreSQL | USE + INTEGRATE | Postgres repositories/UoW |
| SQLite | USE + INTEGRATE | SQLite repositories |
| Object storage | USE + INTEGRATE | BlobStore |
| IAM/OIDC | USE + INTEGRATE | Identity/Authorization ports |
| Secrets | USE + INTEGRATE | SecretProvider |
| OpenTelemetry | USE + INTEGRATE | TelemetryPort |
| Broker | USE + INTEGRATE | Messaging adapters |
| Git | USE + INTEGRATE | Git/workspace adapter |
| Container runtime | USE + INTEGRATE | sandbox/workspace adapter |

---

# 178. Decision Matrix — Agent Ecosystem

| Capability | Decision |
|---|---|
| Native Runner | KEEP + INTEGRATE |
| LangGraph | INTEGRATE |
| PydanticAI | INTEGRATE |
| OpenAI Agents | INTEGRATE |
| CrewAI | INTEGRATE if useful |
| AutoGen | INTEGRATE if useful |
| Codex | INTEGRATE |
| Claude Code | INTEGRATE |
| OpenCode | INTEGRATE |

---

# 179. Decision Matrix — External Systems

| Capability | Decision |
|---|---|
| GitHub | INTEGRATE |
| GitLab | INTEGRATE |
| Azure DevOps | INTEGRATE |
| Slack | INTEGRATE |
| Jira | INTEGRATE |
| ERP | INTEGRATE |
| CRM | INTEGRATE |
| Cloud APIs | INTEGRATE |
| payment providers | INTEGRATE |
| deployment systems | INTEGRATE |

---

# 180. Decision Matrix — Explicit Non-Goals

| Capability | Decision |
|---|---|
| generic workflow engine | DO NOT BUILD |
| general scheduler | DO NOT BUILD |
| IAM product | DO NOT BUILD |
| message broker | DO NOT BUILD |
| vector DB | DO NOT BUILD |
| observability backend | DO NOT BUILD |
| Git hosting | DO NOT BUILD |
| cloud platform | DO NOT BUILD |
| container orchestrator | DO NOT BUILD |
| secrets platform | DO NOT BUILD |

---

# 181. Architectural Rule BBI-INV-01

```text
PyAgentsKit owns semantic authority, not commodity infrastructure.
```

---

# 182. BBI-INV-02

```text
Provider-specific types never define core Domain semantics.
```

---

# 183. BBI-INV-03

```text
A commodity may implement a guarantee, but does not define the guarantee.
```

Example :

```text
PostgreSQL enforces unique Effect key
but
Effect idempotency is a PyAgentsKit semantic.
```

---

# 184. BBI-INV-04

```text
Replacing an adapter must not require rewriting Domain invariants.
```

---

# 185. BBI-INV-05

```text
No external runtime may become the sole source of truth for Effects.
```

---

# 186. BBI-INV-06

```text
No broker may become the ownership authority.
```

---

# 187. BBI-INV-07

```text
No IAM provider may define Approval semantics.
```

---

# 188. BBI-INV-08

```text
No observability backend may replace Audit semantics.
```

---

# 189. BBI-INV-09

```text
No generic retry library may decide Effect replay safety.
```

---

# 190. BBI-INV-10

```text
Core dependency weight must remain bounded.
```

---

# 191. Architecture Review Checklist

Avant d’ajouter une dépendance externe :

```text
[ ] Is this a commodity?
[ ] Does PyAgentsKit need semantic ownership?
[ ] Can it live behind a Port?
[ ] Is the SDK optional?
[ ] Could the provider be replaced?
[ ] What happens on timeout?
[ ] What happens on ambiguous write?
[ ] Does it retry internally?
[ ] Does it expose idempotency?
[ ] Does it expose reconciliation?
[ ] Does it introduce credentials?
[ ] Does it expand the trust boundary?
```

---

# 192. Build Review Checklist

Avant BUILD :

```text
[ ] Is this core differentiation?
[ ] Is this required for safety?
[ ] Is there already a mature solution?
[ ] What is the maintenance burden?
[ ] What is the operational burden?
[ ] Could an adapter solve the problem instead?
```

---

# 193. Buy Review Checklist

Avant BUY/USE :

```text
[ ] Is the product mature?
[ ] Is it actively maintained?
[ ] Does licensing fit?
[ ] Is data portability acceptable?
[ ] Is vendor lock-in bounded?
[ ] Can we wrap it?
```

---

# 194. Integrate Review Checklist

```text
[ ] Canonical Port exists
[ ] ACL exists
[ ] Errors normalized
[ ] Capabilities explicit
[ ] Secrets scoped
[ ] Retry semantics known
[ ] Timeout semantics known
[ ] Reconciliation strategy known
[ ] Contract tests exist
```

---

# 195. Dependency Evaluation Template

Chaque nouvelle dépendance importante doit documenter :

```text
Purpose
Category
Build/Buy/Integrate decision
Alternatives
License
Maintenance health
Security implications
Data access
Failure behavior
Retry behavior
Lock-in
Adapter boundary
Removal strategy
```

---

# 196. Vendor Lock-In Mitigation

Utiliser :

```text
canonical models
ports
ACLs
opaque handles
external references
```

---

# 197. Exit Strategy

Pour chaque provider :

```text
How do we remove it?
```

doit être raisonnablement clair.

---

# 198. Adapter Removal

La suppression d’un adapter ne doit pas casser les autres.

---

# 199. Core Removal Resistance

Le core ne doit pas contenir :

```text
provider-specific enum
provider-specific metadata requirement
provider-specific exception
```

---

# 200. Dependency Security

Un adapter tiers est une trust boundary et une supply-chain risk.

---

# 201. Official Adapter Criteria

Pour être official :

```text
contract compliant
maintained
security reviewed
known limitations documented
qualification level published
```

---

# 202. Plugin Ecosystem

À terme, des adapters peuvent être distribués séparément.

---

# 203. Plugin Naming

Exemples :

```text
pyagentskit-langgraph
pyagentskit-codex
pyagentskit-github
```

---

# 204. Plugin Rule

Un plugin n’étend pas le Domain arbitrairement.

Il implémente :

```text
existing ports
```

ou propose un ADR pour extension du core.

---

# 205. Build vs Buy & SemVer

Ajouter un nouvel adapter compatible :

```text
minor release
```

Modifier une sémantique core stable :

```text
potential major release
```

---

# 206. Build vs Buy & Packaging

Core :

```text
minimal required dependencies
```

Adapters :

```text
optional extras or separate packages
```

---

# 207. Build vs Buy & Testing

BUILD capabilities exigent :

```text
unit + invariants + failure tests
```

INTEGRATE capabilities exigent :

```text
contract + integration + provider failure tests
```

---

# 208. Build vs Buy & Qualification

Un adapter critique n’est production-ready que si ses semantics de panne ont été testées avec le vrai provider ou une qualification réaliste.

---

# 209. Build vs Buy & Documentation

Chaque adapter officiel documente :

```text
what it controls
what it cannot control
capabilities
failure semantics
idempotency
reconciliation
```

---

# 210. Build vs Buy & Roadmap

Ordre recommandé :

```text
1. Build the V2 semantic core.
2. Integrate Native Runtime.
3. Build Effect/Recovery semantics.
4. Integrate PostgreSQL.
5. Build Governance/Audit.
6. Integrate one external runtime.
7. Integrate one coding runtime.
8. Integrate GitHub.
9. Broaden ecosystem only after contracts stabilize.
```

---

# 211. P0 BUILD backlog

```text
Run V2
RuntimeInvocation
Effect V2
Reconciliation
RecoveryPlanner
Approval V2
Lease/Fencing contract
AgentRuntimeAdapter
Connector contract
Audit semantics
```

---

# 212. P0 INTEGRATE backlog

```text
NativeRuntimeAdapter
PostgreSQL
Filesystem/Object Storage
OpenTelemetry
```

---

# 213. P1 INTEGRATE backlog

```text
one external general-purpose runtime
one coding runtime
GitHub
OIDC/AuthZ
```

---

# 214. P2 ecosystem backlog

```text
additional runtimes
GitLab
Slack
Jira
Azure DevOps
additional secret stores
additional brokers
```

---

# 215. Deferred

```text
multi-region
generic plugin marketplace
advanced policy engines
operator UI
multi-agent reliability
```

---

# 216. Architecture Decision Candidates

Créer des ADR spécifiques pour :

```text
BUILD semantics / INTEGRATE infrastructure
PostgreSQL reference backend
OpenTelemetry adoption
first external runtime
first coding runtime
first connector
plugin packaging
ORM strategy
migration tool
```

---

# 217. Success Criteria

La stratégie Build vs Buy est réussie si :

1. le core reste compact ;
2. les sémantiques safety-critical appartiennent à PyAgentsKit ;
3. les technologies externes restent remplaçables ;
4. les SDK provider restent hors Domain ;
5. aucune commodité importante n’est reconstruite inutilement ;
6. les adapters annoncent honnêtement leurs capabilities ;
7. le nombre d’adapters peut croître sans complexifier le core ;
8. le coût opérationnel du projet reste maîtrisé ;
9. la roadmap favorise les garanties avant l’écosystème ;
10. PyAgentsKit garde une identité produit claire.

---

# 218. Definition of Done

Ce cadre est correctement appliqué lorsque :

1. chaque grande capability est classifiée BUILD / BUY / INTEGRATE ;
2. les non-goals sont explicites ;
3. la roadmap respecte ce découpage ;
4. les Ports existent avant les integrations majeures ;
5. les adapters critiques ont des contract suites ;
6. les commodités restent optionnelles quand possible ;
7. les dependencies lourdes sont isolées ;
8. les erreurs provider sont normalisées ;
9. les retries provider sont audités ;
10. les ADR correspondants existent ;
11. le core peut tourner sans l’ensemble des SDK externes ;
12. la suppression d’un adapter ne change pas les invariants Domain.

---

# 219. Résumé stratégique

La stratégie de PyAgentsKit peut être résumée ainsi :

```text
                   ┌────────────────────────────┐
                   │         BUILD              │
                   │                            │
                   │ Run semantics              │
                   │ Effect safety              │
                   │ Recovery                   │
                   │ Approval                   │
                   │ Lease / Fencing            │
                   │ Runtime contracts          │
                   │ Audit semantics            │
                   └─────────────┬──────────────┘
                                 │
                                 ▼
                    PORTS & CANONICAL MODELS
                                 │
           ┌─────────────────────┼─────────────────────┐
           ▼                     ▼                     ▼
       INTEGRATE             INTEGRATE             INTEGRATE
       Runtimes              Infrastructure        External Systems
       LangGraph             PostgreSQL            GitHub
       Codex                 S3                    GitLab
       Claude Code           OIDC                  Slack
       PydanticAI            OTel                  ERP
```

Et autour :

```text
DO NOT BUILD
────────────────────────────
Generic workflow engine
Generic scheduler
IAM
Broker
Database engine
Object storage engine
Observability backend
Git hosting
Container orchestrator
Vector database
```

La doctrine finale est :

> **PyAgentsKit doit posséder les décisions qui déterminent si une exécution est sûre, durable, gouvernée et récupérable. Il doit intégrer — et non reproduire — les systèmes qui fournissent le calcul, le stockage, l’identité, le transport ou les interactions externes.**

---

# 220. Formule courte

```text
Build semantics.
Integrate runtimes and systems.
Reuse infrastructure.
Avoid commodity reinvention.
```
