from datetime import date, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

AssetType = Literal[
    "bridge", "culvert", "drainage", "sign", "guardrail",
    "retaining_wall", "marker", "lighting", "other",
]
AssetCriticality = Literal["low", "medium", "high", "critical"]
AssetStatus = Literal[
    "active", "needs_inspection", "maintenance_required", "out_of_service", "retired",
]


class RoadAsset(BaseModel):
    id: UUID
    organization_id: UUID
    road_id: UUID
    road_section_id: UUID | None = None
    asset_code: str
    asset_type: AssetType
    name: str
    chainage_km: Decimal | None = None
    latitude: Decimal | None = None
    longitude: Decimal | None = None
    condition_rating: int | None = None
    criticality: AssetCriticality
    status: AssetStatus
    installation_date: date | None = None
    last_inspected_at: date | None = None
    notes: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class RoadAssetCreate(BaseModel):
    road_id: UUID
    road_section_id: UUID | None = None
    asset_code: str = Field(min_length=1, max_length=80)
    asset_type: AssetType
    name: str = Field(min_length=1, max_length=200)
    chainage_km: Decimal | None = Field(default=None, ge=0)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    condition_rating: int | None = Field(default=None, ge=1, le=5)
    criticality: AssetCriticality = "medium"
    status: AssetStatus = "active"
    installation_date: date | None = None
    last_inspected_at: date | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("Latitude and longitude must be provided together.")
        return self


class RoadAssetUpdate(BaseModel):
    road_section_id: UUID | None = None
    asset_type: AssetType | None = None
    name: str | None = Field(default=None, min_length=1, max_length=200)
    chainage_km: Decimal | None = Field(default=None, ge=0)
    latitude: Decimal | None = Field(default=None, ge=-90, le=90)
    longitude: Decimal | None = Field(default=None, ge=-180, le=180)
    condition_rating: int | None = Field(default=None, ge=1, le=5)
    criticality: AssetCriticality | None = None
    status: AssetStatus | None = None
    installation_date: date | None = None
    last_inspected_at: date | None = None
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def coordinate_pair(self):
        if self.latitude is not None and self.longitude is None:
            raise ValueError("Longitude is required when latitude is updated.")
        if self.longitude is not None and self.latitude is None:
            raise ValueError("Latitude is required when longitude is updated.")
        return self
