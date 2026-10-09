from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Asset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    asset_code: str
    name: str
    category: str | None = None
    location: str | None = None
    status: str
    acquisition_date: date | None = None
    acquisition_cost: Decimal | None = None
    current_value: Decimal | None = None
    assigned_to: UUID | None = None
    created_at: datetime
    updated_at: datetime


class AssetCreate(BaseModel):
    asset_code: str = Field(min_length=1, max_length=100)
    name: str = Field(min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    status: str = Field(default="active", max_length=50)
    acquisition_date: date | None = None
    acquisition_cost: Decimal | None = Field(default=None, ge=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    assigned_to: UUID | None = None


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    category: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=255)
    status: str | None = Field(default=None, max_length=50)
    acquisition_date: date | None = None
    acquisition_cost: Decimal | None = Field(default=None, ge=0)
    current_value: Decimal | None = Field(default=None, ge=0)
    assigned_to: UUID | None = None


class AssetSummary(BaseModel):
    total: int
    active_count: int
    by_status: dict[str, int]
    by_category: dict[str, int]
    total_current_value: Decimal
