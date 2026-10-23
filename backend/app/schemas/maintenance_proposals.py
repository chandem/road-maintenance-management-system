from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


ProposalStatus = Literal["draft", "submitted", "under_review", "approved", "rejected", "revision_required"]


class BoqItem(BaseModel):
    description: str = Field(min_length=1, max_length=500)
    unit: str = Field(min_length=1, max_length=40)
    quantity: Decimal = Field(gt=0, max_digits=16, decimal_places=3)
    unit_rate: Decimal = Field(ge=0, max_digits=16, decimal_places=2)


class MaintenanceProposal(BaseModel):
    id: UUID
    organization_id: UUID
    maintenance_plan_id: UUID
    road_section_id: UUID | None = None
    title: str
    work_scope: str
    boq_items: list[BoqItem]
    evidence_notes: str | None = None
    status: ProposalStatus
    review_notes: str | None = None
    submitted_by: UUID | None = None
    reviewed_by: UUID | None = None
    submitted_at: datetime | None = None
    reviewed_at: datetime | None = None
    created_by: UUID | None = None
    created_at: datetime
    updated_at: datetime


class MaintenanceProposalCreate(BaseModel):
    maintenance_plan_id: UUID
    road_section_id: UUID | None = None
    title: str = Field(min_length=1, max_length=255)
    work_scope: str = Field(min_length=1, max_length=8000)
    boq_items: list[BoqItem] = Field(min_length=1, max_length=200)
    evidence_notes: str | None = Field(default=None, max_length=8000)


class MaintenanceProposalUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    work_scope: str | None = Field(default=None, min_length=1, max_length=8000)
    road_section_id: UUID | None = None
    boq_items: list[BoqItem] | None = Field(default=None, min_length=1, max_length=200)
    evidence_notes: str | None = Field(default=None, max_length=8000)
    status: ProposalStatus | None = None
    review_notes: str | None = Field(default=None, max_length=8000)

    @model_validator(mode="after")
    def require_review_notes_for_rejection(self):
        if self.status == "rejected" and not (self.review_notes or "").strip():
            raise ValueError("Review notes are required when rejecting a proposal.")
        return self
