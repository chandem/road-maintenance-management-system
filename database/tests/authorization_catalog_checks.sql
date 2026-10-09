-- AI-RMMS authorization catalog regression checks.
-- Run in an ISOLATED staging database after applying migrations 011-015.
-- This script is read-only: it inspects catalog metadata and raises an error
-- when required protections are missing. It does NOT prove row-level behavior;
-- authenticated-JWT integration tests are still mandatory.

DO $checks$
DECLARE
  rel_name text;
  required_tables text[] := ARRAY[
    'roads',
    'road_sections',
    'road_inspections',
    'materials',
    'maintenance_plans',
    'work_orders',
    'machinery',
    'assets',
    'budgets',
    'expenses',
    'employees',
    'documents',
    'document_chunks',
    'ai_conversations',
    'ai_messages',
    'ai_message_sources'
  ];
  required_policy_tables text[] := ARRAY[
    'roads',
    'road_sections',
    'road_inspections',
    'materials',
    'maintenance_plans',
    'work_orders',
    'machinery',
    'assets',
    'budgets',
    'expenses',
    'employees',
    'documents',
    'document_chunks',
    'ai_conversations',
    'ai_messages',
    'ai_message_sources'
  ];
  missing_tables text[] := ARRAY[]::text[];
  missing_rls text[] := ARRAY[]::text[];
  missing_policies text[] := ARRAY[]::text[];
  policy_record record;
  helper_oid oid;
  helper_security_definer boolean;
  match_function record;
BEGIN
  FOREACH rel_name IN ARRAY required_tables LOOP
    IF to_regclass(format('public.%I', rel_name)) IS NULL THEN
      missing_tables := array_append(missing_tables, rel_name);
    ELSIF NOT EXISTS (
      SELECT 1
      FROM pg_class c
      WHERE c.oid = to_regclass(format('public.%I', rel_name))
        AND c.relrowsecurity
    ) THEN
      missing_rls := array_append(missing_rls, rel_name);
    END IF;
  END LOOP;

  IF cardinality(missing_tables) > 0 THEN
    RAISE EXCEPTION 'Required authorization tables missing: %', array_to_string(missing_tables, ', ');
  END IF;

  IF cardinality(missing_rls) > 0 THEN
    RAISE EXCEPTION 'RLS is not enabled on: %', array_to_string(missing_rls, ', ');
  END IF;

  -- Every table must have at least one policy applicable to authenticated.
  FOREACH rel_name IN ARRAY required_policy_tables LOOP
    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies p
      WHERE p.schemaname = 'public'
        AND p.tablename = rel_name
        AND 'authenticated' = ANY(p.roles)
    ) THEN
      missing_policies := array_append(missing_policies, rel_name);
    END IF;
  END LOOP;

  IF cardinality(missing_policies) > 0 THEN
    RAISE EXCEPTION 'No authenticated policy found on: %', array_to_string(missing_policies, ', ');
  END IF;

  -- The public RPC wrapper should be SECURITY INVOKER; the privileged helper
  -- belongs in private and must not be SECURITY INVOKER accidentally replaced.
  SELECT p.oid, p.prosecdef
    INTO helper_oid, helper_security_definer
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'public'
    AND p.proname = 'has_department_role'
  ORDER BY p.oid
  LIMIT 1;

  IF helper_oid IS NULL THEN
    RAISE EXCEPTION 'public.has_department_role wrapper is missing';
  END IF;

  IF helper_security_definer THEN
    RAISE EXCEPTION 'public.has_department_role must be SECURITY INVOKER';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private'
      AND p.proname = 'has_department_role'
      AND p.prosecdef
  ) THEN
    RAISE EXCEPTION 'private.has_department_role SECURITY DEFINER helper is missing';
  END IF;

  -- Direct authenticated inserts must be limited to user-role messages.
  -- Assistant/system replies are written only by the server-side trusted client.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies p
    WHERE p.schemaname = 'public'
      AND p.tablename = 'ai_messages'
      AND p.cmd = 'INSERT'
      AND 'authenticated' = ANY(p.roles)
      AND coalesce(p.with_check, '') ILIKE '%role%user%'
  ) THEN
    RAISE EXCEPTION 'ai_messages lacks an authenticated INSERT policy that restricts role to user';
  END IF;

  -- Authenticated users must not be able to fabricate AI evidence/source rows.
  IF has_table_privilege('authenticated', 'public.ai_message_sources', 'INSERT') THEN
    RAISE EXCEPTION 'authenticated role unexpectedly has INSERT privilege on ai_message_sources';
  END IF;

  -- AI message SELECT policies must not reference ai_message_sources directly:
  -- PostgreSQL policy expressions cannot use a table that is not in their query.
  IF EXISTS (
    SELECT 1
    FROM pg_policies p
    WHERE p.schemaname = 'public'
      AND p.tablename = 'ai_messages'
      AND coalesce(p.qual, '') ILIKE '%ai_message_sources%'
  ) THEN
    RAISE EXCEPTION 'ai_messages policy contains an invalid direct reference to ai_message_sources';
  END IF;

  -- Require department-aware document access and road-section integrity trigger.
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'documents'
      AND column_name = 'department_code'
  ) THEN
    RAISE EXCEPTION 'documents.department_code is missing';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_trigger t
    WHERE t.tgrelid = 'public.road_sections'::regclass
      AND t.tgname = 'enforce_road_section_organization'
      AND NOT t.tgisinternal
  ) THEN
    RAISE EXCEPTION 'road-section organization integrity trigger is missing';
  END IF;

  -- Semantic search must remain SECURITY INVOKER so RLS applies to chunk rows.
  SELECT p.prosecdef, pg_get_function_identity_arguments(p.oid) AS args
    INTO match_function
  FROM pg_proc p
  JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'public'
    AND p.proname = 'match_document_chunks'
  ORDER BY p.oid
  LIMIT 1;

  IF match_function IS NULL THEN
    RAISE EXCEPTION 'public.match_document_chunks function is missing';
  END IF;

  IF match_function.prosecdef THEN
    RAISE EXCEPTION 'public.match_document_chunks must remain SECURITY INVOKER';
  END IF;

  RAISE NOTICE 'Authorization catalog checks passed. Runtime JWT/RLS tests are still required.';
END
$checks$;
