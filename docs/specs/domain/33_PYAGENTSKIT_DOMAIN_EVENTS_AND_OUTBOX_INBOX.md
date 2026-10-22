# PyAgentsKit — Domain Events, Outbox & Inbox

**Document :** `../domain/33_PYAGENTSKIT_DOMAIN_EVENTS_AND_OUTBOX_INBOX.md`  
**Version :** 1.0  
**Date :** 22 octobre 2026  
**Statut :** Domain Events & Messaging Reliability Specification  
**Projet :** PyAgentsKit  

**Documents de référence :**
- `../architecture/05_PYAGENTSKIT_PRINCIPES_ARCHITECTURAUX.md`
- `../domain/06_PYAGENTSKIT_OBJETS_METIERS.md`
- `../domain/07_PYAGENTSKIT_ENTITES.md`
- `../domain/09_PYAGENTSKIT_VALUE_OBJECTS.md`
- `../domain/10_PYAGENTSKIT_ETATS_ET_CYCLES_DE_VIE.md`
- `../architecture/11_PYAGENTSKIT_ARCHITECTURE_CIBLE.md`
- `../runtime/14_PYAGENTSKIT_DURABLE_EXECUTION_MODEL.md`
- `../runtime/15_PYAGENTSKIT_DISTRIBUTED_COORDINATION_MODEL.md`
- `../runtime/16_PYAGENTSKIT_PERSISTENCE_AND_STATE_STORES.md`
- `../runtime/17_PYAGENTSKIT_HUMAN_GOVERNANCE_AND_APPROVALS.md`
- `../security-governance/18_PYAGENTSKIT_SECURITY_AND_TRUST_MODEL.md`
- `../security-governance/20_PYAGENTSKIT_OBSERVABILITY_AND_AUDIT_MODEL.md`
- `../runtime/23_PYAGENTSKIT_API_AND_PUBLIC_CONTRACTS.md`
- `../operations/24_PYAGENTSKIT_POSTGRESQL_DATA_MODEL.md`
- `../operations/25_PYAGENTSKIT_FAILURE_AND_RECOVERY_SCENARIOS.md`
- `../architecture/27_PYAGENTSKIT_BOUNDED_CONTEXTS_AND_CONTEXT_MAP.md`
- `../architecture/28_PYAGENTSKIT_PORTS_AND_ADAPTERS_CATALOG.md`
- `../architecture/29_PYAGENTSKIT_PACKAGE_DEPENDENCY_RULES.md`
- `../runtime/31_PYAGENTSKIT_APPLICATION_SERVICES_AND_USE_CASES.md`
- `../runtime/32_PYAGENTSKIT_REPOSITORIES_AND_UNIT_OF_WORK.md`
- `../operations/38_PYAGENTSKIT_TEST_STRATEGY.md`
- `../operations/39_PYAGENTSKIT_CONTRACT_TESTING_STRATEGY.md`
- `../operations/40_PYAGENTSKIT_PRODUCTION_QUALIFICATION_PLAN.md`
- `../operations/41_PYAGENTSKIT_DEPLOYMENT_AND_OPERATIONS.md`
- `../operations/42_PYAGENTSKIT_RUNBOOKS_AND_INCIDENT_RESPONSE.md`
- `../reference/47_PYAGENTSKIT_GLOSSAIRE.md`

---

# 1. Objet

Ce document définit le modèle de **Domain Events**, **Integration Events**, **Outbox** et **Inbox** de PyAgentsKit V2.

L’objectif est de répondre à quatre questions :

1. comment représenter un fait métier interne ;
2. comment propager ce fait vers d’autres bounded contexts ou systèmes ;
3. comment rendre la publication fiable sans transaction distribuée ;
4. comment traiter les redeliveries et doublons sans répéter une conséquence métier.

Le principe directeur est :

> **Domain truth is committed first; external propagation is made reliable through explicit durable messaging boundaries.**

---

# 2. Distinctions fondamentales

PyAgentsKit doit maintenir des séparations strictes :

```text
DomainEvent
!=
IntegrationEvent
!=
RuntimeEvent
!=
AuditEvent
```

et également :

```text
Outbox delivery
!=
Run ownership
```

```text
Inbox deduplication
!=
Effect idempotency
```

```text
Broker acknowledgment
!=
business success
```

---

# 3. DomainEvent

Un `DomainEvent` représente :

> **un fait métier significatif qui s’est déjà produit à l’intérieur d’un bounded context.**

Exemples :

```text
RunStarted
RunWaiting
RunCompleted
EffectStarted
EffectSucceeded
EffectBecameUnknown
ApprovalRequested
ApprovalApproved
LeaseTakenOver
ConversationCreated
ArtifactRegistered
```

---

# 4. DomainEvent Is Past Tense

Le naming recommandé utilise un fait accompli :

```text
EffectSucceeded
ApprovalRejected
RunCancelled
```

et non :

```text
SucceedEffect
RejectApproval
CancelRun
```

Les seconds sont des Commands.

---

# 5. Command != DomainEvent

```text
Command
=
request to do something

DomainEvent
=
fact that something happened
```

Exemple :

```text
ApproveApproval
→
ApprovalApproved
```

---

# 6. DomainEvent Ownership

Chaque DomainEvent appartient à un bounded context précis.

Exemples :

```text
Execution
→ RunStarted
→ RunWaiting
→ RunSucceeded

Effects
→ EffectStarted
→ EffectSucceeded
→ EffectBecameUnknown

Governance
→ ApprovalRequested
→ ApprovalApproved

Coordination
→ LeaseAcquired
→ LeaseTakenOver
```

---

# 7. DomainEvent Is Not Automatically External

Un DomainEvent peut rester entièrement interne au bounded context.

Il ne doit devenir un message inter-contextes ou externe que si :

```text
another component truly needs it
```

---

# 8. IntegrationEvent

Un `IntegrationEvent` représente :

> **un événement destiné à franchir une frontière de bounded context, de process, de service ou de système.**

Il est généralement dérivé d’un DomainEvent ou d’une décision applicative.

---

# 9. DomainEvent → IntegrationEvent

Exemple :

```text
DomainEvent:
EffectSucceeded

IntegrationEvent:
pyagentskit.effects.effect_succeeded.v1
```

---

# 10. Why Separate Them

Le Domain ne doit pas dépendre :

```text
Kafka schema
RabbitMQ routing key
JSON wire format
HTTP webhook structure
```

Le modèle interne reste stable même si le transport change.

---

# 11. RuntimeEvent

Un `RuntimeEvent` décrit ce que fait ou observe un runtime agentique.

Exemples :

```text
RuntimeStarted
ModelCallStarted
ToolRequested
RuntimeWaiting
RuntimeCompleted
```

Il appartient au boundary Runtime Integration.

---

# 12. RuntimeEvent Is Not Domain Truth

Un runtime peut dire :

```text
ToolCallCompleted
```

sans que cela prouve automatiquement :

```text
EffectSucceeded
```

---

# 13. AuditEvent

Un `AuditEvent` répond à :

```text
who did what
when
why
against what
with what authority/evidence
```

Il est orienté traçabilité et responsabilité.

---

# 14. AuditEvent Is Not DomainEvent

Les deux peuvent être produits à partir d’une même action.

Exemple :

```text
DomainEvent:
ApprovalApproved

AuditEvent:
principal X approved Approval Y
with policy version Z
```

---

# 15. Canonical Distinction

```text
DomainEvent
→ business fact

IntegrationEvent
→ published interoperability message

RuntimeEvent
→ runtime observation

AuditEvent
→ accountability evidence
```

---

# 16. Event Envelope

Les DomainEvents et IntegrationEvents doivent être transportés dans une enveloppe stable.

Proposition :

