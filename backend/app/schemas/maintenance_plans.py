from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


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
