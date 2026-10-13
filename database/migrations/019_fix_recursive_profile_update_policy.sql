-- Fix recursive RLS evaluation in the self-profile update policy.
-- Migration 003 compared organization_id by selecting from user_profiles
-- inside a policy on user_profiles, which causes SQLSTATE 42P17 on UPDATE.
--
-- Migration 018 restricts authenticated column privileges to full_name only,
-- so protected organization/department/status fields cannot be changed by a
-- caller JWT. Keep the row policy ownership-based and non-recursive.
DROP POLICY IF EXISTS "users can update own profile fields" ON public.user_profiles;
DROP POLICY IF EXISTS "users can update own profile" ON public.user_profiles;

CREATE POLICY "users can update own profile fields"
ON public.user_profiles
FOR UPDATE
TO authenticated
USING (id = (SELECT auth.uid()))
WITH CHECK (id = (SELECT auth.uid()));

COMMENT ON POLICY "users can update own profile fields" ON public.user_profiles IS
  'Allows a user to update their own profile row; column grants restrict authenticated updates to full_name.';
