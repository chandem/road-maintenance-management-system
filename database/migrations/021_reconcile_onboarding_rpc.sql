-- Reconcile the onboarding RPC with the recovered production definition.
-- This is a forward migration: do not edit an already-applied migration in place.
-- Apply only after the full sequence passes in an isolated disposable Supabase DB.

CREATE OR REPLACE FUNCTION public.create_organization_for_current_user(
  p_name text,
  p_code text DEFAULT NULL
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = ''
AS $$
DECLARE
  v_user_id uuid := auth.uid();
  v_org_id uuid;
  v_name text := btrim(p_name);
  v_code text := nullif(btrim(p_code), '');
BEGIN
  IF v_user_id IS NULL THEN
    RAISE EXCEPTION 'Authentication required';
  END IF;

  IF v_name IS NULL OR v_name = '' THEN
    RAISE EXCEPTION 'Organization name is required';
  END IF;

  IF EXISTS (
    SELECT 1
    FROM public.user_profiles
    WHERE id = v_user_id
      AND organization_id IS NOT NULL
  ) THEN
    RAISE EXCEPTION 'User already belongs to an organization';
  END IF;

  IF v_code IS NOT NULL AND EXISTS (
    SELECT 1
    FROM public.organizations
    WHERE code = v_code
  ) THEN
    RAISE EXCEPTION 'Organization code already exists';
  END IF;

  INSERT INTO public.organizations (name, code)
  VALUES (v_name, v_code)
  RETURNING id INTO v_org_id;

  INSERT INTO public.organization_members (organization_id, user_id, role, is_active)
  VALUES (v_org_id, v_user_id, 'admin', true)
  ON CONFLICT (organization_id, user_id) DO UPDATE
    SET role = 'admin',
        is_active = true;

  INSERT INTO public.user_profiles (id, organization_id, is_active)
  VALUES (v_user_id, v_org_id, true)
  ON CONFLICT (id) DO UPDATE
    SET organization_id = EXCLUDED.organization_id,
        is_active = true,
        updated_at = pg_catalog.now();

  RETURN v_org_id;
END;
$$;

-- Onboarding is available to authenticated users only, not PUBLIC/anon/service_role.
REVOKE ALL ON FUNCTION public.create_organization_for_current_user(text, text)
  FROM PUBLIC, anon, service_role;
GRANT EXECUTE ON FUNCTION public.create_organization_for_current_user(text, text)
  TO authenticated;
