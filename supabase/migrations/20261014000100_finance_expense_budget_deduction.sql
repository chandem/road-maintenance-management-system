-- Atomically record a finance expense and apply its effect to the linked budget.
-- SECURITY INVOKER preserves the caller's Supabase RLS context.
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
begin
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
