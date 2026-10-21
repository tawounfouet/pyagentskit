# Production state stores

## PostgreSQL

Create one application-owned asyncpg pool, initialize adapters during readiness, and inject the
existing store protocols into the runtime:

```python
from pyagentskit.postgres import create_asyncpg_pool
from pyagentskit.postgres_state import PostgresMemoryStore, PostgresSessionStore

pool = await create_asyncpg_pool(dsn, min_size=2, max_size=20)
sessions = PostgresSessionStore(pool)
memory = PostgresMemoryStore(pool)
await sessions.initialize()
await memory.initialize()
```

For controlled deployments apply `docs/sql/postgres_v1.sql`, then `postgres_v2.sql` with a
migration role. Runtime lazy initialization is idempotent but requires DDL rights; pre-migration
allows narrower runtime DML grants.

## SQLite migration

Stop writers, back up the SQLite files, validate, migrate, verify counts, then switch traffic:

```bash
pyagentskit migrate-state --sqlite sessions.db --sqlite memory.db --dry-run
export PYAGENTSKIT_POSTGRES_DSN='postgresql://...'
pyagentskit migrate-state --sqlite sessions.db --sqlite memory.db
```

Identical reruns are accepted. Conflicting target records fail closed unless `--overwrite` is
explicit. Durable run documents are copied; stored tool effects are never executed. Filesystem
artifacts are not silently uploaded and require an application-specific data-transfer plan.

## Row-Level Security

`docs/sql/postgres_rls.sql` is an opt-in defense-in-depth template. Use a non-owner runtime role and
set `pyagentskit.tenant_scope` inside each transaction before accessing a protected table. Validate
positive access and cross-tenant denial using the exact pool/role configuration before enabling
`FORCE ROW LEVEL SECURITY` in production.

## Object artifacts

```python
from pyagentskit.blobs import S3ArtifactStore, create_s3_client

client = create_s3_client(region_name="eu-west-1")
artifacts = S3ArtifactStore(client, bucket="agent-artifacts")
```

`AzureBlobArtifactStore` accepts an async Azure `ContainerClient`. Credential discovery, bucket or
container creation, IAM, encryption, object lifecycle and client closing stay under application
control. Tenant IDs are not exposed in object keys; a stable SHA-256-derived tenant prefix is used.

## Operational checklist

- pin and test PostgreSQL/asyncpg or cloud SDK versions;
- configure TLS, least-privilege roles, timeouts and pool limits;
- rehearse migration and rollback from a production-sized copy;
- monitor aggregate/object growth and schedule expiry purges;
- coordinate database and object-store retention;
- test RLS, backups and restore before cutover;
- run live S3/Azure tests only against isolated non-production resources.
