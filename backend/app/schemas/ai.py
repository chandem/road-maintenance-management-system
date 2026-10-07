from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class RoadPriorityRequest(BaseModel):
    road_section_id: UUID


class RoadPriorityRecommendation(BaseModel):
    road_section_id: UUID
    priority_score: Decimal = Field(ge=0, le=100)
    priority_level: str
    reasons: list[str]
    evidence: list[str]
    confidence: Decimal = Field(ge=0, le=1)
    explanation: str
    recommended_action: str


class RoadRankingRequest(BaseModel):
    limit: int = Field(default=10, ge=1, le=100)


class RoadRankingItem(BaseModel):
    rank: int
    road_section_id: UUID
    section_code: str | None
    priority_score: Decimal = Field(ge=0, le=100)
    priority_level: str
    condition_rating: int | None
    status: str | None
    active_work_orders: int
    urgent_work_orders: int
    confidence: Decimal = Field(ge=0, le=1)
    explanation: str | None = None
    recommended_action: str | None = None


class RoadRankingResponse(BaseModel):
    total_sections_analyzed: int
    rankings: list[RoadRankingItem]
    methodology: str
    ai_generated: bool = False
