from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PaymentRequest(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    budget_id: UUID | None = None
    request_no: str
    title: str
    payee: str | None = None
    amount: Decimal
    currency: str
    status: str
    requested_on: date
    due_date: date | None = None
    notes: str | None = None
    decided_by: UUID | None = None
    decided_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class PaymentRequestCreate(BaseModel):
    request_no: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=255)
    payee: str | None = Field(default=None, max_length=255)
    amount: Decimal = Field(gt=0)
    currency: str = Field(default="ETB", max_length=10)
    budget_id: UUID | None = None
    status: str = Field(default="draft", max_length=30)
    requested_on: date | None = None
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class PaymentRequestUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    payee: str | None = Field(default=None, max_length=255)
    amount: Decimal | None = Field(default=None, gt=0)
    status: str | None = Field(default=None, max_length=30)
    due_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)
    budget_id: UUID | None = None
