# PyAgentsKit — Target Codebase Topology
## DDD + Hexagonal Architecture + Ports & Adapters

**Date :** 21 octobre 2026  
**Statut :** Architecture cible recommandée pour PyAgentsKit V2  
**Objet :** Topologie des dossiers, fichiers, bounded contexts, ports, adapters et règles de dépendance

---

# 1. Décision architecturale

La cible recommandée combine :

```text
Domain-Driven Design
+
Hexagonal Architecture
+
Ports & Adapters
+
Application Services
+
Explicit Composition Root
+
Anti-Corruption Layers
```

Le principe fondamental est :

> **Le domaine PyAgentsKit ne connaît ni PostgreSQL, ni LangGraph, ni Codex, ni GitHub, ni OpenTelemetry.**

Ces technologies sont des détails externes branchés sur des ports.

La direction des dépendances est toujours :

```text
INBOUND ADAPTERS
       │
       ▼
APPLICATION
       │
       ▼
DOMAIN
       ▲
       │
OUTBOUND PORTS
       ▲
       │
OUTBOUND ADAPTERS
```

Le `bootstrap` / composition root est le seul endroit autorisé à assembler les deux côtés.

---

# 2. Règle de dépendance

```text
domain
  imports nothing from application/adapters/bootstrap

application
  imports domain
  declares ports
  does not import concrete adapters

adapters
  import domain contracts and application ports
  implement concrete technologies

api/inbound adapters
  call application use cases
  do not orchestrate business rules

bootstrap
  may import everything
  performs dependency injection
```

---

# 3. Vue d’ensemble du repository

```text
pyagentskit/
├── pyproject.toml
├── README.md
├── CHANGELOG.md
├── LICENSE
│
├── src/
│   └── pyagentskit/
│       ├── __init__.py
│       ├── _version.py
│       │
│       ├── contracts/
│       ├── domain/
│       ├── application/
│       ├── adapters/
│       ├── api/
│       ├── bootstrap/
│       ├── compat/
│       └── testing/
│
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── failure/
│   ├── security/
│   ├── e2e/
│   └── compatibility/
│
├── docs/
│   ├── architecture/
│   ├── adr/
│   ├── concepts/
│   ├── guides/
│   ├── runbooks/
│   └── migration/
│
├── examples/
│   ├── native/
│   ├── langgraph/
│   ├── coding_agents/
│   └── distributed/
│
└── scripts/
    ├── release_check.py
    ├── db_migrate.py
    └── qualification/
```

---

# 4. Topologie cible détaillée

