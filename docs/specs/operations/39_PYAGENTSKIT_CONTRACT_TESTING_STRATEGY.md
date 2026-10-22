# PyAgentsKit — Contract Testing Strategy

**Document :** `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Test Architecture — Contract Testing  
**Projet :** PyAgentsKit  

---

# 1. Objet

Ce document définit la stratégie de **Contract Testing** de PyAgentsKit V2.

L’objectif est de garantir que plusieurs implémentations d’un même Port respectent les **mêmes garanties observables**, même si leur technologie sous-jacente est différente.

Exemples :

```text
MemoryRepository
SQLiteRepository
PostgresRepository
```

ou :

```text
NativeRuntimeAdapter
LangGraphRuntimeAdapter
PydanticAIRuntimeAdapter
OpenAIAgentsRuntimeAdapter
```

Le principe fondamental est :

> **A Python Protocol defines shape. A Contract Test Suite defines behavior.**

Autrement dit :

```text
same method signatures
!=
same semantics
```

---

# 2. Pourquoi les Contract Tests sont essentiels

PyAgentsKit est construit autour de :

```text
DDD
+
Hexagonal Architecture
+
Ports & Adapters
+
Provider Neutrality
```

La promesse d’interchangeabilité ne peut pas reposer uniquement sur le typage.

Sans Contract Tests :

```text
Port interface
+
multiple adapters
+
divergent failure semantics
=
unsafe portability
```

La stratégie contractuelle doit donc vérifier :

- comportement nominal ;
- erreurs canoniques ;
- idempotency ;
- ordering ;
- tenant isolation ;
- concurrency ;
- capability support ;
- failure semantics ;
- round-trip fidelity ;
- invariants safety-critical.

---

# 3. Ce qu’un Contract Test prouve

Un Contract Test permet de dire :

```text
If Adapter X passes Contract Suite Y,
Application Layer may rely on guarantees Y.
```

Il valide le **comportement observable** du Port.

Il ne dépend pas de :

```text
SQL exact
SDK-specific classes
private implementation details
provider internals
```

---

# 4. Ce qu’un Contract Test ne prouve pas seul

Il ne suffit pas pour certifier :

```text
production scale
provider SLA
high availability
performance under load
security of the complete deployment
```

Ces preuves appartiennent à :

```text
integration testing
failure testing
distributed qualification
production qualification
```

---

# 5. Contract Testing Levels

PyAgentsKit définit cinq niveaux :

```text
CTL0 — Structural Contract
CTL1 — Behavioral Contract
CTL2 — Failure Contract
CTL3 — Concurrency Contract
CTL4 — Provider Qualification Contract
```

## CTL0 — Structural Contract

Vérifie :

```text
methods
signatures
return types
descriptor
capability declaration
```

## CTL1 — Behavioral Contract

Vérifie :

```text
normal behavior
state semantics
round trip
error normalization
idempotency
```

## CTL2 — Failure Contract

Vérifie :

```text
not found
timeout
conflict
partial failure
provider unavailable
```

## CTL3 — Concurrency Contract

Vérifie :

```text
races
optimistic concurrency
unique reservations
lease ownership
terminality
```

## CTL4 — Provider Qualification Contract

Vérifie l’adapter avec son **vrai backend/provider**, en environnement contrôlé.

---

# 6. Contract Families

Les suites principales sont :

```text
Repository Contracts
Store Contracts
UnitOfWork Contract
AgentRuntimeAdapter Contract
Connector Contract
ReconciliationPort Contract
Authorization Contract
Identity/Secret Contracts
Telemetry Contract
Public API Contract
```

---

# 7. Repository Contracts

Un Repository représente l’accès à un **aggregate métier**.

Chaque Repository doit au minimum tester :

```text
save/create
get
not found
round-trip semantic fidelity
tenant scope
version behavior
transaction participation
```

---

# 8. Round-Trip Contract

Pattern :

```text
save(A)
A2 = get(A.id)

