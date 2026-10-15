from collections import Counter
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.training_records import (
    TrainingRecord,
    TrainingRecordCreate,
    TrainingRecordSummary,
    TrainingRecordUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/training-records", tags=["training-records"])

SELECT_COLS = (
    "id,organization_id,employee_id,title,record_type,provider,certificate_no,"
    "completed_on,expires_on,status,notes,created_by,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[TrainingRecord])
def list_training_records(
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
        .table("hr_training_records")
        .select(SELECT_COLS)
        .order("expires_on")
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if employee_id:
        query = query.eq("employee_id", employee_id)
    return query.execute().data or []


@router.get("/summary", response_model=TrainingRecordSummary)
def training_summary(
    current_user=Depends(
        require_department_access(
            "human_resources", ["department_manager", "officer", "read_only"]
        )
    ),
):
    rows = (
        current_user["client"]
        .table("hr_training_records")
        .select("status,record_type,expires_on")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_status = Counter((r.get("status") or "unknown").lower() for r in rows)
    by_type = Counter((r.get("record_type") or "other").lower() for r in rows)
    horizon = date.today() + timedelta(days=60)
    expiring = 0
    for row in rows:
        if (row.get("status") or "").lower() != "valid":
            continue
        exp = row.get("expires_on")
        if not exp:
            continue
        try:
            exp_d = date.fromisoformat(str(exp)[:10])
        except ValueError:
            continue
        if date.today() <= exp_d <= horizon:
            expiring += 1
    return TrainingRecordSummary(
        total=len(rows),
        valid_count=by_status.get("valid", 0),
        expiring_soon_count=expiring,
        expired_count=by_status.get("expired", 0),
        by_type=dict(by_type),
    )


@router.post("", response_model=TrainingRecord, status_code=201)
def create_training_record(
    payload: TrainingRecordCreate,
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
        **payload.model_dump(mode="json"),
    }
    response = current_user["client"].table("hr_training_records").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Training record could not be created")
    return response.data[0]


@router.patch("/{record_id}", response_model=TrainingRecord)
def update_training_record(
    record_id: UUID,
    payload: TrainingRecordUpdate,
    current_user=Depends(
        require_department_access("human_resources", ["department_manager", "officer"])
    ),
):
    updates = {k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("hr_training_records")
        .update(updates)
        .eq("id", str(record_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Training record not found")
    return response.data[0]
