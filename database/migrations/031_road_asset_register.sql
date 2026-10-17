-- Road infrastructure asset register for the Road Asset department.
-- Review and test in staging before applying to production.
CREATE TABLE IF NOT EXISTS public.road_assets (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  road_id uuid NOT NULL REFERENCES public.roads(id) ON DELETE RESTRICT,
  road_section_id uuid REFERENCES public.road_sections(id) ON DELETE SET NULL,
  asset_code text NOT NULL CHECK (length(trim(asset_code)) BETWEEN 1 AND 80),
  asset_type text NOT NULL CHECK (asset_type IN (
    'bridge', 'culvert', 'drainage', 'sign', 'guardrail',
    'retaining_wall', 'marker', 'lighting', 'other'
  )),
  name text NOT NULL CHECK (length(trim(name)) BETWEEN 1 AND 200),
  chainage_km numeric(10,3) CHECK (chainage_km IS NULL OR chainage_km >= 0),
  latitude numeric(10,7) CHECK (latitude IS NULL OR latitude BETWEEN -90 AND 90),
  longitude numeric(10,7) CHECK (longitude IS NULL OR longitude BETWEEN -180 AND 180),
  condition_rating smallint CHECK (condition_rating IS NULL OR condition_rating BETWEEN 1 AND 5),
  criticality text NOT NULL DEFAULT 'medium' CHECK (criticality IN ('low', 'medium', 'high', 'critical')),
  status text NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'needs_inspection', 'maintenance_required', 'out_of_service', 'retired')),
  installation_date date,
  last_inspected_at date,
  notes text CHECK (notes IS NULL OR length(notes) <= 4000),
  created_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT road_assets_org_code_unique UNIQUE (organization_id, asset_code)
);

CREATE INDEX IF NOT EXISTS road_assets_org_road_idx ON public.road_assets (organization_id, road_id);
CREATE INDEX IF NOT EXISTS road_assets_org_type_status_idx ON public.road_assets (organization_id, asset_type, status);
CREATE INDEX IF NOT EXISTS road_assets_section_idx ON public.road_assets (road_section_id);

ALTER TABLE public.road_assets ENABLE ROW LEVEL SECURITY;

-- A permissive policy is required for access; restrictive policies alone cannot grant it.
DROP POLICY IF EXISTS road_assets_department_access ON public.road_assets;
CREATE POLICY road_assets_department_access
  ON public.road_assets FOR ALL TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

-- Defense in depth: read-only members may not delete records.
DROP POLICY IF EXISTS road_assets_delete_write_roles ON public.road_assets;
CREATE POLICY road_assets_delete_write_roles
  ON public.road_assets AS RESTRICTIVE FOR DELETE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

GRANT SELECT, INSERT, UPDATE, DELETE ON public.road_assets TO authenticated;

-- Enforce organization/parent consistency even when writes do not use the API.
CREATE OR REPLACE FUNCTION private.enforce_road_asset_parent_scope()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
DECLARE
  road_org uuid;
  section_road_id uuid;
  section_org uuid;
BEGIN
  SELECT r.organization_id INTO road_org
  FROM public.roads AS r WHERE r.id = NEW.road_id;
  IF NOT FOUND OR road_org IS DISTINCT FROM NEW.organization_id THEN
    RAISE EXCEPTION 'Road asset must reference a road in the same organization'
      USING ERRCODE = '23514';
  END IF;

  IF NEW.road_section_id IS NOT NULL THEN
    SELECT s.road_id, s.organization_id INTO section_road_id, section_org
    FROM public.road_sections AS s WHERE s.id = NEW.road_section_id;
    IF NOT FOUND OR section_road_id IS DISTINCT FROM NEW.road_id
       OR section_org IS DISTINCT FROM NEW.organization_id THEN
      RAISE EXCEPTION 'Road asset section must belong to its road and organization'
        USING ERRCODE = '23514';
    END IF;
  END IF;

  NEW.updated_at := now();
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION private.enforce_road_asset_parent_scope() FROM PUBLIC, anon, authenticated, service_role;

DROP TRIGGER IF EXISTS road_assets_parent_scope ON public.road_assets;
CREATE TRIGGER road_assets_parent_scope
BEFORE INSERT OR UPDATE OF organization_id, road_id, road_section_id
ON public.road_assets
FOR EACH ROW EXECUTE FUNCTION private.enforce_road_asset_parent_scope();

DROP TRIGGER IF EXISTS road_assets_updated_at ON public.road_assets;
CREATE TRIGGER road_assets_updated_at
BEFORE UPDATE ON public.road_assets
FOR EACH ROW EXECUTE FUNCTION private.enforce_road_asset_parent_scope();

COMMENT ON TABLE public.road_assets IS
  'Road-specific infrastructure asset register; distinct from general organizational assets.';