```text
event_id
event_type
event_version
occurred_at
tenant_id
correlation_id
causation_id
aggregate_type
aggregate_id
aggregate_version
payload
metadata
```

---

# 17. event_id

Identifiant unique du message/event.

---

# 18. event_type

Nom canonique.

Exemple :

```text
pyagentskit.effects.effect_succeeded
```

---

# 19. event_version

Version du schema de payload.

Exemple :

```text
1
```

---

# 20. occurred_at

Timestamp UTC du fait métier.

---

# 21. tenant_id

Requis pour tout événement tenant-scoped.

---

# 22. correlation_id

Permet de relier :

```text
Run
Effect
Approval
RuntimeInvocation
```

sans imposer une relation métier directe.

---

# 23. causation_id

Référence à l’élément ayant causé cet événement.

Exemple :

```text
command id
prior event id
request id
```

---

# 24. aggregate_type

Exemples :

```text
Run
Effect
Approval
Lease
```

---

# 25. aggregate_id

Identité de l’aggregate concerné.

---

# 26. aggregate_version

Version de l’aggregate après la transition.

Utile pour :

```text
ordering
diagnostics
idempotent projections
```

---

# 27. payload

Contient uniquement les données nécessaires au consumer.

---

# 28. metadata

Peut contenir :

```text
schema version
producer version
trace reference
```

mais pas de secrets.

---

# 29. Event ID Immutability

Une fois créé :

```text
event_id
```

ne change jamais.

---

# 30. Event Payload Immutability

Un événement publié ne doit pas être réécrit.

Une correction ultérieure se représente par :

```text
new event
```

---

# 31. Event Versioning

Toute modification incompatible du payload nécessite :

```text
event_version increment
```

---

# 32. Event Version != Package Version

Exemple :

```text
PyAgentsKit 2.1.0
```

peut toujours publier :

```text
EffectSucceeded v1
```

---

# 33. Event Type Naming

Convention recommandée :

```text
<namespace>.<context>.<event_name>
```

Exemple :

```text
pyagentskit.effects.effect_succeeded
pyagentskit.execution.run_waiting
```

---

# 34. Public vs Internal Events

Tous les DomainEvents ne deviennent pas publics.

Classification :

```text
INTERNAL
INTEGRATION
PUBLIC
```

---

# 35. INTERNAL

Utilisé à l’intérieur du même process/context.

---

# 36. INTEGRATION

Utilisé entre bounded contexts ou services PyAgentsKit.

---

# 37. PUBLIC

Contract externe supporté/documenté.

---

# 38. Avoid Event Explosion

Ne pas publier chaque micro-transition.

Publier les faits réellement utiles.

---

# 39. Event Granularity

Bon :

```text
EffectBecameUnknown
```

Moins bon :

```text
EffectFieldStatusChanged
```

---

# 40. Domain Event Collection

Un aggregate peut accumuler temporairement :

```text
pending_domain_events
```

pendant une transaction.

---

# 41. Aggregate Pattern

Concept :

```python
aggregate.raise_event(...)
```

L’événement est ensuite collecté par l’Application/UnitOfWork.

---

# 42. Domain Does Not Publish

Le Domain :

```text
creates facts
```

Il ne doit pas :

```text
call broker
call webhook
call Kafka producer
```

---

# 43. UnitOfWork Responsibility

Le UnitOfWork peut collecter les DomainEvents produits par les aggregates modifiés.

---

# 44. Local Domain Dispatch

Certains DomainEvents peuvent déclencher des handlers internes dans la même transaction ou juste après commit selon besoin.

---

# 45. Transactional Handler Rule

Un handler exécuté avant commit doit :

```text
remain local
remain deterministic
avoid remote I/O
```

---

# 46. Post-Commit Handler Rule

Les actions externes doivent se faire :

```text
after durable commit
```

---

# 47. The Dual-Write Problem

Sans Outbox :

```text
1. commit DB
2. publish broker
```

peut échouer entre 1 et 2.

Inversement :

```text
1. publish broker
2. commit DB
```

peut publier un événement correspondant à une transaction finalement rollbackée.

---

# 48. Outbox Pattern

Solution :

```text
same local transaction:
  persist domain state
  persist outbox event
commit

then:
  publish outbox asynchronously
```

---

# 49. Core Outbox Invariant

```text
Domain state and Outbox record commit atomically.
```

---

# 50. Why No Distributed Transaction

PyAgentsKit ne doit pas exiger :

```text
2PC
XA transaction
distributed DB+broker commit
```

---

# 51. OutboxRecord

Objet technique.

Champs proposés :

```text
id
tenant_id
event_id
event_type
event_version
payload
headers
created_at
available_at
published_at
attempt_count
last_error
status
partition_key
sequence
```

---

# 52. Outbox Status

Proposition :

```text
PENDING
CLAIMED
PUBLISHED
FAILED
DEAD_LETTER
```

---

# 53. PENDING

Événement prêt ou bientôt prêt à publier.

---

# 54. CLAIMED

Pris temporairement par un publisher.

---

# 55. PUBLISHED

Publication confirmée selon le transport.

---

# 56. FAILED

Tentative échouée mais retryable.

---

# 57. DEAD_LETTER

Événement non publiable automatiquement après budget de retries.

---

# 58. Outbox Claim

Plusieurs publishers peuvent fonctionner en parallèle.

Un mécanisme de claim évite du travail inutilement dupliqué.

---

# 59. Claim != Exactly Once

Même avec claim, un publisher peut :

```text
send
crash before mark PUBLISHED
```

Le broker peut donc recevoir le message deux fois.

---

# 60. Outbox Delivery Semantics

Le modèle cible suppose :

```text
at-least-once publication
```

avec deduplication côté consumer.

---

# 61. No Exactly-Once Claim

PyAgentsKit ne doit pas promettre :

```text
exactly-once message delivery
```

de manière générale.

---

# 62. Publish Crash Window

```text
W-O1 claim
W-O2 send
W-O3 broker accepts
W-O4 publisher crashes before mark published
```

Après recovery :

```text
message may be sent again
```

---

# 63. Inbox Pattern

L’Inbox protège le consumer contre les redeliveries.

---

# 64. InboxRecord

Champs proposés :

```text
message_id
tenant_id
consumer_name
event_type
payload_digest
received_at
processed_at
status
attempt_count
last_error
```

---

# 65. Inbox Status

```text
RECEIVED
PROCESSING
PROCESSED
FAILED
DEAD_LETTER
```

---

# 66. Inbox Dedup Key

Typiquement :

```text
consumer_name + message_id
```

unique.

---

# 67. Why Consumer Name

Le même IntegrationEvent peut être traité légitimement par plusieurs consumers.

---

# 68. Inbox Duplicate Delivery

Si :

```text
same message_id
same payload_digest
```

le consumer doit reconnaître le doublon.

---

# 69. Inbox Payload Conflict

Si :

```text
same message_id
different payload_digest
```

alors :

```text
hard conflict
```

et potentiellement incident.

---

# 70. Inbox Atomicity

Le traitement métier doit idéalement être atomique avec :

```text
mark Inbox PROCESSED
```

dans la même transaction locale.

---

# 71. Consumer Transaction Pattern

```text
BEGIN
insert inbox record if absent
apply local domain changes
mark inbox processed
COMMIT
```

---

# 72. Consumer Crash Before Commit

Tout rollback.

Message pourra être redélivré.

---

# 73. Consumer Crash After Commit Before Ack

Broker peut redélivrer.

Inbox reconnaît :

```text
already processed
```

---

# 74. Inbox Is Not Effect Idempotency

Inbox répond à :

```text
Have I already consumed this message?
```

Effect idempotency répond à :

```text
Has this real-world action already been logically attempted/applied?
```

---

# 75. EventPublisher Port

Outbound port :