```text
src/pyagentskit/
│
├── __init__.py
├── _version.py
│
├── contracts/
│   ├── __init__.py
│   ├── ids.py
│   ├── errors.py
│   ├── events.py
│   ├── pagination.py
│   ├── correlation.py
│   └── serialization.py
│
├── domain/
│   │
│   ├── shared/
│   │   ├── __init__.py
│   │   ├── entity.py
│   │   ├── aggregate.py
│   │   ├── value_object.py
│   │   ├── domain_event.py
│   │   ├── errors.py
│   │   └── time.py
│   │
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── run.py
│   │   ├── run_state.py
│   │   ├── checkpoint.py
│   │   ├── runtime_invocation.py
│   │   ├── recovery.py
│   │   ├── events.py
│   │   ├── policies.py
│   │   └── errors.py
│   │
│   ├── effects/
│   │   ├── __init__.py
│   │   ├── effect.py
│   │   ├── effect_state.py
│   │   ├── idempotency.py
│   │   ├── external_reference.py
│   │   ├── reconciliation.py
│   │   ├── risk.py
│   │   ├── events.py
│   │   └── errors.py
│   │
│   ├── governance/
│   │   ├── __init__.py
│   │   ├── approval.py
│   │   ├── approval_scope.py
│   │   ├── approval_policy.py
│   │   ├── principal.py
│   │   ├── authorization.py
│   │   ├── segregation_of_duties.py
│   │   ├── events.py
│   │   └── errors.py
│   │
│   ├── coordination/
│   │   ├── __init__.py
│   │   ├── lease.py
│   │   ├── fencing.py
│   │   ├── ownership.py
│   │   ├── resource_identity.py
│   │   ├── worker.py
│   │   ├── events.py
│   │   └── errors.py
│   │
│   ├── conversations/
│   │   ├── __init__.py
│   │   ├── session.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── actor.py
│   │   ├── participant.py
│   │   ├── memory.py
│   │   ├── events.py
│   │   └── errors.py
│   │
│   ├── runtime_integration/
│   │   ├── __init__.py
│   │   ├── descriptor.py
│   │   ├── capabilities.py
│   │   ├── runtime_handle.py
│   │   ├── runtime_status.py
│   │   ├── runtime_event.py
│   │   └── errors.py
│   │
│   ├── artifacts/
│   │   ├── __init__.py
│   │   ├── artifact.py
│   │   ├── checksum.py
│   │   ├── provenance.py
│   │   └── errors.py
│   │
│   └── audit/
│       ├── __init__.py
│       ├── audit_event.py
│       ├── audit_subject.py
│       ├── audit_action.py
│       └── errors.py
│
├── application/
│   │
│   ├── ports/
│   │   │
│   │   ├── inbound/
│   │   │   ├── __init__.py
│   │   │   ├── run_commands.py
│   │   │   ├── run_queries.py
│   │   │   ├── effect_commands.py
│   │   │   ├── approval_commands.py
│   │   │   ├── conversation_commands.py
│   │   │   └── admin_commands.py
│   │   │
│   │   └── outbound/
│   │       ├── __init__.py
│   │       │
│   │       ├── repositories/
│   │       │   ├── run_repository.py
│   │       │   ├── session_repository.py
│   │       │   ├── conversation_repository.py
│   │       │   ├── message_repository.py
│   │       │   ├── effect_repository.py
│   │       │   ├── reconciliation_repository.py
│   │       │   ├── approval_repository.py
│   │       │   ├── lease_repository.py
│   │       │   ├── worker_repository.py
│   │       │   └── audit_repository.py
│   │       │
│   │       ├── runtime/
│   │       │   ├── agent_runtime_adapter.py
│   │       │   └── runtime_registry.py
│   │       │
│   │       ├── connectors/
│   │       │   ├── connector.py
│   │       │   ├── connector_registry.py
│   │       │   └── reconciliation_port.py
│   │       │
│   │       ├── security/
│   │       │   ├── authorization_port.py
│   │       │   ├── identity_provider.py
│   │       │   ├── secret_provider.py
│   │       │   └── policy_evaluator.py
│   │       │
│   │       ├── storage/
│   │       │   ├── blob_store.py
│   │       │   └── artifact_store.py
│   │       │
│   │       ├── messaging/
│   │       │   ├── outbox_store.py
│   │       │   ├── inbox_store.py
│   │       │   └── event_publisher.py
│   │       │
│   │       ├── telemetry/
│   │       │   ├── telemetry_port.py
│   │       │   └── audit_publisher.py
│   │       │
│   │       └── unit_of_work.py
│   │
│   ├── execution/
│   │   ├── __init__.py
│   │   ├── create_run.py
│   │   ├── start_run.py
│   │   ├── resume_run.py
│   │   ├── pause_run.py
│   │   ├── cancel_run.py
│   │   ├── inspect_run.py
│   │   └── durable_runner.py
│   │
│   ├── recovery/
│   │   ├── __init__.py
│   │   ├── recovery_planner.py
│   │   ├── recover_run.py
│   │   ├── recovery_policy.py
│   │   └── next_action.py
│   │
│   ├── effects/
│   │   ├── __init__.py
│   │   ├── plan_effect.py
│   │   ├── execute_effect.py
│   │   ├── reconcile_effect.py
│   │   ├── resolve_effect.py
│   │   └── effect_gateway.py
│   │
│   ├── governance/
│   │   ├── __init__.py
│   │   ├── request_approval.py
│   │   ├── decide_approval.py
│   │   ├── revalidate_approval.py
│   │   └── evaluate_policy.py
│   │
│   ├── coordination/
│   │   ├── __init__.py
│   │   ├── acquire_lease.py
│   │   ├── renew_lease.py
│   │   ├── release_lease.py
│   │   ├── takeover.py
│   │   └── worker_controller.py
│   │
│   ├── conversations/
│   │   ├── __init__.py
│   │   ├── create_session.py
│   │   ├── create_conversation.py
│   │   ├── append_message.py
│   │   └── write_memory.py
│   │
│   ├── artifacts/
│   │   ├── __init__.py
│   │   ├── create_artifact.py
│   │   └── load_artifact.py
│   │
│   └── queries/
│       ├── __init__.py
│       ├── run_views.py
│       ├── effect_views.py
│       ├── approval_views.py
│       ├── worker_views.py
│       └── timeline_views.py
│
├── adapters/
│   │
│   ├── inbound/
│   │   ├── __init__.py
│   │   │
│   │   ├── python/
│   │   │   ├── __init__.py
│   │   │   ├── async_client.py
│   │   │   └── sync_client.py
│   │   │
│   │   ├── cli/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── runs.py
│   │   │   ├── effects.py
│   │   │   ├── approvals.py
│   │   │   └── admin.py
│   │   │
│   │   ├── http/
│   │   │   ├── __init__.py
│   │   │   ├── app.py
│   │   │   ├── routes_runs.py
│   │   │   ├── routes_effects.py
│   │   │   ├── routes_approvals.py
│   │   │   ├── routes_health.py
│   │   │   └── schemas.py
│   │   │
│   │   ├── workers/
│   │   │   ├── __init__.py
│   │   │   ├── worker_loop.py
│   │   │   ├── queue_consumer.py
│   │   │   └── shutdown.py
│   │   │
│   │   └── webhooks/
│   │       ├── __init__.py
│   │       ├── receiver.py
│   │       └── signature.py
│   │
│   └── outbound/
│       ├── __init__.py
│       │
│       ├── persistence/
│       │   ├── __init__.py
│       │   │
│       │   ├── memory/
│       │   │   ├── run_repository.py
│       │   │   ├── effect_repository.py
│       │   │   ├── approval_repository.py
│       │   │   └── lease_repository.py
│       │   │
│       │   ├── sqlite/
│       │   │   ├── connection.py
│       │   │   ├── run_repository.py
│       │   │   ├── effect_repository.py
│       │   │   └── approval_repository.py
│       │   │
│       │   └── postgres/
│       │       ├── __init__.py
│       │       ├── connection.py
│       │       ├── unit_of_work.py
│       │       ├── schema.py
│       │       ├── mapping.py
│       │       │
│       │       ├── repositories/
│       │       │   ├── run_repository.py
│       │       │   ├── session_repository.py
│       │       │   ├── conversation_repository.py
│       │       │   ├── message_repository.py
│       │       │   ├── effect_repository.py
│       │       │   ├── reconciliation_repository.py
│       │       │   ├── approval_repository.py
│       │       │   ├── lease_repository.py
│       │       │   ├── worker_repository.py
│       │       │   ├── audit_repository.py
│       │       │   ├── outbox_store.py
│       │       │   └── inbox_store.py
│       │       │
│       │       └── migrations/
│       │           ├── env.py
│       │           └── versions/
│       │
│       ├── runtimes/
│       │   ├── __init__.py
│       │   ├── native/
│       │   │   ├── adapter.py
│       │   │   ├── runner_bridge.py
│       │   │   ├── event_mapper.py
│       │   │   └── checkpoint_mapper.py
│       │   │
│       │   ├── langgraph/
│       │   │   ├── adapter.py
│       │   │   ├── capabilities.py
│       │   │   └── mapper.py
│       │   │
│       │   ├── pydantic_ai/
│       │   │   ├── adapter.py
│       │   │   └── mapper.py
│       │   │
│       │   ├── openai_agents/
│       │   │   ├── adapter.py
│       │   │   └── mapper.py
│       │   │
│       │   └── coding/
│       │       ├── __init__.py
│       │       ├── common/
│       │       │   ├── workspace.py
│       │       │   ├── command.py
│       │       │   ├── git.py
│       │       │   └── effects.py
│       │       ├── codex/
│       │       │   ├── adapter.py
│       │       │   └── process.py
│       │       ├── claude_code/
│       │       │   ├── adapter.py
│       │       │   └── process.py
│       │       └── opencode/
│       │           ├── adapter.py
│       │           └── process.py
│       │
│       ├── models/
│       │   ├── __init__.py
│       │   ├── openai.py
│       │   ├── anthropic.py
│       │   ├── google.py
│       │   ├── xai.py
│       │   ├── openrouter.py
│       │   └── ollama.py
│       │
│       ├── connectors/
│       │   ├── __init__.py
│       │   ├── github/
│       │   │   ├── connector.py
│       │   │   ├── reconciliation.py
│       │   │   └── mapper.py
│       │   ├── gitlab/
│       │   ├── slack/
│       │   ├── email/
│       │   ├── jira/
│       │   ├── stripe/
│       │   ├── aws/
│       │   ├── azure/
│       │   └── generic_http/
│       │
│       ├── storage/
│       │   ├── filesystem.py
│       │   ├── s3.py
│       │   └── azure_blob.py
│       │
│       ├── security/
│       │   ├── environment_secrets.py
│       │   ├── oidc.py
│       │   ├── authorization.py
│       │   └── policy_engine.py
│       │
│       └── telemetry/
│           ├── logging.py
│           ├── metrics.py
│           ├── opentelemetry.py
│           └── audit.py
│
├── api/
│   ├── __init__.py
│   ├── client.py
│   ├── async_client.py
│   ├── sync_client.py
│   ├── run_view.py
│   ├── effect_view.py
│   ├── approval_view.py
│   ├── artifact_view.py
│   └── errors.py
│
├── bootstrap/
│   ├── __init__.py
│   ├── config.py
│   ├── container.py
│   ├── factories.py
│   ├── profiles.py
│   └── health.py
│
├── compat/
│   └── v1/
│       ├── __init__.py
│       ├── runner.py
│       ├── durability.py
│       ├── approvals.py
│       ├── sessions.py
│       └── exports.py
│
└── testing/
    ├── __init__.py
    ├── fakes.py
    ├── fixtures.py
    ├── fake_runtime.py
    ├── fake_connector.py
    ├── fault_injection.py
    └── assertions.py
```

