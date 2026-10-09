from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user, require_department_access
from app.schemas.finance import (
    Budget,
    BudgetCreate,
    BudgetUpdate,
    Expense,
    ExpenseCreate,
    FinanceSummary,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/finance", tags=["finance"])

BUDGET_COLS = (
    "id,organization_id,fiscal_year,budget_code,category,"
    "allocated_amount,spent_amount,committed_amount,status,"
    "created_at,updated_at"
)
EXPENSE_COLS = (
    "id,organization_id,budget_id,work_order_id,expense_date,"
    "description,category,amount,reference_no,status,"
    "created_by,created_at"
)


def _org_id(current_user) -> str:
    try:
        org_id = resolve_organization_id(current_user["client"], current_user["id"])
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail="Organization membership could not be verified.",
        ) from exc
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("/summary", response_model=FinanceSummary)
def finance_summary(
    current_user=Depends(require_department_access("finance", ['department_manager', 'officer', 'read_only'])),
    fiscal_year: str | None = Query(default=None, max_length=20),
):
    """Budget utilization snapshot (Financial Management)."""
    supabase = current_user["client"]
    budget_query = supabase.table("budgets").select(
        "allocated_amount,spent_amount,committed_amount,status,fiscal_year"
    ).limit(500)
    if fiscal_year:
        budget_query = budget_query.eq("fiscal_year", fiscal_year)
    budgets = budget_query.execute().data or []

    expense_query = supabase.table("expenses").select("id,amount").limit(2000)
    expenses = expense_query.execute().data or []

    total_allocated = sum(Decimal(str(b.get("allocated_amount") or 0)) for b in budgets)
    total_spent = sum(Decimal(str(b.get("spent_amount") or 0)) for b in budgets)
    total_committed = sum(Decimal(str(b.get("committed_amount") or 0)) for b in budgets)
    remaining = total_allocated - total_spent - total_committed
    utilization = (
        float((total_spent + total_committed) / total_allocated * 100)
        if total_allocated > 0
        else 0.0
    )

    return FinanceSummary(
        budget_count=len(budgets),
        expense_count=len(expenses),
        total_allocated=total_allocated,
        total_spent=total_spent,
        total_committed=total_committed,
        remaining=remaining,
        utilization_percent=round(utilization, 2),
    )


@router.get("/budgets", response_model=list[Budget])
def list_budgets(
    current_user=Depends(require_department_access("finance", ['department_manager', 'officer', 'read_only'])),
    limit: int = Query(default=50, ge=1, le=100),
    fiscal_year: str | None = Query(default=None, max_length=20),
    status: str | None = Query(default=None, max_length=50),
):
    supabase = current_user["client"]
    query = (
        supabase.table("budgets")
        .select(BUDGET_COLS)
        .order("fiscal_year", desc=True)
        .limit(limit)
    )
    if fiscal_year:
        query = query.eq("fiscal_year", fiscal_year)
    if status:
        query = query.eq("status", status)
    return query.execute().data or []


@router.get("/budgets/{budget_id}", response_model=Budget)
def get_budget(
    budget_id: UUID,
    current_user=Depends(require_department_access("finance", ['department_manager', 'officer', 'read_only'])),
):
    response = (
        current_user["client"]
        .table("budgets")
        .select(BUDGET_COLS)
        .eq("id", str(budget_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Budget not found")
    return response.data


@router.post("/budgets", response_model=Budget, status_code=201)
def create_budget(
    payload: BudgetCreate,
    current_user=Depends(require_department_access("finance", ['department_manager', 'officer'])),
):
    organization_id = _org_id(current_user)
    row = {"organization_id": organization_id, **payload.model_dump(mode="json")}
    response = current_user["client"].table("budgets").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Budget could not be created")
    return response.data[0]


@router.patch("/budgets/{budget_id}", response_model=Budget)
def update_budget(
    budget_id: UUID,
    payload: BudgetUpdate,
    current_user=Depends(require_department_access("finance", ['department_manager', 'officer'])),
):
    updates = {
        k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("budgets")
        .update(updates)
        .eq("id", str(budget_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Budget not found")
    return response.data[0]


@router.get("/expenses", response_model=list[Expense])
def list_expenses(
    current_user=Depends(require_department_access("finance", ['department_manager', 'officer', 'read_only'])),
    limit: int = Query(default=100, ge=1, le=200),
    budget_id: UUID | None = Query(default=None),
    work_order_id: UUID | None = Query(default=None),
):
    supabase = current_user["client"]
    query = (
        supabase.table("expenses")
        .select(EXPENSE_COLS)
        .order("expense_date", desc=True)
        .limit(limit)
    )
    if budget_id:
        query = query.eq("budget_id", str(budget_id))
    if work_order_id:
        query = query.eq("work_order_id", str(work_order_id))
    return query.execute().data or []


@router.get("/expenses/{expense_id}", response_model=Expense)
def get_expense(
    expense_id: UUID,
    current_user=Depends(require_department_access("finance", ['department_manager', 'officer', 'read_only'])),
):
    response = (
        current_user["client"]
        .table("expenses")
        .select(EXPENSE_COLS)
        .eq("id", str(expense_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Expense not found")
    return response.data


@router.post("/expenses", response_model=Expense, status_code=201)
def create_expense(
    payload: ExpenseCreate,
    current_user=Depends(require_department_access("finance", ['department_manager', 'officer'])),
):
    """Record an expense. Does not approve payments — advisory record only."""
    organization_id = _org_id(current_user)
    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **payload.model_dump(mode="json"),
    }
    response = current_user["client"].table("expenses").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Expense could not be created")
    return response.data[0]
