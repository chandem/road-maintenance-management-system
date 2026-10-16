-- Road infrastructure asset register for the Road Asset department.
-- Apply through the reviewed migration workflow; do not run against production until approved.
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

CREATE INDEX IF NOT EXISTS road_assets_org_road_idx
  ON public.road_assets (organization_id, road_id);
CREATE INDEX IF NOT EXISTS road_assets_org_type_status_idx
  ON public.road_assets (organization_id, asset_type, status);
CREATE INDEX IF NOT EXISTS road_assets_section_idx
  ON public.road_assets (road_section_id);

ALTER TABLE public.road_assets ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS road_assets_org_access ON public.road_assets;
CREATE POLICY road_assets_org_access
  ON public.road_assets AS RESTRICTIVE FOR ALL TO authenticated
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

CREATE OR REPLACE FUNCTION private.set_road_assets_updated_at()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = ''
AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END;
$$;
REVOKE ALL ON FUNCTION private.set_road_assets_updated_at() FROM PUBLIC, anon, authenticated, service_role;

DROP TRIGGER IF EXISTS road_assets_updated_at ON public.road_assets;
CREATE TRIGGER road_assets_updated_at
BEFORE UPDATE ON public.road_assets
FOR EACH ROW EXECUTE FUNCTION private.set_road_assets_updated_at();

COMMENT ON TABLE public.road_assets IS
  'Road-specific infrastructure asset register; distinct from general organizational assets.';
