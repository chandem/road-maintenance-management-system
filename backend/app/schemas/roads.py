from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Road(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    road_code: str
    name: str
    start_location: str | None = None
    end_location: str | None = None
    total_length_km: Decimal | None = None
    road_class: str | None = None
    surface_type: str | None = None
    status: str
    created_at: datetime
    updated_at: datetime
