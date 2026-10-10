-- Runtime RLS regression test for road department permissions.
-- Runs only against the disposable local Supabase database in CI.
-- Uses synthetic auth.users and request.jwt.claim.sub values; this exercises
-- PostgreSQL RLS under the authenticated role, but is NOT a substitute for
-- real signed JWT requests through the staging PostgREST/Data API.
-- All fixtures are rolled back at the end.

BEGIN;

INSERT INTO auth.users (
  id, aud, role, email, encrypted_password, email_confirmed_at,
  raw_app_meta_data, raw_user_meta_data, created_at, updated_at
) VALUES
  ('a1000000-0000-4000-8000-000000000001', 'authenticated', 'authenticated', 'rls-admin@example.invalid', '', now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a1000000-0000-4000-8000-000000000002', 'authenticated', 'authenticated', 'rls-road-manager@example.invalid', '', now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a1000000-0000-4000-8000-000000000003', 'authenticated', 'authenticated', 'rls-road-readonly@example.invalid', '', now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a1000000-0000-4000-8000-000000000004', 'authenticated', 'authenticated', 'rls-finance@example.invalid', '', now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a1000000-0000-4000-8000-000000000005', 'authenticated', 'authenticated', 'rls-unassigned@example.invalid', '', now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now()),
  ('a1000000-0000-4000-8000-000000000006', 'authenticated', 'authenticated', 'rls-other-org@example.invalid', '', now(), '{"provider":"email","providers":["email"]}'::jsonb, '{}'::jsonb, now(), now())
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.organizations (id, name, code) VALUES
  ('b1000000-0000-4000-8000-000000000001', 'RLS Test Organization A', 'RLS-TEST-A'),
  ('b1000000-0000-4000-8000-000000000002', 'RLS Test Organization B', 'RLS-TEST-B')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.organization_members (organization_id, user_id, role, is_active) VALUES
  ('b1000000-0000-4000-8000-000000000001', 'a1000000-0000-4000-8000-000000000001', 'admin', true),
  ('b1000000-0000-4000-8000-000000000001', 'a1000000-0000-4000-8000-000000000002', 'member', true),
  ('b1000000-0000-4000-8000-000000000001', 'a1000000-0000-4000-8000-000000000003', 'member', true),
  ('b1000000-0000-4000-8000-000000000001', 'a1000000-0000-4000-8000-000000000004', 'member', true),
  ('b1000000-0000-4000-8000-000000000001', 'a1000000-0000-4000-8000-000000000005', 'member', true),
  ('b1000000-0000-4000-8000-000000000002', 'a1000000-0000-4000-8000-000000000006', 'member', true)
ON CONFLICT (organization_id, user_id) DO NOTHING;

INSERT INTO public.departments (id, organization_id, name, code) VALUES
  ('c1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000001', 'RLS Road Asset', 'road_asset'),
  ('c1000000-0000-4000-8000-000000000002', 'b1000000-0000-4000-8000-000000000001', 'RLS Finance', 'finance')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.user_department_roles (organization_id, user_id, department_id, role, is_active) VALUES
  ('b1000000-0000-4000-8000-000000000001', 'a1000000-0000-4000-8000-000000000002', 'c1000000-0000-4000-8000-000000000001', 'department_manager', true),
  ('b1000000-0000-4000-8000-000000000001', 'a1000000-0000-4000-8000-000000000003', 'c1000000-0000-4000-8000-000000000001', 'read_only', true),
  ('b1000000-0000-4000-8000-000000000001', 'a1000000-0000-4000-8000-000000000004', 'c1000000-0000-4000-8000-000000000002', 'department_manager', true)
ON CONFLICT (organization_id, user_id, department_id) DO NOTHING;

INSERT INTO public.roads (id, organization_id, road_code, name) VALUES
  ('d1000000-0000-4000-8000-000000000001', 'b1000000-0000-4000-8000-000000000001', 'RLS-A-ROAD', 'RLS Test Road A'),
  ('d1000000-0000-4000-8000-000000000002', 'b1000000-0000-4000-8000-000000000002', 'RLS-B-ROAD', 'RLS Test Road B')
ON CONFLICT (id) DO NOTHING;

