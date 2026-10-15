from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.asset_transfers import AssetTransfer, AssetTransferCreate, AssetTransferDecision
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/asset-transfers", tags=["asset-transfers"])
SELECT_COLS = (
    "id,organization_id,asset_id,from_location,to_location,from_custodian,"
    "to_custodian,reason,status,requested_by,decided_by,decision_notes,"
    "decided_at,created_at,updated_at"
)


def _org_id(user) -> str:
    organization_id = resolve_organization_id(user["client"], user["id"])
    if not organization_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return str(organization_id)


@router.get("", response_model=list[AssetTransfer])
def list_transfers(
    current_user=Depends(require_department_access("general_assets", ["department_manager", "officer", "read_only"])),
    status: str | None = Query(default=None, max_length=30),
    asset_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    query = (
        current_user["client"].table("asset_transfers").select(SELECT_COLS)
        .order("created_at", desc=True).limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if asset_id:
        query = query.eq("asset_id", str(asset_id))
    return query.execute().data or []


@router.post("", response_model=AssetTransfer, status_code=201)
def create_transfer(
    payload: AssetTransferCreate,
    current_user=Depends(require_department_access("general_assets", ["department_manager", "officer"])),
):
    org_id = _org_id(current_user)
    asset = (
        current_user["client"].table("assets").select("id,organization_id,location,assigned_to")
        .eq("id", str(payload.asset_id)).eq("organization_id", org_id).maybe_single().execute()
    )
    if not asset.data:
        raise HTTPException(status_code=404, detail="Asset not found in your organization.")
    row = {
        "organization_id": org_id,
        "asset_id": str(payload.asset_id),
        "from_location": asset.data.get("location"),
        "from_custodian": asset.data.get("assigned_to"),
        "to_location": payload.to_location.strip(),
        "to_custodian": str(payload.to_custodian) if payload.to_custodian else None,
        "reason": payload.reason.strip(),
        "status": "pending",
        "requested_by": current_user["id"],
    }
    result = current_user["client"].table("asset_transfers").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Transfer request could not be created.")
    return result.data[0]


@router.patch("/{transfer_id}", response_model=AssetTransfer)
def decide_transfer(
    transfer_id: UUID,
    payload: AssetTransferDecision,
    current_user=Depends(require_department_access("general_assets", ["department_manager"])),
):
    if payload.status not in {"approved", "rejected", "cancelled"}:
        raise HTTPException(status_code=422, detail="Decision must be approved, rejected, or cancelled.")
    org_id = _org_id(current_user)
    client = current_user["client"]
    existing = (
        client.table("asset_transfers").select(SELECT_COLS)
        .eq("id", str(transfer_id)).eq("organization_id", org_id).maybe_single().execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Transfer request not found.")
    if existing.data["status"] != "pending":
        raise HTTPException(status_code=409, detail="Only pending transfer requests can be decided.")
    updates = {
        "status": payload.status,
        "decision_notes": payload.decision_notes,
        "decided_by": current_user["id"],
        "decided_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    result = (
        client.table("asset_transfers").update(updates)
        .eq("id", str(transfer_id)).eq("organization_id", org_id).eq("status", "pending").execute()
    )
    if not result.data:
        raise HTTPException(status_code=409, detail="Transfer was already decided; refresh and try again.")
    return result.data[0]
