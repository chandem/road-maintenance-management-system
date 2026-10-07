from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.assets import Asset

router = APIRouter(prefix="/assets", tags=["assets"])


@router.get("", response_model=list[Asset])
def list_assets(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None, max_length=50),
    category: str | None = Query(default=None, max_length=100),
):
    """List general assets for the authenticated user's organization."""
    supabase = current_user["client"]

    query = (
        supabase.table("assets")
        .select(
            "id,organization_id,asset_code,name,category,location,status,"
            "acquisition_date,acquisition_cost,current_value,assigned_to,"
            "created_at,updated_at"
        )
        .order("name")
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)
    if category:
        query = query.eq("category", category)

    response = query.execute()
    return response.data or []


@router.get("/{asset_id}", response_model=Asset)
def get_asset(
    asset_id: UUID,
    current_user=Depends(get_current_user),
):
    """Retrieve a single asset record by ID."""
    supabase = current_user["client"]

    response = (
        supabase.table("assets")
        .select(
            "id,organization_id,asset_code,name,category,location,status,"
            "acquisition_date,acquisition_cost,current_value,assigned_to,"
            "created_at,updated_at"
        )
        .eq("id", str(asset_id))
        .maybe_single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Asset not found")

    return response.data
