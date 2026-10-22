# PyAgentsKit — Agent Runtime Adapter Specification

**Document :** `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`  
**Version :** 1.0  
**Date :** 19 octobre 2026  
**Statut :** Spécification d’interface / Runtime Integration Contract  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/02_PYAGENTSKIT_PARTIES_PRENANTES_ET_CAS_D_USAGE.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../architecture/08_PYAGENTSKIT_ERD.md`
- `../domain/PYAGENTSKIT_MODELE_CONCEPTUEL_DU_DOMAINE.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`

---

# 1. Objet du document

Ce document spécifie le contrat `AgentRuntimeAdapter` de PyAgentsKit.

Ce contrat constitue la frontière entre :

```text
PyAgentsKit
```

et :

```text
un runtime agentique externe
```

L’objectif est de permettre à PyAgentsKit de fournir les mêmes garanties de fiabilité à plusieurs familles de runtimes sans intégrer leur logique interne dans le core.

Exemples :

```text
LangGraph
PydanticAI
OpenAI Agents SDK
Claude Agent SDK
AutoGen
CrewAI

Codex
Claude Code
OpenCode
Antigravity CLI (agy)

runtime propriétaire
application Python custom
```

Le principe directeur est :

> **PyAgentsKit doit comprendre le cycle de vie et les résultats d’un runtime, sans avoir à comprendre sa manière de raisonner.**

---

# 2. Positionnement du contrat

Le contrat se situe ici :

```text
External Runtime
      │
      ▼
AgentRuntimeAdapter
      │
      ▼
PyAgentsKit Application Layer
      │
      ▼
PyAgentsKit Domain
```

Il joue trois rôles :

```text
1. Port d’intégration
2. Anti-Corruption Layer
3. Capability boundary
```

---

# 3. Objectifs

`AgentRuntimeAdapter` doit permettre :

```text
start
resume
cancel
status inspection
event streaming
context propagation
capability discovery
tool/effect interception
message normalization
checkpoint handoff
```

sans imposer :

```text
graph model
chat model
prompt model
repository model
specific tool protocol
specific provider
```

---

# 4. Non-objectifs

Le contrat ne doit pas :

```text
réimplémenter le runtime
reproduire son moteur de raisonnement
reproduire sa mémoire interne
réimplémenter son terminal
réimplémenter son système de tools
réimplémenter Git
devenir un LLM abstraction layer généraliste
```

---

# 5. Familles de runtimes

## 5.1 Runtimes généralistes

```text
LangGraph
PydanticAI
OpenAI Agents SDK
Claude Agent SDK
AutoGen
CrewAI
```

Ils fournissent principalement :

```text
agent orchestration
tool usage
handoffs
messages
state
sub-agents
```

---

## 5.2 Coding-agent runtimes

```text
Codex
Claude Code
OpenCode
Antigravity CLI (agy)
```

Ils fournissent notamment :

```text
repository understanding
file modification
command execution
tests
git interactions
code generation
```

---

## 5.3 Runtimes propriétaires

Exemples :

```text
internal agent platform
Python service
custom workflow
domain-specific agent runtime
```

---

# 6. Principe d’abstraction

PyAgentsKit doit normaliser uniquement les concepts nécessaires à ses garanties.

Le contrat ne cherche pas à normaliser toute la richesse de chaque runtime.

```text
runtime-specific richness
          │
          ▼
minimal normalized contract
          │
          ▼
PyAgentsKit guarantees
```

---

# 7. Vue conceptuelle du contrat

```text
AgentRuntimeAdapter
├── identity
├── capabilities
├── start()
├── resume()
├── cancel()
├── inspect()
├── events()
├── checkpoint()
└── close()
```

Le contrat réel peut être découpé en plusieurs Protocols spécialisés.

---

# 8. Contrat Python conceptuel

```python
from typing import AsyncIterator, Protocol

class AgentRuntimeAdapter(Protocol):

    @property
    def descriptor(self) -> "RuntimeDescriptor":
        ...

    async def start(
        self,
        request: "RuntimeStartRequest",
    ) -> "RuntimeHandle":
        ...

    async def resume(
        self,
        request: "RuntimeResumeRequest",
    ) -> "RuntimeHandle":
        ...

    async def cancel(
        self,
        request: "RuntimeCancelRequest",
    ) -> "RuntimeCancelResult":
        ...

    async def inspect(
        self,
        handle: "RuntimeHandle",
    ) -> "RuntimeStatus":
        ...

    async def events(
        self,
        handle: "RuntimeHandle",
    ) -> AsyncIterator["NormalizedRuntimeEvent"]:
        ...

    async def checkpoint(
        self,
        handle: "RuntimeHandle",
    ) -> "RuntimeCheckpoint | None":
        ...

    async def close(self) -> None:
        ...
