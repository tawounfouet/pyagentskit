# PyAgentsKit — External Systems & Connectors

**Document :** `../security-governance/22_PYAGENTSKIT_EXTERNAL_SYSTEMS_AND_CONNECTORS.md`  
**Version :** 1.0  
**Date :** 20 octobre 2026  
**Statut :** Spécification métier et technique — External Systems & Connectors  
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
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/19_PYAGENTSKIT_THREAT_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/21_PYAGENTSKIT_CODING_AGENT_INTEGRATION_MODEL.md`

---

# 1. Objet

Ce document définit le modèle d’intégration des **systèmes externes et connectors** de PyAgentsKit.

Il précise comment PyAgentsKit doit interagir avec :

- APIs HTTP ;
- webhooks ;
- bases de données externes ;
- systèmes de messaging ;
- SaaS ;
- Git providers ;
- CI/CD ;
- registries de packages ;
- plateformes cloud ;
- ERP/CRM ;
- systèmes de paiement ;
- services de messagerie ;
- systèmes internes ;
- systèmes de fichiers/stockage ;
- brokers et queues.

Le principe directeur est :

> **PyAgentsKit ne doit jamais confondre “savoir appeler un système externe” avec “savoir garantir la sûreté de l’effet produit sur ce système”.**

---

# 2. Objectifs

Le modèle doit fournir :

```text
connector neutrality
explicit contracts
security boundaries
idempotency awareness
reconciliation awareness
rate-limit awareness
retry discipline
observable integrations
safe degradation
versioned capabilities
```

---

# 3. Non-objectifs

PyAgentsKit ne devient pas :

```text
iPaaS généraliste
ESB
API gateway
message broker
ETL platform
service mesh
generic SDK generator
universal connector marketplace
```

---

# 4. Terminologie

## External System

Un système externe est une dépendance hors du contrôle transactionnel direct de PyAgentsKit.

## Connector

Un connector est un adapter d’intégration avec un système externe.

## Port

Un Port exprime un contrat dont le domaine ou l’application a besoin.

## Provider Adapter

Implémentation concrète d’un port pour un fournisseur donné.

---

# 5. Principe Ports & Adapters

```text
Domain/Application
        │
        ▼
       Port
        │
        ▼
    Connector
        │
        ▼
 External System
