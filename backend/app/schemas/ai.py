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