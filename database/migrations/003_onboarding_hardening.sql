-- AI-RMMS onboarding hardening
-- Provides a controlled first-organization bootstrap for authenticated users.
-- Authorization remains organization-membership based.

create or replace function private.create_organization_for_current_user(
  p_name text,
  p_code text default null
)
returns uuid
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_org_id uuid;
  v_user_id uuid;
begin
  v_user_id := (select auth.uid());

  if v_user_id is null then
    raise exception 'Authentication required';
  end if;

  if p_name is null or btrim(p_name) = '' then
    raise exception 'Organization name is required';
  end if;

  insert into public.organizations(name, code)
  values (btrim(p_name), nullif(btrim(p_code), ''))
  returning id into v_org_id;

  insert into public.organization_members(organization_id, user_id, role, is_active)
  values (v_org_id, v_user_id, 'owner', true);

  insert into public.user_profiles(id, organization_id)
  values (v_user_id, v_org_id)
  on conflict (id) do update
    set organization_id = excluded.organization_id,
        updated_at = now();

  return v_org_id;
end;
$$;

revoke all on function private.create_organization_for_current_user(text, text) from public;
grant execute on function private.create_organization_for_current_user(text, text) to authenticated;

-- The bootstrap function is the only path that assigns an initial organization.
-- Existing users may still update their own profile fields, but cannot move
-- themselves between organizations through the profile RLS policy.
drop policy if exists "users can update own profile" on user_profiles;

create policy "users can update own profile fields"
on user_profiles for update
to authenticated
using (id = (select auth.uid()))
with check (
  id = (select auth.uid())
  and organization_id = (
    select up.organization_id
    from public.user_profiles up
    where up.id = (select auth.uid())
  )
);

-- Prevent anonymous access to the private schema function surface.
revoke usage on schema private from anon;
