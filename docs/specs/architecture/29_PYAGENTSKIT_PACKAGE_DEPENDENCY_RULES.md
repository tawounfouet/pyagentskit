# PyAgentsKit — Package Dependency Rules

**Document :** `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`  
**Version :** 1.0  
**Date :** 21 octobre 2026  
**Statut :** Architecture enforcement — Dependency Rules  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/PYAGENTSKIT_TARGET_CODEBASE_TOPOLOGY_DDD_HEXAGONAL.md`

---

# 1. Objet

Ce document définit les **règles de dépendance entre packages** de PyAgentsKit V2.

L’objectif est de transformer l’architecture cible en contraintes vérifiables par CI.

Il formalise :

- la direction des dépendances ;
- les imports autorisés ;
- les imports interdits ;
- les dépendances entre Bounded Contexts ;
- le rôle du Shared Kernel ;
- la séparation des ports et adapters ;
- l’indépendance des runtime adapters ;
- l’indépendance des connectors ;
- le rôle du bootstrap ;
- les règles de dépendances optionnelles ;
- les règles de tests ;
- les mécanismes de contrôle automatiques.

Le principe directeur est :

> **Une architecture qui n’est pas testée finit toujours par devenir une simple convention.**

---

# 2. Règle fondamentale

La dépendance pointe vers le centre.

```text
Adapters / API / Bootstrap
          │
          ▼
      Application
          │
          ▼
        Domain
```

En sens inverse :

```text
Domain
!-> Application
!-> Adapters
!-> API
!-> Bootstrap
```

---

# 3. Direction générale

```text
bootstrap
  ├──> api
  ├──> adapters
  ├──> application
  └──> domain

api
  └──> application

adapters
  ├──> application ports
  └──> domain contracts

application
  └──> domain

domain
  └──> shared kernel only
