from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Material(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    material_code: str
    name: str
    category: str | None = None
    unit: str
    quantity_on_hand: Decimal
    reorder_level: Decimal | None = None
    unit_cost: Decimal | None = None
    location: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class MaterialCreate(BaseModel):
    material_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str = Field(default="unit", max_length=30)
    quantity_on_hand: Decimal = Field(default=Decimal("0"), ge=0)
    reorder_level: Decimal | None = Field(default=None, ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=255)
    status: str = Field(default="active", max_length=50)


class MaterialUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    unit: str | None = Field(default=None, max_length=30)
    quantity_on_hand: Decimal | None = Field(default=None, ge=0)
    reorder_level: Decimal | None = Field(default=None, ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    location: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=50)


class MaterialSummary(BaseModel):
    total: int
    active_count: int
    low_stock_count: int
    by_category: dict[str, int]
    estimated_inventory_value: Decimal
