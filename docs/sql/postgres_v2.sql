-- PyAgentsKit 1.4.0 production state migration (v1 -> v2)
-- Prefix: pyagentskit. Apply with a migration role before deploying 1.4.0.

BEGIN;

CREATE TABLE IF NOT EXISTS pyagentskit_schema_versions (
    component TEXT PRIMARY KEY,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS pyagentskit_state (
    tenant_scope TEXT NOT NULL,
    collection TEXT NOT NULL,
    owner_id TEXT NOT NULL,
    record_id TEXT NOT NULL,
    payload_json JSONB NOT NULL,
    search_text TEXT NOT NULL DEFAULT '',
    session_id TEXT,
    tags TEXT[] NOT NULL DEFAULT '{}',
    status TEXT,
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    expires_at TIMESTAMPTZ,
    PRIMARY KEY (tenant_scope, collection, owner_id, record_id)
);

CREATE INDEX IF NOT EXISTS pyagentskit_state_lookup_idx
    ON pyagentskit_state(tenant_scope, collection, owner_id, updated_at DESC);

CREATE INDEX IF NOT EXISTS pyagentskit_state_expiry_idx
    ON pyagentskit_state(expires_at) WHERE expires_at IS NOT NULL;

CREATE INDEX IF NOT EXISTS pyagentskit_state_tags_gin_idx
    ON pyagentskit_state USING GIN(tags);

INSERT INTO pyagentskit_schema_versions(component, version)
VALUES ('production_state', 2)
ON CONFLICT(component) DO UPDATE SET version = EXCLUDED.version
WHERE pyagentskit_schema_versions.version < EXCLUDED.version;

COMMIT;