```

---

# 4. Topologie de référence

```text
src/pyagentskit/
├── contracts/
├── domain/
├── application/
├── adapters/
├── api/
├── bootstrap/
├── compat/
└── testing/
```

---

# 5. Layer Definitions

## Domain

Contient :

```text
entities
aggregates
value objects
domain services
domain events
domain errors
invariants
```

## Application

Contient :

```text
use cases
application services
ports
orchestration
queries
recovery planning
```

## Adapters

Contient :

```text
PostgreSQL
SQLite
runtime SDKs
connectors
storage providers
OIDC
OpenTelemetry
HTTP clients
```

## API

Contient :

```text
public Python facade
public DTOs/views
public errors
sync/async clients
```

## Bootstrap

Contient :

```text
dependency injection
composition root
adapter construction
configuration
profiles
```

---

# 6. Rule DR-001 — Domain independence

Interdit :

```text
domain -> application
domain -> adapters
domain -> api
domain -> bootstrap
```

---

# 7. Rule DR-002 — Application independence from concrete adapters

Interdit :

```text
application -> adapters
```

Application ne peut importer que :

```text
domain
application ports
contracts
```

---

# 8. Rule DR-003 — API does not bypass Application

Interdit :

```text
api -> adapters
api -> persistence
api -> runtime SDK
```

Autorisé :

```text
api -> application
api -> contracts
```

---

# 9. Rule DR-004 — Adapters implement ports

Autorisé :

```text
adapters -> application.ports
adapters -> domain contracts
adapters -> contracts
```

---

# 10. Rule DR-005 — Bootstrap may compose everything

`bootstrap/` est le seul package autorisé à connaître simultanément :

```text
application
adapters
api
domain
```

---

# 11. Rule DR-006 — No business logic in Bootstrap

Le fait que bootstrap puisse tout importer ne lui donne pas le droit de contenir :

```text
Run transition logic
Effect retry logic
Approval decision logic
Lease takeover logic
```

---

# 12. Rule DR-007 — Public API remains technology-neutral

Interdit dans `api/` :

```text
psycopg
SQLAlchemy
boto3
azure SDK
langgraph
github SDK
OpenTelemetry SDK
```

---

# 13. Rule DR-008 — Contracts package remains lightweight

`contracts/` ne doit contenir que :

```text
public IDs
public references
public errors
public envelopes
public serialization helpers
```

Pas :

```text
business aggregate
concrete adapter
ORM
provider SDK
```

---

# 14. Domain package structure

```text
domain/
├── shared/
├── execution/
├── effects/
├── governance/
├── coordination/
├── conversations/
├── runtime_integration/
├── artifacts/
└── audit/
```

---

# 15. Rule DR-009 — Context aggregate isolation

Un Bounded Context ne doit pas importer directement l’aggregate d’un autre contexte.

Exemple interdit :

```python
from pyagentskit.domain.effects.effect import Effect
```

dans :

```text
domain.execution
```

si Execution n’est censé consommer qu’un :

```text
EffectReference
EffectSummary
```

---

# 16. Rule DR-010 — Published Language only

Les échanges inter-contextes doivent passer par :

```text
ID
Reference
Summary
Published DTO
Domain/Integration Event
Application Port
```

---

# 17. Rule DR-011 — Shared Kernel minimal

`domain/shared/` peut contenir :

```text
TenantId
CorrelationContext
Version
DomainEvent base
Clock abstraction
Typed ID base
```

---

# 18. Rule DR-012 — Shared Kernel cannot contain aggregates

Interdit :

```text
Run
Effect
Approval
Lease
Conversation
Message
Artifact
RuntimeHandle
```

dans `domain/shared/`.

---

# 19. Rule DR-013 — Shared Kernel growth gate

Toute nouvelle classe ajoutée au Shared Kernel doit répondre à :

```text
Used by at least two Bounded Contexts?
Semantically identical in both?
Stable enough to share?
No ownership conflict?
```

Sinon :

```text
keep local
```

---

# 20. Rule DR-014 — Execution does not own Effects

Interdit :

```text
domain.execution -> domain.effects.Effect
```

Autorisé :

```text
EffectId
EffectStatusView
EffectSummary
```

---

# 21. Rule DR-015 — Execution does not own Approvals

Même règle.

Execution peut connaître :

```text
ApprovalId
ApprovalSummary
ApprovalApplicability
```

mais pas muter `Approval`.

---

# 22. Rule DR-016 — Execution does not own Lease internals

Execution consomme :

```text
OwnershipContext
```

et non l’aggregate Lease complet.

---

# 23. Rule DR-017 — Effects depend on Governance via port/contract

Effects peut demander :

```text
PolicyDecision
ApprovalApplicability
AuthorizationDecision
```

mais ne modifie pas l’Approval.

---

# 24. Rule DR-018 — Effects depend on Coordination via ownership contract

Effects peut consommer :

```text
OwnershipContext
FencingToken
```

mais ne renouvelle pas lui-même un lease.

---

# 25. Rule DR-019 — Conversations remain independent of Runtime SDKs

Interdit :

```text
domain.conversations -> LangGraph
domain.conversations -> OpenAI SDK
domain.conversations -> Codex SDK
```

---

# 26. Rule DR-020 — Runtime Integration domain remains canonical

`domain/runtime_integration/` peut connaître :

```text
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeStatus
RuntimeEvent
```

mais aucun runtime concret.

---

# 27. Rule DR-021 — Artifacts remain storage-neutral

Interdit :

```text
domain.artifacts -> boto3
domain.artifacts -> azure.storage
domain.artifacts -> pathlib-specific storage behavior
```

---

# 28. Rule DR-022 — Audit remains telemetry-neutral

Interdit :

```text
domain.audit -> OpenTelemetry
domain.audit -> logging
domain.audit -> Prometheus
```

---

# 29. Application package structure

```text
application/
├── ports/
│   ├── inbound/
│   └── outbound/
├── execution/
├── recovery/
├── effects/
├── governance/
├── coordination/
├── conversations/
├── artifacts/
└── queries/
```

---

# 30. Rule DR-023 — Use cases depend on ports, not implementations

Mauvais :

```python
from pyagentskit.adapters.outbound.persistence.postgres import PostgresRunRepository
```

dans `application/execution/start_run.py`.

Bon :

```python
from pyagentskit.application.ports.outbound.repositories import RunRepository
```

---

# 31. Rule DR-024 — Application orchestration may cross contexts

Application peut orchestrer plusieurs contextes.

Exemple :

```text
ResumeRun
→ Coordination
→ Effects
→ Governance
→ Runtime Integration
```

Mais sans muter directement les aggregates étrangers.

---

# 32. Rule DR-025 — No cross-context repository mutation

Interdit :

```text
ApprovalRepository updates Run
EffectRepository updates Lease
RunRepository updates Approval
```

---

# 33. Rule DR-026 — Query layer may compose read models

`application/queries/` peut composer :

```text
RunView
EffectView
ApprovalView
TimelineView
```

à partir de plusieurs sources.

Mais :

```text
read-only
non-authoritative
```

---

# 34. Rule DR-027 — Read models cannot be used for safety decisions

Interdit :

```text
take RunView from replica
→ decide lease authority
```

---

# 35. Rule DR-028 — No direct adapter-to-adapter business flow

Interdit :

```text
GitHubConnector -> PostgresEffectRepository
CodexAdapter -> S3BlobStore
HTTPAdapter -> PostgresRunRepository
```

Le flux doit repasser par Application.

---

# 36. Adapter package structure

```text
adapters/
├── inbound/
└── outbound/
```

---

# 37. Rule DR-029 — Inbound adapters depend only on inbound ports/API contracts

Exemple HTTP :

```text
HTTP route
→ CreateRunCommand
→ RunCommandPort
```

Pas :

```text
HTTP route
→ SQL
```

---

# 38. Rule DR-030 — Outbound adapters implement outbound ports

Exemple :

```text
PostgresRunRepository
implements
RunRepository
```

---

# 39. Rule DR-031 — Runtime adapters are mutually independent

Interdit :

```text
LangGraphAdapter -> CodexAdapter
CodexAdapter -> NativeRuntimeAdapter
ClaudeCodeAdapter -> OpenCodeAdapter
```

---

# 40. Rule DR-032 — Connectors are mutually independent

Interdit :

```text
GitHubConnector -> GitLabConnector
SlackConnector -> JiraConnector
```

---

# 41. Rule DR-033 — Runtime adapters cannot call connectors directly

Un runtime peut demander un Effect.

Mais :

```text
RuntimeAdapter
!-> GitHubConnector
```

La mutation externe passe par :

```text
Application EffectGateway
```

---

# 42. Rule DR-034 — Connectors cannot decide Governance

Interdit :

```text
GitHubConnector decides "approval required"
```

---

# 43. Rule DR-035 — Persistence adapters cannot decide domain transitions

Interdit :

```text
PostgresRunRepository automatically converts WAITING -> RUNNING
```

---

# 44. Rule DR-036 — Telemetry adapters cannot affect business outcome

Une panne metrics ne doit pas transformer automatiquement :

```text
SUCCEEDED -> FAILED
```

sauf policy explicite High Assurance pour audit critique.

---

# 45. Rule DR-037 — Security adapters return canonical decisions

OIDC/IAM adapters doivent traduire les résultats vers :

```text
Principal
AuthorizationDecision
```

pas propager les objets provider.

---

# 46. Rule DR-038 — Provider SDK containment

Un type SDK ne doit exister que dans :

```text
adapter implementation
adapter mapping layer
adapter tests
```

---

# 47. Provider containment examples

```text
LangGraph graph state
→ only adapters/outbound/runtimes/langgraph/

