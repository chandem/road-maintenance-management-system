-- MMMS preventive maintenance schedules
-- Apply after 024_machinery_work_orders.sql (and department RLS helpers).

create table if not exists public.machinery_maintenance_schedules (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  machinery_id uuid not null references public.machinery(id) on delete restrict,
  schedule_code text not null,
  title text not null,
  service_type text,
  interval_hours numeric(18,2),
  interval_days integer,
  last_service_date date,
  last_service_hours numeric(18,2),
  next_due_date date,
  next_due_hours numeric(18,2),
  status text not null default 'active',
  notes text,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, schedule_code),
  check (status in ('active', 'paused', 'completed', 'cancelled')),
  check (interval_hours is null or interval_hours > 0),
  check (interval_days is null or interval_days > 0),
  check (last_service_hours is null or last_service_hours >= 0),
  check (next_due_hours is null or next_due_hours >= 0),
  check (
    interval_hours is not null
    or interval_days is not null
  )
);

create index if not exists idx_mms_sched_org_status
  on public.machinery_maintenance_schedules (organization_id, status);
create index if not exists idx_mms_sched_machinery
  on public.machinery_maintenance_schedules (machinery_id);
create index if not exists idx_mms_sched_next_due
  on public.machinery_maintenance_schedules (organization_id, next_due_date);

alter table public.machinery_maintenance_schedules enable row level security;

drop policy if exists mms_sched_select_member on public.machinery_maintenance_schedules;
create policy mms_sched_select_member on public.machinery_maintenance_schedules
  for select to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists mms_sched_insert_member on public.machinery_maintenance_schedules;
create policy mms_sched_insert_member on public.machinery_maintenance_schedules
  for insert to authenticated
  with check (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists mms_sched_update_member on public.machinery_maintenance_schedules;
create policy mms_sched_update_member on public.machinery_maintenance_schedules
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

drop policy if exists mms_sched_delete_member on public.machinery_maintenance_schedules;
create policy mms_sched_delete_member on public.machinery_maintenance_schedules
  for delete to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists department_scope_access on public.machinery_maintenance_schedules;
create policy department_scope_access
  on public.machinery_maintenance_schedules as restrictive for all to authenticated
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

drop policy if exists department_scope_delete_write_roles on public.machinery_maintenance_schedules;
create policy department_scope_delete_write_roles
  on public.machinery_maintenance_schedules as restrictive for delete to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'machinery_maintenance',
      array['department_manager', 'officer']::text[]
    )
  );
