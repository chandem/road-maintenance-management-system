from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


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
