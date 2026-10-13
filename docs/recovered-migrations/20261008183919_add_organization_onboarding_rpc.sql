-- RECOVERY ARTIFACT: exact SQL statement recovered from production
-- Supabase project: firzbqzbezuecvplsibi
-- Ledger version: 20261008183919
-- Ledger name: add_organization_onboarding_rpc
-- Recovered 2026-10-10 from supabase_migrations.schema_migrations.statements.
-- Evidence archive only; do not replay against production as part of source recovery.

create or replace function public.create_organization_for_current_user(p_name text, p_code text default null)
returns uuid
language plpgsql
security definer
set search_path = public, pg_catalog
as $$
declare
  v_user_id uuid := auth.uid();
  v_org_id uuid;
  v_name text := btrim(p_name);
  v_code text := nullif(btrim(p_code), '');
begin
  if v_user_id is null then
    raise exception 'Authentication required';
  end if;

  if v_name is null or v_name = '' then
    raise exception 'Organization name is required';
  end if;

  if exists (
    select 1
    from public.user_profiles
    where id = v_user_id
      and organization_id is not null
  ) then
    raise exception 'User already belongs to an organization';
  end if;

  if v_code is not null and exists (
    select 1 from public.organizations where code = v_code
  ) then
    raise exception 'Organization code already exists';
  end if;

  insert into public.organizations (name, code)
  values (v_name, v_code)
  returning id into v_org_id;

  insert into public.organization_members (organization_id, user_id, role, is_active)
  values (v_org_id, v_user_id, 'admin', true)
  on conflict (organization_id, user_id) do update
    set role = 'admin', is_active = true;

  insert into public.user_profiles (id, organization_id, is_active)
  values (v_user_id, v_org_id, true)
  on conflict (id) do update
    set organization_id = excluded.organization_id,
        is_active = true,
        updated_at = now();

  return v_org_id;
end;
$$;

revoke all on function public.create_organization_for_current_user(text, text) from public;
grant execute on function public.create_organization_for_current_user(text, text) to authenticated;
