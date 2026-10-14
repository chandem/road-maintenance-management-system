-- Prevent linked expenses from exceeding the available budget.
-- The budget row lock serializes concurrent expense requests for the same budget.
create or replace function public.record_finance_expense(
  p_organization_id uuid,
  p_created_by uuid,
  p_budget_id uuid,
  p_work_order_id uuid,
  p_expense_date date,
  p_description text,
  p_category text,
  p_amount numeric,
  p_reference_no text,
  p_status text
)
returns public.expenses
language plpgsql
security invoker
set search_path = public
as $$
declare
  v_budget public.budgets%rowtype;
  v_expense public.expenses%rowtype;
  v_status text := lower(trim(coalesce(p_status, 'recorded')));
  v_available numeric;
begin
  if auth.uid() is null or auth.uid() <> p_created_by then
    raise exception 'Expense creator must match the authenticated user';
  end if;

  if not exists (
    select 1
      from public.organization_members om
     where om.organization_id = p_organization_id
       and om.user_id = auth.uid()
       and om.is_active = true
       and om.role in ('owner', 'admin')
  ) and coalesce(
    public.has_department_role(
      p_organization_id,
      'finance',
      array['department_manager', 'officer']::text[]
    ),
    false
  ) is not true then
    raise exception 'Finance expense recording permission is required';
  end if;

  if p_amount is null or p_amount <= 0 then
    raise exception 'Expense amount must be greater than zero';
  end if;

  if v_status not in ('recorded', 'committed', 'approved', 'paid', 'rejected') then
    raise exception 'Unsupported expense status';
  end if;

  if p_budget_id is not null then
    select *
      into v_budget
      from public.budgets
     where id = p_budget_id
       and organization_id = p_organization_id
     for update;

    if not found then
      raise exception 'Selected budget was not found in this organization';
    end if;

    if v_status in ('paid', 'committed', 'approved') then
      if lower(coalesce(v_budget.status, '')) <> 'active' then
        raise exception 'Expenses can only be charged to an active budget';
      end if;

      v_available := coalesce(v_budget.allocated_amount, 0)
        - coalesce(v_budget.spent_amount, 0)
        - coalesce(v_budget.committed_amount, 0);

      if p_amount > v_available then
        raise exception 'Insufficient budget: available balance is %, requested amount is %',
          v_available, p_amount;
      end if;
    end if;
  end if;

  insert into public.expenses (
    organization_id, created_by, budget_id, work_order_id, expense_date,
    description, category, amount, reference_no, status
  ) values (
    p_organization_id, p_created_by, p_budget_id, p_work_order_id, p_expense_date,
    trim(p_description), p_category, p_amount, p_reference_no, v_status
  )
  returning * into v_expense;

  if p_budget_id is not null and v_status = 'paid' then
    update public.budgets
       set spent_amount = coalesce(spent_amount, 0) + p_amount,
           updated_at = now()
     where id = p_budget_id
       and organization_id = p_organization_id;
  elsif p_budget_id is not null and v_status in ('committed', 'approved') then
    update public.budgets
       set committed_amount = coalesce(committed_amount, 0) + p_amount,
           updated_at = now()
     where id = p_budget_id
       and organization_id = p_organization_id;
  end if;

  return v_expense;
end;
$$;

grant execute on function public.record_finance_expense(uuid, uuid, uuid, uuid, date, text, text, numeric, text, text) to authenticated;