---

# 5. Les Bounded Contexts

La topologie du `domain/` ne doit pas être organisée par technologie.

Elle doit refléter le langage métier PyAgentsKit.

## 5.1 Execution

Responsable de :

```text
Run
RunState
Checkpoint
RuntimeInvocation
Recovery state
```

Il ne connaît pas :

```text
PostgreSQL
LangGraph
HTTP
S3
```

---

## 5.2 Effects

Responsable de :

```text
Effect
EffectStatus
EffectRiskLevel
IdempotencyKey
InputFingerprint
ExternalReference
ReconciliationCase
```

C’est ici que résident les invariants :

```text
SUCCEEDED Effect is not implicitly replayed
UNKNOWN != FAILED
```

---

## 5.3 Governance

Responsable de :

```text
Approval
ApprovalScope
Principal
Authorization decision
Policy decision
SoD
```

Important :

```text
Authentication
!=
Authorization
!=
Approval
```

---

## 5.4 Coordination

Responsable de :

```text
Lease
FencingToken
OwnershipContext
Worker
ResourceIdentity
```

Invariants :

```text
one authoritative owner
monotonic fencing
stale worker rejected
```

---

## 5.5 Conversations

Responsable de :

```text
Session
Conversation
Actor
Participant
Message
MemoryEntry
```

