from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.machinery import Machinery

router = APIRouter(prefix="/machinery", tags=["machinery"])


@router.get("", response_model=list[Machinery])
def list_machinery(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None, max_length=50),
):
    """List machinery assets for the authenticated user's organization."""
    supabase = current_user["client"]

    query = (
        supabase.table("machinery")
        .select(
            "id,organization_id,asset_code,name,machinery_type,make,model,"
            "serial_number,status,purchase_date,purchase_cost,current_hours,"
            "created_at,updated_at"
        )
        .order("name")
        .limit(limit)
    )

    if status:
        query = query.eq("status", status)

    response = query.execute()
    return response.data or []


@router.get("/{machinery_id}", response_model=Machinery)
def get_machinery(
    machinery_id: UUID,
    current_user=Depends(get_current_user),
):
    """Retrieve a single machinery record by ID."""
    supabase = current_user["client"]

    response = (
        supabase.table("machinery")
        .select(
            "id,organization_id,asset_code,name,machinery_type,make,model,"
            "serial_number,status,purchase_date,purchase_cost,current_hours,"
            "created_at,updated_at"
        )
        .eq("id", str(machinery_id))
        .maybe_single()
        .execute()
    )

    if not response.data:
        raise HTTPException(status_code=404, detail="Machinery record not found")

    return response.data
