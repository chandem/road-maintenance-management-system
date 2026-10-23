from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.maintenance_proposals import (
    MaintenanceProposal,
    MaintenanceProposalCreate,
    MaintenanceProposalUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/maintenance-proposals", tags=["maintenance-proposals"])
SELECT_COLS = (
    "id,organization_id,maintenance_plan_id,road_section_id,title,work_scope,boq_items,"
    "evidence_notes,status,review_notes,submitted_by,reviewed_by,submitted_at,reviewed_at,"
    "created_by,created_at,updated_at"
)
EDITABLE = ["department_manager", "officer"]
READABLE = ["department_manager", "officer", "read_only"]


def _organization_id(user) -> str:
    value = resolve_organization_id(user["client"], user["id"])
    if not value:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return value


def _verify_links(client, organization_id: str, plan_id: str, section_id: str | None):
    plan = (client.table("maintenance_plans").select("id")
            .eq("id", plan_id).eq("organization_id", organization_id)
            .maybe_single().execute())
    if not plan.data:
        raise HTTPException(status_code=404, detail="Maintenance plan not found in this organization.")
    if section_id:
        section = (client.table("road_sections").select("id")
                   .eq("id", section_id).eq("organization_id", organization_id)
                   .maybe_single().execute())
        if not section.data:
            raise HTTPException(status_code=404, detail="Road section not found in this organization.")


def _total(items) -> float:
    return round(sum(float(item["quantity"]) * float(item["unit_rate"]) for item in items), 2)


@router.get("", response_model=list[MaintenanceProposal])
def list_proposals(
    current_user=Depends(require_department_access("road_asset", READABLE)),
    maintenance_plan_id: UUID | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (current_user["client"].table("maintenance_proposals").select(SELECT_COLS)
             .order("created_at", desc=True).limit(limit))
    if maintenance_plan_id:
        query = query.eq("maintenance_plan_id", str(maintenance_plan_id))
    if status:
        query = query.eq("status", status)
    return query.execute().data or []


@router.post("", response_model=MaintenanceProposal, status_code=201)
def create_proposal(
    payload: MaintenanceProposalCreate,
    current_user=Depends(require_department_access("road_asset", EDITABLE)),
):
    org_id = _organization_id(current_user)
    client = current_user["client"]
    _verify_links(client, org_id, str(payload.maintenance_plan_id),
                  str(payload.road_section_id) if payload.road_section_id else None)
    row = {
        "organization_id": org_id,
        "created_by": current_user["id"],
        "maintenance_plan_id": str(payload.maintenance_plan_id),
        "road_section_id": str(payload.road_section_id) if payload.road_section_id else None,
        "title": payload.title.strip(),
        "work_scope": payload.work_scope.strip(),
        "boq_items": [item.model_dump(mode="json") for item in payload.boq_items],
        "evidence_notes": payload.evidence_notes,
        "status": "draft",
    }
    response = client.table("maintenance_proposals").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Maintenance proposal could not be created.")
    return response.data[0]


@router.patch("/{proposal_id}", response_model=MaintenanceProposal)
def update_proposal(
    proposal_id: UUID,
    payload: MaintenanceProposalUpdate,
    current_user=Depends(require_department_access("road_asset", EDITABLE)),
):
    org_id = _organization_id(current_user)
    client = current_user["client"]
    existing = (client.table("maintenance_proposals").select(SELECT_COLS)
                .eq("id", str(proposal_id)).eq("organization_id", org_id)
                .maybe_single().execute())
    if not existing.data:
        raise HTTPException(status_code=404, detail="Maintenance proposal not found.")
    current = existing.data
    updates = payload.model_dump(mode="json", exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")
    status = updates.get("status")
    allowed_transitions = {
        "draft": {"submitted"},
        "revision_required": {"submitted"},
        "submitted": {"under_review", "approved", "rejected", "revision_required"},
        "under_review": {"under_review", "approved", "rejected", "revision_required"},
        "approved": set(),
        "rejected": set(),
    }
    if status is not None and status not in allowed_transitions[current["status"]]:
        raise HTTPException(status_code=409, detail="Invalid proposal status transition.")
    if current["status"] in ("approved", "rejected") and any(k in updates for k in ("title", "work_scope", "road_section_id", "boq_items", "evidence_notes")):
        raise HTTPException(status_code=409, detail="Finalized proposals cannot be edited. Create a revision instead.")
    if status == "submitted":
        if current["status"] not in ("draft", "revision_required"):
            raise HTTPException(status_code=409, detail="Only drafts or proposals requiring revision can be submitted.")
        updates["submitted_by"] = current_user["id"]
        updates["submitted_at"] = datetime.now(timezone.utc).isoformat()
        updates["review_notes"] = None
    if status in ("under_review", "approved", "rejected", "revision_required"):
        if current["status"] not in ("submitted", "under_review"):
            raise HTTPException(status_code=409, detail="Only submitted proposals can be reviewed.")
        updates["reviewed_by"] = current_user["id"]
        updates["reviewed_at"] = datetime.now(timezone.utc).isoformat()
    section_id = updates.get("road_section_id", current.get("road_section_id"))
    if section_id:
        section = (client.table("road_sections").select("id")
                   .eq("id", str(section_id)).eq("organization_id", org_id)
                   .maybe_single().execute())
        if not section.data:
            raise HTTPException(status_code=404, detail="Road section not found in this organization.")
    if "boq_items" in updates:
        updates["boq_items"] = [item.model_dump(mode="json") for item in payload.boq_items]
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    response = (client.table("maintenance_proposals").update(updates)
                .eq("id", str(proposal_id)).eq("organization_id", org_id).execute())
    if not response.data:
        raise HTTPException(status_code=404, detail="Maintenance proposal not found.")
    return response.data[0]