Ici la cible impose réellement :

```text
Session != Conversation
```

---

## 5.6 Runtime Integration

Ce contexte représente les concepts neutres de runtime :

```text
RuntimeDescriptor
RuntimeCapability
RuntimeHandle
RuntimeStatus
RuntimeEvent
```

Attention :

```text
LangGraph object
Codex process
Claude Code session
```

n’appartiennent jamais au domaine.

Ils vivent dans les adapters.

---

## 5.7 Artifacts

Responsable des métadonnées métier :

```text
Artifact
Checksum
Provenance
```

Le stockage S3/Azure/FileSystem est un détail adapter.

---

## 5.8 Audit

Responsable de l’événement d’audit durable.

Il ne faut pas le confondre avec :

```text
runtime event
log
trace
metric
```

---

# 6. Application Layer

Le domaine contient les règles.

L’application contient les **cas d’usage**.

Exemple :

```text
ResumeRun
```

peut orchestrer :

```text
RunRepository
LeaseRepository
EffectRepository
ApprovalRepository
AgentRuntimeAdapter
RecoveryPlanner
AuditPublisher
```

mais la logique métier elle-même reste dans les objets/services du domaine.

---

# 7. Ports entrants

Les ports entrants définissent ce que l’extérieur peut demander à PyAgentsKit.

Exemples :

```text
CreateRun
StartRun
ResumeRun
CancelRun
Approve
Reject
ReconcileEffect
AppendMessage
```

Ils sont appelés par :

```text
Python SDK
CLI
HTTP
queue consumer
webhook receiver
```

---

# 8. Ports sortants

Les ports sortants expriment ce dont les cas d’usage ont besoin.

Exemple :

```python
class RunRepository(Protocol):
    async def get(self, run_id: RunId) -> Run: ...
    async def save(self, run: Run, expected_version: int) -> None: ...
```

L’application ne sait pas si cela utilise :

```text
PostgreSQL
SQLite
Memory
```

---

# 9. AgentRuntimeAdapter

C’est le port le plus important de la V2.

Il doit vivre dans :

```text
application/ports/outbound/runtime/agent_runtime_adapter.py
```

Contrat conceptuel :

```python
class AgentRuntimeAdapter(Protocol):
    async def start(self, request: RuntimeStartRequest) -> RuntimeHandle:
        ...

    async def resume(
        self,
        handle: RuntimeHandle,
        request: RuntimeResumeRequest,
    ) -> RuntimeHandle:
        ...

    async def inspect(self, handle: RuntimeHandle) -> RuntimeStatus:
        ...

    async def cancel(self, handle: RuntimeHandle) -> None:
        ...

    async def checkpoint(
        self,
        handle: RuntimeHandle,
    ) -> RuntimeCheckpoint | None:
        ...

    def events(
        self,
        handle: RuntimeHandle,
    ) -> AsyncIterator[RuntimeEvent]:
        ...
```

Implémentations :

