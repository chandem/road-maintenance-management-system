-- Department-role foundation for clean installs.
-- This schema already exists in production through earlier timestamped SQL-editor
-- migrations, but was missing from the repository's reproducible migration chain.
-- Keep this file before 010_road_inspections / 011_department_road_rls in the
-- isolated test sequence. Do not replay it against production without ledger review.

CREATE TABLE IF NOT EXISTS public.departments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  name text NOT NULL,
  code text,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, name)
);

CREATE TABLE IF NOT EXISTS public.user_department_roles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  organization_id uuid NOT NULL REFERENCES public.organizations(id) ON DELETE CASCADE,
  user_id uuid NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
  department_id uuid NOT NULL REFERENCES public.departments(id) ON DELETE CASCADE,
  role text NOT NULL DEFAULT 'officer'
    CHECK (role IN ('department_manager', 'officer', 'read_only')),
  is_active boolean NOT NULL DEFAULT true,
  assigned_by uuid REFERENCES auth.users(id) ON DELETE SET NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, user_id, department_id)
);

CREATE INDEX IF NOT EXISTS idx_departments_organization
  ON public.departments (organization_id);
CREATE INDEX IF NOT EXISTS idx_user_department_roles_user_org_active
  ON public.user_department_roles (user_id, organization_id, is_active);
CREATE INDEX IF NOT EXISTS idx_user_department_roles_department_active
  ON public.user_department_roles (department_id, is_active);

ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.user_department_roles ENABLE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE, DELETE ON public.departments TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.user_department_roles TO authenticated;

DROP POLICY IF EXISTS "admins can manage departments" ON public.departments;
CREATE POLICY "admins can manage departments"
  ON public.departments FOR ALL TO authenticated
  USING ((SELECT private.is_org_admin(organization_id)))
  WITH CHECK ((SELECT private.is_org_admin(organization_id)));

DROP POLICY IF EXISTS "members can view departments" ON public.departments;
CREATE POLICY "members can view departments"
  ON public.departments FOR SELECT TO authenticated
  USING ((SELECT private.is_org_member(organization_id)));

DROP POLICY IF EXISTS org_admins_manage_department_roles ON public.user_department_roles;
CREATE POLICY org_admins_manage_department_roles
  ON public.user_department_roles FOR ALL TO authenticated
  USING (private.is_org_admin(organization_id))
  WITH CHECK (
    private.is_org_admin(organization_id)
    AND EXISTS (
      SELECT 1
      FROM public.departments d
      WHERE d.id = user_department_roles.department_id
        AND d.organization_id = user_department_roles.organization_id
    )
    AND EXISTS (
      SELECT 1
      FROM public.organization_members om
      WHERE om.organization_id = user_department_roles.organization_id
        AND om.user_id = user_department_roles.user_id
        AND om.is_active = true
    )
  );

DROP POLICY IF EXISTS users_can_view_own_department_roles ON public.user_department_roles;
CREATE POLICY users_can_view_own_department_roles
  ON public.user_department_roles FOR SELECT TO authenticated
  USING (
    user_id = (SELECT auth.uid())
    OR private.is_org_admin(organization_id)
  );

CREATE OR REPLACE FUNCTION public.has_department_role(
  p_organization_id uuid,
  p_department_code text,
  p_allowed_roles text[] DEFAULT NULL::text[]
)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = ''
AS $function$
  SELECT EXISTS (
    SELECT 1
    FROM public.user_department_roles udr
    JOIN public.departments d
      ON d.id = udr.department_id
     AND d.organization_id = udr.organization_id
    JOIN public.organization_members om
      ON om.organization_id = udr.organization_id
     AND om.user_id = udr.user_id
     AND om.is_active = true
    WHERE udr.organization_id = p_organization_id
      AND udr.user_id = (SELECT auth.uid())
      AND udr.is_active = true
      AND d.code = p_department_code
      AND (p_allowed_roles IS NULL OR udr.role = ANY(p_allowed_roles))
  );
$function$;

COMMENT ON FUNCTION public.has_department_role(uuid, text, text[])
  IS 'Checks the current authenticated user active department role for an organization and department code.';
