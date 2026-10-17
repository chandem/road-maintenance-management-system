from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.api.dependencies import require_department_access
from app.schemas.maintenance_plan_activities import (
    MaintenancePlanActivity,
    MaintenancePlanActivityCreate,
    MaintenancePlanActivityUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/maintenance-plan-activities", tags=["maintenance-plan-activities"])

SELECT_COLS = (
    "id,organization_id,maintenance_plan_id,road_section_id,activity_name,description,"
    "unit,planned_quantity,unit_rate,planned_cost,actual_quantity,actual_cost,status,"
    "created_by,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


def _verify_plan_and_section(client, organization_id: str, plan_id: str, section_id: str | None):
    plan = (
        client.table("maintenance_plans")
        .select("id")
        .eq("id", plan_id)
        .eq("organization_id", organization_id)
        .maybe_single()
        .execute()
    )
    if not plan.data:
        raise HTTPException(status_code=404, detail="Maintenance plan not found in this organization.")
    if section_id:
        section = (
            client.table("road_sections")
            .select("id")
            .eq("id", section_id)
            .eq("organization_id", organization_id)
            .maybe_single()
            .execute()
        )
        if not section.data:
            raise HTTPException(status_code=404, detail="Road section not found in this organization.")


@router.get("", response_model=list[MaintenancePlanActivity])
def list_plan_activities(
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer", "read_only"])),
    maintenance_plan_id: UUID | None = Query(default=None),
    road_section_id: UUID | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
):
    query = (
        current_user["client"].table("maintenance_plan_activities")
        .select(SELECT_COLS)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if maintenance_plan_id:
        query = query.eq("maintenance_plan_id", str(maintenance_plan_id))
    if road_section_id:
        query = query.eq("road_section_id", str(road_section_id))
    return query.execute().data or []


@router.post("", response_model=MaintenancePlanActivity, status_code=201)
def create_plan_activity(
    payload: MaintenancePlanActivityCreate,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer"])),
):
    organization_id = _org_id(current_user)
    client = current_user["client"]
    _verify_plan_and_section(
        client, organization_id, str(payload.maintenance_plan_id),
        str(payload.road_section_id) if payload.road_section_id else None,
    )
    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **payload.model_dump(mode="json"),
    }
    response = client.table("maintenance_plan_activities").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Maintenance plan activity could not be created.")
    return response.data[0]


@router.patch("/{activity_id}", response_model=MaintenancePlanActivity)
def update_plan_activity(
    activity_id: UUID,
    payload: MaintenancePlanActivityUpdate,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer"])),
):
    organization_id = _org_id(current_user)
    client = current_user["client"]
    existing = (
        client.table("maintenance_plan_activities")
        .select("id,road_section_id")
        .eq("id", str(activity_id))
        .eq("organization_id", organization_id)
        .maybe_single()
        .execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Maintenance plan activity not found.")
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    section_id = updates.get("road_section_id", existing.data.get("road_section_id"))
    if section_id:
        section = (
            client.table("road_sections").select("id")
            .eq("id", str(section_id)).eq("organization_id", organization_id)
            .maybe_single().execute()
        )
        if not section.data:
            raise HTTPException(status_code=404, detail="Road section not found in this organization.")
    updates["updated_at"] = "now()"
    response = (
        client.table("maintenance_plan_activities").update(updates)
        .eq("id", str(activity_id)).eq("organization_id", organization_id).execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Maintenance plan activity not found.")
    return response.data[0]


@router.delete("/{activity_id}", status_code=204)
def delete_plan_activity(
    activity_id: UUID,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer"])),
):
    organization_id = _org_id(current_user)
    client = current_user["client"]
    existing = (
        client.table("maintenance_plan_activities").select("id,status")
        .eq("id", str(activity_id)).eq("organization_id", organization_id)
        .maybe_single().execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Maintenance plan activity not found.")
    if existing.data["status"] != "planned":
        raise HTTPException(status_code=409, detail="Only planned activities can be deleted.")
    response = (
        client.table("maintenance_plan_activities").delete()
        .eq("id", str(activity_id)).eq("organization_id", organization_id).execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Maintenance plan activity not found.")
    return Response(status_code=204)