assert semantic_equivalence(A, A2)
```

Le test compare la signification métier, pas nécessairement la représentation interne.

---

# 9. Repository Not-Found Contract

Toutes les implémentations doivent suivre la même convention :

```text
None
or
canonical NotFoundError
```

Le choix est défini une fois dans le Port.

---

# 10. Optimistic Concurrency Contract

Si un aggregate possède une version :

```text
stale version
→ canonical ConcurrencyConflict
```

Toutes les implémentations doivent reproduire ce comportement.

---

# 11. Tenant Isolation Contract

Une ressource :

```text
tenant=A
```

ne doit jamais être lisible ou modifiable depuis :

```text
tenant=B
```

---

# 12. RunRepository Contract

Doit couvrir :

```text
create Run
load Run
update state
WAITING persistence
PAUSED persistence
terminal persistence
version conflict
tenant isolation
```

Invariant :

```text
WAITING != terminal
```

doit survivre au round trip.

---

# 13. EffectRepository Contract

Doit couvrir :

```text
reserve Effect
load Effect
status transitions
idempotency key lookup
fingerprint
external reference
tenant scope
```

---

# 14. Effect Idempotency Contract

```text
same idempotency key
+
same fingerprint
```

doit représenter le même logical Effect.

---

# 15. Effect Idempotency Conflict Contract

```text
same idempotency key
+
different fingerprint
```

doit produire un conflit explicite.

Jamais :

```text
silent overwrite
```

---

# 16. Effect Success Persistence Contract

Un Effect `SUCCEEDED` relu doit rester autoritatif.

Le Repository ne doit fournir aucune sémantique impliquant :

```text
"retry because caller did not receive result"
```

---

# 17. Effect UNKNOWN Contract

`UNKNOWN` doit être persisté comme état distinct de :

```text
FAILED
```

---

# 18. ApprovalRepository Contract

Doit couvrir :

```text
create
pending
approve
reject
expire
cancel
scope
version
tenant
```

---

# 19. Approval Terminality Contract

Deux décisions terminales concurrentes ne doivent pas gagner toutes les deux.

Exemple :

```text
APPROVED
vs
REJECTED
```

Une seule transition valide doit être autoritative.

---

# 20. LeaseRepository Contract

Doit couvrir :

```text
acquire
renew
release
expire
takeover
fencing token
```

---

# 21. Lease Exclusive Ownership Contract

Pour une ressource donnée :

```text
at most one authoritative active lease
```

---

# 22. Lease Fencing Contract

Après takeover :

```text
new_fencing_token > old_fencing_token
```

---

# 23. Stale Lease Contract

L’ancien owner ne peut plus :

```text
renew as current owner
```

après takeover.

---

# 24. ConversationRepository Contract

Doit couvrir :

```text
conversation creation
participants
message ordering
tenant scope
```

---

# 25. MessageRepository Contract

Doit couvrir :

```text
append
ordered read
recipient persistence
deduplication if supported
```

---

# 26. ArtifactRepository Contract

Doit couvrir :

```text
register metadata
checksum
provenance
blob reference
tenant scope
```

---

# 27. ReconciliationRepository Contract

Doit couvrir :

```text
create case
append evidence
change state
manual resolution metadata
terminal outcome
```

---

# 28. Store Contracts

Les Stores sont techniques :

```text
BlobStore
AuditStore
OutboxStore
InboxStore
```

---

# 29. BlobStore Contract

Tests :

```text
put
get
exists
stream
delete if supported
checksum fidelity
```

---

# 30. AuditStore Contract

Tests :

```text
append
read
ordering
immutability expectations
```

Un AuditEvent persisté ne doit pas être modifiable via l’API normale.

---

# 31. OutboxStore Contract

Tests :

```text
append
claim
publish marker
retry metadata
ordering where specified
```

---

# 32. Outbox Atomicity Contract

Avec UnitOfWork :

```text
domain change
+
outbox append
```

doivent être atomiques localement.

---

# 33. InboxStore Contract

Tests :

```text
deduplication
payload fingerprint
processing state
```

Même message ID avec payload différent :

```text
conflict
```

---

# 34. UnitOfWork Contract

Doit couvrir :

```text
commit
rollback
repository participation
visibility
```

Invariant :

```text
all local writes committed
or
none committed
```

---

# 35. UnitOfWork Safety Contract

Le contract ne doit jamais valider un modèle où :

```text
remote call
```

reste inclus dans une transaction DB longue.

---

# 36. AgentRuntimeAdapter Contract

Contrat cible :

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

Principe :

> **Declared capability must equal demonstrated capability.**

---

# 37. Runtime Descriptor Contract

Doit exposer :

```text
runtime name
adapter version
capabilities
```

sans imposer des types SDK au core.

---

# 38. Runtime Start Contract

`start()` doit :

```text
create/attach invocation
return opaque RuntimeHandle
normalize startup errors
```

---

# 39. Runtime Resume Contract

Si `RESUME` est déclaré :

```text
resume(handle)
```

doit réellement poursuivre l’exécution logique précédente selon les garanties documentées.

---

# 40. Unsupported Capability Contract

Si `RESUME` n’est pas supporté :

```text
resume()
→ canonical UnsupportedCapabilityError
```

Pas de pseudo-resume caché.

---

# 41. Runtime Inspect Contract

`inspect()` retourne un état normalisé exploitable par :

```text
RecoveryPlanner
```

---

# 42. Runtime Cancel Contract

`cancel()` signifie :

```text
request runtime cancellation
```

Il ne signifie jamais :

```text
rollback Effects
```

---

# 43. Runtime Events Contract

Les événements provider sont mappés vers :

```text
RuntimeEvent
```

et ne deviennent pas automatiquement :

```text
DomainEvent
AuditEvent
```

---

# 44. Runtime Checkpoint Contract

Si `NATIVE_CHECKPOINT` déclaré, l’adapter doit réellement fournir un checkpoint exploitable.

---

# 45. Runtime Error Normalization

Les exceptions SDK doivent être traduites en catégories canoniques.

---

# 46. Runtime Timeout Contract

Un timeout runtime ne doit pas automatiquement terminer le Run en `FAILED`.

---

# 47. Runtime Capability Matrix

Chaque adapter publie :

| Capability | Declared | Contract Passed | Failure Tested |
|---|---:|---:|---:|
| START |  |  |  |
| RESUME |  |  |  |
| CANCEL |  |  |  |
| STATUS |  |  |  |
| EVENT_STREAM |  |  |  |
| NATIVE_CHECKPOINT |  |  |  |
| TOOL_INTERCEPTION |  |  |  |
| SESSION_RESUME |  |  |  |

---

# 48. Native Runtime Contract

`NativeRuntimeAdapter` est la première implémentation de référence.

Mais il ne bénéficie d’aucune exception contractuelle.

---

# 49. External Runtime Contract

La même suite doit être applicable à :

```text
LangGraph
PydanticAI
OpenAI Agents
Codex
Claude Code
OpenCode
```

Les tests sont conditionnés uniquement par les capabilities déclarées.

---

# 50. Skip Rule

Un test peut être skipped si :

```text
capability explicitly unsupported
```

Jamais pour masquer une divergence de sémantique.

---

# 51. Connector Contract

Un Connector doit normaliser :

```text
operations
errors
external references
idempotency hooks
reconciliation
```

---

# 52. Connector Descriptor Contract

Expose :

```text
connector name
adapter version
capabilities
operations
```

---

# 53. Connector Read Contract

Une opération annoncée comme read-only doit ne pas produire d’Effect métier selon les garanties du provider.

---

# 54. Connector Write Contract

Une écriture réelle doit être intégrable au modèle :

```text
Effect
```

---

# 55. Connector Timeout Contract

L’adapter distingue, lorsque possible :

```text
timeout before send
timeout after possible send
```

---

# 56. Connector Ambiguity Contract

Si l’application de l’action externe est incertaine :

```text
UNKNOWN
```

Jamais :

```text
FAILED by default
```

---

# 57. Connector Native Idempotency Contract

Si provider supporte une clé idempotency native :

```text
PyAgentsKit idempotency key
→ provider idempotency primitive
```

sans abandonner son propre Effect identity.

---

# 58. Connector ExternalReference Contract

Une opération réussie fournit une référence externe lorsque possible.

---

# 59. ReconciliationPort Contract

Concept :

```text
reconcile(effect)
→ ReconciliationResult
```

Résultats :

```text
CONFIRMED_SUCCESS
CONFIRMED_FAILURE
STILL_UNKNOWN
NOT_FOUND
MANUAL_REQUIRED
```

---

# 60. Reconciliation Evidence Contract

Le résultat peut fournir :

```text
external reference
provider evidence
provider timestamp
reason
```

---

# 61. Reconciliation No-Guess Contract

Si les preuves ne suffisent pas :

```text
STILL_UNKNOWN
or
MANUAL_REQUIRED
```

Jamais un résultat inventé.

---

# 62. Reconciliation Idempotency Contract

Répéter la reconciliation :

```text
does not create a new Effect
```

---

# 63. Generic HTTP Connector Baseline

Doit couvrir :

```text
HTTP status normalization
timeouts
connection reset
idempotency headers
auth errors
```

---

# 64. GitHub Connector Contract

Doit couvrir au minimum :

```text
lookup
PR creation
merge
external references
rate limit
auth errors
reconciliation
```

---

# 65. Git Push Reconciliation Contract

Pour un push ambigu :

```text
remote ref
vs
expected SHA
```

sert de preuve principale.

---

# 66. AuthorizationPort Contract

Entrées canoniques :

```text
Principal
Tenant
Action
Resource
SecurityContext
```

Sortie canonique :

```text
AuthorizationDecision
```

---

# 67. Authorization Fail-Closed Contract

Pour opération high-risk :

```text
authorization backend unavailable
→ block
```

selon profil.

---

# 68. PolicyEvaluator Contract

Même :

```text
inputs
+
policy version
```

doit produire la même décision dans les limites définies.

---

# 69. IdentityProviderPort Contract

Mappe une identité externe vers :

```text
Principal
```

sans exposer le modèle IAM externe au Domain.

---

# 70. SecretProvider Contract

Tests :

```text
resolve SecretReference
missing reference
rotation/reload if supported
no secret value in logs
```

---

# 71. TelemetryPort Contract

Tests :

```text
metrics emission
trace emission
failure isolation
```

La panne observability ne doit pas casser le core dans le profil standard.

---

# 72. ClockPort Contract

Permet :

```text
deterministic time
```

dans les tests.

---

# 73. Public API Contract

Couvre :

```text
public imports
serialization
enum values
errors
command/query behavior
```

---

# 74. Public Import Freeze

Une suite doit comparer les symboles publics attendus.

---

# 75. Serialization Contract

Les modèles publics doivent avoir :

```text
stable field semantics
stable enum semantics
documented versioning
```

---

# 76. Error Taxonomy Contract

Les adapters ne doivent pas laisser fuiter des erreurs comme :

```text
psycopg.Error
httpx.ReadTimeout
github.SomeSdkException
```

à travers les Ports publics.

---

# 77. Test Architecture

Structure recommandée :

```text
tests/
└── contracts/
    ├── repositories/
    ├── stores/
    ├── coordination/
    ├── runtimes/
    ├── connectors/
    ├── reconciliation/
    ├── governance/
    └── public_api/
