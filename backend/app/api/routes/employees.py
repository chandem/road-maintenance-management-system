from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.employees import Employee

router = APIRouter(prefix="/employees", tags=["employees"])


@router.get("", response_model=list[Employee])
def list_employees(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None, max_length=50),
):
    """List employees for the authenticated user's organization."""
    supabase = current_user["client"]

    query = (
        supabase.table("employees")
        .select(
            "id,organization_id,employee_code,full_name,department_id,"
            "job_title,employment_type,hire_date,status,phone,"
            "created_at,updated_at"
        )
        .order("full_name")
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    response = query.execute()
    return response.data or []


@router.get("/{employee_id}", response_model=Employee)
def get_employee(
    employee_id: UUID,
    current_user=Depends(get_current_user),
):
    """Retrieve a single employee record by ID."""
    supabase = current_user["client"]

    response = (
        supabase.table("employees")
        .select(
            "id,organization_id,employee_code,full_name,department_id,"
            "job_title,employment_type,hire_date,status,phone,"
            "created_at,updated_at"
        )
        .eq("id", str(employee_id))
        .maybe_single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Employee not found")

    return response.data
