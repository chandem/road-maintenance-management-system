from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class TrainingRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    employee_id: UUID
    title: str
    record_type: str
    provider: str | None = None
    certificate_no: str | None = None
    completed_on: date | None = None
    expires_on: date | None = None
    status: str
    notes: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class TrainingRecordCreate(BaseModel):
    employee_id: UUID
    title: str = Field(min_length=1, max_length=255)
    record_type: str = Field(default="training", max_length=40)
    provider: str | None = Field(default=None, max_length=255)
    certificate_no: str | None = Field(default=None, max_length=100)
    completed_on: date | None = None
    expires_on: date | None = None
    status: str = Field(default="valid", max_length=30)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def dates_ok(self):
        if self.completed_on and self.expires_on and self.expires_on < self.completed_on:
            raise ValueError("expires_on must be on or after completed_on")
        return self


class TrainingRecordUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    record_type: str | None = Field(default=None, max_length=40)
    provider: str | None = Field(default=None, max_length=255)
    certificate_no: str | None = Field(default=None, max_length=100)
    completed_on: date | None = None
    expires_on: date | None = None
    status: str | None = Field(default=None, max_length=30)
    notes: str | None = Field(default=None, max_length=2000)


class TrainingRecordSummary(BaseModel):
    total: int
    valid_count: int
    expiring_soon_count: int
    expired_count: int
    by_type: dict[str, int]
