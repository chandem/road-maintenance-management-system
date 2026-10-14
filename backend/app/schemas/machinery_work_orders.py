from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MachineryWorkOrder(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    machinery_id: UUID
    work_order_no: str
    title: str
    description: str | None = None
    fault_type: str | None = None
    priority: str
    status: str
    reported_at: date
    planned_start: date | None = None
    planned_end: date | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    estimated_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MachineryWorkOrderCreate(BaseModel):
    machinery_id: UUID
    work_order_no: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    fault_type: str | None = Field(default=None, max_length=100)
    priority: str = Field(default="medium", max_length=20)
    status: str = Field(default="reported", max_length=30)
    reported_at: date | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    estimated_cost: Decimal | None = Field(default=None, ge=0)


class MachineryWorkOrderUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)
    fault_type: str | None = Field(default=None, max_length=100)
    priority: str | None = Field(default=None, max_length=20)
    status: str | None = Field(default=None, max_length=30)
    planned_start: date | None = None
    planned_end: date | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    estimated_cost: Decimal | None = Field(default=None, ge=0)
    actual_cost: Decimal | None = Field(default=None, ge=0)


class MachineryWorkOrderSummary(BaseModel):
    total: int
    open_count: int
    completed_count: int
    by_status: dict[str, int]
    by_priority: dict[str, int]
