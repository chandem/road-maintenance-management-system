from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MachineryMaintenanceSchedule(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    machinery_id: UUID
    schedule_code: str
    title: str
    service_type: str | None = None
    interval_hours: Decimal | None = None
    interval_days: int | None = None
    last_service_date: date | None = None
    last_service_hours: Decimal | None = None
    next_due_date: date | None = None
    next_due_hours: Decimal | None = None
    status: str
    notes: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MachineryMaintenanceScheduleCreate(BaseModel):
    machinery_id: UUID
    schedule_code: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    service_type: str | None = Field(default=None, max_length=100)
    interval_hours: Decimal | None = Field(default=None, gt=0)
    interval_days: int | None = Field(default=None, gt=0)
    last_service_date: date | None = None
    last_service_hours: Decimal | None = Field(default=None, ge=0)
    next_due_date: date | None = None
    next_due_hours: Decimal | None = Field(default=None, ge=0)
    status: str = Field(default="active", max_length=30)
    notes: str | None = Field(default=None, max_length=4000)

    @model_validator(mode="after")
    def require_interval(self):
        if self.interval_hours is None and self.interval_days is None:
            raise ValueError("Provide interval_hours and/or interval_days")
        return self


class MachineryMaintenanceScheduleUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    service_type: str | None = Field(default=None, max_length=100)
    interval_hours: Decimal | None = Field(default=None, gt=0)
    interval_days: int | None = Field(default=None, gt=0)
    last_service_date: date | None = None
    last_service_hours: Decimal | None = Field(default=None, ge=0)
    next_due_date: date | None = None
    next_due_hours: Decimal | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=4000)


class MachineryMaintenanceScheduleSummary(BaseModel):
    total: int
    active_count: int
    due_soon_count: int
    by_status: dict[str, int]