```python
class EventPublisher(Protocol):
    async def publish(self, event: IntegrationEvent) -> None:
        ...
```

---

# 76. Outbox Publisher

Composant applicatif/adapter :

```text
OutboxStore
→ EventPublisher
```

---

# 77. Publisher Loop

```text
claim batch
→ publish each
→ mark published
→ retry failures
```

---

# 78. Publisher Is Not Domain

Le publisher appartient :

```text
Application / Adapter / Operations
```

selon package final.

---

# 79. OutboxStore Port

Doit supporter :

```text
append
claim
mark_published
mark_failed
release/expire claim
```

---

# 80. InboxStore Port

Doit supporter :

```text
register/try_begin
mark_processed
mark_failed
lookup
```

---

# 81. Ordering

L’ordering global n’est pas garanti.

---

# 82. Aggregate Ordering

PyAgentsKit peut garantir un ordering logique par aggregate via :

```text
aggregate_version
sequence
partition_key
```

---

# 83. Partition Key

Souvent :

```text
aggregate_id
```

ou :

```text
tenant_id + aggregate_id
```

---

# 84. Ordering Guarantee Scope

Documenter précisément :

```text
per aggregate
per partition
or none
```

---

# 85. No Global Total Order

Éviter toute promesse :

```text
all PyAgentsKit events have a global total order
```

---

# 86. Sequence

Un `sequence` local peut être monotone par aggregate/outbox stream.

---

# 87. Out-of-Order Delivery

Consumers doivent être capables de détecter :

```text
aggregate_version gap
```

si ordering requis.

---

# 88. Handling Gaps

Possibles :

```text
wait for missing version
re-read authoritative state
ignore obsolete event
rebuild projection
```

selon consumer.

---

# 89. Read Models

IntegrationEvents peuvent alimenter :

```text
CQRS-light read models
```

---

# 90. Read Model Consistency

Les projections sont :

```text
eventually consistent
```

---

# 91. Read Model Is Not Authority

Un read model ne doit pas décider :

```text
Effect safety
Approval validity
Lease ownership
```

---

# 92. Broker Role

Le broker est optionnel.

Exemples :

```text
Kafka
RabbitMQ
NATS
SQS
Service Bus
Redis Streams
```

---

# 93. Broker Is Transport

Le broker ne devient pas :

```text
source of truth
```

---

# 94. Broker Delivery != Ownership

Recevoir un message :

```text
RecoverRun(run_id)
```

ne donne pas automatiquement le droit d’agir.

Le worker doit encore :

```text
acquire/validate Lease
```

---

# 95. Queue Delivery != Lease

Invariant fondamental.

---

# 96. Message Visibility Timeout

Un visibility timeout de queue n’est pas :

```text
Run lease TTL
```

---

# 97. Why

Les deux scopes sont différents :

```text
message processing
vs
business execution ownership
```

---

# 98. Event-Driven Recovery

IntegrationEvents peuvent déclencher :

```text
RecoverRun
```

sur :

```text
ApprovalApproved
LeaseExpired
ReconciliationResolved
RuntimeFailed
```

---

# 99. But Recovery Remains State-Driven

Le message est un trigger.

Le `RecoveryPlanner` relit l’état durable et décide.

---

# 100. Missed Events

Un événement perdu/retardé ne doit pas rendre le système irrécupérable.

---

# 101. Recovery Scanner

Un scan périodique peut retrouver les Runs éligibles.

---

# 102. Hybrid Trigger Model

Recommandation :

```text
events for responsiveness
+
periodic scans for completeness
```

---

# 103. Domain Event Examples — Execution

```text
RunCreated
RunStarted
RunWaiting
RunPaused
RunResumed
RunSucceeded
RunFailed
RunCancelled
```

---

# 104. Domain Event Examples — Effects

```text
EffectPlanned
EffectStarted
EffectSucceeded
EffectFailed
EffectBecameUnknown
EffectReconciliationRequested
EffectReconciled
```

---

# 105. Domain Event Examples — Governance

```text
ApprovalRequested
ApprovalApproved
ApprovalRejected
ApprovalExpired
ApprovalCancelled
```

---

# 106. Domain Event Examples — Coordination

```text
LeaseAcquired
LeaseRenewed
LeaseExpired
LeaseReleased
LeaseTakenOver
StaleFencingRejected
```

---

# 107. Domain Event Examples — Runtime Integration

Runtime-specific facts that become DomainEvents only if meaningful:

```text
RuntimeInvocationStarted
RuntimeInvocationWaiting
RuntimeInvocationCompleted
RuntimeInvocationFailed
```

---

# 108. Domain Event Examples — Conversations

```text
ConversationCreated
ParticipantAdded
MessageAppended
```

---

# 109. Domain Event Examples — Artifacts

```text
ArtifactRegistered
ArtifactVerified
ArtifactInvalidated
```

---

# 110. Integration Event Selection

Ne pas publier tous les DomainEvents.

Exemple :

```text
LeaseRenewed
```

peut être trop fréquent pour external consumers.

---

# 111. Event Noise Control

Préférer publication sur :

```text
meaningful state changes
```

---

# 112. Internal Event Handlers

Exemple :

```text
ApprovalApproved
→ mark Run eligible for recovery
```

---

# 113. Avoid Hidden Workflows

Les handlers ne doivent pas devenir un workflow engine implicite.

---

# 114. Rule

Si une orchestration devient complexe :

```text
make it an Application Use Case
```

plutôt qu’une chaîne opaque de handlers.

---

# 115. Synchronous Domain Handlers

À utiliser pour :

```text
local invariant-preserving reactions
```

---

# 116. Asynchronous Integration Handlers

À utiliser pour :

```text
cross-context/process propagation
```

---

# 117. Eventual Consistency

Consumers inter-contextes doivent accepter qu’un event arrive :

```text
later
more than once
out of order
```

selon transport.

---

# 118. Idempotent Consumers

Un consumer IntegrationEvent doit être conçu :

```text
idempotent
```

ou protégé par Inbox.

---

# 119. Consumer Business Idempotency

Même avec Inbox, une opération externe déclenchée doit encore utiliser :

```text
Effect idempotency
```

---

# 120. Example — Event Triggers Email

```text
RunSucceeded event
→ notification consumer
→ send email
```

L’envoi email doit être :

```text
Effect
```

dans le consumer approprié si PyAgentsKit le gouverne.

---

# 121. Message Schema

JSON est un bon format initial.

---

# 122. Serialization Rules

```text
UTF-8
stable field names
explicit timestamps
explicit enums
no Python class names
```

---

# 123. Timestamp Format

Recommandation :

```text
RFC 3339 / ISO 8601 UTC
```

---

# 124. UUID Representation

String canonique.

---

# 125. Enum Representation

Valeurs string stables.

---

# 126. Unknown Fields

Consumers doivent idéalement ignorer les champs additionnels non breaking.

---

# 127. Required Field Removal

Breaking change.

---

# 128. Event Evolution

Patterns :

```text
add optional field
publish new version
support dual readers
```

---

# 129. Producer Compatibility

Nouveau producer peut publier v1 ou v2 selon phase de migration.

---

# 130. Consumer Compatibility

Un consumer doit annoncer les versions acceptées.

---

# 131. Event Schema Registry

Pas nécessaire de construire un registry service.

Un dossier de schemas versionnés peut suffire.

---

# 132. Potential Layout

```text
contracts/events/
  execution/
  effects/
  governance/
```

---

# 133. Pydantic Models

Peuvent définir les wire contracts.

Mais éviter de lier le Domain directement aux modèles externes.

---

# 134. Domain-to-Integration Mapper

Composant :

```text
IntegrationEventMapper
```

ou handlers explicites.

---

# 135. No Generic Reflection Magic

Préférer mapping explicite pour événements publics critiques.

