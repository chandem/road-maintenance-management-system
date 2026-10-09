from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.inspections import (
    RoadInspection,
    RoadInspectionCreate,
    RoadInspectionUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/inspections", tags=["inspections"])

SELECT_COLS = (
    "id,organization_id,road_section_id,inspection_date,inspector_name,"
    "condition_rating,surface_condition,defects_summary,recommended_action,"
    "weather_notes,status,created_by,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(
            status_code=409, detail="User is not assigned to an organization."
        )
    return org_id


@router.get("", response_model=list[RoadInspection])
def list_inspections(
    current_user=Depends(get_current_user),
    road_section_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
):
    """List road inspections (newest first)."""
    query = (
        current_user["client"]
        .table("road_inspections")
        .select(SELECT_COLS)
        .order("inspection_date", desc=True)
        .limit(limit)
    )
    if road_section_id:
        query = query.eq("road_section_id", str(road_section_id))
    return query.execute().data or []


@router.get("/{inspection_id}", response_model=RoadInspection)
def get_inspection(
    inspection_id: UUID,
    current_user=Depends(get_current_user),
):
    response = (
        current_user["client"]
        .table("road_inspections")
        .select(SELECT_COLS)
        .eq("id", str(inspection_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return response.data


@router.post("", response_model=RoadInspection, status_code=201)
def create_inspection(
    payload: RoadInspectionCreate,
    current_user=Depends(get_current_user),
):
    """Record an inspection; optionally refresh section condition_rating."""
    organization_id = _org_id(current_user)
    supabase = current_user["client"]

    section = (
        supabase.table("road_sections")
        .select("id")
        .eq("id", str(payload.road_section_id))
        .maybe_single()
        .execute()
    )
    if not section.data:
        raise HTTPException(status_code=404, detail="Road section not found")

    row = {
        "organization_id": organization_id,
        "created_by": current_user["id"],
        **payload.model_dump(
            mode="json", exclude={"update_section_condition"}
        ),
    }
    response = supabase.table("road_inspections").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Inspection could not be created")

    if payload.update_section_condition and payload.condition_rating is not None:
        try:
            supabase.table("road_sections").update(
                {"condition_rating": float(payload.condition_rating)}
            ).eq("id", str(payload.road_section_id)).execute()
        except Exception:
            # Inspection is stored even if section update fails.
            pass

    return response.data[0]


@router.patch("/{inspection_id}", response_model=RoadInspection)
def update_inspection(
    inspection_id: UUID,
    payload: RoadInspectionUpdate,
    current_user=Depends(get_current_user),
):
    updates = {
        k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("road_inspections")
        .update(updates)
        .eq("id", str(inspection_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Inspection not found")
    return response.data[0]
