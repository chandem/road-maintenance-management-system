from collections import Counter
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.assets import Asset, AssetCreate, AssetSummary, AssetUpdate
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/assets", tags=["assets"])

SELECT_COLS = (
    "id,organization_id,asset_code,name,category,location,status,"
    "acquisition_date,acquisition_cost,current_value,assigned_to,"
    "created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[Asset])
def list_assets(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None, max_length=50),
    category: str | None = Query(default=None, max_length=100),
):
    """List general assets (not roads/machinery)."""
    query = (
        current_user["client"]
        .table("assets")
        .select(SELECT_COLS)
        .order("name")
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if category:
        query = query.eq("category", category)
    return query.execute().data or []


@router.get("/summary", response_model=AssetSummary)
def asset_summary(current_user=Depends(get_current_user)):
    """General asset portfolio summary."""
    rows = (
        current_user["client"]
        .table("assets")
        .select("status,category,current_value")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_status = Counter((r.get("status") or "unknown").lower() for r in rows)
    by_category = Counter((r.get("category") or "unspecified").lower() for r in rows)
    total_value = sum(Decimal(str(r.get("current_value") or 0)) for r in rows)
    return AssetSummary(
        total=len(rows),
        active_count=by_status.get("active", 0),
        by_status=dict(by_status),
        by_category=dict(by_category),
        total_current_value=total_value,
    )


@router.get("/{asset_id}", response_model=Asset)
def get_asset(
    asset_id: UUID,
    current_user=Depends(get_current_user),
):
    response = (
        current_user["client"]
        .table("assets")
        .select(SELECT_COLS)
        .eq("id", str(asset_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Asset not found")
    return response.data


@router.post("", response_model=Asset, status_code=201)
def create_asset(
    payload: AssetCreate,
    current_user=Depends(get_current_user),
):
    """Register a general organizational asset."""
    organization_id = _org_id(current_user)
    row = {"organization_id": organization_id, **payload.model_dump(mode="json")}
    response = current_user["client"].table("assets").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Asset could not be created")
    return response.data[0]


@router.patch("/{asset_id}", response_model=Asset)
def update_asset(
    asset_id: UUID,
    payload: AssetUpdate,
    current_user=Depends(get_current_user),
):
    updates = {
        k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("assets")
        .update(updates)
        .eq("id", str(asset_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Asset not found")
    return response.data[0]