```

---

# 78. Reusable Contract Suite Pattern

Exemple :

```python
class EffectRepositoryContract:
    def make_repository(self): ...
    def test_round_trip(self): ...
    def test_idempotency(self): ...
    def test_conflict(self): ...
```

Chaque implémentation fournit uniquement :

```text
factory
setup
cleanup
```

---

# 79. Same Suite, Multiple Backends

```text
EffectRepositoryContract
├── Memory
├── SQLite
└── PostgreSQL
```

Le test commun exprime la garantie.

Les tests backend-specific viennent en complément.

---

# 80. Runtime Harness

Doit fournir :

```text
adapter factory
runtime fixture
capability set
controlled task
cleanup
```

---

# 81. LLM Non-Determinism

Les Contract Tests ne vérifient pas :

```text
exact generated prose
```

Ils vérifient :

```text
control semantics
handle behavior
events
resume
cancel
errors
```

---

# 82. Connector Harness

Doit fournir :

```text
sandbox credentials
test tenant
resource prefix
cleanup
```

---

# 83. External Resource Naming

Convention possible :

```text
pyagentskit-contract-<suite-id>-<random-id>
```

---

# 84. Contract Test Isolation

Chaque test doit être isolé :

```text
DB
filesystem
provider resource
tenant namespace
```

---

# 85. PostgreSQL Isolation

Options :

```text
temporary schema
temporary database
unique tenant scope
transaction rollback where compatible
```

---

# 86. True Concurrency

Les contracts concurrency doivent utiliser :

```text
independent connections
and/or
independent processes
```

Pas des appels séquentiels déguisés.

---

# 87. Lease Race Contract

Deux workers réels/connexions tentent acquisition concurrente.

Attendu :

```text
one authority
```

---

# 88. Approval Race Contract

Deux décisions terminales concurrentes.

Attendu :

```text
one valid terminal outcome
```

---

# 89. Effect Reservation Race

Deux workers tentent même idempotency key.

Attendu :

```text
one logical Effect
```

---

# 90. Contract vs Integration

```text
Contract Test
=
same semantics across implementations

