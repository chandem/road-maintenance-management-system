-- Read-only preflight for the proposed department-role release.
-- Run as a database administrator against an isolated staging project before
-- applying migrations 011-018. This script makes no schema or data changes.
-- It reports observations; a PASS here is not a substitute for JWT/API tests.

WITH expected_relations(name) AS (
  VALUES
    ('public.roads'),
    ('public.road_sections'),
    ('public.road_inspections'),
    ('public.materials'),
    ('public.maintenance_plans'),
    ('public.work_orders'),
    ('public.machinery'),
    ('public.assets'),
    ('public.budgets'),
    ('public.expenses'),
    ('public.employees'),
    ('public.documents'),
    ('public.document_chunks'),
    ('public.ai_analysis_runs'),
    ('public.ai_recommendations'),
    ('public.departments'),
    ('public.organization_members'),
    ('public.organizations'),
    ('public.user_department_roles'),
    ('public.user_profiles')
)
SELECT
  'required_relation' AS check_group,
  name AS check_name,
  CASE WHEN to_regclass(name) IS NOT NULL THEN 'PASS' ELSE 'BLOCKER' END AS result,
  CASE WHEN to_regclass(name) IS NOT NULL
       THEN 'Relation exists'
       ELSE 'Required relation missing; do not apply dependent migrations'
  END AS details
FROM expected_relations
UNION ALL
SELECT
  'planned_relation' AS check_group,
  name AS check_name,
  CASE WHEN to_regclass(name) IS NULL THEN 'EXPECTED_BEFORE_014' ELSE 'PRESENT' END AS result,
  'Migration 014 is expected to create this relation if absent; verify backend schema expectations'
FROM (VALUES
  ('public.ai_conversations'),
  ('public.ai_messages'),
  ('public.ai_message_sources')
) AS planned(name)
UNION ALL
SELECT
  'required_function' AS check_group,
  signature AS check_name,
  CASE WHEN to_regprocedure(signature) IS NOT NULL THEN 'PASS' ELSE 'BLOCKER' END AS result,
  CASE WHEN to_regprocedure(signature) IS NOT NULL
       THEN 'Function signature exists'
       ELSE 'Required function missing; reconcile schema before applying proposals'
  END AS details
FROM (VALUES
  ('public.has_department_role(uuid,text,text[])'),
  ('public.create_organization_for_current_user(text,text)'),
  ('private.is_org_admin(uuid)'),
  ('private.is_org_member(uuid)')
) AS required(signature)
UNION ALL
SELECT
  'required_column' AS check_group,
  item.table_name || '.' || item.column_name AS check_name,
  CASE WHEN EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'public'
      AND c.table_name = item.table_name
      AND c.column_name = item.column_name
  ) THEN 'PASS' ELSE 'BLOCKER' END AS result,
  CASE WHEN EXISTS (
    SELECT 1
    FROM information_schema.columns c
    WHERE c.table_schema = 'public'
      AND c.table_name = item.table_name
      AND c.column_name = item.column_name
  ) THEN 'Required column exists'
    ELSE 'Required column missing; check migration dependency and current schema'
  END AS details
FROM (VALUES
  ('roads','organization_id'),
  ('road_sections','road_id'),
  ('road_sections','organization_id'),
  ('road_inspections','organization_id'),
  ('materials','organization_id'),
  ('maintenance_plans','organization_id'),
  ('work_orders','organization_id'),
  ('machinery','organization_id'),
  ('assets','organization_id'),
  ('budgets','organization_id'),
  ('expenses','organization_id'),
  ('employees','organization_id'),
  ('documents','organization_id'),
  ('document_chunks','document_id'),
  ('document_chunks','organization_id'),
  ('user_profiles','id'),
  ('user_profiles','organization_id'),
  ('user_profiles','full_name')
) AS item(table_name,column_name)
UNION ALL
SELECT
  'road_section_integrity' AS check_group,
  'sections_with_missing_parent_or_org_mismatch' AS check_name,
  CASE WHEN EXISTS (
    SELECT 1
    FROM public.road_sections s
    LEFT JOIN public.roads r ON r.id = s.road_id
    WHERE r.id IS NULL
       OR r.organization_id IS NULL
       OR (s.organization_id IS NOT NULL AND s.organization_id <> r.organization_id)
  ) THEN 'BLOCKER' ELSE 'PASS' END AS result,
  'Read-only check. If BLOCKER, migration 015 will abort; resolve data in staging first.'
WHERE to_regclass('public.road_sections') IS NOT NULL
  AND to_regclass('public.roads') IS NOT NULL
ORDER BY check_group, check_name;

-- Review these separately; the first query intentionally reports only existence.
-- It does not prove safe function bodies, grant state, policy correctness, or API behavior.
SELECT
  n.nspname AS schema_name,
  p.proname AS function_name,
  pg_get_function_identity_arguments(p.oid) AS arguments,
  p.prosecdef AS security_definer,
  p.proconfig AS function_settings,
  pg_get_userbyid(p.proowner) AS owner
FROM pg_proc p
JOIN pg_namespace n ON n.oid = p.pronamespace
WHERE (n.nspname = 'public' AND p.proname IN (
         'has_department_role', 'create_organization_for_current_user'
       ))
   OR (n.nspname = 'private' AND p.proname IN (
         'has_department_role', 'is_org_admin', 'is_org_member'
       ))
ORDER BY n.nspname, p.proname;

-- Verify current RLS/policies for the core organization tables. Review policy
-- expressions manually; this listing does not test them with an authenticated JWT.
SELECT tablename, policyname, permissive, roles, cmd, qual, with_check
FROM pg_policies
WHERE schemaname = 'public'
  AND tablename IN (
    'user_profiles', 'organization_members', 'user_department_roles',
    'departments', 'organizations', 'roads', 'road_sections',
    'road_inspections', 'documents', 'document_chunks'
  )
ORDER BY tablename, policyname;
