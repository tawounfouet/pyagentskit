# PyAgentsKit — Runtime Registry & Capability Negotiation

**Document :** `../runtime/34_PYAGENTSKIT_RUNTIME_REGISTRY_AND_CAPABILITY_NEGOTIATION.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Runtime Integration Specification  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`
- `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../strategy/26_PYAGENTSKIT_GAP_CLOSURE_AND_V2_IMPLEMENTATION_PLAN.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/35_PYAGENTSKIT_NATIVE_RUNTIME_ADAPTER.md`
- `../runtime/36_PYAGENTSKIT_RECOVERY_PLANNER_SPECIFICATION.md`
- `../operations/38_PYAGENTSKIT_TEST_STRATEGY.md`
- `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../strategy/44_PYAGENTSKIT_COMPETITIVE_AND_ECOSYSTEM_ANALYSIS.md`
- `../strategy/45_PYAGENTSKIT_BUILD_VS_BUY_VS_INTEGRATE.md`
- `../architecture/46_PYAGENTSKIT_ARCHITECTURE_DECISION_RECORDS_INDEX.md`
- `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`
- `../strategy/48_PYAGENTSKIT_ROADMAP_AND_RELEASE_STRATEGY.md`

---

# 1. Objet

Ce document définit le **Runtime Registry** et le mécanisme de **Capability Negotiation** de PyAgentsKit V2.

L’objectif est de permettre à PyAgentsKit de sélectionner et piloter plusieurs runtimes agentiques hétérogènes sans introduire de chemins spécifiques dans le Core.

Exemples de runtimes potentiels :

```text
PyAgentsKit Native Runtime
LangGraph
PydanticAI
OpenAI Agents SDK
Claude Agent SDK
AutoGen
CrewAI
Codex
Claude Code
OpenCode
custom internal runtimes
```

Le problème central est :

> **Comment savoir si un runtime est capable de fournir les garanties requises par un Run avant de lui confier l’exécution ?**

Le principe directeur est :

> **Runtime selection must be capability-driven, not brand-driven.**

---

# 2. Positionnement architectural

Le Registry appartient au bounded context :

```text
Runtime Integration
```

Il constitue un **outbound-facing integration mechanism** pour l’Application Layer.

Le Core ne doit jamais contenir :

```python
if runtime == "langgraph":
    ...
elif runtime == "codex":
    ...
```

Le choix passe par :

```text
RuntimeRegistry
+
RuntimeDescriptor
+
RuntimeCapability
+
RuntimeRequirements
+
CapabilityNegotiator
```

---

# 3. Objectifs

Le système doit permettre :

1. d’enregistrer plusieurs `AgentRuntimeAdapter` ;
2. d’identifier chaque adapter de manière stable ;
3. de publier ses capabilities ;
4. de distinguer required vs optional capabilities ;
5. de sélectionner un runtime compatible ;
6. d’échouer avant exécution si une garantie obligatoire manque ;
7. de gérer les versions ;
8. de gérer plusieurs instances/configurations d’un même runtime ;
9. de tenir compte du niveau de contrôle des side effects ;
10. de publier le niveau de qualification d’un adapter ;
11. de rendre la sélection explicable ;
12. de préserver la neutralité du Core.

---

# 4. Non-goals

Le Runtime Registry ne doit pas devenir :

- un service discovery général ;
- un plugin marketplace ;
- un scheduler ;
- un workflow engine ;
- un load balancer réseau ;
- un orchestrateur Kubernetes ;
- un secret store ;
- un registry de modèles LLM générique ;
- un moteur de policy généraliste.

---

# 5. Concepts principaux

```text
RuntimeRegistry
RuntimeDescriptor
RuntimeIdentity
RuntimeCapability
RuntimeRequirements
RuntimeBinding
RuntimeCandidate
CapabilityNegotiator
RuntimeSelectionPolicy
RuntimeQualificationLevel
SideEffectControlLevel
RuntimeCompatibility
```

---

# 6. RuntimeRegistry

Le `RuntimeRegistry` contient les adapters disponibles dans le process/composition root.

Conceptuellement :

```python
class RuntimeRegistry(Protocol):
    def register(self, adapter: AgentRuntimeAdapter) -> None: ...
    def unregister(self, runtime_id: str) -> None: ...
    def get(self, runtime_id: str) -> AgentRuntimeAdapter: ...
    def list(self) -> Sequence[RuntimeDescriptor]: ...
    def find(self, requirements: RuntimeRequirements) -> Sequence[RuntimeCandidate]: ...
```

---

# 7. Registry Scope

Le Registry est :

```text
process-local by default
```

Il ne représente pas nécessairement l’inventaire distribué de tous les workers.

---

# 8. Registry != Worker Registry

```text
RuntimeRegistry
=
what runtime adapters this process knows

WorkerRegistry
=
which workers exist and what they can execute
```

---

# 9. Why Keep Them Separate

Un worker peut annoncer :

```text
native
codex
```

alors qu’un autre worker annonce :

```text
native
langgraph
```

Le RuntimeRegistry décrit la capacité locale.

Le WorkerRegistry décrit la capacité distribuée.

---

# 10. RuntimeIdentity

Value Object stable.

Proposition :

```text
namespace
name
major_version
variant
```

Exemple :

```text
pyagentskit/native@2
langgraph/default@1
openai/agents@1
coding/codex@1
```

---

# 11. Canonical Runtime ID

Format recommandé :

```text
<namespace>/<name>[@<contract-major>]
```

Exemples :

```text
pyagentskit/native@2
langgraph/runtime@1
pydanticai/runtime@1
openai/agents@1
coding/codex@1
```

---

# 12. Human-Friendly Alias

Le Registry peut accepter :

```text
native
langgraph
codex
```

comme alias.

Mais un `RuntimeBinding` durable doit stocker l’identité canonique.

---

# 13. RuntimeDescriptor

Le descriptor décrit un adapter sans l’exécuter.

Proposition :

```text
runtime_id
display_name
adapter_version
runtime_version
contract_version
capabilities
side_effect_control_level
qualification_level
supported_platforms
configuration_schema_ref
metadata
```

---

# 14. Descriptor Invariant

Le descriptor doit être :

```text
cheap to read
side-effect free
stable enough for discovery
```

---

# 15. Runtime Version vs Adapter Version

Distinguer :

```text
adapter_version
runtime_version
contract_version
```

Exemple :

```text
Adapter PyAgentsKit-LangGraph = 0.3.0
LangGraph runtime = 1.x
AgentRuntimeAdapter contract = 2
```

---

# 16. Why Distinguish Versions

Un même adapter peut supporter :

```text
runtime provider versions N..M
```

sans changer le contract PyAgentsKit.

---

# 17. RuntimeCapability

Enum canonique cible :

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

# 18. Capability Semantics

Une capability ne signifie pas :

```text
method exists
```

mais :

```text
behavior has contract-defined semantics
```

---

# 19. START

Le runtime peut démarrer une nouvelle invocation.

---

# 20. RESUME

Le runtime peut poursuivre une invocation existante.

---

# 21. CANCEL

Le runtime peut accepter une demande d’arrêt.

Ne signifie pas rollback.

---

# 22. STATUS