GitHub PullRequest object
→ only adapters/outbound/connectors/github/

psycopg connection
→ only adapters/outbound/persistence/postgres/
```

---

# 48. Rule DR-039 — No optional dependency import at core import time

`import pyagentskit` ne doit pas exiger :

```text
psycopg
boto3
langgraph
azure SDK
```

---

# 49. Rule DR-040 — Adapter-local optional imports

Les imports optionnels doivent être contenus dans le package adapter.

Exemple :

```python
# adapters/outbound/runtimes/langgraph/adapter.py
import langgraph
```

---

# 50. Rule DR-041 — Clear missing-extra errors

Si adapter optionnel utilisé sans extra :

```text
raise explicit installation error
```

Exemple :

```text
Install with pyagentskit[langgraph]
```

---

# 51. Rule DR-042 — Core dependency budget

Le core doit rester volontairement léger.

Dépendances candidates core :

```text
typing
dataclasses/pydantic according ADR
standard library
small stable runtime deps only
```

---

# 52. Rule DR-043 — Infrastructure dependencies belong to extras

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

# 53. Rule DR-044 — Adapter extras cannot leak transitively into core tests

Les tests unitaires Domain/Application doivent pouvoir tourner sans installer toutes les extras.

---

# 54. Rule DR-045 — Bootstrap is the composition root

Seulement `bootstrap/` construit les graphes concrets de dépendance.

---

# 55. Rule DR-046 — No global singleton registries

Interdit :

```text
GLOBAL_RUNTIME_REGISTRY
GLOBAL_CONNECTOR_REGISTRY
```

si cela empêche isolation/testabilité.

---

# 56. Rule DR-047 — Registries are injected

```text
RuntimeRegistry
ConnectorRegistry
```

sont construits au bootstrap et injectés.

---

# 57. Rule DR-048 — No service locator in entities

Interdit :

```python
adapter = get_service("github")
```

dans le Domain.

---

# 58. Rule DR-049 — Configuration belongs outside Domain

Configuration technique :

```text
DSN
endpoint
retry timeout
bucket
provider model name
```

n’appartient pas aux Entities.

---

# 59. Rule DR-050 — Domain may reference policy facts, not infrastructure config

Exemple acceptable :

```text
EffectRiskLevel.CRITICAL
```

Pas :

```text
github_timeout=30
```

---

# 60. API dependency rules

```text
api
→ application
→ domain
```

---

# 61. Rule DR-051 — Public view models are independent from persistence

`RunView` ne doit pas être :

```text
SQLAlchemy RunRow
```

---

# 62. Rule DR-052 — Public error taxonomy hides infrastructure

Public :

```text
ConflictError
RuntimeUnavailable
ConnectorUnavailable
PolicyDenied
```

Pas :

```text
psycopg.OperationalError
```

---

# 63. Rule DR-053 — Sync facade wraps async semantics

La façade sync dépend :

```text
api async/application
```

pas de versions alternatives des business services.

---

# 64. Compatibility package rules

```text
compat/v1/
```

est une frontière temporaire/longue durée contrôlée.

---

# 65. Rule DR-054 — V1 compatibility may depend on V2 public/application contracts

Autorisé progressivement :

```text
compat.v1 -> application
compat.v1 -> domain published contracts
```

---

# 66. Rule DR-055 — V2 domain must never depend on compat.v1

Interdit :

```text
domain -> compat.v1
application core -> compat.v1
```

---

# 67. Rule DR-056 — NativeRuntimeAdapter may depend on V1 Runner

C’est une exception contrôlée.

```text
adapters.outbound.runtimes.native
→ V1 Runner
```

---

# 68. Rule DR-057 — Compatibility exception must be explicit

Toute exception V1 doit être :

```text
documented
tested
temporary or justified
```

---

# 69. Testing package rules

```text
testing/
```

peut fournir :

```text
fakes
fixtures
contract bases
fault injection
```

---

# 70. Rule DR-058 — Production code cannot depend on testing package

Interdit :

```text
domain -> testing
application -> testing
adapters -> testing
api -> testing
```

---

# 71. Rule DR-059 — Tests may depend inward freely

Tests peuvent importer le package sous test.

---

# 72. Rule DR-060 — Contract tests target ports

Un contract test ne dépend pas des internals d’un adapter.

---

# 73. Rule DR-061 — Adapter integration tests may use provider SDKs

Seulement dans :

```text
tests/integration/adapters/
```

---

# 74. Rule DR-062 — Architecture tests run in CI

Ils ne sont pas optionnels.

---

# 75. Circular dependency policy

Aucun cycle entre packages de production.

---

# 76. Rule DR-063 — Domain contexts must be acyclic

Exemple interdit :

```text
execution -> effects -> governance -> execution
```

directement.

Les cycles se cassent via :

```text
Published Language
Application orchestration
Domain events
ports
```

---

# 77. Rule DR-064 — Application dependency graph should be acyclic

Si deux use cases s’importent mutuellement :

```text
extract shared service or orchestrator
```

---

# 78. Rule DR-065 — Adapter cycles forbidden

```text
postgres -> telemetry -> postgres
```

à éviter.

Utiliser decorators/bootstrap si besoin.

---

# 79. Domain Context Dependency Matrix

Légende :

```text
A = allowed via Published Language / shared VO
P = allowed via port/application boundary
X = forbidden direct aggregate import
```

| From \ To | Execution | Effects | Governance | Coordination | Conversations | Runtime Integration | Artifacts | Audit |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Execution | — | P | P | P | P | P | P | P |
| Effects | A | — | P | P | X | X | P | P |
| Governance | A | A | — | X | A | X | X | P |
| Coordination | A | A | X | — | X | X | X | P |
| Conversations | A | X | A | X | — | P | P | P |
| Runtime Integration | A | P | X | X | P | — | P | P |
| Artifacts | A | A | X | X | X | X | — | P |
| Audit | A | A | A | A | A | A | A | — |

La matrice décrit l’intention architecturale, pas nécessairement des imports Python directs.

---

# 80. Rule DR-066 — Audit is sink-oriented

Les autres contextes peuvent publier vers Audit.

Audit ne commande pas leurs transitions métier.

---

# 81. Rule DR-067 — Runtime Integration is not the orchestrator

Runtime Integration expose la capacité.

Execution/Application décide quand l’utiliser.

---

# 82. Rule DR-068 — Conversations cannot authorize effects

Un message :

```text
"vas-y"
```

n’est pas une Approval sans conversion explicite via Governance.

---

# 83. Rule DR-069 — Coordination cannot infer business completion

La perte d’un lease ne signifie pas :

```text
Run FAILED
```

---

# 84. Rule DR-070 — Artifact existence cannot infer Effect success

Un fichier présent ne prouve pas automatiquement qu’un Effect externe a réussi.

---

# 85. Import-linter strategy

Recommandation :

```text
import-linter
```

ou outil équivalent.

---

# 86. Import-linter contract — Layers

Conceptuellement :

```text
bootstrap
api
adapters
application
domain
```

avec dépendances contrôlées.

---

# 87. Import-linter contract — Domain isolation

```text
domain cannot import:
pyagentskit.application
pyagentskit.adapters
pyagentskit.api
pyagentskit.bootstrap
pyagentskit.compat
```

---

# 88. Import-linter contract — Application isolation

```text
application cannot import:
pyagentskit.adapters
pyagentskit.bootstrap
```

---

# 89. Import-linter contract — API isolation

```text
api cannot import:
pyagentskit.adapters.outbound
```

---

# 90. Import-linter contract — Adapter independence

Pour chaque runtime adapter :

```text
no sibling runtime adapter imports
```

---

# 91. Import-linter contract — Connector independence

Même règle.

---

# 92. Import-linter contract — Testing isolation

```text
production packages cannot import pyagentskit.testing
```

---

# 93. Import-linter config example

Exemple conceptuel :

```ini
[importlinter]
root_package = pyagentskit