```

Cette API est conceptuelle.

La version publique finale devra être validée par ADR et tests d’usage.

---

# 9. `RuntimeDescriptor`

## Définition

Décrit le runtime supporté par l’adapter.

## Structure conceptuelle

```python
@dataclass(frozen=True)
class RuntimeDescriptor:
    adapter_name: str
    runtime_family: str
    runtime_name: str
    runtime_version: str | None
    adapter_version: str
    capabilities: frozenset["RuntimeCapability"]
```

## Exemple

```text
adapter_name = "claude-agent-sdk"
runtime_family = "general-purpose"
runtime_name = "Claude Agent SDK"
runtime_version = "..."
adapter_version = "1.0"
```

---

# 10. `RuntimeCapability`

Le contrat doit utiliser un modèle de capabilities plutôt que supposer que tous les runtimes savent tout faire.

Capacités candidates :

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

# 11. Capability negotiation

Avant d’utiliser une fonction optionnelle :

```text
PyAgentsKit
↓
adapter.capabilities
↓
supports?
```

Exemple :

```python
if RuntimeCapability.NATIVE_CHECKPOINT in adapter.capabilities:
    ...
```

Le core ne doit jamais supposer une capability non déclarée.

---

# 12. `RuntimeStartRequest`

## Responsabilité

Transmettre au runtime le contexte nécessaire pour démarrer une exécution.

## Structure conceptuelle

```text
run_id
session_id?
conversation_id?
input
runtime_config_reference
correlation_context
ownership_context?
metadata
```

## Ne doit pas contenir

```text
database connection
store implementation
secret values persisted in clear
```

---

# 13. `RuntimeResumeRequest`

## Structure conceptuelle

```text
run_id
runtime_handle
checkpoint_reference?
runtime_checkpoint?
resume_input?
correlation_context
ownership_context?
metadata
```

## Principe

Une reprise PyAgentsKit peut combiner :

```text
PyAgentsKit checkpoint
+
runtime-native checkpoint
```

sans fusionner les deux modèles.

---

# 14. `RuntimeCancelRequest`

## Structure conceptuelle

```text
run_id
runtime_handle
reason
requested_by
deadline?
```

## Résultat attendu

```text
CANCELLED
CANCELLATION_REQUESTED
NOT_SUPPORTED
ALREADY_TERMINAL
FAILED
```

---

# 15. `RuntimeHandle`

## Définition

Référence opaque vers une exécution runtime.

## Exemple

```text
thread_id
session_id
execution_id
process_id
conversation_handle
```

PyAgentsKit ne doit pas dépendre de sa structure interne.

## Structure conceptuelle

```python
@dataclass(frozen=True)
class RuntimeHandle:
    adapter_name: str
    external_id: str
    metadata: Mapping[str, Any]
```

---

# 16. Opaque runtime state

Tout état spécifique au runtime doit rester :

```text
opaque to core
```

Exemples :

```text
LangGraph checkpoint id
Claude session id
Codex thread id
OpenCode session id
```

PyAgentsKit stocke la référence sans interpréter son contenu métier interne.

---

# 17. `RuntimeCheckpoint`

## Définition

Checkpoint natif fourni par le runtime lorsqu’il supporte cette capacité.

## Structure

```text
runtime_checkpoint_id
runtime_handle
payload_reference?
created_at
metadata
```

## Distinction

```text
PyAgentsKit Checkpoint
!=
RuntimeCheckpoint
```

Le premier décrit l’état de fiabilité global.

Le second décrit l’état natif du runtime.

---

# 18. `RuntimeStatus`

États normalisés candidats :

```text
CREATED
STARTING
RUNNING
WAITING
COMPLETED
FAILED
CANCELLED
UNKNOWN
```

L’adapter traduit le modèle externe vers ce modèle minimal.

---

# 19. Normalisation d’état

Exemple :

```text
Claude runtime state
        │
        ▼
ClaudeAgentAdapter
        │
        ▼
RuntimeStatus.RUNNING
```

ou :

```text
Codex thread state
        │
        ▼
CodexAdapter
        │
        ▼
RuntimeStatus.WAITING
```

---

# 20. `NormalizedRuntimeEvent`

## Définition

Événement runtime traduit dans un vocabulaire stable PyAgentsKit.

## Types candidats

```text
RUNTIME_STARTED
RUNTIME_WAITING
RUNTIME_RESUMED
RUNTIME_COMPLETED
RUNTIME_FAILED

MESSAGE_EMITTED
MESSAGE_RECEIVED

TOOL_REQUESTED
TOOL_STARTED
TOOL_COMPLETED
TOOL_FAILED

CHECKPOINT_AVAILABLE

APPROVAL_REQUESTED

SUBAGENT_STARTED
SUBAGENT_COMPLETED

STDOUT
STDERR
DIAGNOSTIC
```

---

# 21. Structure d’un événement normalisé

```python
@dataclass(frozen=True)
class NormalizedRuntimeEvent:
    event_id: str
    event_type: RuntimeEventType
    runtime_handle: RuntimeHandle
    timestamp: datetime
    correlation_context: CorrelationContext
    payload: Mapping[str, Any]
    raw_reference: str | None = None
