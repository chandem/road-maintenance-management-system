from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel


class WorkOrder(BaseModel):
    id: UUID
    organization_id: UUID
    road_section_id: UUID | None = None
    maintenance_plan_id: UUID | None = None
    work_order_no: str
    title: str
    maintenance_type: str | None = None
    priority: str | None = None
    status: str
    planned_cost: Decimal | None = None
    actual_cost: Decimal | None = None
    planned_start: date | None = None
    planned_end: date | None = None
    actual_start: date | None = None
    actual_end: date | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime
