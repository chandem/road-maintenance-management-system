from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user, require_department_access
from app.schemas.work_orders import WorkOrder, WorkOrderCreate, WorkOrderUpdate
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/work-orders", tags=["work-orders"])

SELECT_COLS = (
    "id,organization_id,road_section_id,maintenance_plan_id,work_order_no,title,"
    "maintenance_type,priority,status,planned_cost,actual_cost,planned_start,"
    "planned_end,actual_start,actual_end,created_by,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[WorkOrder])
def list_work_orders(
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer', 'read_only'])),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    road_section_id: str | None = Query(default=None),
    maintenance_plan_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"]
        .table("work_orders")
        .select(SELECT_COLS)
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
    return query.execute().data or []


@router.get("/{work_order_id}", response_model=WorkOrder)
def get_work_order(work_order_id: UUID, current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer', 'read_only']))):
    response = (
        current_user["client"]
        .table("work_orders")
        .select(SELECT_COLS)
        .eq("id", str(work_order_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Work order not found")
    return response.data


@router.post("", response_model=WorkOrder, status_code=201)
def create_work_order(
    payload: WorkOrderCreate,
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer'])),
):
    organization_id = _org_id(current_user)
    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **payload.model_dump(mode="json"),
    }
    response = current_user["client"].table("work_orders").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Work order could not be created")
    return response.data[0]


@router.patch("/{work_order_id}", response_model=WorkOrder)
def update_work_order(
    work_order_id: UUID,
    payload: WorkOrderUpdate,
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer'])),
):
    updates = {
        k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("work_orders")
        .update(updates)
        .eq("id", str(work_order_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Work order not found")
    return response.data[0]
