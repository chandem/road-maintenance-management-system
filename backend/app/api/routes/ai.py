from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user
from app.schemas.ai import RoadPriorityRecommendation, RoadPriorityRequest

router = APIRouter(prefix="/ai", tags=["ai"])

def clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("100"), value))

@router.post("/road-priority", response_model=RoadPriorityRecommendation)
def analyze_road_priority(request: RoadPriorityRequest, current_user=Depends(get_current_user)):
    supabase = current_user["client"]
    section = (supabase.table("road_sections")
        .select("id,road_id,section_code,start_chainage_km,end_chainage_km,length_km,condition_rating,status")
        .eq("id", str(request.road_section_id)).maybe_single().execute())
    if not section.data:
        raise HTTPException(status_code=404, detail="Road section not found")
    data = section.data
    reasons: list[str] = []
    evidence: list[str] = []

    rating = data.get("condition_rating")
    if rating is None:
        condition = Decimal("50")
        reasons.append("Condition rating is not available; a neutral score was used.")
    else:
        condition = clamp((Decimal("5") - Decimal(str(rating))) * Decimal("25"))
        reasons.append(f"Recorded condition rating is {rating}.")
    evidence.append(f"Road section status: {data.get('status') or 'not recorded'}.")

    work_orders = (supabase.table("work_orders")
        .select("id,work_order_no,title,priority,status,planned_cost,actual_cost")
        .eq("road_section_id", str(request.road_section_id)).limit(100).execute().data or [])
    open_orders = [w for w in work_orders if (w.get("status") or "").lower() not in {"completed", "closed", "cancelled"}]
    urgent_orders = [w for w in open_orders if (w.get("priority") or "").lower() in {"critical", "high", "urgent"}]
    urgency = Decimal("100") if urgent_orders else Decimal("60") if open_orders else Decimal("0")
    reasons.append(f"{len(open_orders)} active work order(s) are linked to this section.")
    evidence.append(f"Linked work orders: {len(work_orders)}; active: {len(open_orders)}; urgent/high: {len(urgent_orders)}.")

    planning = Decimal("100") if open_orders else Decimal("70") if str(data.get("status") or "").lower() in {"critical", "poor", "failed"} else Decimal("0")
    data_points = sum(1 for value in (rating, data.get("status")) if value is not None) + (1 if work_orders else 0)
    data_quality = Decimal("100") if data_points == 3 else Decimal("70") if data_points == 2 else Decimal("40")
    score = clamp(condition * Decimal("0.50") + urgency * Decimal("0.20") + planning * Decimal("0.10") + data_quality * Decimal("0.05"))
    level = "critical" if score >= 80 else "high" if score >= 60 else "medium" if score >= 40 else "low"
    confidence = Decimal("0.90") if data_points == 3 else Decimal("0.70") if data_points == 2 else Decimal("0.45")
    evidence.append(f"Score components: condition={condition}, urgency={urgency}, planning={planning}, data_quality={data_quality}.")

    return RoadPriorityRecommendation(road_section_id=request.road_section_id, priority_score=score.quantize(Decimal("0.01")), priority_level=level, reasons=reasons, evidence=evidence, confidence=confidence)