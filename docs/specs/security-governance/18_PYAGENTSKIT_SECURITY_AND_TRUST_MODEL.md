# PyAgentsKit — Security & Trust Model

**Document :** `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Spécification métier et technique — Security & Trust  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../foundation/00_PYAGENTSKIT_DEFINITION_DU_BESOIN.md`
- `../foundation/01_PYAGENTSKIT_ANALYSE_DU_BESOIN.md`
- `../foundation/03_PYAGENTSKIT_EXIGENCES_FONCTIONNELLES.md`
- `../foundation/04_PYAGENTSKIT_EXIGENCES_NON_FONCTIONNELLES.md`
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/12_PYAGENTSKIT_AGENT_RUNTIME_ADAPTER_SPECIFICATION.md`
- `../runtime/13_PYAGENTSKIT_EFFECTS_AND_SIDE_EFFECT_SAFETY.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`

---

# 1. Objet

Ce document définit le **Security & Trust Model** de PyAgentsKit.

Il formalise :

- les frontières de confiance ;
- les identités et principals ;
- l’authentification ;
- l’autorisation ;
- les permissions d’outils ;
- la gestion des secrets ;
- l’isolation des runtimes ;
- l’isolation des coding agents ;
- le multi-tenancy ;
- les contrôles sur les Protected Effects ;
- la sécurité des workers ;
- la sécurité des stores ;
- l’audit ;
- les comportements fail-closed ;
- les mécanismes de break-glass ;
- les profils de sécurité.

Le principe directeur est :

> **Un agent peut proposer une action ; il ne doit jamais acquérir implicitement le droit de l’exécuter.**

---

# 2. Objectifs de sécurité

Le modèle doit fournir :

```text
explicit trust boundaries
least privilege
deny by default
strong identity
explicit authorization
secret minimization
runtime isolation
tenant isolation
effect control
auditable decisions
secure recovery
```

---

# 3. Non-objectifs

PyAgentsKit ne devient pas :

```text
Identity Provider
IAM complet
Secrets Manager
SIEM
EDR
WAF
service mesh
container runtime
sandbox vendor
PKI platform
```

Il s’intègre à ces composants lorsqu’ils existent.

---

# 4. Principes fondamentaux

```text
SEC-PR-01 Least Privilege
SEC-PR-02 Deny by Default
SEC-PR-03 Explicit Trust Boundaries
SEC-PR-04 Defense in Depth
SEC-PR-05 No Implicit Authority
SEC-PR-06 Secrets Externalized
SEC-PR-07 Durable Audit
SEC-PR-08 Fail Closed for Critical Effects
SEC-PR-09 Tenant Isolation
SEC-PR-10 Runtime Isolation
SEC-PR-11 Approval Is Not Authentication
SEC-PR-12 Lease Is Not Authorization
SEC-PR-13 Runtime Output Is Untrusted
SEC-PR-14 Adapter Is Not Automatically Trusted
SEC-PR-15 Security Controls Survive Recovery
```

---

# 5. Trust Domains

Les domaines de confiance principaux sont :

```text
Human Trust Domain
Application Trust Domain
PyAgentsKit Core Trust Domain
Runtime Trust Domain
Worker Trust Domain
Persistence Trust Domain
External Systems Trust Domain
Observability Trust Domain
Administration Trust Domain
```

---

# 6. Frontières de confiance

Les frontières critiques sont :

```text
Human → API
External Event → API
API → PyAgentsKit Core
Core → RuntimeAdapter
RuntimeAdapter → Runtime
Runtime → ToolGateway
ToolGateway → External System
Worker → LeaseStore
Core → State Stores
Core → BlobStore
Admin → Control Plane
Plugin → Worker Process
```

---

# 7. Vue de confiance

```text
Untrusted / Semi-trusted Inputs
             │
             ▼
       Validation Layer
             │
             ▼
      Identity / Tenant
             │
             ▼
        Authorization
             │
             ▼
           Policy
             │
             ▼
         Approval
             │
             ▼
     Ownership / Fencing
             │
             ▼
       Tool / Effect Gate
             │
             ▼
       Secret Resolution
             │
             ▼
       External Systems
             │
             ▼
      Audit / Telemetry
