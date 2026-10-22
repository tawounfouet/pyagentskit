# PyAgentsKit — Native Runtime Adapter

**Document :** `../runtime/35_PYAGENTSKIT_NATIVE_RUNTIME_ADAPTER.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Runtime Integration Specification  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../strategy/30_PYAGENTSKIT_V1_TO_V2_MIGRATION_STRATEGY.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/35_PYAGENTSKIT_NATIVE_RUNTIME_ADAPTER.md`
- `../runtime/36_PYAGENTSKIT_RECOVERY_PLANNER_SPECIFICATION.md`
- `../operations/38_PYAGENTSKIT_TEST_STRATEGY.md`
- `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`
- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`

---

# 1. Objet

Ce document spécifie le **Native Runtime Adapter** de PyAgentsKit V2.

Le Native Runtime Adapter est le premier adapter concret du Port :

```text
AgentRuntimeAdapter
```

Son rôle est de transformer le runtime natif historiquement porté par le `Runner` V1 en une implémentation conforme à l’architecture V2.

La stratégie n’est pas :

```text
rewrite Runner from scratch
```

mais :

```text
extract
wrap
isolate
adapt
qualify
```

Le principe directeur est :

> **Le Runner V1 devient un runtime parmi d’autres ; il ne reste plus le centre architectural de PyAgentsKit.**

---

# 2. Contexte V1

Dans PyAgentsKit 1.6, le `Runner` possède directement une large partie de l’exécution agentique :

```text
model call
tool selection
tool execution
model follow-up
limits
guardrails
events
approvals
session interactions
```

Cette architecture a permis de construire un runtime mono-agent cohérent.

Cependant, dans V2, PyAgentsKit change de niveau d’abstraction :

```text
V1
PyAgentsKit = Agent Runtime

V2
PyAgentsKit = Agent Reliability Layer
```

Le runtime natif doit donc être repositionné.

---

# 3. Décision architecturale

Le `Runner` V1 est requalifié en :

```text
Native Agent Runtime
```

et exposé via :

```text
NativeRuntimeAdapter
```

Le reste du Core ne dépend plus directement du `Runner`.

---

# 4. Target Relationship

```text
Application Services
        │
        ▼
AgentRuntimeAdapter
        │
        ▼
NativeRuntimeAdapter
        │
        ▼
Native Runtime Engine
        │
        ├── Model
        ├── Tool Execution
        ├── Guardrails
        └── Runtime Events
```

---

# 5. Critical Architectural Consequence

Le Core V2 doit pouvoir remplacer :

```text
NativeRuntimeAdapter
```

par :

```text
LangGraphRuntimeAdapter
PydanticAIRuntimeAdapter
OpenAIAgentsRuntimeAdapter
CodingAgentRuntimeAdapter
```

sans modifier :

```text
Effect semantics
Approval semantics
Recovery semantics
Lease/Fencing semantics
Audit semantics
```

---

# 6. Scope

Le Native Runtime Adapter couvre :

- runtime descriptor ;
- capabilities ;
- start ;
- resume ;
- cancel ;
- inspect ;
- events ;
- checkpoints ;
- close ;
- runtime handle ;
- runtime invocation identity ;
- tool interception ;
- interaction avec Effects ;
- interaction avec Approvals ;
- mapping V1 Runner → V2 runtime semantics ;
- error normalization ;
- test contract ;
- qualification.

---

# 6.1. Qualification effective en 2.0.0a2

La surface réellement annoncée par le Native Runtime en `2.0.0a2` est volontairement
conservatrice :

```text
START
STATUS
CANCEL
EVENT_STREAM
```

Le niveau de contrôle des side effects est :

```text
BOUNDED
```

`TOOL_INTERCEPTION`, `RESUME` et `NATIVE_CHECKPOINT` restent des capacités cibles de
l'adapter, mais ne sont pas annoncées tant que leur comportement V2 n'est pas démontré par les
Contract Tests correspondants. En particulier, la réutilisation du ToolExecutor V1 ne suffit pas,
à elle seule, à prouver le contrat V2 de protected Effect interception.

---

# 7. Non-goals

Le Native Runtime Adapter ne doit pas :

- posséder le cycle de vie du `Run` ;
- décider seul de la sécurité d’un Effect ;
- posséder les Leases ;
- créer des Approvals autoritatives ;
- décider des politiques d’Authorization ;
- écrire directement dans les aggregates d’autres bounded contexts ;
- devenir un workflow engine générique ;
- devenir un scheduler ;
- devenir le seul runtime possible.

---

# 8. Port cible

Le Port canonique est :

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

Le Native Adapter doit implémenter ce contrat sans extension implicite inaccessible aux autres runtimes.

---

# 9. NativeRuntimeAdapter

Proposition conceptuelle :

```python
class NativeRuntimeAdapter(AgentRuntimeAdapter):
    ...
```

Il encapsule :

```text
NativeRuntimeEngine
```

qui peut initialement réutiliser le code du Runner V1.

---

# 10. NativeRuntimeEngine

Le moteur interne représente la logique historique :

```text
model → tool → model
```

Il devient une implémentation interne du bounded context Runtime Integration.

---

# 11. Important Separation

```text
NativeRuntimeAdapter
!=
NativeRuntimeEngine
```

L’Adapter traduit :

```text
canonical V2 runtime contract
↔
native engine semantics
```

---

# 12. Why Keep the Adapter Boundary Even for Native

Sans adapter natif, le Core V2 risquerait de conserver un chemin privilégié :

```text
if native:
    use internal Runner directly
```

Ce serait contraire à la neutralité runtime.

---

# 13. Native Must Pass Same Contract

Le Native Adapter doit passer la même suite :

```text
AgentRuntimeAdapterContract
```

que les adapters externes.

---

# 14. No Native Exception

Principe :

> **Native is first-party, not privileged.**

---

# 15. RuntimeDescriptor

Le Native Adapter expose un descriptor.

Proposition :

```text
runtime_id = "pyagentskit.native"
name = "PyAgentsKit Native Runtime"
adapter_version
engine_version
capabilities
control_level
```

---

# 16. RuntimeCapability Set

Capabilities initiales probables :

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
STRUCTURED_OUTPUT
```

Selon implémentation effective.

---

# 17. Capability Truthfulness

Aucune capability ne doit être annoncée tant qu’elle n’est pas démontrée.

Exemple :

```text
SESSION_RESUME
```

ne doit pas être exposée uniquement parce qu’un objet Session existe.

---

# 18. Runtime Control Level

Le Native Adapter cible :

```text
FULL
```

car PyAgentsKit contrôle :

```text
model invocation
tool interception
tool execution path
events
checkpoint boundaries
```

---

# 19. Why FULL Matters

Cela permet à PyAgentsKit d’appliquer ses garanties maximales :

```text
Effect interception
Approval gating
Recovery-aware tool execution
Audit
Fencing-aware protected actions
```

---

# 20. RuntimeHandle

Le Native Adapter retourne un handle opaque.

Proposition :

```text
NativeRuntimeHandle
```

---

# 21. RuntimeHandle Fields

