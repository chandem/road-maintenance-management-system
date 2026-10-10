-- Harden execution privileges and name resolution for privileged public RPCs.
-- Source-controlled proposal only: test after migrations 011-017 in an
-- isolated staging database. Do not apply directly to production.
--
-- Migration 011 converts has_department_role into a SECURITY INVOKER wrapper.
-- Repeat the grants here as defense in depth for environments where grants
-- survived earlier function replacements.
REVOKE EXECUTE ON FUNCTION public.has_department_role(uuid, text, text[])
  FROM PUBLIC, anon;
GRANT EXECUTE ON FUNCTION public.has_department_role(uuid, text, text[])
  TO authenticated;
REVOKE EXECUTE ON FUNCTION public.has_department_role(uuid, text, text[])
  FROM service_role;

REVOKE EXECUTE ON FUNCTION private.has_department_role(uuid, text, text[])
  FROM PUBLIC, anon, service_role;
GRANT EXECUTE ON FUNCTION private.has_department_role(uuid, text, text[])
  TO authenticated;

-- This SECURITY DEFINER function already schema-qualifies application tables.
-- An empty search_path additionally prevents accidental object shadowing if
-- its body is changed later. Built-in functions resolve through pg_catalog.
ALTER FUNCTION public.create_organization_for_current_user(text, text)
  SET search_path = '';

-- Organization creation is an authenticated-user operation, never anonymous.
REVOKE EXECUTE ON FUNCTION public.create_organization_for_current_user(text, text)
  FROM PUBLIC, anon, service_role;
GRANT EXECUTE ON FUNCTION public.create_organization_for_current_user(text, text)
  TO authenticated;