[importlinter:contract:domain_isolation]
name = Domain must remain independent
type = forbidden
source_modules =
    pyagentskit.domain
forbidden_modules =
    pyagentskit.application
    pyagentskit.adapters
    pyagentskit.api
    pyagentskit.bootstrap
    pyagentskit.compat
```

---

# 94. Application rule example

```ini
[importlinter:contract:application_no_adapters]
name = Application must not depend on adapters
type = forbidden
source_modules =
    pyagentskit.application
forbidden_modules =
    pyagentskit.adapters
```

---

# 95. Runtime adapter independence example

```ini
[importlinter:contract:runtimes_independent]
name = Runtime adapters are independent
type = independence
modules =
    pyagentskit.adapters.outbound.runtimes.native
    pyagentskit.adapters.outbound.runtimes.langgraph
    pyagentskit.adapters.outbound.runtimes.codex
    pyagentskit.adapters.outbound.runtimes.claude_code
```

---

# 96. Connector independence example

Même pattern.

---

# 97. Architecture test code

En complément, tests Python explicites peuvent vérifier :

```text
public imports
optional dependency absence
forbidden package references
```

---

# 98. Static typing boundary

Les Protocols de ports doivent être vérifiés par :

```text
mypy
pyright
```

selon toolchain retenue.

---

# 99. Type-only imports

Utiliser :

```python
if TYPE_CHECKING:
```

n’autorise pas à violer une frontière architecturale.

Une dépendance de type reste une dépendance conceptuelle.

---

# 100. Forward references

Même règle.

---

# 101. Runtime optional import rule

Ne pas faire :

```python
try:
    import langgraph
