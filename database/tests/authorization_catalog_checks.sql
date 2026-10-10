-- AI-RMMS authorization catalog regression checks.
-- Run in an ISOLATED staging database after applying migrations 011-017.
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
    'ai_analysis_runs',
    'ai_recommendations',
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
    'ai_analysis_runs',
    'ai_recommendations',
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

  -- Restrictive policies narrow access but cannot grant it by themselves.
  -- Require at least one applicable permissive policy per table as well;
  -- otherwise a missing baseline policy can make every request fail closed.
  FOREACH rel_name IN ARRAY required_policy_tables LOOP
    IF NOT EXISTS (
      SELECT 1
      FROM pg_policies p
      WHERE p.schemaname = 'public'
        AND p.tablename = rel_name
        AND p.permissive = 'PERMISSIVE'
        AND 'authenticated' = ANY(p.roles)
    ) THEN
      RAISE EXCEPTION
        'No permissive authenticated baseline policy found on public.%', rel_name;
    END IF;
  END LOOP;

  -- A policy existing on a table is not enough: it could be permissive-only,
  -- leaving organization-level policies broader than intended. For each
  -- department-protected business table, require restrictive coverage for
  -- SELECT, INSERT, UPDATE, and DELETE (a FOR ALL policy covers each command).
  FOREACH rel_name IN ARRAY ARRAY[
    'roads', 'road_sections', 'road_inspections',
    'materials', 'maintenance_plans', 'work_orders',
    'machinery', 'assets', 'budgets', 'expenses', 'employees',
    'documents', 'document_chunks', 'ai_analysis_runs', 'ai_recommendations'
  ] LOOP
    IF EXISTS (
      SELECT 1
      FROM unnest(ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE']::text[]) AS cmd_name(cmd)
      WHERE NOT EXISTS (
        SELECT 1
        FROM pg_policies p
        WHERE p.schemaname = 'public'
          AND p.tablename = rel_name
          AND p.permissive = 'RESTRICTIVE'
          AND 'authenticated' = ANY(p.roles)
          AND p.cmd IN ('ALL', cmd_name.cmd)
      )
    ) THEN
      RAISE EXCEPTION 'Missing restrictive command coverage (SELECT/INSERT/UPDATE/DELETE) for public.%', rel_name;
    END IF;
  END LOOP;

  -- AI conversation tables intentionally expose fewer commands. Require
  -- restrictive policies only for the commands that authenticated clients use.
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

  -- Ensure the restrictive INSERT policy still prevents authenticated clients
  -- from forging assistant/system messages. Policy presence alone is insufficient.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'ai_messages'
      AND policyname = 'ai_messages_department_insert'
      AND permissive = 'RESTRICTIVE'
      AND cmd = 'INSERT'
      AND 'authenticated' = ANY(roles)
      AND coalesce(with_check, '') ILIKE '%role%'
      AND coalesce(with_check, '') ILIKE '%user%'
      AND coalesce(with_check, '') ILIKE '%has_department_role%'
  ) THEN
    RAISE EXCEPTION
      'ai_messages restrictive INSERT policy must enforce user-role messages and department authorization';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies
    WHERE schemaname = 'public' AND tablename = 'ai_message_sources'
      AND permissive = 'RESTRICTIVE' AND cmd = 'SELECT'
      AND 'authenticated' = ANY(roles)
  ) THEN
    RAISE EXCEPTION 'ai_message_sources missing restrictive SELECT policy';
  END IF;

  -- Non-admin road users may see only approved road-maintenance source types.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies
    WHERE schemaname = 'public'
      AND tablename = 'ai_message_sources'
      AND policyname = 'ai_message_sources_department_select'
      AND permissive = 'RESTRICTIVE'
      AND cmd = 'SELECT'
      AND 'authenticated' = ANY(roles)
      AND coalesce(qual, '') ILIKE '%source_type%'
      AND coalesce(qual, '') ILIKE '%road%'
      AND coalesce(qual, '') ILIKE '%work_order%'
      AND coalesce(qual, '') ILIKE '%has_department_role%'
  ) THEN
    RAISE EXCEPTION
      'ai_message_sources restrictive SELECT policy must limit non-admin evidence to authorized road-maintenance sources';
  END IF;

  -- RLS does not protect TRUNCATE. Normal authenticated users must not
  -- retain elevated table privileges from project defaults or older migrations.
  FOREACH rel_name IN ARRAY ARRAY[
    'roads', 'road_sections', 'road_inspections',
    'materials', 'maintenance_plans', 'work_orders',
    'machinery', 'assets', 'budgets', 'expenses', 'employees',
    'documents', 'document_chunks', 'ai_analysis_runs', 'ai_recommendations',
    'ai_conversations', 'ai_messages', 'ai_message_sources'
  ] LOOP
    IF has_table_privilege('authenticated', to_regclass(format('public.%I', rel_name)), 'TRUNCATE')
       OR has_table_privilege('authenticated', to_regclass(format('public.%I', rel_name)), 'REFERENCES')
       OR has_table_privilege('authenticated', to_regclass(format('public.%I', rel_name)), 'TRIGGER') THEN
      RAISE EXCEPTION
        'Authenticated role retains TRUNCATE/REFERENCES/TRIGGER on public.%', rel_name;
    END IF;
  END LOOP;

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

  -- SECURITY DEFINER is not sufficient by itself: the helper must pin an empty
  -- search_path so object resolution cannot be redirected by caller-controlled
  -- schemas. Migration 011 relies on the helper retaining this hardening.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private'
      AND p.proname = 'has_department_role'
      AND p.prosecdef
      AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'private.has_department_role must be SECURITY DEFINER with search_path set to empty';
  END IF;

  -- The exposed RPC wrapper is SECURITY INVOKER too; pin its path rather than
  -- relying on ambient role/session configuration.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname = 'has_department_role'
      AND NOT p.prosecdef
      AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'public.has_department_role must be SECURITY INVOKER with empty search_path';
  END IF;

  -- The SECURITY INVOKER public wrapper calls the private helper as the caller.
  -- Schema USAGE is therefore required for authenticated users, but not anon.
  IF NOT has_schema_privilege('authenticated', 'private', 'USAGE') THEN
    RAISE EXCEPTION 'authenticated role lacks USAGE on private schema required by role helper';
  END IF;
  IF has_schema_privilege('anon', 'private', 'USAGE') THEN
    RAISE EXCEPTION 'anon role unexpectedly has USAGE on private schema';
  END IF;

  IF NOT has_function_privilege(
    'authenticated',
    'private.has_department_role(uuid,text,text[])',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'authenticated role cannot execute private department-role helper';
  END IF;

  IF has_function_privilege(
       'anon',
       'private.has_department_role(uuid,text,text[])',
       'EXECUTE'
     )
     OR has_function_privilege(
       'service_role',
       'private.has_department_role(uuid,text,text[])',
       'EXECUTE'
     ) THEN
    RAISE EXCEPTION 'anon or service_role unexpectedly can execute private department-role helper';
  END IF;

  IF NOT has_function_privilege(
    'authenticated',
    'public.has_department_role(uuid,text,text[])',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'authenticated role cannot execute public department-role RPC wrapper';
  END IF;

  IF has_function_privilege(
       'anon',
       'public.has_department_role(uuid,text,text[])',
       'EXECUTE'
     )
     OR has_function_privilege(
       'service_role',
       'public.has_department_role(uuid,text,text[])',
       'EXECUTE'
     ) THEN
    RAISE EXCEPTION 'anon or service_role unexpectedly can execute public department-role RPC wrapper';
  END IF;

  IF NOT has_function_privilege(
    'authenticated',
    'public.has_department_role(uuid,text,text[])',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'authenticated role cannot execute public.has_department_role RPC wrapper';
  END IF;

  IF NOT has_function_privilege(
    'authenticated',
    'private.has_department_role(uuid,text,text[])',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'authenticated role cannot execute private.has_department_role helper';
  END IF;

  IF has_function_privilege(
    'anon',
    'public.has_department_role(uuid,text,text[])',
    'EXECUTE'
  ) OR has_function_privilege(
    'anon',
    'private.has_department_role(uuid,text,text[])',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'anon role unexpectedly has EXECUTE on department-role helper functions';
  END IF;

  IF has_function_privilege(
    'service_role',
    'private.has_department_role(uuid,text,text[])',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'service_role unexpectedly has EXECUTE on private department-role helper';
  END IF;

  -- Policies also depend on the private organization-admin helper. Keep it
  -- SECURITY DEFINER with a locked search_path, callable by authenticated only.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private'
      AND p.proname = 'is_org_admin'
      AND p.prosecdef
      AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'private.is_org_admin must be SECURITY DEFINER with empty search_path';
  END IF;

  IF NOT has_function_privilege(
    'authenticated',
    'private.is_org_admin(uuid)',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'authenticated role cannot execute private.is_org_admin';
  END IF;

  IF has_function_privilege(
    'anon',
    'private.is_org_admin(uuid)',
    'EXECUTE'
  ) OR has_function_privilege(
    'service_role',
    'private.is_org_admin(uuid)',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'anon or service_role unexpectedly has EXECUTE on private.is_org_admin';
  END IF;

  -- Migration 014 uses private.is_org_member in permissive and restrictive
  -- conversation policies. The private schema USAGE grant alone is insufficient:
  -- authenticated must also be able to execute this exact helper signature.
  IF NOT has_function_privilege(
    'authenticated',
    'private.is_org_member(uuid)',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION
      'authenticated role cannot execute private.is_org_member required by AI conversation policies';
  END IF;

  -- is_org_member is called from policies on AI conversation tables. Because
  -- it is SECURITY DEFINER, pin its search_path and prevent direct execution
  -- by anonymous/service roles; authenticated needs EXECUTE for policy checks.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private'
      AND p.proname = 'is_org_member'
      AND pg_get_function_identity_arguments(p.oid) = 'uuid'
      AND p.prosecdef
      AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION
      'private.is_org_member(uuid) must be SECURITY DEFINER with empty search_path';
  END IF;

  IF has_function_privilege(
       'anon',
       'private.is_org_member(uuid)',
       'EXECUTE'
     )
     OR has_function_privilege(
       'service_role',
       'private.is_org_member(uuid)',
       'EXECUTE'
     ) THEN
    RAISE EXCEPTION
      'anon or service_role unexpectedly has EXECUTE on private.is_org_member';
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

  -- Even organization admins must not impersonate another conversation owner
  -- when inserting a user-role message directly through the Data API.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_policies p
    WHERE p.schemaname = 'public'
      AND p.tablename = 'ai_messages'
      AND p.cmd = 'INSERT'
      AND 'authenticated' = ANY(p.roles)
      AND coalesce(p.with_check, '') ILIKE '%created_by%'
      AND coalesce(p.with_check, '') ILIKE '%auth.uid%'
  ) THEN
    RAISE EXCEPTION 'ai_messages INSERT policy must enforce conversation ownership';
  END IF;

  -- Message rows are append-only for authenticated clients. Without UPDATE,
  -- users cannot rewrite a user message into an assistant/system response.
  IF has_table_privilege('authenticated', 'public.ai_messages', 'UPDATE') THEN
    RAISE EXCEPTION 'authenticated role unexpectedly has UPDATE privilege on ai_messages';
  END IF;
  IF has_table_privilege('authenticated', 'public.ai_messages', 'DELETE') THEN
    RAISE EXCEPTION 'authenticated role unexpectedly has DELETE privilege on ai_messages';
  END IF;

  -- Authenticated users must not be able to fabricate AI evidence/source rows.
  IF has_table_privilege('authenticated', 'public.ai_message_sources', 'INSERT') THEN
    RAISE EXCEPTION 'authenticated role unexpectedly has INSERT privilege on ai_message_sources';
  END IF;

  -- These tables contain user conversations and trusted AI output. Verify that
  -- no stale grants survived a rerun against a pre-existing table definition.
  IF has_table_privilege('authenticated', 'public.ai_conversations', 'UPDATE') THEN
    RAISE EXCEPTION 'authenticated role unexpectedly has UPDATE privilege on ai_conversations';
  END IF;

  -- The trusted backend relies on explicit grants, not environment-specific
  -- default privileges, to save assistant replies and touch conversation time.
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

  -- Every chunk policy must require a matching parent document in the same
  -- organization, including the organization-admin branch. Otherwise an admin
  -- could create or update orphaned/cross-organization chunk rows.
  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public'
      AND p.tablename = 'document_chunks'
      AND p.policyname = 'document_chunks_department_select'
      AND p.cmd = 'SELECT'
      AND coalesce(p.qual, '') ILIKE '%d.id = document_chunks.document_id%'
      AND coalesce(p.qual, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
  ) THEN
    RAISE EXCEPTION 'document chunk SELECT policy must require a matching parent document in the same organization';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public'
      AND p.tablename = 'document_chunks'
      AND p.policyname = 'document_chunks_department_insert'
      AND p.cmd = 'INSERT'
      AND coalesce(p.with_check, '') ILIKE '%d.id = document_chunks.document_id%'
      AND coalesce(p.with_check, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
  ) THEN
    RAISE EXCEPTION 'document chunk INSERT policy must require a matching parent document in the same organization';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public'
      AND p.tablename = 'document_chunks'
      AND p.policyname = 'document_chunks_department_update'
      AND p.cmd = 'UPDATE'
      AND coalesce(p.qual, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
      AND coalesce(p.with_check, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
  ) THEN
    RAISE EXCEPTION 'document chunk UPDATE policy must preserve parent organization consistency';
  END IF;

  IF NOT EXISTS (
    SELECT 1 FROM pg_policies p
    WHERE p.schemaname = 'public'
      AND p.tablename = 'document_chunks'
      AND p.policyname = 'document_chunks_department_delete'
      AND p.cmd = 'DELETE'
      AND coalesce(p.qual, '') ILIKE '%d.id = document_chunks.document_id%'
      AND coalesce(p.qual, '') ILIKE '%d.organization_id = document_chunks.organization_id%'
  ) THEN
    RAISE EXCEPTION 'document chunk DELETE policy must require a matching parent document in the same organization';
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

  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.columns
    WHERE table_schema = 'public'
      AND table_name = 'road_sections'
      AND column_name = 'organization_id'
      AND is_nullable = 'NO'
  ) THEN
    RAISE EXCEPTION 'road_sections.organization_id must be NOT NULL after migration 015';
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'private'
      AND p.proname = 'enforce_road_section_organization'
      AND p.prosecdef
      AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'Road-section trigger function must be SECURITY DEFINER with empty search_path';
  END IF;

  IF has_function_privilege(
    'anon',
    'private.enforce_road_section_organization()',
    'EXECUTE'
  ) OR has_function_privilege(
    'authenticated',
    'private.enforce_road_section_organization()',
    'EXECUTE'
  ) OR has_function_privilege(
    'service_role',
    'private.enforce_road_section_organization()',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'API roles unexpectedly have direct EXECUTE on the road-section trigger function';
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

  -- Privileged organization creation must be callable by authenticated users only
  -- and the SECURITY DEFINER function must not depend on a caller-controlled path.
  IF NOT EXISTS (
    SELECT 1
    FROM pg_proc p
    JOIN pg_namespace n ON n.oid = p.pronamespace
    WHERE n.nspname = 'public'
      AND p.proname = 'create_organization_for_current_user'
      AND p.prosecdef
      AND p.proconfig @> ARRAY['search_path=""']
  ) THEN
    RAISE EXCEPTION 'create_organization_for_current_user must be SECURITY DEFINER with empty search_path';
  END IF;

  IF has_function_privilege(
       'anon',
       'public.create_organization_for_current_user(text,text)',
       'EXECUTE'
     ) THEN
    RAISE EXCEPTION 'anonymous execution is unexpectedly allowed on organization creation';
  END IF;

  IF NOT has_function_privilege(
    'authenticated',
    'public.create_organization_for_current_user(text,text)',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'authenticated role cannot execute organization creation function';
  END IF;

  IF has_function_privilege(
    'service_role',
    'public.create_organization_for_current_user(text,text)',
    'EXECUTE'
  ) THEN
    RAISE EXCEPTION 'service_role unexpectedly can execute organization creation function';
  END IF;

  RAISE NOTICE 'Authorization catalog checks passed. Runtime JWT/RLS tests are still required.';
END
$checks$;