```

---

# 8. Hypothèses de confiance

PyAgentsKit doit partir des hypothèses suivantes :

```text
LLM output may be wrong or maliciously influenced
runtime events may be malformed or replayed
external content is untrusted
webhooks are untrusted until verified
worker-local cache is not authoritative
human identity must be externally authenticated
plugins/adapters are code with process-level privileges
stores are high-value assets
```

---

# 9. Principal

Un `Principal` représente un sujet de sécurité.

Types candidats :

```text
HUMAN
SERVICE
AGENT
WORKER
SYSTEM
```

---

# 10. Actor vs Principal

```text
Actor
= identité métier / conversationnelle

Principal
= identité de sécurité utilisée pour AuthN/AuthZ
```

Un `Actor` peut référencer un `Principal`.

---

# 11. Authentication

L’authentification répond à :

```text
Who are you?
```

Elle doit être déléguée à un système externe.

Exemples :

```text
OIDC
OAuth2
mTLS
API key verification
workload identity
cloud IAM
```

---

# 12. IdentityProviderPort

Contrat conceptuel :

```python
class IdentityProviderPort(Protocol):
    async def authenticate(...) -> Principal:
        ...
```

---

# 13. External Identity Reference

Exemples :

```text
entra://user/abc
keycloak://subject/123
github://user/456
service://worker/42
```

---

# 14. Authorization

L’autorisation répond à :

```text
May this Principal perform this action on this resource?
```

Décision minimale :

```text
ALLOW
DENY
```

---

# 15. AuthorizationPort

```python
class AuthorizationPort(Protocol):
    async def authorize(
        self,
        principal,
        action,
        resource,
        context,
    ) -> AuthorizationDecision:
        ...
```

---

# 16. Deny by Default

Pour toute action sensible :

```text
no explicit ALLOW
→ DENY
```

---

# 17. Permissions

Convention :

```text
resource.action
```

Exemples :

```text
run.create
run.start
run.pause
run.cancel
run.inspect

effect.execute
effect.reconcile
effect.resolve_manually

approval.request
approval.decide

lease.inspect
lease.force_takeover

artifact.read
artifact.write
artifact.delete

audit.read

admin.migrate
admin.repair
```

---

# 18. RBAC

Rôles candidats :

```text
VIEWER
OPERATOR
APPROVER
DEVELOPER
RELEASE_MANAGER
SECURITY_ADMIN
PLATFORM_ADMIN
AUDITOR
```

---

# 19. ABAC

Attributs possibles :

```text
tenant
environment
risk_level
effect_kind
resource_owner
amount
time_window
actor_type
```

---

# 20. RBAC + ABAC

Le modèle cible peut combiner :

```text
role grants
+
contextual constraints
```

---

# 21. Distinctions de sécurité essentielles

```text
AUTHENTICATION
≠
AUTHORIZATION
≠
APPROVAL

LEASE
≠
AUTHORIZATION

FENCING TOKEN
≠
CREDENTIAL

MESSAGE
≠
AUTHORIZED COMMAND

RUNTIME OUTPUT
≠
AUTHORITY
```

---

# 22. Approval n’est pas Authorization

```text
Authorization:
cet acteur a-t-il le droit de décider ?

