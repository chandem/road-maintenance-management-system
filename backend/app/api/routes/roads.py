from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.schemas.roads import Road

router = APIRouter(prefix="/roads", tags=["roads"])


@router.get("", response_model=list[Road])
def list_roads(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=100),
):
    supabase = current_user["client"]

    response = (
        supabase.table("roads")
        .select("id,organization_id,road_code,name,start_location,end_location,total_length_km,road_class,surface_type,status,created_at,updated_at")
        .order("name")
        .limit(limit)
        .execute()
    )

    return response.data