```

Le core ne doit pas dépendre directement de :

```text
requests
boto3
google sdk
github sdk
stripe sdk
azure sdk
```

---

# 6. Connector Categories

Catégories principales :

```text
READ_CONNECTOR
WRITE_CONNECTOR
EVENT_SOURCE
MESSAGING_CONNECTOR
STORAGE_CONNECTOR
IDENTITY_CONNECTOR
RUNTIME_CONNECTOR
ADMIN_CONNECTOR
```

---

# 7. Read Connector

Permet :

```text
query
lookup
inspect
list
read status
```

Sans mutation durable externe.

---

# 8. Write Connector

Permet une mutation telle que :

```text
create
update
delete
publish
send
deploy
trigger
merge
```

Ces opérations doivent être analysées comme Effects.

---

# 9. Event Source

Exemples :

```text
webhook
queue
stream
polling source
scheduler callback
```

---

# 10. Messaging Connector

Exemples :

```text
Kafka
RabbitMQ
NATS
SQS
Pub/Sub
Service Bus
```

---

# 11. Storage Connector

Exemples :

```text
S3
Azure Blob
GCS
filesystem
database object store
```

---

# 12. Identity Connector

Exemples :

```text
OIDC provider
OAuth provider
workload identity
service account provider
```

---

# 13. Connector Contract

Un connector doit documenter :

```text
name
provider
version
capabilities
authentication mode
required permissions
supported operations
side effects
idempotency behavior
reconciliation behavior
rate limits
timeouts
retry semantics
error mapping
security limitations
```

---

# 14. ConnectorDescriptor

Value Object candidat :

```text
connector_name
provider
connector_version
api_version
capabilities
security_profile
effect_control_level
```

---

# 15. Connector Capabilities

Exemples :

```text
READ
WRITE
IDEMPOTENCY_KEY
EXTERNAL_REFERENCE
RECONCILIATION
WEBHOOKS
POLLING
STREAMING
BATCH
PAGINATION
CONDITIONAL_WRITE
REMOTE_FENCING
```

---

# 16. Capability Negotiation

PyAgentsKit ne doit pas supposer qu’un provider supporte :

```text
idempotency
reconciliation
transactions
conditional updates
```

Chaque connector le déclare explicitement.

---

# 17. SideEffectControlLevel

Niveaux candidats :

```text
OBSERVE_ONLY
PARTIAL_CONTROL
FULL_CONTROL
```

---

# 18. FULL_CONTROL

Signifie idéalement :

```text
all state-changing operations intercepted
policy enforceable
approval enforceable
idempotency/reconciliation hooks available
```

---

# 19. PARTIAL_CONTROL

Signifie :

```text
some side effects may occur outside PyAgentsKit control
```

Cette limitation doit être visible.

---

# 20. OBSERVE_ONLY

PyAgentsKit peut observer mais pas bloquer.

---

# 21. Connector Registry

Composant conceptuel :

```text
ConnectorRegistry
```

Responsabilités :

```text
register
resolve
validate compatibility
expose capabilities
disable
list
```

---

# 22. Connector Registration

En production :

```text
explicit registration
```

préférable au chargement implicite.

---

# 23. Connector Allowlist

Un connector inconnu :

```text
DENY
```

par défaut pour les actions sensibles.

---

# 24. Version Pinning

Chaque connector devrait être version-pinné.

---

# 25. API Versioning

Le connector doit distinguer :

```text
connector version
provider API version
```

---

# 26. Authentication Modes

Exemples :

```text
API_KEY
OAUTH2
OIDC
MTLS
BASIC
SIGNED_REQUEST
WORKLOAD_IDENTITY
NONE
```

---

# 27. Credential Scope

Les credentials doivent être :

```text
least-privileged
scoped
short-lived when possible
```

---

# 28. Credential Brokering

Flux recommandé :

```text
Tool/Connector call
↓
SecretProvider / Workload Identity
↓
scoped credential
↓
connector
```

---

# 29. No Global Credentials

À éviter :

```text
one global admin token for all tenants
```

---

# 30. Tenant-specific Integrations

Un tenant peut avoir ses propres :

```text
credentials
provider accounts
webhook secrets
endpoints
policies
```

---

# 31. Connector Configuration

Structure candidate :

```text
connector_id
tenant_id?
provider
settings
secret_references
enabled
environment
```

---

# 32. Connector Configuration Security

Les secrets ne doivent pas être stockés dans :

```text
plain config
logs
audit payload
```

---

# 33. HTTP Connector

Doit supporter :

```text
timeouts
TLS
headers
auth
status mapping
retry policy
pagination
rate limits
```

---

# 34. HTTP Timeout

Toujours borné.

```text
connect timeout
read timeout
overall timeout
```

---

# 35. HTTP Retry

Retry acceptable selon :

```text
HTTP method
idempotency support
request state
provider semantics
```

---

# 36. Unsafe HTTP Retry

À éviter :

```text
blind POST retry
```

sans :

```text
idempotency key
or reconciliation
```

---

# 37. HTTP Status Mapping

Exemples :

```text
2xx → success
409 → conflict
429 → rate limited
5xx → provider failure
401/403 → authorization failure
```

Le mapping exact dépend du provider.

---

# 38. Retry-After

Si provider renvoie :

```text
Retry-After
```

le connector doit le respecter lorsque approprié.

---

# 39. Rate Limits

Le connector doit pouvoir exposer :

```text
remaining quota
reset time
retry-after
```

si disponible.

---

# 40. Rate-limit Awareness

PyAgentsKit peut appliquer :

```text
backoff
queueing
admission reduction
```

---

# 41. Backoff

Stratégies :

```text
fixed
exponential
bounded exponential
jittered
```

---

# 42. Retry Budget

Chaque connector devrait pouvoir définir :

```text
max attempts
max elapsed time
```

---

# 43. Retry != Recovery

```text
Retry
= repeat same operation soon

Recovery
= reconstruct safe next action after failure
```

---

# 44. Retry != Reconciliation

```text
Reconciliation
= determine what actually happened
```

---

# 45. ExternalReference

Après mutation externe réussie :

```text
ExternalReference
```

doit être capturée dès que possible.

---

# 46. ExternalReference Structure

```text
system
kind
value
provider
tenant?
metadata?
```

---

# 47. ExternalReference Examples

```text
github:pr:123
stripe:payment_intent:pi_x
aws:deployment:dpl_42
jira:issue:ABC-123
```

---

# 48. Idempotency

Un connector peut déclarer :

```text
NATIVE_IDEMPOTENCY
EMULATED_IDEMPOTENCY
NO_IDEMPOTENCY
```

---

# 49. Native Idempotency

Le provider accepte une :

```text
idempotency key
```

et garantit une sémantique définie.

---

# 50. Emulated Idempotency

PyAgentsKit doit utiliser :

```text
business key
lookup
conditional create
unique external constraint
```

---

# 51. No Idempotency

Les actions doivent être considérées comme plus risquées.

---

# 52. InputFingerprint

Avant un Effect :

```text
canonical input
↓
fingerprint
```

pour détecter réutilisation incorrecte.

---

# 53. Reconciliation Capability

Niveaux candidats :

```text
NONE
LOOKUP_BY_ID
LOOKUP_BY_BUSINESS_KEY
LIST_AND_MATCH
STATUS_QUERY
FULL_RECONCILIATION
```

---

# 54. ReconciliationPort

Contrat :

```python
class ReconciliationPort(Protocol):
    async def reconcile(
        self,
        effect,
        external_system,
    ) -> ReconciliationResult:
        ...
