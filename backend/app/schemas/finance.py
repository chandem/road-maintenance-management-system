from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


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


class BudgetCreate(BaseModel):
    fiscal_year: str = Field(min_length=4, max_length=20)
    budget_code: str | None = Field(default=None, max_length=50)
    category: str | None = Field(default=None, max_length=100)
    allocated_amount: Decimal = Field(default=Decimal("0"), ge=0)
    spent_amount: Decimal = Field(default=Decimal("0"), ge=0)
    committed_amount: Decimal = Field(default=Decimal("0"), ge=0)
    status: str = Field(default="active", max_length=50)


class BudgetUpdate(BaseModel):
    budget_code: str | None = Field(default=None, max_length=50)
    category: str | None = Field(default=None, max_length=100)
    allocated_amount: Decimal | None = Field(default=None, ge=0)
    spent_amount: Decimal | None = Field(default=None, ge=0)
    committed_amount: Decimal | None = Field(default=None, ge=0)
    status: str | None = Field(default=None, max_length=50)


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


class ExpenseCreate(BaseModel):
    expense_date: date
    description: str = Field(min_length=1, max_length=500)
    amount: Decimal = Field(gt=0)
    budget_id: UUID | None = None
    work_order_id: UUID | None = None
    category: str | None = Field(default=None, max_length=100)
    reference_no: str | None = Field(default=None, max_length=100)
    status: str = Field(default="recorded", max_length=50)


class FinanceSummary(BaseModel):
    budget_count: int
    expense_count: int
    total_allocated: Decimal
    total_spent: Decimal
    total_committed: Decimal
    remaining: Decimal
    utilization_percent: float
