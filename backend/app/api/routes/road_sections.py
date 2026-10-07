from fastapi import APIRouter, Depends, Query

from app.api.dependencies import get_current_user
from app.schemas.road_sections import RoadSection

router = APIRouter(prefix="/road-sections", tags=["road-sections"])


@router.get("", response_model=list[RoadSection])
def list_road_sections(
    current_user=Depends(get_current_user),
    road_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=100),
):
    supabase = current_user["client"]
    query = (
        supabase.table("road_sections")
        .select("id,organization_id,road_id,section_code,start_chainage_km,end_chainage_km,length_km,condition_rating,status,created_at,updated_at")
        .order("start_chainage_km")
        .limit(limit)
    )
    if road_id:
        query = query.eq("road_id", road_id)
    response = query.execute()
    return response.data