```

---

# 55. ReconciliationResult

```text
CONFIRMED_SUCCESS
CONFIRMED_FAILURE
NOT_FOUND
AMBIGUOUS
MANUAL_REVIEW_REQUIRED
```

---

# 56. Provider-specific Reconciliation

Exemples :

```text
Git push → inspect branch SHA
PR create → lookup head/base
Payment → lookup merchant reference
Email → provider message ID/status
Deploy → query deployment state
```

---

# 57. Webhook Connectors

Les webhooks doivent gérer :

```text
signature validation
timestamp validation
deduplication
replay protection
schema validation
```

---

# 58. Webhook Event Identity

Chaque événement doit idéalement disposer de :

```text
provider_event_id
```

---

# 59. InboxStore

Le webhook passe par :

```text
InboxStore
```

pour empêcher le traitement multiple.

---

# 60. Webhook Flow

```text
Provider
↓
Webhook Endpoint
↓
Signature Validation
↓
Inbox Dedup
↓
Schema Validation
↓
Domain/Application Command
```

---

# 61. Out-of-order Events

Les providers peuvent envoyer des événements hors ordre.

Le connector doit utiliser :

```text
provider sequence
event timestamp
current-state query
```

selon possibilité.

---

# 62. Webhook as Hint

Dans certains systèmes, un webhook doit être traité comme :

```text
signal to re-read authoritative provider state
```

plutôt que comme vérité complète.

---

# 63. Polling Connectors

Utiles si pas de webhook.

---

# 64. Polling Cursor

Concept :

```text
cursor
offset
last_seen_at
page_token
```

---

# 65. Durable Cursor

Le cursor doit être durable si perdre l’état peut provoquer :

```text
missed events
duplicate processing
```

---

# 66. Polling Dedup

Le polling doit utiliser :

```text
external ID
timestamp
business key
InboxStore
```

---

# 67. Messaging Connectors

Semantics possibles :

```text
at-most-once
at-least-once
effectively-once via dedup
```

---

# 68. Queue Delivery != Ownership

Recevoir un message n’autorise pas automatiquement l’exécution.

---

# 69. Message Ack

Ack uniquement lorsque la stratégie de traitement le permet.

---

# 70. At-least-once Messaging

Prévoir :

```text
deduplication
idempotent consumers
InboxStore
```

---

# 71. Dead Letter

Les messages impossibles à traiter peuvent être déplacés vers :

```text
DLQ
```

---

# 72. DLQ Handling

Doit être :

```text
observable
auditable
replay-controlled
```

---

# 73. Event Schema Versioning

Les événements entrants/sortants doivent être versionnés.

---

# 74. Backward Compatibility

Une migration rolling peut nécessiter :

```text
producer vN
consumer vN+1
```

ou inversement.

---

# 75. Schema Validation

Toute donnée externe doit être validée.

---

# 76. Unknown Fields

Stratégie explicite :

```text
ignore
preserve
reject
```

selon connector.

---

# 77. Missing Required Fields

Toujours :

```text
validation failure
```

---

# 78. Pagination

Le connector doit cacher la complexité provider tout en permettant :

```text
bounded reads
streaming iteration
```

---

# 79. Unbounded Listing

À éviter pour :

```text
millions of resources
```

Préférer pagination/cursors.

---

# 80. Batching

Un connector peut supporter :

```text
batch read
batch write
```

---

# 81. Batch Side Effects

Un batch write doit préciser sa sémantique :

```text
all-or-nothing?
partial success?
per-item idempotency?
```

---

# 82. Partial Success

Un batch externe peut retourner :

```text
some succeeded
some failed
```

Il faut modéliser les résultats par item si nécessaire.

---

# 83. Long-running External Operations

Exemples :

```text
deployment
data export
ML job
infrastructure apply
```

---

# 84. Async External Job

Pattern :

```text
submit
↓
ExternalReference(job_id)
↓
poll/webhook
↓
terminal status
```

---

# 85. External Job Effect

L’Effect peut être :

```text
SUCCEEDED
```

au sens :

```text
submission accepted
```

ou attendre completion selon contrat.

Cette sémantique doit être explicite.

---

# 86. Submission vs Completion

Distinguer :

```text
REQUEST_ACCEPTED
OPERATION_COMPLETED
```

---

# 87. Connector Error Taxonomy

Taxonomie candidate :

```text
ConnectorError
AuthenticationError
AuthorizationError
RateLimitError
TimeoutError
NetworkError
ValidationError
ConflictError
NotFoundError
ProviderUnavailable
AmbiguousOutcomeError
UnsupportedCapability
```

---

# 88. AmbiguousOutcomeError

Signifie :

```text
request may have succeeded externally
```

Donc :

```text
Effect → UNKNOWN
```

pas :

```text
FAILED
```

---

# 89. AuthenticationError

Peut nécessiter :

```text
credential refresh
```

mais pas retry infini.

---

# 90. AuthorizationError

Généralement :

```text
fail
```

et alerte/config correction.

---

# 91. RateLimitError

Peut être retriable avec :

```text
retry-after
backoff
```

---

# 92. ValidationError

Non retriable tant que l’entrée ne change pas.

---

# 93. ConflictError

Peut nécessiter :

```text
reload current external state
```

---

# 94. Connector Health

États :

```text
HEALTHY
DEGRADED
UNAVAILABLE
UNKNOWN
```

---

# 95. Connector Readiness

Un worker peut être non-ready pour certains workloads si connector requis indisponible.

---

# 96. Partial Readiness

Exemple :

```text
GitHub connector unhealthy
```

n’empêche pas nécessairement :

```text
local LangGraph runs
```

---

# 97. Connector Metrics

```text
connector_requests_total
connector_errors_total
connector_rate_limits_total
connector_timeouts_total
connector_retries_total
connector_reconciliations_total
```

---

# 98. Connector Latency

```text
connector_request_duration_seconds
connector_reconciliation_duration_seconds
```

---

# 99. Connector Labels

Labels candidats :

```text
connector
provider
operation
result
```

Éviter :

```text
external_id
run_id
```

---

# 100. Connector Tracing

Spans :

```text
connector.call
connector.authenticate
connector.reconcile
connector.webhook.process
connector.poll
```

---

# 101. Logs

Champs :

```text
connector
provider
operation
status
duration
retry_count
trace_id
correlation_id
```

sans credentials.

---

# 102. Audit

Toute mutation critique via connector doit pouvoir produire un AuditEvent.

---

# 103. Security Boundary

Le connector est une frontière de confiance.

Il doit considérer comme non fiables :

```text
provider payloads
headers
external IDs
redirects
webhook content
```

---

# 104. TLS

Les connectors réseau doivent utiliser TLS lorsqu’approprié.

---

# 105. Certificate Validation

À ne jamais désactiver par défaut.

---

# 106. mTLS

Peut être supporté pour :

```text
internal APIs
high-assurance providers
```

---

# 107. Proxy Support

Peut être utile en environnement entreprise.

---

# 108. Network Policy

Les destinations réseau doivent être contrôlables.

---

# 109. SSRF Prevention

Pour URLs dynamiques :

```text
scheme validation
host allowlist
private network restrictions
redirect validation
```

---

# 110. Data Classification

Le connector doit pouvoir recevoir :

```text
DataClassification
```

pour appliquer une policy.

---

# 111. Provider Data Policy

Exemple :

```text
RESTRICTED data
→ provider X forbidden
```

---

# 112. Regional Constraints

Le connector peut déclarer :

```text
region
data residency
```

---

# 113. PII Minimization

N’envoyer au provider que :

```text
minimum necessary data
```

---

# 114. Logging External Payloads

Par défaut :

```text
metadata only
```

---

# 115. Large Payloads

Utiliser :

```text
Artifact / BlobStore
```

plutôt que logs ou messages.

---

# 116. Streaming Responses

Certains connectors supportent streaming.

---

# 117. Streaming Backpressure

Doit être borné.

---

# 118. Stream Interruption

Le connector doit exposer :

```text
partial data
resume capability?
reconnect semantics?
```

---

# 119. File Transfer Connectors

Exemples :

```text
SFTP
Object Storage
HTTP download/upload
```

---

# 120. Upload Integrity

Vérifier :

```text
checksum
size
content type
```

---

# 121. Download Integrity

Idem.

---

# 122. Database Connectors

Accès externe à une base ne doit pas être confondu avec le State Store interne.

---

# 123. DB Read Connector

Peut exécuter :

```text
SELECT
```

avec policy de lecture.

---

# 124. DB Write Connector

Toute mutation externe :

```text
INSERT
UPDATE
DELETE
DDL
```

peut être un Effect.

---

# 125. Transaction Scope

Une transaction sur DB externe ne couvre pas PostgreSQL interne PyAgentsKit.

---

# 126. Dual-write Problem

```text
PyAgentsKit DB
+
external DB
```

ne partagent généralement pas une transaction.

Utiliser :

```text
Effect model
Outbox
reconciliation
```

---

# 127. SaaS Connectors

Exemples :

```text
GitHub
GitLab
Jira
Slack
ServiceNow
Salesforce
Stripe
```

---

# 128. Cloud Connectors

Exemples :

```text
AWS
Azure
GCP
Kubernetes API
```

---

# 129. Git Connectors

Doivent supporter si possible :

```text
repository read
branch inspect
push
PR create
PR merge
status checks
```

---

# 130. Git Idempotency

Operations :

```text
push → expected SHA
PR create → head/base lookup
merge → PR status / merge SHA
```

---

# 131. Registry Connectors

Exemples :

```text
PyPI
npm
Docker Registry
Artifact Registry
```

---

# 132. Publish Safety

Doit utiliser :

```text
package/version identity
artifact checksum
approval
```

---

# 133. Messaging SaaS

Exemples :

```text
Slack
Teams
Email
SMS
```

---

# 134. Send Message as Effect

Envoyer un message externe est un Effect.

---

# 135. Messaging Idempotency

Difficile selon provider.

Peut utiliser :

```text
provider message ID
client reference
dedup window
```

---

# 136. Payment Connectors

Exigent :

```text
CRITICAL effect safety
native idempotency when available
strong reconciliation
approval policies
```

---

# 137. Payment ExternalReference

Exemples :

```text
payment intent
transaction ID
merchant reference
```

---

# 138. ERP/CRM Connectors

Peuvent avoir des APIs anciennes sans idempotency.

---

# 139. Legacy Connector Risk

Dans ce cas :

```text
reconciliation
business keys
manual review
```

deviennent cruciaux.

---

# 140. Connector-specific Policies

Une policy peut dépendre de :

```text
connector
provider
operation
risk
environment
tenant
```

---

# 141. Connector Permission Model

Exemples :

```text
github.pull_request.create
github.pull_request.merge
stripe.payment.create
aws.deployment.execute
slack.message.send
```

---

# 142. Least Privilege Scopes

Le connector doit documenter le scope minimal requis.

---

# 143. Connector Secret References

Ne stocker que :

```text
SecretReference
```

---

# 144. Credential Rotation

Le connector doit pouvoir continuer après rotation sans migration des objets métier.

---

# 145. Token Refresh

Pour OAuth :

```text
refresh token
access token
expiration
```

doivent être gérés de manière sûre.

---

# 146. Refresh Token Security

Un refresh token est un secret de haute valeur.

---

# 147. Multi-account Providers

Le connector doit pouvoir distinguer :

```text
account
organization
subscription
project
workspace
```

---

# 148. Provider Resource Scope

Exemple :

```text
GitHub organization
AWS account
Azure subscription
GCP project
Stripe account
```

---

# 149. Account Boundary

Un agent ne doit pas pouvoir changer d’account via un argument non fiable.

---

# 150. External System Identity

Une référence externe doit inclure suffisamment de contexte pour éviter ambiguïté.

---

# 151. Connector State

Un connector doit être aussi stateless que possible.

---

# 152. Durable Connector State

Si nécessaire :

```text
cursor
external subscription ID
webhook registration
token metadata
```

doit être persistant.

---

# 153. ConnectorStateStore

À créer seulement si le besoin dépasse les stores existants.

---

# 154. Avoid Generic Connector Store

Ne pas introduire un store générique sans sémantique claire.

---

# 155. Subscription Management

Certains providers nécessitent :

```text
webhook subscription create/renew/delete
```

---

# 156. Webhook Subscription as Effect

Créer une subscription distante est un Effect.

---

# 157. Subscription Renewal

Peut être une automation technique, mais doit rester auditée.

---

# 158. Connector Lifecycle

États candidats :

```text
REGISTERED
READY
DEGRADED
DISABLED
UNAVAILABLE
```

---

# 159. Connector Disable

Désactiver un connector doit :

```text
stop new operations
preserve existing state
keep audit/history
```

---

# 160. In-flight Calls

Disable ne peut pas annuler rétroactivement une requête déjà partie.

---

# 161. Graceful Connector Shutdown

Doit arrêter :

```text
new admissions
```

et laisser se terminer ou marquer ambiguë l’opération courante.

---

# 162. Connector Configuration Reload

Peut être :

```text
dynamic
```

mais doit être versionné/audité si sécurité critique.

---

# 163. Connector Version Upgrade

Avant upgrade :

```text
compatibility check
contract tests
migration if needed
```

---

# 164. Conformance Suite

Chaque connector doit passer des tests standard.

---

# 165. Contract Tests

Vérifier :

```text
auth
timeouts
error mapping
retry behavior
idempotency
reconciliation
rate-limit handling
observability
```

---

# 166. Effect Conformance

Pour opérations mutantes :

```text
no blind replay
external reference captured
ambiguous outcome mapped to UNKNOWN
```

---

# 167. Webhook Conformance

Tester :

```text
signature
replay
duplicate
out-of-order
schema drift
```

---

# 168. Polling Conformance

Tester :

```text
cursor persistence
pagination
duplicate detection
provider downtime
```

---

# 169. Messaging Conformance

Tester :

```text
duplicate delivery
ack loss
redelivery
DLQ
consumer restart
```

---

# 170. Rate-limit Conformance

Simuler :

```text
429
Retry-After
quota exhaustion
```

---

# 171. Network Failure Tests

Simuler :

```text
connection reset
DNS failure
TLS failure
timeout
partial response
```

---

# 172. Ambiguous Outcome Tests

Très important pour writes :

```text
provider accepted request
connection dropped before response
```

Résultat :

```text
Effect UNKNOWN
```

---

# 173. Reconciliation Tests

Vérifier que :

```text
UNKNOWN
↓
provider lookup
↓
confirmed success/failure
```

fonctionne.

---

# 174. Idempotency Tests

Envoyer deux fois la même intention.

Résultat :

```text
one logical external effect
```

si capability le permet.

---

# 175. Tenant Isolation Tests

Deux tenants avec même provider doivent rester isolés.

---

# 176. Credential Scope Tests

Vérifier qu’un connector ne peut pas exécuter une opération hors scope.

---

# 177. Security Tests

Inclure :

```text
SSRF
malformed webhook
credential leakage
invalid redirect
cross-account resource
```

---

# 178. Load Tests

Mesurer :

```text
throughput
latency
rate-limit behavior
connection pooling
backpressure
```

---

# 179. Connector Metrics Dashboard

Afficher :

```text
requests
errors
p95/p99 latency
rate limits
retries
unknown outcomes
reconciliations
```

---

# 180. Connector Incident Runbooks

Runbooks candidats :

```text
CONNECTOR_AUTH_FAILURE
CONNECTOR_RATE_LIMIT
CONNECTOR_PROVIDER_OUTAGE
CONNECTOR_WEBHOOK_FAILURE
CONNECTOR_UNKNOWN_OUTCOME
CONNECTOR_SCHEMA_CHANGE
```

---

# 181. Provider Outage

Comportement :

```text
reads may degrade
writes stop/retry depending policy
Protected Effects may WAIT
readiness may become partial
```

---

# 182. Safe Degradation

Un outage de connector ne doit pas provoquer :

```text
blind replay
cross-provider fallback without policy
```

---

# 183. Provider Failover

Changer de provider automatiquement peut modifier la sémantique.

Doit être :

```text
explicitly configured
```

---

# 184. No Silent Provider Substitution

Exemple interdit :

```text
email provider A down
→ silently use provider B
```

si cela change :

```text
compliance
sender identity
data residency
```

---

# 185. Connector Audit Events

Événements candidats :

```text
connector.registered
connector.disabled
connector.call_failed
connector.rate_limited
connector.reconciliation_started
connector.reconciliation_completed
connector.credentials_rotated
connector.version_changed
```

---

# 186. External Operation Audit

Conserver :

```text
connector
provider
operation
external reference
effect id
principal
tenant
result
```

---

# 187. External Payload Audit

Ne pas stocker le payload complet par défaut.

---

# 188. API Keys in Query String

À éviter.

---

# 189. Redirect Handling

Limiter :

```text
max redirects
allowed hosts
protocol changes
```

---

# 190. DNS Rebinding

Pour URLs dynamiques à haut risque, considérer validation IP après résolution/connexion selon architecture.

---

# 191. Proxy Trust

Si proxy d’entreprise :

```text
proxy credentials
CA certificates
routing
```

doivent être explicitement gérés.

---

# 192. Certificate Pinning

Option high-assurance, pas obligatoire par défaut.

---

# 193. Request Signing

Peut être requis par certains providers.

---

# 194. Clock Skew

Les signatures temporelles doivent tolérer un skew borné.

---

# 195. Connector Caching

Peut être utilisé pour reads.

---

# 196. Cache Is Not Authority

Pour :

```text
effect status
approval status
ownership
```

ne jamais utiliser un cache externe comme vérité.

---

# 197. Read-after-write

Un provider peut être éventuellement cohérent.

Le connector doit documenter :

```text
consistency model
```

---

# 198. Eventual Consistency

La reconciliation doit en tenir compte.

---

# 199. Search-after-create Delay

Exemple :

```text
PR created
lookup immediately returns not found
```

Ne pas conclure trop vite à échec.

---

# 200. Reconciliation Window

Peut inclure :

```text
initial delay
bounded retries
backoff
manual fallback
```

---

# 201. Connector-specific Business Keys

Exemples :

```text
merchant_reference
client_request_id
branch + SHA
package + version
issue key
```

---

# 202. Business Key Registry

Peut rester dans le connector, pas dans un core générique.

---

# 203. Data Mapping

Le connector traduit :

```text
domain/app model
↔
provider model
```

---

# 204. Anti-Corruption Layer

Le connector agit comme :

```text
Anti-Corruption Layer
```

pour empêcher le modèle provider d’envahir le domaine.

---

# 205. Provider-specific Enums

Ne pas propager directement :

```text
GitHubStatus
StripeStatus
AWSStatus
```

dans le core.

---

# 206. Canonical Internal Status

Mapper vers des concepts internes lorsque pertinent.

---

# 207. Unknown Provider Status

Si provider ajoute un statut inconnu :

```text
UNKNOWN_EXTERNAL_STATUS
```

ou mapping sécurisé.

---

# 208. Forward Compatibility

Ne pas crasher silencieusement sur nouvelle valeur provider.

---

# 209. Connector Package Layout

Exemple :

```text
pyagentskit/
├── ports/
│   └── connectors/
├── adapters/
│   ├── github/
│   ├── stripe/
│   ├── aws/
│   ├── slack/
│   └── generic_http/
```

---

# 210. Generic HTTP Connector

Utile, mais ne doit pas prétendre connaître la sémantique métier d’un provider spécifique.

---

# 211. Provider-specific Connector

Préférable lorsqu’il faut :

```text
idempotency
reconciliation
typed references
risk mapping
```

---

# 212. Connector SDK

Une base commune peut fournir :

```text
auth helpers
timeouts
retry helpers
telemetry
error mapping utilities
```

sans masquer la sémantique provider.

---

# 213. Connector Base Class

À éviter si elle impose trop de comportement implicite.

Préférer :

```text
composition
protocols
small reusable helpers
```

---

# 214. Connector Invariants

```text
CONN-INV-01
Connector output is not authority by itself.

