-- General asset maintenance work orders and warranty tracking.
create table if not exists public.asset_maintenance_orders (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  asset_id uuid not null references public.assets(id) on delete restrict,
  title text not null,
  description text,
  maintenance_type text not null default 'corrective',
  priority text not null default 'normal',
  status text not null default 'requested',
  requested_by uuid not null references auth.users(id) on delete restrict,
  assigned_to uuid references auth.users(id) on delete set null,
  scheduled_date date,
  completed_at timestamptz,
  cost numeric(14,2) not null default 0,
  vendor text,
  notes text,
  next_service_date date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint asset_maintenance_type_check check (maintenance_type in ('preventive','corrective','inspection')),
  constraint asset_maintenance_priority_check check (priority in ('low','normal','high','urgent')),
  constraint asset_maintenance_status_check check (status in ('requested','approved','in_progress','completed','rejected','cancelled')),
  constraint asset_maintenance_cost_check check (cost >= 0),
  constraint asset_maintenance_title_check check (length(trim(title)) > 0)
);

create index if not exists idx_asset_maintenance_org_status
  on public.asset_maintenance_orders(organization_id, status, created_at desc);
create index if not exists idx_asset_maintenance_asset
  on public.asset_maintenance_orders(asset_id, created_at desc);

alter table public.asset_maintenance_orders enable row level security;
drop policy if exists asset_maintenance_department_scope on public.asset_maintenance_orders;
create policy asset_maintenance_department_scope on public.asset_maintenance_orders
  as restrictive for all to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(organization_id, 'general_assets', array['department_manager','officer','read_only']::text[])
  )
  with check (
    private.is_org_admin(organization_id)
    or public.has_department_role(organization_id, 'general_assets', array['department_manager','officer']::text[])
  );
drop policy if exists asset_maintenance_org_select on public.asset_maintenance_orders;
create policy asset_maintenance_org_select on public.asset_maintenance_orders
  for select to authenticated using (
    organization_id in (select organization_id from public.user_profiles where id = auth.uid())
  );
drop policy if exists asset_maintenance_org_insert on public.asset_maintenance_orders;
create policy asset_maintenance_org_insert on public.asset_maintenance_orders
  for insert to authenticated with check (
    organization_id in (select organization_id from public.user_profiles where id = auth.uid())
  );
drop policy if exists asset_maintenance_org_update on public.asset_maintenance_orders;
create policy asset_maintenance_org_update on public.asset_maintenance_orders
  for update to authenticated
  using (organization_id in (select organization_id from public.user_profiles where id = auth.uid()))
  with check (organization_id in (select organization_id from public.user_profiles where id = auth.uid()));

create table if not exists public.asset_warranties (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  asset_id uuid not null references public.assets(id) on delete cascade,
  provider text,
  reference_number text,
  start_date date not null,
  end_date date not null,
  coverage_notes text,
  created_by uuid not null references auth.users(id) on delete restrict,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint asset_warranty_dates_check check (end_date >= start_date)
);

create index if not exists idx_asset_warranties_org_end_date
  on public.asset_warranties(organization_id, end_date);
create index if not exists idx_asset_warranties_asset
  on public.asset_warranties(asset_id, end_date);

alter table public.asset_warranties enable row level security;
drop policy if exists asset_warranties_department_scope on public.asset_warranties;
create policy asset_warranties_department_scope on public.asset_warranties
  as restrictive for all to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(organization_id, 'general_assets', array['department_manager','officer','read_only']::text[])
  )
  with check (
    private.is_org_admin(organization_id)
    or public.has_department_role(organization_id, 'general_assets', array['department_manager','officer']::text[])
  );
drop policy if exists asset_warranties_org_select on public.asset_warranties;
create policy asset_warranties_org_select on public.asset_warranties
  for select to authenticated using (
    organization_id in (select organization_id from public.user_profiles where id = auth.uid())
  );
drop policy if exists asset_warranties_org_insert on public.asset_warranties;
create policy asset_warranties_org_insert on public.asset_warranties
  for insert to authenticated with check (
    organization_id in (select organization_id from public.user_profiles where id = auth.uid())
  );
