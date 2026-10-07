from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Budget(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    fiscal_year: str
    budget_code: str | None = None
    category: str | None = None
    allocated_amount: Decimal
    spent_amount: Decimal
    committed_amount: Decimal
    status: str
    created_at: datetime
    updated_at: datetime


class Expense(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    budget_id: UUID | None = None
    work_order_id: UUID | None = None
    expense_date: date
    description: str
    category: str | None = None
    amount: Decimal
    reference_no: str | None = None
    status: str
    created_by: UUID | None = None
    created_at: datetime
