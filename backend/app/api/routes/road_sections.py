from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.road_sections import RoadSection, RoadSectionCreate, RoadSectionUpdate
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/road-sections", tags=["road-sections"])

SELECT_COLS = (
    "id,organization_id,road_id,section_code,start_chainage_km,end_chainage_km,"
    "length_km,condition_rating,status,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[RoadSection])
def list_road_sections(
    current_user=Depends(get_current_user),
    road_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"]
        .table("road_sections")
        .select(SELECT_COLS)
        .order("start_chainage_km")
        .limit(limit)
    )
    if road_id:
        query = query.eq("road_id", road_id)
    return query.execute().data or []


@router.get("/{section_id}", response_model=RoadSection)
def get_road_section(section_id: UUID, current_user=Depends(get_current_user)):
    response = (
        current_user["client"]
        .table("road_sections")
        .select(SELECT_COLS)
        .eq("id", str(section_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Road section not found")
    return response.data


@router.post("", response_model=RoadSection, status_code=201)
def create_road_section(
    payload: RoadSectionCreate,
    current_user=Depends(get_current_user),
):
    organization_id = _org_id(current_user)
    row = {"organization_id": organization_id, **payload.model_dump(mode="json")}
    response = current_user["client"].table("road_sections").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Road section could not be created")
    return response.data[0]


@router.patch("/{section_id}", response_model=RoadSection)
def update_road_section(
    section_id: UUID,
    payload: RoadSectionUpdate,
    current_user=Depends(get_current_user),
):
    updates = {
        k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("road_sections")
        .update(updates)
        .eq("id", str(section_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Road section not found")
    return response.data[0]
