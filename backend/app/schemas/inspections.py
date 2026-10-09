from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class RoadInspection(BaseModel):
    id: UUID
    organization_id: UUID
    road_section_id: UUID
    inspection_date: date
    inspector_name: str | None = None
    condition_rating: Decimal | None = None
    surface_condition: str | None = None
    defects_summary: str | None = None
    recommended_action: str | None = None
    weather_notes: str | None = None
    status: str
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class RoadInspectionCreate(BaseModel):
    road_section_id: UUID
    inspection_date: date
    inspector_name: str | None = Field(default=None, max_length=255)
    condition_rating: Decimal | None = Field(default=None, ge=0, le=5)
    surface_condition: str | None = Field(default=None, max_length=100)
    defects_summary: str | None = Field(default=None, max_length=5000)
    recommended_action: str | None = Field(default=None, max_length=2000)
    weather_notes: str | None = Field(default=None, max_length=500)
    status: str = Field(default="recorded", max_length=50)
    update_section_condition: bool = True


class RoadInspectionUpdate(BaseModel):
    inspection_date: date | None = None
    inspector_name: str | None = Field(default=None, max_length=255)
    condition_rating: Decimal | None = Field(default=None, ge=0, le=5)
    surface_condition: str | None = Field(default=None, max_length=100)
    defects_summary: str | None = Field(default=None, max_length=5000)
    recommended_action: str | None = Field(default=None, max_length=2000)
    weather_notes: str | None = Field(default=None, max_length=500)
    status: str | None = Field(default=None, max_length=50)
