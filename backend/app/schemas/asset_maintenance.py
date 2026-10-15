from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssetMaintenanceOrder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    asset_id: UUID
    title: str
    description: str | None = None
    maintenance_type: str
    priority: str
    status: str
    requested_by: UUID
    assigned_to: UUID | None = None
    scheduled_date: date | None = None
    completed_at: datetime | None = None
    cost: Decimal
    vendor: str | None = None
    notes: str | None = None
    next_service_date: date | None = None
    created_at: datetime
    updated_at: datetime


class AssetMaintenanceCreate(BaseModel):
    asset_id: UUID
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    maintenance_type: str = Field(default="corrective", pattern="^(preventive|corrective|inspection)$")
    priority: str = Field(default="normal", pattern="^(low|normal|high|urgent)$")
    scheduled_date: date | None = None


class AssetMaintenanceUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(approved|in_progress|completed|rejected|cancelled)$")
    assigned_to: UUID | None = None
    scheduled_date: date | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    vendor: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=4000)
    next_service_date: date | None = None


class AssetWarranty(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    asset_id: UUID
    provider: str | None = None
    reference_number: str | None = None
    start_date: date
    end_date: date
    coverage_notes: str | None = None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class AssetWarrantyCreate(BaseModel):
    asset_id: UUID
    provider: str | None = Field(default=None, max_length=255)
    reference_number: str | None = Field(default=None, max_length=255)
    start_date: date
    end_date: date
    coverage_notes: str | None = Field(default=None, max_length=4000)