Conceptuellement :

```text
runtime_invocation_id
native_execution_id
session_ref
checkpoint_ref
engine_version
```

---

# 22. Opaque to Domain

Le Domain ne dépend pas de la structure interne du handle.

---

# 23. Serializable Reference

Le handle durable ne doit pas contenir :

```text
live Python object
open coroutine
model SDK object
database connection
```

---

# 24. Why

Recovery peut avoir lieu dans :

```text
another process
another worker
another pod
```

---

# 25. RuntimeInvocation

Chaque démarrage/restart crée une entité :

```text
RuntimeInvocation
```

distincte du Run.

---

# 26. Run != RuntimeInvocation

Un Run peut avoir :

```text
RuntimeInvocation #1
RuntimeInvocation #2
RuntimeInvocation #3
```

après recovery/restart.

---

# 27. Invocation Fields

Proposition :

```text
id
run_id
runtime_descriptor
status
handle
started_at
completed_at
parent_invocation_id
restart_reason
checkpoint_origin
version
```

---

# 28. RuntimeInvocation State

États candidats :

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

---

# 29. Native Start

`start()` reçoit un contexte canonique.

Exemple conceptuel :

```text
RunInput
RuntimeBinding
Session context
Messages
Memory
Tool definitions
Policies
```

---

# 30. Start Flow

```text
Application Service
      │
      ▼
create RuntimeInvocation
      │
      ▼
NativeRuntimeAdapter.start()
      │
      ▼
NativeRuntimeEngine
      │
      ▼
model/tool loop
```

---

# 31. Start Must Not Own Run State

Le Native Adapter ne doit pas décider :

```text
Run → SUCCEEDED
```

Il rapporte :

```text
runtime outcome
```

à l’Application Layer.

---

# 32. Native Resume

`resume()` doit reprendre :

```text
same logical RuntimeInvocation
```

si la capability le permet.

---

# 33. Resume Preconditions

Avant `resume()` :

```text
RecoveryPlanner
```

doit avoir validé :

- ownership ;
- Effects ;
- Approvals ;
- security ;
- runtime capability ;
- checkpoint consistency.

---

# 34. Resume Does Not Re-run Completed Effects

Le moteur natif doit pouvoir reconstruire son contexte sans exécuter à nouveau un tool call déjà transformé en :

```text
Effect.SUCCEEDED
```

---

# 35. Native Restart

`RESTART_RUNTIME` est différent de `resume()`.

Il crée :

```text
new RuntimeInvocation
```

mais peut réutiliser :

```text
Session
Conversation
Messages
Memory
Effects
Checkpoint
```

---

# 36. Restart Safety

Le Native Runtime ne peut redémarrer que si :

```text
prior external Effects are authoritative
```

---

# 37. Cancel

`cancel()` demande l’arrêt du moteur natif.

Il ne signifie jamais :

```text
rollback Effects
```

---

# 38. Cancellation Model

Le Native Engine doit réagir à :

```text
cancellation token
async task cancellation
explicit stop request
```

de façon bornée.

---

# 39. Cancel Safe Point

Le moteur doit vérifier la cancellation :

```text
before model call
before tool preparation
before new Effect
after external boundaries
```

---

# 40. Cancel During External Effect

Si action externe déjà envoyée :

```text
cancellation cannot assert rollback
```

Le résultat peut devenir :

```text
UNKNOWN
```

selon fenêtre.

---

# 41. Inspect

`inspect()` doit retourner un :

```text
RuntimeInspectionSnapshot
```

normalisé.

---

# 42. Inspection Fields

Proposition :

```text
runtime_invocation_id
status
handle_valid
last_event_type
checkpoint_available
pending_tool_calls
observed_at
```

---

# 43. Inspect Is Observation

Il ne doit pas muter le runtime.

---

# 44. Events

Le Native Adapter produit :

```text
RuntimeEvent
```

---

# 45. RuntimeEvent Examples

```text
RuntimeStarted
ModelCallStarted
ModelCallCompleted
ToolRequested
ToolResultReceived
RuntimeWaiting
RuntimeCompleted
RuntimeFailed
RuntimeCancelled
```

---

# 46. RuntimeEvent != DomainEvent

Un événement interne du runtime n’est pas automatiquement un DomainEvent.

---

# 47. RuntimeEvent != AuditEvent

Même distinction.

---

# 48. Event Mapping Layer

L’Application peut décider que certains RuntimeEvents déclenchent :

```text
Domain Event
Audit Event
metrics
```

---

# 49. Message Stream

Si `MESSAGE_STREAM` est supporté, l’Adapter peut exposer :

```text
runtime output tokens/messages
```

---

# 50. RuntimeMessage != ConversationMessage

Un message produit pendant l’exécution n’est durablement publié dans la Conversation qu’après passage par l’Application/Conversation context.

---

# 51. Tool Interception

C’est la capability la plus stratégique du Native Runtime.

---

# 52. Native Tool Request Flow

```text
Model
  │
  ▼
ToolCall Request
  │
  ▼
Native Runtime Adapter
  │
  ▼
Tool Interception Boundary
  │
  ▼
Application / Effects / Governance
  │
  ▼
Allowed?
  │
 ┌┴┐
No Yes
│   │
▼   ▼
deny execute safely
```

---

# 53. ToolCall != Effect

Le Native Runtime reçoit :

```text
ToolCall
```

mais PyAgentsKit V2 peut le transformer en :

```text
Effect
```

seulement si l’action est effectful.

---

# 54. Pure Tools

Exemples :

```text
calculator
local parse
pure transform
```

peuvent ne pas nécessiter Effect durable.

---

# 55. Effectful Tools

Exemples :

```text
HTTP POST
Git push
send email
create PR
deploy
```

doivent passer par le modèle Effect.

---

# 56. Tool Classification

Le runtime peut fournir :

```text
ToolDefinition
ToolRisk
```

mais la décision finale d’exécution appartient à la reliability layer.

---

# 57. Existing V1 Tool Assets

À réutiliser autant que possible :

```text
ToolDefinition
ToolRisk
ToolExecutionPolicy
ToolExecutor
GuardrailPipeline
```

---

# 58. Refactoring Principle

Ne pas jeter ces primitives.

Les déplacer derrière le bon boundary.

---

# 59. ToolExecutionPolicy

Devient un mécanisme local pouvant contribuer à :

```text
tool admissibility
```

mais ne remplace pas :

```text
Authorization
Approval
Effect safety
```

---

# 60. GuardrailPipeline

Reste utile pour :

```text
input/output/tool guardrails
```

mais ne devient pas security authority.

---

# 61. ToolExecutor

Peut rester une primitive du runtime natif pour :

```text
pure/local tool execution
```

Les Protected Effects passent par l’Application Layer.

---

# 62. Effect Interception Contract

Lorsqu’un ToolCall est classé effectful :

```text
NativeRuntimeEngine
must pause before external execution
```

---

# 63. Pause Boundary

Le runtime transmet :

```text
ToolInvocationRequest
```

au NativeRuntimeAdapter/Application.

---

# 64. ToolInvocationRequest

Proposition :

