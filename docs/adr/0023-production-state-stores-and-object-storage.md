# ADR-0023 — Production state stores and object storage

Status: Accepted  
Date: 2026-09-09

## Decision

Implement session, memory and approval stores over the existing async PostgreSQL pool port using
tenant-scoped transactional JSONB documents and indexed query columns. Introduce a minimal async
`BlobStore` port and compose the frozen `ArtifactStore` contract over S3 or Azure Blob adapters.

Migrations are explicit, versioned and operator-triggered. SQLite-to-PostgreSQL import validates
all documents and copies durable effects without executing them. RLS remains an opt-in deployment
hardening layer in addition to mandatory query scoping.

## Consequences

- local memory/SQLite/filesystem implementations remain first-class and dependency-free;
- cloud SDKs and asyncpg remain optional extras;
- the V1 root namespace remains frozen;
- cross-store atomicity, credentials, roles, encryption, backup and lifecycle remain deployment
  responsibilities;
- no automatic retry or effect replay is allowed at the persistence boundary.
