-- Optional tenant Row-Level Security hardening for PyAgentsKit 1.4.0.
--
-- The application role must execute this inside every transaction:
--   SELECT set_config('pyagentskit.tenant_scope', '<tenant>', true);
-- A dedicated migration/admin role should own the tables and must not be used
-- by the application. Empty tenant_scope represents the explicit global scope.

BEGIN;

ALTER TABLE pyagentskit_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE pyagentskit_state FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pyagentskit_state_tenant ON pyagentskit_state;
CREATE POLICY pyagentskit_state_tenant ON pyagentskit_state
    USING (
        tenant_scope = current_setting('pyagentskit.tenant_scope', true)
        AND current_setting('pyagentskit.tenant_scope', true) IS NOT NULL
    )
    WITH CHECK (
        tenant_scope = current_setting('pyagentskit.tenant_scope', true)
        AND current_setting('pyagentskit.tenant_scope', true) IS NOT NULL
    );

ALTER TABLE pyagentskit_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE pyagentskit_runs FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pyagentskit_runs_tenant ON pyagentskit_runs;
CREATE POLICY pyagentskit_runs_tenant ON pyagentskit_runs
    USING (tenant_scope = current_setting('pyagentskit.tenant_scope', true))
    WITH CHECK (tenant_scope = current_setting('pyagentskit.tenant_scope', true));

ALTER TABLE pyagentskit_run_locks ENABLE ROW LEVEL SECURITY;
ALTER TABLE pyagentskit_run_locks FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pyagentskit_run_locks_tenant ON pyagentskit_run_locks;
CREATE POLICY pyagentskit_run_locks_tenant ON pyagentskit_run_locks
    USING (tenant_scope = current_setting('pyagentskit.tenant_scope', true))
    WITH CHECK (tenant_scope = current_setting('pyagentskit.tenant_scope', true));

ALTER TABLE pyagentskit_leases ENABLE ROW LEVEL SECURITY;
ALTER TABLE pyagentskit_leases FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pyagentskit_leases_tenant ON pyagentskit_leases;
CREATE POLICY pyagentskit_leases_tenant ON pyagentskit_leases
    USING (tenant_scope = current_setting('pyagentskit.tenant_scope', true))
    WITH CHECK (tenant_scope = current_setting('pyagentskit.tenant_scope', true));

ALTER TABLE pyagentskit_lease_tokens ENABLE ROW LEVEL SECURITY;
ALTER TABLE pyagentskit_lease_tokens FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS pyagentskit_lease_tokens_tenant ON pyagentskit_lease_tokens;
CREATE POLICY pyagentskit_lease_tokens_tenant ON pyagentskit_lease_tokens
    USING (tenant_scope = current_setting('pyagentskit.tenant_scope', true))
    WITH CHECK (tenant_scope = current_setting('pyagentskit.tenant_scope', true));

COMMIT;
