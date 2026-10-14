"""Aggregated MMMS fleet report from existing operational tables."""

from __future__ import annotations

from collections import Counter
from datetime import date, timedelta
from decimal import Decimal

from fastapi import APIRouter, Depends

from app.api.dependencies import require_department_access

router = APIRouter(prefix="/machinery", tags=["machinery-fleet-report"])

AVAILABLE = {"available", "ready", "operational"}
DOWN = {"down", "under_maintenance", "broken", "unavailable"}
OPEN_WO = {"reported", "diagnosed", "in_progress", "waiting_parts"}


@router.get("/fleet-report")
def fleet_report(
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
) -> dict:
    """Fleet availability, open repairs, PM due soon, and fuel cost summary."""
    client = current_user["client"]

    machinery = (
        client.table("machinery")
        .select("id,asset_code,name,status,machinery_type,current_hours")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_status = Counter((r.get("status") or "unknown").lower() for r in machinery)
    available = sum(by_status[s] for s in AVAILABLE if s in by_status)
    down = sum(by_status[s] for s in DOWN if s in by_status)

    work_orders: list = []
    try:
        work_orders = (
            client.table("machinery_work_orders")
            .select("status,priority,estimated_cost,actual_cost")
            .limit(2000)
            .execute()
            .data
            or []
        )
    except Exception:
        work_orders = []

    wo_by_status = Counter((r.get("status") or "unknown").lower() for r in work_orders)
    open_wo = sum(wo_by_status[s] for s in OPEN_WO if s in wo_by_status)
    repair_cost = Decimal("0")
    for row in work_orders:
        val = row.get("actual_cost") if row.get("actual_cost") is not None else row.get("estimated_cost")
        if val is not None:
            repair_cost += Decimal(str(val))

    schedules: list = []
    due_soon = 0
    horizon = date.today() + timedelta(days=30)
    try:
        schedules = (
            client.table("machinery_maintenance_schedules")
            .select("status,next_due_date")
            .limit(2000)
            .execute()
            .data
            or []
        )
        for row in schedules:
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
    except Exception:
        schedules = []

    fuel_qty = Decimal("0")
    fuel_cost = Decimal("0")
    fuel_logs = 0
    try:
        fuel_rows = (
            client.table("machinery_fuel_logs")
            .select("fuel_quantity,total_cost")
            .limit(5000)
            .execute()
            .data
            or []
        )
        fuel_logs = len(fuel_rows)
        for row in fuel_rows:
            if row.get("fuel_quantity") is not None:
                fuel_qty += Decimal(str(row["fuel_quantity"]))
            if row.get("total_cost") is not None:
                fuel_cost += Decimal(str(row["total_cost"]))
    except Exception:
        pass

    high_hour_units = sorted(
        [
            {
                "asset_code": r.get("asset_code"),
                "name": r.get("name"),
                "current_hours": r.get("current_hours"),
                "status": r.get("status"),
            }
            for r in machinery
            if r.get("current_hours") is not None
        ],
        key=lambda x: float(x["current_hours"] or 0),
        reverse=True,
    )[:10]

    return {
        "title": "MMMS Fleet Report",
        "fleet": {
            "total": len(machinery),
            "available_count": available,
            "down_or_maintenance_count": down,
            "by_status": dict(by_status),
        },
        "repairs": {
            "total_work_orders": len(work_orders),
            "open_count": open_wo,
            "by_status": dict(wo_by_status),
            "estimated_or_actual_cost": float(repair_cost),
        },
        "preventive": {
            "total_schedules": len(schedules),
            "due_within_30_days": due_soon,
        },
        "fuel": {
            "log_count": fuel_logs,
            "total_quantity": float(fuel_qty),
            "total_cost": float(fuel_cost),
        },
        "highest_hour_units": high_hour_units,
        "advisory_note": (
            "Decision-support only. Figures come from registered equipment, "
            "work orders, schedules, and fuel logs visible to your department."
        ),
    }
