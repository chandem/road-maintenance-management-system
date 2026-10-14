-- Allow machinery_maintenance department to use materials as spare-parts inventory.
-- Road asset department retains existing access. Apply after 012 (has_department_role).

DROP POLICY IF EXISTS department_scope_access ON public.materials;
CREATE POLICY department_scope_access
  ON public.materials AS RESTRICTIVE FOR ALL TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
    OR public.has_department_role(
      organization_id, 'machinery_maintenance',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
    OR public.has_department_role(
      organization_id, 'machinery_maintenance',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.materials;
CREATE POLICY department_scope_delete_write_roles
  ON public.materials AS RESTRICTIVE FOR DELETE TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'road_asset',
      ARRAY['department_manager', 'officer']::text[]
    )
    OR public.has_department_role(
      organization_id, 'machinery_maintenance',
      ARRAY['department_manager', 'officer']::text[]
    )
  );
