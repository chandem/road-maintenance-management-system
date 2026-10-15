-- General asset transfer requests with department and organization isolation.
create table if not exists public.asset_transfers (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  asset_id uuid not null references public.assets(id) on delete restrict,
  from_location text,
  to_location text not null,
  from_custodian uuid references auth.users(id) on delete set null,
  to_custodian uuid references auth.users(id) on delete set null,
  reason text not null,
  status text not null default 'pending',
  requested_by uuid not null references auth.users(id) on delete restrict,
  decided_by uuid references auth.users(id) on delete set null,
  decision_notes text,
  decided_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint asset_transfers_status_check check (status in ('pending','approved','rejected','cancelled')),
  constraint asset_transfers_locations_check check (length(trim(to_location)) > 0),
  constraint asset_transfers_reason_check check (length(trim(reason)) > 0)
);
create index if not exists idx_asset_transfers_org_status on public.asset_transfers(organization_id,status,created_at desc);
create index if not exists idx_asset_transfers_asset on public.asset_transfers(asset_id,created_at desc);
alter table public.asset_transfers enable row level security;
drop policy if exists asset_transfers_department_scope on public.asset_transfers;
create policy asset_transfers_department_scope on public.asset_transfers
  as restrictive for all to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(organization_id,'general_assets',array['department_manager','officer','read_only']::text[])
  )
  with check (
    private.is_org_admin(organization_id)
    or public.has_department_role(organization_id,'general_assets',array['department_manager','officer']::text[])
  );
drop policy if exists asset_transfers_org_member_select on public.asset_transfers;
create policy asset_transfers_org_member_select on public.asset_transfers
  for select to authenticated using (
    organization_id in (select organization_id from public.user_profiles where id = auth.uid())
  );
drop policy if exists asset_transfers_org_member_insert on public.asset_transfers;
create policy asset_transfers_org_member_insert on public.asset_transfers
  for insert to authenticated with check (
    organization_id in (select organization_id from public.user_profiles where id = auth.uid())
  );

create or replace function public.apply_approved_asset_transfer()
returns trigger
language plpgsql
security invoker
set search_path = public
as $$
begin
  if old.status <> 'approved' and new.status = 'approved' then
    update public.assets
       set location = new.to_location,
           assigned_to = new.to_custodian,
           updated_at = now()
     where id = new.asset_id
       and organization_id = new.organization_id;
    if not found then
      raise exception 'Asset not found in this organization';
    end if;
  end if;
  return new;
end;
$$;
drop trigger if exists trg_apply_approved_asset_transfer on public.asset_transfers;
create trigger trg_apply_approved_asset_transfer
after update of status on public.asset_transfers
for each row execute function public.apply_approved_asset_transfer();
