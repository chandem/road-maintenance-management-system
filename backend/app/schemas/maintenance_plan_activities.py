from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


ActivityStatus = Literal["planned", "in_progress", "completed", "cancelled"]


class MaintenancePlanActivity(BaseModel):
    id: UUID
    organization_id: UUID
    maintenance_plan_id: UUID
    road_section_id: UUID | None = None
    activity_name: str
    description: str | None = None
    unit: str
    planned_quantity: Decimal
    unit_rate: Decimal
    planned_cost: Decimal
    actual_quantity: Decimal | None = None
    actual_cost: Decimal | None = None
    status: ActivityStatus
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MaintenancePlanActivityCreate(BaseModel):
    maintenance_plan_id: UUID
    road_section_id: UUID | None = None
    activity_name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    unit: str = Field(min_length=1, max_length=40)
    planned_quantity: Decimal = Field(ge=0, max_digits=16, decimal_places=3)
    unit_rate: Decimal = Field(ge=0, max_digits=16, decimal_places=2)
    actual_quantity: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=3)
    actual_cost: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    status: ActivityStatus = "planned"


class MaintenancePlanActivityUpdate(BaseModel):
    road_section_id: UUID | None = None
    activity_name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    unit: str | None = Field(default=None, min_length=1, max_length=40)
    planned_quantity: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=3)
    unit_rate: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=2)
    actual_quantity: Decimal | None = Field(default=None, ge=0, max_digits=16, decimal_places=3)
    actual_cost: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    status: ActivityStatus | None = None