Approval:
quelle décision a-t-il effectivement prise ?
```

---

# 23. Lease n’est pas Authorization

Un worker avec lease possède :

```text
execution authority
```

mais pas automatiquement :

```text
business permission
```

---

# 24. Fencing n’est pas Authentication

Le `FencingToken` représente :

```text
ownership generation
```

pas :

```text
human or service identity
```

---

# 25. Tool Security Model

Chaque tool/action peut déclarer :

```text
required_permission
risk_level
approval_policy
allowed_principals
environment_constraints
tenant_constraints
```

---

# 26. Tool Categories

```text
READ
COMPUTE
WRITE
SENSITIVE_WRITE
CRITICAL_EFFECT
```

---

# 27. ToolGateway

Le `ToolGateway` constitue une frontière de sécurité centrale.

```text
Runtime
↓
Tool Request
↓
Schema Validation
↓
Tenant Validation
↓
Authorization
↓
Risk Classification
↓
Policy
↓
Approval
↓
Ownership/Fencing
↓
Secret Resolution
↓
Execution
↓
Audit
```

---

# 28. SecurityContext

Structure conceptuelle :

```text
principal
tenant_id?
permissions
authorization_context
correlation_context
ownership_context?
approval_reference?
```

---

# 29. ProtectedEffectContext

Pour une action sensible :

```text
principal
tenant_id
effect_id
approval_reference?
ownership_context
fencing_token
correlation_context
```

---

# 30. Runtime Trust

Tout output runtime est :

```text
untrusted data
```

et non :

```text
authority
```

---

# 31. Runtime cannot self-authorize

Un runtime ne peut pas produire :

```text
approved=true
role=admin
tenant_id=other
permission=deploy
```

et modifier ainsi son `SecurityContext`.

---

# 32. Adapter Trust

Un adapter est du code exécuté dans le worker.

Il doit être :

```text
explicitly registered
allowlisted
version-pinned
observable
reviewed
```

---

# 33. Dynamic Plugin Loading

Le chargement dynamique arbitraire devrait être :

```text
disabled by default
```

en production.

---

# 34. Supply Chain Security

Contrôles recommandés :

```text
pinned versions
lockfiles
hash verification
dependency scanning
minimal transitive dependencies
trusted registries
SBOM
signed artifacts when available
```

---

# 35. Secrets

Secrets concernés :

```text
API tokens
database passwords
private keys
OAuth client secrets
cloud credentials
registry tokens
```

---

# 36. SecretProviderPort

```python
class SecretProviderPort(Protocol):
    async def resolve(
        self,
        reference: SecretReference,
    ) -> SecretValue:
        ...