```text
runtime_invocation_id
tool_name
arguments
call_id
risk
metadata
```

---

# 65. Effect Fingerprint

L’Application calcule :

```text
canonical Effect fingerprint
```

à partir de l’intention normalisée.

---

# 66. Approval Gating

Si l’Effect exige Approval :

```text
Run → WAITING
RuntimeInvocation → WAITING
```

---

# 67. Native Runtime Waiting

Le moteur natif doit pouvoir attendre durablement sans rester :

```text
live coroutine forever
```

---

# 68. Durable Wait

Il doit sortir/rendre contrôle au Core avec :

```text
RuntimeWaiting
checkpoint
pending tool request reference
```

---

# 69. Resume After Approval

Après Approval :

```text
RecoveryPlanner
→ RESUME_RUNTIME
```

avec le résultat de tool execution éventuellement injecté.

---

# 70. Tool Result Injection

Le Native Runtime doit pouvoir recevoir :

```text
ToolResult
```

sans réémettre le ToolCall.

---

# 71. Critical Invariant

```text
approved/executed tool result
must be injected as result
not cause model to repeat call implicitly
```

---

# 72. Pending Tool Call Identity

Conserver :

```text
call_id
```

entre :

```text
request
Effect
tool result
runtime resume
```

---

# 73. Mapping ToolCall → Effect

Concept :

```text
Runtime ToolCall ID
→ Effect ID
```

persisté ou reconstructible.

---

# 74. Effect Result → Runtime Tool Result

Après succès :

```text
Effect outcome
→ canonical ToolResult
→ runtime resume
```

---

# 75. Unknown Effect

Si external call devient `UNKNOWN` :

```text
Native Runtime remains WAITING
```

---

# 76. Reconciliation Before Tool Result

Aucun tool result final ne doit être injecté tant que :

```text
Effect outcome unresolved
```

---

# 77. Reconciliation Success

Après confirmation :

```text
inject successful ToolResult
```

---

# 78. Reconciliation Failure

Après failure confirmée :

```text
inject canonical failure ToolResult
```

si policy continue runtime.

---

# 79. Manual Intervention

Le runtime reste :

```text
WAITING
```

tant qu’aucune décision sûre n’existe.

---

# 80. Checkpoint Model

Le Native Runtime peut produire des checkpoints à des frontières contrôlées.

---

# 81. Checkpoint Purpose

```text
reconstruct runtime computational context
```

---

# 82. Checkpoint Does Not Own Truth

Checkpoint ne peut pas écraser :

```text
Effect state
Approval state
Lease state
Authorization state
```

---

# 83. Checkpoint Kinds

Proposition :

```text
RUNTIME_STATE
PRE_TOOL
POST_TOOL
WAITING
MODEL_BOUNDARY
```

---

# 84. PRE_TOOL Checkpoint

Avant un ToolCall effectful :

```text
runtime context can be reconstructed
```

sans exécuter l’action.

---

# 85. POST_TOOL Checkpoint

Après injection du résultat.

Mais le résultat Effect durable reste la source de vérité.

---

# 86. Waiting Checkpoint

Capture :

```text
pending call
runtime context
reason
```

---

# 87. Native Checkpoint Format

Doit être :

```text
versioned
serializable
adapter-private
```

---

# 88. Opaque Checkpoint Payload

Le Core peut stocker :

```text
blob/reference
```

sans comprendre tous les détails.

---

# 89. Checkpoint Compatibility

Le Native Adapter doit définir :

```text
engine version compatibility
```

---

# 90. Upgrade Recovery

Un checkpoint créé par version N doit être :

```text
readable by N+1
```

pendant la fenêtre supportée, ou migration/compatibility explicite.

---

# 91. Runtime Checkpoint Size

Doit rester borné.

Les gros objets deviennent :

```text
Artifact references
```

si nécessaire.

---

# 92. Model Abstraction Reuse

Le Native Runtime peut continuer d’utiliser le Port V1 :

```text
Model
```

en interne.

---

# 93. Model Port Status in V2

`Model` n’est plus le Port central de PyAgentsKit.

Il devient :

```text
native-runtime internal/provider abstraction
```

---

# 94. Provider Adapters Reuse

Les adapters existants :

```text
OpenAI
Anthropic
Gemini
xAI
Ollama
OpenRouter
```

peuvent être conservés pour le Native Runtime.

---

# 95. Critical Boundary

Un provider model adapter :

```text
OpenAIModel
```

n’est pas un :

```text
AgentRuntimeAdapter
```

---

# 96. ModelAdapter != RuntimeAdapter

Cette distinction doit être explicite dans package naming.

---

# 97. Package Topology

Proposition :

```text
src/pyagentskit/
  adapters/
    runtimes/
      native/
        __init__.py
        adapter.py
        engine.py
        handle.py
        checkpoint.py
        events.py
        tool_bridge.py
        errors.py
```

---

# 98. Native Model Providers

Possibles :

```text
adapters/
  models/
    openai.py
    anthropic.py
    gemini.py
```

ou sous package native selon décision finale.

---

# 99. Preferred Dependency Direction

```text
NativeRuntimeAdapter
→ NativeRuntimeEngine
→ Model Port
→ Model Provider Adapter
```

---

# 100. No Reverse Dependency

Les model provider adapters ne connaissent pas :

```text
RecoveryPlanner
Effect aggregate
Approval aggregate
```

---

# 101. NativeRuntimeEngine Responsibilities

Le moteur peut posséder :

```text
model loop
local tool request generation
message formatting
token/turn limits
runtime guardrails
runtime event production
```

---

# 102. Responsibilities It Must Lose

Le moteur ne doit plus posséder directement :

```text
Run terminality
Effect truth
Approval authority
Lease ownership
cross-runtime recovery
```

---

# 103. Extracting V1 Runner

Le refactor recommandé suit plusieurs étapes.

---

# 104. Step N1 — Freeze Behavior

Avant extraction :

```text
lock current V1 Runner behavior with characterization tests
```

---

# 105. Step N2 — Identify Pure Engine Logic

Extraire :

```text
model interaction loop
tool request emission
message progression
```

---

# 106. Step N3 — Externalize Reliability Decisions

Retirer du Runner direct :

```text
Approval decisions
Effect execution decisions
Run finalization
distributed ownership
```

---

# 107. Step N4 — Add Adapter Facade

Créer :

```text
NativeRuntimeAdapter
```

qui expose les contracts V2.

---

# 108. Step N5 — Add RuntimeInvocation

Chaque exécution native passe par :

```text
RuntimeInvocation
```

---

# 109. Step N6 — Add Durable Waiting Boundary

Le runtime peut s’arrêter proprement sur :

```text
Approval
Unknown Effect
Human input
```

---

# 110. Step N7 — Pass Runtime Contract Suite

Le Native Adapter devient :

```text
L1 Contract Compliant
```

---

# 111. Step N8 — Failure Qualification

Ajouter :

```text
crash
resume
checkpoint
tool interception
```

---

# 112. V1 Compatibility

Le public V1 `Runner` peut rester disponible via :

```text
compat.v1
```

