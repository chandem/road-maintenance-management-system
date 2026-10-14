from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MachineryFuelLog(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    machinery_id: UUID
    log_date: date
    fuel_quantity: Decimal | None = None
    fuel_unit: str
    meter_hours: Decimal | None = None
    unit_cost: Decimal | None = None
    total_cost: Decimal | None = None
    notes: str | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MachineryFuelLogCreate(BaseModel):
    machinery_id: UUID
    log_date: date | None = None
    fuel_quantity: Decimal | None = Field(default=None, ge=0)
    fuel_unit: str = Field(default="litre", max_length=20)
    meter_hours: Decimal | None = Field(default=None, ge=0)
    unit_cost: Decimal | None = Field(default=None, ge=0)
    total_cost: Decimal | None = Field(default=None, ge=0)
    notes: str | None = Field(default=None, max_length=2000)
    update_machinery_hours: bool = False

    @model_validator(mode="after")
    def require_fuel_or_hours(self):
        if self.fuel_quantity is None and self.meter_hours is None:
            raise ValueError("Provide fuel_quantity and/or meter_hours")
        return self


class MachineryFuelLogSummary(BaseModel):
    total_logs: int
    total_fuel_quantity: Decimal
    total_cost: Decimal
    logs_with_meter: int