```text
NativePyAgentsRuntimeAdapter
LangGraphRuntimeAdapter
PydanticAIRuntimeAdapter
OpenAIAgentsRuntimeAdapter
CodexRuntimeAdapter
ClaudeCodeRuntimeAdapter
```

---

# 10. Anti-Corruption Layer

Chaque runtime adapter doit traduire :

```text
runtime-native model
        ↕
PyAgentsKit canonical model
```

Exemple :

```text
LangGraph checkpoint
→ RuntimeCheckpoint

Codex process/session id
→ RuntimeHandle

Claude Code event
→ RuntimeEvent
```

Jamais :

```text
LangGraphState
CodexSDKObject
ClaudeCodeSession
```

dans le domaine.

---

# 11. Connectors ≠ Runtime Adapters

Il faut séparer clairement :

```text
Runtime Adapter
= exécute/pilote un agent runtime

Connector
= parle à un système métier/externe
```

Exemple :

```text
Codex
→ Runtime Adapter

GitHub
→ Connector

Stripe
→ Connector

Slack
→ Connector
```

Un coding runtime peut demander un Effect :

```text
git push
```

mais l’Effect peut être exécuté par :

```text
GitHubConnector
```

ou par une primitive Git contrôlée.

---

# 12. Native Runtime

Le `Runner` V1 actuel ne doit pas disparaître.

Il devient :

```text
adapters/outbound/runtimes/native/
```

Conceptuellement :

```text
NativeRuntimeAdapter
    │
    └── current Runner
```

Le code existant :

```text
Model
ToolExecutor
Guardrails
Provider adapters
```

continue donc d’exister comme **runtime natif**.

---

# 13. Models providers

Les actuels :

```text
OpenAI
Anthropic
Google
xAI
OpenRouter
Ollama
```

ne sont pas des `AgentRuntimeAdapter`.

Ils restent des :

```text
Model adapters
```

utilisés par le `NativeRuntimeAdapter`.

D’où la séparation :

```text
adapters/outbound/models/
```

et :

```text
adapters/outbound/runtimes/
```

---

# 14. Tool Gateway

Le Tool Gateway appartient à l’application, pas à un adapter.

Flux :

```text
Runtime
↓
Tool request
↓
Tool Gateway
↓
Risk classification
↓
Authorization
↓
Policy
↓
Approval
↓
Lease/Fencing validation
↓
Effect reservation
↓
Connector / Tool adapter
↓
Effect outcome
↓
Audit
```

Il peut vivre dans :

```text
application/effects/effect_gateway.py
```

---

# 15. Persistence

PostgreSQL est un adapter.

Donc :

```text
domain
```

ne contient jamais :

```text
SQL
ORM
psycopg
SQLAlchemy
Alembic
```

Tout cela appartient à :

```text
adapters/outbound/persistence/postgres/
```

---

# 16. Mapping PostgreSQL

Il faut séparer :

```text
Domain Model
```

de :

```text
Persistence Model
```

Exemple :

```text
domain.effects.Effect
         ↓ mapper
Postgres Effect row
```

Le fichier :

```text
mapping.py
```

ou les mappers par repository assurent cette transformation.

---

# 17. Unit of Work

Le port :

```text
application/ports/outbound/unit_of_work.py
```

définit :

```text
begin
commit
rollback
```

sans exposer :

```text
psycopg connection
SQLAlchemy Session
```

L’adapter PostgreSQL fournit l’implémentation.

---

# 18. Public API

Le package :

```text
api/
```

n’est pas le domaine.

Il fournit des modèles publics stables :

```text
RunView
EffectView
ApprovalView
ArtifactView
```

Il appelle les ports entrants.

Il ne retourne jamais :

```text
SQLAlchemy object
database row
runtime SDK object
```

---

# 19. API Python

Surface candidate :

```python
from pyagentskit.api import PyAgentsKit

kit = PyAgentsKit(...)

run = await kit.runs.create(...)
await kit.runs.start(run.run_id)
```

Cette façade est un inbound adapter.

---

# 20. HTTP API

Si ajoutée :

```text
adapters/inbound/http/
```

Elle convertit :

```text
HTTP request
→ application command
→ application response
→ HTTP response
```

Aucune règle de métier dans les routes.

---

# 21. Bootstrap / Composition Root

`bootstrap/` est crucial.

C’est le seul endroit qui peut faire :

```python
run_repository = PostgresRunRepository(...)
runtime = LangGraphRuntimeAdapter(...)
authorization = OIDCAuthorizationAdapter(...)
audit = PostgresAuditRepository(...)

service = ResumeRun(
    run_repository=run_repository,
    runtime=runtime,
    authorization=authorization,
    audit=audit,
)
```