CONN-INV-02
Mutating operations are classified as Effects when durable externally.

CONN-INV-03
Ambiguous write outcomes never become FAILED automatically.

CONN-INV-04
Unknown connector is denied for sensitive operations.

CONN-INV-05
Credentials are scoped and externalized.

CONN-INV-06
Provider payloads are validated.

CONN-INV-07
Retries follow provider and idempotency semantics.

CONN-INV-08
Reconciliation is provider-specific.

CONN-INV-09
Connector configuration is tenant-safe.

CONN-INV-10
External references are captured when available.
```

---

# 215. Anti-patterns

À éviter :

```text
blind retry of POST
generic connector claiming universal idempotency
provider SDK objects leaking into domain
global admin credential
webhook without replay protection
connector logs full secrets
retry == reconciliation
HTTP 500 == business failure
queue delivery == ownership
silent provider failover
```

---

# 216. Acceptance Criteria

Le modèle External Systems & Connectors est opérationnel si :

1. les connectors sont derrière des ports ;
2. chaque connector expose ses capabilities ;
3. AuthN et credentials sont explicitement gérés ;
4. les writes sont classifiés comme Effects lorsque nécessaire ;
5. idempotency support est déclaré ;
6. reconciliation support est déclaré ;
7. ambiguous outcomes deviennent `UNKNOWN` ;
8. webhooks sont signés/dédupliqués ;
9. polling cursors peuvent être durables ;
10. messaging duplicate delivery est supporté ;
11. rate limits sont respectés ;
12. erreurs provider sont normalisées ;
13. observability est disponible ;
14. multi-tenancy est respecté ;
15. unknown connector/tool est refusé par défaut ;
16. contract/conformance tests existent ;
17. provider outage possède un comportement sûr ;
18. les limitations de sécurité sont visibles.

---

# 217. Architecture cible

```text
                    PyAgentsKit Core
                           │
                ┌──────────┼──────────┐
                ▼          ▼          ▼
             ReadPort   WritePort   EventPort
                │          │          │
                ▼          ▼          ▼
            Connector   Connector   Connector
                │          │          │
                └──────────┼──────────┘
                           ▼
                   External Systems
             Git / SaaS / Cloud / DB /
             Messaging / Storage / APIs

