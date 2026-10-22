# ADR 0026 — V2 PostgreSQL identifiers and normalized safety columns

**Status:** Accepted  
**Date:** 2026-10-22  
**Milestone:** 2.0.0a4 — Persistence V2

## Context

The V2 domain already exposes typed identifiers such as `RunId`, `EffectId`,
`LeaseId` and `RuntimeBindingId`. Their canonical representation is a validated
string (for example `run_<hex>`) rather than a UUID object.

The PostgreSQL reference-model specification recommends UUIDs, but also requires
that persistence must not dictate the Domain or silently rewrite public semantics.

At the same time, the database must physically protect critical invariants:

- optimistic concurrency;
- Effect idempotency;
- one active lease per resource;
- monotonic fencing;
- Inbox deduplication;
- local state + Audit + Outbox atomicity.

## Decision

For the 2.0.0a4 V2 schema:

1. Domain identifiers are persisted as bounded `TEXT`/varchar-compatible values.
2. Adapters never generate a second database-only identifier for a Domain aggregate.
3. Safety-critical state is stored in typed columns, not hidden only in JSONB:
   - status;
   - aggregate version;
   - run/effect/resource relationships;
   - idempotency scope/namespace/key;
   - fingerprint;
   - fencing token;
   - claim status/timestamps;
   - Inbox digest.
4. JSONB is used only as an explicit persistence document for reconstructing the
   current aggregate shape and for extensible metadata/payloads.
5. PostgreSQL foreign keys are added where the current Domain exposes an unambiguous
   strong relationship.
6. Table names remain prefixable for integration qualification; the production
   deployment may use the canonical `pyagentskit` prefix.

## Consequences

### Positive

- no lossy Identifier ↔ UUID conversion;
- no duplicate identity model;
- V2 Domain remains persistence-independent;
- CAS and fencing are queryable and enforceable at the database layer;
- test databases can be isolated by table prefix.

### Trade-offs

- the physical model differs from the UUID recommendation in the reference document;
- a future migration to UUID/UUIDv7 would require an explicit breaking persistence
  migration rather than an invisible adapter conversion.

## Rejected alternatives

### Convert typed identifiers to UUIDs inside adapters

Rejected because current identifiers are not guaranteed to contain a UUID and such
conversion would create persistence semantics not represented by the Domain.

### Store complete aggregates only as JSONB

Rejected because it would hide the invariants A4 exists to protect physically.

### Rewrite the V2 Domain identifier model in A4

Rejected because persistence must not dictate the Domain and the milestone is not an
identity-model rewrite.
