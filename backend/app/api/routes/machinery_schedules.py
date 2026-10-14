from collections import Counter
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.machinery_schedules import (
    MachineryMaintenanceSchedule,
    MachineryMaintenanceScheduleCreate,
    MachineryMaintenanceScheduleSummary,
    MachineryMaintenanceScheduleUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/machinery-schedules", tags=["machinery-schedules"])

SELECT_COLS = (
    "id,organization_id,machinery_id,schedule_code,title,service_type,"
    "interval_hours,interval_days,last_service_date,last_service_hours,"
    "next_due_date,next_due_hours,status,notes,created_by,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[MachineryMaintenanceSchedule])
def list_schedules(
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
    status: str | None = Query(default=None, max_length=30),
    machinery_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"]
        .table("machinery_maintenance_schedules")
        .select(SELECT_COLS)
        .order("next_due_date")
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if machinery_id:
        query = query.eq("machinery_id", machinery_id)
    return query.execute().data or []


@router.get("/summary", response_model=MachineryMaintenanceScheduleSummary)
def schedules_summary(
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
):
    rows = (
        current_user["client"]
        .table("machinery_maintenance_schedules")
        .select("status,next_due_date")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_status = Counter((r.get("status") or "unknown").lower() for r in rows)
    horizon = date.today() + timedelta(days=30)
    due_soon = 0
    for row in rows:
        if (row.get("status") or "").lower() != "active":
            continue
        due = row.get("next_due_date")
        if not due:
            continue
        try:
            due_d = date.fromisoformat(str(due)[:10])
        except ValueError:
            continue
        if due_d <= horizon:
            due_soon += 1
    return MachineryMaintenanceScheduleSummary(
        total=len(rows),
        active_count=by_status.get("active", 0),
        due_soon_count=due_soon,
        by_status=dict(by_status),
    )


@router.get("/{schedule_id}", response_model=MachineryMaintenanceSchedule)
def get_schedule(
    schedule_id: UUID,
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
):
    response = (
        current_user["client"]
        .table("machinery_maintenance_schedules")
        .select(SELECT_COLS)
        .eq("id", str(schedule_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")
    return response.data


@router.post("", response_model=MachineryMaintenanceSchedule, status_code=201)
def create_schedule(
    payload: MachineryMaintenanceScheduleCreate,
    current_user=Depends(
        require_department_access("machinery_maintenance", ["department_manager", "officer"])
    ),
):
    organization_id = _org_id(current_user)
    machine = (
        current_user["client"]
        .table("machinery")
        .select("id")
        .eq("id", str(payload.machinery_id))
        .maybe_single()
        .execute()
    )
    if not machine.data:
        raise HTTPException(status_code=400, detail="Machinery asset not found in this organization")

    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **payload.model_dump(mode="json"),
    }
    response = (
        current_user["client"].table("machinery_maintenance_schedules").insert(row).execute()
    )
    if not response.data:
        raise HTTPException(status_code=500, detail="Maintenance schedule could not be created")
    return response.data[0]


@router.patch("/{schedule_id}", response_model=MachineryMaintenanceSchedule)
def update_schedule(
    schedule_id: UUID,
    payload: MachineryMaintenanceScheduleUpdate,
    current_user=Depends(
        require_department_access("machinery_maintenance", ["department_manager", "officer"])
    ),
):
    updates = {k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("machinery_maintenance_schedules")
        .update(updates)
        .eq("id", str(schedule_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Maintenance schedule not found")
    return response.data[0]
