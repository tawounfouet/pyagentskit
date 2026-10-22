CREATE TABLE IF NOT EXISTS __PFX___v2_sessions (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS __PFX___v2_conversations (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL,
    CONSTRAINT __PFX___v2_conversations_session_fk
        FOREIGN KEY (session_id) REFERENCES __PFX___v2_sessions(id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS __PFX___v2_conversations_session_idx
ON __PFX___v2_conversations(session_id);

CREATE TABLE IF NOT EXISTS __PFX___v2_messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL,
    CONSTRAINT __PFX___v2_messages_conversation_fk
        FOREIGN KEY (conversation_id) REFERENCES __PFX___v2_conversations(id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS __PFX___v2_messages_conversation_idx
ON __PFX___v2_messages(conversation_id, created_at, id);

CREATE TABLE IF NOT EXISTS __PFX___v2_workers (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    status VARCHAR(32) NOT NULL
        CHECK (status IN ('admitted','ready','draining','stopped')),
    version BIGINT NOT NULL CHECK (version >= 0),
    created_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS __PFX___v2_artifacts (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    payload_json JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS __PFX___v2_runtime_bindings (
    id TEXT PRIMARY KEY,
    run_id TEXT,
    runtime_id TEXT NOT NULL,
    runtime_family TEXT,
    bound_at TIMESTAMPTZ NOT NULL,
    payload_json JSONB NOT NULL,
    CONSTRAINT __PFX___v2_runtime_bindings_run_fk
        FOREIGN KEY (run_id) REFERENCES __PFX___v2_runs(id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS __PFX___v2_runtime_bindings_run_idx
ON __PFX___v2_runtime_bindings(run_id);

CREATE TABLE IF NOT EXISTS __PFX___v2_runtime_invocations (
    id TEXT PRIMARY KEY,
    run_id TEXT NOT NULL,
    binding_id TEXT NOT NULL,
    status VARCHAR(32) NOT NULL,
    version BIGINT NOT NULL CHECK (version >= 0),
    payload_json JSONB NOT NULL,
    CONSTRAINT __PFX___v2_runtime_invocations_run_fk
        FOREIGN KEY (run_id) REFERENCES __PFX___v2_runs(id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED,
    CONSTRAINT __PFX___v2_runtime_invocations_binding_fk
        FOREIGN KEY (binding_id) REFERENCES __PFX___v2_runtime_bindings(id)
        ON DELETE RESTRICT DEFERRABLE INITIALLY DEFERRED
);

CREATE INDEX IF NOT EXISTS __PFX___v2_runtime_invocations_run_idx
ON __PFX___v2_runtime_invocations(run_id);

CREATE INDEX IF NOT EXISTS __PFX___v2_runtime_invocations_binding_idx
ON __PFX___v2_runtime_invocations(binding_id);

INSERT INTO __PFX___v2_schema_migrations(component, version)
VALUES ('persistence_v2', 2)
ON CONFLICT(component) DO UPDATE SET version = excluded.version;
