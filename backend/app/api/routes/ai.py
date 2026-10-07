from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user
from app.schemas.ai import RoadPriorityRecommendation, RoadPriorityRequest

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/road-priority", response_model=RoadPriorityRecommendation)
def analyze_road_priority(
    request: RoadPriorityRequest,
    current_user=Depends(get_current_user),
):
    supabase = current_user["client"]
    section = (
        supabase.table("road_sections")
        .select("id,road_id,section_code,start_chainage_km,end_chainage_km,length_km,condition_rating,status")
        .eq("id", str(request.road_section_id))
        .maybe_single()
        .execute()
    )

    if not section.data:
        raise HTTPException(status_code=404, detail="Road section not found")

    data = section.data
    rating = data.get("condition_rating")
    reasons: list[str] = []
    evidence: list[str] = []

    if rating is None:
        score = Decimal("50")
        reasons.append("Condition rating is not available; a neutral score was assigned.")
        evidence.append("No condition rating recorded for this road section.")
        confidence = Decimal("0.30")
    else:
        rating_value = Decimal(str(rating))
        score = max(Decimal("0"), min(Decimal("100"), Decimal("100") - rating_value * Decimal("20")))
        reasons.append(f"Condition rating is {rating_value}.")
        evidence.append(f"Recorded condition rating: {rating_value}.")
        confidence = Decimal("0.80")

    if score >= 75:
        level = "high"
    elif score >= 50:
        level = "medium"
    else:
        level = "low"

    return RoadPriorityRecommendation(
        road_section_id=request.road_section_id,
        priority_score=score,
        priority_level=level,
        reasons=reasons,
        evidence=evidence,
        confidence=confidence,
    )
