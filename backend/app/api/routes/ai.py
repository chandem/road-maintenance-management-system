import json
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException
from openai import OpenAI

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.schemas.ai import (
    RoadPriorityRecommendation,
    RoadPriorityRequest,
    RoadRankingItem,
    RoadRankingRequest,
    RoadRankingResponse,
)

router = APIRouter(prefix="/ai", tags=["ai"])


def clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("100"), value))


def calculate_priority(
    data: dict, work_orders: list[dict]
) -> tuple[Decimal, str, Decimal, list[str], list[str]]:
    reasons: list[str] = []
    evidence: list[str] = []

    rating = data.get("condition_rating")
    if rating is None:
        condition = Decimal("50")
        reasons.append("Condition rating is not available; a neutral score was used.")
    else:
        condition = clamp((Decimal("5") - Decimal(str(rating))) * Decimal("25"))
        reasons.append(f"Recorded condition rating is {rating}.")

    evidence.append(
        f"Road section status: {data.get('status') or 'not recorded'}."
    )

    open_orders = [
        w
        for w in work_orders
        if (w.get("status") or "").lower()
        not in {"completed", "closed", "cancelled"}
    ]
    urgent_orders = [
        w
        for w in open_orders
        if (w.get("priority") or "").lower() in {"critical", "high", "urgent"}
    ]

    urgency = (
        Decimal("100")
        if urgent_orders
        else Decimal("60")
        if open_orders
        else Decimal("0")
    )

    reasons.append(f"{len(open_orders)} active work order(s) are linked to this section.")
    evidence.append(
        f"Linked work orders: {len(work_orders)}; active: {len(open_orders)}; "
        f"urgent/high: {len(urgent_orders)}."
    )

    planning = (
        Decimal("100")
        if open_orders
        else Decimal("70")
        if str(data.get("status") or "").lower()
        in {"critical", "poor", "failed"}
        else Decimal("0")
    )

    data_points = sum(
        1 for value in (rating, data.get("status")) if value is not None
    ) + (1 if work_orders else 0)

    data_quality = (
        Decimal("100")
        if data_points == 3
        else Decimal("70")
        if data_points == 2
        else Decimal("40")
    )

    raw_score = (
        condition * Decimal("0.50")
        + urgency * Decimal("0.20")
        + planning * Decimal("0.10")
        + data_quality * Decimal("0.05")
    )

    # The four components above total 85%, so normalize to a 0-100 score.
    score = clamp(raw_score / Decimal("0.85"))

    level = (
        "critical"
        if score >= 80
        else "high"
        if score >= 60
        else "medium"
        if score >= 40
        else "low"
    )

    confidence = (
        Decimal("0.90")
        if data_points == 3
        else Decimal("0.70")
        if data_points == 2
        else Decimal("0.45")
    )

    evidence.append(
        f"Score components: condition={condition}, urgency={urgency}, "
        f"planning={planning}, data_quality={data_quality}."
    )

    return (
        score.quantize(Decimal("0.01")),
        level,
        confidence,
        reasons,
        evidence,
    )


def baseline_action(level: str) -> str:
    return {
        "critical": "Prioritize field verification and maintenance action.",
        "high": "Schedule field verification and include in near-term maintenance planning.",
        "medium": "Monitor the section and address it through planned maintenance.",
        "low": "Continue routine monitoring and update condition data when available.",
    }[level]


def generate_ai_explanation(
    data: dict,
    score: Decimal,
    level: str,
    evidence: list[str],
    recommended_action: str,
) -> str | None:
    settings = get_settings()
    if not settings.openai_api_key:
        return None

    client = OpenAI(api_key=settings.openai_api_key)
    prompt = (
        f"Road section: {data.get('section_code') or 'not recorded'}\n"
        f"Priority score: {score}/100\n"
        f"Priority level: {level}\n"
        f"Evidence:\n- "
        + "\n- ".join(evidence)
        + f"\nBaseline action: {recommended_action}\n\n"
        "Explain using only these facts. Do not invent causes, costs, dates, "
        "measurements, traffic data, or site observations. Do not change the "
        "score or priority level. Return one concise engineering-office explanation."
    )

    try:
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": "You are an AI road-maintenance analyst.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        return response.output_text.strip() or None
    except Exception:
        return None


def generate_ranking_ai_explanations(
    rankings: list[RoadRankingItem],
) -> dict[str, dict[str, str]]:
    settings = get_settings()
    if not settings.openai_api_key or not rankings:
        return {}

    payload = [
        {
            "road_section_id": str(item.road_section_id),
            "rank": item.rank,
            "section_code": item.section_code,
            "priority_score": float(item.priority_score),
            "priority_level": item.priority_level,
            "condition_rating": item.condition_rating,
            "status": item.status,
            "active_work_orders": item.active_work_orders,
            "urgent_work_orders": item.urgent_work_orders,
            "confidence": float(item.confidence),
        }
        for item in rankings
    ]

    prompt = (
        "Analyze these deterministic road-maintenance rankings. The numeric "
        "score, rank, level, and confidence are authoritative and MUST NOT be changed. "
        "Use only the supplied facts. Do not invent causes, costs, dates, traffic "
        "conditions, measurements, or site observations. For every road section, "
        "return a concise explanation and a practical recommended action. "
        "The action must be advisory and must not authorize expenditure or a contract. "
        "Return ONLY valid JSON as an array with objects containing "
        "road_section_id, explanation, and recommended_action.\n\n"
        + json.dumps(payload, default=str)
    )

    try:
        client = OpenAI(api_key=settings.openai_api_key)
        response = client.responses.create(
            model=settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": "You are an AI road-maintenance planning assistant.",
                },
                {"role": "user", "content": prompt},
            ],
        )
        raw = response.output_text.strip()
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return {}

        result: dict[str, dict[str, str]] = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            section_id = str(item.get("road_section_id", "")).strip()
            explanation = str(item.get("explanation", "")).strip()
            action = str(item.get("recommended_action", "")).strip()
            if section_id and explanation and action:
                result[section_id] = {
                    "explanation": explanation,
                    "recommended_action": action,
                }
        return result
    except Exception:
        return {}


