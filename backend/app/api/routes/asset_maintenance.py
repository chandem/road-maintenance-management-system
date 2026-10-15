from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import require_department_access
from app.schemas.asset_maintenance import (
    AssetMaintenanceCreate,
    AssetMaintenanceOrder,
    AssetMaintenanceUpdate,
    AssetWarranty,
    AssetWarrantyCreate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/asset-maintenance", tags=["asset-maintenance"])

ORDER_COLS = (
    "id,organization_id,asset_id,title,description,maintenance_type,priority,status,"
    "requested_by,assigned_to,scheduled_date,completed_at,cost,vendor,notes,"
    "next_service_date,created_at,updated_at"
)
WARRANTY_COLS = (
    "id,organization_id,asset_id,provider,reference_number,start_date,end_date,"
    "coverage_notes,created_by,created_at,updated_at"
)
READ_ROLES = ["department_manager", "officer", "read_only"]
WRITE_ROLES = ["department_manager", "officer"]


def _org_id(user) -> str:
    organization_id = resolve_organization_id(user["client"], user["id"])
    if not organization_id:
        raise HTTPException(status_code=409, detail="User is not assigned to an organization.")
    return str(organization_id)


def _ensure_asset(client, asset_id: UUID, organization_id: str) -> None:
    asset = (
        client.table("assets").select("id")
        .eq("id", str(asset_id)).eq("organization_id", organization_id)
        .maybe_single().execute()
    )
    if not asset.data:
        raise HTTPException(status_code=404, detail="Asset not found in your organization.")


@router.get("/orders", response_model=list[AssetMaintenanceOrder])
def list_maintenance_orders(
    current_user=Depends(require_department_access("general_assets", READ_ROLES)),
    status: str | None = Query(default=None, max_length=30),
    asset_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    organization_id = _org_id(current_user)
    query = (
        current_user["client"].table("asset_maintenance_orders")
        .select(ORDER_COLS).eq("organization_id", organization_id)
        .order("created_at", desc=True).limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if asset_id:
        query = query.eq("asset_id", str(asset_id))
    return query.execute().data or []


@router.post("/orders", response_model=AssetMaintenanceOrder, status_code=201)
def create_maintenance_order(
    payload: AssetMaintenanceCreate,
    current_user=Depends(require_department_access("general_assets", WRITE_ROLES)),
):
    organization_id = _org_id(current_user)
    client = current_user["client"]
    _ensure_asset(client, payload.asset_id, organization_id)
    row = {
        "organization_id": organization_id,
        "asset_id": str(payload.asset_id),
        "title": payload.title.strip(),
        "description": payload.description.strip() if payload.description else None,
        "maintenance_type": payload.maintenance_type,
        "priority": payload.priority,
        "status": "requested",
        "requested_by": current_user["id"],
        "scheduled_date": payload.scheduled_date.isoformat() if payload.scheduled_date else None,
    }
    result = client.table("asset_maintenance_orders").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Maintenance request could not be created.")
    return result.data[0]


@router.patch("/orders/{order_id}", response_model=AssetMaintenanceOrder)
def update_maintenance_order(
    order_id: UUID,
    payload: AssetMaintenanceUpdate,
    current_user=Depends(require_department_access("general_assets", WRITE_ROLES)),
):
    organization_id = _org_id(current_user)
    client = current_user["client"]
    existing = (
        client.table("asset_maintenance_orders").select(ORDER_COLS)
        .eq("id", str(order_id)).eq("organization_id", organization_id)
        .maybe_single().execute()
    )
    if not existing.data:
        raise HTTPException(status_code=404, detail="Maintenance order not found.")
    current_status = existing.data["status"]
    allowed_transitions = {
        "requested": {"approved", "rejected", "cancelled"},
        "approved": {"in_progress", "cancelled"},
        "in_progress": {"completed", "cancelled"},
        "completed": set(),
        "rejected": set(),
        "cancelled": set(),
    }
    updates = payload.model_dump(exclude_unset=True, mode="json")
    next_status = updates.get("status")
    if next_status is not None and next_status != current_status:
        if next_status not in allowed_transitions.get(current_status, set()):
            raise HTTPException(
                status_code=409,
                detail=f"Invalid maintenance status transition: {current_status} to {next_status}.",
            )
        if next_status == "completed":
            updates["completed_at"] = datetime.now(timezone.utc).isoformat()
    elif next_status == current_status:
        updates.pop("status", None)
    if not updates:
        raise HTTPException(status_code=400, detail="No maintenance fields to update.")
    updates["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("asset_maintenance_orders").update(updates)
        .eq("id", str(order_id)).eq("organization_id", organization_id)
        .eq("status", current_status).execute()
    )
    if not result.data:
        raise HTTPException(status_code=409, detail="Maintenance order changed; refresh and try again.")
    return result.data[0]


@router.get("/warranties", response_model=list[AssetWarranty])
def list_asset_warranties(
    current_user=Depends(require_department_access("general_assets", READ_ROLES)),
    asset_id: UUID | None = None,
    limit: int = Query(default=100, ge=1, le=200),
):
    organization_id = _org_id(current_user)
    query = (
        current_user["client"].table("asset_warranties")
        .select(WARRANTY_COLS).eq("organization_id", organization_id)
        .order("end_date").limit(limit)
    )
    if asset_id:
        query = query.eq("asset_id", str(asset_id))
    return query.execute().data or []


@router.post("/warranties", response_model=AssetWarranty, status_code=201)
def create_asset_warranty(
    payload: AssetWarrantyCreate,
    current_user=Depends(require_department_access("general_assets", WRITE_ROLES)),
):
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="Warranty end date must be on or after its start date.")
    organization_id = _org_id(current_user)
    client = current_user["client"]
    _ensure_asset(client, payload.asset_id, organization_id)
    row = {
        "organization_id": organization_id,
        "asset_id": str(payload.asset_id),
        "provider": payload.provider.strip() if payload.provider else None,
        "reference_number": payload.reference_number.strip() if payload.reference_number else None,
        "start_date": payload.start_date.isoformat(),
        "end_date": payload.end_date.isoformat(),
        "coverage_notes": payload.coverage_notes.strip() if payload.coverage_notes else None,
        "created_by": current_user["id"],
    }
    result = client.table("asset_warranties").insert(row).execute()
    if not result.data:
        raise HTTPException(status_code=500, detail="Warranty record could not be created.")
    return result.data[0]