```

---

# 37. SecretReference

Exemples :

```text
vault://prod/github/token
azurekv://pyagentskit/db-password
awssecrets://runtime/provider-key
```

---

# 38. Secret Handling

Les secrets ne doivent pas être persistés par défaut dans :

```text
Run.metadata
Message.content
MemoryEntry
Effect.metadata
AuditEvent.payload
logs
traces
```

---

# 39. Secret Resolution

Principe :

```text
resolve late
use briefly
do not persist
do not expose to runtime unless required
```

---

# 40. Secret Rotation

Les objets métier doivent stocker :

```text
SecretReference
```

et non :

```text
resolved secret value
```

afin de permettre la rotation transparente.

---

# 41. Workload Identity

À préférer lorsque disponible :

```text
managed identity
IAM role
OIDC workload identity
mTLS workload certificate
```

---

# 42. Credential Brokering

Modèle recommandé :

```text
Runtime requests tool
↓
ToolGateway
↓
SecretProvider resolves scoped credential
↓
Tool executes
```

Le runtime ne voit pas nécessairement le secret.

---

# 43. No Secret in Prompt

Principe fort :

> **Une valeur de secret ne doit pas être insérée dans le contexte LLM sauf nécessité exceptionnelle explicitement justifiée.**

---

# 44. Worker Security

Un worker doit fonctionner avec le minimum de :

```text
OS privileges
filesystem access
network access
cloud permissions
tool permissions
```

---

# 45. Worker Credential Scope

Un worker ne devrait pas avoir accès à des credentials correspondant à des tools qu’il n’exécute jamais.

---

# 46. Worker Pools

Pools possibles :

```text
low-risk
coding-agent
production-effects
high-trust-admin
```

---

# 47. Privilege Separation

Éviter :

```text
one universal worker with every adapter and every credential
```

Préférer :

```text
specialized trust zones
```

---

# 48. Runtime Isolation

Niveaux candidats :

```text
NONE
PROCESS
CONTAINER
MICROVM
REMOTE_SANDBOX
```

---

# 49. Sandbox Controls

Un sandbox peut contrôler :

```text
filesystem
process execution
network
environment variables
devices
CPU
memory
disk
wall-clock
```

---

# 50. Coding-Agent Security

Les coding agents sont particulièrement sensibles car ils peuvent :

```text
read source code
modify files
execute shell commands
access Git
trigger CI/CD
publish packages
deploy infrastructure
```

---

# 51. Coding Workspace Isolation

Recommandations :

```text
dedicated workspace
ephemeral clone/worktree
restricted mounts
no host home directory
no Docker socket
no unrestricted SSH agent forwarding
```

---

# 52. Shell Security

La classification d’une commande dépend de :

```text
executable
arguments
working directory
environment
network target
identity
```

---

# 53. Git Security

Recommandations :

```text
read repo
write workspace
PR-based mutation
protected branches
expected SHA
scoped tokens
required CI
```

---

# 54. Package Publishing Security

Pour publier :

```text
package namespace restriction
artifact checksum
scoped registry token
approval
```

---

# 55. Deployment Security

Séparer autant que possible :

```text
build identity
deploy identity
production admin identity
```

---

# 56. Infrastructure Security

Pour IaC :

```text
plan permissions
apply permissions
state access
```

doivent être minimisés et séparés si possible.

---

# 57. Network Policy

Les workers doivent disposer du minimum d’egress nécessaire.

Cibles typiques :

```text
LLM provider
PostgreSQL
Object Storage
approved APIs
Git provider
CI/CD
```

---

# 58. Arbitrary Network Access

Un coding agent avec accès réseau global représente une forte surface de risque.

Ce mode doit être :

```text
explicitly configured
```

---

# 59. Dynamic URL Tools

Les tools acceptant une URL doivent pouvoir appliquer :

```text
scheme allowlist
host allowlist
DNS/IP validation
private-network restrictions
redirect policy
```

---

# 60. Filesystem Boundary

Avant accès fichier :

```text
normalize path
↓
resolve symlinks
↓
verify allowed root
↓
access
```

---

# 61. Artifact Security

Les artifacts peuvent contenir :

```text
source code
logs
PII
reports
generated files
secrets by mistake
```

Ils nécessitent :

```text
access control
checksum
retention
private storage
encryption at rest
```

---

# 62. Message Security

Un `Message` est une donnée potentiellement hostile.

Il peut contenir :

```text
prompt injection
malicious links
secrets
PII
pseudo-commands
```

---

# 63. Message Is Not Authority

```text
Message
≠
ApprovalDecision
≠
Authorization
≠
Policy
```

---

# 64. Conversation Isolation

Une Conversation doit être liée à :

```text
tenant
session
participants
```

et contrôlée par autorisation.

---

# 65. Memory Security

`MemoryEntry` peut contenir des informations sensibles ou manipulées.

Contrôles :

```text
scope
provenance
retention
authorization
redaction
```

---

# 66. Global Memory

Une mémoire globale cross-tenant doit être :

```text
disabled by default
```

ou fortement partitionnée.

---

# 67. Multi-tenancy

Objets typiquement tenant-bound :

```text
Run
Session
Conversation
Message
Effect
Approval
Artifact
MemoryEntry
```

---

# 68. Tenant Isolation Invariants

```text
tenant A cannot read tenant B
tenant A cannot approve tenant B Effect
tenant A cannot reuse tenant B idempotency namespace
tenant A cannot acquire tenant B resource without authorization
```

---

# 69. Tenant Propagation

Le tenant autoritatif doit provenir d’un contexte authentifié.

Il est propagé dans :

```text
SecurityContext
stores
EffectContext
Artifact access
Audit
Correlation
```

---

# 70. Persistence Isolation

Options possibles :

```text
shared schema + tenant_id
Row Level Security
schema per tenant
database per tenant
```

---

# 71. RLS

PostgreSQL RLS peut renforcer :

```text
tenant isolation
```

mais ne remplace jamais l’autorisation applicative.

---

# 72. Protected Effect Security

Avant un Protected Effect :

```text
resolve Principal
validate tenant
authorize
evaluate policy
validate approval
validate ownership
validate fencing
validate idempotency
resolve scoped secret
execute
audit
```

---

# 73. Fail Closed

Pour un Effect critique :

```text
security state UNKNOWN
→ BLOCK
```

---

# 74. Fail Open

Autorisé uniquement si :

```text
operation is non-critical
behavior explicitly configured
risk accepted
```

---

# 75. Data Classification

Niveaux candidats :

```text
PUBLIC
INTERNAL
CONFIDENTIAL
RESTRICTED
```

---

# 76. Classification Propagation

Une sortie dérivée de données sensibles peut hériter de leur classification.

---

# 77. Telemetry Minimization

Éviter d’exporter par défaut :

```text
full prompts
message bodies
raw tool payloads
secrets
sensitive artifacts
```

---

# 78. Audit Security

L’AuditStore doit protéger :

```text
integrity
access
retention
ordering
```

---

# 79. Audit Roles

Un rôle :

```text
AUDITOR
```

peut disposer d’un accès en lecture sans droits opérationnels.

---

# 80. Audit Immutability

Le modèle est :

```text
append-oriented
```

et peut être renforcé physiquement par permissions DB ou stockage externe.

---

# 81. Security Events

Événements candidats :

```text
AuthenticationFailed
AuthorizationDenied
SecretResolutionFailed
FencingRejected
TenantIsolationViolation
ApprovalAuthorizationDenied
AdapterNotAllowed
ToolBlockedByPolicy
SandboxViolation
BreakGlassUsed
```

---

# 82. Security Metrics

```text
authn_failures_total
authz_denials_total
tool_policy_denials_total
fencing_rejections_total
sandbox_violations_total
secret_resolution_failures_total
break_glass_total
```

---

# 83. Secure Defaults

En production :

```text
deny sensitive actions
no unrestricted shell
no unrestricted network
no dynamic plugins
no global memory
no secret persistence
no direct production writes
```

---

# 84. Security Profiles

Concept candidat :

```text
DEVELOPMENT
STANDARD
HIGH_ASSURANCE
CUSTOM
```

---

# 85. Development Profile

Peut assouplir certaines protections, mais doit afficher clairement :

```text
NOT PRODUCTION SAFE
```

---

# 86. Standard Profile

Peut imposer :

```text
AuthZ
externalized secrets
audit
tool classification
approval support
lease/fencing
tenant isolation
```

---

# 87. High-Assurance Profile

Peut imposer :

```text
mTLS
remote sandbox / microVM
strict egress
multi-approval
separate worker pools
RLS
immutable audit
short-lived credentials
```

---

# 88. Break-glass

Un mécanisme d’urgence peut exister.

Il doit exiger :

```text
strong permission
explicit reason
short TTL
limited scope
full audit
alerting
```

---

# 89. Break-glass Is Not Global Bypass

Il doit relâcher :

```text
one explicit control
```

pas désactiver toute la sécurité.

---

# 90. Administrative Security

Actions sensibles :

```text
force takeover
manual effect resolution
state repair
migration
audit export
policy modification
tenant deletion
kill switch
```

---

# 91. Admin Controls

Ces actions exigent :

```text
strong AuthN
strong AuthZ
explicit audit
```

---

# 92. Control Plane

```text
admin API
policy configuration
adapter registry
tenant configuration
security configuration
```

---

# 93. Data Plane

```text
workers
runtime invocations
tool calls
effects
messages
```

---

# 94. Control Plane vs Data Plane

La séparation peut être logique au départ, puis physique pour les environnements à assurance renforcée.

---

# 95. Database Security

Le worker applicatif ne doit pas disposer de privilèges tels que :

```text
SUPERUSER
CREATE ROLE
DROP DATABASE
```

---

# 96. Migration Identity

Les migrations peuvent utiliser une identité distincte de l’identité runtime.

---

# 97. Audit DB Identity

Option de renforcement :

```text
write-only audit role
```

pour l’application.

---

# 98. Blob Storage Security

Séparer si possible :

```text
artifact.read
artifact.write
artifact.delete
```

---

# 99. Delete Protection

Artifacts ou audits critiques peuvent bénéficier de :

```text
versioning
retention lock
MFA delete
```

selon backend.

---

# 100. Secure Serialization

Éviter :

```text
pickle from untrusted storage
```

Préférer :

```text
JSON-compatible
typed schema
validated payload
```

---

# 101. Dynamic Code Execution

Le core ne doit pas utiliser normalement :

```text
eval()
exec()
```

sur du contenu non fiable.

---

# 102. Webhook Security

Contrôles :

```text
signature validation
timestamp validation
replay protection
source identification
Inbox deduplication
```

---

# 103. API Security

Contrôles :

```text
TLS
AuthN
AuthZ
rate limiting
request-size limits
schema validation
```

---

# 104. Abuse Prevention

Limiter :

```text
run explosion
tool-call loops
artifact growth
message spam
reconciliation storms
approval flooding
```

---

# 105. Quotas

Quotas candidats :

```text
runs per tenant
concurrent runs
effects per run
artifact bytes
messages per conversation
approvals per interval
```

---

# 106. Resource Limits

Workers/runtimes peuvent appliquer :

```text
CPU
memory
disk
process count
wall-clock
network
```

---

# 107. Security on Recovery

Après reprise :

```text
revalidate tenant
revalidate authorization
revalidate approval
revalidate ownership
revalidate policy
re-resolve secrets
```

---

# 108. No Persisted Transient Credential

Le recovery doit utiliser :

```text
SecretReference
```

pas les anciennes valeurs résolues.

---

# 109. Takeover Security

Un nouveau worker doit obtenir :

```text
fresh OwnershipContext
fresh secret resolution
current policy
current authorization context
```

---

# 110. Security Context Freshness

Le contexte peut devenir obsolète après :

```text
role revocation
tenant suspension
approval expiration
secret rotation
policy change
```

---

# 111. Revalidation Points

Recommandés :

```text
before Protected Effect
after long WAITING
after takeover
after recovery
before admin action
```

---

# 112. Policy Trust

Les policies sont de la configuration/code de haute confiance.

Elles doivent être :

```text
versioned
reviewed
audited
rollbackable
```

---

# 113. Policy Version

Pour audit :

```text
policy_id
policy_version
```

doivent pouvoir être reliés à une décision.

---

# 114. Policy Tampering

Toute modification de policy sensible doit produire :

```text
AuditEvent
```

---

# 115. Model Provider Trust

Un provider LLM est un système externe.

Les données envoyées doivent respecter :

```text
data classification
provider allowlist
model allowlist
privacy policy
regional constraints
```

---

# 116. ModelPolicy

Concept candidat :

```text
allowed_providers
allowed_models
maximum_data_classification
allowed_regions
```

---

# 117. Connector Trust

Chaque connector/tool provider doit documenter :

```text
authentication
required scopes
data sent
data received
side effects
idempotency
reconciliation
security limitations
```

---

# 118. Connector Allowlist

En production :

```text
registered connectors only
```

---

# 119. Unknown Tool

Politique par défaut :

```text
unknown tool
→ DENY
```

---

# 120. Tool Schema Validation

Les arguments doivent être validés.

Exemples :

```text
amount > 0
environment in allowlist
repository allowed
path under workspace
URL host approved
```

---

# 121. Defense in Depth

PyAgentsKit complète les contrôles natifs :

```text
Git protected branches
Terraform state lock
cloud IAM
database constraints
registry immutability
CI reviews
```

---

# 122. Security Posture Visibility

L’opérateur doit pouvoir voir :

```text
runtime isolation level
adapter control level
effect safety profile
fencing grade
AuthZ enabled?
Audit enabled?
SecretProvider available?
```

---

# 123. Security Status Command

Candidate :

```text
pyagentskit security status
```

---

# 124. Security Drift

Les baisses de garantie doivent être visibles :

```text
audit disabled
sandbox removed
allowlist widened
policy weakened
secret provider bypassed
```

---

# 125. Secure Startup

Vérifier selon profil :

```text
schema compatibility
SecretProvider
AuthorizationProvider
critical policies
AuditStore
LeaseStore
```

---

# 126. Security Readiness

Un worker peut être :

```text
alive
```

mais :

```text
not security-ready
```

---

# 127. Incident Containment

Actions possibles :

```text
disable tenant
disable tool
disable runtime adapter
drain worker pool
revoke secret
block Effect kind
freeze Protected Effects
```

---

# 128. SecurityKillSwitch

Concept candidat :

```text
SecurityKillSwitch
```

Scopes possibles :

```text
all Protected Effects
tool
effect kind
tenant
runtime adapter
worker pool
```

---

# 129. Kill Switch Properties

Doit être :

```text
explicit
audited
fast
reversible
scoped
```

---

# 130. Effect Freeze

```text
protected_effects_enabled = false
```

peut placer les Runs concernés en :

```text
WAITING
```

sans forcément les terminer.

---

# 131. Security Invariants

```text
SEC-INV-01
No sensitive action without an authorized Principal.

