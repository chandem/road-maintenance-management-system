from datetime import date
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.machinery_fuel import (
    MachineryFuelLog,
    MachineryFuelLogCreate,
    MachineryFuelLogSummary,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/machinery-fuel-logs", tags=["machinery-fuel-logs"])

SELECT_COLS = (
    "id,organization_id,machinery_id,log_date,fuel_quantity,fuel_unit,"
    "meter_hours,unit_cost,total_cost,notes,created_by,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[MachineryFuelLog])
def list_fuel_logs(
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
    machinery_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"]
        .table("machinery_fuel_logs")
        .select(SELECT_COLS)
        .order("log_date", desc=True)
        .limit(limit)
    )
    if machinery_id:
        query = query.eq("machinery_id", machinery_id)
    return query.execute().data or []


@router.get("/summary", response_model=MachineryFuelLogSummary)
def fuel_summary(
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
):
    rows = (
        current_user["client"]
        .table("machinery_fuel_logs")
        .select("fuel_quantity,total_cost,meter_hours")
        .limit(5000)
        .execute()
        .data
        or []
    )
    fuel = Decimal("0")
    cost = Decimal("0")
    with_meter = 0
    for row in rows:
        if row.get("fuel_quantity") is not None:
            fuel += Decimal(str(row["fuel_quantity"]))
        if row.get("total_cost") is not None:
            cost += Decimal(str(row["total_cost"]))
        if row.get("meter_hours") is not None:
            with_meter += 1
    return MachineryFuelLogSummary(
        total_logs=len(rows),
        total_fuel_quantity=fuel,
        total_cost=cost,
        logs_with_meter=with_meter,
    )


@router.post("", response_model=MachineryFuelLog, status_code=201)
def create_fuel_log(
    payload: MachineryFuelLogCreate,
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

    data = payload.model_dump(mode="json", exclude={"update_machinery_hours"})
    if data.get("log_date") is None:
        data["log_date"] = date.today().isoformat()
    if data.get("total_cost") is None and data.get("fuel_quantity") is not None and data.get("unit_cost") is not None:
        data["total_cost"] = float(Decimal(str(data["fuel_quantity"])) * Decimal(str(data["unit_cost"])))

    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **data,
    }
    response = current_user["client"].table("machinery_fuel_logs").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Fuel log could not be created")

    if payload.update_machinery_hours and payload.meter_hours is not None:
        current_user["client"].table("machinery").update(
            {"current_hours": float(payload.meter_hours)}
        ).eq("id", str(payload.machinery_id)).execute()

    return response.data[0]