Integration Test
=
implementation works with real dependency
```

---

# 91. Contract vs Qualification

```text
Contract Compliance
!=
Production Qualified
```

Un adapter peut être `L1 Contract Compliant` sans être `L4 Production Qualified`.

---

# 92. Consumer-Driven Contracts

Peuvent être utilisés pour certaines APIs HTTP.

Mais le modèle principal de PyAgentsKit reste :

```text
Port-owned provider contract suite
```

---

# 93. Contract Ownership

Le core possède :

```text
Port semantics
Contract Suite
Canonical errors
```

L’adapter possède :

```text
provider mapping
```

---

# 94. Adapter Cannot Redefine Semantics

Un adapter ne peut pas décider :

```text
UNKNOWN means FAILED on this provider
```

---

# 95. Capability-Based Variation

Une différence provider doit être exposée via :

```text
capability
```

ou limitation documentée.

---

# 96. Capability Negotiation Contract

Le registry doit pouvoir vérifier :

```text
required capabilities
⊆
adapter capabilities
```

avant invocation.

---

# 97. Contract Versioning

Chaque contract family possède une version.

Exemple :

```text
AgentRuntimeAdapter Contract v2
Connector Contract v2
EffectRepository Contract v2
```

---

# 98. Breaking Contract Change

Modification de sémantique existante :

```text
potential major version
```

---

# 99. Optional Capability Addition

Peut être non breaking si réellement optionnelle.

---

# 100. Compatibility Matrix

Maintenir :

| Core | Contract | Adapter | Compatible |
|---|---|---|---|
| 2.x | Runtime v2 | Adapter 1.x | yes/no |
| 2.x | Connector v2 | Adapter 1.x | yes/no |

---

# 101. Public Contract Harness

Cible :

```text
pyagentskit.testing.contracts
```

Exemple :

```python
from pyagentskit.testing.contracts import (
    AgentRuntimeAdapterContract,
    ConnectorContract,
    EffectRepositoryContract,
)
```

---

# 102. Third-Party Adapter Certification

Un adapter communautaire peut déclarer :

```text
Contract Compliant
```

si la suite officielle passe.

---

# 103. Adapter Qualification Levels

```text
L0 — Fake
L1 — Contract Compliant
L2 — Integration Tested
L3 — Failure Tested
L4 — Production Qualified
```

---

# 104. CI Strategy

## Pull Request

```text
CTL0
CTL1
fast repository contracts
```

## Main

```text
full local contract suite
PostgreSQL contracts
```

## Nightly

```text
real external adapters
concurrency
failure contracts
```

## Release

```text
CTL4 / production qualification
```

---

# 105. Pytest Markers

Recommandés :

```text
contract
integration
external
destructive
postgres
runtime
connector
concurrency
```

---

# 106. Contract Test Failure Messages

Doivent exprimer la garantie violée.

Exemple :

```text
Expected Effect.UNKNOWN after ambiguous external send; adapter returned FAILED.
```

---

# 107. Golden Tests

Utiles pour :

```text
public schemas
event envelopes
```

Pas pour :

```text
LLM natural-language output
```

---

# 108. Snapshot Tests

Acceptables pour :

```text
serialization contracts
public metadata
```

avec review explicite des updates.

---

# 109. Property-Based Contracts

Très utiles pour :

```text
round trips
fingerprints
serialization
state transitions
```

---

# 110. Model-Based Contracts

Pertinents pour :

```text
Effect
Approval
Lease
Run
```

---

# 111. Core Contract Invariants

```text
CTC-INV-01 Same Port means same semantic guarantee.
CTC-INV-02 Provider-specific errors do not leak through the Port.
CTC-INV-03 Unsupported capability is explicit.
CTC-INV-04 Contract tests observe behavior, not implementation.
CTC-INV-05 Safety tests are not skipped for convenience.
CTC-INV-06 Concurrency contracts use real concurrency.
CTC-INV-07 Ambiguous outcomes remain ambiguous.
CTC-INV-08 Hidden retries cannot violate Effect semantics.
CTC-INV-09 Contract compliance != production qualification.
CTC-INV-10 Every official adapter publishes qualification level.
```

---

# 112. Repository Contract Checklist

```text
[ ] create/save
[ ] get
[ ] not found
[ ] round trip
[ ] tenant isolation
[ ] version conflict
[ ] transaction behavior
```

---

# 113. Effect Repository Checklist

```text
[ ] reserve
[ ] same key / same fingerprint
[ ] same key / different fingerprint
[ ] concurrent reservation
[ ] status persistence
[ ] SUCCEEDED durable
[ ] UNKNOWN durable
[ ] external reference
```

---

# 114. Lease Checklist

```text
[ ] acquire
[ ] conflict
[ ] renew
[ ] expire
[ ] release
[ ] takeover
[ ] fencing monotonicity
[ ] stale owner rejected
```

---

# 115. Runtime Adapter Checklist

```text
[ ] descriptor
[ ] capability declaration
[ ] start
[ ] inspect
[ ] events
[ ] resume if declared
[ ] cancel if declared
[ ] checkpoint if declared
[ ] close
[ ] canonical errors
```

---

# 116. Connector Checklist

```text
[ ] descriptor
[ ] read
[ ] write
[ ] auth errors
[ ] timeout behavior
[ ] rate limit
[ ] idempotency
[ ] external reference
[ ] reconciliation
[ ] ambiguity
```

---

# 117. Governance Checklist

```text
[ ] Principal mapping
[ ] tenant scope
[ ] ALLOW/DENY semantics
[ ] backend unavailable
[ ] policy version
[ ] audit evidence
```

---

# 118. Public API Checklist

```text
[ ] import freeze
[ ] schema
[ ] enum values
[ ] errors
[ ] compatibility
[ ] no internal leakage
```

---

# 119. Contract Failure Severity

```text
CT-P0 — Safety semantic violation
CT-P1 — Core behavioral mismatch
CT-P2 — Compatibility issue
CT-P3 — Metadata/documentation issue
```

---

# 120. CT-P0 Examples

```text
UNKNOWN returned as FAILED
stale fencing accepted
idempotency conflict ignored
cross-tenant entity exposed
Approval terminality broken
```

Un `CT-P0` bloque le statut Contract Compliant.

---

# 121. Regression Rule

Lorsqu’un bug révèle une garantie générale manquante :

```text
bug
→ new common Contract Test
→ all adapters rerun
```

---

# 122. Traceability

Chaque Contract Test critique doit référencer :

```text
specification
invariant
ADR
release gate
```

Exemple :

```text
CT-EFFECT-UNKNOWN-001
→ doc 13
→ GATE-04
```

---

# 123. Test ID Convention

```text
CT-REP-RUN-001
CT-REP-EFFECT-001
CT-REP-APPROVAL-001
CT-LEASE-001
CT-RUNTIME-001
CT-CONN-001
CT-RECON-001
CT-AUTHZ-001
CT-API-001
```

---

# 124. Contract Registry

| Contract | Owner Context | Implementations |
|---|---|---|
| RunRepository | Execution | Memory, SQLite, PostgreSQL |
| EffectRepository | Effects | Memory, SQLite, PostgreSQL |
| ApprovalRepository | Governance | Memory, SQLite, PostgreSQL |
| LeaseRepository | Coordination | Memory, SQLite, PostgreSQL |
| AgentRuntimeAdapter | Runtime Integration | Native + externals |
| Connector | Connectors | HTTP, GitHub, others |
| ReconciliationPort | Effects/Connectors | provider-specific |

---

# 125. Contract Metadata

Chaque suite publie :

```text
contract name
contract version
required guarantees
optional capabilities
owner
```

---

# 126. Provider SDK Upgrade Rule

Après upgrade d’un SDK runtime/connector :

```text
rerun
CTL0
CTL1
integration
failure tests
```

---

# 127. Hidden Retry Detection

Tester ou documenter :

```text
automatic SDK retries
```

car ils peuvent modifier les garanties d’Effect.

---

# 128. Timeout Configuration Contract

Les adapters critiques doivent offrir un timeout borné/configurable lorsque le provider le permet.

---

# 129. Cancellation Contract

Cancellation locale n’implique jamais :

```text
external rollback
```

---

# 130. Retry Contract

Un retry est autorisé uniquement lorsque :

```text
safe to retry
```

est démontré par le modèle.

---

# 131. Contract Test Observability

Les tests externes doivent tracer :

```text
test id
adapter
operation
external resource id
```

sans secret.

---

# 132. Flaky Contract Tests

Un test contractuel safety-critical flaky est considéré comme :

```text
test problem or implementation problem
```

jamais comme bruit acceptable.

---

# 133. Contract Coverage Matrix

| Port | Memory/Fake | SQLite | PostgreSQL | External |
|---|---:|---:|---:|---:|
| RunRepository | ✓ | ✓ | ✓ | n/a |
| EffectRepository | ✓ | ✓ | ✓ | n/a |
| ApprovalRepository | ✓ | ✓ | ✓ | n/a |
| LeaseRepository | ✓ | ✓ | ✓ | n/a |
| BlobStore | ✓ | Filesystem | n/a | S3/Azure |
| AgentRuntimeAdapter | Fake/Native | n/a | n/a | runtimes |
| Connector | Fake | n/a | n/a | GitHub/HTTP |
| ReconciliationPort | Fake | n/a | n/a | provider-specific |

---

# 134. Minimal Official Adapter Bar

Pour être official :

```text
CTL0 PASS
CTL1 PASS
documentation complete
known limitations explicit
```

---

# 135. Stable Adapter Bar

```text
CTL0
CTL1
CTL2
CTL3
```

---

# 136. Production Qualified Adapter Bar

```text
CTL0–CTL4
+
production-like qualification
```

---

# 137. Contract Freeze

Avant `2.0.0rc1` :

```text
freeze all P0 Port semantics
```

---

# 138. V1 Compatibility Contract

La couche `compat.v1` possède ses propres tests.

Mais :

```text
V1 compatibility
must never redefine
V2 contracts
```

---

# 139. Anti-Patterns

Interdits :

```text
mock everything
interface-only compliance
provider-specific assertions in common suite
skip failing safety test
sequential fake concurrency
production credentials
adapter-specific public errors
capability lies
exact LLM prose assertions
```

---

# 140. Review Checklist

Avant merge d’un nouveau Contract Test :

```text
[ ] observable behavior?
[ ] provider-neutral?
[ ] maps to invariant?
[ ] reproducible?
[ ] error canonical?
[ ] concurrency real if required?
[ ] cleanup reliable?
[ ] no secrets?
[ ] failure message understandable?
```

---

# 141. Bounded Context Ownership

```text
Execution
→ RunRepository

