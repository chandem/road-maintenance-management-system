from collections import Counter
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.schemas.materials import (
    Material,
    MaterialCreate,
    MaterialSummary,
    MaterialUpdate,
)
from app.services.ai_audit import resolve_organization_id

router = APIRouter(prefix="/materials", tags=["materials"])

SELECT_COLS = (
    "id,organization_id,material_code,name,category,unit,quantity_on_hand,"
    "reorder_level,unit_cost,location,status,created_at,updated_at"
)


def _org_id(current_user) -> str:
    org_id = resolve_organization_id(current_user["client"], current_user["id"])
    if not org_id:
        raise HTTPException(
            status_code=409, detail="User is not assigned to an organization."
        )
    return org_id


@router.get("", response_model=list[Material])
def list_materials(
    current_user=Depends(get_current_user),
    limit: int = Query(default=100, ge=1, le=200),
    status: str | None = Query(default=None, max_length=50),
    category: str | None = Query(default=None, max_length=100),
):
    """List materials inventory for the organization."""
    query = (
        current_user["client"]
        .table("materials")
        .select(SELECT_COLS)
        .order("name")
        .limit(limit)
    )
    if status:
        query = query.eq("status", status)
    if category:
        query = query.eq("category", category)
    return query.execute().data or []


@router.get("/summary", response_model=MaterialSummary)
def materials_summary(current_user=Depends(get_current_user)):
    """Inventory health: active items, low stock, value by category."""
    rows = (
        current_user["client"]
        .table("materials")
        .select("status,category,quantity_on_hand,reorder_level,unit_cost")
        .limit(2000)
        .execute()
        .data
        or []
    )
    by_category = Counter((r.get("category") or "unspecified").lower() for r in rows)
    active = sum(1 for r in rows if (r.get("status") or "").lower() == "active")
    low_stock = 0
    value = Decimal("0")
    for row in rows:
        qty = Decimal(str(row.get("quantity_on_hand") or 0))
        cost = Decimal(str(row.get("unit_cost") or 0))
        value += qty * cost
        reorder = row.get("reorder_level")
        if reorder is not None and qty <= Decimal(str(reorder)):
            low_stock += 1
    return MaterialSummary(
        total=len(rows),
        active_count=active,
        low_stock_count=low_stock,
        by_category=dict(by_category),
        estimated_inventory_value=value,
    )


@router.get("/{material_id}", response_model=Material)
def get_material(material_id: UUID, current_user=Depends(get_current_user)):
    response = (
        current_user["client"]
        .table("materials")
        .select(SELECT_COLS)
        .eq("id", str(material_id))
        .maybe_single()
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Material not found")
    return response.data


@router.post("", response_model=Material, status_code=201)
def create_material(
    payload: MaterialCreate,
    current_user=Depends(get_current_user),
):
    organization_id = _org_id(current_user)
    row = {"organization_id": organization_id, **payload.model_dump(mode="json")}
    response = current_user["client"].table("materials").insert(row).execute()
    if not response.data:
        raise HTTPException(status_code=500, detail="Material could not be created")
    return response.data[0]


@router.patch("/{material_id}", response_model=Material)
def update_material(
    material_id: UUID,
    payload: MaterialUpdate,
    current_user=Depends(get_current_user),
):
    updates = {
        k: v for k, v in payload.model_dump(mode="json", exclude_unset=True).items()
    }
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    response = (
        current_user["client"]
        .table("materials")
        .update(updates)
        .eq("id", str(material_id))
        .execute()
    )
    if not response.data:
        raise HTTPException(status_code=404, detail="Material not found")
    return response.data[0]