Le runtime peut fournir une observation normalisée de l’état.

---

# 23. EVENT_STREAM

Le runtime peut exposer un flux d’événements.

---

# 24. NATIVE_CHECKPOINT

Le runtime possède sa propre primitive de checkpoint exploitable.

---

# 25. TOOL_INTERCEPTION

PyAgentsKit peut intercepter une demande d’outil avant exécution externe.

---

# 26. MESSAGE_STREAM

Le runtime peut diffuser des messages/tokens structurés.

---

# 27. HUMAN_APPROVAL_HOOK

Le runtime sait se suspendre autour d’une action nécessitant une décision humaine externe.

Cela ne signifie pas que le runtime possède l’Approval.

---

# 28. SUBAGENTS

Le runtime peut orchestrer des sous-agents selon un contrat explicite.

---

# 29. SESSION_RESUME

Le runtime peut reconnecter une session/thread provider existante.

Distinct de `RESUME` si la sémantique le nécessite.

---

# 30. STRUCTURED_OUTPUT

Le runtime peut produire un résultat structuré validable.

---

# 31. WORKSPACE

Le runtime dispose d’un workspace de travail explicite.

---

# 32. COMMAND_EXECUTION

Le runtime sait exécuter des commandes.

---

# 33. FILE_EDITING

Le runtime sait modifier des fichiers.

---

# 34. Capability Truthfulness

Principe :

> **A capability must be declared only if it has passed the corresponding contract tests.**

---

# 35. Capability Lies Are P0

Si un adapter annonce :

```text
RESUME
```

mais recrée en réalité une nouvelle exécution sans garanties équivalentes :

```text
semantic bug
```

potentiellement P0.

---

# 36. RuntimeRequirements

Objet décrivant ce qu’un Run exige.

Proposition :

```text
required_capabilities
preferred_capabilities
forbidden_capabilities
minimum_qualification_level
minimum_side_effect_control
runtime_family
runtime_id
version_constraints
platform_constraints
metadata_constraints
```

---

# 37. Required Capabilities

Si une capability obligatoire manque :

```text
selection fails
```

avant toute invocation.

---

# 38. Preferred Capabilities

Améliorent la sélection mais ne bloquent pas.

Exemple :

```text
NATIVE_CHECKPOINT preferred
```

---

# 39. Forbidden Capabilities

Rarement nécessaires.

Plus utile :

```text
forbid OPAQUE side-effect control
```

plutôt que capability négative.

---

# 40. Minimum Qualification

Exemple :

```text
L2 Integration Tested
```

pour staging.

```text
L4 Production Qualified
```

pour certains workloads critiques.

---

# 41. SideEffectControlLevel

Value Object / enum :

```text
FULL
BOUNDED
OPAQUE
```

---

# 42. FULL

PyAgentsKit peut intercepter tous les Effects critiques pertinents avant exécution.

---

# 43. BOUNDED

Une partie seulement des actions externes est contrôlable.

---

# 44. OPAQUE

Le runtime peut agir à l’extérieur sans interception fiable.

---

# 45. Why Control Level Is Separate from Capability

Un runtime peut annoncer :

```text
TOOL_INTERCEPTION
```

mais seulement pour certains outils.

Donc :

```text
capability
+
control level
```

sont complémentaires.

---

# 46. RuntimeQualificationLevel

Aligné avec les documents de test :

```text
L0 — Fake
L1 — Contract Compliant
L2 — Integration Tested
L3 — Failure Tested
L4 — Production Qualified
```

---

# 47. L0

Adapter de développement/test.

---

# 48. L1

Passe les Contract Tests.

---

# 49. L2

Testé avec runtime/provider réel.

---

# 50. L3

Failure semantics qualifiées.

---

# 51. L4

Production-like qualification complète.

---

# 52. Qualification Is Capability-Scoped

Un adapter peut être :

```text
L4 for START/STATUS
L2 for RESUME
```

si besoin d’une granularité avancée.

---

# 53. Initial Simplification

V2 initial peut stocker un niveau global, avec limitations documentées.

---

# 54. RuntimeBinding

Objet durable liant un Run à une sélection runtime.

Proposition :

```text
binding_id
run_id
runtime_id
adapter_version
runtime_version
required_capabilities
selected_capabilities
configuration_ref
selection_reason
bound_at
```

---

# 55. Binding Purpose

Le `RuntimeBinding` répond à :

```text
which runtime was selected?
with what assumptions?
```

---

# 56. Binding Is Durable

Un Run long ne doit pas redécouvrir silencieusement un autre runtime au milieu de son exécution.

---

# 57. Binding Stability

Par défaut :

```text
same Run
→ same runtime family/binding
```

sauf use case explicite de migration/failover compatible.

---

# 58. Runtime Failover

Changer de runtime en cours de Run est complexe.

Exemple :

```text
LangGraph
→ Native Runtime
```

n’est pas automatiquement sûr.

---

# 59. Default V2 Rule

```text
runtime failover across different runtime families
=
not automatic
```

---

# 60. Same Adapter Failover

Changer de worker tout en gardant :

```text
same runtime adapter + durable handle
```

est normal.

---

# 61. Binding vs Invocation

```text
RuntimeBinding
=
which runtime integration is assigned to the Run

RuntimeInvocation
=
one concrete execution attempt
```

---

# 62. Multiple Invocations per Binding

```text
Run
  └── RuntimeBinding
       ├── Invocation #1
       ├── Invocation #2
       └── Invocation #3
```

---

# 63. Capability Negotiator

Concept :

```python
class CapabilityNegotiator:
    def negotiate(
        self,
        requirements: RuntimeRequirements,
        candidates: Sequence[RuntimeDescriptor],
    ) -> NegotiationResult:
        ...
```

---

# 64. Negotiation Input

```text
requirements
available descriptors
selection policy
environment/profile
```

---

# 65. Negotiation Output

```text
selected candidate
matched capabilities
missing preferred capabilities
selection score/reason
rejected candidates
```

---

# 66. NegotiationResult

Proposition :

```text
selected_runtime_id
satisfied_requirements
missing_preferences
rejected[]
reason
policy_version
```

---

# 67. RejectedCandidate

Inclut :

```text
runtime_id
reason_codes[]
```

---

# 68. Rejection Reason Codes

Exemples :

```text
MISSING_REQUIRED_CAPABILITY
QUALIFICATION_TOO_LOW
SIDE_EFFECT_CONTROL_TOO_WEAK
VERSION_INCOMPATIBLE
PLATFORM_INCOMPATIBLE
RUNTIME_DISABLED
SECURITY_PROFILE_INCOMPATIBLE
```

---

# 69. Selection Is Explainable

L’utilisateur/ops doit pouvoir comprendre :

```text
why runtime A was chosen over B
```

---

# 70. Selection Must Be Deterministic

À :

```text
same registry
same requirements
same policy
```

la sélection doit être stable, hors métriques dynamiques explicitement incluses.

---

# 71. Deterministic Tie-Breaker

Exemples :

```text
explicit priority
runtime_id lexical
configuration order
```

---

# 72. Avoid Random Runtime Selection

Sauf use case explicite.

---

# 73. RuntimeSelectionPolicy

Objet possible :