```

---

# 22. Raw event preservation

Un adapter peut conserver une référence ou copie contrôlée de l’événement brut :

```text
raw_reference
```

pour :

```text
debug
audit technique
adapter evolution
```

sans faire dépendre le domaine de ce format.

---

# 23. Mapping vers `DomainEvent`

Tous les `RuntimeEvent` ne deviennent pas des `DomainEvent`.

Exemples :

```text
MESSAGE_EMITTED
→ peut créer Message

TOOL_REQUESTED
→ peut créer EffectIntent

RUNTIME_COMPLETED
→ peut conduire à RunSucceeded

STDOUT
→ log seulement
```

La conversion appartient à la couche Application.

---

# 24. Messages

Le runtime adapter peut produire ou recevoir des messages normalisés.

## Sortie runtime

```text
runtime
↓
MESSAGE_EMITTED
↓
MessageService
↓
MessageStore
```

## Entrée runtime

```text
Message
↓
RuntimeResumeRequest / runtime input
↓
adapter
↓
runtime
```

---

# 25. Agent-to-agent messages

L’adapter ne doit pas imposer un protocole multi-agent global.

Deux agents peuvent communiquer via :

```text
runtime-native handoff
Message + new invocation
Message + child Run
external transport
```

PyAgentsKit normalise le résultat utile :

```text
Conversation
Message
correlation
run relationship
```

---

# 26. Tool interception

Une capability :

```text
TOOL_INTERCEPTION
```

permet à PyAgentsKit d’observer ou intercepter les appels d’outils.

Flux cible :

```text
Agent Runtime
   ↓
tool request
   ↓
AgentRuntimeAdapter
   ↓
PyAgentsKit Tool Gateway
   ↓
Effect Classification
   ↓
Policy / Approval / Fencing
   ↓
Tool Execution
```

---

# 27. Tool classification

Un appel peut être classé :

```text
READ
COMPUTE
WRITE
SENSITIVE_WRITE
CRITICAL_EFFECT
```

Cette classification ne doit pas être spécifique au runtime.

---

# 28. Protected Tool Gateway

Interface conceptuelle :

```python
class ToolGateway(Protocol):
    async def invoke(
        self,
        request: ToolInvocationRequest,
    ) -> ToolInvocationResult:
        ...
```

Le runtime adapter peut rediriger ses tools vers ce gateway.

---

# 29. Effect promotion

Tous les tools ne deviennent pas des `Effect`.

Exemples :

```text
calculate_sum
→ not Effect

read_file
→ usually not Effect

send_email
→ Effect

git_push
→ Effect

publish_package
→ Effect

deploy_production
→ Effect
```

---

# 30. Tool result propagation

Après exécution :

```text
ToolGateway
↓
ToolInvocationResult
↓
AgentRuntimeAdapter
↓
runtime-native tool result
```

L’adapter transforme le résultat normalisé vers le format attendu par le runtime.

---

# 31. Approval hooks

Certains runtimes supportent leurs propres hooks d’approbation.

PyAgentsKit peut les utiliser, mais la source de vérité de l’approval reste :

```text
ApprovalStore
```

et non :

```text
runtime callback memory
```

---

# 32. Approval flow

```text
runtime requests sensitive action
↓
adapter emits TOOL_REQUESTED
↓
PyAgentsKit classifies Effect
↓
PolicyEvaluator
↓
Approval required
↓
Approval persisted
↓
Run WAITING
↓
human decision
↓
runtime resume
```

---

# 33. Cancellation semantics

Le contrat doit distinguer :

```text
cancel requested
cancel acknowledged
runtime terminal
```

Un adapter ne doit pas prétendre qu’une annulation est terminée si elle n’est qu’envoyée.

---

# 34. Graceful cancellation

Un runtime peut supporter :

```text
graceful cancel
```

ou uniquement :

```text
process termination
```

Cette différence doit être exposée via capabilities ou résultat.

---

# 35. Failure model

Le contrat doit distinguer :

```text
RuntimeAdapterError
RuntimeTransportError
RuntimeRejectedInput
RuntimeUnavailable
RuntimeExecutionFailed
RuntimeStateUnknown
RuntimeCancellationFailed
RuntimeCapabilityUnsupported
```

---

# 36. Exception hierarchy conceptuelle

```python
class RuntimeAdapterError(Exception):
    pass

class RuntimeUnavailable(RuntimeAdapterError):
    pass

class RuntimeStateUnknown(RuntimeAdapterError):
    pass

class UnsupportedRuntimeCapability(RuntimeAdapterError):
    pass
