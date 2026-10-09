from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class MaintenancePlan(BaseModel):
    id: UUID
    organization_id: UUID
    name: str
    fiscal_year: str | None = None
    plan_type: str | None = None
    status: str
    budget_amount: Decimal | None = None
    start_date: date | None = None
    end_date: date | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MaintenancePlanCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    fiscal_year: str | None = Field(default=None, max_length=20)
    plan_type: str | None = Field(default=None, max_length=100)
    status: str = Field(default="draft", max_length=50)
    budget_amount: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None


class MaintenancePlanUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    fiscal_year: str | None = Field(default=None, max_length=20)
    plan_type: str | None = Field(default=None, max_length=100)
    status: str | None = Field(default=None, max_length=50)
    budget_amount: Decimal | None = Field(default=None, ge=0)
    start_date: date | None = None
    end_date: date | None = None
