-- MMMS machinery breakdown / repair work orders
-- Apply after department RLS foundation (011–012) is live.

create table if not exists public.machinery_work_orders (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  machinery_id uuid not null references public.machinery(id) on delete restrict,
  work_order_no text not null,
  title text not null,
  description text,
  fault_type text,
  priority text not null default 'medium',
  status text not null default 'reported',
  reported_at date not null default (current_date),
  planned_start date,
  planned_end date,
  actual_start date,
  actual_end date,
  estimated_cost numeric(18,2),
  actual_cost numeric(18,2),
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (organization_id, work_order_no),
  check (priority in ('low', 'medium', 'high', 'critical')),
  check (status in ('reported', 'diagnosed', 'in_progress', 'waiting_parts', 'completed', 'cancelled')),
  check (estimated_cost is null or estimated_cost >= 0),
  check (actual_cost is null or actual_cost >= 0)
);

create index if not exists idx_machinery_wo_org_status
  on public.machinery_work_orders (organization_id, status);
create index if not exists idx_machinery_wo_machinery
  on public.machinery_work_orders (machinery_id);
create index if not exists idx_machinery_wo_org_priority
  on public.machinery_work_orders (organization_id, priority);

alter table public.machinery_work_orders enable row level security;

-- Baseline org membership (permissive)
drop policy if exists machinery_wo_select_member on public.machinery_work_orders;
create policy machinery_wo_select_member on public.machinery_work_orders
  for select to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists machinery_wo_insert_member on public.machinery_work_orders;
create policy machinery_wo_insert_member on public.machinery_work_orders
  for insert to authenticated
  with check (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists machinery_wo_update_member on public.machinery_work_orders;
create policy machinery_wo_update_member on public.machinery_work_orders
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

drop policy if exists machinery_wo_delete_member on public.machinery_work_orders;
create policy machinery_wo_delete_member on public.machinery_work_orders
  for delete to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

-- Restrictive department scope: machinery_maintenance
drop policy if exists department_scope_access on public.machinery_work_orders;
create policy department_scope_access
  on public.machinery_work_orders as restrictive for all to authenticated
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

drop policy if exists department_scope_delete_write_roles on public.machinery_work_orders;
create policy department_scope_delete_write_roles
  on public.machinery_work_orders as restrictive for delete to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'machinery_maintenance',
      array['department_manager', 'officer']::text[]
    )
  );
