-- Read-only verification for 020_revoke_anonymous_department_role_acl.sql.
-- Run after applying migrations to an isolated/staging database as a database
-- owner. This raises on a failed invariant and performs no mutations.

DO $checks$
DECLARE
  v_table regclass := 'public.user_department_roles'::regclass;
  v_column record;
BEGIN
  IF has_table_privilege('anon', v_table, 'SELECT')
     OR has_table_privilege('anon', v_table, 'INSERT')
     OR has_table_privilege('anon', v_table, 'UPDATE')
     OR has_table_privilege('anon', v_table, 'DELETE')
     OR has_table_privilege('anon', v_table, 'TRUNCATE')
     OR has_table_privilege('anon', v_table, 'REFERENCES')
     OR has_table_privilege('anon', v_table, 'TRIGGER') THEN
    RAISE EXCEPTION 'anon retains a table-level privilege on user_department_roles';
  END IF;

  FOR v_column IN
    SELECT a.attname
    FROM pg_attribute a
    WHERE a.attrelid = v_table
      AND a.attnum > 0
      AND NOT a.attisdropped
  LOOP
    IF has_column_privilege('anon', v_table, v_column.attname, 'SELECT')
       OR has_column_privilege('anon', v_table, v_column.attname, 'INSERT')
       OR has_column_privilege('anon', v_table, v_column.attname, 'UPDATE')
       OR has_column_privilege('anon', v_table, v_column.attname, 'REFERENCES') THEN
      RAISE EXCEPTION 'anon retains a column-level privilege on user_department_roles.%', v_column.attname;
    END IF;
  END LOOP;

  IF has_table_privilege('authenticated', v_table, 'TRUNCATE')
     OR has_table_privilege('authenticated', v_table, 'REFERENCES')
     OR has_table_privilege('authenticated', v_table, 'TRIGGER') THEN
    RAISE EXCEPTION 'authenticated retains structural privileges on user_department_roles';
  END IF;
END
$checks$;

-- Runtime JWT/API tests are still required: this catalog test does not prove
-- that authenticated administrators can manage assignments or that anonymous
-- API calls are rejected by the deployed Data API.
