-- AI-RMMS frontend onboarding RPC
-- Exposes only the authenticated first-organization bootstrap through the Data API.

create or replace function public.create_organization_for_current_user(
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

  if exists (
    select 1
    from public.user_profiles up
    where up.id = v_user_id
      and up.organization_id is not null
  ) then
    raise exception 'User already belongs to an organization';
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

revoke all on function public.create_organization_for_current_user(text, text) from public;
grant execute on function public.create_organization_for_current_user(text, text) to authenticated;
