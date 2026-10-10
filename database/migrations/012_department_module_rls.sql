-- Department-level RLS for non-road modules.
-- Apply only after 011_department_road_rls.sql has been reviewed and tested.
-- These are RESTRICTIVE policies: existing organization-membership policies
-- still grant baseline access, while these policies narrow it to department
-- assignments. Organization owners/admins retain administrative access.
--
-- Documents and AI analysis records are intentionally admin-only for now:
-- documents do not yet have a trustworthy department ACL, so broad semantic
-- retrieval could leak HR, finance, or other sensitive content. Relax only
-- after adding document-level department ownership and permission-aware search.

-- Road maintenance materials, plans, and work orders.
DROP POLICY IF EXISTS department_scope_access ON public.materials;
CREATE POLICY department_scope_access
  ON public.materials AS RESTRICTIVE FOR ALL TO authenticated
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

DROP POLICY IF EXISTS department_scope_access ON public.maintenance_plans;
CREATE POLICY department_scope_access
  ON public.maintenance_plans AS RESTRICTIVE FOR ALL TO authenticated
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

DROP POLICY IF EXISTS department_scope_access ON public.work_orders;
CREATE POLICY department_scope_access
  ON public.work_orders AS RESTRICTIVE FOR ALL TO authenticated
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

-- Machinery maintenance management.
DROP POLICY IF EXISTS department_scope_access ON public.machinery;
CREATE POLICY department_scope_access
  ON public.machinery AS RESTRICTIVE FOR ALL TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'machinery_maintenance',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'machinery_maintenance',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

-- General asset management.
DROP POLICY IF EXISTS department_scope_access ON public.assets;
CREATE POLICY department_scope_access
  ON public.assets AS RESTRICTIVE FOR ALL TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'general_assets',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'general_assets',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

-- Finance.
DROP POLICY IF EXISTS department_scope_access ON public.budgets;
CREATE POLICY department_scope_access
  ON public.budgets AS RESTRICTIVE FOR ALL TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'finance',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'finance',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

DROP POLICY IF EXISTS department_scope_access ON public.expenses;
CREATE POLICY department_scope_access
  ON public.expenses AS RESTRICTIVE FOR ALL TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'finance',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'finance',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

-- Human resources.
DROP POLICY IF EXISTS department_scope_access ON public.employees;
CREATE POLICY department_scope_access
  ON public.employees AS RESTRICTIVE FOR ALL TO authenticated
  USING (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'human_resources',
      ARRAY['department_manager', 'officer', 'read_only']::text[]
    )
  )
  WITH CHECK (
    private.is_org_admin(organization_id)
    OR public.has_department_role(
      organization_id, 'human_resources',
      ARRAY['department_manager', 'officer']::text[]
    )
  );

-- Sensitive shared records: keep admin-only until record-level department ACLs
-- and department-filtered retrieval are implemented.
DROP POLICY IF EXISTS department_scope_access ON public.documents;
CREATE POLICY department_scope_access
  ON public.documents AS RESTRICTIVE FOR ALL TO authenticated
  USING (private.is_org_admin(organization_id))
  WITH CHECK (private.is_org_admin(organization_id));

DROP POLICY IF EXISTS department_scope_access ON public.document_chunks;
CREATE POLICY department_scope_access
  ON public.document_chunks AS RESTRICTIVE FOR ALL TO authenticated
  USING (private.is_org_admin(organization_id))
  WITH CHECK (private.is_org_admin(organization_id));

DROP POLICY IF EXISTS department_scope_access ON public.ai_analysis_runs;
CREATE POLICY department_scope_access
  ON public.ai_analysis_runs AS RESTRICTIVE FOR ALL TO authenticated
  USING (private.is_org_admin(organization_id))
  WITH CHECK (private.is_org_admin(organization_id));

DROP POLICY IF EXISTS department_scope_access ON public.ai_recommendations;
CREATE POLICY department_scope_access
  ON public.ai_recommendations AS RESTRICTIVE FOR ALL TO authenticated
  USING (private.is_org_admin(organization_id))
  WITH CHECK (private.is_org_admin(organization_id));


-- IMPORTANT: The broad FOR ALL policy above permits read_only in USING, which
-- would otherwise also permit DELETE. Add command-specific restrictive DELETE
-- policies so read_only can read but cannot delete. PostgreSQL combines
-- restrictive policies with AND, so these narrow DELETE without affecting SELECT.
DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.materials;
CREATE POLICY department_scope_delete_write_roles
  ON public.materials AS RESTRICTIVE FOR DELETE TO authenticated
  USING (private.is_org_admin(organization_id) OR public.has_department_role(
    organization_id, 'road_asset', ARRAY['department_manager', 'officer']::text[]
  ));

DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.maintenance_plans;
CREATE POLICY department_scope_delete_write_roles
  ON public.maintenance_plans AS RESTRICTIVE FOR DELETE TO authenticated
  USING (private.is_org_admin(organization_id) OR public.has_department_role(
    organization_id, 'road_asset', ARRAY['department_manager', 'officer']::text[]
  ));

DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.work_orders;
CREATE POLICY department_scope_delete_write_roles
  ON public.work_orders AS RESTRICTIVE FOR DELETE TO authenticated
  USING (private.is_org_admin(organization_id) OR public.has_department_role(
    organization_id, 'road_asset', ARRAY['department_manager', 'officer']::text[]
  ));

DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.machinery;
CREATE POLICY department_scope_delete_write_roles
  ON public.machinery AS RESTRICTIVE FOR DELETE TO authenticated
  USING (private.is_org_admin(organization_id) OR public.has_department_role(
    organization_id, 'machinery_maintenance', ARRAY['department_manager', 'officer']::text[]
  ));

DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.assets;
CREATE POLICY department_scope_delete_write_roles
  ON public.assets AS RESTRICTIVE FOR DELETE TO authenticated
  USING (private.is_org_admin(organization_id) OR public.has_department_role(
    organization_id, 'general_assets', ARRAY['department_manager', 'officer']::text[]
  ));

DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.budgets;
CREATE POLICY department_scope_delete_write_roles
  ON public.budgets AS RESTRICTIVE FOR DELETE TO authenticated
  USING (private.is_org_admin(organization_id) OR public.has_department_role(
    organization_id, 'finance', ARRAY['department_manager', 'officer']::text[]
  ));

DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.expenses;
CREATE POLICY department_scope_delete_write_roles
  ON public.expenses AS RESTRICTIVE FOR DELETE TO authenticated
  USING (private.is_org_admin(organization_id) OR public.has_department_role(
    organization_id, 'finance', ARRAY['department_manager', 'officer']::text[]
  ));

DROP POLICY IF EXISTS department_scope_delete_write_roles ON public.employees;
CREATE POLICY department_scope_delete_write_roles
  ON public.employees AS RESTRICTIVE FOR DELETE TO authenticated
  USING (private.is_org_admin(organization_id) OR public.has_department_role(
    organization_id, 'human_resources', ARRAY['department_manager', 'officer']::text[]
  ));

-- Do not apply in production until the staging checklist passes with actual
-- authenticated tokens for each role. The migration must be applied after
-- 011_department_road_rls.sql so public.has_department_role is the invoker
-- wrapper and the private helper is available.