---

# 22. Profiles

`bootstrap/profiles.py` peut proposer :

```text
LocalProfile
SQLiteProfile
PostgresProfile
DistributedWorkerProfile
HighAssuranceProfile
```

sans mettre ces choix dans le domaine.

---

# 23. Compatibility V1

La V1 possède un contrat public fort.

Il ne faut pas détruire immédiatement :

```text
pyagentskit.Runner
pyagentskit.DurableRunner
pyagentskit.SessionStore
...
```

Approche :

```text
compat/v1/
```

puis les anciens modules peuvent devenir des façades/re-exports.

Exemple conceptuel :

```python
# pyagentskit/runtime.py
from pyagentskit.compat.v1.runner import Runner
```

ou garder temporairement l’implémentation actuelle en place et migrer par strangler pattern.

---

# 24. Strangler migration

Ordre conseillé :

```text
existing V1
   │
   ├── remains green
   │
   └── progressively wrapped
          by V2 ports
```

Premier adapter V2 :

```text
NativePyAgentsRuntimeAdapter
```

qui encapsule la V1.

---

# 25. Mapping de l’existant

| Fichier actuel | Cible |
|---|---|
| `runtime.py` | `adapters/outbound/runtimes/native/` + extraction application |
| `durability.py` | `domain/execution`, `domain/effects`, `application/recovery` |
| `distributed.py` | `domain/coordination`, `application/coordination`, telemetry adapter |
| `coordination.py` | `domain/coordination` + persistence adapters |
| `approvals.py` | `domain/governance` + application + repositories |
| `sessions.py` | `domain/conversations/session.py` + repositories |
| `messages.py` | split `RuntimeMessage` vs `ConversationMessage` |
| `memory.py` | `domain/conversations/memory.py` |
| `postgres.py` | `adapters/outbound/persistence/postgres/` |
| `postgres_state.py` | idem, puis décomposition par repository |
| `artifact_store.py` | domain artifacts + storage port |
| `blobs.py` | outbound storage adapters |
| `observability.py` | telemetry adapter |
| `telemetry.py` | outbound telemetry |
| `providers/` | `adapters/outbound/models/` |
| `ports.py` | éclaté en ports spécifiques |
| `tools.py` | capability contract + application effect gateway |

---

# 26. Fichiers à éviter dans la cible

Éviter les fichiers fourre-tout tels que :

```text
models.py
ports.py
services.py
utils.py
common.py
helpers.py
```

lorsqu’ils grossissent.

Ils deviennent rapidement des zones sans frontière métier.

Préférer :

```text
effect.py
approval.py
lease.py
agent_runtime_adapter.py
run_repository.py
```

---

# 27. Agrégats recommandés

Agrégats principaux :

```text
Run
Effect
Approval
Conversation
Session
Lease
```

Important :

```text
Run
```

ne doit pas contenir en mémoire :

```text
all Effects
all Messages
all AuditEvents
```

sinon il devient un aggregate gigantesque.

---

# 28. Références entre agrégats

Utiliser :

```text
RunId
EffectId
ApprovalId
ConversationId
```

plutôt que références Python directes.

Exemple :

```text
Approval
  effect_id: EffectId
```

et non :

```text
Approval.effect: Effect
```

---

# 29. Domain Events

Chaque aggregate peut produire :

```text
RunStarted
RunWaiting
EffectPlanned
EffectSucceeded
EffectBecameUnknown
ApprovalRequested
ApprovalApproved
LeaseTakenOver
```

Ces Domain Events ne sont pas encore :

```text
Kafka event
Webhook
OpenTelemetry span
AuditEvent
```

L’application/adapters décident de la projection.

---

# 30. AuditEvent ≠ DomainEvent

Exemple :

```text
EffectSucceeded
```

est un DomainEvent.

Il peut provoquer :

```text
AuditEvent
OutboxEvent
Metric
Trace event
```

mais ces objets ne sont pas identiques.

---

# 31. Outbox/Inbox

Ils appartiennent à l’infrastructure/persistence mais sont exposés via ports.

```text
application
→ OutboxStore port
→ PostgresOutboxStore
```

et :

```text
Webhook/Queue
→ InboxStore
→ application command
```

---

# 32. Tests cible

