from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class WorkOrder(BaseModel):
    id: UUID
    organization_id: UUID
    road_section_id: UUID | None = None
    maintenance_plan_id: UUID | None = None
    work_order_no: str
    title: str
    maintenance_type: str | None = None
    priority: str | None = None
    status: str
    planned_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class WorkOrderCreate(BaseModel):
    work_order_no: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    road_section_id: UUID | None = None
    maintenance_plan_id: UUID | None = None
    maintenance_type: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=50)
    status: str = Field(default="planned", max_length=50)
    planned_cost: Decimal | None = Field(default=None, ge=0)
    actual_cost: Decimal | None = Field(default=None, ge=0)
    planned_start: date | None = None
    planned_end: date | None = None
    actual_start: date | None = None
    actual_end: date | None = None


class WorkOrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    road_section_id: UUID | None = None
    maintenance_plan_id: UUID | None = None
    maintenance_type: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=50)
    status: str | None = Field(default=None, max_length=50)
    planned_cost: Decimal | None = Field(default=None, ge=0)
    actual_cost: Decimal | None = Field(default=None, ge=0)
    planned_start: date | None = None
    planned_end: date | None = None
    actual_start: date | None = None
    actual_end: date | None = None
