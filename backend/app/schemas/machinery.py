from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Machinery(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    asset_code: str
    name: str
    machinery_type: str | None = None
    make: str | None = None
    model: str | None = None
    serial_number: str | None = None
    status: str
    purchase_date: date | None = None
    purchase_cost: Decimal | None = None
    current_hours: Decimal | None = None
    created_at: datetime
    updated_at: datetime


class MachineryCreate(BaseModel):
    asset_code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    machinery_type: str | None = Field(default=None, max_length=100)
    make: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    status: str = Field(default="available", max_length=50)
    purchase_date: date | None = None
    purchase_cost: Decimal | None = Field(default=None, ge=0)
    current_hours: Decimal | None = Field(default=None, ge=0)


class MachineryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    machinery_type: str | None = Field(default=None, max_length=100)
    make: str | None = Field(default=None, max_length=100)
    model: str | None = Field(default=None, max_length=100)
    serial_number: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    purchase_date: date | None = None
    purchase_cost: Decimal | None = Field(default=None, ge=0)
    current_hours: Decimal | None = Field(default=None, ge=0)


class MachinerySummary(BaseModel):
    total: int
    by_status: dict[str, int]
    available_count: int
    down_or_maintenance_count: int