```text
preferred_runtime_ids
prefer_native
prefer_highest_qualification
prefer_full_control
cost_weight
latency_weight
```

---

# 74. Default Selection Philosophy

Ordre recommandé :

```text
1. satisfy all required semantics
2. maximize side-effect control
3. satisfy preferred capabilities
4. prefer highest qualification
5. apply explicit operator preference
6. use deterministic tie-break
```

---

# 75. Safety Before Cost

Un runtime moins cher ne doit pas être choisi si :

```text
required safety guarantee missing
```

---

# 76. Safety Before Latency

Même principe.

---

# 77. Required Capabilities Example — Durable Tool Agent

```text
START
STATUS
TOOL_INTERCEPTION
```

Avec préférence :

```text
RESUME
NATIVE_CHECKPOINT
```

---

# 78. Required Capabilities Example — Approval-Heavy Agent

```text
START
TOOL_INTERCEPTION
HUMAN_APPROVAL_HOOK
```

---

# 79. Required Capabilities Example — Coding Agent

```text
START
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
```

Et si Git push protégé :

```text
TOOL_INTERCEPTION or equivalent protected-action hook
```

---

# 80. Coding Runtime Safety Requirement

Un coding runtime peut être très capable mais :

```text
OPAQUE
```

sur certaines actions shell/network.

Dans ce cas PyAgentsKit ne doit pas prétendre offrir une garantie `FULL`.

---

# 81. Explicit Degraded Mode

Un Run peut éventuellement autoriser :

```text
BOUNDED
```

control si policy le permet.

Cela doit être :

```text
explicit
audited
visible
```

---

# 82. No Silent Downgrade

Interdit :

```text
requested FULL
→ selected BOUNDED
```

sans erreur/consentement explicite.

---

# 83. Runtime Family Constraint

`RuntimeRequirements` peut demander :

```text
runtime_family = coding
```

ou :

```text
runtime_id = coding/codex@1
```

---

# 84. Strong Binding Request

Si utilisateur/config impose un runtime exact :

```text
selection must either use it or fail
```

---

# 85. Soft Preference

Si config dit :

```text
prefer native
```

le negotiator peut choisir autre runtime si Native ne satisfait pas requirements.

---

# 86. Registry Registration

`register(adapter)` doit :

1. lire descriptor ;
2. valider runtime_id ;
3. valider contract version ;
4. détecter collisions ;
5. vérifier capabilities connues ;
6. enregistrer l’adapter.

---

# 87. Duplicate Registration

Même runtime_id :

```text
error
```

par défaut.

---

# 88. Versioned Multi-Registration

Option future :

```text
same runtime family
multiple adapter versions
```

dans un même process.

Pas nécessaire initialement.

---

# 89. Alias Collision

Deux adapters ne doivent pas posséder le même alias sans résolution explicite.

---

# 90. Registry Freeze

Après bootstrap production :

```text
registry may become immutable
```

pour éviter modifications dynamiques imprévisibles.

---

# 91. Dynamic Plugins

Support futur possible.

Mais :

```text
dynamic adapter loading
```

n’est pas requis pour V2 initiale.

---

# 92. Plugin Discovery

Si introduit :

```text
Python entry points
```

peuvent être utilisés.

---

# 93. Plugin Discovery Safety

Un plugin découvert n’est pas automatiquement :

```text
enabled
trusted
qualified
```

---

# 94. Registration != Authorization

Un adapter présent dans Registry ne signifie pas qu’il est autorisé pour tous les tenants/workloads.

---

# 95. Runtime Enablement Policy

Peut filtrer :

```text
environment
tenant
risk class
feature flag
```

---

# 96. Tenant Restrictions

Exemple :

```text
Tenant A → Native only
Tenant B → Native + LangGraph
```

---

# 97. Security Profile Restrictions

Exemple High Assurance :

```text
minimum_side_effect_control = FULL
minimum_qualification_level = L4
```

---

# 98. Environment Restrictions

En production :

```text
experimental adapters disabled by default
```

---

# 99. Runtime Availability

Le Registry indique disponibilité logique locale.

Mais runtime/provider peut être momentanément indisponible.

---

# 100. Registry Availability != Provider Health

```text
registered
!=
healthy
```

---

# 101. RuntimeHealth

Objet observé séparément.

Proposition :

```text
AVAILABLE
DEGRADED
UNAVAILABLE
UNKNOWN
```

---

# 102. Health Is Dynamic

La sélection initiale peut prendre en compte health si :

```text
policy says so
```

---

# 103. Health Must Not Rewrite Semantics

Un runtime `DEGRADED` n’est pas remplacé automatiquement en milieu de Run par une autre famille.

---

# 104. Runtime Admission

Pour un nouveau Run, health peut exclure :

```text
UNAVAILABLE
```

candidates.

---

# 105. Running Run on Unavailable Runtime

Le RecoveryPlanner peut :

```text
WAIT
RESUME later
MANUAL
```

selon capability.

---

# 106. Runtime Compatibility

Objet :

```text
RuntimeCompatibility
```

peut décrire :

```text
core contract version
adapter contract version
checkpoint format versions
supported provider versions
```

---

# 107. Contract Version

Exemple :

```text
AgentRuntimeAdapter Contract v2
```

---

# 108. Adapter Contract Compatibility

Un adapter contract v1 ne doit pas être enregistré dans Core exigeant v2 sans compatibility layer.

---

# 109. Checkpoint Compatibility

Le Registry/Descriptor peut annoncer :

```text
checkpoint_format_version
```

---

# 110. N/N+1 Rolling Upgrade

Un worker N et worker N+1 doivent pouvoir coexister si :

```text
runtime binding
checkpoint
public contracts
```

restent compatibles.

---

# 111. Runtime Version Drift

Un long Run peut démarrer avec :

```text
adapter version A
```

puis être repris par worker avec version B.

---

# 112. Resume Compatibility Rule

Avant resume :

```text
B must declare compatibility with A-produced durable runtime state
```

---

# 113. Incompatible Resume

Si non compatible :

```text
RESTART_RUNTIME if safe
or
MANUAL_INTERVENTION
```

---

# 114. Binding Version Snapshot

Conserver la version sélectionnée dans `RuntimeBinding`.

---

# 115. Adapter Upgrade Policy

Le descriptor peut exposer :

```text
compatible_from_versions
```

ou un mécanisme équivalent.

---

# 116. Runtime Candidate

Objet transitoire :

```text
descriptor
health
effective capabilities
qualification
policy eligibility
score
```

---

# 117. Effective Capabilities

Peuvent différer des declared capabilities à cause de configuration.

Exemple :

```text
TOOL_INTERCEPTION supported by adapter
but disabled for this runtime mode
```

---

# 118. Configuration-Dependent Capability

Le Registry doit pouvoir calculer :

```text
effective descriptor
```

par binding/config.

---

# 119. Example

Un coding runtime supporte :

```text
COMMAND_EXECUTION
FILE_EDITING
```

mais dans `read_only` mode :

```text
FILE_EDITING unavailable
```

---

# 120. Capability Negotiation Timing

Trois moments :

```text
bootstrap
Run creation
recovery
```

---

# 121. Bootstrap Negotiation

Valide les adapters disponibles.

---

# 122. Run Creation Negotiation