pendant la migration.

---

# 113. Compatibility Direction

```text
V1 Runner API
→ compatibility facade
→ V2 NativeRuntimeAdapter/Application
```

et non l’inverse.

---

# 114. Critical Rule

Le nouveau V2 Core ne doit pas importer :

```text
compat.v1
```

---

# 115. V1 Runner as Internal Legacy

Pendant transition, une partie du code Runner peut être appelée par Native Engine.

Mais cette dépendance doit rétrécir.

---

# 116. Strangler Approach

```text
existing Runner
      │
      ▼
wrapped by Native Adapter
      │
      ▼
logic progressively extracted
      │
      ▼
legacy Runner facade becomes thin
```

---

# 117. No Big-Bang Rewrite

Raison :

```text
V1 already has tested behavior
```

et les risques de régression sont importants.

---

# 118. V1 RunStatus Mapping

Le Native Adapter ne doit pas exposer directement les anciens états :

```text
WAITING_APPROVAL
UNKNOWN_EFFECT
LIMIT_EXCEEDED
```

comme runtime states V2.

---

# 119. Mapping

Exemples :

```text
V1 WAITING_APPROVAL
→ Runtime WAITING + Run WAITING + Approval blocker

V1 UNKNOWN_EFFECT
→ Runtime WAITING + Effect UNKNOWN

V1 COMPLETED
→ Runtime COMPLETED
```

---

# 120. LIMIT_EXCEEDED

Doit devenir :

```text
runtime termination reason
```

ou known failure selon policy, pas nécessairement état canonique global.

---

# 121. Runtime Termination Reason

Value Object possible :

```text
COMPLETED
CANCELLED
MODEL_ERROR
TOOL_ERROR
LIMIT_EXCEEDED
PROVIDER_ERROR
```

---

# 122. Run Outcome Remains Separate

L’Application décide si :

```text
Run succeeds
fails
waits
```

---

# 123. Session Mapping

V1 `Session` est historiquement proche d’une conversation/runtime session.

V2 impose :

```text
Session != Conversation
```

---

# 124. Native Adapter Must Not Preserve Ambiguity

Le Native Runtime peut consommer :

```text
SessionContext
ConversationContext
```

distinctement.

---

# 125. V1 Message Mapping

V1 `Message` doit être requalifié.

---

# 126. Native Runtime Message

Le moteur travaille avec :

```text
RuntimeMessage
```

---

# 127. Conversation Message

Le bounded context Conversations possède :

```text
ConversationMessage
```

---

# 128. Translation

L’Application/ACL peut traduire :

```text
ConversationMessage
→ RuntimeMessage
```

et :

```text
RuntimeMessage output
→ ConversationMessage
```

---

# 129. ToolCall Mapping

V1 ToolCall :

```text
runtime-level request
```

Il ne devient Effect que si l’outil est classé effectful.

---

# 130. Approval Mapping

V1 Runner pouvait gérer Approval dans son flow.

V2 :

```text
Native Runtime requests gated tool
→ Application/Governance creates Approval
→ runtime waits
```

---

# 131. Approval Status Legacy

Les anciens :

```text
CLAIMED
EXECUTED
```

ne doivent pas apparaître comme décision states V2.

---

# 132. Runtime Waiting Reasons

Proposition :

```text
APPROVAL_REQUIRED
EFFECT_RECONCILIATION
HUMAN_INPUT
DEPENDENCY
EXTERNAL_PAUSE
```

---

# 133. Waiting Reason != Run State

`WAITING` reste Run state.

Reason explique le blocker.

---

# 134. Human Input

Le Native Runtime peut supporter une attente conversationnelle.

Mais :

```text
human input
!=
Approval
```

---

# 135. Human Approval Hook Capability

`HUMAN_APPROVAL_HOOK` signifie que le runtime peut :

```text
pause around a protected request
```

pas qu’il possède la décision d’Approval.

---

# 136. Event Stream Semantics

Le Native Adapter peut produire un flux async.

---

# 137. Event Durability

Tous RuntimeEvents ne doivent pas forcément être persistés.

---

# 138. Critical Runtime Events

Certains peuvent alimenter durablement :

```text
RuntimeInvocation state
checkpoint
audit
```

---

# 139. Streaming Backpressure

Le flux doit être :

```text
bounded
```

ou capable de spill/drop non-critical events.

---

# 140. Slow Consumer

Ne doit pas bloquer indéfiniment un Protected Effect boundary.

---

# 141. Structured Output

Si `STRUCTURED_OUTPUT` supporté :

```text
model/native engine
```

peut produire un payload validé.

---

# 142. Structured Output Is Not Authority

Un modèle peut produire :

```text
{"approved": true}
```

Cela ne vaut pas Approval.

---

# 143. Subagents

Le Native Runtime V1 est historiquement mono-agent.

---

# 144. V2 Initial Scope

Le Native Adapter peut ne pas annoncer :

```text
SUBAGENTS
```

dans un premier temps.

---

# 145. Important

Ne pas forcer multi-agent uniquement pour suivre le marché.

La reliability layer est indépendante de ce choix.

---

# 146. Workspace Capability

Le Native Runtime général n’a pas nécessairement :

```text
WORKSPACE
```

sauf extension coding.

---

# 147. Command Execution

Même règle.

---

# 148. Coding Agent Distinction

Un futur Coding Runtime Adapter peut posséder :

```text
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
```

Le Native Adapter n’a pas besoin de tout implémenter.

---

# 149. Runtime Binding

Un Run doit référencer un :

```text
RuntimeBinding
```

---

# 150. RuntimeBinding Fields

Proposition :

```text
runtime_type
adapter_name
adapter_version
configuration_ref
capability_requirements
```

---

# 151. Binding to Native

Exemple :

```text
runtime_type = pyagentskit.native
```

---

# 152. Configuration

Native runtime config peut inclure :

```text
model
temperature
limits
tool set
guardrail configuration
```

mais pas secrets résolus.

---

# 153. Secret References

Provider credentials passent via :

```text
SecretReference
```

---

# 154. Native Model Selection

L’Adapter peut résoudre :

```text
model provider adapter
```

via registry/configuration.

---

# 155. Runtime Registry

Le Native Adapter est enregistré dans :

```text
RuntimeRegistry
```

---

# 156. Registration

Exemple conceptuel :

```text
registry.register(native_adapter)
```

---

# 157. Capability Negotiation

Avant Run :

```text
required capabilities
⊆
NativeRuntimeAdapter.capabilities
```

---

# 158. Missing Capability

Fail before execution.

---

# 159. Error Taxonomy

Le Native Adapter doit produire des erreurs canoniques.

---

# 160. Candidate Runtime Errors

```text
RuntimeUnavailable
RuntimeStartFailed
RuntimeResumeFailed
RuntimeCancelled
RuntimeCapabilityUnsupported
RuntimeHandleInvalid
RuntimeCheckpointInvalid
RuntimeProtocolViolation
```

---

# 161. Model Errors

Les erreurs provider sont traduites avant de traverser la frontière Runtime Adapter.

---

# 162. Provider Rate Limit

Peut devenir :

