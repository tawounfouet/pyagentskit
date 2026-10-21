-- PyAgentsKit 1.3.0 canonical PostgreSQL schema (prefix: pyagentskit)
-- Apply with a migration role; runtime roles may use narrower DML grants.

BEGIN;

CREATE TABLE IF NOT EXISTS pyagentskit_schema_versions (
    component TEXT PRIMARY KEY,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pyagentskit_lease_tokens (
    tenant_scope TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    last_token BIGINT NOT NULL,
    PRIMARY KEY (tenant_scope, resource_id)
);

CREATE TABLE IF NOT EXISTS pyagentskit_leases (
    tenant_scope TEXT NOT NULL,
    resource_id TEXT NOT NULL,
    lease_id TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    fencing_token BIGINT NOT NULL,
    revision BIGINT NOT NULL,
    acquired_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (tenant_scope, resource_id)
);

CREATE INDEX IF NOT EXISTS pyagentskit_leases_expiry_idx
    ON pyagentskit_leases(expires_at);

CREATE TABLE IF NOT EXISTS pyagentskit_run_locks (
    tenant_scope TEXT NOT NULL,
    run_id UUID NOT NULL,
    PRIMARY KEY (tenant_scope, run_id)
);

CREATE TABLE IF NOT EXISTS pyagentskit_runs (
    tenant_scope TEXT NOT NULL,
    run_id UUID NOT NULL,
    payload_json JSONB NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (tenant_scope, run_id)
);

CREATE INDEX IF NOT EXISTS pyagentskit_runs_payload_gin_idx
    ON pyagentskit_runs USING GIN(payload_json);

INSERT INTO pyagentskit_schema_versions(component, version)
VALUES ('coordination_leases', 1)
ON CONFLICT(component) DO NOTHING;

INSERT INTO pyagentskit_schema_versions(component, version)
VALUES ('durable_runs', 1)
ON CONFLICT(component) DO NOTHING;

COMMIT;