Effects
→ EffectRepository
→ ReconciliationPort

Governance
→ ApprovalRepository
→ AuthorizationPort

Coordination
→ LeaseRepository

Runtime Integration
→ AgentRuntimeAdapter

Connectors
→ Connector
```

---

# 142. Adapter Compliance Report

Exemple :

```text
Adapter: GitHubConnector
Contract: Connector v2
CTL0: PASS
CTL1: PASS
CTL2: PASS
CTL3: PASS
CTL4: NOT YET QUALIFIED
Known limitations:
- ...
```

---

# 143. Contract Testing and Build-vs-Buy

Les Contract Tests rendent réellement possible la doctrine :

```text
Build semantics.
Integrate infrastructure.
```

Ils garantissent que la sémantique reste dans PyAgentsKit même lorsque l’implémentation change.

---

# 144. Contract Testing and Hexagonal Architecture

Sans Contract Tests :

```text
Port
=
Python interface
```

Avec Contract Tests :

```text
Port
=
behavioral boundary
```

---

# 145. Contract Testing and Runtime Neutrality

La neutralité runtime est démontrée seulement lorsque plusieurs runtimes hétérogènes passent la même suite.

---

# 146. Contract Testing and Production Qualification

Les résultats alimentent directement :

```text
GATE-03 Runtime Adapters
GATE-06 Coordination
GATE-07 Persistence
GATE-08 Governance
```

du plan de qualification production.

---

# 147. Roadmap

## Phase 1

```text
RunRepository
EffectRepository
ApprovalRepository
LeaseRepository
UnitOfWork
```

## Phase 2

```text
AgentRuntimeAdapter
NativeRuntimeAdapter
```

## Phase 3

```text
Connector
ReconciliationPort
```

## Phase 4

```text
public testing package
third-party adapter certification
```

---

# 148. P0 Contract Suites

Avant V2 stable :

```text
RunRepository
EffectRepository
ApprovalRepository
LeaseRepository
UnitOfWork
AgentRuntimeAdapter
Connector
ReconciliationPort
```

---

# 149. P1 Contract Suites

```text
ConversationRepository
MessageRepository
ArtifactRepository
BlobStore
AuditStore
OutboxStore
InboxStore
AuthorizationPort
SecretProvider
```

---

# 150. P2 Contract Suites

```text
TelemetryPort
IdentityProviderPort
optional plugins
```

---

# 151. Definition of Ready

Une suite contractuelle est prête si :

```text
Port stable enough
observable behavior specified
canonical errors defined
fixture strategy defined
```

---

# 152. Definition of Done — Contract Suite

Une suite est complète si :

1. comportement nominal couvert ;
2. erreurs canoniques couvertes ;
3. idempotency couverte si applicable ;
4. tenant isolation couverte si applicable ;
5. concurrency couverte si applicable ;
6. capability handling couvert ;
7. utilisée sur plusieurs implémentations lorsque possible ;
8. intégrée en CI ;
9. failure messages sont explicites ;
10. documentation et version existent.

---

# 153. Acceptance Criteria

La stratégie est conforme si :

1. chaque Port critique possède une suite comportementale ;
2. les suites communes sont provider-neutral ;
3. Memory/SQLite/PostgreSQL partagent les mêmes repository contracts ;
4. Runtime Adapters partagent un harness commun ;
5. Connectors partagent un harness commun ;
6. unsupported capability est explicite ;
7. erreurs provider sont normalisées ;
8. vraie concurrence est utilisée pour les races ;
9. `UNKNOWN` reste `UNKNOWN` à travers tous les adapters ;
10. le harness peut être utilisé par des plugins tiers ;
11. les niveaux L0–L4 dépendent de preuves ;
12. tout bug généralisable ajoute un test commun ;
13. les suites sont versionnées ;
14. les contract changes suivent SemVer ;
15. Contract Compliance reste distinct de Production Qualification.

---

# 154. Definition of Done — Document

`../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md` est mature lorsque :

1. `tests/contracts/` existe ;
2. les repository contracts sont exécutables ;
3. Effect/Approval/Lease contracts sont exécutables ;
4. UnitOfWork contract est exécutable ;
5. AgentRuntimeAdapter contract est exécutable ;
6. NativeRuntimeAdapter passe la suite ;
7. au moins un runtime externe passe la même suite ;
8. Connector contract est exécutable ;
9. au moins un connector réel passe la suite ;
10. ReconciliationPort contract est exécutable ;
11. les concurrency contracts utilisent plusieurs connexions/processus ;
12. le harness public est importable ;
13. CI distingue fast/external contracts ;
14. des compliance reports sont générables ;
15. les niveaux de qualification sont publiés ;
16. les tests critiques sont traçables vers leurs invariants ;
17. le contract freeze est atteint avant RC ;
18. les adapters tiers peuvent réutiliser le harness ;
19. aucun adapter officiel ne contourne un safety contract en échec ;
20. le plan de qualification production consomme les résultats.

---

# 155. Résumé

Le modèle cible est :

```text
                 PYAGENTSKIT PORT
                       │
                       ▼
                 CONTRACT SUITE
                       │
          ┌────────────┼────────────┐
          ▼            ▼            ▼
      Adapter A     Adapter B    Adapter C
      Memory        PostgreSQL   External
          │            │            │
          └────────────┼────────────┘
                       ▼
             SAME SEMANTIC GUARANTEE
```

Pour les runtimes :

```text
AgentRuntimeAdapter Contract
        │
        ├── NativeRuntimeAdapter
        ├── LangGraphAdapter
        ├── PydanticAIAdapter
        ├── OpenAIAgentsAdapter
        └── CodingRuntimeAdapter
```

Pour les connectors :

```text
Connector Contract
        │
        ├── GenericHTTP
        ├── GitHub
        ├── GitLab
        └── Business Systems
```

La règle fondamentale est :

> **Dans PyAgentsKit, l’interchangeabilité ne doit jamais être une promesse fondée uniquement sur le typage : deux adapters ne sont réellement interchangeables que lorsqu’ils ont démontré, par la même suite contractuelle, qu’ils produisent les mêmes décisions, les mêmes erreurs et les mêmes garanties face aux mêmes situations.**
