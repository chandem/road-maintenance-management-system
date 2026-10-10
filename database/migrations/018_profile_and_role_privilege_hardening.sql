-- AI-RMMS profile and role-assignment privilege hardening.
-- Proposal only: test in isolated staging with the real signup/profile-edit flows
-- before production. This migration intentionally makes organization/department
-- assignment and account status administrator-controlled, not self-service.
--
-- RLS remains necessary. These grants only restrict which operations/columns
-- an API role can attempt; existing policies still decide which rows are visible.

-- Anonymous clients must have no direct privileges on department-role assignments.
REVOKE ALL PRIVILEGES
  ON TABLE public.user_department_roles
  FROM PUBLIC, anon;

-- Authenticated users may read their own profile under RLS and create a minimal
-- profile for themselves. Organization, department, employee code, and active
-- status must be populated by a trusted/admin workflow.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER
  ON TABLE public.user_profiles
  FROM PUBLIC, anon, authenticated;

-- Also clear any legacy column-level ACLs: revoking table-level grants alone
-- does not remove separately granted column privileges.
REVOKE INSERT (
  id, organization_id, department_id, full_name, employee_code,
  job_title, is_active, created_at, updated_at
) ON TABLE public.user_profiles FROM PUBLIC, anon, authenticated;
REVOKE UPDATE (
  id, organization_id, department_id, full_name, employee_code,
  job_title, is_active, created_at, updated_at
) ON TABLE public.user_profiles FROM PUBLIC, anon, authenticated;

GRANT SELECT ON TABLE public.user_profiles TO authenticated;
GRANT INSERT (id, full_name) ON TABLE public.user_profiles TO authenticated;
GRANT UPDATE (full_name) ON TABLE public.user_profiles TO authenticated;

-- Organization membership and role assignments remain administrator-managed.
-- Existing RLS policies restrict authenticated mutations to organization admins.
-- Remove unnecessary structural privileges, but preserve ordinary DML grants
-- because the admin dashboard may manage membership/department roles directly
-- through RLS. Migration 016 separately removes TRUNCATE/REFERENCES/TRIGGER.
REVOKE TRUNCATE, REFERENCES, TRIGGER
  ON TABLE public.organization_members, public.organizations, public.departments
  FROM PUBLIC, anon, authenticated;

-- Do not apply until staging verifies:
-- 1. Signup/profile bootstrap can insert (id, full_name) and nothing privileged.
-- 2. A user can update full_name but cannot alter organization_id, department_id,
--    employee_code, is_active, or other protected profile fields.
-- 3. Organization admins can still manage membership and department assignments.
-- 4. Anon cannot read or mutate user_department_roles through the Data API.
-- 5. Backend service-role flows continue to work and no frontend depends on
--    direct writes to protected profile fields.