```

L’API finale pourra utiliser des Result types ou exceptions.

---

# 37. `UNKNOWN` runtime state

Lorsque l’adapter ne peut pas déterminer l’état réel :

```text
RuntimeStatus.UNKNOWN
```

doit être utilisé plutôt que :

```text
FAILED
```

La même philosophie que `Effect.UNKNOWN` s’applique.

---

# 38. Retry policy

L’adapter ne doit jamais cacher un retry critique.

Retries autorisés dans l’adapter :

```text
safe transport retry
read-only retry
idempotent runtime status query
```

Retries sensibles :

```text
tool write
external side effect
runtime action with effect
```

doivent être coordonnés avec PyAgentsKit.

---

# 39. Idempotency du `start`

Le contrat devrait permettre une clé logique ou corrélation stable.

Objectif :

```text
duplicate start request
```

ne doit pas nécessairement produire :

```text
two external runtime executions
```

si le runtime permet la déduplication.

---

# 40. Session resume

Certains runtimes savent reprendre une session native.

Capability :

```text
SESSION_RESUME
```

L’adapter expose cette fonction sans imposer son modèle au core.

---

# 41. Native checkpointing

Capability :

```text
NATIVE_CHECKPOINT
```

Si absente :

```text
PyAgentsKit checkpoint
```

reste suffisant pour la reprise des garanties externes.

---

# 42. Streaming

Capability :

```text
EVENT_STREAM
```

Le contrat doit permettre :

```text
async iterator
```

sans imposer que tous les runtimes streament.

---

# 43. Backpressure

Lorsqu’un runtime produit trop d’événements :

```text
adapter
↓
bounded buffer / flow control
↓
consumer
```

doit éviter une croissance mémoire non bornée.

---

# 44. Event ordering

L’adapter doit documenter si les événements sont :

```text
strictly ordered
best effort ordered
possibly duplicated
possibly delayed
```

PyAgentsKit ne doit pas supposer un ordre plus fort que celui garanti.

---

# 45. Event deduplication

Lorsque le runtime fournit un ID stable :

```text
external_event_id
```

l’adapter doit le conserver.

Sinon, PyAgentsKit peut générer un ID local mais ne peut pas garantir une déduplication externe parfaite.

---

# 46. Concurrency model

Un adapter doit déclarer si une instance est :

```text
single-run
multi-run
thread-safe
process-safe
stateless
stateful
```

Ces propriétés doivent apparaître dans son descriptor ou metadata.

---

# 47. Adapter lifecycle

Cycle recommandé :

```text
construct
↓
initialize
↓
ready
↓
serve start/resume/events
↓
drain
↓
close
```

---

# 48. Initialization

Une initialisation peut vérifier :

```text
runtime available
credentials present
binary installed
SDK compatible
configuration valid
```

sans exécuter un run.

---

# 49. Readiness

L’adapter doit pouvoir contribuer à la readiness du worker.

Exemple :

```text
Claude Code binary missing
→ adapter not ready

Postgres healthy
→ worker alive
but coding runtime unavailable
→ capability degraded
```

---

# 50. Partial readiness

Tous les adapters n’ont pas besoin d’être disponibles pour rendre le worker globalement prêt.

Exemple :

```text
LangGraph adapter ready
Codex adapter unavailable
```

Le worker peut rester prêt pour les workloads LangGraph.

---

# 51. Adapter registry

Composant conceptuel :

```text
RuntimeAdapterRegistry
```

Fonctions :

```text
register
resolve
list
inspect capabilities
health
```

---

# 52. Résolution d’adapter

Exemple :

```text
runtime_type = "claude-agent-sdk"
↓
RuntimeAdapterRegistry
↓
ClaudeAgentAdapter
```

---

# 53. Versioning

Le contrat doit supporter :

```text
adapter version
runtime version
contract version
```

Exemple :

```text
adapter_api_version = "1"
```

Une évolution breaking doit être explicite.

---

# 54. Compatibility declaration

Un adapter peut exposer :

```text
supported_runtime_versions
minimum_python_version
optional dependencies
platform constraints
```

---

# 55. Configuration

La configuration doit être séparée des secrets.

Exemple :

```text
RuntimeConfig
├── model
├── workspace
├── feature flags
└── timeouts

SecretProvider
├── API token
└── credentials
```

---

# 56. Secret handling

Le contrat ne doit pas exiger que les secrets soient persistés dans `RuntimeBinding`.

Préférer :

```text
configuration_reference
secret_reference
```

---

# 57. Security context

Un runtime peut recevoir :

```text
Principal
Authorization context
OwnershipContext
```

mais l’adapter ne doit pas inventer une autorisation plus permissive que PyAgentsKit.

---

# 58. Isolation

Les adapters de coding agents peuvent nécessiter :

```text
workspace
container
sandbox
process
filesystem isolation
```

Cette isolation appartient au module adapter/runtime, pas au core.

---

# 59. Resource cleanup

L’adapter doit libérer :

```text
subprocess
file descriptors
temporary workspace handles
network connections
stream consumers
```

lors de `close()` ou d’une invocation terminée.

---

# 60. Timeouts

Trois timeouts distincts peuvent exister :

```text
adapter operation timeout
runtime execution timeout
tool/effect timeout
```

Ils ne doivent pas être confondus.

---

# 61. LangGraph Adapter — mapping conceptuel

Exemples de mapping :

```text
LangGraph thread/checkpoint
→ RuntimeHandle / RuntimeCheckpoint

