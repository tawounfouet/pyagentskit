BEGIN IMMEDIATE;

CREATE TABLE IF NOT EXISTS v2_sessions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_conversations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (session_id) REFERENCES v2_sessions(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_v2_conversations_session
ON v2_conversations(session_id);

CREATE TABLE IF NOT EXISTS v2_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES v2_conversations(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_v2_messages_conversation
ON v2_messages(conversation_id, created_at, id);

CREATE TABLE IF NOT EXISTS v2_workers (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    status TEXT NOT NULL,
    version INTEGER NOT NULL CHECK (version >= 0),
    created_at TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_artifacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS v2_runtime_bindings (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    runtime_id TEXT NOT NULL,
    runtime_family TEXT,
    bound_at TEXT NOT NULL,
    payload_json TEXT NOT NULL,
    FOREIGN KEY (run_id) REFERENCES v2_runs(id) ON DELETE RESTRICT
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
    FOREIGN KEY (run_id) REFERENCES v2_runs(id) ON DELETE RESTRICT,
    FOREIGN KEY (binding_id) REFERENCES v2_runtime_bindings(id) ON DELETE RESTRICT
);

CREATE INDEX IF NOT EXISTS ix_v2_runtime_invocations_run
ON v2_runtime_invocations(run_id);

CREATE INDEX IF NOT EXISTS ix_v2_runtime_invocations_binding
ON v2_runtime_invocations(binding_id);

INSERT INTO v2_schema_migrations(component, version)
VALUES ('persistence_v2', 2)
ON CONFLICT(component) DO UPDATE SET version = excluded.version;

COMMIT;
