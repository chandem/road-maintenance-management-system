from collections import Counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.employees import (
    Employee,
    EmployeeCreate,
    EmployeeSummary,
    EmployeeUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/employees", tags=["employees"])

SELECT_COLS = (
    "id,organization_id,employee_code,full_name,department_id,"
    "job_title,employment_type,hire_date,status,phone,"
    "created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[Employee])
def list_employees(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None, max_length=50),
    department_id: UUID | None = Query(default=None),
):
    """List employees for the authenticated user's organization (HR)."""
    query = (
        current_user["client"]
        .table("employees")
        .select(SELECT_COLS)
        .order("full_name")
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if department_id:
        query = query.eq("department_id", str(department_id))
    return query.execute().data or []


@router.get("/summary", response_model=EmployeeSummary)
def employee_summary(current_user=Depends(get_current_user)):
    """Workforce summary for HR Management."""
    rows = (
        current_user["client"]
        .table("employees")
        .select("status,employment_type")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_status = Counter((r.get("status") or "unknown").lower() for r in rows)
    by_type = Counter((r.get("employment_type") or "unspecified").lower() for r in rows)
    return EmployeeSummary(
        total=len(rows),
        active_count=by_status.get("active", 0),
        by_status=dict(by_status),
        by_employment_type=dict(by_type),
    )


@router.get("/{employee_id}", response_model=Employee)
def get_employee(
    employee_id: UUID,
    current_user=Depends(get_current_user),
):
    response = (
        current_user["client"]
        .table("employees")
        .select(SELECT_COLS)
        .eq("id", str(employee_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Employee not found")
    return response.data


@router.post("", response_model=Employee, status_code=201)
def create_employee(
    payload: EmployeeCreate,
    current_user=Depends(get_current_user),
):
    """Register an employee record (HR)."""
    organization_id = _org_id(current_user)
    row = {"organization_id": organization_id, **payload.model_dump(mode="json")}
    response = current_user["client"].table("employees").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Employee could not be created")
    return response.data[0]


@router.patch("/{employee_id}", response_model=Employee)
def update_employee(
    employee_id: UUID,
    payload: EmployeeUpdate,
    current_user=Depends(get_current_user),
):
    updates = {
        k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("employees")
        .update(updates)
        .eq("id", str(employee_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Employee not found")
    return response.data[0]