SEC-INV-02
Approval never replaces Authorization.

SEC-INV-03
Lease never replaces Authorization.

SEC-INV-04
Runtime cannot increase its own permissions.

SEC-INV-05
Secrets are not persisted in domain objects by default.

SEC-INV-06
Tenant isolation applies to critical state.

SEC-INV-07
Protected Effects block if ownership/fencing is UNKNOWN.

SEC-INV-08
Unregistered adapters are not implicitly loaded.

SEC-INV-09
Free-form Messages are not authorized commands.

SEC-INV-10
Critical security decisions are auditable.

SEC-INV-11
Recovery revalidates security context.

SEC-INV-12
Unknown tools are denied by default.
```

---

# 132. Anti-patterns

À éviter :

```text
single admin token everywhere
all workers with prod credentials
secrets in prompts
approval == authorization
lease == authorization
runtime output trusted as policy
dynamic plugins without allowlist
unrestricted shell by default
unrestricted egress by default
global cross-tenant memory
pickle from untrusted state
silent security bypass
```

---

# 133. Test Strategy

Tests nécessaires :

```text
AuthN
AuthZ
tenant isolation
tool permissions
secret redaction
sandboxing
fencing
approval revalidation
break-glass
admin controls
recovery security
```

---

# 134. Test — Unauthorized Effect

```text
Principal lacks permission
↓
Effect blocked
↓
AuthorizationDenied audit
```

---

# 135. Test — Cross Tenant

```text
tenant A requests tenant B artifact
```

Résultat :

```text
DENY
```

---

# 136. Test — Stale Approval

```text
approval fingerprint A
effect fingerprint B
```

Résultat :

```text
BLOCK
```

---

# 137. Test — Secret Redaction

Injecter un secret connu puis vérifier son absence dans :

```text
logs
traces
audit
messages
```

---

# 138. Test — Stale Worker

Après takeover, l’ancien worker ne doit pas pouvoir exécuter un Protected Effect.

---

# 139. Test — Runtime Self-Elevation

Runtime retourne :

```text
permission=admin
```

Résultat :

```text
ignored / rejected
```

---

# 140. Test — Unknown Tool

Runtime demande un tool non enregistré.

Résultat :

```text
DENY
```

---

# 141. Test — Break-glass

Vérifier :

```text
strong permission
reason
TTL
audit
alert
```

---

# 142. Test — Sandbox Escape

Tester :

```text
path traversal
symlink escape
host filesystem access
network bypass
privilege escalation
```

---

# 143. Test — Webhook Replay

Même webhook reçu plusieurs fois.

Résultat :

```text
validated
deduplicated
single logical processing
```

---

# 144. Test — Permission Revoked After WAITING

```text
permission valid
Run WAITING
permission revoked
Run resumes
```

Le Protected Effect doit revalider.

---

# 145. Test — Policy Engine Unavailable

Pour un effect `CRITICAL` :

```text
policy unavailable
→ BLOCK
```

---

# 146. Test — SecretProvider Unavailable

Si tool requiert secret :

```text
do not execute
```

---

# 147. Test — AuditStore Unavailable

En profil `HIGH_ASSURANCE` :

```text
critical action may fail closed
```

---

# 148. Production Qualification

Une qualification sécurité production exige :

```text
real IAM integration
real SecretProvider
multi-tenant tests
sandbox tests
coding-agent tests
security logging
audit review
least-privilege credentials
```

---

# 149. Security Review Checklist

Avant release :

```text
permissions reviewed
secrets inventory reviewed
adapters allowlisted
tools classified
critical Effects mapped
tenant boundaries tested
audit paths tested
break-glass reviewed
```

---

# 150. Architecture cible

```text
              Authenticated Principal
                       │
                       ▼
                SecurityContext
                       │
                       ▼
                 Authorization
                       │
                       ▼
                  Policy Engine
             ┌─────────┼─────────┐
             ▼         ▼         ▼
           ALLOW      DENY   REQUIRE_APPROVAL
                                │
                                ▼
                             Approval
                                │
                ┌───────────────┴───────────────┐
                ▼                               ▼
          Ownership/Fencing                Tenant Checks
                │                               │
                └───────────────┬───────────────┘
                                ▼
                         Tool / Effect Gate
                                │
                                ▼
                         Secret Resolution
                                │
                                ▼
                         External System
                                │
                                ▼
                         Audit / Telemetry
