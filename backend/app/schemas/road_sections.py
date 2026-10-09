from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class RoadSection(BaseModel):
    id: UUID
    organization_id: UUID
    road_id: UUID
    section_code: str
    start_chainage_km: Decimal
    end_chainage_km: Decimal
    length_km: Decimal | None = None
    condition_rating: Decimal | None = None
    status: str
    created_at: datetime
    updated_at: datetime


class RoadSectionCreate(BaseModel):
    road_id: UUID
    section_code: str = Field(min_length=1, max_length=50)
    start_chainage_km: Decimal = Field(ge=0)
    end_chainage_km: Decimal = Field(ge=0)
    length_km: Decimal | None = Field(default=None, ge=0)
    condition_rating: Decimal | None = Field(default=None, ge=0, le=5)
    status: str = Field(default="active", max_length=50)

    @model_validator(mode="after")
    def chainage_order(self):
        if self.end_chainage_km < self.start_chainage_km:
            raise ValueError("end_chainage_km must be >= start_chainage_km")
        return self


class RoadSectionUpdate(BaseModel):
    section_code: str | None = Field(default=None, min_length=1, max_length=50)
    start_chainage_km: Decimal | None = Field(default=None, ge=0)
    end_chainage_km: Decimal | None = Field(default=None, ge=0)
    length_km: Decimal | None = Field(default=None, ge=0)
    condition_rating: Decimal | None = Field(default=None, ge=0, le=5)
    status: str | None = Field(default=None, max_length=50)