---

# 136. Why

Permet :

```text
schema control
data minimization
versioning
```

---

# 137. Outbox Persistence

Table :

```text
outbox_events
```

---

# 138. Suggested Columns

```text
id UUID PK
tenant_id
event_id UNIQUE
event_type
event_version
aggregate_type
aggregate_id
aggregate_version
partition_key
payload JSONB
headers JSONB
status
attempt_count
available_at
claimed_by
claim_expires_at
created_at
published_at
last_error
```

---

# 139. Outbox Unique Constraint

```text
event_id
```

unique.

---

# 140. Outbox Tenant Scope

Queries doivent inclure tenant lorsque nécessaire.

---

# 141. Outbox Claim with PostgreSQL

Pattern possible :

```sql
SELECT ...
FOR UPDATE SKIP LOCKED
LIMIT N
```

---

# 142. SKIP LOCKED Semantics

C’est un mécanisme de distribution de travail.

Ce n’est pas :

```text
exactly-once publication
```

---

# 143. Claim Timeout

Si publisher meurt :

```text
claim expires
record becomes eligible again
```

---

# 144. Publisher Identity

Stocker éventuellement :

```text
claimed_by
```

pour diagnostics.

---

# 145. Retry Policy

Peut utiliser :

```text
exponential backoff
jitter
max attempts
```

---

# 146. Retryable Errors

Exemples :

```text
network timeout
broker unavailable
rate limit
```

---

# 147. Non-Retryable Errors

Exemples :

```text
invalid schema
serialization failure
unsupported destination
```

peuvent aller plus vite vers dead letter.

---

# 148. Poison Message

Un record systématiquement non publiable est un :

```text
poison message
```

---

# 149. Dead Letter Handling

Doit :

```text
preserve payload
preserve error
surface alert
allow operator inspection
```

---

# 150. Dead Letter Is Not Deletion

Jamais supprimer silencieusement.

---

# 151. Replay Dead Letter

Use case administré :

```text
requeue
```

après correction.

---

# 152. Requeue Audit

Toute requeue manuelle doit être auditable.

---

# 153. Inbox Persistence

Table :

```text
inbox_events
```

---

# 154. Suggested Inbox Columns

```text
id UUID PK
tenant_id
consumer_name
message_id
event_type
event_version
payload_digest
status
received_at
processed_at
attempt_count
last_error
```

---

# 155. Inbox Unique Constraint

```text
UNIQUE(tenant_id, consumer_name, message_id)
```

selon scope.

---

# 156. Payload Digest

Permet de détecter :

```text
same ID, different body
```

---

# 157. Processing Claim

Si plusieurs consumer workers :

```text
claim/lock
```

peut être utilisé.

---

# 158. Consumer Retry

Si traitement local rollback :

```text
redelivery or retry
```

est acceptable.

---

# 159. External Effect from Consumer

Si consumer appelle un système externe :

```text
Inbox does not replace Effect model
```

---

# 160. Event Publishing Transaction Boundary

Pattern correct :

```text
BEGIN
load aggregate
apply domain transition
save aggregate
append outbox record
COMMIT
```

---

# 161. Wrong Pattern

```text
BEGIN
save aggregate
publish broker
COMMIT
```

---

# 162. Why Wrong

Broker may accept while transaction rolls back.

---

# 163. Wrong Pattern 2

```text
save aggregate
COMMIT
publish broker without Outbox
```

---

# 164. Why Wrong 2

Crash after commit loses propagation.

---

# 165. Outbox and UnitOfWork

Le UnitOfWork V2 doit permettre :

```text
repositories
+
outbox
```

dans la même transaction locale.

---

# 166. DomainEvent Extraction

Avant commit ou pendant UnitOfWork :

```text
collect events
map to outbox
save atomically
```

---

# 167. When To Clear Pending Events

Seulement après succès du commit.

---

# 168. Commit Failure

Les pending events ne doivent pas être considérés publiés.

---

# 169. Aggregate Save Failure

Outbox insert rollback également.

---

# 170. Audit + Outbox

Audit critique et Domain state peuvent aussi nécessiter même transaction locale selon profile.

---

# 171. High Assurance Profile

Peut imposer :

```text
domain mutation
+
audit append
+
outbox append
```

atomiques localement.

---

# 172. Audit Failure Semantics

Selon profile standard :

```text
some operations may continue
```

High Assurance :

```text
protected mutation may fail closed
```

---

# 173. Outbox Backlog

Un broker outage crée :

```text
growing PENDING backlog
```

---

# 174. Core Domain May Continue

Si la publication n’est pas nécessaire à la sûreté immédiate :

```text
yes
```

jusqu’aux limites de backlog/policy.

---

# 175. Backlog Limits

Définir :

```text
max age
max rows
max bytes
```

pour alerting/capacity.

---

# 176. Backpressure

Si Outbox explose, le système peut entrer en :

```text
DEGRADED
```

ou bloquer certaines nouvelles actions selon criticité.

---

# 177. Event Criticality

Classification possible :

```text
NON_CRITICAL
IMPORTANT
SAFETY_CRITICAL
```

---

# 178. Safety-Critical Propagation

Exemple :

```text
central policy service must receive revocation
```

peut nécessiter traitement plus strict.

---

# 179. But Source of Truth Remains Local

Même alors, publication failure ne change pas rétroactivement le fait métier déjà commit.

---

# 180. Inbox Backlog

Un consumer outage accumule des messages chez broker.

---

# 181. Catch-Up

Le consumer reprend avec Inbox dedup.

---

# 182. Reprocessing

Il peut être nécessaire de reconstruire un read model.

---

# 183. Projection Rebuild

Peut repartir depuis :

```text
authoritative DB
event archive
```

selon architecture.

---

# 184. Outbox Is Not Event Sourcing

PyAgentsKit V2 ne devient pas event-sourced simplement parce qu’il stocke des DomainEvents/Outbox.

---

# 185. Source of Truth

Le modèle reste principalement :

```text
state-oriented aggregates in PostgreSQL
```

avec events pour propagation/audit.

---

# 186. Event Sourcing Future

Possible pour certains contexts si justification claire.

Non-goal initial.

---

# 187. Domain Event Retention

Les DomainEvents pending peuvent être éphémères en mémoire avant commit.

---

# 188. Outbox Retention

Les records PUBLISHED peuvent être purgés après période définie.

---

# 189. Inbox Retention

Les dedup records doivent être conservés assez longtemps pour couvrir :

```text
maximum redelivery window
```

---

# 190. Long-Term Event Archive

Optionnel.

---

# 191. Purge Safety

Ne pas supprimer Inbox trop tôt si broker peut redélivrer longtemps après.

---

# 192. Retention Policy Fields

```text
retention_days
redelivery_window
archive_required
```

---

# 193. Observability — Outbox Metrics

```text
outbox_pending_total
outbox_published_total
outbox_failed_total
outbox_dead_letter_total
outbox_oldest_age_seconds
outbox_publish_latency_seconds
```

---

# 194. Observability — Inbox Metrics

```text
inbox_received_total
inbox_duplicate_total
inbox_processed_total
inbox_failed_total
inbox_conflict_total
```

---

# 195. Observability — Event Metrics

```text
integration_events_published_total
integration_events_consumed_total
```

Labels faibles cardinalité :

```text
event_type
consumer
status
```

---

# 196. Avoid High Cardinality

Ne pas utiliser :

```text
event_id
aggregate_id
tenant_id
```

comme labels globaux sauf cas maîtrisé.

---

# 197. Outbox Alerts

```text
oldest pending too old
dead letter > 0
publish error spike
backlog growth
```

---

# 198. Inbox Alerts

```text
conflict detected
processing failure spike
consumer lag
```

---

# 199. Tracing

Span possible :

