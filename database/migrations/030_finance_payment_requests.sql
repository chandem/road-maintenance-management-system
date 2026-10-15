-- Finance payment requests / commitments
-- Apply after budgets table and department RLS helpers exist.

create table if not exists public.finance_payment_requests (
  id uuid primary key default gen_random_uuid(),
  organization_id uuid not null references public.organizations(id) on delete cascade,
  budget_id uuid references public.budgets(id) on delete set null,
  request_no text not null,
  title text not null,
  payee text,
  amount numeric(14,2) not null,
  currency text not null default 'ETB',
  status text not null default 'draft',
  requested_on date not null default (current_date),
  due_date date,
  notes text,
  decided_by uuid references auth.users(id),
  decided_at timestamptz,
  created_by uuid references auth.users(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (amount > 0),
  check (status in ('draft', 'submitted', 'approved', 'rejected', 'paid', 'cancelled')),
  unique (organization_id, request_no)
);

create index if not exists idx_payreq_org_status
  on public.finance_payment_requests (organization_id, status);
create index if not exists idx_payreq_budget
  on public.finance_payment_requests (budget_id);

alter table public.finance_payment_requests enable row level security;

drop policy if exists payreq_select_member on public.finance_payment_requests;
create policy payreq_select_member on public.finance_payment_requests
  for select to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists payreq_insert_member on public.finance_payment_requests;
create policy payreq_insert_member on public.finance_payment_requests
  for insert to authenticated
  with check (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists payreq_update_member on public.finance_payment_requests;
create policy payreq_update_member on public.finance_payment_requests
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

drop policy if exists payreq_delete_member on public.finance_payment_requests;
create policy payreq_delete_member on public.finance_payment_requests
  for delete to authenticated
  using (
    organization_id in (
      select organization_id from public.user_profiles where id = auth.uid()
    )
  );

drop policy if exists department_scope_access on public.finance_payment_requests;
create policy department_scope_access
  on public.finance_payment_requests as restrictive for all to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'finance',
      array['department_manager', 'officer', 'read_only']::text[]
    )
  )
  with check (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'finance',
      array['department_manager', 'officer']::text[]
    )
  );

drop policy if exists department_scope_delete_write_roles on public.finance_payment_requests;
create policy department_scope_delete_write_roles
  on public.finance_payment_requests as restrictive for delete to authenticated
  using (
    private.is_org_admin(organization_id)
    or public.has_department_role(
      organization_id,
      'finance',
      array['department_manager', 'officer']::text[]
    )
  );