```text
tests/
│
├── unit/
│   ├── domain/
│   │   ├── execution/
│   │   ├── effects/
│   │   ├── governance/
│   │   └── coordination/
│   └── application/
│
├── contract/
│   ├── run_repository_contract.py
│   ├── effect_repository_contract.py
│   ├── approval_repository_contract.py
│   ├── lease_repository_contract.py
│   ├── runtime_adapter_contract.py
│   └── connector_contract.py
│
├── integration/
│   ├── postgres/
│   ├── sqlite/
│   ├── runtimes/
│   │   ├── native/
│   │   ├── langgraph/
│   │   └── coding/
│   └── connectors/
│
├── failure/
│   ├── sigterm/
│   ├── sigkill/
│   ├── sigstop/
│   ├── postgres_outage/
│   ├── effect_ambiguity/
│   └── restore/
│
├── security/
│   ├── tenant_isolation/
│   ├── stale_fencing/
│   ├── approval_bypass/
│   └── secret_leakage/
│
├── e2e/
│   ├── durable_run/
│   ├── distributed_takeover/
│   ├── approval_resume/
│   └── coding_agent/
│
└── compatibility/
    └── v1/
```

---

# 33. Contract tests

Chaque adapter doit passer le même contrat.

Exemple :

```text
RunRepositoryContract
```

testé contre :

```text
MemoryRunRepository
SQLiteRunRepository
PostgresRunRepository
```

Même logique pour :

```text
AgentRuntimeAdapterContract
ConnectorContract
LeaseRepositoryContract
ArtifactStoreContract
```

---

# 34. Import architecture tests

Ajouter `import-linter` ou équivalent.

Règles :

```text
domain !-> application
domain !-> adapters
domain !-> api
domain !-> bootstrap

application !-> adapters
application !-> bootstrap

adapters !-> bootstrap

runtime adapter A !-> runtime adapter B
connector A !-> connector B
```

---

# 35. Bounded Context dependency map

```text
Conversations
      │
      ▼
Execution
  │   │   │
  │   │   └──────────► Runtime Integration
  │   │
  │   ├──────────────► Governance
  │
  ├──────────────────► Effects
  │
  └──────────────────► Coordination

Effects
  ├──────────────────► Governance
  └──────────────────► Audit

All application contexts
  └──────────────────► Audit / Telemetry via ports
```

Les dépendances doivent être minimales.

---

# 36. Runtime invocation vs Run

Séparation importante :

```text
Run
= intention métier durable

RuntimeInvocation
= tentative concrète d’un runtime
```

Un Run peut avoir :

```text
Invocation #1 worker A
↓ crash
Invocation #2 worker B
↓ resume
```

sans devenir un nouveau Run.

---

# 37. Session vs Conversation

```text
Session
= contexte durable global

Conversation
= thread de communication

Message
= unité de communication
```

Un Session peut contenir plusieurs Conversations.

---

# 38. Effect vs ToolCall

```text
ToolCall
= demande du runtime

Effect
= conséquence durable gouvernée
```

Tous les ToolCalls ne sont pas des Effects.

Tous les Effects ne sont pas nécessairement des ToolCalls.

---

# 39. Repository vs Store

Convention recommandée :

```text
Repository
= persistance d’un aggregate métier

Store
= infrastructure technique / append-only / blob / outbox
```

Donc :

```text
RunRepository
EffectRepository
ApprovalRepository

BlobStore
OutboxStore
InboxStore
AuditStore
```

---

# 40. Commands and Queries

Éviter une classe `PyAgentsKitService` géante.

Préférer des use cases ciblés :

```text
CreateRun
ResumeRun
ReconcileEffect
ApproveRequest
AcquireLease
AppendMessage
```

---

# 41. DTOs

Les DTOs applicatifs ne sont pas les Entities.

Exemple :

```text
CreateRunCommand
RunView
```

distincts de :

```text
domain.execution.Run
```

---

# 42. Pas d’ORM dans le Domain

Interdit :

```python
class Run(Base):
    __tablename__ = "runs"
```

dans `domain/`.

Le Domain Model doit être indépendant du stockage.

---

# 43. Pas de SDK provider dans les Entities

Interdit :

```python
class RuntimeInvocation:
    langgraph_state: LangGraphState
```

Préférer :

```python
runtime_handle: RuntimeHandle
```

opaque et canonique.

---

# 44. Pas de `if runtime == ...` dans le core

Interdit :

```python
if runtime == "codex":
    ...
elif runtime == "langgraph":
    ...
```

Cette logique appartient au registry + adapter.

---

# 45. Pas de `if provider == ...` dans Effect

Même principe.

---

# 46. Configuration

Les objets configuration appartiennent à :

```text
bootstrap/config.py
```

ou `contracts/` s’ils sont publics.

Pas dans les Entities métier.

---

# 47. Configuration runtime

```text
RuntimeDescriptor
```

peut référencer :

```text
adapter name
capabilities
control level
```

mais les credentials/config provider concrets restent dans l’adapter/bootstrap.

---

# 48. Composition Root

Exemple conceptuel :

