# PyAgentsKit 1.4.0 — Production State Stores

Release date: 2026-09-09

PyAgentsKit 1.4.0 completes the production persistence layer without changing the frozen V1 root
API. It adds PostgreSQL implementations for sessions, lexical memory and approvals, plus a
provider-neutral object-storage port with S3 and Azure Blob artifact adapters.

## Added

- `PostgresSessionStore` with atomic idempotent appends and optimistic revisions;
- `PostgresMemoryStore` with tenant/agent indexes, lexical filtering, tags and expiration;
- `PostgresApprovalStore` with transactional resolve, claim and complete transitions;
- asynchronous `BlobStore`, `S3BlobStore` and `AzureBlobStore` ports/adapters;
- integrity-checked `ObjectArtifactStore`, `S3ArtifactStore` and `AzureBlobArtifactStore`;
- PostgreSQL schema migration v2 and optional tenant RLS policies;
- `pyagentskit migrate-state` with dry-run, multiple SQLite inputs and conflict-safe imports;
- common semantic contracts across memory, SQLite and PostgreSQL stores;
- a PostgreSQL 16 service qualification job in CI; local live tests remain explicitly gated.

## Safety and compatibility

- every state key and query includes tenant scope;
- migration copies durable aggregates and never invokes model or tool code;
- object bytes are checked against size and SHA-256 metadata;
- SDKs, credentials, pools, containers and buckets remain application-owned;
- no implicit retry, failover, network connection or effect replay is introduced;
- the 155-name root API, 28 event values, provider signatures and frozen schemas are unchanged.

Install only the required adapters:

```bash
pip install "pyagentskit[postgres]"
pip install "pyagentskit[s3]"
pip install "pyagentskit[azure]"
pip install "pyagentskit[production-stores]"
```
