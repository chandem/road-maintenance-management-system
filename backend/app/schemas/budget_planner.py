from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class BudgetPlanCandidateRequest(BaseModel):
    road_section_id: UUID
    estimated_cost: Decimal = Field(ge=0, max_digits=16, decimal_places=2)
    cost_basis: str = Field(min_length=3, max_length=120)


class BudgetPlanRequest(BaseModel):
    budget: Decimal = Field(ge=0, max_digits=16, decimal_places=2)
    candidates: list[BudgetPlanCandidateRequest] = Field(min_length=1, max_length=100)

    @field_validator("candidates")
    @classmethod
    def unique_section_ids(cls, candidates):
        ids = [str(candidate.road_section_id) for candidate in candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("Each road section may appear only once.")
        return candidates


class BudgetPlanItem(BaseModel):
    road_section_id: UUID
    section_code: str | None = None
    road_code: str | None = None
    road_name: str | None = None
    priority_score: Decimal = Field(ge=0, le=100)
    priority_level: str
    confidence: Decimal = Field(ge=0, le=1)
    estimated_cost: Decimal = Field(ge=0)
    cost_basis: str
    reason: str


class BudgetPlanResponse(BaseModel):
    budget: Decimal
    selected: list[BudgetPlanItem]
    deferred: list[BudgetPlanItem]
    selected_total: Decimal
    remaining_budget: Decimal
    method: str
    advisory_only: bool = True
    limitations: list[str]
