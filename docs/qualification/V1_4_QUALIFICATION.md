# PyAgentsKit 1.4.0 qualification

## Qualification matrix

| Area | Deterministic release gate | Live CI gate |
|---|---|---|
| Sessions | Common memory/SQLite/PostgreSQL contract | PostgreSQL 16 round trip |
| Memory | Common search, tags, expiry and tenant contract | PostgreSQL 16 indexed query |
| Approvals | Common create/resolve/claim/complete contract | Schema/readiness exercised |
| Durable runs | Aggregate import without effect replay | Existing PostgreSQL lifecycle |
| S3 | boto3-compatible client double | Deployment-owned bucket test |
| Azure Blob | async client double | Deployment-owned container test |
| Migration | Real SQLite source and transactional PostgreSQL double | Operator cutover rehearsal |
| RLS | Static, versioned SQL review | Deployment role/policy test |

The default local release gate opens no socket. GitHub CI provisions PostgreSQL 16 and supplies
both `PYAGENTSKIT_LIVE_POSTGRES=I_ACCEPT_DATABASE_WRITES` and an ephemeral DSN. The same test module
is skipped locally unless both values are explicitly present.

## Required release gates

- Ruff lint and format;
- strict mypy across every source module;
- full branch-aware test suite at or above 90% coverage;
- frozen V1 API and event vocabulary checks;
- versioned schema and migration dry-run tests;
- wheel/sdist build, Twine validation and reproducible rebuild;
- installed-wheel imports and offline examples;
- ZIP integrity, secret hygiene and SHA-256 manifest.

Cloud object stores are adapter-qualified, not service-certified: production acceptance still owns
IAM, KMS/encryption, retention, lifecycle rules, regional behavior and live integration testing.
