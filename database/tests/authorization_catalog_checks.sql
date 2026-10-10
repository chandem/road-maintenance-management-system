-- AI-RMMS authorization catalog regression checks.
-- Run in an ISOLATED staging database after applying migrations 011-018.
-- This script is read-only: it inspects catalog metadata and raises an error
-- when required protections are missing. It does NOT prove row-level behavior;
-- authenticated-JWT integration tests are still mandatory.

DO $checks$
DECLARE
  rel_name text;
  required_tables text[] := ARRAY[
    'roads', 'road_sections', 'road_inspections', 'materials',
    'maintenance_plans', 'work_orders', 'machinery', 'assets',
    'budgets', 'expenses', 'employees', 'ai_analysis_runs',
    'ai_recommendations', 'documents', 'document_chunks',
    'ai_conversations', 'ai_messages', 'ai_message_sources',
    'departments', 'organization_members', 'organizations',
    'user_department_roles', 'user_profiles'
  ];
  required_policy_tables text[] := ARRAY[
    'roads', 'road_sections', 'road_inspections', 'materials',
    'maintenance_plans', 'work_orders', 'machinery', 'assets',
    'budgets', 'expenses', 'employees', 'ai_analysis_runs',
    'ai_recommendations', 'documents', 'document_chunks',
    'ai_conversations', 'ai_messages', 'ai_message_sources'
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
      SELECT 1 FROM pg_class c
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

  FOREACH rel_name IN ARRAY required_policy_tables LOOP
    IF NOT EXISTS (
      SELECT 1 FROM pg_policies p
      WHERE p.schemaname = 'public' AND p.tablename = rel_name
        AND 'authenticated' = ANY(p.roles)
    ) THEN
      missing_policies := array_append(missing_policies, rel_name);
    END IF;
  END LOOP;
  IF cardinality(missing_policies) > 0 THEN
    RAISE EXCEPTION 'No authenticated policy found on: %', array_to_string(missing_policies, ', ');
  END IF;

  FOREACH rel_name IN ARRAY required_policy_tables LOOP
    IF NOT EXISTS (
      SELECT 1 FROM pg_policies p
      WHERE p.schemaname = 'public' AND p.tablename = rel_name
        AND p.permissive = 'PERMISSIVE'
        AND 'authenticated' = ANY(p.roles)
    ) THEN
      RAISE EXCEPTION 'No permissive authenticated baseline policy found on public.%', rel_name;
    END IF;
  END LOOP;

  -- Department-protected business tables require restrictive coverage for all
  -- DML commands. This is structural verification only, not runtime RLS proof.
  FOREACH rel_name IN ARRAY ARRAY[
    'roads', 'road_sections', 'road_inspections', 'materials',
    'maintenance_plans', 'work_orders', 'machinery', 'assets',
    'budgets', 'expenses', 'employees', 'documents',
    'document_chunks', 'ai_analysis_runs', 'ai_recommendations'
  ] LOOP
    IF EXISTS (
      SELECT 1
      FROM unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']::text[]) AS cmd_name(cmd)
      WHERE NOT EXISTS (
        SELECT 1 FROM pg_policies p
        WHERE p.schemaname = 'public' AND p.tablename = rel_name
          AND p.permissive = 'RESTRICTIVE'
          AND 'authenticated' = ANY(p.roles)
          AND p.cmd IN ('ALL', cmd_name.cmd)
      )
    ) THEN
      RAISE EXCEPTION 'Missing restrictive command coverage (SELECT/INSERT/UPDATE/DELETE) for public.%', rel_name;
    END IF;
  END LOOP;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ai_conversations'
      AND permissive = 'RESTRICTIVE' AND cmd = 'SELECT'
      AND 'authenticated' = ANY(roles)
  ) OR NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ai_conversations'
      AND permissive = 'RESTRICTIVE' AND cmd = 'INSERT'
      AND 'authenticated' = ANY(roles)
  ) THEN
    RAISE EXCEPTION 'ai_conversations missing restrictive SELECT or INSERT policy';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ai_messages'
      AND permissive = 'RESTRICTIVE' AND cmd = 'SELECT'
      AND 'authenticated' = ANY(roles)
  ) OR NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ai_messages'
      AND permissive = 'RESTRICTIVE' AND cmd = 'INSERT'
      AND 'authenticated' = ANY(roles)
  ) THEN
    RAISE EXCEPTION 'ai_messages missing restrictive SELECT or INSERT policy';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ai_messages'
      AND policyname = 'ai_messages_department_insert'
      AND permissive = 'RESTRICTIVE' AND cmd = 'INSERT'
      AND 'authenticated' = ANY(roles)
      AND coalesce(with_check, '') ILIKE '%role%'
      AND coalesce(with_check, '') ILIKE '%user%'
      AND coalesce(with_check, '') ILIKE '%has_department_role%'
      AND coalesce(with_check, '') ILIKE '%status%'
      AND coalesce(with_check, '') ILIKE '%active%'
      AND coalesce(with_check, '') ILIKE '%created_by%'
      AND coalesce(with_check, '') ILIKE '%auth.uid%'
  ) THEN
    RAISE EXCEPTION 'ai_messages restrictive INSERT policy must enforce user-role messages, active-conversation status, caller ownership, and department authorization';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ai_message_sources'
      AND permissive = 'RESTRICTIVE' AND cmd = 'SELECT'
      AND 'authenticated' = ANY(roles)
  ) THEN
    RAISE EXCEPTION 'ai_message_sources missing restrictive SELECT policy';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ai_message_sources'
      AND policyname = 'ai_message_sources_department_select'
      AND permissive = 'RESTRICTIVE' AND cmd = 'SELECT'
      AND 'authenticated' = ANY(roles)
      AND coalesce(qual, '') ILIKE '%source_type%'
      AND coalesce(qual, '') ILIKE '%road%'
      AND coalesce(qual, '') ILIKE '%work_order%'
      AND coalesce(qual, '') ILIKE '%has_department_role%'
  ) THEN
    RAISE EXCEPTION 'ai_message_sources restrictive SELECT policy must limit non-admin evidence to authorized road-maintenance sources';
  END IF;

  -- Migration 016 audits every relation from the production privilege audit.
  -- RLS does not protect TRUNCATE; REFERENCES and TRIGGER are unnecessary
  -- for normal authenticated clients. Keep this list synchronized with 016.
  FOREACH rel_name IN ARRAY ARRAY[
    'roads', 'road_sections', 'road_inspections', 'materials',
    'maintenance_plans', 'work_orders', 'machinery', 'assets',
    'budgets', 'expenses', 'employees', 'documents', 'document_chunks',
    'ai_analysis_runs', 'ai_recommendations', 'ai_conversations',
    'ai_messages', 'ai_message_sources', 'departments',
    'organization_members', 'organizations', 'user_department_roles',
    'user_profiles'
  ] LOOP
    IF has_table_privilege('authenticated', to_regclass(format('public.%I', rel_name)), 'TRUNCATE')
       OR has_table_privilege('authenticated', to_regclass(format('public.%I', rel_name)), 'REFERENCES')
       OR has_table_privilege('authenticated', to_regclass(format('public.%I', rel_name)), 'TRIGGER') THEN
      RAISE EXCEPTION 'Authenticated role retains TRUNCATE/REFERENCES/TRIGGER on public.%', rel_name;
    END IF;
  END LOOP;

  SELECT p.oid, p.prosecdef INTO helper_oid, helper_security_definer
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'public' AND p.proname = 'has_department_role'
  ORDER BY p.oid LIMIT 1;
  IF helper_oid IS NULL THEN RAISE EXCEPTION 'public.has_department_role wrapper is missing'; END IF;
  IF helper_security_definer THEN RAISE EXCEPTION 'public.has_department_role must be SECURITY INVOKER'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private' AND p.proname = 'has_department_role'
      AND p.prosecdef AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'private.has_department_role must be SECURITY DEFINER with empty search_path';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname = 'has_department_role'
      AND NOT p.prosecdef AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'public.has_department_role must be SECURITY INVOKER with empty search_path';
  END IF;

  IF NOT has_schema_privilege('authenticated', 'private', 'USAGE') THEN
    RAISE EXCEPTION 'authenticated role lacks USAGE on private schema required by role helper';
  END IF;
  IF has_schema_privilege('anon', 'private', 'USAGE') THEN
    RAISE EXCEPTION 'anon role unexpectedly has USAGE on private schema';
  END IF;

  IF NOT has_function_privilege('authenticated', 'private.has_department_role(uuid,text,text[])', 'EXECUTE') THEN
    RAISE EXCEPTION 'authenticated role cannot execute private department-role helper';
  END IF;
  IF has_function_privilege('anon', 'private.has_department_role(uuid,text,text[])', 'EXECUTE')
     OR has_function_privilege('service_role', 'private.has_department_role(uuid,text,text[])', 'EXECUTE') THEN
    RAISE EXCEPTION 'anon or service_role unexpectedly can execute private department-role helper';
  END IF;
  IF NOT has_function_privilege('authenticated', 'public.has_department_role(uuid,text,text[])', 'EXECUTE') THEN
    RAISE EXCEPTION 'authenticated role cannot execute public department-role RPC wrapper';
  END IF;
  IF has_function_privilege('anon', 'public.has_department_role(uuid,text,text[])', 'EXECUTE')
     OR has_function_privilege('service_role', 'public.has_department_role(uuid,text,text[])', 'EXECUTE') THEN
    RAISE EXCEPTION 'anon or service_role unexpectedly can execute public department-role RPC wrapper';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private' AND p.proname = 'is_org_admin'
      AND p.prosecdef AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'private.is_org_admin must be SECURITY DEFINER with empty search_path';
  END IF;
  IF NOT has_function_privilege('authenticated', 'private.is_org_admin(uuid)', 'EXECUTE') THEN
    RAISE EXCEPTION 'authenticated role cannot execute private.is_org_admin';
  END IF;
  IF has_function_privilege('anon', 'private.is_org_admin(uuid)', 'EXECUTE')
     OR has_function_privilege('service_role', 'private.is_org_admin(uuid)', 'EXECUTE') THEN
    RAISE EXCEPTION 'anon or service_role unexpectedly has EXECUTE on private.is_org_admin';
  END IF;

  IF NOT has_function_privilege('authenticated', 'private.is_org_member(uuid)', 'EXECUTE') THEN
    RAISE EXCEPTION 'authenticated role cannot execute private.is_org_member required by AI conversation policies';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private' AND p.proname = 'is_org_member'
      AND p.pronargs = 1
      AND p.proargtypes[0] = 'uuid'::regtype
      AND p.prosecdef AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'private.is_org_member(uuid) must be SECURITY DEFINER with empty search_path';
  END IF;
  IF has_function_privilege('anon', 'private.is_org_member(uuid)', 'EXECUTE')
     OR has_function_privilege('service_role', 'private.is_org_member(uuid)', 'EXECUTE') THEN
    RAISE EXCEPTION 'anon or service_role unexpectedly has EXECUTE on private.is_org_member';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public' AND p.tablename = 'ai_messages'
      AND p.cmd = 'INSERT' AND 'authenticated' = ANY(p.roles)
      AND coalesce(p.with_check, '') ILIKE '%role%user%'
  ) THEN
    RAISE EXCEPTION 'ai_messages lacks an authenticated INSERT policy that restricts role to user';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public' AND p.tablename = 'ai_messages'
      AND p.cmd = 'INSERT' AND 'authenticated' = ANY(p.roles)
      AND coalesce(p.with_check, '') ILIKE '%created_by%'
      AND coalesce(p.with_check, '') ILIKE '%auth.uid%'
  ) THEN
    RAISE EXCEPTION 'ai_messages INSERT policy must enforce conversation ownership';
  END IF;

  IF has_table_privilege('authenticated', 'public.ai_messages', 'UPDATE')
     OR has_table_privilege('authenticated', 'public.ai_messages', 'DELETE') THEN
    RAISE EXCEPTION 'authenticated role unexpectedly has UPDATE/DELETE privilege on ai_messages';
  END IF;
  IF has_table_privilege('authenticated', 'public.ai_message_sources', 'INSERT') THEN
    RAISE EXCEPTION 'authenticated role unexpectedly has INSERT privilege on ai_message_sources';
  END IF;
  IF has_table_privilege('authenticated', 'public.ai_conversations', 'UPDATE') THEN
    RAISE EXCEPTION 'authenticated role unexpectedly has UPDATE privilege on ai_conversations';
  END IF;

  IF NOT has_table_privilege('service_role', 'public.ai_conversations', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.ai_conversations', 'INSERT')
     OR NOT has_table_privilege('service_role', 'public.ai_conversations', 'UPDATE') THEN
    RAISE EXCEPTION 'service_role lacks required SELECT/INSERT/UPDATE on ai_conversations';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.ai_messages', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.ai_messages', 'INSERT') THEN
    RAISE EXCEPTION 'service_role lacks required SELECT/INSERT on ai_messages';
  END IF;
  IF NOT has_table_privilege('service_role', 'public.ai_message_sources', 'SELECT')
     OR NOT has_table_privilege('service_role', 'public.ai_message_sources', 'INSERT') THEN
    RAISE EXCEPTION 'service_role lacks required SELECT/INSERT on ai_message_sources';
  END IF;

  IF has_table_privilege('authenticated', 'public.ai_conversations', 'DELETE')
     OR has_table_privilege('authenticated', 'public.ai_conversations', 'TRUNCATE')
     OR has_table_privilege('authenticated', 'public.ai_conversations', 'REFERENCES')
     OR has_table_privilege('authenticated', 'public.ai_conversations', 'TRIGGER') THEN
    RAISE EXCEPTION 'authenticated role has an unexpected privilege on ai_conversations';
  END IF;
  IF has_table_privilege('authenticated', 'public.ai_messages', 'UPDATE')
     OR has_table_privilege('authenticated', 'public.ai_messages', 'DELETE')
     OR has_table_privilege('authenticated', 'public.ai_messages', 'TRUNCATE')
     OR has_table_privilege('authenticated', 'public.ai_messages', 'REFERENCES')
     OR has_table_privilege('authenticated', 'public.ai_messages', 'TRIGGER') THEN
    RAISE EXCEPTION 'authenticated role has an unexpected UPDATE/DELETE/non-DML privilege on ai_messages';
  END IF;
  IF has_table_privilege('authenticated', 'public.ai_message_sources', 'UPDATE')
     OR has_table_privilege('authenticated', 'public.ai_message_sources', 'DELETE')
     OR has_table_privilege('authenticated', 'public.ai_message_sources', 'TRUNCATE')
     OR has_table_privilege('authenticated', 'public.ai_message_sources', 'REFERENCES')
     OR has_table_privilege('authenticated', 'public.ai_message_sources', 'TRIGGER') THEN
    RAISE EXCEPTION 'authenticated role has an unexpected privilege on ai_message_sources';
  END IF;
  IF has_table_privilege('anon', 'public.ai_conversations', 'SELECT')
     OR has_table_privilege('anon', 'public.ai_messages', 'SELECT')
     OR has_table_privilege('anon', 'public.ai_message_sources', 'SELECT') THEN
    RAISE EXCEPTION 'anon role unexpectedly has SELECT privilege on AI conversation tables';
  END IF;

  IF EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public' AND p.tablename = 'ai_messages'
      AND coalesce(p.qual, '') ILIKE '%ai_message_sources%'
  ) THEN
    RAISE EXCEPTION 'ai_messages policy contains an invalid direct reference to ai_message_sources';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'documents'
      AND column_name = 'department_code'
  ) THEN
    RAISE EXCEPTION 'documents.department_code is missing';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public' AND p.tablename = 'document_chunks'
      AND p.policyname = 'document_chunks_department_select' AND p.cmd = 'SELECT'
      AND coalesce(p.qual, '') ILIKE '%d.id = document_chunks.document_id%'
      AND coalesce(p.qual, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
  ) THEN
    RAISE EXCEPTION 'document chunk SELECT policy must require a matching parent document in the same organization';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public' AND p.tablename = 'document_chunks'
      AND p.policyname = 'document_chunks_department_insert' AND p.cmd = 'INSERT'
      AND coalesce(p.with_check, '') ILIKE '%d.id = document_chunks.document_id%'
      AND coalesce(p.with_check, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
  ) THEN
    RAISE EXCEPTION 'document chunk INSERT policy must require a matching parent document in the same organization';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public' AND p.tablename = 'document_chunks'
      AND p.policyname = 'document_chunks_department_update' AND p.cmd = 'UPDATE'
      AND coalesce(p.qual, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
      AND coalesce(p.with_check, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
  ) THEN
    RAISE EXCEPTION 'document chunk UPDATE policy must preserve parent organization consistency';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public' AND p.tablename = 'document_chunks'
      AND p.policyname = 'document_chunks_department_delete' AND p.cmd = 'DELETE'
      AND coalesce(p.qual, '') ILIKE '%d.id = document_chunks.document_id%'
      AND coalesce(p.qual, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
  ) THEN
    RAISE EXCEPTION 'document chunk DELETE policy must require a matching parent document in the same organization';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger t
    WHERE t.tgrelid = 'public.road_sections'::regclass
      AND t.tgname = 'enforce_road_section_organization'
      AND NOT t.tgisinternal
  ) THEN
    RAISE EXCEPTION 'road-section organization integrity trigger is missing';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_schema = 'public' AND table_name = 'road_sections'
      AND column_name = 'organization_id' AND is_nullable = 'NO'
  ) THEN
    RAISE EXCEPTION 'road_sections.organization_id must be NOT NULL after migration 015';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_trigger t
    WHERE t.tgrelid = 'public.roads'::regclass
      AND t.tgname = 'prevent_road_organization_change_with_sections'
      AND NOT t.tgisinternal
  ) THEN
    RAISE EXCEPTION 'road organization-change guard trigger is missing';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private'
      AND p.proname = 'prevent_road_organization_change_with_sections'
      AND p.prosecdef AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'road organization-change guard must be SECURITY DEFINER with empty search_path';
  END IF;
  IF has_function_privilege('anon', 'private.prevent_road_organization_change_with_sections()', 'EXECUTE')
     OR has_function_privilege('authenticated', 'private.prevent_road_organization_change_with_sections()', 'EXECUTE')
     OR has_function_privilege('service_role', 'private.prevent_road_organization_change_with_sections()', 'EXECUTE') THEN
    RAISE EXCEPTION 'API roles unexpectedly have direct EXECUTE on road organization-change guard';
  END IF;
  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private' AND p.proname = 'enforce_road_section_organization'
      AND p.prosecdef AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'Road-section trigger function must be SECURITY DEFINER with empty search_path';
  END IF;
  IF has_function_privilege('anon', 'private.enforce_road_section_organization()', 'EXECUTE')
     OR has_function_privilege('authenticated', 'private.enforce_road_section_organization()', 'EXECUTE')
     OR has_function_privilege('service_role', 'private.enforce_road_section_organization()', 'EXECUTE') THEN
    RAISE EXCEPTION 'API roles unexpectedly have direct EXECUTE on the road-section trigger function';
  END IF;

  SELECT p.prosecdef, pg_get_function_identity_arguments(p.oid) AS args INTO match_function
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
  WHERE n.nspname = 'public' AND p.proname = 'match_document_chunks'
  ORDER BY p.oid LIMIT 1;
  IF match_function IS NULL THEN RAISE EXCEPTION 'public.match_document_chunks function is missing'; END IF;
  IF match_function.prosecdef THEN RAISE EXCEPTION 'public.match_document_chunks must remain SECURITY INVOKER'; END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public' AND p.proname = 'create_organization_for_current_user'
      AND p.prosecdef AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'create_organization_for_current_user must be SECURITY DEFINER with empty search_path';
  END IF;
  IF has_function_privilege('anon', 'public.create_organization_for_current_user(text,text)', 'EXECUTE') THEN
    RAISE EXCEPTION 'anonymous execution is unexpectedly allowed on organization creation';
  END IF;
  IF NOT has_function_privilege('authenticated', 'public.create_organization_for_current_user(text,text)', 'EXECUTE') THEN
    RAISE EXCEPTION 'authenticated role cannot execute organization creation function';
  END IF;
  IF has_function_privilege('service_role', 'public.create_organization_for_current_user(text,text)', 'EXECUTE') THEN
    RAISE EXCEPTION 'service_role unexpectedly can execute organization creation function';
  END IF;

  RAISE NOTICE 'Authorization catalog checks passed. Runtime JWT/RLS tests are still required.';
