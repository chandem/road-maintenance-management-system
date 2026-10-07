from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Machinery(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    asset_code: str
    name: str
    machinery_type: str | None = None
    make: str | None = None
    model: str | None = None
    serial_number: str | None = None
    status: str
    purchase_date: date | None = None
    purchase_cost: Decimal | None = None
    current_hours: Decimal | None = None
    created_at: datetime
    updated_at: datetime
