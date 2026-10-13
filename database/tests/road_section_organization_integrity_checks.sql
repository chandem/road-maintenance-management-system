-- Road/road-section organization-integrity regression tests.
-- Runs only against the disposable local Supabase database in CI.
-- All synthetic fixtures are rolled back; never run this as a production migration.

BEGIN;

INSERT INTO public.organizations (id, name, code)
VALUES
  ('b7100000-0000-4000-8000-000000000001', 'Section Integrity Test A', 'SECTION-INT-A'),
  ('b7100000-0000-4000-8000-000000000002', 'Section Integrity Test B', 'SECTION-INT-B')
ON CONFLICT (id) DO NOTHING;

INSERT INTO public.roads (id, organization_id, road_code, name)
VALUES
  ('d7100000-0000-4000-8000-000000000001', 'b7100000-0000-4000-8000-000000000001', 'SECTION-ROAD-A', 'Section Integrity Road A'),
  ('d7100000-0000-4000-8000-000000000002', 'b7100000-0000-4000-8000-000000000002', 'SECTION-ROAD-B', 'Section Integrity Road B')
ON CONFLICT (id) DO NOTHING;

DO $test$
DECLARE
  v_section_id uuid := 'e7100000-0000-4000-8000-000000000001';
  v_org_id uuid;
  v_rejected boolean;
BEGIN
  -- A valid section derives organization_id from its parent when omitted.
  INSERT INTO public.road_sections
    (id, road_id, section_code, start_chainage_km, end_chainage_km)
  VALUES
    (v_section_id, 'd7100000-0000-4000-8000-000000000001', 'SECTION-A-001', 0, 0.5)
  ON CONFLICT (id) DO NOTHING;

  SELECT organization_id INTO v_org_id
  FROM public.road_sections WHERE id = v_section_id;

  IF v_org_id IS DISTINCT FROM 'b7100000-0000-4000-8000-000000000001'::uuid THEN
    RAISE EXCEPTION 'FAIL: section organization_id was not derived from its parent road';
  END IF;

  -- A caller cannot explicitly assign the section to a different organization.
  v_rejected := false;
  BEGIN
    INSERT INTO public.road_sections
      (road_id, organization_id, section_code, start_chainage_km, end_chainage_km)
    VALUES
      ('d7100000-0000-4000-8000-000000000001',
       'b7100000-0000-4000-8000-000000000002',
       'SECTION-A-MISMATCH', 0.5, 1.0);
  EXCEPTION WHEN check_violation THEN
    v_rejected := true;
  END;
  IF NOT v_rejected THEN
    RAISE EXCEPTION 'FAIL: mismatched section organization was accepted';
  END IF;

  -- A section cannot be re-parented to a road in another organization.
  v_rejected := false;
  BEGIN
    UPDATE public.road_sections
    SET road_id = 'd7100000-0000-4000-8000-000000000002'
    WHERE id = v_section_id;
  EXCEPTION WHEN check_violation THEN
    v_rejected := true;
  END;
  IF NOT v_rejected THEN
    RAISE EXCEPTION 'FAIL: cross-organization section re-parenting was accepted';
  END IF;

  -- A parent road cannot change organization while it still has sections.
  v_rejected := false;
  BEGIN
    UPDATE public.roads
    SET organization_id = 'b7100000-0000-4000-8000-000000000002'
    WHERE id = 'd7100000-0000-4000-8000-000000000001';
  EXCEPTION WHEN check_violation THEN
    v_rejected := true;
  END;
  IF NOT v_rejected THEN
    RAISE EXCEPTION 'FAIL: parent road organization change with sections was accepted';
  END IF;

  RAISE NOTICE 'PASS: road-section organization integrity checks';
END
$test$;

ROLLBACK;