```text
outbox.publish
inbox.consume
integration.handle
```

---

# 200. Trace Correlation

Utiliser :

```text
correlation_id
```

dans baggage/attributes si acceptable.

---

# 201. Security — Event Payloads

Events ne doivent pas contenir :

```text
access tokens
resolved secrets
passwords
private keys
```

---

# 202. Data Minimization

Publier seulement les champs nécessaires.

---

# 203. PII

Si événement contient PII :

```text
DataPolicy
retention
access controls
```

doivent s’appliquer.

---

# 204. Tenant Isolation

Chaque consumer doit valider :

```text
tenant scope
```

avant mutation.

---

# 205. Forged Event

Un message externe ne devient pas automatiquement trusted DomainEvent.

---

# 206. Integration Boundary

Inbound message :

```text
validate authenticity
validate schema
map to command/input
```

---

# 207. Signed Webhooks

Si une IntegrationEvent vient d’un webhook provider :

```text
signature verification
```

est requise si supportée.

---

# 208. Internal Broker Security

Utiliser :

```text
TLS
authentication
ACLs
```

selon infrastructure.

---

# 209. Event Authentication != Business Authorization

Un message authentique peut quand même être :

```text
unauthorized for requested action
```

---

# 210. Integration Event Consumer

Le consumer passe par :

```text
Application Service
```

et ne mutate pas directement un aggregate hors règles.

---

# 211. Cross-Context Communication

Préférer :

```text
published language
```

défini par contracts publics/inter-contextes.

---

# 212. Shared Database Anti-Pattern

Deux contexts ne doivent pas :

```text
query each other's tables
```

pour business logic à la place d’un Port/event explicite.

---

# 213. Events vs Direct Ports

Utiliser un appel direct Port lorsque :

```text
immediate response required
same consistency boundary
```

Utiliser event lorsque :

```text
decoupling
asynchrony
fan-out
eventual consistency
```

sont souhaités.

---

# 214. Decision Rule

Ne pas utiliser un event uniquement parce que :

```text
"microservices best practice"
```

---

# 215. Example — Approval Approved

Governance émet :

```text
ApprovalApproved
```

Execution peut utiliser cet event comme trigger pour :

```text
RecoverRun
```

mais relit ensuite ApprovalRepository.

---

# 216. Important

Le consumer ne doit pas considérer le payload de l’event comme la seule source de vérité pour une décision safety-critical.

---

# 217. Why

Event peut être :

```text
stale
duplicated
delayed
```

---

# 218. Example — Lease Expired

Event :

```text
LeaseExpired
```

peut déclencher scan/recovery.

Mais le worker doit vérifier la base avant takeover.

---

# 219. Example — Effect Reconciled

Event :

```text
EffectReconciled
```

déclenche recovery.

RecoveryPlanner relit l’Effect.

---

# 220. Example — Runtime Completed

Event :

```text
RuntimeInvocationCompleted
```

ne signifie pas :

```text
RunSucceeded
```

L’Application vérifie les blockers.

---

# 221. Event Idempotency

Produire deux fois le même DomainEvent logique peut être évité via :

```text
aggregate version
transition uniqueness
event_id persistence
```

---

# 222. Outbox Idempotency

`event_id` unique empêche insertion du même event deux fois dans certaines flows.

---

# 223. Publisher Duplicate

Le même outbox record peut être envoyé deux fois.

Inbox gère.

---

# 224. Event Generation Location

Les DomainEvents sont idéalement générés au moment où l’aggregate accepte la transition.

---

# 225. Application-Generated Events

Acceptables pour faits purement applicatifs :

```text
RuntimeSelected
MigrationCompleted
```

---

# 226. Technical Events

Certains événements purement techniques ne sont pas DomainEvents.

Exemples :

```text
WorkerHeartbeatMissed
DBPoolSaturated
```

peuvent être Ops/Telemetry events.

---

# 227. Event Taxonomy

```text
Domain
Integration
Runtime
Audit
Operational
Telemetry
```

Ne pas tout fusionner.

---

# 228. Event Storage

Tous les event types n’ont pas besoin du même store.

---

# 229. Domain/Integration

Outbox.

---

# 230. Audit

AuditStore.

---

# 231. Runtime

Runtime event stream / optional persistence.

---

# 232. Telemetry

Observability backend.

---

# 233. Operational

Logs/metrics/events selon usage.

---

# 234. Outbox Event Mapper

Le mapper peut transformer :

```text
DomainEvent
→ IntegrationEvent
```

en supprimant les données privées/non nécessaires.

---

# 235. Schema Example

DomainEvent :

```text
EffectSucceeded(
    effect_id,
    run_id,
    full internal metadata
)
```

IntegrationEvent :

```text
EffectSucceededV1(
    effect_id,
    run_id,
    effect_type,
    occurred_at
)
```

---

# 236. IntegrationEvent Does Not Expose Secrets

Même si DomainEvent interne référence des metadata sensibles.

---

# 237. Versioned Mapper

Mapper explicite par event version.

---

# 238. Event Compatibility Tests

Document 39 doit couvrir :

```text
serialization
required fields
unknown fields
event version
```

---

# 239. Golden Schema Tests

Pertinents pour IntegrationEvents publics.

---

# 240. Contract Test IDs

Exemples :

```text
CT-EVT-001
CT-OUTBOX-001
CT-INBOX-001
```

---

# 241. Outbox Contract Tests

Obligatoires :

```text
append
atomic commit
claim
mark published
retry
claim expiry
duplicate publish tolerance
```

---

# 242. Inbox Contract Tests

Obligatoires :

```text
first delivery
duplicate same digest
duplicate conflicting digest
transaction rollback
processed replay
```

---

# 243. Failure Tests — Outbox

```text
publisher crash before send
publisher crash after send
broker timeout
broker ack lost
DB unavailable when marking published
```

---

# 244. Failure Tests — Inbox

```text
consumer crash before DB commit
consumer crash after commit before broker ack
duplicate redelivery
payload conflict
```

---

# 245. Production Qualification

Doit démontrer :

```text
broker outage
publisher restart
consumer restart
duplicate delivery
poison message
backlog recovery
```

---

# 246. No Broker Required

PyAgentsKit core doit pouvoir fonctionner :

```text
without external broker
```

pour single-process/local profiles.

---

# 247. Local EventPublisher

Possibilité :

```text
InProcessEventPublisher
```

pour dev/tests.

---

# 248. In-Process Warning

Il ne fournit pas :

```text
cross-process durability
```

---

# 249. Database Polling Outbox

Peut suffire en production initiale :

```text
PostgreSQL outbox
+
publisher worker
```

sans Kafka.

---

# 250. Broker Adoption

À introduire seulement si :

```text
throughput
fan-out
decoupling
```

le justifient.

---

# 251. Build vs Buy

PyAgentsKit doit :

```text
build event semantics
build Outbox/Inbox ports
integrate existing brokers
```

et non construire un broker.

---

# 252. Package Topology

Proposition :

```text
domain/
  shared/
    events.py

application/
  messaging/
    dispatch_domain_events.py
    publish_outbox.py
    consume_inbox.py

adapters/
  persistence/
    outbox/
    inbox/
  messaging/
    inprocess/
    kafka/
    rabbitmq/
    ...
```

---

# 253. Alternative Context Placement

Les DomainEvents spécifiques restent près de leur bounded context.

Exemple :

```text
domain/effects/events.py
domain/execution/events.py
```

---

# 254. Shared Event Envelope

Peut vivre dans :

```text
contracts/events
```

ou Shared Kernel minimal.

---

# 255. Dependency Rule

Domain contexts peuvent dépendre d’une abstraction minimale :

```text
DomainEvent base/value objects
```

pas d’un broker adapter.

---

# 256. No Adapter Imports in Domain

Invariant.

