from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.schemas.maintenance_plans import MaintenancePlan

router = APIRouter(prefix="/maintenance-plans", tags=["maintenance-plans"])


@router.get("", response_model=list[MaintenancePlan])
def list_maintenance_plans(
    current_user=Depends(get_current_user),
    status: str | None = Query(default=None),
    fiscal_year: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
):
    supabase = current_user["client"]
    query = (
        supabase.table("maintenance_plans")
        .select("id,organization_id,name,fiscal_year,plan_type,status,budget_amount,start_date,end_date,created_by,created_at,updated_at")
        .order("start_date", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if fiscal_year:
        query = query.eq("fiscal_year", fiscal_year)
    response = query.execute()
    return response.data
