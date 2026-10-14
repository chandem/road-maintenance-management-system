-- MMMS fuel issues and meter-hour readings
-- Apply after machinery table and department RLS helpers (012+) are live.

create table if not exists public.machinery_fuel_logs (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  machinery_id uuid not null references public.machinery(id) on delete restrict,
  log_date date not null default (current_date),
  fuel_quantity numeric(18,3),
  fuel_unit text not null default 'litre',
  meter_hours numeric(18,2),
  unit_cost numeric(18,2),
  total_cost numeric(18,2),
  notes text,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (fuel_quantity is null or fuel_quantity >= 0),
  check (meter_hours is null or meter_hours >= 0),
  check (unit_cost is null or unit_cost >= 0),
  check (total_cost is null or total_cost >= 0),
  check (
    fuel_quantity is not null
    or meter_hours is not null
  )
);

create index if not exists idx_mfl_org_date
  on public.machinery_fuel_logs (organization_id, log_date desc);
create index if not exists idx_mfl_machinery
  on public.machinery_fuel_logs (machinery_id);

alter table public.machinery_fuel_logs enable row level security;

drop policy if exists mfl_select_member on public.machinery_fuel_logs;
create policy mfl_select_member on public.machinery_fuel_logs
  for select to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists mfl_insert_member on public.machinery_fuel_logs;
create policy mfl_insert_member on public.machinery_fuel_logs
  for insert to authenticated
  with check (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists mfl_update_member on public.machinery_fuel_logs;
create policy mfl_update_member on public.machinery_fuel_logs
  for update to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  )
  with check (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists mfl_delete_member on public.machinery_fuel_logs;
create policy mfl_delete_member on public.machinery_fuel_logs
  for delete to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists department_scope_access on public.machinery_fuel_logs;
create policy department_scope_access
  on public.machinery_fuel_logs as restrictive for all to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'machinery_maintenance',
      array['department_manager', 'officer', 'read_only']::text[]
    )
  )
  with check (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'machinery_maintenance',
      array['department_manager', 'officer']::text[]
    )
  );

drop policy if exists department_scope_delete_write_roles on public.machinery_fuel_logs;
create policy department_scope_delete_write_roles
  on public.machinery_fuel_logs as restrictive for delete to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'machinery_maintenance',
      array['department_manager', 'officer']::text[]
    )
  );