---

# 257. Event Handler Placement

Handlers inter-contextes :

```text
application/
```

plutôt que Domain externe.

---

# 258. Outbox Publisher Placement

Adapter/application service.

---

# 259. Inbox Consumer Placement

Inbound adapter + Application Service.

---

# 260. Idempotent Consumer Pattern

```text
receive event
→ inbox try_begin
→ already processed?
   yes → ack
   no → execute Application use case
→ commit local state + inbox processed
→ ack
```

---

# 261. Ack Timing

Ack broker :

```text
after local commit
```

---

# 262. Early Ack Anti-Pattern

Ack avant commit peut perdre le message.

---

# 263. Late Ack Consequence

Peut causer redelivery.

Inbox protège.

---

# 264. Dead Letter Queue

Broker DLQ peut compléter :

```text
Inbox DEAD_LETTER
```

mais ne remplace pas l’état local.

---

# 265. DLQ Is Transport-Level

Inbox dead-letter est application-level.

---

# 266. Poison Event Investigation

Doit capturer :

```text
message_id
event_type
schema version
consumer
error
attempts
```

---

# 267. Schema Incompatibility

Si consumer reçoit version inconnue :

```text
reject/dead-letter
```

avec alert.

---

# 268. Forward Compatibility

Si event version compatible et seulement champs optionnels ajoutés :

```text
consume normally
```

---

# 269. Backward Compatibility

Pendant rolling upgrade, N and N+1 consumers peuvent coexister.

---

# 270. Event Contract Freeze

Avant `2.0.0rc1`, les IntegrationEvents publics P0 doivent être gelés.

---

# 271. Migration V1 → V2

V1 possède déjà des EventType internes.

Ils ne doivent pas être automatiquement déclarés comme DomainEvents/IntegrationEvents V2.

---

# 272. Existing EventType Set

V1 a un set historique de core events.

V2 doit les classifier :

```text
runtime
domain
audit
telemetry
legacy
```

---

# 273. Migration Rule

Ne pas préserver un event legacy comme public uniquement pour éviter un changement interne.

---

# 274. Compatibility Layer

`compat.v1` peut continuer d’émettre/mapper certains événements legacy.

---

# 275. V2 Event Model Independent

Le Domain V2 ne dépend pas du legacy EventType.

---

# 276. Legacy Event Mapping

Créer un mapping explicite si nécessaire.

---

# 277. Outbox Migration

Les données V1 existantes n’ont pas nécessairement besoin d’être rétroactivement transformées en Outbox records.

---

# 278. Migration Cutover

À partir du cutover :

```text
new V2 domain mutation
→ outbox atomically
```

---

# 279. Dual Publishing

Pendant migration, dual publishing peut être utilisé temporairement.

---

# 280. Dual Publishing Risk

Peut créer :

```text
duplicates
inconsistent schemas
```

Doit être borné et instrumenté.

---

# 281. Prefer Single Canonical Publisher

Une fois cutover terminé.

---

# 282. Restore / PITR

Restore DB peut faire réapparaître :

```text
PENDING outbox
PROCESSED inbox entries missing
```

selon point de restauration.

---

# 283. Restore Safety

Cela peut provoquer redelivery/republication.

---

# 284. Effect Safety Remains Separate

Même si event redelivered, un external write doit encore être protégé par :

```text
Effect idempotency/reconciliation
```

---

# 285. Inbox After Restore

Si Inbox record a disparu mais external Effect a déjà eu lieu :

```text
Effect model
```

doit empêcher double conséquence.

---

# 286. Restore Rule

```text
Outbox/Inbox restoration
does not prove external world rolled back
```

---

# 287. Runbook Implication

Le document 42 doit prévoir :

```text
Outbox backlog
Inbox conflict
restore redelivery
poison messages
```

---

# 288. Operational Modes

En mode :

```text
NO_PROTECTED_EFFECTS
```

Outbox publication d’événements purement informationnels peut continuer selon policy.

---

# 289. Maintenance Mode

Publisher/consumer peuvent être :

```text
drained
paused
resumed
```

---

# 290. Graceful Shutdown — Publisher

Séquence :

```text
stop claiming
finish bounded sends
release claims
close broker
```

---

# 291. Graceful Shutdown — Consumer

```text
stop receiving
finish/rollback in-flight local transactions
ack only committed
```

---

# 292. Scaling Out Publishers

Safe avec claim + duplicate tolerance.

---

# 293. Scaling Out Consumers

Safe avec Inbox + broker partition semantics.

---

# 294. Performance Model

Dimensions :

```text
outbox inserts/sec
publish/sec
consumer/sec
payload bytes/sec
backlog age
```

---

# 295. Outbox Insert Cost

Doit rester faible et dans transaction locale.

---

# 296. Large Payload Anti-Pattern

Ne pas mettre gros artifacts dans event payload.

---

# 297. Artifact Reference

Publier :

```text
artifact_id
```

ou blob reference contrôlée.

---

# 298. Payload Size Limit

À définir par transport/profile.

---

# 299. Compression

Adapter-level si nécessaire.

Pas Domain concern.

---

# 300. Event Fan-Out

Un IntegrationEvent peut avoir plusieurs consumers.

Chacun possède :

```text
its own Inbox identity
```

---

# 301. Consumer Independence

Le succès consumer A ne signifie pas succès consumer B.

---

# 302. Event Replay

Peut être utile pour :

```text
read-model rebuild
reprocessing
```

mais doit être explicite.

---

# 303. Replay and Effects

Un replay d’IntegrationEvents ne doit jamais provoquer involontairement :

```text
duplicate external Effects
```

---

# 304. Replay Mode

Consumers à effets externes doivent :

```text
disable side effects
or
rely on durable Effect idempotency
```

selon use case.

---

# 305. Event Archive Replay

Doit être marqué :

```text
replay=true
```

dans metadata si utile.

---

# 306. Audit of Replay

Replays administratifs importants sont audités.

---

# 307. Event Causality

Correlation/causation servent à reconstruire :

```text
Command
→ DomainEvent
→ IntegrationEvent
→ Consumer Command
→ DomainEvent
```

---

# 308. No Causal Loop

Les handlers doivent éviter boucle infinie :

```text
A event → B event → A event ...
```

---

# 309. Loop Detection

Peut utiliser :

```text
causation chain
hop count
```

si architecture le nécessite.

---

# 310. Initial Recommendation

Ne pas introduire moteur générique de boucle.

Gardez les flows explicites.

---

# 311. Event Handler Retry

Retry du handler local est distinct de :

```text
Effect retry
```

---

# 312. Handler Failure

Si consumer transaction échoue :

```text
message stays unprocessed
```

---

# 313. Handler Poison Failure

Après budget :

```text
dead-letter
manual intervention
```

---

# 314. Manual Reprocessing

Doit préserver :

```text
message_id
```

pour dedup semantics.

---

# 315. New Corrected Message

Si payload doit changer :

```text
new message_id
new event
```

pas mutation du précédent.

---

# 316. Domain Event Evolution Policy

Ajouter un champ interne peut être simple.

IntegrationEvent public exige review de compatibilité.

---

# 317. ADR Requirement

Tout changement majeur de messaging semantics P0 doit produire :

```text
ADR
```

---

# 318. Event Governance

Pour chaque event public :

```text
owner
schema
version
consumers
retention
compatibility policy
```

---

# 319. Event Catalog

Maintenir un catalogue documentaire.

---

# 320. Event Catalog Entry

Exemple :

```text
Name: pyagentskit.effects.effect_succeeded
Version: 1
Owner: Effects
Scope: Integration
Ordering: per Effect aggregate
Payload: ...
Consumers: ...
```

---

# 321. P0 Integration Events

Probables :

