BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS v2_schema_migrations (
    component TEXT PRIMARY KEY,
    version INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_runs (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_effects (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    status TEXT NOT NULL,
    idempotency_scope TEXT NOT NULL,
    idempotency_namespace TEXT,
    idempotency_key TEXT,
    fingerprint TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    payload_json TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_v2_effect_idempotency
ON v2_effects(idempotency_scope, idempotency_namespace, idempotency_key)
WHERE idempotency_key IS NOT NULL;

CREATE TABLE IF NOT EXISTS v2_memory_entries (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    scope TEXT NOT NULL,
    scope_id TEXT,
    memory_key TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_reconciliation_cases (
    id TEXT PRIMARY KEY,
    effect_id TEXT NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_v2_reconciliation_effect
ON v2_reconciliation_cases(effect_id, created_at);

CREATE TABLE IF NOT EXISTS v2_reconciliation_evidence (
    id TEXT PRIMARY KEY,
    case_id TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_approvals (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_leases (
    id TEXT PRIMARY KEY,
    resource TEXT NOT NULL,
    status TEXT NOT NULL,
    worker_id TEXT,
    fencing_token INTEGER NOT NULL CHECK (fencing_token >= 0),
    version INTEGER NOT NULL CHECK (version >= 0),
    payload_json TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_v2_active_lease_resource
ON v2_leases(resource)
WHERE status = 'held';

CREATE TABLE IF NOT EXISTS v2_fencing_counters (
    resource TEXT PRIMARY KEY,
    last_token INTEGER NOT NULL CHECK (last_token >= 0)
);

CREATE TABLE IF NOT EXISTS v2_runtime_bindings (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    runtime_id TEXT NOT NULL,
    runtime_family TEXT,
    bound_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_v2_runtime_bindings_run
ON v2_runtime_bindings(run_id);

CREATE TABLE IF NOT EXISTS v2_runtime_invocations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    binding_id TEXT NOT NULL,
    runtime_id TEXT,
    status TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    started_at TEXT,
    completed_at TEXT,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (binding_id) REFERENCES v2_runtime_bindings(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_v2_runtime_invocations_run
ON v2_runtime_invocations(run_id);

CREATE INDEX IF NOT EXISTS ix_v2_runtime_invocations_binding
ON v2_runtime_invocations(binding_id);

CREATE TABLE IF NOT EXISTS v2_audit_events (
    id TEXT PRIMARY KEY,
    subject TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_outbox_events (
    event_id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 0 CHECK (attempt_count >= 0),
    next_attempt_at TEXT,
    claimed_by TEXT,
    claimed_at TEXT,
    published_at TEXT,
    last_error TEXT,
    occurred_at TEXT NOT NULL,
    event_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_v2_outbox_dispatch
ON v2_outbox_events(status, next_attempt_at, occurred_at);

CREATE TABLE IF NOT EXISTS v2_inbox_events (
    source TEXT NOT NULL,
    external_event_id TEXT NOT NULL,
    digest TEXT NOT NULL,
    status TEXT NOT NULL,
    tenant_id TEXT,
    processed_at TEXT,
    last_error TEXT,
    PRIMARY KEY (source, external_event_id)
);


INSERT INTO v2_schema_migrations(component, version)
VALUES ('persistence_v2', 1)
ON CONFLICT(component) DO UPDATE SET version = excluded.version;

COMMIT;