```text
RuntimeTemporarilyUnavailable
```

ou erreur canonique avec retry metadata.

---

# 163. Model Timeout

Ne doit pas devenir :

```text
Effect.UNKNOWN
```

s’il n’y avait aucun external Effect.

---

# 164. Tool Timeout

Dépend :

```text
pure local tool
vs
external effectful tool
```

---

# 165. Pure Tool Timeout

Peut devenir runtime/tool failure connue.

---

# 166. Effectful Tool Timeout

Passe par le modèle Effect/Reconciliation.

---

# 167. Tool Exceptions

Le Native Runtime ne doit pas avaler les erreurs de reliability layer.

---

# 168. Tool Result Envelope

Proposition :

```text
call_id
status
value
error
effect_id
external_reference
```

---

# 169. Tool Result Status

```text
SUCCESS
FAILURE
WAITING
CANCELLED
```

`UNKNOWN` external reste bloqué avant injection finale.

---

# 170. Model Loop after Tool Failure

Le moteur peut permettre au modèle de réagir à :

```text
known tool failure
```

si policy autorise.

---

# 171. Model Loop after Approval Rejection

Peut injecter :

```text
tool denied/rejected
```

comme résultat canonique.

---

# 172. Approval Rejection Is Not Runtime Failure

Le runtime peut continuer avec une autre stratégie.

---

# 173. Runtime Guardrails

Entrées/sorties/tools peuvent être validés.

---

# 174. Guardrail Failure

Doit être normalisé.

---

# 175. Guardrail and Governance

```text
Guardrail
!=
Authorization
!=
Approval
```

---

# 176. Native Runtime Observability

Metrics :

```text
native_runtime_starts_total
native_runtime_resumes_total
native_runtime_failures_total
native_runtime_active
native_runtime_tool_requests_total
```

---

# 177. Latency Metrics

```text
runtime_start_latency
model_call_latency
tool_wait_duration
resume_latency
```

---

# 178. Trace Spans

```text
runtime.start
runtime.model_call
runtime.tool_request
runtime.wait
runtime.resume
runtime.complete
```

---

# 179. Audit

Le runtime n’écrit pas directement tous les AuditEvents.

L’Application/Audit boundary décide.

---

# 180. Useful Audit Events

Exemples :

```text
RuntimeInvocationStarted
RuntimeInvocationResumed
RuntimeInvocationRestarted
RuntimeInvocationCancelled
RuntimeInvocationCompleted
```

---

# 181. Run Correlation

Chaque RuntimeInvocation porte :

```text
run_id
```

pour correlation.

---

# 182. RuntimeInvocation Correlation

Chaque RuntimeEvent porte :

```text
runtime_invocation_id
```

---

# 183. Tool Correlation

ToolCall/Effect mapping porte :

```text
call_id
effect_id
```

---

# 184. Distributed Operation

Le Native Runtime peut être repris sur un autre worker.

---

# 185. Process Independence

Aucun état nécessaire à recovery ne doit exister uniquement :

```text
in Python memory
```

---

# 186. Active In-Memory State

Pendant execution, du state peut être en mémoire.

Mais des checkpoints/authoritative state doivent permettre :

```text
safe reconstruction
```

aux frontières nécessaires.

---

# 187. Lease Awareness

Le Native Adapter n’acquiert pas le Lease lui-même.

---

# 188. Ownership Context Injection

L’Application peut injecter :

```text
OwnershipContext
```

pour les protected tool boundaries.

---

# 189. Fencing Propagation

Pour un Effect protégé, le tool/connector reçoit si applicable :

```text
fencing_token
```

---

# 190. Native Adapter Role in Fencing

Il préserve le contexte de call.

Il ne définit pas le token.

---

# 191. Stale Worker

Si worker perd ownership :

```text
NativeRuntimeAdapter must stop requesting new protected execution
```

---

# 192. Lease Loss Detection

Le Worker/Application signale :

```text
authority lost
```

au runtime.

---

# 193. Runtime Behavior on Lease Loss

Doit :

```text
pause/stop at safe boundary
```

---

# 194. Immediate Stop Before New Effect

Invariance critique :

```text
no new protected Effect after known lease loss
```

---

# 195. In-flight Model Call

Peut être laissé terminer ou cancel selon policy.

Mais son output ne peut produire un protected Effect sans nouvelle authority.

---

# 196. In-flight Pure Compute

Peut terminer.

---

# 197. In-flight External Effect

Géré par Effect state, pas par simple runtime cancel.

---

# 198. Crash Recovery

Après worker crash :

```text
new worker
→ RecoveryPlanner
→ inspect authoritative state
→ resume/restart Native Runtime
```

---

# 199. Native Runtime Restartability

La meilleure garantie native est atteinte si :

```text
model/tool loop state
```

est reconstructible depuis des données durables.

---

# 200. Conversation Replay

Une stratégie possible :

```text
reconstruct model context from RuntimeMessages
```

---

# 201. Replay Warning

Rejouer des messages au modèle peut produire :

```text
different reasoning/output
```

---

# 202. Deterministic Recovery Goal

PyAgentsKit ne doit pas prétendre :

```text
same tokens
same reasoning
```

---

# 203. Semantic Recovery Goal

Le but est :

```text
safe continuation
```

pas reproduction bit-for-bit du LLM.

---

# 204. Tool Results as Anchors

Les résultats d’Effects déjà exécutés doivent être réinjectés pour empêcher :

```text
re-execution
```

---

# 205. Runtime State vs Domain State

```text
Runtime state
=
how the agent continues

Domain state
=
what is true
```

Le second reste prioritaire.

---

# 206. Checkpoint Frequency

Doit être choisie selon :

```text
cost
recovery precision
state size
```

---

# 207. Recommended Boundaries

Checkpoints au minimum autour :

```text
runtime start
pre-effectful tool
waiting
post-effect result injection
runtime completion
```

---

# 208. Excessive Checkpointing

Peut augmenter :

```text
DB/storage load
```

sans bénéfice.

---

# 209. Checkpoint Storage

Peut utiliser :

```text
CheckpointRepository
BlobStore
```

selon taille.

---

# 210. Native Runtime Persistence

Ne doit pas créer une seconde source de vérité concurrente au RunStore V2.

---

# 211. Existing V1 DurableRunner

Le `DurableRunner` V1 doit être requalifié.

---

# 212. V1 DurableRunner Role

Il contient aujourd’hui :

```text
checkpointing
effect tracking
recovery plan
```

---

# 213. V2 Migration

Ses responsabilités doivent être séparées :

```text
runtime checkpoint support
→ Native Runtime

Effect truth
→ Effects bounded context

Recovery decision
→ RecoveryPlanner

Run durability
→ Repositories/Application
```

---

# 214. Existing DistributedDurableRunner

Même logique.

---

# 215. V1 Distributed Runner Responsibilities

```text
lease guard
fencing tool policy
distributed worker control
```

---

# 216. V2 Placement

```text
Lease/Fencing
→ Coordination

Worker control
→ Application/Operations

Runtime execution
→ NativeRuntimeAdapter
```

---