```text
EffectBecameUnknown
EffectReconciled
ApprovalApproved
ApprovalRejected
RunWaiting
RunSucceeded
LeaseTakenOver
```

selon architecture finale.

---

# 322. Avoid Publishing Secrets by Convenience

Jamais :

```text
full Run snapshot
full SecurityContext
full provider response
```

par défaut.

---

# 323. Snapshot Event Anti-Pattern

Des events énormes couplent fortement producers/consumers.

---

# 324. Thin Event Principle

Publier :

```text
identity
state change
minimal evidence
```

et laisser consumer relire via Port si nécessaire.

---

# 325. But Avoid Mandatory Cross-DB Reads

Consumer d’un autre service ne doit pas lire directement les tables du producer.

Utiliser API/Port public ou payload suffisant.

---

# 326. Event Payload Balance

Assez de données pour éviter couplage excessif.

Pas assez pour fuiter tout le Domain.

---

# 327. DomainEvent Handler Ordering

Si plusieurs handlers synchrones :

```text
ordering must be explicit
```

ou éviter dépendance à l’ordre.

---

# 328. Prefer Independent Handlers

Réduit coupling.

---

# 329. Failure of Non-Critical Handler

Ne doit pas forcément rollback une mutation métier si handler peut passer en async Outbox.

---

# 330. Critical Local Handler

S’il fait partie de l’invariant :

```text
execute in same transaction
```

---

# 331. Example — Run Waiting

`EffectBecameUnknown` peut conduire localement à :

```text
Run WAITING
```

si orchestré par application dans même use case.

Ne pas nécessairement utiliser async event pour une invariance immédiate.

---

# 332. Event as Notification, Not Invariant Mechanism

Les invariants critiques doivent être garantis par transaction/application logic, pas par eventual event delivery.

---

# 333. Core Messaging Invariants

```text
EVT-INV-01 DomainEvent != IntegrationEvent.
EVT-INV-02 RuntimeEvent != DomainEvent.
EVT-INV-03 AuditEvent != DomainEvent.
EVT-INV-04 Domain never publishes directly to broker.
EVT-INV-05 Domain mutation and Outbox append are atomic locally.
EVT-INV-06 Outbox delivery is at-least-once by default.
EVT-INV-07 Consumers are idempotent or Inbox-protected.
EVT-INV-08 Broker delivery does not grant Run ownership.
EVT-INV-09 Inbox dedup does not replace Effect idempotency.
EVT-INV-10 Public event schemas are versioned.
EVT-INV-11 Safety-critical consumers re-read authoritative state when required.
EVT-INV-12 Read models are not safety authority.
EVT-INV-13 Poison messages are surfaced, never silently dropped.
EVT-INV-14 Restore/PITR may cause redelivery and must remain safe.
EVT-INV-15 Event payloads contain no resolved secrets.
```

---

# 334. Anti-Pattern — Publish Inside Aggregate

Interdit.

---

# 335. Anti-Pattern — Broker as Transaction Coordinator

Interdit.

---

# 336. Anti-Pattern — Exactly-Once Marketing Claim

Interdit sans scope extrêmement précis et prouvé.

---

# 337. Anti-Pattern — Queue Message Means Ownership

Interdit.

---

# 338. Anti-Pattern — Inbox Means Effect Safe

Interdit.

---

# 339. Anti-Pattern — Event Payload as Safety Authority

Interdit pour données susceptibles d’être stale.

---

# 340. Anti-Pattern — Same Class for All Event Types

Évite de mélanger :

```text
RuntimeEvent
AuditEvent
DomainEvent
IntegrationEvent
```

---

# 341. Anti-Pattern — Infinite Event Chains

Éviter orchestration cachée.

---

# 342. Anti-Pattern — Shared DB Consumer

Un consumer cross-context ne doit pas bypass l’interface publiée.

---

# 343. Anti-Pattern — Large Blob in Event

Utiliser Artifact reference.

---

# 344. Anti-Pattern — Reuse Message ID With Changed Payload

Conflit.

---

# 345. Anti-Pattern — Drop Poison Message

Interdit.

---

# 346. Anti-Pattern — Retry External Effect From Message Handler Without Effect Model

Interdit.

---

# 347. Testing Strategy

Tests unitaires :

```text
event envelope
mappers
versioning
payload digest
```

---

# 348. Contract Tests

```text
OutboxStore
InboxStore
EventPublisher
event serialization
```

---

# 349. Integration Tests

```text
PostgreSQL
broker adapter
consumer transactions
```

---

# 350. Failure Tests

```text
publish after broker accepted / before DB mark
consumer commit / before ack
broker outage
claim expiry
dead letter
```

---

# 351. Distributed Tests

Plusieurs :

```text
publishers
consumers
```

sur même Outbox/Inbox.

---

# 352. Restore Tests

PITR avec :

```text
old Outbox states
old Inbox states
```

et external Effects déjà appliqués.

---

# 353. P0 Tests

```text
EVT-P0-01 domain state + outbox atomic
EVT-P0-02 publisher crash after send
EVT-P0-03 duplicate consumer delivery
EVT-P0-04 same message id/different payload conflict
EVT-P0-05 queue delivery without lease cannot execute protected Run
EVT-P0-06 restored outbox cannot duplicate protected Effect
EVT-P0-07 secret scan on public events
EVT-P0-08 stale event cannot override authoritative state
```

---

# 354. Production Qualification

Le document 40 doit démontrer :

```text
broker unavailable
publisher restart
consumer restart
backlog catch-up
duplicate redelivery
poison message
restore/PITR redelivery
```

---

# 355. Operational Runbooks

Le document 42 doit contenir ou référencer :

```text
Outbox backlog
Inbox conflict
Dead-letter recovery
Broker outage
Consumer poison event
```

---

# 356. Metrics Acceptance

Avant stable :

```text
outbox lag
dead letter count
inbox conflict count
consumer lag
```

doivent être observables.

---

# 357. Package Dependency Rules

Le Domain ne dépend d’aucun client broker.

---

# 358. Optional Broker Extras

Exemples :

```text
pyagentskit[kafka]
pyagentskit[rabbitmq]
```

si adapters officiels introduits.

---

# 359. Minimal Core

Le core doit fonctionner sans broker externe.

---

# 360. PostgreSQL-Only Production

Un profil peut utiliser :

```text
PostgreSQL Outbox
+
polling publisher
+
HTTP/webhook consumer
```

sans broker.

---

# 361. Scalability

Le modèle doit permettre introduction ultérieure de :

```text
Kafka
NATS
Service Bus
```

sans changer Domain semantics.

---

# 362. Event Publisher Adapter Maturity

Même modèle :

```text
L0 fake
L1 contract
L2 integration
L3 failure
L4 production qualified
```

---

# 363. Consumer Adapter Maturity

Idem.

---

# 364. Example End-to-End Flow

```text
Approval approved
      │
      ▼
Governance aggregate changes
      │
      ▼
DomainEvent ApprovalApproved
      │
      ▼
same DB transaction
      │
      ├── Approval state
      └── Outbox record
              │
           COMMIT
              │
              ▼
       Outbox Publisher
              │
              ▼
            Broker
              │
              ▼
       Execution Consumer
              │
              ▼
      Inbox try_begin
              │
              ▼
       RecoverRun command
              │
              ▼
       RecoveryPlanner
              │
              ▼
      re-read Approval state
              │
              ▼
        safe NextAction
              │
              ▼
     Inbox mark processed
              │
            COMMIT
              │
              ▼
             ACK
```

---

# 365. Important Observation

L’event :

```text
ApprovalApproved
```

n’autorise pas directement l’action.

Il déclenche :

```text
re-read authoritative Approval
```

puis le RecoveryPlanner décide.

---

# 366. Second Example — Effect UNKNOWN