END
$checks$;


-- Migration 018 profile/role grant regression checks.
DO $profile_grant_checks$
DECLARE
  expected_privilege record;
BEGIN
  IF has_table_privilege('anon', 'public.user_department_roles', 'SELECT')
     OR has_table_privilege('anon', 'public.user_department_roles', 'INSERT')
     OR has_table_privilege('anon', 'public.user_department_roles', 'UPDATE')
     OR has_table_privilege('anon', 'public.user_department_roles', 'DELETE')
     OR has_table_privilege('anon', 'public.user_department_roles', 'TRUNCATE')
     OR has_table_privilege('anon', 'public.user_department_roles', 'REFERENCES')
     OR has_table_privilege('anon', 'public.user_department_roles', 'TRIGGER') THEN
    RAISE EXCEPTION 'anon retains a privilege on public.user_department_roles';
  END IF;

  IF NOT has_table_privilege('authenticated', 'public.user_profiles', 'SELECT') THEN
    RAISE EXCEPTION 'authenticated must retain SELECT on public.user_profiles';
  END IF;

  IF has_table_privilege('authenticated', 'public.user_profiles', 'INSERT')
     OR has_table_privilege('authenticated', 'public.user_profiles', 'UPDATE')
     OR has_table_privilege('authenticated', 'public.user_profiles', 'DELETE')
     OR has_table_privilege('authenticated', 'public.user_profiles', 'TRUNCATE')
     OR has_table_privilege('authenticated', 'public.user_profiles', 'REFERENCES')
     OR has_table_privilege('authenticated', 'public.user_profiles', 'TRIGGER') THEN
    RAISE EXCEPTION 'authenticated retains broad table-level mutation/structural privileges on public.user_profiles';
  END IF;

  IF NOT has_column_privilege('authenticated', 'public.user_profiles', 'id', 'INSERT')
     OR NOT has_column_privilege('authenticated', 'public.user_profiles', 'full_name', 'INSERT') THEN
    RAISE EXCEPTION 'authenticated must retain INSERT on user_profiles(id, full_name)';
  END IF;

  IF has_column_privilege('authenticated', 'public.user_profiles', 'organization_id', 'INSERT')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'department_id', 'INSERT')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'employee_code', 'INSERT')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'is_active', 'INSERT')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'job_title', 'INSERT')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'created_at', 'INSERT')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'updated_at', 'INSERT') THEN
    RAISE EXCEPTION 'authenticated retains INSERT privilege on protected user_profiles columns';
  END IF;

  IF NOT has_column_privilege('authenticated', 'public.user_profiles', 'full_name', 'UPDATE') THEN
    RAISE EXCEPTION 'authenticated must retain UPDATE on user_profiles.full_name';
  END IF;

  IF has_column_privilege('authenticated', 'public.user_profiles', 'organization_id', 'UPDATE')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'department_id', 'UPDATE')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'employee_code', 'UPDATE')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'is_active', 'UPDATE')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'job_title', 'UPDATE')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'id', 'UPDATE')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'created_at', 'UPDATE')
     OR has_column_privilege('authenticated', 'public.user_profiles', 'updated_at', 'UPDATE') THEN
    RAISE EXCEPTION 'authenticated retains UPDATE privilege on protected user_profiles columns';
  END IF;
END;
$profile_grant_checks$;
