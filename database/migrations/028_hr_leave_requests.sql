-- HR leave requests
-- Apply after employees table and department RLS helpers exist.

create table if not exists public.hr_leave_requests (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  employee_id uuid not null references public.employees(id) on delete restrict,
  leave_type text not null default 'annual',
  start_date date not null,
  end_date date not null,
  days_requested numeric(8,2) not null default 1,
  status text not null default 'pending',
  reason text,
  decision_notes text,
  decided_by uuid references auth.users(id),
  decided_at timestamptz,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (end_date >= start_date),
  check (days_requested > 0),
  check (leave_type in ('annual', 'sick', 'unpaid', 'maternity', 'paternity', 'compassionate', 'other')),
  check (status in ('pending', 'approved', 'rejected', 'cancelled'))
);

create index if not exists idx_hr_leave_org_status
  on public.hr_leave_requests (organization_id, status);
create index if not exists idx_hr_leave_employee
  on public.hr_leave_requests (employee_id);
create index if not exists idx_hr_leave_dates
  on public.hr_leave_requests (organization_id, start_date, end_date);

alter table public.hr_leave_requests enable row level security;

drop policy if exists hr_leave_select_member on public.hr_leave_requests;
create policy hr_leave_select_member on public.hr_leave_requests
  for select to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists hr_leave_insert_member on public.hr_leave_requests;
create policy hr_leave_insert_member on public.hr_leave_requests
  for insert to authenticated
  with check (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists hr_leave_update_member on public.hr_leave_requests;
create policy hr_leave_update_member on public.hr_leave_requests
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

drop policy if exists hr_leave_delete_member on public.hr_leave_requests;
create policy hr_leave_delete_member on public.hr_leave_requests
  for delete to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists department_scope_access on public.hr_leave_requests;
create policy department_scope_access
  on public.hr_leave_requests as restrictive for all to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'human_resources',
      array['department_manager', 'officer', 'read_only']::text[]
    )
  )
  with check (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'human_resources',
      array['department_manager', 'officer']::text[]
    )
  );

drop policy if exists department_scope_delete_write_roles on public.hr_leave_requests;
create policy department_scope_delete_write_roles
  on public.hr_leave_requests as restrictive for delete to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'human_resources',
      array['department_manager', 'officer']::text[]
    )
  );
