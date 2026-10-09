from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Road(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    road_code: str
    name: str
    start_location: str | None = None
    end_location: str | None = None
    total_length_km: Decimal | None = None
    road_class: str | None = None
    surface_type: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class RoadCreate(BaseModel):
    road_code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    start_location: str | None = Field(default=None, max_length=255)
    end_location: str | None = Field(default=None, max_length=255)
    total_length_km: Decimal | None = Field(default=None, ge=0)
    road_class: str | None = Field(default=None, max_length=50)
    surface_type: str | None = Field(default=None, max_length=50)
    status: str = Field(default="active", max_length=50)


class RoadUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    start_location: str | None = Field(default=None, max_length=255)
    end_location: str | None = Field(default=None, max_length=255)
    total_length_km: Decimal | None = Field(default=None, ge=0)
    road_class: str | None = Field(default=None, max_length=50)
    surface_type: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)