Sélectionne/binde le runtime.

---

# 123. Recovery Negotiation

Ne re-sélectionne pas librement.

Il vérifie :

```text
binding still satisfiable?
adapter compatible?
required capabilities still available?
```

---

# 124. Recovery Capability Drift

Si capability requise disparaît après upgrade/config :

```text
do not silently continue
```

---

# 125. Recovery Outcome

Possible :

```text
MANUAL_INTERVENTION
```

ou rollback de version.

---

# 126. Capability Requirements Source

Peuvent venir de :

```text
RunDefinition
Application policy
Tool set
Risk class
Tenant policy
Runtime-specific configuration
```

---

# 127. Derived Requirements

L’Application peut dériver automatiquement :

```text
Effectful tools present
→ TOOL_INTERCEPTION required
```

---

# 128. Approval-Derived Requirement

Si protected tool nécessite Approval :

```text
HUMAN_APPROVAL_HOOK
```

ou capacité équivalente de suspension durable peut être requise.

---

# 129. Durable Execution Requirement

Si Run doit survivre process loss sans full restart :

```text
RESUME or restart-safe checkpoint capability
```

---

# 130. Structured Output Requirement

Si downstream attend schema :

```text
STRUCTURED_OUTPUT
```

peut devenir required.

---

# 131. Coding Requirement

Si Run modifie un repo :

```text
WORKSPACE
FILE_EDITING
```

required.

---

# 132. Command Requirement

Si Run exécute tests/build :

```text
COMMAND_EXECUTION
```

required.

---

# 133. Requirement Inference Must Be Explainable

Le système doit pouvoir expliquer :

```text
TOOL_INTERCEPTION required because Run includes protected external tools.
```

---

# 134. RuntimeRequirements Builder

Pattern possible :

```python
requirements = RuntimeRequirements.for_run(run_spec)
```

mais la logique métier doit rester explicite.

---

# 135. Requirements Are Immutable Snapshot

Après binding :

```text
required capabilities
```

doivent être durables pour audit/recovery.

---

# 136. Requirement Changes Mid-Run

Si le Run acquiert un nouveau besoin :

```text
new tool requiring FILE_EDITING
```

le binding doit être revalidé.

---

# 137. Mid-Run Capability Escalation

Si runtime courant ne supporte pas :

```text
fail/wait
```

plutôt que migration automatique vers autre runtime.

---

# 138. Optional Runtime Rebinding

Future capability :

```text
RuntimeRebinding
```

peut être définie avec règles strictes.

Non-goal V2 initial.

---

# 139. Runtime Selection API

Use case possible :

```text
SelectRuntime
```

---

# 140. SelectRuntime Inputs

```text
RuntimeRequirements
tenant
environment
risk profile
optional preference
```

---

# 141. SelectRuntime Output

```text
RuntimeSelection
```

---

# 142. RuntimeSelection

Champs :

```text
runtime_id
descriptor_snapshot
requirements_snapshot
selection_reason
selected_at
policy_version
```

---

# 143. Persist Selection

La sélection devient :

```text
RuntimeBinding
```

au démarrage du Run.

---

# 144. No Late Surprise

Le système doit échouer :

```text
before expensive work
```

si requirements impossibles.

---

# 145. Selection Failure

Erreur canonique :

```text
NoCompatibleRuntime
```

---

# 146. Missing Capability Error

Détail :

```text
MissingRuntimeCapabilities
```

avec :

```text
required
available
missing
```

---

# 147. Qualification Error

```text
RuntimeQualificationInsufficient
```

---

# 148. Control Level Error

```text
RuntimeSideEffectControlInsufficient
```

---

# 149. Version Error

```text
RuntimeVersionIncompatible
```

---

# 150. Disabled Runtime Error

```text
RuntimeDisabled
```

---

# 151. RuntimeNotRegistered

Pour binding explicite absent.

---

# 152. CapabilityNegotiationError

Base commune possible.

---

# 153. Error Messages

Doivent être actionnables.

Exemple :

```text
Run requires TOOL_INTERCEPTION and FULL side-effect control.
Adapter coding/codex@1 provides TOOL_INTERCEPTION with BOUNDED control.
```

---

# 154. Selection Scoring

Le score n’est appliqué qu’après satisfaction des hard constraints.

---

# 155. Hard Constraints

```text
required capabilities
minimum qualification
minimum control level
version compatibility
security policy
platform
explicit runtime id
```

---

# 156. Soft Constraints

```text
preferred capabilities
cost
latency
operator preference
native preference
```

---

# 157. Suggested Scoring Order

Exemple conceptuel :

```text
FULL control            +100
preferred capability     +20 each
qualification level      +10/level
explicit preference      +5
```

Mais ne pas figer des poids arbitraires dans Domain.

---

# 158. Policy Owns Weights

Si scoring numérique utilisé :

```text
selection policy
```

possède les poids.

---

# 159. Simpler Alternative

Préférable initialement :

```text
lexicographic ranking
```

plutôt que score opaque.

---

# 160. Lexicographic Ranking

Exemple :

```text
control level
→ qualification level
→ preferred capability count
→ configured priority
→ runtime_id
```

---

# 161. Why Prefer Lexicographic

Plus :

```text
explainable
testable
stable
```

---

# 162. Registry Persistence

Le RuntimeRegistry lui-même n’a pas besoin d’être persistant.

---

# 163. What Must Be Persisted

```text
RuntimeBinding
descriptor snapshot
requirements snapshot
```

---

# 164. Why Snapshot Descriptor

Parce qu’après upgrade :

```text
current descriptor
```

peut différer de ce qui a été sélectionné historiquement.

---

# 165. Snapshot Size

Conserver seulement données pertinentes :

```text
runtime_id
versions
capabilities
control level
qualification
```

---

# 166. Runtime Descriptor Source

Chaque adapter fournit son descriptor.

---

# 167. Descriptor Validation

Le Registry vérifie :

```text
known capabilities
valid semantic version
unique runtime id
supported contract major
```

---

# 168. Descriptor Tampering

Pour plugins tiers, le descriptor est :

```text
self-declared metadata
```

et la qualification réelle doit venir des tests/evidence.

---

# 169. Trust Model

Ne pas confondre :

```text
adapter says L4
```

avec :

```text
PyAgentsKit verified L4
```

---

# 170. Qualification Authority

Le Core peut distinguer :

```text
SELF_DECLARED
VERIFIED
FIRST_PARTY_VERIFIED
```

---

# 171. Initial Simplification

V2 initial peut limiter les badges officiels aux adapters first-party.

---

# 172. Third-Party Adapter Metadata

Exposer :

```text
qualification_source
```

si nécessaire.

---

# 173. Runtime Families

Candidats :

```text
NATIVE
GENERAL_AGENT
CODING_AGENT
CUSTOM
```

---

# 174. Family Is Descriptive

Elle ne remplace pas les capabilities.

---

# 175. Why Capabilities Win

Deux runtimes de même famille peuvent avoir des garanties très différentes.

---

# 176. General Agent Example

LangGraph peut supporter :

```text
START
RESUME
STATUS
...
```

selon adapter.

---

# 177. Coding Agent Example

Codex peut supporter :

```text
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
```