Cross-cutting:
- AuthN / Credentials
- Policy / Approval
- Idempotency
- Reconciliation
- Rate Limits
- Audit / Telemetry
```

---

# 218. Flux Write nominal

```text
Run
↓
Effect intent
↓
Policy / Approval
↓
Connector capability check
↓
Idempotency strategy
↓
External call
↓
ExternalReference
↓
Effect SUCCEEDED
↓
Audit
```

---

# 219. Flux Write ambigu

```text
Effect STARTED
↓
external request sent
↓
network timeout
↓
outcome unknown
↓
Effect UNKNOWN
↓
Reconciliation
↓
confirmed success / failure / manual review
```

---

# 220. Flux Webhook

```text
Provider
↓
Webhook
↓
Signature Validation
↓
Inbox Dedup
↓
Schema Validation
↓
Command/Event
↓
Run creation or wake-up
```

---

# 221. Flux Queue

```text
Message Broker
↓
delivery
↓
Inbox/Dedup
↓
Run candidate
↓
Lease acquisition
↓
execution
↓
ack
```

---

# 222. Flux Provider Outage

```text
connector call
↓
provider unavailable
↓
safe retry/backoff if read/idempotent
or
Effect UNKNOWN / WAITING
↓
readiness degraded
↓
runbook / alert
```

---

# 223. Questions ouvertes

```text
Q-CONN-01 ConnectorDescriptor dans le core ou package integration ?
Q-CONN-02 Generic HTTP connector officiel ?
Q-CONN-03 Quel niveau de capability negotiation public ?
Q-CONN-04 ConnectorStateStore nécessaire ?
Q-CONN-05 Quels connectors de référence implémenter d’abord ?
Q-CONN-06 Quelle stratégie de retries commune ?
Q-CONN-07 Comment versionner les provider API mappings ?
Q-CONN-08 Faut-il un certification level officiel des connectors ?
Q-CONN-09 Comment représenter eventual consistency ?
Q-CONN-10 Quels connectors supportent REMOTE_FENCING ?
Q-CONN-11 Faut-il un connector marketplace à long terme ?
Q-CONN-12 Quelle politique standard pour provider failover ?
```

---

# 224. ADR induits

```text
ADR-CONN-001 ConnectorDescriptor
ADR-CONN-002 Capability declaration
ADR-CONN-003 Authentication and credential brokering
ADR-CONN-004 Retry policy
ADR-CONN-005 Reconciliation contract
ADR-CONN-006 Webhook security
ADR-CONN-007 Messaging deduplication
ADR-CONN-008 Provider error taxonomy
ADR-CONN-009 Connector versioning
ADR-CONN-010 Multi-tenant connector config
ADR-CONN-011 Generic HTTP connector boundaries
ADR-CONN-012 Connector conformance certification
```

---

# 225. Definition of Done

La couche External Systems & Connectors est mature lorsque :

1. le registre de connectors existe ;
2. les capabilities sont déclarées ;
3. les credentials sont externalisés ;
4. les writes sensibles sont des Effects ;
5. les ambiguous outcomes sont correctement gérés ;
6. au moins un connector avec idempotency native est qualifié ;
7. au moins un connector sans idempotency native est qualifié avec reconciliation ;
8. webhooks et polling sont couverts ;
9. messaging at-least-once est couvert ;
10. les rate limits sont testés ;
11. les connectors passent une conformance suite ;
12. multi-tenancy est testé ;
13. sécurité réseau et webhook est testée ;
14. telemetry/audit est complète ;
15. provider outage et safe degradation sont testés ;
16. aucun objet SDK provider ne fuit dans le core.

---

# 226. Résumé

La couche External Systems & Connectors repose sur :

```text
PORTS
+
EXPLICIT CONNECTORS
+
CAPABILITY DECLARATION
+
SCOPED CREDENTIALS
+
IDEMPOTENCY
+
RECONCILIATION
+
RATE-LIMIT AWARENESS
+
OBSERVABILITY
+
AUDIT
```

Les distinctions centrales sont :

```text
RETRY
≠
RECONCILIATION

QUEUE DELIVERY
≠
OWNERSHIP

CONNECTOR CALL
≠
EFFECT SUCCESS

PROVIDER RESPONSE
≠
TRUSTED AUTHORITY

GENERIC HTTP
≠
PROVIDER SEMANTICS
```

Le principe fondamental reste :

> **PyAgentsKit doit être capable de parler à beaucoup de systèmes externes sans jamais prétendre que tous offrent les mêmes garanties.**

Le document suivant naturel est :

```text
../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md
```