# 217. Avoid Wrapper-on-Wrapper Forever

La migration peut commencer par wrappers.

Mais cible finale :

```text
cleanly separated responsibilities
```

---

# 218. Legacy Extraction Matrix

| V1 Component | V2 Destination |
|---|---|
| Runner model loop | NativeRuntimeEngine |
| Model Protocol | Native runtime model provider layer |
| ToolDefinition | Shared/runtime tool contract |
| ToolExecutor | Native runtime / tool execution support |
| ToolExecutionPolicy | runtime/tool policy support |
| GuardrailPipeline | native runtime guardrails |
| DurableRunner checkpoints | checkpoint/runtime integration |
| DurableRunner Effect tracking | Effects context |
| RecoveryPlan | RecoveryPlanner V2 |
| DistributedDurableRunner lease guard | Coordination |
| FencingToolPolicy | Effects/Coordination bridge |
| Session runtime context | split Session/Conversation/runtime state |

---

# 219. Migration Characterization Tests

Avant déplacement :

```text
record V1 behavior
```

sur :

- simple response ;
- tool call ;
- approval ;
- tool failure ;
- model failure ;
- cancellation ;
- checkpoint ;
- limits.

---

# 220. Characterization != Final Contract

Les anciens comportements erronés ne doivent pas devenir normes V2.

---

# 221. Explicit Semantic Breaks

Certains comportements V1 doivent changer volontairement :

```text
WAITING_APPROVAL terminality
UNKNOWN_EFFECT terminality
Session ≈ Conversation
Effect COMPLETED naming
Approval CLAIMED/EXECUTED semantics
```

---

# 222. Compatibility Facade

Le V1 API peut traduire le nouveau modèle vers les anciens états publics pendant période de compatibilité.

---

# 223. Native Adapter Public API

Les utilisateurs V2 n’ont généralement pas besoin d’instancier l’engine directement.

---

# 224. Bootstrap

Composition root :

```text
NativeRuntimeAdapter(
    engine=NativeRuntimeEngine(...),
    model_registry=...,
    ...
)
```

---

# 225. Dependency Injection

Le Native Adapter reçoit :

```text
model providers
clock
telemetry
configuration
```

via injection.

---

# 226. No Global Singletons

Éviter :

```text
global model client
global runtime registry
```

---

# 227. Thread/Async Safety

L’Adapter doit documenter s’il est :

```text
shareable across concurrent Runs
```

---

# 228. Preferred

Les clients stateless/pools peuvent être partagés.

Le state d’exécution reste par Invocation.

---

# 229. RuntimeExecutionContext

Objet per-invocation possible :

```text
invocation
messages
pending calls
checkpoint
limits
```

---

# 230. No Shared Mutable Run State

Entre invocations concurrentes.

---

# 231. Resource Cleanup

`close()` doit libérer :

```text
HTTP clients
background tasks
provider resources
```

---

# 232. Adapter Lifetime

Peut être :

```text
process-scoped
```

avec invocations multiples.

---

# 233. Invocation Lifetime

Distinct de l’Adapter lifetime.

---

# 234. Start Idempotency

`start()` ne doit pas être appelé deux fois pour la même Invocation sans protection.

---

# 235. Invocation Identity Constraint

Une RuntimeInvocation :

```text
starts once
```

---

# 236. Resume Idempotency

Multiple duplicate resume commands doivent être dédupliqués/version-protected.

---

# 237. Cancel Idempotency

Cancel repeated :

```text
safe
```

---

# 238. Close Idempotency

Close repeated :

```text
safe
```

si possible.

---

# 239. Inspect Idempotency

Read-only.

---

# 240. Events Ordering

RuntimeEvents d’une invocation doivent porter :

```text
sequence
```

si ordering nécessaire.

---

# 241. Event Sequence

Candidat :

```text
runtime_event_seq
```

monotone par invocation.

---

# 242. Event Gaps

Si events non durables/perdus :

```text
inspect
```

reste plus autoritatif sur runtime status.

---

# 243. Runtime Status Source

`RuntimeInvocation` durable est la source PyAgentsKit.

Le runtime provider/engine fournit observation.

---

# 244. Final Status Commit

Après engine completion :

```text
Application persists RuntimeInvocation.COMPLETED
```

---

# 245. Crash Before Final Commit

Peut produire :

```text
runtime provider completed
PyAgentsKit invocation still RUNNING/UNKNOWN
```

Recovery inspect résout.

---

# 246. Native Engine Completion Reconciliation

Puisque moteur natif est local, recovery peut souvent déduire via checkpoints/events.

Mais il doit suivre les mêmes principes.

---

# 247. Local Does Not Mean Atomic

Process crash peut toujours couper entre :

```text
engine completion
and
DB commit
```

---

# 248. Runtime Completion Evidence

Peut être :

```text
checkpoint
terminal runtime event
result artifact
```

mais le Run reste séparé.

---

# 249. Output Artifact

Un runtime result important peut être enregistré comme :

```text
Artifact
```

---

# 250. Structured Final Output

Le Native Adapter peut retourner :

```text
RuntimeResult
```

---

# 251. RuntimeResult

Proposition :

```text
status
output
structured_output
artifact_refs
usage
termination_reason
```

---

# 252. Usage

Peut inclure :

```text
tokens
model calls
tool calls
duration
```

---

# 253. Usage Is Observational

Ne décide pas Run outcome sauf policy :

```text
limit exceeded
budget exceeded
```

---

# 254. Limits

Native Runtime peut appliquer :

```text
max turns
max model calls
max tokens
max duration
```

---

# 255. Limit Exceeded

Produit :

```text
termination_reason = LIMIT_EXCEEDED
```

L’Application décide :

```text
FAILED
WAITING
manual
```

selon policy.

---

# 256. Budget Policy

Peut être externe au runtime.

---

# 257. Model Selection Failure

Runtime error connue.

---

# 258. Tool Definition Validation

Avant start :

```text
unique names
valid schema
supported serialization
```

---

# 259. Tool Schema Stability

Pour un Run long :

```text
tool version
```

doit être traçable.

---

# 260. Tool Version Drift

Après recovery, si tool implementation/schema change :

```text
compatibility check
```

nécessaire.

---

# 261. Tool Descriptor

Peut contenir :

```text
name
version
risk
schema
effect classification
```

---

# 262. Runtime Binding Snapshot

Conserver une référence à la configuration/runtime version utilisée.

---

# 263. Model Configuration Snapshot

Peut conserver :

```text
model name
provider
parameters
```

sans secret.

---

# 264. Reproducibility

Ne garantit pas même LLM output.

Mais facilite diagnostic.

---

# 265. Native Runtime Security

Le runtime ne doit pas pouvoir :

```text
construct arbitrary SecurityContext
```

---

# 266. SecurityContext Injection

Fourni par Application.

---

# 267. Runtime Untrusted Output

Tout contenu modèle est :

```text
untrusted input
```

pour governance.

---

# 268. Tool Arguments

Doivent être validés contre :

```text
schema
policy
Effect fingerprinting rules
```

---

# 269. Prompt Injection

