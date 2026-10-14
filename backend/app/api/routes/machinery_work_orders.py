from collections import Counter
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.machinery_work_orders import (
    MachineryWorkOrder,
    MachineryWorkOrderCreate,
    MachineryWorkOrderSummary,
    MachineryWorkOrderUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/machinery-work-orders", tags=["machinery-work-orders"])

SELECT_COLS = (
    "id,organization_id,machinery_id,work_order_no,title,description,fault_type,"
    "priority,status,reported_at,planned_start,planned_end,actual_start,actual_end,"
    "estimated_cost,actual_cost,created_by,created_at,updated_at"
)

OPEN_STATUSES = {"reported", "diagnosed", "in_progress", "waiting_parts"}


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[MachineryWorkOrder])
def list_machinery_work_orders(
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
    status: str | None = Query(default=None, max_length=30),
    priority: str | None = Query(default=None, max_length=20),
    machinery_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"]
        .table("machinery_work_orders")
        .select(SELECT_COLS)
        .order("reported_at", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if priority:
        query = query.eq("priority", priority)
    if machinery_id:
        query = query.eq("machinery_id", machinery_id)
    return query.execute().data or []


@router.get("/summary", response_model=MachineryWorkOrderSummary)
def machinery_work_order_summary(
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
):
    rows = (
        current_user["client"]
        .table("machinery_work_orders")
        .select("status,priority")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_status = Counter((r.get("status") or "unknown").lower() for r in rows)
    by_priority = Counter((r.get("priority") or "unknown").lower() for r in rows)
    open_count = sum(by_status[s] for s in OPEN_STATUSES if s in by_status)
    return MachineryWorkOrderSummary(
        total=len(rows),
        open_count=open_count,
        completed_count=by_status.get("completed", 0),
        by_status=dict(by_status),
        by_priority=dict(by_priority),
    )


@router.get("/{work_order_id}", response_model=MachineryWorkOrder)
def get_machinery_work_order(
    work_order_id: UUID,
    current_user=Depends(
        require_department_access(
            "machinery_maintenance", ["department_manager", "officer", "read_only"]
        )
    ),
):
    response = (
        current_user["client"]
        .table("machinery_work_orders")
        .select(SELECT_COLS)
        .eq("id", str(work_order_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Machinery work order not found")
    return response.data


@router.post("", response_model=MachineryWorkOrder, status_code=201)
def create_machinery_work_order(
    payload: MachineryWorkOrderCreate,
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

    data = payload.model_dump(mode="json")
    if data.get("reported_at") is None:
        data["reported_at"] = date.today().isoformat()
    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **data,
    }
    response = current_user["client"].table("machinery_work_orders").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Machinery work order could not be created")
    return response.data[0]


@router.patch("/{work_order_id}", response_model=MachineryWorkOrder)
def update_machinery_work_order(
    work_order_id: UUID,
    payload: MachineryWorkOrderUpdate,
    current_user=Depends(
        require_department_access("machinery_maintenance", ["department_manager", "officer"])
    ),
):
    updates = {k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("machinery_work_orders")
        .update(updates)
        .eq("id", str(work_order_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Machinery work order not found")
    return response.data[0]
