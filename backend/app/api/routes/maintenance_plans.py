from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user, require_department_access
from app.schemas.maintenance_plans import (
    MaintenancePlan,
    MaintenancePlanCreate,
    MaintenancePlanUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/maintenance-plans", tags=["maintenance-plans"])

SELECT_COLS = (
    "id,organization_id,name,fiscal_year,plan_type,status,budget_amount,"
    "start_date,end_date,created_by,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(
            status_code=409, detail="User is not assigned to an organization."
        )
    return org_id


@router.get("", response_model=list[MaintenancePlan])
def list_maintenance_plans(
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer', 'read_only'])),
    status: str | None = Query(default=None),
    fiscal_year: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"]
        .table("maintenance_plans")
        .select(SELECT_COLS)
        .order("start_date", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if fiscal_year:
        query = query.eq("fiscal_year", fiscal_year)
    return query.execute().data or []


@router.get("/{plan_id}", response_model=MaintenancePlan)
def get_maintenance_plan(
    plan_id: UUID,
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer', 'read_only'])),
):
    response = (
        current_user["client"]
        .table("maintenance_plans")
        .select(SELECT_COLS)
        .eq("id", str(plan_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Maintenance plan not found")
    return response.data


@router.post("", response_model=MaintenancePlan, status_code=201)
def create_maintenance_plan(
    payload: MaintenancePlanCreate,
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer'])),
):
    organization_id = _org_id(current_user)
    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **payload.model_dump(mode="json"),
    }
    response = (
        current_user["client"].table("maintenance_plans").insert(row).execute()
    )
    if not response.data:
        raise HTTPException(
            status_code=500, detail="Maintenance plan could not be created"
        )
    return response.data[0]


@router.patch("/{plan_id}", response_model=MaintenancePlan)
def update_maintenance_plan(
    plan_id: UUID,
    payload: MaintenancePlanUpdate,
    current_user=Depends(require_department_access("road_asset", ['department_manager', 'officer'])),
):
    updates = {
        k: v
        for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("maintenance_plans")
        .update(updates)
        .eq("id", str(plan_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Maintenance plan not found")
    return response.data[0]