Le Native Runtime peut utiliser guardrails.

Mais protected Effects restent gouvernés indépendamment des prompts.

---

# 270. Tool Allowlist

Peut être défini par RuntimeBinding/Application.

---

# 271. Dynamic Tool Availability

Peut dépendre :

```text
tenant
principal
Run
policy
```

---

# 272. Do Not Expose Unauthorized Tools

Idéalement filtrer avant model call.

---

# 273. Defense in Depth

Même tool non exposé ne dispense pas de vérifier Authorization au moment d’exécution.

---

# 274. Tool Result Sanitization

Les outputs providers peuvent être :

```text
untrusted
```

et doivent être traités comme tels avant retour modèle.

---

# 275. Secret Leakage Prevention

Ne jamais renvoyer secret résolu dans :

```text
RuntimeMessage
logs
checkpoint
```

sauf besoin explicitement sécurisé.

---

# 276. Runtime Checkpoint Privacy

Checkpoint peut contenir prompts/messages sensibles.

Appliquer :

```text
DataPolicy
retention
encryption if needed
```

---

# 277. Observability Privacy

Même règle pour events/traces.

---

# 278. Native Runtime Qualification Levels

```text
NR-L0 — Adapter Skeleton
NR-L1 — Contract Compliant
NR-L2 — Integration Tested
NR-L3 — Failure Tested
NR-L4 — Production Qualified
```

---

# 279. NR-L0

```text
descriptor
capabilities
method signatures
```

---

# 280. NR-L1

Passage complet du :

```text
AgentRuntimeAdapter Contract
```

---

# 281. NR-L2

Vrai model provider + tool flow.

---

# 282. NR-L3

Tests :

```text
model timeout
tool wait
cancel
checkpoint recovery
process crash
```

---

# 283. NR-L4

Tests :

```text
multi-worker recovery
W1–W5 around Effects
production-like runtime
soak
operations
```

---

# 284. P0 Native Tests

```text
NRT-P0-01 start
NRT-P0-02 resume after waiting
NRT-P0-03 cancel
NRT-P0-04 inspect
NRT-P0-05 checkpoint restore
NRT-P0-06 tool interception
NRT-P0-07 Effect SUCCEEDED not replayed
NRT-P0-08 Effect UNKNOWN blocks runtime
NRT-P0-09 Approval wait/resume
NRT-P0-10 stale ownership blocks new protected tool
```

---

# 285. W1–W5 Native Tests

Le Native Runtime doit être intégré aux tests :

```text
W1 pre-intent
W2 post-intent/pre-send
W3 post-send/pre-response
W4 post-response/pre-persist
W5 post-persist/pre-runtime-progress
```

---

# 286. Native Adapter Contract Tests

Doivent couvrir :

```text
start
resume
cancel
inspect
events
checkpoint
close
capability errors
```

---

# 287. Property Tests

Possibles :

```text
same checkpoint version round-trip
event sequence monotonic
completed invocation never resumes
```

---

# 288. Concurrency Tests

Deux Runs indépendants sur même Adapter instance.

Attendu :

```text
no state leakage
```

---

# 289. Resume Race

Deux workers tentent resume.

Ownership/CAS bloque le stale path.

---

# 290. Cancellation Race

Cancel arrive pendant :

```text
model call
tool wait
```

Doit produire state cohérent.

---

# 291. Failure Injection

Hooks test-only autour :

```text
pre-model
post-model
pre-tool
post-effect-result
pre-checkpoint
post-checkpoint
```

---

# 292. Package Dependency Rules

`domain/` ne doit jamais importer `native/`.

---

# 293. Application Depends on Port

Pas sur :

```text
NativeRuntimeAdapter
```

directement.

---

# 294. Bootstrap Selects Adapter

Le composition root choisit :

```text
runtime registry
```

---

# 295. Optional Dependencies

Le Native Runtime peut dépendre uniquement du core model abstraction.

Provider SDKs restent extras.

---

# 296. Installation Profiles

Exemples :

```text
pyagentskit
pyagentskit[openai]
pyagentskit[anthropic]
```

selon packaging final.

---

# 297. Backward Compatibility

V1 users peuvent continuer :

```text
Runner(...)
```

pendant fenêtre définie.

---

# 298. V1 Facade Behavior

Le V1 facade traduit en V2 puis retourne anciennes structures compatibles.

---

# 299. Deprecation

Après adoption V2 suffisante :

```text
Runner legacy API
```

peut être deprecated selon SemVer.

---

# 300. No Premature Removal

La transition doit permettre migration progressive.

---

# 301. Performance Model

Le Native Runtime ajoute peu de overhead par rapport à V1.

Le coût dominant reste :

```text
model calls
external tool calls
persistence boundaries
```

---

# 302. Performance Metrics

Comparer :

```text
V1 Runner baseline
vs
V2 Native Adapter
```

---

# 303. Acceptable Overhead

Doit être mesuré.

Ne pas fixer un chiffre arbitraire avant benchmark.

---

# 304. Waiting Efficiency

Un runtime WAITING ne doit pas maintenir :

```text
active model connection
live task
worker slot
```

si attente longue.

---

# 305. Resume Latency

Mesurer :

```text
load checkpoint
rebuild context
resume loop
```

---

# 306. Checkpoint Storage Cost

Mesurer :

```text
bytes/checkpoint
checkpoints/run
```

---

# 307. Event Volume

Mesurer :

```text
runtime events/model call
runtime events/tool call
```

---

# 308. Failure Semantics

Le Native Adapter doit distinguer :

```text
RuntimeFailure
ToolKnownFailure
EffectUnknown
Cancellation
Waiting
```

---

# 309. Never Collapse

Ne pas transformer toutes exceptions en :

```text
RuntimeFailed
```

sans classifier.

---

# 310. RuntimeProtocolViolation

Si moteur produit état impossible :

```text
raise canonical protocol violation
```

et demander manual/recovery intervention.

---

# 311. Native Runtime Runbook Implications

Incidents possibles :

```text
checkpoint incompatible
runtime loop stuck
provider SDK regression
tool bridge mismatch
```

---

# 312. Checkpoint Incompatibility

Doit conduire à :

```text
restart if safe
or
manual intervention
```

---

# 313. Provider SDK Regression

Adapter model-specific peut être pin/reverted sans modifier Domain.

---

# 314. Tool Bridge Regression

P0 si risque de bypass Effect safety.

---

# 315. Audit Requirement

Toute tool execution protected doit être corrélable à :

```text
RuntimeInvocation
Effect
Run
```

---

# 316. Native Runtime Developer Experience

Usage V2 doit rester simple.

Concept :

```python
kit = PyAgentsKit(
    runtime="native",
    model="openai:...",
)
```

ou composition explicite.

---

# 317. Explicit Adapter Usage

Pour avancé :

```python
runtime = NativeRuntimeAdapter(...)
```

---

# 318. Runtime Registry Alias

Alias :

```text
native
```

---

# 319. Default Runtime

PyAgentsKit peut garder Native comme default.

Mais l’architecture ne doit pas l’assumer.

---

# 320. Default != Privileged

