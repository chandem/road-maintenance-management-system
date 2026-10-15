from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class LeaveRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    employee_id: UUID
    leave_type: str
    start_date: date
    end_date: date
    days_requested: Decimal
    status: str
    reason: str | None = None
    decision_notes: str | None = None
    decided_by: UUID | None = None
    decided_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class LeaveRequestCreate(BaseModel):
    employee_id: UUID
    leave_type: str = Field(default="annual", max_length=30)
    start_date: date
    end_date: date
    days_requested: Decimal = Field(default=Decimal("1"), gt=0)
    reason: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def dates_ok(self):
        if self.end_date < self.start_date:
            raise ValueError("end_date must be on or after start_date")
        return self


class LeaveRequestUpdate(BaseModel):
    status: str | None = Field(default=None, max_length=30)
    decision_notes: str | None = Field(default=None, max_length=2000)
    leave_type: str | None = Field(default=None, max_length=30)
    start_date: date | None = None
    end_date: date | None = None
    days_requested: Decimal | None = Field(default=None, gt=0)
    reason: str | None = Field(default=None, max_length=2000)


class LeaveRequestSummary(BaseModel):
    total: int
    pending_count: int
    approved_count: int
    rejected_count: int
    by_type: dict[str, int]