graph invoke
→ RuntimeInvocation

tool node
→ TOOL_REQUESTED

graph completion
→ RUNTIME_COMPLETED
```

PyAgentsKit ne doit pas intégrer `StateGraph` dans son domaine.

---

# 62. PydanticAI Adapter — mapping conceptuel

Exemples :

```text
agent run
→ RuntimeInvocation

tool call
→ TOOL_REQUESTED

message history
→ optional Message mapping

result
→ RUNTIME_COMPLETED
```

---

# 63. OpenAI Agents SDK Adapter — mapping conceptuel

Exemples :

```text
agent run
→ RuntimeInvocation

handoff
→ RuntimeEvent / possible child invocation

tool request
→ TOOL_REQUESTED

human approval hooks
→ normalized Approval flow
```

---

# 64. Claude Agent SDK Adapter — mapping conceptuel

Exemples :

```text
SDK session
→ RuntimeHandle

tool call
→ TOOL_REQUESTED

hook
→ normalized event

resume session
→ RuntimeResumeRequest

subagent
→ SUBAGENT_STARTED / COMPLETED
```

---

# 65. AutoGen Adapter — mapping conceptuel

Exemples :

```text
conversation
→ Conversation mapping optionnel

agent message
→ MESSAGE_EMITTED

tool execution
→ TOOL_REQUESTED

multi-agent handoff
→ RuntimeEvent / Message
```

---

# 66. CrewAI Adapter — mapping conceptuel

Exemples :

```text
crew execution
→ RuntimeInvocation

task transition
→ diagnostic/runtime event

tool
→ TOOL_REQUESTED

crew completion
→ RUNTIME_COMPLETED
```

Le concept `Task` CrewAI ne devient pas automatiquement une entité PyAgentsKit.

---

# 67. Codex Adapter — mapping conceptuel

Surface potentielle :

```text
thread
→ RuntimeHandle

turn
→ RuntimeInvocation

command execution
→ RuntimeEvent

file edit
→ runtime-local activity

git push
→ Effect

PR creation
→ Effect
```

---

# 68. Claude Code Adapter — mapping conceptuel

Surface potentielle :

```text
session
→ RuntimeHandle

tool use
→ TOOL_REQUESTED

file edit
→ runtime-local action

shell command
→ classify

git push / deploy
→ Effect
```

Le fait qu’un runtime puisse éditer du code ne change pas la sémantique PyAgentsKit.

---

# 69. OpenCode Adapter — mapping conceptuel

Surface potentielle :

```text
session / run
→ RuntimeHandle

CLI/server events
→ NormalizedRuntimeEvent

tools
→ TOOL_REQUESTED

write operations
→ Effect classification when applicable
```

---

# 70. Antigravity CLI (`agy`) Adapter

Si `agy` expose une CLI ou API contrôlable :

```text
subprocess / API session
→ RuntimeHandle

stdout structured events
→ NormalizedRuntimeEvent

command lifecycle
→ RuntimeInvocation
```

La compatibilité exacte dépendra de la surface d’intégration disponible.

---

# 71. Custom Runtime Adapter

Le framework doit permettre une implémentation minimale.

Exemple :

```python
class MyRuntimeAdapter:
    ...
```

sans importer :

```text
LangGraph
OpenAI
Anthropic
Codex
```

---

# 72. Adapter minimal viable

Un adapter minimal peut ne supporter que :

```text
START
STATUS
EVENT_STREAM
```

et retourner :

```text
RESUME unsupported
CANCEL unsupported
```

Le core doit gérer les capabilities explicitement.

---

# 73. Adapter production-grade

Un adapter de production complet devrait idéalement supporter :

```text
START
RESUME
CANCEL
STATUS
EVENT_STREAM
TOOL_INTERCEPTION
SESSION_RESUME
CHECKPOINT or equivalent
HEALTH
```

selon les capacités natives du runtime.

---

# 74. CodingAgentAdapter — spécialisation éventuelle

Option :

```python
class CodingAgentAdapter(AgentRuntimeAdapter, Protocol):
    ...
