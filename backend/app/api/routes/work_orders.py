from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.schemas.work_orders import WorkOrder

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


@router.get("", response_model=list[WorkOrder])
def list_work_orders(
    current_user=Depends(get_current_user),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    road_section_id: str | None = Query(default=None),
    maintenance_plan_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
):
    supabase = current_user["client"]
    query = (
        supabase.table("work_orders")
        .select("id,organization_id,road_section_id,maintenance_plan_id,work_order_no,title,maintenance_type,priority,status,planned_cost,actual_cost,planned_start,planned_end,actual_start,actual_end,created_by,created_at,updated_at")
        .order("planned_start", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if priority:
        query = query.eq("priority", priority)
    if road_section_id:
        query = query.eq("road_section_id", road_section_id)
    if maintenance_plan_id:
        query = query.eq("maintenance_plan_id", maintenance_plan_id)
    response = query.execute()
    return response.data
