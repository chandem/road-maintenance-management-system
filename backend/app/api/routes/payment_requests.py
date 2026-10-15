from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.payment_requests import (
    PaymentRequest,
    PaymentRequestCreate,
    PaymentRequestUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/finance/payment-requests", tags=["payment-requests"])

SELECT_COLS = (
    "id,organization_id,budget_id,request_no,title,payee,amount,currency,"
    "status,requested_on,due_date,notes,decided_by,decided_at,"
    "created_by,created_at,updated_at"
)

DECISION_STATUSES = {"approved", "rejected", "paid", "cancelled"}


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[PaymentRequest])
def list_payment_requests(
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer", "read_only"])
    ),
    status: str | None = Query(default=None, max_length=30),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"]
        .table("finance_payment_requests")
        .select(SELECT_COLS)
        .order("requested_on", desc=True)
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    return query.execute().data or []


@router.post("", response_model=PaymentRequest, status_code=201)
def create_payment_request(
    payload: PaymentRequestCreate,
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer"])
    ),
):
    organization_id = _org_id(current_user)
    body = payload.model_dump(mode="json")
    if body.get("requested_on") is None:
        body.pop("requested_on", None)
    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **body,
    }
    response = current_user["client"].table("finance_payment_requests").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Payment request could not be created")
    return response.data[0]


@router.patch("/{request_id}", response_model=PaymentRequest)
def update_payment_request(
    request_id: UUID,
    payload: PaymentRequestUpdate,
    current_user=Depends(
        require_department_access("finance", ["department_manager", "officer"])
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
        .table("finance_payment_requests")
        .update(updates)
        .eq("id", str(request_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Payment request not found")
    return response.data[0]
