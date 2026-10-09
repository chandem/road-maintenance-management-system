from collections import Counter
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.machinery import (
    Machinery,
    MachineryCreate,
    MachinerySummary,
    MachineryUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/machinery", tags=["machinery"])

SELECT_COLS = (
    "id,organization_id,asset_code,name,machinery_type,make,model,"
    "serial_number,status,purchase_date,purchase_cost,current_hours,"
    "created_at,updated_at"
)

AVAILABLE_STATUSES = {"available", "ready", "operational"}
DOWN_STATUSES = {"down", "under_maintenance", "broken", "unavailable"}


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[Machinery])
def list_machinery(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None, max_length=50),
    machinery_type: str | None = Query(default=None, max_length=100),
):
    """List machinery for the authenticated user's organization (MMMS)."""
    supabase = current_user["client"]
    query = (
        supabase.table("machinery")
        .select(SELECT_COLS)
        .order("name")
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if machinery_type:
        query = query.eq("machinery_type", machinery_type)
    return query.execute().data or []


@router.get("/summary", response_model=MachinerySummary)
def machinery_summary(current_user=Depends(get_current_user)):
    """Operational availability summary for MMMS."""
    rows = (
        current_user["client"]
        .table("machinery")
        .select("status")
        .limit(2000)
        .execute()
        .data
        or []
    )
    counts = Counter((row.get("status") or "unknown").lower() for row in rows)
    available = sum(counts[s] for s in AVAILABLE_STATUSES if s in counts)
    down = sum(counts[s] for s in DOWN_STATUSES if s in counts)
    return MachinerySummary(
        total=len(rows),
        by_status=dict(counts),
        available_count=available,
        down_or_maintenance_count=down,
    )


@router.get("/{machinery_id}", response_model=Machinery)
def get_machinery(
    machinery_id: UUID,
    current_user=Depends(get_current_user),
):
    response = (
        current_user["client"]
        .table("machinery")
        .select(SELECT_COLS)
        .eq("id", str(machinery_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Machinery record not found")
    return response.data


@router.post("", response_model=Machinery, status_code=201)
def create_machinery(
    payload: MachineryCreate,
    current_user=Depends(get_current_user),
):
    """Register a machinery asset (MMMS)."""
    organization_id = _org_id(current_user)
    row = {
        "organization_id": organization_id,
        **payload.model_dump(mode="json"),
    }
    response = current_user["client"].table("machinery").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Machinery could not be created")
    return response.data[0]


@router.patch("/{machinery_id}", response_model=Machinery)
def update_machinery(
    machinery_id: UUID,
    payload: MachineryUpdate,
    current_user=Depends(get_current_user),
):
    """Update machinery fields (status, hours, identity)."""
    updates = {k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    response = (
        current_user["client"]
        .table("machinery")
        .update(updates)
        .eq("id", str(machinery_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Machinery record not found")
    return response.data[0]