```

Capacités supplémentaires :

```text
workspace_reference
repository_reference
diff_reference
command events
```

Mais cette spécialisation ne doit pas être nécessaire au core.

---

# 75. Quand NE PAS créer `CodingAgentAdapter`

Si les différences peuvent être modélisées uniquement par :

```text
RuntimeCapability
metadata
tool classification
```

alors garder un seul `AgentRuntimeAdapter`.

Principe :

> **Ne pas multiplier les abstractions avant d’avoir une différence contractuelle réelle.**

---

# 76. Runtime-specific extensions

Un adapter peut exposer une extension namespacée :

```text
adapter.extensions["codex"]
```

ou :

```text
runtime_metadata
```

sans modifier le modèle principal.

---

# 77. Conformance Test Suite

Tout adapter doit pouvoir être validé par une suite contractuelle commune.

Tests minimum :

```text
descriptor valid
capabilities coherent
start returns stable handle
status normalization valid
events conform to schema
cancel behavior documented
close is safe
errors normalized
```

---

# 78. Tests de reprise

Si `RESUME` est déclaré :

```text
start
↓
checkpoint / handle persisted
↓
adapter process recreated
↓
resume
↓
same logical runtime execution
```

doit être testé.

---

# 79. Tests de cancellation

Si `CANCEL` est déclaré :

```text
start
↓
cancel
↓
inspect
↓
terminal or acknowledged cancellation
```

doit être cohérent.

---

# 80. Tests d’événements

La suite doit vérifier :

```text
event IDs
ordering contract
duplicate behavior
correlation propagation
terminal events
error events
```

---

# 81. Tests de tool interception

Si `TOOL_INTERCEPTION` est déclaré :

```text
runtime requests tool
↓
adapter emits TOOL_REQUESTED
↓
PyAgentsKit decision
↓
result returned to runtime
```

doit être démontré.

---

# 82. Tests de fault injection

Scénarios :

```text
runtime process crash
SDK connection loss
event stream disconnect
adapter restart
timeout
cancel during execution
```

---

# 83. Test matrix

| Capability | Test obligatoire |
|---|---|
| START | start creates handle |
| STATUS | status maps correctly |
| EVENT_STREAM | events are normalized |
| RESUME | resume after adapter restart |
| CANCEL | cancellation semantics |
| TOOL_INTERCEPTION | tool roundtrip |
| NATIVE_CHECKPOINT | checkpoint restore |
| SESSION_RESUME | session continuity |

---

# 84. Adapter certification levels

Niveaux possibles :

```text
LEVEL 0 — Experimental
LEVEL 1 — Start/Status
LEVEL 2 — Events/Cancel
LEVEL 3 — Resume/Checkpoint
LEVEL 4 — Tool interception + production qualification
```

Optionnel mais utile pour communiquer la maturité.

---

# 85. Observability adapter

Chaque adapter doit produire des métriques de base :

```text
runtime_invocations_total
runtime_invocation_failures_total
runtime_event_stream_disconnects_total
runtime_latency
runtime_adapter_errors_total
```

sans labels à forte cardinalité comme `run_id`.

---

# 86. Logging adapter

Logs structurés :

```text
adapter_name
runtime_name
runtime_version
operation
status
duration
error_type
```

avec corrélation :

```text
run_id
trace_id
```

dans le contexte, pas comme métriques.

---

# 87. Tracing adapter

Spans candidats :

```text
runtime.start
runtime.resume
runtime.cancel
runtime.status
runtime.events
tool.intercept
```

---

# 88. Health model

Chaque adapter devrait exposer :

```text
HEALTHY
DEGRADED
UNAVAILABLE
UNKNOWN
```

avec :

```text
reason
checked_at
```

---

# 89. Adapter health vs runtime status

Ne pas confondre :

```text
adapter health
```

et :

```text
runtime invocation status
```

Un adapter peut être healthy alors qu’un run runtime est FAILED.

---

# 90. Thread/process safety

La documentation de l’adapter doit préciser :

```text
safe for concurrent calls?
one instance per worker?
one instance per run?
subprocess per run?
```

---

# 91. Packaging

Les adapters optionnels doivent idéalement utiliser des extras :

```text
pyagentskit[langgraph]
pyagentskit[openai]
pyagentskit[anthropic]
pyagentskit[codex]
```

ou packages séparés si nécessaire.

---

# 92. Dependency isolation

Le core ne doit pas importer les SDK optionnels.

Exemple :

```text
import langgraph
```

interdit dans :

```text
pyagentskit.domain
```

---

# 93. Adapter discovery

Mécanismes possibles :

```text
explicit registration
entry points
plugin registry
dependency injection
```

Préférence :

```text
explicit > magical
```

---

# 94. RuntimeBinding

Le domaine associe un run à un adapter via :

```text
RuntimeBinding
```

Exemple :

```text
runtime_type = "claude-agent-sdk"
adapter_name = "claude-agent-sdk"
config_reference = "cfg://..."
```

---

# 95. Persistence du handle

Le `RuntimeHandle` doit être persistable.

Contraintes :

```text
serializable
opaque
stable enough for resume if capability exists
```

---

# 96. Serialization

Le contrat doit privilégier des structures :

```text
JSON-compatible
```

pour la persistence et l’interopérabilité.

Les objets Python non sérialisables restent internes à l’adapter.

---

# 97. Raw provider objects

Interdit de stocker directement dans le domaine :

```text
OpenAI SDK object
Anthropic SDK object
LangGraph internal class
Codex internal object
```

Ils doivent être convertis en références ou payloads stables.

---

# 98. Data minimization

L’adapter ne doit pas persister automatiquement :

```text
full prompts
full model context
secrets
raw filesystem contents
```

sans besoin explicite.

---

# 99. Privacy

Si des messages runtime sont persistés :

```text
retention
redaction
sensitivity
```

doivent pouvoir être appliquées.

---

# 100. Approval security

Un callback runtime du type :

```text
"approved"
```

ne vaut pas preuve suffisante.

La décision autoritative reste dans :

```text
Approval
ApprovalStore
Actor identity
```

---

# 101. Fencing propagation

Un adapter capable d’intercepter un outil protégé doit recevoir :

```text
OwnershipContext
```

et transmettre :

```text
fencing_token
```

au gateway approprié.

---

# 102. Runtime-native side effects

Certains runtimes peuvent produire des effets sans passer par un tool hook.

Dans ce cas :

```text
adapter may not provide full effect protection
```

La limitation doit être explicitement documentée.

---

# 103. Safety grade

Un adapter peut exposer un niveau de sûreté :

```text
OBSERVE_ONLY
PARTIAL_CONTROL
FULL_TOOL_CONTROL
```

Exemple :

```text
runtime where tools cannot be intercepted
→ PARTIAL_CONTROL
```

---

# 104. Full control criteria

`FULL_TOOL_CONTROL` nécessite idéalement :

```text
all side-effecting tools intercepted
approval enforcement possible
fencing propagation possible
result capture possible
```

---

# 105. Adapter constraints metadata

Exemple :

```text
requires_local_binary = true
requires_workspace = true
requires_network = true
supports_headless = true
```

utile pour le scheduler et le worker placement.

---

# 106. Worker capability matching

Un worker peut déclarer :

```text
adapters:
- langgraph
- claude-code
```

Un run nécessitant :

```text
codex
```

ne doit pas être admis sur ce worker.

---

# 107. Scheduling / placement

PyAgentsKit ne devient pas scheduler global, mais peut exposer des contraintes :

```text
required_runtime
required_capabilities
workspace_required
platform
```

à un orchestrateur externe.

---

# 108. Adapter version migration

Un changement d’adapter pendant un run actif peut être dangereux.

Principe :

```text
runtime_binding pinned for run lifetime
```

sauf migration explicite.

---

# 109. Runtime migration

Migration d’un run :

```text
LangGraph → Claude Agent SDK
```

ne doit pas être supposée possible.

Elle nécessite :

```text
explicit migration strategy
state conversion
compatibility validation
```

---

# 110. Adapter replacement between runs

Changer d’adapter entre deux runs d’une même Session est acceptable.

```text
Session
├── Run 1 → LangGraph
└── Run 2 → Claude Agent SDK
```

---

# 111. Cross-runtime conversation

Une Conversation peut contenir des messages provenant de plusieurs runtimes.

```text
Agent A via LangGraph
Agent B via Claude Agent SDK
Human
```

Le modèle `Message` reste commun.

---

# 112. Adapter responsibilities summary

L’adapter DOIT :

```text
translate runtime lifecycle
normalize status
normalize events
preserve opaque handle
declare capabilities
surface failures
propagate correlation
respect PyAgentsKit control decisions
```

---

# 113. Adapter non-responsibilities summary

L’adapter NE DOIT PAS :

```text
own business state
hide critical retries
silently approve actions
bypass fencing
invent domain semantics
persist secrets casually
couple core to runtime internals
```

---

# 114. Reference sequence — start

```text
Application
   ↓