```text
Effect becomes UNKNOWN
      │
      ▼
DomainEvent
      │
      ▼
Outbox
      │
      ▼
Reconciliation consumer
      │
      ▼
Inbox
      │
      ▼
Open/Reconcile case
```

---

# 367. Reconciliation Result Event

Après résolution :

```text
EffectReconciled
```

peut déclencher :

```text
RecoverRun
```

---

# 368. No Event Shortcut

Aucun event ne bypass :

```text
Application Service
Authorization
Lease/Fencing
Effect state
```

---

# 369. Event Replay Safety

Si `EffectReconciled` redelivered :

```text
RecoverRun
```

relit l’état.

Si déjà terminal :

```text
no duplicate Effect
```

---

# 370. CQRS-Light

Les events peuvent alimenter :

```text
RunTimeline
OpsDashboard
AuditProjection
```

sans introduire full CQRS/event sourcing.

---

# 371. Read Model Rebuildability

Un read model important doit être :

```text
rebuildable
```

depuis sources autoritatives ou event history disponible.

---

# 372. Read Model Staleness

UI doit pouvoir afficher :

```text
last_updated_at
```

pour données eventual-consistent.

---

# 373. Public API Event Subscriptions

Future feature possible :

```text
webhooks
SSE
event subscriptions
```

---

# 374. Public Webhook Delivery

Si introduit, utiliser lui aussi Outbox semantics.

---

# 375. Webhook Delivery Idempotency

Chaque delivery peut avoir :

```text
delivery_id
```

distinct du `event_id`.

---

# 376. Webhook Retry

At-least-once.

---

# 377. Consumer Guidance

Documenter pour utilisateurs externes :

```text
dedupe by event_id
```

---

# 378. Webhook Signature

Recommandée.

---

# 379. Subscription Failure

Une destination cassée ne doit pas bloquer toute la plateforme.

---

# 380. Fan-Out Outbox Design

Option :

```text
one canonical event
multiple delivery records
```

si webhooks multiples.

---

# 381. Non-goal Initial

Ne pas construire un service SaaS complet de webhooks dans V2 initial.

---

# 382. Domain Event Catalog — Initial Proposal

## Execution

```text
RunCreated
RunStarted
RunWaiting
RunPaused
RunResumed
RunSucceeded
RunFailed
RunCancelled
```

## Effects

```text
EffectPlanned
EffectStarted
EffectSucceeded
EffectFailed
EffectBecameUnknown
EffectReconciliationRequested
EffectReconciled
```

## Governance

```text
ApprovalRequested
ApprovalApproved
ApprovalRejected
ApprovalExpired
ApprovalCancelled
```

## Coordination

```text
LeaseAcquired
LeaseExpired
LeaseReleased
LeaseTakenOver
StaleFencingRejected
```

## Runtime Integration

```text
RuntimeBindingCreated
RuntimeInvocationStarted
RuntimeInvocationWaiting
RuntimeInvocationCompleted
RuntimeInvocationFailed
```

## Conversations

```text
SessionCreated
ConversationCreated
ParticipantAdded
MessageAppended
```

## Artifacts

```text
ArtifactRegistered
ArtifactVerified
ArtifactInvalidated
```

---

# 383. Catalog Is Not Frozen Yet

Avant `2.0.0rc1`, le catalogue doit être revu puis gelé pour les événements publics.

---

# 384. Domain Events vs State Changes

Tous les changements de champs n’ont pas besoin d’un event.

---

# 385. Criteria for Event

Créer un DomainEvent si le fait :

```text
has business meaning
may trigger another action
must be observable
is useful for audit/integration
```

---

# 386. Event Handler Registration

Peut être explicite :

```text
handler registry
```

mais sans magie excessive.

---

# 387. Handler Failure Isolation

Handlers async séparés grâce à Outbox.

---

# 388. In-Transaction Handler Failure

Rollback si handler fait partie de l’invariant local.

---

# 389. Handler Ordering Documentation

Si order matters, documenter.

---

# 390. Event Naming Stability

Après stable :

```text
rename event
```

est breaking pour public events.

---

# 391. Consumer Contract

Chaque consumer documente :

```text
accepted event types
versions
idempotency
ordering assumptions
failure behavior
```

---

# 392. Event Producer Contract

Chaque producer documente :

```text
when emitted
payload semantics
ordering
duplication possibility
```

---

# 393. Event Catalog as Documentation Artifact

Un futur document généré peut exposer :

```text
event name
version
producer
consumers
schema
```

---

# 394. Acceptance Criteria

Le modèle Domain Events / Outbox / Inbox est conforme si :

1. `DomainEvent`, `IntegrationEvent`, `RuntimeEvent` et `AuditEvent` sont distincts ;
2. le Domain ne publie pas directement au broker ;
3. Domain mutation et Outbox append sont atomiques localement ;
4. publication Outbox accepte at-least-once ;
5. consommateurs sont idempotents/Inbox-protected ;
6. Inbox conflict détecte même ID + payload différent ;
7. broker delivery ne confère jamais ownership ;
8. Inbox ne remplace pas Effect idempotency ;
9. event schemas publics sont versionnés ;
10. payloads minimisent les données ;
11. aucun secret résolu n’est publié ;
12. ordering est explicitement scoped ;
13. read models restent non autoritatifs ;
14. poison messages sont conservés/alertés ;
15. Restore/PITR redelivery reste sûre ;
16. public event catalog existe ;
17. V1 legacy events sont reclassifiés explicitement ;
18. handlers complexes restent des Application Use Cases ;
19. Outbox/Inbox sont contract-tested ;
20. broker reste optionnel.

---

# 395. Definition of Done

`../domain/33_PYAGENTSKIT_DOMAIN_EVENTS_AND_OUTBOX_INBOX.md` est considéré mature lorsque :

1. une base `DomainEvent` est implémentée ;
2. un `IntegrationEvent` envelope est implémenté ;
3. les event types P0 sont définis ;
4. `OutboxStore` existe ;
5. `InboxStore` existe ;
6. tables PostgreSQL `outbox_events` et `inbox_events` existent ;
7. UnitOfWork commit Domain + Outbox atomiquement ;
8. un OutboxPublisher existe ;
9. un EventPublisher in-process existe ;
10. au moins un transport réel peut être branché ;
11. Inbox dedup est physiquement protégée ;
12. poison/dead-letter semantics existent ;
13. event serialization est versionnée ;
14. consumer transaction pattern est implémenté ;
15. duplicates/redelivery sont testés ;
16. publisher crash-after-send est testé ;
17. restore/PITR redelivery est testée ;
18. métriques backlog/lag sont exposées ;
19. V1 EventType migration est documentée ;
20. GATE-09/GATE-12 du plan de qualification consomment ces preuves.

---

# 396. Résumé

Le modèle cible est :

```text
DOMAIN AGGREGATE
      │
      ▼
  DomainEvent
      │
      ▼
APPLICATION / UoW
      │
      ├── persist state
      └── append Outbox
              │
            COMMIT
              │
              ▼
       OUTBOX PUBLISHER
              │
              ▼
            BROKER
              │
              ▼
         INBOX CONSUMER
              │
              ▼
      dedupe + local tx
              │
              ▼
      Application Use Case
```

La chaîne de fiabilité est :

```text
business state
+
outbox
=
one local transaction

message delivery
=
at-least-once

consumer processing
=
deduplicated / idempotent

external consequence
=
still governed by Effect safety
```

La distinction structurante est :

```text
DomainEvent
!= IntegrationEvent
!= RuntimeEvent
!= AuditEvent
```

et la règle fondamentale est :

> **PyAgentsKit ne doit jamais confondre le fait qu’un événement a été livré avec le fait qu’un worker possède l’autorité d’agir, ni confondre la déduplication d’un message avec la sûreté d’un Effect réel.**