mais side-effect interception dépend du mode d’intégration.

---

# 178. Registry Query API

Exemples :

```text
list runtimes
show runtime
find compatible runtimes
explain selection
```

---

# 179. Future CLI

```text
pyagentskit runtimes list
pyagentskit runtimes show native
pyagentskit runtimes match --require RESUME,TOOL_INTERCEPTION
```

---

# 180. Runtime Registry Read Model

Afficher :

```text
runtime_id
version
capabilities
control level
qualification
enabled
health
```

---

# 181. Operations Use

Permet de voir :

```text
why new coding Runs cannot start
```

après adapter disable.

---

# 182. Health and Readiness

Worker readiness peut dépendre des runtimes obligatoires.

---

# 183. Worker Runtime Capability Advertisement

Le WorkerRegistry peut publier :

```text
available runtime_ids
effective capabilities
```

---

# 184. Distributed Scheduling

Le scheduler/admission peut router un Run vers un worker ayant le bon runtime.

---

# 185. Important

```text
worker routing
!=
runtime selection
```

Runtime selection choisit le binding.

Worker routing trouve un worker capable de l’exécuter.

---

# 186. Example

```text
RuntimeBinding = coding/codex@1
```

Puis workers éligibles :

```text
worker-03
worker-07
```

---

# 187. No Worker Available

Le Run reste :

```text
WAITING
```

ou admission rejected selon use case.

---

# 188. Worker Capability Drift

Un worker peut perdre accès à un runtime.

WorkerRegistry doit être mis à jour.

---

# 189. Runtime Registry Startup Checks

Au démarrage :

```text
validate descriptors
validate configuration
optional smoke check
```

---

# 190. Smoke Check

Peut vérifier :

```text
SDK import
credential reference present
provider endpoint configured
```

sans forcément lancer un agent.

---

# 191. Deep Health Check

Peut être coûteux.

À séparer de liveness.

---

# 192. Registry Fail-Fast

Une configuration explicitement requise mais invalide peut empêcher readiness.

---

# 193. Optional Runtime Failure

Un adapter optionnel cassé ne doit pas forcément empêcher tout le process de démarrer.

---

# 194. Required Runtime Set

Configuration peut déclarer :

```text
required_at_startup
```

---

# 195. Example

Production worker coding pool :

```text
required_at_startup = [coding/codex@1]
```

---

# 196. Runtime Disable

Un runtime peut être administrativement désactivé.

---

# 197. Disable Semantics

```text
no new bindings
```

Par défaut, les Runs déjà bindés sont traités selon recovery policy.

---

# 198. Hard Disable

Pour incident critique :

```text
no start/resume
```

même pour existing bindings.

---

# 199. Kill Switch vs Runtime Disable

```text
Runtime Disable
=
stop using runtime

Effect Kill Switch
=
stop classes of external Effects
```

Distincts.

---

# 200. Runtime Quarantine

État possible ops :

```text
QUARANTINED
```

après bug provider/adapter.

---

# 201. Quarantine Behavior

```text
new selection forbidden
existing Runs wait/manual
```

---

# 202. RuntimeLifecycle Admin State

Possible :

```text
ENABLED
DISABLED
QUARANTINED
```

---

# 203. Capability Deprecation

Une capability peut être retirée dans une version future.

---

# 204. Deprecation Rule

Adapter doit :

```text
announce change
respect SemVer
```

---

# 205. Run Bound to Deprecated Capability

Existing Run doit rester recoverable pendant compatibility window ou être explicitement migrated/manual.

---

# 206. Contract Major Versioning

Une redéfinition de `RESUME` peut nécessiter :

```text
contract major bump
```

---

# 207. Capability Extensions

Ajouter une capability optionnelle est généralement compatible.

---

# 208. RuntimeDescriptor Versioning

Le descriptor schema doit lui-même être versionnable.

---

# 209. Capability Names Stability

Les noms publics deviennent contractuels avant stable.

---

# 210. Registry Thread Safety

Le Registry peut être lu par plusieurs tasks.

---

# 211. Immutable Registry Recommendation

Après bootstrap :

```text
read-only mapping
```

simplifie concurrency.

---

# 212. Dynamic Updates

Si supportés, utiliser lock/version snapshot.

Non nécessaire initialement.

---

# 213. Registry Lookup Complexity

Doit rester simple :

```text
O(1) by runtime_id
O(N) for match
```

N est faible.

---

# 214. No Need for External Database

Le Registry local ne justifie pas un service dédié.

---

# 215. Runtime Candidate Filtering Flow

```text
all registered
   │
   ▼
enabled?
   │
   ▼
contract compatible?
   │
   ▼
required capabilities?
   │
   ▼
control level?
   │
   ▼
qualification?
   │
   ▼
platform/policy?
   │
   ▼
rank preferences
   │
   ▼
selected
```

---

# 216. Capability Negotiation Example — Native vs External

Requirements :

```text
START
RESUME
TOOL_INTERCEPTION
FULL control
L3+
```

Candidates :

```text
Native: all satisfied, L4, FULL
Runtime B: START/RESUME, no tool interception
Runtime C: all capabilities, BOUNDED
```

Result :

```text
Native selected
```

---

# 217. Explain Output

```text
Runtime B rejected: missing TOOL_INTERCEPTION.
Runtime C rejected: side-effect control BOUNDED < FULL.
Native selected: all hard requirements satisfied.
```

---

# 218. Capability Negotiation Example — Coding

Requirements :

```text
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
L2+
```

Preferred :

```text
TOOL_INTERCEPTION
EVENT_STREAM
```

Le negotiator choisit le runtime coding le mieux qualifié.

---

# 219. Capability Negotiation Example — Structured Extraction

Requirements :

```text
START
STRUCTURED_OUTPUT
```

Pas besoin de :

```text
TOOL_INTERCEPTION
```

si aucun Effect.

---

# 220. Capability Negotiation Example — Pure Read Agent

Peut accepter :

```text
BOUNDED
```

side-effect control si aucun write possible.

---

# 221. Derived Side-Effect Requirement

Si tool set est purement read-only :

```text
minimum control level may be relaxed
```

selon policy.

---

# 222. Tool Inventory Influence

Les RuntimeRequirements peuvent être calculés après analyse de :

```text
ToolDefinitions
ToolRisks
Effect classifications
```

---

# 223. Runtime + Connector Combined Feasibility

Un Run peut avoir un runtime compatible mais aucun Connector capable de reconciliation.

La sélection runtime seule ne suffit pas.

---

# 224. Application Feasibility Check

Avant start :

```text
Runtime requirements
+
Connector requirements
+
Governance requirements
```

doivent être satisfaits ensemble.

---

# 225. No Hidden Cross-Dependency

Le RuntimeRegistry ne doit pas connaître directement tous les Connectors.

L’Application orchestre les checks.

---

# 226. Capability Negotiation and Approvals

Si runtime ne sait pas attendre durablement :

```text
HUMAN_APPROVAL_HOOK absent
```

PyAgentsKit peut parfois externaliser l’attente en arrêtant/restartant le runtime.

---

# 227. Equivalent Capability Semantics

Donc un besoin métier peut être satisfaisable par plusieurs patterns :

