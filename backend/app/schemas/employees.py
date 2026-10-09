from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Employee(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    employee_code: str
    full_name: str
    department_id: UUID | None = None
    job_title: str | None = None
    employment_type: str | None = None
    hire_date: date | None = None
    status: str
    phone: str | None = None
    created_at: datetime
    updated_at: datetime


class EmployeeCreate(BaseModel):
    employee_code: str = Field(min_length=1, max_length=50)
    full_name: str = Field(min_length=1, max_length=255)
    department_id: UUID | None = None
    job_title: str | None = Field(default=None, max_length=100)
    employment_type: str | None = Field(default=None, max_length=50)
    hire_date: date | None = None
    status: str = Field(default="active", max_length=50)
    phone: str | None = Field(default=None, max_length=50)


class EmployeeUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    department_id: UUID | None = None
    job_title: str | None = Field(default=None, max_length=100)
    employment_type: str | None = Field(default=None, max_length=50)
    hire_date: date | None = None
    status: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=50)


class EmployeeSummary(BaseModel):
    total: int
    active_count: int
    by_status: dict[str, int]
    by_employment_type: dict[str, int]