@router.post("/road-priority", response_model=RoadPriorityRecommendation)
def analyze_road_priority(
    request: RoadPriorityRequest,
    current_user=Depends(get_current_user),
):
    supabase = current_user["client"]
    section = (
        supabase.table("road_sections")
        .select(
            "id,road_id,section_code,start_chainage_km,end_chainage_km,"
            "length_km,condition_rating,status"
        )
        .eq("id", str(request.road_section_id))
        .maybe_single()
        .execute()
    )

    if not section.data:
        raise HTTPException(status_code=404, detail="Road section not found")

    data = section.data
    work_orders = (
        supabase.table("work_orders")
        .select("id,work_order_no,title,priority,status,planned_cost,actual_cost")
        .eq("road_section_id", str(request.road_section_id))
        .limit(100)
        .execute()
        .data
        or []
    )

    score, level, confidence, reasons, evidence = calculate_priority(
        data, work_orders
    )
    action = baseline_action(level)

    explanation = (
        generate_ai_explanation(data, score, level, evidence, action)
        or f"Section {data.get('section_code') or request.road_section_id} "
        f"has a {level} maintenance priority with a score of {score}/100, "
        "based on the recorded evidence."
    )

    return RoadPriorityRecommendation(
        road_section_id=request.road_section_id,
        priority_score=score,
        priority_level=level,
        reasons=reasons,
        evidence=evidence,
        confidence=confidence,
        explanation=explanation,
        recommended_action=action,
    )


@router.post("/road-ranking", response_model=RoadRankingResponse)
def rank_road_sections(
    request: RoadRankingRequest,
    current_user=Depends(get_current_user),
):
    supabase = current_user["client"]

    sections = (
        supabase.table("road_sections")
        .select(
            "id,road_id,section_code,start_chainage_km,end_chainage_km,"
            "length_km,condition_rating,status"
        )
        .limit(1000)
        .execute()
        .data
        or []
    )

    if not sections:
        return RoadRankingResponse(
            total_sections_analyzed=0,
            rankings=[],
            methodology="No road sections were available to analyze.",
        )

    rows = []

    for section in sections:
        orders = (
            supabase.table("work_orders")
            .select("id,priority,status")
            .eq("road_section_id", str(section["id"]))
            .limit(100)
            .execute()
            .data
            or []
        )

        score, level, confidence, _, _ = calculate_priority(section, orders)

        active = [
            w
            for w in orders
            if (w.get("status") or "").lower()
            not in {"completed", "closed", "cancelled"}
        ]
        urgent = [
            w
            for w in active
            if (w.get("priority") or "").lower() in {"critical", "high", "urgent"}
        ]

        rows.append(
            RoadRankingItem(
                rank=0,
                road_section_id=section["id"],
                section_code=section.get("section_code"),
                priority_score=score,
                priority_level=level,
                condition_rating=section.get("condition_rating"),
                status=section.get("status"),
                active_work_orders=len(active),
                urgent_work_orders=len(urgent),
                confidence=confidence,
            )
        )

    rows.sort(
        key=lambda item: (
            -item.priority_score,
            -item.confidence,
            item.section_code or "",
        )
    )

    rankings = [
        item.model_copy(update={"rank": index})
        for index, item in enumerate(rows[: request.limit], start=1)
    ]

    ai_explanations = generate_ranking_ai_explanations(rankings)
    ai_generated = bool(ai_explanations)

    enriched_rankings = []
    for item in rankings:
        ai_item = ai_explanations.get(str(item.road_section_id))
        if ai_item:
            enriched_rankings.append(
                item.model_copy(
                    update={
                        "explanation": ai_item["explanation"],
                        "recommended_action": ai_item["recommended_action"],
                    }
                )
            )
        else:
            action = baseline_action(item.priority_level)
            enriched_rankings.append(
                item.model_copy(
                    update={
                        "explanation": (
                            f"Section {item.section_code or item.road_section_id} "
                            f"has a {item.priority_level} priority with a score of "
                            f"{item.priority_score}/100 based on recorded condition "
                            "and maintenance-work-order signals."
                        ),
                        "recommended_action": action,
                    }
                )
            )

    return RoadRankingResponse(
        total_sections_analyzed=len(rows),
        rankings=enriched_rankings,
        methodology=(
            "Sections are ranked using deterministic condition, work-order urgency, "
            "planning, and data-quality signals. The resulting score and rank are "
            "authoritative; AI only explains the verified evidence and suggests "
            "advisory next actions."
        ),
        ai_generated=ai_generated,
    )