```

---

# 151. Flux Protected Effect

```text
Runtime requests action
↓
schema validation
↓
Principal / tenant resolution
↓
Authorization
↓
Policy
↓
Approval if required
↓
Ownership / Fencing
↓
Secret resolution
↓
External call
↓
Effect outcome
↓
Audit
```

---

# 152. Flux Coding Agent

```text
Coding Agent
↓
shell/git/tool request
↓
workspace boundary
↓
tool classification
↓
Authorization
↓
Policy
↓
Approval if sensitive
↓
scoped credential
↓
Git / CI / Cloud
```

---

# 153. Flux Takeover sécurisé

```text
Worker A loses lease
↓
Worker B takeover
↓
fresh fencing token
↓
fresh secret resolution
↓
revalidate policy
↓
revalidate approval
↓
continue
```

---

# 154. Flux Break-glass

```text
Operator requests emergency override
↓
strong AuthN
↓
break-glass permission
↓
explicit reason
↓
short-lived scope
↓
action
↓
high-priority audit + alert
```

---

# 155. Questions ouvertes

```text
Q-SEC-01 SecurityContext doit-il être un Value Object du core ?
Q-SEC-02 Quel RBAC minimal intégrer ?
Q-SEC-03 AuthorizationPort obligatoire en production ?
Q-SEC-04 Quel sandbox par défaut pour coding agents ?
Q-SEC-05 Faut-il un SecurityProfile natif ?
Q-SEC-06 KillSwitch dans le core ?
Q-SEC-07 RLS recommandé ou seulement optionnel ?
Q-SEC-08 Comment versionner les policies ?
Q-SEC-09 Adapter signing nécessaire à terme ?
Q-SEC-10 Quels SecurityEvents sont P0 ?
Q-SEC-11 Quel comportement exact si AuditStore est indisponible ?
Q-SEC-12 Break-glass dans le core ou via governance plugin ?
```

---

# 156. ADR induits

```text
ADR-SEC-001 Principal and SecurityContext
ADR-SEC-002 AuthorizationPort
ADR-SEC-003 Deny-by-default
ADR-SEC-004 SecretProvider abstraction
ADR-SEC-005 Tool permission model
ADR-SEC-006 Runtime trust levels
ADR-SEC-007 Coding-agent sandbox baseline
ADR-SEC-008 Tenant isolation strategy
ADR-SEC-009 Security readiness
ADR-SEC-010 Break-glass model
ADR-SEC-011 Kill-switch strategy
ADR-SEC-012 Adapter allowlisting
ADR-SEC-013 Audit fail-closed behavior
ADR-SEC-014 Production security profiles
```

---

# 157. Definition of Done

Le Security & Trust Model est mature lorsque :

1. les trust boundaries sont documentées ;
2. `Principal` et `SecurityContext` sont formalisés ;
3. AuthN est déléguée à un provider externe ;
4. AuthZ est vérifiée avant les actions sensibles ;
5. les Protected Effects passent par un Tool/Effect Gate ;
6. les secrets sont externalisés ;
7. les workers utilisent least privilege ;
8. les coding agents ont une baseline d’isolation ;
9. les tenants sont isolés ;
10. Approval et Authorization restent distinctes ;
11. Lease/Fencing et Authorization restent distincts ;
12. les adapters sont allowlistés/versionnés ;
13. les security events sont auditables ;
14. les contrôles critiques sont fail-closed ;
15. recovery et takeover revalident le contexte sécurité ;
16. le break-glass est limité et audité ;
17. une posture de sécurité est visible opérationnellement ;
18. la qualification production inclut IAM, secrets, sandbox et multi-tenancy réels.

---

# 158. Résumé

Le Security & Trust Model de PyAgentsKit repose sur :

```text
IDENTITY
+
AUTHORIZATION
+
LEAST PRIVILEGE
+
POLICY
+
APPROVAL
+
OWNERSHIP
+
FENCING
+
SECRET ISOLATION
+
RUNTIME SANDBOXING
+
TENANT ISOLATION
+
AUDIT
```

Les distinctions critiques sont :

```text
AUTHENTICATION ≠ AUTHORIZATION ≠ APPROVAL
LEASE ≠ PERMISSION
FENCING TOKEN ≠ CREDENTIAL
MESSAGE ≠ AUTHORIZED COMMAND
RUNTIME OUTPUT ≠ AUTHORITY
```

Le principe fondamental est :

> **L’intelligence d’un agent peut être dynamique ; son autorité doit rester explicitement bornée, vérifiable et révocable.**

Le document suivant approfondit les menaces concrètes :

```text
../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md
```