Important.

---

# 321. Native Runtime Example Flow

```text
CreateRun
   │
   ▼
RuntimeBinding(native)
   │
   ▼
StartRun
   │
   ▼
RuntimeInvocation #1
   │
   ▼
NativeRuntimeAdapter.start
   │
   ▼
Model requests tool
   │
   ▼
Tool intercepted
   │
   ▼
Effect created
   │
   ▼
Approval required?
   │
  Yes
   │
   ▼
Run WAITING
Runtime WAITING
   │
   ▼
Approval
   │
   ▼
RecoverRun
   │
   ▼
RESUME_RUNTIME
   │
   ▼
Effect executed
   │
   ▼
ToolResult injected
   │
   ▼
Model continues
   │
   ▼
RuntimeCompleted
   │
   ▼
Completion checks
   │
   ▼
Run SUCCEEDED
```

---

# 322. Native Runtime Crash Flow

```text
Runtime working
   │
   ▼
Effect sent
   │
   ▼
Worker crashes before response
   │
   ▼
Lease expires
   │
   ▼
New worker takeover
   │
   ▼
RecoveryPlanner
   │
   ▼
Effect UNKNOWN
   │
   ▼
RECONCILE_EFFECT
   │
   ▼
confirmed success
   │
   ▼
ToolResult restored
   │
   ▼
RESUME_RUNTIME
```

---

# 323. Key Native Invariants

```text
NRA-INV-01 Native is an adapter, not the Core.
NRA-INV-02 Run != RuntimeInvocation.
NRA-INV-03 RuntimeMessage != ConversationMessage.
NRA-INV-04 ToolCall != Effect.
NRA-INV-05 Runtime completion != Run success.
NRA-INV-06 Runtime cancel != rollback.
NRA-INV-07 Checkpoint != external truth.
NRA-INV-08 SUCCEEDED Effects are never replayed.
NRA-INV-09 UNKNOWN Effects block dangerous resume.
NRA-INV-10 Approval authority stays outside runtime.
NRA-INV-11 Lease ownership stays outside runtime.
NRA-INV-12 Runtime capabilities are truthful.
NRA-INV-13 Native checkpoints are process-independent.
NRA-INV-14 Model provider SDK types do not leak into Core.
NRA-INV-15 Native adapter passes the same contract as external adapters.
```

---

# 324. Anti-Pattern — Keep Runner as Core

Interdit.

---

# 325. Anti-Pattern — Special Native Code Path

Interdit dans Application services.

---

# 326. Anti-Pattern — Runtime Executes Protected Tool Directly

Interdit.

---

# 327. Anti-Pattern — Approval Inside Prompt

Interdit comme source d’autorité.

---

# 328. Anti-Pattern — Live Coroutine as Durable State

Interdit.

---

# 329. Anti-Pattern — Checkpoint Contains Resolved Secrets

Interdit.

---

# 330. Anti-Pattern — Resume Without RecoveryPlanner

Interdit pour durable Runs.

---

# 331. Anti-Pattern — Restart on UNKNOWN

Interdit.

---

# 332. Anti-Pattern — Model Adapter Treated as Runtime Adapter

Interdit.

---

# 333. Anti-Pattern — Runtime Event Treated as Audit Truth

Interdit.

---

# 334. Anti-Pattern — Native Adapter Knows PostgreSQL

Le Port/Adapter runtime ne doit pas dépendre directement du repository concret.

---

# 335. Anti-Pattern — Native Runtime Owns Lease

Coordination reste séparée.

---

# 336. Anti-Pattern — Native Runtime Owns Approval State

Governance reste séparée.

---

# 337. Acceptance Criteria

Le Native Runtime Adapter est conforme si :

1. le Runner V1 est repositionné comme runtime natif ;
2. Application dépend de `AgentRuntimeAdapter`, pas du Runner ;
3. Native passe la même Contract Suite que les runtimes externes ;
4. RuntimeInvocation est distinct du Run ;
5. RuntimeHandle est process-independent ;
6. `start/resume/cancel/inspect/events/checkpoint/close` sont définis ;
7. capabilities sont explicites et véridiques ;
8. ToolCall est distinct d’Effect ;
9. Protected Effects sont interceptés avant exécution ;
10. Approval est externe au runtime ;
11. lease/fencing est externe au runtime ;
12. SUCCEEDED Effect ne peut pas être replayé ;
13. UNKNOWN bloque resume dangereux ;
14. checkpoints n’écrasent pas la vérité Domain ;
15. runtime WAITING ne consomme pas indéfiniment un worker slot ;
16. V1 Session/Message ambiguïtés sont corrigées ;
17. V1 Runner compatibility reste possible ;
18. model providers restent réutilisables ;
19. provider SDK types ne fuitent pas ;
20. failure semantics sont normalisées.

---

# 338. Definition of Done

`../runtime/35_PYAGENTSKIT_NATIVE_RUNTIME_ADAPTER.md` est considéré mature lorsque :

1. `NativeRuntimeAdapter` existe ;
2. `NativeRuntimeEngine` est séparé du facade V1 ;
3. `RuntimeDescriptor` est stable ;
4. `RuntimeHandle` est sérialisable ;
5. `RuntimeInvocation` est persisté ;
6. capabilities sont publiées ;
7. Contract Suite L1 est verte ;
8. start/resume/cancel/inspect/events fonctionnent ;
9. checkpoints sont versionnés ;
10. tool interception existe ;
11. ToolCall→Effect mapping est durable ;
12. Approval wait/resume fonctionne ;
13. UNKNOWN wait/reconciliation fonctionne ;
14. stale worker ne peut pas déclencher de nouveau protected tool ;
15. model providers V1 sont réutilisés ;
16. V1 Runner facade reste compatible ;
17. SIGKILL recovery est testé ;
18. W1–W5 sont testés avec Native ;
19. métriques/traces sont exposées ;
20. Native atteint le niveau `NR-L4` avant V2 stable.

---

# 339. Résumé

La transformation architecturale est :

```text
V1

PyAgentsKit Runner
      │
      ├── Model
      ├── Tools
      ├── Approvals
      ├── Durability
      ├── Recovery
      └── Coordination

                ↓ V2 REFACTOR ↓

PyAgentsKit Reliability Core
      │
      ├── Effects
      ├── Governance
      ├── RecoveryPlanner
      ├── Coordination
      └── Persistence
              │
              ▼
      AgentRuntimeAdapter
              │
              ▼
      NativeRuntimeAdapter
              │
              ▼
      NativeRuntimeEngine
              │
              ├── Model
              ├── Tool Requests
              ├── Guardrails
              └── Runtime Events
```

Le Native Runtime devient donc :

```text
first-party
reference
fully controllable
contract-compliant
```

mais pas :

```text
architecturally privileged
```

La règle fondamentale est :

> **Le runtime natif doit préserver tout ce que PyAgentsKit V1 sait déjà bien faire, tout en abandonnant ce qu’il ne doit plus posséder : la vérité des Effects, l’autorité des Approvals, l’ownership distribué et la décision de recovery appartiennent désormais au Reliability Core V2.**