Create Run
   ↓
Resolve RuntimeBinding
   ↓
RuntimeAdapterRegistry
   ↓
AgentRuntimeAdapter.start()
   ↓
RuntimeHandle
   ↓
persist handle
   ↓
consume events
```

---

# 115. Reference sequence — resume

```text
RecoveryPlanner
   ↓
RecoveryPlan = RESUME_RUNTIME
   ↓
load RuntimeBinding
   ↓
resolve adapter
   ↓
AgentRuntimeAdapter.resume()
   ↓
RuntimeHandle
   ↓
consume events
```

---

# 116. Reference sequence — protected tool

```text
Runtime
  ↓
Adapter
  ↓
TOOL_REQUESTED
  ↓
ToolGateway
  ↓
Effect classification
  ↓
Policy
  ↓
Approval if required
  ↓
Fencing validation
  ↓
execute
  ↓
persist outcome
  ↓
return runtime-native result
```

---

# 117. Reference sequence — runtime crash

```text
runtime process crash
↓
adapter reports failure / stream ends
↓
Run remains non-terminal until recovery decision
↓
RecoveryPlanner
↓
resume if supported
or
restart from PyAgentsKit checkpoint
or
manual intervention
```

---

# 118. Reference sequence — unknown runtime state

```text
inspect runtime
↓
network unavailable
↓
RuntimeStatus.UNKNOWN
↓
do not claim FAILED
↓
retry safe status query / manual recovery
```

---

# 119. Reference sequence — coding agent

```text
Run
↓
CodexAdapter
↓
Codex
↓
edit/test
↓
git_push request
↓
ToolGateway
↓
Effect
↓
Approval
↓
Git remote
```

---

# 120. Minimal implementation checklist

Un nouvel adapter doit documenter :

```text
runtime identity
supported versions
capabilities
start semantics
resume semantics
cancel semantics
status mapping
event mapping
tool interception
checkpoint support
error mapping
health checks
thread safety
resource cleanup
security considerations
known limitations
```

---

# 121. Adapter README template

Chaque adapter devrait inclure :

```text
Overview
Installation
Supported runtime versions
Capabilities
Configuration
Secrets
Example
Lifecycle mapping
Event mapping
Tool/effect behavior
Resume behavior
Cancellation behavior
Observability
Limitations
Conformance test status
```

---

# 122. Definition of Done d’un adapter

Un adapter est considéré prêt lorsqu’il :

1. implémente le contrat déclaré ;
2. expose un descriptor valide ;
3. déclare ses capabilities ;
4. normalise ses statuts ;
5. normalise ses événements ;
6. propage la corrélation ;
7. passe la conformance suite ;
8. documente ses limites ;
9. ne bypass pas les Protected Effects ;
10. gère proprement `close()` ;
11. expose sa health ;
12. fonctionne après restart de l’adapter si `RESUME` est déclaré.

---

# 123. Definition of Done du contrat

Le contrat `AgentRuntimeAdapter` est mature lorsque :

1. au moins deux runtimes très différents l’implémentent ;
2. un runtime généraliste est supporté ;
3. un coding agent est supporté ;
4. un runtime custom minimal est supporté ;
5. aucun runtime-specific concept n’est requis par le core ;
6. les capabilities couvrent les différences sans explosion d’interfaces ;
7. les événements sont suffisamment stables ;
8. la reprise est testable ;
9. les Protected Effects peuvent être appliqués lorsque le runtime permet l’interception ;
10. la suite de conformité est automatisée.

---

# 124. Questions ouvertes

```text
Q-ADP-01 Un seul Protocol ou plusieurs Protocols spécialisés ?
Q-ADP-02 CodingAgentAdapter dédié ou capabilities uniquement ?
Q-ADP-03 RuntimeStatus.WAITING doit-il inclure la raison ?
Q-ADP-04 events() doit-il être obligatoire ?
Q-ADP-05 checkpoint() doit-il appartenir au contrat de base ?
Q-ADP-06 faut-il un hook bidirectionnel de tool interception ?
Q-ADP-07 faut-il normaliser les sub-agents ?
Q-ADP-08 comment versionner le schema NormalizedRuntimeEvent ?
Q-ADP-09 comment certifier PARTIAL_CONTROL vs FULL_TOOL_CONTROL ?
Q-ADP-10 comment gérer les runtimes qui n’exposent qu’une CLI ?
Q-ADP-11 faut-il persister RuntimeHandle dans RuntimeBinding ou RuntimeInvocation ?
Q-ADP-12 faut-il autoriser plusieurs handles par Run ?
```

---

# 125. ADR induits

```text
ADR-ADP-001 AgentRuntimeAdapter base contract
ADR-ADP-002 Runtime capability model
ADR-ADP-003 RuntimeHandle persistence
ADR-ADP-004 Runtime event normalization
ADR-ADP-005 Tool interception contract
ADR-ADP-006 Adapter registry
ADR-ADP-007 Adapter health model
ADR-ADP-008 Runtime-specific extensions
ADR-ADP-009 CodingAgentAdapter decision
ADR-ADP-010 Runtime binding version pinning
```

---

# 126. Architecture récapitulative

```text
┌────────────────────────────────────┐
│        External Agent Runtime      │
│                                    │
│ LangGraph / OpenAI / Claude        │
│ Codex / Claude Code / OpenCode     │
│ Custom Runtime                     │
└──────────────────┬─────────────────┘
                   │
                   ▼
