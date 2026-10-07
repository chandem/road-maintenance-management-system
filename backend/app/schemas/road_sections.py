from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class RoadSection(BaseModel):
    id: UUID
    organization_id: UUID
    road_id: UUID
    section_code: str
    start_chainage_km: Decimal
    end_chainage_km: Decimal
    length_km: Decimal | None = None
    condition_rating: Decimal | None = None
    status: str
    created_at: datetime
    updated_at: datetime
