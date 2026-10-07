from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Asset(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    asset_code: str
    name: str
    category: str | None = None
    location: str | None = None
    status: str
    acquisition_date: date | None = None
    acquisition_cost: Decimal | None = None
    current_value: Decimal | None = None
    assigned_to: UUID | None = None
    created_at: datetime
    updated_at: datetime
