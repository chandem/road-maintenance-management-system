from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class AssetTransfer(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    organization_id: UUID
    asset_id: UUID
    from_location: str | None = None
    to_location: str
    from_custodian: UUID | None = None
    to_custodian: UUID | None = None
    reason: str
    status: str
    requested_by: UUID
    decided_by: UUID | None = None
    decision_notes: str | None = None
    decided_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class AssetTransferCreate(BaseModel):
    asset_id: UUID
    to_location: str = Field(min_length=1, max_length=255)
    to_custodian: UUID | None = None
    reason: str = Field(min_length=1, max_length=2000)


class AssetTransferDecision(BaseModel):
    status: str
    decision_notes: str | None = Field(default=None, max_length=2000)
