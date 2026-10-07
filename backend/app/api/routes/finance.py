from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.finance import Budget, Expense

router = APIRouter(prefix="/finance", tags=["finance"])


@router.get("/budgets", response_model=list[Budget])
def list_budgets(
    current_user=Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=100),
    fiscal_year: str | None = Query(default=None, max_length=20),
    status: str | None = Query(default=None, max_length=50),
):
    """List budgets for the authenticated user's organization."""
    supabase = current_user["client"]

    query = (
        supabase.table("budgets")
        .select(
            "id,organization_id,fiscal_year,budget_code,category,"
            "allocated_amount,spent_amount,committed_amount,status,"
            "created_at,updated_at"
        )
        .order("fiscal_year", desc=True)
        .limit(limit)
    )

    if fiscal_year:
        query = query.eq("fiscal_year", fiscal_year)
    if status:
        query = query.eq("status", status)

    response = query.execute()
    return response.data or []


@router.get("/budgets/{budget_id}", response_model=Budget)
def get_budget(
    budget_id: UUID,
    current_user=Depends(get_current_user),
):
    """Retrieve a single budget by ID."""
    supabase = current_user["client"]

    response = (
        supabase.table("budgets")
        .select(
            "id,organization_id,fiscal_year,budget_code,category,"
            "allocated_amount,spent_amount,committed_amount,status,"
            "created_at,updated_at"
        )
        .eq("id", str(budget_id))
        .maybe_single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Budget not found")

    return response.data


@router.get("/expenses", response_model=list[Expense])
def list_expenses(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
    budget_id: UUID | None = Query(default=None),
    work_order_id: UUID | None = Query(default=None),
):
    """List expenses for the authenticated user's organization."""
    supabase = current_user["client"]

    query = (
        supabase.table("expenses")
        .select(
            "id,organization_id,budget_id,work_order_id,expense_date,"
            "description,category,amount,reference_no,status,"
            "created_by,created_at"
        )
        .order("expense_date", desc=True)
        .limit(limit)
    )

    if budget_id:
        query = query.eq("budget_id", str(budget_id))
    if work_order_id:
        query = query.eq("work_order_id", str(work_order_id))

    response = query.execute()
    return response.data or []


@router.get("/expenses/{expense_id}", response_model=Expense)
def get_expense(
    expense_id: UUID,
    current_user=Depends(get_current_user),
):
    """Retrieve a single expense by ID."""
    supabase = current_user["client"]

    response = (
        supabase.table("expenses")
        .select(
            "id,organization_id,budget_id,work_order_id,expense_date,"
            "description,category,amount,reference_no,status,"
            "created_by,created_at"
        )
        .eq("id", str(expense_id))
        .maybe_single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Expense not found")

    return response.data
