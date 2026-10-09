from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user, require_department_access
from app.schemas.roads import Road, RoadCreate, RoadUpdate
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/roads", tags=["roads"])

SELECT_COLS = (
    "id,organization_id,road_code,name,start_location,end_location,"
    "total_length_km,road_class,surface_type,status,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[Road])
def list_roads(
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer", "read_only"])),
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None, max_length=50),
):
    query = (
        current_user["client"]
        .table("roads")
        .select(SELECT_COLS)
        .eq("organization_id", _org_id(current_user))
        .order("name")
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    return query.execute().data or []


@router.get("/{road_id}", response_model=Road)
def get_road(
    road_id: UUID,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer", "read_only"])),
):
    response = (
        current_user["client"]
        .table("roads")
        .select(SELECT_COLS)
        .eq("id", str(road_id))
        .eq("organization_id", _org_id(current_user))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Road not found")
    return response.data


@router.post("", response_model=Road, status_code=201)
def create_road(
    payload: RoadCreate,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer"])),
):
    organization_id = _org_id(current_user)
    row = {"organization_id": organization_id, **payload.model_dump(mode="json")}
    response = current_user["client"].table("roads").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Road could not be created")
    return response.data[0]


@router.patch("/{road_id}", response_model=Road)
def update_road(
    road_id: UUID,
    payload: RoadUpdate,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer"])),
):
    updates = {
        k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("roads")
        .update(updates)
        .eq("id", str(road_id))
        .eq("organization_id", _org_id(current_user))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Road not found")
    return response.data[0]
