# Audit — PyAgentsKit 1.4.0 Production State Stores

Audit date: 2026-09-09

## Conclusion

The release closes the production-state gap identified in 1.3.0 while preserving all V1 contracts.
State transitions are transactional, tenant filters are structural, migrations validate before
writing, and no migration path replays model or tool effects.

## Controls reviewed

- safe bounded SQL table-prefix interpolation only;
- composite tenant/collection/owner/record primary key;
- row locking for session append and approval transitions;
- immutable memory `created_at` and deterministic indexed search order;
- idempotent identical migration and explicit `--overwrite` for replacement;
- DSN passed by environment-variable name rather than command-line value;
- migration `--dry-run` requires no PostgreSQL dependency or connection;
- conditional cloud object creation, sidecar identity checks and SHA-256 verification;
- lazy optional SDK imports and application-owned client/pool lifecycle;
- versioned SQL, future-schema rejection and separate RLS hardening script;
- no root API expansion, hidden retry, distributed transaction or effect execution.

## Residual deployment risks

- migration cutover requires quiescing SQLite writers and verifying backups;
- RLS must be tested with the real application role and tenant session setting;
- JSONB session/run aggregates can grow and need deployment-specific limits/retention;
- S3/Azure consistency, IAM, encryption, lifecycle and disaster recovery are operator-owned;
- cross-store session/artifact deletion is not an atomic distributed transaction;
- PostgreSQL connection, statement and lock timeout policy remains application-owned.
