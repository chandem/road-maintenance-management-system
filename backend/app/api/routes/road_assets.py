from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.road_assets import RoadAsset, RoadAssetCreate, RoadAssetUpdate
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/road-assets", tags=["road-assets"])

SELECT_COLS = (
    "id,organization_id,road_id,road_section_id,asset_code,asset_type,name,"
    "chainage_km,latitude,longitude,condition_rating,criticality,status,"
    "installation_date,last_inspected_at,notes,created_by,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return org_id


@router.get("", response_model=list[RoadAsset])
def list_road_assets(
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer", "read_only"])),
    road_id: UUID | None = None,
    asset_type: str | None = Query(default=None, max_length=40),
    status: str | None = Query(default=None, max_length=40),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"].table("road_assets").select(SELECT_COLS)
        .eq("organization_id", _org_id(current_user))
        .order("asset_code").limit(limit)
    )
    if road_id:
        query = query.eq("road_id", str(road_id))
    if asset_type:
        query = query.eq("asset_type", asset_type)
    if status:
        query = query.eq("status", status)
    return query.execute().data or []


@router.get("/{asset_id}", response_model=RoadAsset)
def get_road_asset(
    asset_id: UUID,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer", "read_only"])),
):
    response = (
        current_user["client"].table("road_assets").select(SELECT_COLS)
        .eq("id", str(asset_id)).eq("organization_id", _org_id(current_user))
        .maybe_single().execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Road asset not found")
    return response.data


@router.post("", response_model=RoadAsset, status_code=201)
def create_road_asset(
    payload: RoadAssetCreate,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer"])),
):
    organization_id = _org_id(current_user)
    client = current_user["client"]
    # Verify both parent records belong to this organization before inserting.
    road = (
        client.table("roads").select("id")
        .eq("id", str(payload.road_id)).eq("organization_id", organization_id)
        .maybe_single().execute()
    )
    if not road.data:
        raise HTTPException(status_code=422, detail="Select a road in your organization.")
    if payload.road_section_id:
        section = (
            client.table("road_sections").select("id,road_id,organization_id")
            .eq("id", str(payload.road_section_id)).eq("road_id", str(payload.road_id))
            .eq("organization_id", organization_id).maybe_single().execute()
        )
        if not section.data:
            raise HTTPException(status_code=422, detail="The selected section must belong to this road and organization.")
    row = {
        **payload.model_dump(mode="json"),
        "organization_id": organization_id,
        "created_by": current_user["id"],
    }
    try:
        response = client.table("road_assets").insert(row).execute()
    except Exception as exc:
        message = str(exc).lower()
        if "duplicate" in message or "unique" in message:
            raise HTTPException(status_code=409, detail="An asset with this code already exists in your organization.") from exc
        raise
    if not response.data:
        raise HTTPException(status_code=500, detail="Road asset could not be created.")
    return response.data[0]


@router.patch("/{asset_id}", response_model=RoadAsset)
def update_road_asset(
    asset_id: UUID,
    payload: RoadAssetUpdate,
    current_user=Depends(require_department_access("road_asset", ["department_manager", "officer"])),
):
    client = current_user["client"]
    organization_id = _org_id(current_user)
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    existing = (
        client.table("road_assets").select("id,road_id")
        .eq("id", str(asset_id)).eq("organization_id", organization_id)
        .maybe_single().execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Road asset not found.")
    section_id = updates.get("road_section_id", None)
    if section_id:
        section = (
            client.table("road_sections").select("id")
            .eq("id", str(section_id)).eq("road_id", existing.data["road_id"])
            .eq("organization_id", organization_id).maybe_single().execute()
        )
        if not section.data:
            raise HTTPException(status_code=422, detail="The selected section must belong to this asset's road.")
    response = (
        client.table("road_assets").update(updates)
        .eq("id", str(asset_id)).eq("organization_id", organization_id).execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Road asset not found.")
    return response.data[0]
