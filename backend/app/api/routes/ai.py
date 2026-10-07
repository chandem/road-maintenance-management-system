from decimal import Decimal
import json
from urllib.request import Request, urlopen

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.schemas.ai import RoadPriorityRecommendation, RoadPriorityRequest

router = APIRouter(prefix="/ai", tags=["ai"])

def clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("100"), value))

def generate_ai_explanation(data: dict, score: Decimal, level: str, evidence: list[str], recommended_action: str) -> str | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None
    prompt = {"section": data.get("section_code"), "priority_score": float(score), "priority_level": level, "evidence": evidence, "baseline_action": recommended_action}
    payload = {"model": settings.openai_model, "input": [{"role": "system", "content": "You are an AI road-maintenance analyst. Explain only the supplied evidence. Do not invent missing facts, costs, dates, measurements, or causes. Keep the explanation concise and suitable for an engineering office decision. State uncertainty when evidence is incomplete."}, {"role": "user", "content": json.dumps(prompt)}]}
    request = Request("https://api.openai.com/v1/responses", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            result = json.loads(response.read().decode())
        return result.get("output_text")
    except Exception:
        return None

@router.post("/road-priority", response_model=RoadPriorityRecommendation)
def analyze_road_priority(request: RoadPriorityRequest, current_user=Depends(get_current_user)):
    supabase = current_user["client"]
    section = (supabase.table("road_sections").select("id,road_id,section_code,start_chainage_km,end_chainage_km,length_km,condition_rating,status").eq("id", str(request.road_section_id)).maybe_single().execute())
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
    work_orders = (supabase.table("work_orders").select("id,work_order_no,title,priority,status,planned_cost,actual_cost").eq("road_section_id", str(request.road_section_id)).limit(100).execute().data or [])
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
    baseline = {"critical": "Prioritize field verification and maintenance action.", "high": "Schedule field verification and include in near-term maintenance planning.", "medium": "Monitor the section and address it through planned maintenance.", "low": "Continue routine monitoring and update condition data when available."}[level]
    explanation = generate_ai_explanation(data, score, level, evidence, baseline) or f"Section {data.get('section_code') or request.road_section_id} has a {level} maintenance priority with a score of {score.quantize(Decimal('0.01'))}/100, based on the recorded evidence."
    return RoadPriorityRecommendation(road_section_id=request.road_section_id, priority_score=score.quantize(Decimal("0.01")), priority_level=level, reasons=reasons, evidence=evidence, confidence=confidence, explanation=explanation, recommended_action=baseline)