```python
def build_postgres_distributed_app(settings):
    run_repo = PostgresRunRepository(...)
    effect_repo = PostgresEffectRepository(...)
    lease_repo = PostgresLeaseRepository(...)

    runtime_registry = RuntimeRegistry()
    runtime_registry.register(
        "native",
        NativeRuntimeAdapter(...),
    )

    return Application(
        runs=RunApplicationService(...),
        effects=EffectApplicationService(...),
        recovery=RecoveryApplicationService(...),
    )
```

---

# 49. Extras Python

Le packaging peut refléter les adapters :

```text
pyagentskit[postgres]
pyagentskit[opentelemetry]
pyagentskit[s3]
pyagentskit[azure]
pyagentskit[langgraph]
pyagentskit[pydantic-ai]
pyagentskit[codex]
pyagentskit[claude-code]
```

Le core doit rester léger.

---

# 50. Core install

```bash
pip install pyagentskit
```

ne doit pas installer automatiquement :

```text
LangGraph
boto3
Azure SDK
psycopg
OpenTelemetry SDK
```

sauf dépendances strictement nécessaires.

---

# 51. Public root

`pyagentskit/__init__.py` doit rester petit.

Il ne doit pas devenir un dumping ground de centaines de symbols.

Pour V2, privilégier :

```python
from pyagentskit.api import PyAgentsKit
from pyagentskit.contracts import RunId
```

Les APIs spécialisées restent namespacées.

---

# 52. Recommendation sur `__all__`

La V1 a figé 155 exports racine.

La V2 devrait réduire la surface racine et stabiliser davantage les namespaces.

---

# 53. Architecture de migration V1 → V2

```text
V1 Runner
   │
   ▼
NativeRuntimeAdapter
   │
   ▼
AgentRuntimeAdapter Port
   │
   ▼
V2 Application
   │
   ▼
V2 Domain
```

Ensuite :

```text
LangGraphAdapter
CodexAdapter
...
```

se branchent au même port.

---

# 54. Ce qui ne doit pas être migré immédiatement

Ne pas déplacer physiquement tout le repository dans une seule PR.

Séquence préférable :

```text
1. créer V2 packages
2. créer ports
3. wrapper V1
4. écrire contract tests
5. migrer un domaine à la fois
6. garder V1 imports verts
7. retirer anciens internals en major release
```

---

# 55. Première découpe de PR recommandée

```text
PR-001
Create empty V2 package topology + import rules

PR-002
Domain shared kernel + typed IDs

PR-003
Execution domain

PR-004
Effects domain

PR-005
Governance domain

PR-006
Coordination domain wrappers over existing Lease/Fencing

PR-007
AgentRuntimeAdapter port

PR-008
NativeRuntimeAdapter over current Runner

PR-009
RuntimeAdapter contract test suite

PR-010
RecoveryPlanner V2
```

Le PostgreSQL normalisé vient après la stabilisation de ces contrats.

---

# 56. Architecture finale simplifiée

```text
                     ┌──────────────────────┐
                     │      INBOUND         │
                     │ Python / CLI / HTTP  │
                     │ Queue / Webhook      │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │    APPLICATION       │
                     │ Use Cases / Recovery │
                     │ Tool/Effect Gateway  │
                     └──────────┬───────────┘
                                │
                                ▼
                     ┌──────────────────────┐
                     │       DOMAIN         │
                     │ Runs / Effects       │
                     │ Approval / Lease     │
                     │ Conversation         │
                     └──────────┬───────────┘
                                │
                      outbound ports
                                │
           ┌────────────────────┼─────────────────────┐
           ▼                    ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│ Runtime Adapters  │ │ Persistence       │ │ Connectors        │
│ Native            │ │ PostgreSQL        │ │ GitHub / Slack    │
│ LangGraph         │ │ SQLite            │ │ Stripe / Cloud    │
│ Codex             │ │ Memory            │ │ ERP / HTTP        │
└───────────────────┘ └───────────────────┘ └───────────────────┘
           │                    │                     │
           ▼                    ▼                     ▼
      Agent runtimes       State stores         External systems
```

---

# 57. Verdict

La meilleure topologie cible pour PyAgentsKit n’est pas :

```text
models/
services/
repositories/
utils/
```

Elle doit faire apparaître explicitement le métier :

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

et séparer radicalement :

```text
DOMAIN
from
APPLICATION
from
PORTS
from
ADAPTERS
from
BOOTSTRAP
```

La règle la plus importante est :

> **Les abstractions métier se trouvent au centre ; les frameworks, bases de données, SDKs, runtimes et fournisseurs tournent autour.**

Cette topologie permet de conserver PyAgentsKit V1 comme runtime natif tout en faisant évoluer la V2 vers une véritable **Agent Reliability Layer framework-neutral**.