┌────────────────────────────────────┐
│       AgentRuntimeAdapter          │
│                                    │
│ start / resume / cancel            │
│ status / events / checkpoint       │
│ capability discovery               │
│ tool interception                  │
└──────────────────┬─────────────────┘
                   │
                   ▼
┌────────────────────────────────────┐
│          PyAgentsKit Core          │
│                                    │
│ Run                                │
│ Conversation                       │
│ Effect                             │
│ Approval                           │
│ Lease / Fencing                    │
│ Recovery                           │
│ Audit                              │
└──────────────────┬─────────────────┘
                   │
         ┌─────────┼───────────┐
         ▼         ▼           ▼
      Stores    ToolGateway  Telemetry
         │         │           │
         ▼         ▼           ▼
     PostgreSQL External   OTel / Logs
                Systems
```

---

# 127. Résumé

`AgentRuntimeAdapter` est la frontière qui permet à PyAgentsKit de rester indépendant des runtimes agentiques.

Le contrat doit normaliser :

```text
lifecycle
status
events
handles
capabilities
tool interception
checkpoint/resume
```

sans normaliser :

```text
reasoning
prompting
graph internals
repository semantics
provider-specific objects
```

La règle centrale est :

> **PyAgentsKit contrôle les garanties autour de l’exécution ; l’adapter traduit le runtime ; le runtime conserve son intelligence et son modèle interne.**

Le document suivant peut approfondir la partie la plus différenciante du framework :

```text
../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md
```