```text
native pause/resume
or
safe restart from durable state
```

---

# 228. Requirement Profiles

Pour éviter rigidité, définir des profils de besoin.

Exemple :

```text
DURABLE_WAIT
```

peut être satisfait par :

```text
RESUME
or
safe RESTART capability
```

---

# 229. Composite Requirements

Concept possible :

```text
CapabilityExpression
```

---

# 230. Expression Examples

```text
RESUME OR NATIVE_CHECKPOINT
TOOL_INTERCEPTION AND STATUS
WORKSPACE AND FILE_EDITING
```

---

# 231. Avoid Overengineering

V2 initial peut commencer avec :

```text
required set
preferred set
minimum control
```

et ajouter expressions composites lorsque nécessaire.

---

# 232. Runtime Requirements Profiles

Candidats :

```text
BASIC_AGENT
DURABLE_AGENT
PROTECTED_EFFECT_AGENT
APPROVAL_AWARE_AGENT
CODING_AGENT
```

---

# 233. Profiles Are Convenience

Ils compilent vers des requirements explicites.

---

# 234. BASIC_AGENT

```text
START
STATUS preferred
```

---

# 235. DURABLE_AGENT

```text
START
STATUS
RESUME preferred
NATIVE_CHECKPOINT preferred
```

---

# 236. PROTECTED_EFFECT_AGENT

```text
START
TOOL_INTERCEPTION
minimum_control = FULL
```

---

# 237. APPROVAL_AWARE_AGENT

```text
PROTECTED_EFFECT_AGENT
+
HUMAN_APPROVAL_HOOK preferred/required depending engine strategy
```

---

# 238. CODING_AGENT

```text
START
WORKSPACE
COMMAND_EXECUTION
FILE_EDITING
```

---

# 239. Runtime Registry Package

Topologie cible :

```text
domain/
  runtime_integration/
    capability.py
    descriptor.py
    requirements.py
    binding.py

application/
  runtime_integration/
    select_runtime.py
    negotiate_capabilities.py

adapters/
  runtimes/
    registry.py
```

---

# 240. Alternative Placement

Le Registry concret peut être dans :

```text
bootstrap/runtime_registry.py
```

si pure composition concern.

Mais les contracts `RuntimeRegistry`/selection restent au bon niveau.

---

# 241. Domain vs Application

`RuntimeCapability` et `RuntimeRequirements` sont canoniques.

La sélection concrète d’un adapter est :

```text
Application/Integration concern
```

---

# 242. Registry Port

`RuntimeRegistry` figure dans le catalog des outbound ports.

---

# 243. In-Memory Registry

Première implémentation :

```text
InMemoryRuntimeRegistry
```

suffit.

---

# 244. Why No Persistent Registry Initially

Les adapters sont généralement chargés :

```text
at process startup
```

---

# 245. Runtime Binding Repository

En revanche, `RuntimeBinding` est durable.

---

# 246. RuntimeBinding Persistence

Peut être dans :

```text
runtime_bindings
```

table PostgreSQL cible.

---

# 247. RuntimeInvocation Persistence

Dans :

```text
runtime_invocations
```

---

# 248. Binding Foreign Keys

Conceptuellement :

```text
runtime_binding.run_id → runs.id
```

---

# 249. Descriptor Snapshot Storage

JSONB acceptable pour metadata versionnée, tant que fields critiques sont explicitement accessibles si nécessaire.

---

# 250. Capability Storage

Possibilités :

```text
JSON array
text array
normalized relation
```

Pour V2, array/JSON peut suffire.

---

# 251. Qualification Storage

Le binding conserve le niveau observé lors de la sélection.

---

# 252. Runtime Registry Events

Domain/Application events possibles :

```text
RuntimeRegistered
RuntimeDisabled
RuntimeQuarantined
RuntimeSelected
RuntimeBindingCreated
```

---

# 253. Registration Event

Pas forcément DomainEvent si bootstrap statique.

---

# 254. RuntimeSelected

Peut être AuditEvent utile.

---

# 255. Audit Payload

```text
run_id
runtime_id
requirements
selection_reason
policy_version
```

---

# 256. Security

La sélection runtime peut révéler :

```text
available internal runtimes
```

à ne pas exposer à tous les utilisateurs.

---

# 257. Admin Query Authorization

`list runtimes` peut être restreint.

---

# 258. User-Level Runtime Choice

Un produit peut autoriser un utilisateur à demander :

```text
runtime = codex
```

mais l’Application doit vérifier :

```text
tenant policy
authorization
qualification
requirements
```

---

# 259. User Preference != Authority

Une préférence utilisateur ne force pas un runtime incompatible.

---

# 260. Runtime Configuration Security

`configuration_ref` ne contient pas de secret résolu.

---

# 261. Credentials

Résolus via :

```text
SecretProvider
```

au moment approprié.

---

# 262. Capability Negotiation Security

Un runtime OPAQUE ne doit pas être sélectionné pour high-risk protected Effects si policy exige FULL.

---

# 263. Trust Boundary

Le runtime est potentiellement :

```text
semi-trusted or external
```

Le Registry ne transforme pas une capability déclarée en authority métier.

---

# 264. Structured Output Caveat

`STRUCTURED_OUTPUT` :

```text
shape guarantee
```

pas :

```text
truth guarantee
```

---

# 265. Human Approval Caveat

`HUMAN_APPROVAL_HOOK` :

```text
pause/control integration
```

pas :

```text
Approval authority
```

---

# 266. Workspace Caveat

`WORKSPACE` :

```text
workspace semantics
```

pas nécessairement :

```text
sandbox security
```

---

# 267. Command Execution Caveat

`COMMAND_EXECUTION` ne signifie pas :

```text
safe arbitrary shell
```

---

# 268. Capability Documentation

Chaque capability doit posséder :

```text
definition
required behavior
non-guarantees
contract tests
```

---

# 269. Capability Registry

Une table documentaire doit devenir canonique avant stable.

---

# 270. Runtime Adapter Compliance Report

Chaque adapter produit :

```text
runtime_id
adapter version
contract version
capabilities
qualification
control level
known limitations
```

---

# 271. Native Runtime Example Report

```text
runtime_id: pyagentskit/native@2
control: FULL
qualification: L4 target
capabilities:
  START
  RESUME
  CANCEL
  STATUS
  EVENT_STREAM
  NATIVE_CHECKPOINT
  TOOL_INTERCEPTION
  HUMAN_APPROVAL_HOOK
  STRUCTURED_OUTPUT
```

Valeurs finales basées sur tests réels.

---

# 272. External Runtime Example Report

```text
runtime_id: langgraph/runtime@1
control: depends on integration
qualification: L2/L3 target
```

Ne pas copier les claims provider sans qualification PyAgentsKit.

---

# 273. Coding Runtime Example Report

```text
runtime_id: coding/codex@1
capabilities:
  START
  WORKSPACE
  COMMAND_EXECUTION
  FILE_EDITING
```

Les capabilities Effect/approval doivent être démontrées séparément.

---

# 274. Observability

Metrics :

```text
runtime_registry_registered
runtime_selection_total
runtime_selection_failures_total
runtime_capability_mismatch_total
runtime_bindings_active
```

---

# 275. Metric Labels

