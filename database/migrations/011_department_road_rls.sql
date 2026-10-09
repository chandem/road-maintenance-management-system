-- Department-level access enforcement for road data.
-- This migration is intentionally reviewed in source control before production apply.
-- Organization administrators retain access; other users need an active road_asset role.
-- Existing permissive organization-membership policies remain in place and are narrowed
-- by these RESTRICTIVE policies (Postgres combines restrictive policies with AND).

-- has_department_role is SECURITY DEFINER and only needs to be callable by signed-in
-- users for RLS checks. Remove the default PUBLIC and anonymous execution grants.
REVOKE EXECUTE ON FUNCTION public.has_department_role(uuid, text, text[]) FROM PUBLIC;
REVOKE EXECUTE ON FUNCTION public.has_department_role(uuid, text, text[]) FROM anon;
GRANT EXECUTE ON FUNCTION public.has_department_role(uuid, text, text[]) TO authenticated;
GRANT EXECUTE ON FUNCTION public.has_department_role(uuid, text, text[]) TO service_role;

-- ROADS: all road-asset roles may read; managers/officers may create, edit, or delete.
DROP POLICY IF EXISTS road_asset_department_select ON public.roads;
CREATE POLICY road_asset_department_select
  ON public.roads AS RESTRICTIVE FOR SELECT TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_insert ON public.roads;
CREATE POLICY road_asset_department_insert
  ON public.roads AS RESTRICTIVE FOR INSERT TO authenticated
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_update ON public.roads;
CREATE POLICY road_asset_department_update
  ON public.roads AS RESTRICTIVE FOR UPDATE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_delete ON public.roads;
CREATE POLICY road_asset_department_delete
  ON public.roads AS RESTRICTIVE FOR DELETE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

-- ROAD SECTIONS: use the section's organization_id; NULL organization IDs fail closed.
DROP POLICY IF EXISTS road_asset_department_select ON public.road_sections;
CREATE POLICY road_asset_department_select
  ON public.road_sections AS RESTRICTIVE FOR SELECT TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_insert ON public.road_sections;
CREATE POLICY road_asset_department_insert
  ON public.road_sections AS RESTRICTIVE FOR INSERT TO authenticated
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_update ON public.road_sections;
CREATE POLICY road_asset_department_update
  ON public.road_sections AS RESTRICTIVE FOR UPDATE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_delete ON public.road_sections;
CREATE POLICY road_asset_department_delete
  ON public.road_sections AS RESTRICTIVE FOR DELETE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

-- ROAD INSPECTIONS: all road-asset roles may read; managers/officers may mutate.
DROP POLICY IF EXISTS road_asset_department_select ON public.road_inspections;
CREATE POLICY road_asset_department_select
  ON public.road_inspections AS RESTRICTIVE FOR SELECT TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_insert ON public.road_inspections;
CREATE POLICY road_asset_department_insert
  ON public.road_inspections AS RESTRICTIVE FOR INSERT TO authenticated
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_update ON public.road_inspections;
CREATE POLICY road_asset_department_update
  ON public.road_inspections AS RESTRICTIVE FOR UPDATE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

DROP POLICY IF EXISTS road_asset_department_delete ON public.road_inspections;
CREATE POLICY road_asset_department_delete
  ON public.road_inspections AS RESTRICTIVE FOR DELETE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

-- Before applying in production, verify section organization_id coverage and test:
-- 1) org admin retains access; 2) road_asset manager/officer can read/write;
-- 3) road_asset read_only can read but cannot write; 4) other departments and
--    unassigned users cannot read or write through the Supabase Data API.
