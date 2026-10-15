from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from postgrest.exceptions import APIError

from app.api.dependencies import require_department_access
from app.schemas.finance import (
    Budget,
    BudgetCreate,
    BudgetLineReport,
    BudgetUpdate,
    Expense,
    ExpenseCreate,
    FinanceReport,
    FinanceSummary,
    PaymentRequestStatusCount,
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
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer", "read_only"])
    ),
    fiscal_year: str | None = Query(default=None, max_length=20),
):
    """Budget utilization snapshot (Financial Management)."""
    supabase = current_user["client"]
    budget_query = (
        supabase.table("budgets")
        .select("allocated_amount,spent_amount,committed_amount,status,fiscal_year")
        .limit(500)
    )
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


@router.get("/report", response_model=FinanceReport)
def finance_report(
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer", "read_only"])
    ),
    fiscal_year: str | None = Query(default=None, max_length=20),
):
    """Budget vs actual with payment-request commitment snapshot."""
    supabase = current_user["client"]

    budget_query = (
        supabase.table("budgets")
        .select(
            "id,fiscal_year,budget_code,category,status,"
            "allocated_amount,spent_amount,committed_amount"
        )
        .order("fiscal_year", desc=True)
        .limit(200)
    )
    if fiscal_year:
        budget_query = budget_query.eq("fiscal_year", fiscal_year)
    budgets = budget_query.execute().data or []

    expenses = (
        supabase.table("expenses").select("id,amount").limit(5000).execute().data or []
    )

    payment_rows = (
        supabase.table("finance_payment_requests")
        .select("status,amount")
        .limit(2000)
        .execute()
        .data
        or []
    )

    total_allocated = sum(Decimal(str(b.get("allocated_amount") or 0)) for b in budgets)
    total_spent = sum(Decimal(str(b.get("spent_amount") or 0)) for b in budgets)
    total_committed = sum(Decimal(str(b.get("committed_amount") or 0)) for b in budgets)
    remaining = total_allocated - total_spent - total_committed
    utilization = (
        float((total_spent + total_committed) / total_allocated * 100)
        if total_allocated > 0
        else 0.0
    )
    expense_total = sum(Decimal(str(e.get("amount") or 0)) for e in expenses)

    status_map: dict[str, tuple[int, Decimal]] = {}
    open_count = 0
    open_amount = Decimal("0")
    open_statuses = {"draft", "submitted", "approved"}
    for row in payment_rows:
        st = str(row.get("status") or "unknown")
        amt = Decimal(str(row.get("amount") or 0))
        count, total = status_map.get(st, (0, Decimal("0")))
        status_map[st] = (count + 1, total + amt)
        if st in open_statuses:
            open_count += 1
            open_amount += amt

    by_status = [
        PaymentRequestStatusCount(status=st, count=c, total_amount=t)
        for st, (c, t) in sorted(status_map.items())
    ]

    lines: list[BudgetLineReport] = []
    for b in budgets:
        allocated = Decimal(str(b.get("allocated_amount") or 0))
        spent = Decimal(str(b.get("spent_amount") or 0))
        committed = Decimal(str(b.get("committed_amount") or 0))
        rem = allocated - spent - committed
        util = float((spent + committed) / allocated * 100) if allocated > 0 else 0.0
        lines.append(
            BudgetLineReport(
                budget_id=b["id"],
                fiscal_year=b.get("fiscal_year"),
                budget_code=b.get("budget_code"),
                category=b.get("category"),
                status=b.get("status"),
                allocated=allocated,
                spent=spent,
                committed=committed,
                remaining=rem,
                utilization_percent=round(util, 2),
            )
        )

    return FinanceReport(
        fiscal_year=fiscal_year,
        total_allocated=total_allocated,
        total_spent=total_spent,
        total_committed=total_committed,
        remaining=remaining,
        utilization_percent=round(utilization, 2),
        expense_count=len(expenses),
        expense_total=expense_total,
        payment_request_open_count=open_count,
        payment_request_open_amount=open_amount,
        payment_requests_by_status=by_status,
        budgets=lines,
    )


@router.get("/budgets", response_model=list[Budget])
def list_budgets(
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer", "read_only"])
    ),
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
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer", "read_only"])
    ),
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
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer"])
    ),
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
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer"])
    ),
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
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer", "read_only"])
    ),
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
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer", "read_only"])
    ),
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
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer"])
    ),
):
    """Record an expense and atomically update the linked budget totals."""
    organization_id = _org_id(current_user)
    try:
        result = (
            current_user["client"]
            .rpc(
                "record_finance_expense",
                {
                    "p_organization_id": organization_id,
                    "p_created_by": current_user["id"],
                    "p_budget_id": str(payload.budget_id) if payload.budget_id else None,
                    "p_work_order_id": str(payload.work_order_id)
                    if payload.work_order_id
                    else None,
                    "p_expense_date": payload.expense_date.isoformat(),
                    "p_description": payload.description.strip(),
                    "p_category": payload.category,
                    "p_amount": str(payload.amount),
                    "p_reference_no": payload.reference_no,
                    "p_status": payload.status,
                },
            )
            .execute()
        )
    except APIError as exc:
        if getattr(exc, "code", None) == "P0001":
            raise HTTPException(
                status_code=409,
                detail=getattr(exc, "message", None)
                or "Expense conflicts with the budget rules.",
            ) from exc
        raise HTTPException(
            status_code=400,
            detail=getattr(exc, "message", None) or "Expense could not be recorded.",
        ) from exc
    data = result.data
    if isinstance(data, list):
        data = data[0] if data else None
    if not data:
        raise HTTPException(status_code=500, detail="Expense could not be recorded")
    return data
