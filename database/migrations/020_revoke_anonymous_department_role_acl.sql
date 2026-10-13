-- Targeted recovery hardening for department-role assignment ACLs.
-- This migration is intentionally idempotent. It removes direct and inherited
-- anonymous access while preserving authenticated DML for the existing
-- organization-admin RLS workflow. It does not change production by itself;
-- test the full migration sequence and authenticated API behavior before release.

REVOKE ALL PRIVILEGES
  ON TABLE public.user_department_roles
  FROM PUBLIC, anon;

-- Table-level REVOKE does not clear independent column grants. Clear them too.
DO $revoke_anon_role_columns$
DECLARE
  v_column text;
BEGIN
  FOR v_column IN
    SELECT a.attname
    FROM pg_attribute a
    WHERE a.attrelid = 'public.user_department_roles'::regclass
      AND a.attnum > 0
      AND NOT a.attisdropped
  LOOP
    EXECUTE format(
      'REVOKE SELECT (%1$I), INSERT (%1$I), UPDATE (%1$I), REFERENCES (%1$I) ON TABLE public.user_department_roles FROM PUBLIC, anon',
      v_column
    );
  END LOOP;
END
$revoke_anon_role_columns$;

-- These structural privileges are unnecessary for client JWT roles and bypass
-- ordinary row-level protections (notably TRUNCATE). Preserve SELECT/INSERT/
-- UPDATE/DELETE for authenticated clients because RLS policies still gate
-- administrator role-management workflows.
REVOKE TRUNCATE, REFERENCES, TRIGGER, MAINTAIN
  ON TABLE public.user_department_roles
  FROM PUBLIC, anon, authenticated;

COMMENT ON TABLE public.user_department_roles IS
  'Department role assignments. Anonymous access is revoked; authenticated access is governed by explicit RLS policies and least-privilege table grants.';
