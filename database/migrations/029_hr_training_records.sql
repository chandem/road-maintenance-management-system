-- HR training courses and licence/certificate records
-- Apply after employees table and department RLS helpers exist.

create table if not exists public.hr_training_records (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  employee_id uuid not null references public.employees(id) on delete restrict,
  title text not null,
  record_type text not null default 'training',
  provider text,
  certificate_no text,
  completed_on date,
  expires_on date,
  status text not null default 'valid',
  notes text,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (record_type in ('training', 'licence', 'certificate', 'qualification')),
  check (status in ('valid', 'expired', 'revoked', 'pending')),
  check (expires_on is null or completed_on is null or expires_on >= completed_on)
);

create index if not exists idx_hr_train_org_status
  on public.hr_training_records (organization_id, status);
create index if not exists idx_hr_train_employee
  on public.hr_training_records (employee_id);
create index if not exists idx_hr_train_expires
  on public.hr_training_records (organization_id, expires_on);

alter table public.hr_training_records enable row level security;

drop policy if exists hr_train_select_member on public.hr_training_records;
create policy hr_train_select_member on public.hr_training_records
  for select to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists hr_train_insert_member on public.hr_training_records;
create policy hr_train_insert_member on public.hr_training_records
  for insert to authenticated
  with check (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists hr_train_update_member on public.hr_training_records;
create policy hr_train_update_member on public.hr_training_records
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

drop policy if exists hr_train_delete_member on public.hr_training_records;
create policy hr_train_delete_member on public.hr_training_records
  for delete to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists department_scope_access on public.hr_training_records;
create policy department_scope_access
  on public.hr_training_records as restrictive for all to authenticated
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

drop policy if exists department_scope_delete_write_roles on public.hr_training_records;
create policy department_scope_delete_write_roles
  on public.hr_training_records as restrictive for delete to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'human_resources',
      array['department_manager', 'officer']::text[]
    )
  );