Faible cardinalité :

```text
runtime_type
reason
qualification
control_level
```

---

# 276. Selection Latency

Doit être négligeable.

Le Registry n’est pas sur le chemin dominant coûteux.

---

# 277. Audit Metrics

Nombre de selections fallback peut révéler configuration drift.

---

# 278. Alerts

Alertes possibles :

```text
required runtime unavailable
runtime quarantined with active Runs
capability mismatch after deploy
adapter version incompatibility
```

---

# 279. Startup Diagnostics

Afficher :

```text
registered runtimes
versions
capabilities
qualification
```

sans secrets.

---

# 280. Recovery Integration

`RecoveryPlanner` utilise le binding existant.

---

# 281. Recovery Inputs

```text
RuntimeBinding
RuntimeDescriptor current
RuntimeInvocation
compatibility assessment
```

---

# 282. Recovery Compatibility Check

Questions :

```text
adapter still registered?
version compatible?
required capabilities still available?
checkpoint readable?
control level still sufficient?
```

---

# 283. Missing Adapter on Recovery

Si le runtime bindé n’est plus installé :

```text
MANUAL_INTERVENTION
```

ou install/rollback operational fix.

---

# 284. Incompatible Adapter Upgrade

Même résultat par défaut.

---

# 285. Safe Runtime Restart

Possible seulement si :

```text
same binding semantics
```

et RecoveryPlanner l’autorise.

---

# 286. Runtime Migration

Changer runtime family nécessite use case spécifique futur.

---

# 287. Registry and Deployment

Des worker pools peuvent charger des registries différents.

---

# 288. General Worker Pool

```text
native
langgraph
```

---

# 289. Coding Worker Pool

```text
codex
claude-code
```

---

# 290. Admission Routing

Le système combine :

```text
RuntimeBinding
+
Worker capabilities
```

pour choisir un worker.

---

# 291. No Runtime on Eligible Workers

Run reste en attente.

---

# 292. Capability Advertisement Freshness

Worker heartbeat peut publier :

```text
runtime capabilities hash
```

---

# 293. Descriptor Hash

Possible :

```text
descriptor_hash
```

pour détecter drift.

---

# 294. Worker Drift

Deux workers prétendent même runtime_id mais versions différentes.

Doit être visible.

---

# 295. Mixed Version Policy

Peut être autorisée pendant rolling upgrade.

---

# 296. Outside Upgrade Window

Unexpected drift peut déclencher :

```text
warning/quarantine
```

---

# 297. Testing Strategy

Unit tests :

```text
requirements matching
rejection reasons
ranking
version compatibility
```

---

# 298. Contract Tests

Chaque runtime adapter passe :

```text
AgentRuntimeAdapterContract
```

---

# 299. Registry Unit Tests

```text
register
duplicate
get
list
find
alias
disabled runtime
```

---

# 300. Negotiation Tests

```text
all required present
one capability missing
qualification too low
control too weak
exact runtime requested
preferred fallback
deterministic tie-break
```

---

# 301. Capability Drift Tests

Après descriptor update :

```text
existing binding recovery check
```

---

# 302. Version Tests

```text
compatible N→N+1
incompatible checkpoint
unsupported contract major
```

---

# 303. Security Tests

```text
tenant disallowed runtime
high-assurance OPAQUE rejected
unqualified adapter rejected
```

---

# 304. Distributed Tests

```text
binding requires runtime X
only worker B advertises X
Run routed to B
```

---

# 305. Production Qualification

Doit prouver :

```text
runtime selection before start
capability mismatch fail-fast
rolling upgrade compatibility
adapter quarantine
recovery with same binding
```

---

# 306. P0 Tests

```text
RREG-P0-01 required capability missing → no execution
RREG-P0-02 FULL required / BOUNDED offered → rejected
RREG-P0-03 stale/incompatible adapter cannot resume
RREG-P0-04 explicit runtime unavailable → fail, no fallback
RREG-P0-05 binding immutable through recovery
RREG-P0-06 capability lie caught by contract suite
RREG-P0-07 high-risk Run cannot use OPAQUE runtime
RREG-P0-08 runtime provider identity does not alter Effect semantics
```

---

# 307. Property Tests

Possibles :

```text
selected candidate always satisfies hard requirements
adding incompatible candidate never changes selection
same input yields same selection
```

---

# 308. Determinism Property

```text
negotiate(R, C, P) == negotiate(R, C, P)
```

pour mêmes inputs ordonnés/canoniques.

---

# 309. Monotonic Safety Property

Ajouter un candidat moins sûr ne doit pas faire sélectionner un runtime violant les hard constraints.

---

# 310. Contract with Bootstrap

Bootstrap doit :

```text
instantiate adapters
register them
validate registry
freeze registry
```

---

# 311. Contract with Application

Application demande :

```text
select runtime
```

via abstractions, pas `NativeRuntimeAdapter` concret.

---

# 312. Contract with Worker

Worker exécute seulement un binding qu’il sait satisfaire.

---

# 313. Contract with RecoveryPlanner

Planner ne choisit pas librement un nouveau runtime.

Il vérifie le runtime binding existant.

---

# 314. Contract with Public API

L’API peut permettre :

```text
preferred runtime
```

mais ne doit pas exposer des internals non stables.

---

# 315. Contract with CLI

CLI admin peut inspecter :

```text
runtimes
capabilities
bindings
```

---

# 316. Anti-Pattern — Select by String Everywhere

Éviter :

```python
if runtime_name == ...
```

hors Registry/bootstrap.

---

# 317. Anti-Pattern — Runtime Brand as Guarantee

```text
"LangGraph supports durable execution"
```

ne suffit pas.

PyAgentsKit doit tester les capabilities réellement intégrées.

---

# 318. Anti-Pattern — Assume Provider Claim

Un claim marketing/provider n’est pas un contract PyAgentsKit.

---

# 319. Anti-Pattern — Silent Fallback

Interdit pour runtime exact ou hard requirements.

---

# 320. Anti-Pattern — Best Effort Capability

Une capability required ne peut pas devenir :

```text
best effort
```

---

# 321. Anti-Pattern — Runtime Migration on Error

Ne pas changer de famille runtime automatiquement sur timeout.

---

# 322. Anti-Pattern — Registry as Plugin Marketplace

Hors scope.

---

# 323. Anti-Pattern — Persistent Service Registry

Inutile initialement.

---

# 324. Anti-Pattern — Qualification Self-Assertion

Un adapter ne s’auto-certifie pas L4 sans evidence.

---

# 325. Anti-Pattern — Capability Without Contract Test

Interdit pour adapter officiel.

---

# 326. Anti-Pattern — SideEffectControl Hidden

Doit être explicite.

---

# 327. Anti-Pattern — User Preference Overrides Security

Interdit.

---

# 328. Anti-Pattern — Worker Has Runtime Therefore Run Can Use It

Il faut également :

```text
requirements
policy
qualification
```

---

# 329. Runtime Registry Invariants