except ImportError:
    langgraph = None
```

dans le core.

Le code reste local au package adapter.

---

# 102. Interface segregation

Éviter qu’un port force un adapter à implémenter des méthodes impossibles.

Utiliser :

```text
capabilities
small protocols
optional subprotocols
```

---

# 103. Capability subprotocol example

```text
StartableRuntime
ResumableRuntime
CancellableRuntime
CheckpointableRuntime
```

peut être utilisé si cela simplifie les contrats.

---

# 104. No abstract-base-class inheritance explosion

Le but n’est pas de créer :

```text
40 ABCs
```

pour refléter chaque méthode.

Préférer un design lisible.

---

# 105. Dependency inversion rule

Les besoins métier déterminent les interfaces.

Ne pas recopier l’API du provider dans le port.

---

# 106. Example — bad port design

Mauvais :

```python
class GitHubPort:
    async def post_repos_owner_repo_pulls(...):
        ...
```

Bon :

```python
class PullRequestConnector:
    async def create_pull_request(...):
        ...
```

---

# 107. Example — bad runtime port design

Mauvais :

```python
class LangGraphPort:
    async def invoke_graph(...):
        ...
```

Bon :

```python
class AgentRuntimeAdapter:
    async def start(...):
        ...
```

---

# 108. Dependency rule for DTOs

Inbound DTO :

```text
adapter-specific
```

Application Command :

```text
application-specific
```

Domain Value Object :

```text
domain-specific
```

Public View :

```text
API-specific
```

Ne pas utiliser un seul modèle pour les quatre rôles.

---

# 109. Mapping layer rule

Chaque frontière importante possède un mapping explicite :

```text
HTTP DTO → Command
Provider SDK → canonical runtime model
DB row → Aggregate
Domain → Public View
```

---

# 110. No `model_dump()` architecture

Interdit comme stratégie de mapping universelle.

---

# 111. No implicit field coupling

Si deux modèles partagent aujourd’hui les mêmes noms de champs, cela ne signifie pas qu’ils sont le même contrat.

---

# 112. Persistence dependency rule

Domain ne connaît pas :

```text
tables
columns
indexes
transactions
```

Application connaît seulement :

```text
Repository
UnitOfWork
```

---

# 113. UnitOfWork dependency rule

UnitOfWork est un port.

`PostgresUnitOfWork` reste adapter-specific.

---

# 114. Transaction orchestration

Application peut décider :

```text
begin
save aggregate
append outbox
commit
```

via UnitOfWork.

Elle ne doit pas appeler :

```text
connection.commit()
```

---

# 115. External side effect transaction rule

Jamais :

```text
DB transaction open
→ remote provider call
→ commit
```

sauf justification formelle exceptionnelle.

---

# 116. Cross-context transaction rule

Éviter une transaction DB géante couvrant tous les contexts.

Préférer :

```text
local transaction
+
Outbox
+
reconciliation
```

---

# 117. Event dependency rules

Domain Event peut être défini dans le contexte propriétaire.

Integration Event est défini dans application/contracts d’intégration.

Audit Event appartient à Audit.

Runtime Event appartient à Runtime Integration.

---

# 118. Rule DR-071 — Domain Event cannot import Outbox implementation

Évident mais à tester.

---

# 119. Rule DR-072 — Outbox cannot become business authority

Un event publié n’est pas la vérité métier.

---

# 120. Rule DR-073 — Queue consumer reloads authoritative state

Les notifications peuvent être hints.

---

# 121. Logging dependency rule

Domain ne doit pas dépendre directement de logging infrastructure.

---

# 122. Domain logging

Si besoin exceptionnel :

```text
domain events
```

préférables aux logs techniques.

---

# 123. Telemetry dependency rule

Application peut dépendre d’un :

```text
TelemetryPort
```

mais pas d’OpenTelemetry SDK.

---

# 124. Audit dependency rule

Application peut dépendre de :

```text
AuditPublisher/AuditStore port
```

sans importer persistence implementation.

---

# 125. Security dependency rule

Domain Governance peut définir :

```text
Principal
AuthorizationDecision
PolicyDecision
```

mais pas importer OIDC/JWT.

---

# 126. Secret dependency rule

Domain/Application utilisent :

```text
SecretReference
SecretProvider port
```

jamais les mécanismes provider.

---

# 127. Filesystem dependency rule

Domain ne manipule pas des chemins locaux comme identité durable d’Artifact.

---

# 128. Network dependency rule

Aucun appel HTTP depuis Domain/Application hors port.

---

# 129. Time dependency rule

Éviter `datetime.now()` dispersé dans le Domain.

Utiliser :

```text
ClockPort / injected time
```

sauf objets de construction explicitement fournis.

---

# 130. Randomness dependency rule

IDs générés via factory/typed ID abstraction si testabilité nécessaire.

---

# 131. Environment dependency rule

Domain/Application ne lit pas directement :

```text
os.environ
```

---

# 132. Configuration dependency rule

Environment parsing appartient à bootstrap/adapters.

---

# 133. CLI dependency rule

Domain/Application ne dépend jamais de Click/Typer/argparse.

---

# 134. HTTP dependency rule

Domain/Application ne dépend jamais de FastAPI/Starlette/Flask.

---

# 135. ORM dependency rule

Domain/Application ne dépend jamais de SQLAlchemy models.

---

# 136. Serialization dependency rule

Domain entities ne doivent pas nécessairement être les modèles JSON publics.

---

# 137. Pydantic boundary rule

Si Pydantic est retenu :

```text
allowed in contracts/api/application DTOs
```

selon ADR.

Mais éviter de rendre le Domain dépendant de comportements de validation/serialization spécifiques sans décision explicite.

---

# 138. Backward compatibility dependency rule

V1 compatibility peut temporairement importer des internals historiques.

V2 core ne doit jamais importer V1 compat.

---

# 139. Migration script dependency rule

Scripts migration peuvent connaître :

```text
V1 persistence
V2 persistence
```

car ils jouent un rôle ACL entre générations.

---

# 140. Migration script isolation

Ces dépendances doivent rester dans :

```text
migration tooling
compat
scripts
```

pas le runtime normal V2.

---

# 141. Packaging boundary

Packages extras doivent correspondre aux adapters.

---

# 142. Optional adapter import smoke tests

CI doit tester au moins :

```text
pip install .
python -c "import pyagentskit"
```

sans extras.

---

# 143. Extra-specific smoke tests

Puis :

```text
pip install .[postgres]
pip install .[langgraph]
...
```

---

# 144. Dependency pinning

Les adapters externes doivent déclarer des ranges compatibles et testés.

---

# 145. Upper bounds

À utiliser lorsque provider SDK casse fréquemment ou si nécessaire à la stabilité.

---

# 146. Transitive dependency audit

CI/release doit surveiller les dépendances sensibles.

---

# 147. Supply-chain boundary

Runtime adapters/connectors sont des zones à risque supply-chain plus élevé.

---

# 148. Architectural ownership

Chaque package majeur doit avoir :

```text
owner
purpose
allowed dependencies
forbidden dependencies
```

documentés.

---

# 149. Suggested package README

Chaque package `domain/<context>/` peut contenir un README expliquant :

```text
Purpose
Owns
Does not own
Dependencies
Published Language
Invariants
```

---

# 150. PR review checklist — imports

Chaque PR vérifie :

```text
Did this change add a new dependency direction?
Could this use a port instead?
Is a provider type leaking inward?
Is Shared Kernel growing?
Is a runtime/connector importing a sibling?
```

---

# 151. PR review checklist — models

```text
Is this model domain, application, adapter or API?
Does it have one owner?
Is it reused only because fields look similar?
```

---

# 152. PR review checklist — infrastructure

```text
Does infrastructure decide business semantics?
Does adapter hide ambiguity?
Does retry cross Effect safety boundary?
```

---

# 153. Architecture exception process

Une exception doit inclure :

```text
reason
scope
owner
expiry/review date
ADR
test exclusion if needed
```

---

# 154. No permanent silent exceptions

Toute suppression d’une règle CI doit être visible.

---

# 155. Architecture debt register

Créer éventuellement :

```text
docs/architecture/ARCHITECTURE_DEBT.md
```

pour les exceptions temporaires.

---

# 156. Enforcement levels

```text
LEVEL 0 — documented only
LEVEL 1 — reviewed manually
LEVEL 2 — static checked
LEVEL 3 — CI-blocking
```

Cible V2 :

```text
critical dependency rules = LEVEL 3
```

---

# 157. CI architecture job

Exemple :

```text
lint
typecheck
unit
architecture
contracts
integration
```

---

# 158. Architecture CI failures

Une violation de dépendance doit bloquer le merge.

---

# 159. Exemptions

Uniquement :

```text
compat
migration
explicit test fixtures
```

avec justification.

---

# 160. Rule DR-074 — Public API imports are separately frozen

Architecture interne peut évoluer sans casser :

```text
pyagentskit.api
```

si les façades restent compatibles.

---

# 161. Rule DR-075 — Root package stays minimal

Éviter de réexporter tous les internals V2 dans :

```text
pyagentskit.__init__
```

---

# 162. Rule DR-076 — Namespaced public contracts preferred

Exemples :

```text
pyagentskit.api
pyagentskit.contracts
pyagentskit.runtime
```

selon design final.

---

# 163. Rule DR-077 — No convenience import that violates boundaries

Ne pas créer un re-export depuis Domain qui force le chargement de PostgreSQL ou runtime SDK.

---

# 164. Circular type ownership

Si deux contexts ont besoin de se référencer :

```text
use IDs / references
```

pas imports mutuels.

---

# 165. Example — Run and Effect

Bon :

```python
class Run:
    pending_effect_ids: tuple[EffectId, ...]