-- Organization admin: sees its organization's road, not another tenant's road.
SET LOCAL request.jwt.claim.sub = 'a1000000-0000-4000-8000-000000000001';
SET LOCAL ROLE authenticated;
DO $test$
DECLARE visible_count integer;
BEGIN
  SELECT count(*) INTO visible_count FROM public.roads;
  IF visible_count <> 1 THEN
    RAISE EXCEPTION 'RLS FAIL: org admin expected 1 road, saw %', visible_count;
  END IF;
END
$test$;
RESET ROLE;

-- Road manager: can see and create road records within the assigned organization.
SET LOCAL request.jwt.claim.sub = 'a1000000-0000-4000-8000-000000000002';
SET LOCAL ROLE authenticated;
DO $test$
DECLARE visible_count integer;
BEGIN
  SELECT count(*) INTO visible_count FROM public.roads;
  IF visible_count <> 1 THEN
    RAISE EXCEPTION 'RLS FAIL: road manager expected 1 road, saw %', visible_count;
  END IF;
  INSERT INTO public.roads (organization_id, road_code, name)
  VALUES ('b1000000-0000-4000-8000-000000000001', 'RLS-MANAGER-INSERT', 'Manager test insert');
END
$test$;
RESET ROLE;

-- Read-only road user: can read but cannot insert or update.
SET LOCAL request.jwt.claim.sub = 'a1000000-0000-4000-8000-000000000003';
SET LOCAL ROLE authenticated;
DO $test$
DECLARE visible_count integer; changed_count integer;
BEGIN
  SELECT count(*) INTO visible_count FROM public.roads;
  IF visible_count <> 1 THEN
    RAISE EXCEPTION 'RLS FAIL: road read-only user expected 1 road, saw %', visible_count;
  END IF;
  UPDATE public.roads SET name = 'SHOULD NOT CHANGE'
  WHERE id = 'd1000000-0000-4000-8000-000000000001';
  GET DIAGNOSTICS changed_count = ROW_COUNT;
  IF changed_count <> 0 THEN
    RAISE EXCEPTION 'RLS FAIL: read-only user updated % road row(s)', changed_count;
  END IF;
  BEGIN
    INSERT INTO public.roads (organization_id, road_code, name)
    VALUES ('b1000000-0000-4000-8000-000000000001', 'RLS-READONLY-INSERT', 'Must be denied');
    RAISE EXCEPTION 'RLS FAIL: read-only user unexpectedly inserted a road';
  EXCEPTION WHEN insufficient_privilege THEN
    NULL;
  END;
END
$test$;
RESET ROLE;

-- Finance-only, unassigned, and member of another organization cannot see
-- the test road in organization A. The other-organization user has membership
-- in organization B but deliberately has no road_asset assignment there.
SET LOCAL request.jwt.claim.sub = 'a1000000-0000-4000-8000-000000000004';
SET LOCAL ROLE authenticated;
DO $test$
DECLARE visible_count integer;
BEGIN
  SELECT count(*) INTO visible_count FROM public.roads;
  IF visible_count <> 0 THEN
    RAISE EXCEPTION 'RLS FAIL: finance-only user saw % road row(s)', visible_count;
  END IF;
END
$test$;
RESET ROLE;

SET LOCAL request.jwt.claim.sub = 'a1000000-0000-4000-8000-000000000005';
SET LOCAL ROLE authenticated;
DO $test$
DECLARE visible_count integer;
BEGIN
  SELECT count(*) INTO visible_count FROM public.roads;
  IF visible_count <> 0 THEN
    RAISE EXCEPTION 'RLS FAIL: unassigned user saw % road row(s)', visible_count;
  END IF;
END
$test$;
RESET ROLE;

SET LOCAL request.jwt.claim.sub = 'a1000000-0000-4000-8000-000000000006';
SET LOCAL ROLE authenticated;
DO $test$
DECLARE visible_count integer;
BEGIN
  SELECT count(*) INTO visible_count FROM public.roads;
  IF visible_count <> 0 THEN
    RAISE EXCEPTION 'RLS FAIL: cross-organization user without road role saw % road row(s)', visible_count;
  END IF;
END
$test$;
RESET ROLE;

ROLLBACK;
