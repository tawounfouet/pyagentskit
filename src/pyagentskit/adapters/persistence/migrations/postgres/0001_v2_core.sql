CREATE TABLE IF NOT EXISTS __PFX___v2_schema_migrations (
    component TEXT PRIMARY KEY,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS __PFX___v2_runs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    status VARCHAR(32) NOT NULL
        CHECK (status IN ('created','running','waiting','paused','succeeded','failed','cancelled')),
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS __PFX___v2_runs_status_idx
ON __PFX___v2_runs(status);

CREATE TABLE IF NOT EXISTS __PFX___v2_effects (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    effect_kind VARCHAR(128) NOT NULL,
    status VARCHAR(64) NOT NULL
        CHECK (status IN (
            'not_started','started','succeeded','failed','unknown','reconciliation_required'
        )),
    risk_level VARCHAR(32) NOT NULL
        CHECK (risk_level IN ('low','medium','high','critical')),
    idempotency_scope VARCHAR(64) NOT NULL,
    idempotency_namespace VARCHAR(255),
    idempotency_key VARCHAR(512),
    fingerprint VARCHAR(128) NOT NULL,
    fencing_token BIGINT,
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    payload_json JSONB NOT NULL,
    CONSTRAINT __PFX___v2_effects_run_fk
        FOREIGN KEY (run_id) REFERENCES __PFX___v2_runs(id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT __PFX___v2_effects_timing_ck
        CHECK (completed_at IS NULL OR started_at IS NULL OR completed_at >= started_at)
);

CREATE UNIQUE INDEX IF NOT EXISTS __PFX___v2_effect_idempotency_uq
ON __PFX___v2_effects(idempotency_scope, idempotency_namespace, idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE INDEX IF NOT EXISTS __PFX___v2_effects_run_idx
ON __PFX___v2_effects(run_id);

CREATE TABLE IF NOT EXISTS __PFX___v2_memory_entries (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    scope VARCHAR(32) NOT NULL,
    scope_id TEXT,
    memory_key VARCHAR(255) NOT NULL,
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS __PFX___v2_memory_logical_uq
ON __PFX___v2_memory_entries(tenant_id, scope, COALESCE(scope_id, ''), memory_key);

CREATE INDEX IF NOT EXISTS __PFX___v2_memory_scope_idx
ON __PFX___v2_memory_entries(tenant_id, scope, scope_id);

CREATE TABLE IF NOT EXISTS __PFX___v2_reconciliation_cases (
    id TEXT PRIMARY KEY,
    effect_id TEXT NOT NULL,
    status VARCHAR(32) NOT NULL
        CHECK (status IN (
            'pending','running','resolved_success','resolved_failure','manual_review','failed'
        )),
    attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
    max_attempts INTEGER NOT NULL CHECK (max_attempts >= 1),
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    resolved_at TIMESTAMPTZ,
    payload_json JSONB NOT NULL,
    CONSTRAINT __PFX___v2_reconciliation_effect_fk
        FOREIGN KEY (effect_id) REFERENCES __PFX___v2_effects(id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS __PFX___v2_reconciliation_effect_idx
ON __PFX___v2_reconciliation_cases(effect_id, created_at DESC);

CREATE TABLE IF NOT EXISTS __PFX___v2_reconciliation_evidence (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL,
    CONSTRAINT __PFX___v2_reconciliation_evidence_case_fk
        FOREIGN KEY (case_id) REFERENCES __PFX___v2_reconciliation_cases(id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);

CREATE TABLE IF NOT EXISTS __PFX___v2_approvals (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    scope VARCHAR(32) NOT NULL,
    status VARCHAR(32) NOT NULL
        CHECK (status IN ('pending','approved','rejected','expired','cancelled')),
    expires_at TIMESTAMPTZ,
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS __PFX___v2_approvals_pending_idx
ON __PFX___v2_approvals(expires_at)
WHERE status = 'pending';

CREATE TABLE IF NOT EXISTS __PFX___v2_lease_resources (
    resource TEXT PRIMARY KEY,
    current_fencing_token BIGINT NOT NULL CHECK (current_fencing_token >= 0),
    version BIGINT NOT NULL DEFAULT 0 CHECK (version >= 0)
);

CREATE TABLE IF NOT EXISTS __PFX___v2_leases (
    id TEXT PRIMARY KEY,
    resource TEXT NOT NULL,
    status VARCHAR(32) NOT NULL
        CHECK (status IN ('available','held','released','expired')),
    worker_id TEXT,
    fencing_token BIGINT NOT NULL CHECK (fencing_token >= 0),
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL,
    CONSTRAINT __PFX___v2_lease_fencing_uq UNIQUE(resource, fencing_token)
);

CREATE UNIQUE INDEX IF NOT EXISTS __PFX___v2_active_lease_resource_uq
ON __PFX___v2_leases(resource)
WHERE status = 'held';

CREATE INDEX IF NOT EXISTS __PFX___v2_leases_resource_history_idx
ON __PFX___v2_leases(resource, fencing_token DESC);

CREATE TABLE IF NOT EXISTS __PFX___v2_audit_events (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    event_type VARCHAR(128) NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS __PFX___v2_audit_subject_idx
ON __PFX___v2_audit_events(subject, occurred_at);

CREATE TABLE IF NOT EXISTS __PFX___v2_outbox_events (
    event_id TEXT PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    aggregate_type VARCHAR(128),
    aggregate_id TEXT,
    status VARCHAR(32) NOT NULL
        CHECK (status IN ('pending','claimed','published','failed')),
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    next_attempt_at TIMESTAMPTZ,
    claimed_by TEXT,
    claimed_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ,
    last_error TEXT,
    occurred_at TIMESTAMPTZ NOT NULL,
    event_json JSONB NOT NULL
);

CREATE INDEX IF NOT EXISTS __PFX___v2_outbox_dispatch_idx
ON __PFX___v2_outbox_events(status, next_attempt_at, occurred_at);

CREATE TABLE IF NOT EXISTS __PFX___v2_inbox_events (
    source VARCHAR(128) NOT NULL,
    external_event_id TEXT NOT NULL,
    digest VARCHAR(128) NOT NULL,
    status VARCHAR(32) NOT NULL
        CHECK (status IN ('reserved','processed','failed')),
    tenant_id TEXT,
    processed_at TIMESTAMPTZ,
    last_error TEXT,
    PRIMARY KEY (source, external_event_id)
);


INSERT INTO __PFX___v2_schema_migrations(component, version)
VALUES ('persistence_v2', 1)
ON CONFLICT(component) DO NOTHING;
