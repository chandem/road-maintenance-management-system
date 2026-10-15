from collections import Counter
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.leave_requests import (
    LeaveRequest,
    LeaveRequestCreate,
    LeaveRequestSummary,
    LeaveRequestUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/leave-requests", tags=["leave-requests"])

SELECT_COLS = (
    "id,organization_id,employee_id,leave_type,start_date,end_date,"
    "days_requested,status,reason,decision_notes,decided_by,decided_at,"
    "created_by,created_at,updated_at"
)

DECISION_STATUSES = {"approved", "rejected", "cancelled"}


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[LeaveRequest])
def list_leave_requests(
    current_user=Depends(
        require_department_access(
            "human_resources", ["department_manager", "officer", "read_only"]
        )
    ),
    status: str | None = Query(default=None, max_length=30),
    employee_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"]
        .table("hr_leave_requests")
        .select(SELECT_COLS)
        .order("start_date", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if employee_id:
        query = query.eq("employee_id", employee_id)
    return query.execute().data or []


@router.get("/summary", response_model=LeaveRequestSummary)
def leave_summary(
    current_user=Depends(
        require_department_access(
            "human_resources", ["department_manager", "officer", "read_only"]
        )
    ),
):
    rows = (
        current_user["client"]
        .table("hr_leave_requests")
        .select("status,leave_type")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_status = Counter((r.get("status") or "unknown").lower() for r in rows)
    by_type = Counter((r.get("leave_type") or "other").lower() for r in rows)
    return LeaveRequestSummary(
        total=len(rows),
        pending_count=by_status.get("pending", 0),
        approved_count=by_status.get("approved", 0),
        rejected_count=by_status.get("rejected", 0),
        by_type=dict(by_type),
    )


@router.post("", response_model=LeaveRequest, status_code=201)
def create_leave_request(
    payload: LeaveRequestCreate,
    current_user=Depends(
        require_department_access("human_resources", ["department_manager", "officer"])
    ),
):
    organization_id = _org_id(current_user)
    emp = (
        current_user["client"]
        .table("employees")
        .select("id")
        .eq("id", str(payload.employee_id))
        .maybe_single()
        .execute()
    )
    if not emp.data:
        raise HTTPException(status_code=400, detail="Employee not found in this organization")

    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        "status": "pending",
        **payload.model_dump(mode="json"),
    }
    response = current_user["client"].table("hr_leave_requests").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Leave request could not be created")
    return response.data[0]


@router.patch("/{request_id}", response_model=LeaveRequest)
def update_leave_request(
    request_id: UUID,
    payload: LeaveRequestUpdate,
    current_user=Depends(
        require_department_access("human_resources", ["department_manager", "officer"])
    ),
):
    updates = {k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    new_status = updates.get("status")
    if new_status and new_status.lower() in DECISION_STATUSES:
        updates["decided_by"] = current_user["id"]
        updates["decided_at"] = datetime.now(timezone.utc).isoformat()

    response = (
        current_user["client"]
        .table("hr_leave_requests")
        .update(updates)
        .eq("id", str(request_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Leave request not found")
    return response.data[0]