```text
RREG-INV-01 Runtime selection is capability-driven.
RREG-INV-02 Required capabilities are never silently downgraded.
RREG-INV-03 Runtime identity is durable and canonical.
RREG-INV-04 Binding is distinct from Invocation.
RREG-INV-05 A Run does not silently switch runtime family.
RREG-INV-06 Capability declarations must be contract-tested.
RREG-INV-07 Qualification level is evidence-based.
RREG-INV-08 Side-effect control level is explicit.
RREG-INV-09 Registry presence does not imply runtime health.
RREG-INV-10 Registry presence does not imply authorization.
RREG-INV-11 Recovery respects the existing RuntimeBinding.
RREG-INV-12 Version compatibility is checked before resume.
RREG-INV-13 Native runtime is not privileged.
RREG-INV-14 Provider-specific types do not enter Domain.
RREG-INV-15 Selection is deterministic and explainable.
```

---

# 330. Runtime Capability Contract Table

| Capability | Must Prove | Does NOT Mean |
|---|---|---|
| START | can create invocation | durable recovery |
| RESUME | continue same logical invocation | replay-safe Effects |
| CANCEL | accepts stop request | rollback |
| STATUS | normalized inspection | external truth |
| EVENT_STREAM | emits runtime events | durable audit |
| NATIVE_CHECKPOINT | checkpoint usable | Effect source of truth |
| TOOL_INTERCEPTION | pre-tool control | all tools necessarily safe |
| HUMAN_APPROVAL_HOOK | can pause around approval | owns Approval authority |
| STRUCTURED_OUTPUT | schema-shaped output | truthful output |
| WORKSPACE | explicit workspace | secure sandbox |
| COMMAND_EXECUTION | execute commands | commands are safe |
| FILE_EDITING | mutate files | Git actions are safe |

---

# 331. Runtime Selection Example — High Assurance

Requirements :

```text
required:
  START
  STATUS
  TOOL_INTERCEPTION

minimum_side_effect_control:
  FULL

minimum_qualification:
  L4
```

Si aucun candidate :

```text
NoCompatibleRuntime
```

et non fallback vers BOUNDED.

---

# 332. Runtime Selection Example — Development

Requirements :

```text
START
```

Policy :

```text
minimum qualification L0
```

Native Fake peut être acceptable.

---

# 333. Runtime Selection Example — Staging

Minimum :

```text
L2
```

---

# 334. Runtime Selection Example — Production

Selon risk :

```text
L3 or L4
```

---

# 335. Runtime Selection Profiles

Possibles :

```text
DEV
TEST
STAGING
PRODUCTION
HIGH_ASSURANCE
```

---

# 336. Profile Mapping

```text
DEV
→ L0+

TEST
→ L1+

STAGING
→ L2+

PRODUCTION
→ L3+ or L4 for critical

HIGH_ASSURANCE
→ L4 + FULL control
```

---

# 337. Qualification Promotion

Un adapter monte :

```text
L0
→ L1
→ L2
→ L3
→ L4
```

sans changer runtime_id nécessairement.

---

# 338. Qualification Regression

Si nouvelle version casse une garantie :

```text
qualification may be downgraded
```

jusqu’à requalification.

---

# 339. Version-Specific Qualification

Le niveau appartient idéalement à :

```text
adapter version
```

et non au nom abstrait pour toujours.

---

# 340. Runtime Registry Documentation

Pour chaque adapter officiel, publier une fiche :

```text
identity
versions
capabilities
control level
qualification
supported environments
known limitations
```

---

# 341. Capability Matrix Documentation

Exemple :

| Runtime | Resume | Tool Interception | Checkpoint | Coding | Control | Level |
|---|---:|---:|---:|---:|---|---|
| Native | ✓ | ✓ | ✓ | partial | FULL | target L4 |
| Runtime A | ✓ | ✓/partial | ✓ | no | BOUNDED/FULL | target |
| Coding Runtime | varies | varies | varies | ✓ | varies | target |

Aucun tableau public ne doit contenir des claims non testés.

---

# 342. Runtime Registry API Acceptance Criteria

Le Registry est conforme si :

1. adapter registration est explicitement validée ;
2. runtime IDs sont uniques ;
3. descriptors sont accessibles sans exécution ;
4. capabilities sont canoniques ;
5. required capabilities bloquent la sélection si absentes ;
6. preferred capabilities influencent sans bloquer ;
7. qualification level est pris en compte ;
8. side-effect control est pris en compte ;
9. explicit runtime binding ne fallback pas silencieusement ;
10. sélection est déterministe ;
11. raisons de rejet sont explicables ;
12. RuntimeBinding est durable ;
13. RuntimeInvocation reste distinct ;
14. recovery respecte le binding ;
15. version compatibility est vérifiée ;
16. Registry est distinct du WorkerRegistry ;
17. provider health est distinct de registration ;
18. tenant/security policy peut filtrer ;
19. Native passe le même mécanisme que les autres ;
20. aucune branche provider-specific n’existe dans le Core.

---

# 343. Definition of Done

`../runtime/34_PYAGENTSKIT_RUNTIME_REGISTRY_AND_CAPABILITY_NEGOTIATION.md` est considéré mature lorsque :

1. `RuntimeCapability` est stabilisé ;
2. `RuntimeDescriptor` est implémenté ;
3. `RuntimeRequirements` est implémenté ;
4. `RuntimeBinding` est implémenté et durable ;
5. `RuntimeRegistry` existe ;
6. `InMemoryRuntimeRegistry` existe ;
7. `CapabilityNegotiator` existe ;
8. hard vs soft constraints sont testées ;
9. `SideEffectControlLevel` est stabilisé ;
10. `RuntimeQualificationLevel` est stabilisé ;
11. Native Runtime est enregistré via Registry ;
12. au moins un runtime externe peut être enregistré ;
13. sélection fail-fast sur capability manquante ;
14. sélection fail-fast sur qualification insuffisante ;
15. sélection fail-fast sur control insuffisant ;
16. exact runtime binding ne fallback pas ;
17. recovery vérifie compatibility du binding ;
18. distributed worker routing consomme runtime capability advertisement ;
19. Contract Tests alimentent le niveau de qualification ;
20. Production Qualification inclut selection/drift/quarantine.

---

# 344. Résumé

Le modèle cible est :

```text
RUN / WORKLOAD
      │
      ▼
RuntimeRequirements
      │
      ▼
CapabilityNegotiator
      │
      ├───────────────┬───────────────┐
      ▼               ▼               ▼
 Native Adapter   Runtime Adapter B  Coding Adapter
      │               │               │
      └───────────────┴───────────────┘
                      │
                      ▼
               Hard Constraints
                      │
       ┌──────────────┼───────────────┐
       ▼              ▼               ▼
 capabilities   control level   qualification
       │              │               │
       └──────────────┼───────────────┘
                      ▼
                Ranked Candidates
                      │
                      ▼
                RuntimeBinding
                      │
                      ▼
             RuntimeInvocation(s)
```

La sélection doit toujours suivre :

```text
requirements
→ compatibility
→ safety/control
→ qualification
→ preferences
→ deterministic selection
```

et jamais :

```text
brand preference
→ hope capabilities exist
```

La règle fondamentale est :

> **PyAgentsKit ne doit jamais demander à un runtime de fournir une garantie qu’il n’a pas explicitement déclarée et démontrée ; la négociation de capacités transforme la neutralité runtime d’une promesse architecturale en contrat exécutable.**