```

Pas :

```python
class Run:
    effects: list[Effect]
```

---

# 166. Example — Approval and Effect

Bon :

```python
class ApprovalScope:
    effect_id: EffectId
    fingerprint: InputFingerprint
```

Pas :

```python
class Approval:
    effect: Effect
```

---

# 167. Example — RuntimeInvocation and RuntimeHandle

Bon :

```text
RuntimeInvocation
contains canonical RuntimeHandle
```

Pas :

```text
LangGraphThread
CodexProcess
```

---

# 168. Example — Artifact

Bon :

```text
ArtifactReference
```

Pas :

```text
boto3.Object
```

---

# 169. Runtime callback dependency rule

Runtime callback vers core doit entrer via :

```text
inbound application port
```

ou event mapping.

Pas via mutation directe d’aggregate interne.

---

# 170. Tool interception dependency rule

Runtime adapter transmet l’intention au :

```text
EffectGateway
```

Il ne l’exécute pas automatiquement si protected.

---

# 171. Connector reconciliation dependency rule

Connector peut implémenter `ReconciliationPort`.

Mais le choix de lancer reconciliation appartient à Application/Effects.

---

# 172. Coordination dependency rule

LeaseRepository est appelé par Application Coordination.

Pas par runtime adapter directement sauf wrapper explicitement injecté et contrôlé.

---

# 173. Worker dependency rule

Worker Loop est inbound adapter.

Il appelle Application.

Il ne devient pas un mega-service contenant toute la logique.

---

# 174. Scheduling dependency rule

Si scheduler externe :

```text
Scheduler
→ inbound adapter/command
```

PyAgentsKit core ne dépend pas du scheduler.

---

# 175. Message broker dependency rule

Broker :

```text
adapter
```

et non source de vérité.

---

# 176. Queue delivery rule

```text
queue delivery != ownership
```

doit être visible jusque dans l’architecture.

---

# 177. Caching adapter rule

Cache adapter peut décorer des lectures non critiques.

Il ne doit pas devenir autoritatif.

---

# 178. Read replica rule

Même principe.

---

# 179. Cross-package constants

Éviter un package :

```text
constants.py
```

global massif.

Les constantes métier appartiennent au context propriétaire.

---

# 180. Cross-package enums

Même règle.

```text
RunState
```

reste Execution.

```text
EffectStatus
```

reste Effects.

---

# 181. Generic helpers rule

Éviter :

```text
utils.py
helpers.py
common.py
```

sans ownership clair.

---

# 182. Utility extraction rule

Une fonction utilitaire ne rejoint shared que si :

```text
pure
stable
generic
non-domain-specific
```

---

# 183. Serialization helper rule

Peut vivre dans :

```text
contracts/serialization.py
```

si vraiment transversal.

---

# 184. Domain factory rule

Factories métier restent dans le contexte.

---

# 185. Adapter factory rule

Factories techniques restent dans bootstrap/adapters.

---

# 186. Dependency documentation automation

Possibilité de générer :

```text
module graph
```

dans CI pour détecter dérive.

---

# 187. Architecture visualization

Outils possibles :

```text
pydeps
grimp
import-linter graph
```

selon compatibilité.

---

# 188. Change detection

Un PR qui ajoute une nouvelle arête de dépendance peut nécessiter review architecture.

---

# 189. Forbidden dependency examples

```text
domain.effects -> adapters.connectors.github
domain.execution -> postgres
application.recovery -> langgraph
api -> psycopg
codex adapter -> github connector
github connector -> approval repository
```

---

# 190. Allowed dependency examples

```text
application.recovery -> AgentRuntimeAdapter port
application.effects -> Connector port
postgres adapter -> EffectRepository protocol
native runtime adapter -> V1 Runner
api async client -> RunCommandPort
bootstrap -> PostgresRunRepository
```

---

# 191. Transitional dependency rules

Pendant migration V1→V2, certaines exceptions existent.

Exemple :

```text
NativeRuntimeAdapter -> V1 Runner
```

est temporairement/structurellement accepté.

---

# 192. Transitional rule expiry

Une exception doit indiquer :

```text
permanent compatibility boundary
or
target removal release
```

---

# 193. V1 import freeze

Les V1 public imports restent testés séparément.

---

# 194. V2 internal evolution

La V2 peut refactorer internals tant que :

```text
public contracts
port contracts
migration guarantees
```

restent respectés.

---

# 195. Dependency Rules Acceptance Criteria

Le modèle est correctement appliqué si :

1. Domain n’importe ni Application ni Adapter ;
2. Application n’importe aucun adapter concret ;
3. API ne contourne pas Application ;
4. Bootstrap est le seul composition root concret ;
5. les Bounded Contexts ne partagent pas leurs aggregates ;
6. Shared Kernel reste minimal ;
7. runtime adapters sont indépendants ;
8. connectors sont indépendants ;
9. provider SDK objects restent confinés ;
10. dependencies optionnelles ne sont pas chargées par le core ;
11. production code n’importe jamais `testing` ;
12. les règles sont vérifiées par CI ;
13. les exceptions sont documentées ;
14. aucun cycle de production n’existe ;
15. V1 compatibility n’est jamais importée par le Domain V2.

---

# 196. Definition of Done

Les Package Dependency Rules sont matures lorsque :

1. `import-linter` ou équivalent est configuré ;
2. les règles Domain/Application/Adapters sont CI-blocking ;
3. les runtime adapters ont un contrat d’indépendance ;
4. les connectors ont un contrat d’indépendance ;
5. le Shared Kernel possède une liste d’exports contrôlée ;
6. les optional extras ont des smoke tests ;
7. aucune dépendance infra ne fuit au core ;
8. les cycles sont détectés ;
9. les PRs incluent une architecture review checklist ;
10. les exceptions sont centralisées ;
11. les tests V1 et V2 passent ensemble ;
12. les mappings ACL sont explicites ;
13. les queries cross-context restent non-authoritative ;
14. le root package reste léger ;
15. la topologie peut être reconstruite automatiquement par les outils CI.

---

# 197. Résumé

La topologie PyAgentsKit V2 doit être protégée par des dépendances unidirectionnelles :

```text
BOOTSTRAP
   ↓
API / ADAPTERS
   ↓
APPLICATION
   ↓
DOMAIN
```

Avec une règle encore plus importante entre contextes :

```text
CONTEXT A
does not mutate
CONTEXT B aggregate
```

Les mécanismes utilisés sont :

```text
Published Language
Ports
References
Domain Events
Application orchestration
Anti-Corruption Layers
Minimal Shared Kernel
```

Le principe fondamental est :

> **La qualité de l’architecture ne dépend pas du dessin des dossiers ; elle dépend de l’impossibilité technique de violer leurs frontières sans faire échouer la CI.**

Le document suivant naturel est :

```text
../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md
```
