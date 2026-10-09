import json
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.dependencies import get_current_user
from app.core.config import get_settings
from app.schemas.ai import (
    RoadPriorityRecommendation,
    RoadPriorityRequest,
    RoadRankingItem,
    RoadRankingResponse,
)
from app.schemas.office_assistant import OfficeAssistantRequest, OfficeAssistantResponse
from app.services.ai_audit import log_analysis_run, resolve_organization_id
from app.services.ai_provider import generate_text
from app.services.road_priority import (
    PriorityResult,
    baseline_action,
    calculate_priority as score_road_section,
)
from app.services.semantic_search import search_document_chunks

router = APIRouter(prefix="/ai", tags=["ai"])


def calculate_priority(
    data: dict, work_orders: list[dict]
) -> tuple[Decimal, str, Decimal, list[str], list[str]]:
    """Compatibility wrapper for existing unit tests."""
    result = score_road_section(data, work_orders)
    return (
        result.score,
        result.level,
        result.confidence,
        result.reasons,
        result.evidence,
    )


def generate_ai_explanation(
    data: dict,
    score: Decimal,
    level: str,
    evidence: list[str],
    recommended_action: str,
) -> str | None:
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
    result = generate_text(
        prompt,
        system_instruction="You are an AI road-maintenance analyst.",
    )
    return result.text if result else None


def generate_ranking_ai_explanations(
    rankings: list[RoadRankingItem],
) -> dict[str, dict[str, str]]:
    if not rankings:
        return {}

    payload = [
        {
            "road_section_id": str(item.road_section_id),
            "rank": item.rank,
            "section_code": item.section_code,
            "road_code": item.road_code,
            "road_name": item.road_name,
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

    result = generate_text(
        prompt,
        system_instruction="You are an AI road-maintenance planning assistant.",
    )
    if not result:
        return {}

    try:
        parsed = json.loads(result.text)
        if not isinstance(parsed, list):
            return {}
        out: dict[str, dict[str, str]] = {}
        for item in parsed:
            if not isinstance(item, dict):
                continue
            section_id = str(item.get("road_section_id", "")).strip()
            explanation = str(item.get("explanation", "")).strip()
            action = str(item.get("recommended_action", "")).strip()
            if section_id and explanation and action:
                out[section_id] = {
                    "explanation": explanation,
                    "recommended_action": action,
                }
        return out
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

    plans = (
        supabase.table("maintenance_plans")
        .select("id,name,status,fiscal_year")
        .limit(50)
        .execute()
        .data
        or []
    )

    priority = score_road_section(data, work_orders, related_plans=plans)
    action = baseline_action(priority.level)

    road_meta = {"road_code": None, "road_name": None}
    road_id = data.get("road_id")
    if road_id:
        road = (
            supabase.table("roads")
            .select("id,road_code,name")
            .eq("id", str(road_id))
            .maybe_single()
            .execute()
        )
        if road.data:
            road_meta["road_code"] = road.data.get("road_code")
            road_meta["road_name"] = road.data.get("name")

    document_evidence: list[str] = []
    if request.include_document_evidence:
        try:
            org_id = resolve_organization_id(supabase, current_user["id"])
            query_bits = [
                data.get("section_code") or "",
                road_meta.get("road_name") or "",
                road_meta.get("road_code") or "",
                "maintenance",
            ]
            query = " ".join(bit for bit in query_bits if bit).strip() or "road maintenance"
            if org_id and current_user.get("access_token"):
                matches = search_document_chunks(
                    query,
                    organization_id=org_id,
                    access_token=current_user["access_token"],
                    limit=3,
                    minimum_similarity=0.35,
                )
                document_evidence = [
                    f"{match.content[:240].strip()} (similarity {match.similarity:.2f})"
                    for match in matches
                ]
                if document_evidence:
                    evidence_list = list(priority.evidence) + [
                        f"Related document snippets retrieved: {len(document_evidence)}."
                    ]
                    priority = PriorityResult(
                        score=priority.score,
                        level=priority.level,
                        confidence=priority.confidence,
                        reasons=list(priority.reasons),
                        evidence=evidence_list,
                        active_work_orders=priority.active_work_orders,
                        urgent_work_orders=priority.urgent_work_orders,
                    )
        except Exception:
            document_evidence = []

    explanation = (
        generate_ai_explanation(
            data, priority.score, priority.level, priority.evidence, action
        )
        or f"Section {data.get('section_code') or request.road_section_id} "
        f"has a {priority.level} maintenance priority with a score of "
        f"{priority.score}/100, based on the recorded evidence."
    )

    recommendation = RoadPriorityRecommendation(
        road_section_id=request.road_section_id,
        section_code=data.get("section_code"),
        road_id=UUID(str(road_id)) if road_id else None,
        road_code=road_meta["road_code"],
        road_name=road_meta["road_name"],
        priority_score=priority.score,
        priority_level=priority.level,
        reasons=priority.reasons,
        evidence=priority.evidence,
        document_evidence=document_evidence,
        confidence=priority.confidence,
        explanation=explanation,
        recommended_action=action,
    )

    org_id = resolve_organization_id(supabase, current_user["id"])
    if org_id:
        log_analysis_run(
            supabase,
            organization_id=org_id,
            analysis_type="road_priority",
            entity_type="road_section",
            entity_id=str(request.road_section_id),
            status="completed",
            confidence=float(priority.confidence),
            result={
                "priority_score": float(priority.score),
                "priority_level": priority.level,
                "recommended_action": action,
            },
            evidence={
                "reasons": priority.reasons,
                "evidence": priority.evidence,
                "document_evidence": document_evidence,
            },
            created_by=current_user["id"],
        )

    return recommendation


@router.get("/road-ranking", response_model=RoadRankingResponse)
def rank_road_sections(
    limit: int = Query(default=10, ge=1, le=100),
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

    section_ids = [str(section["id"]) for section in sections]
    work_orders = (
        supabase.table("work_orders")
        .select("id,road_section_id,priority,status")
        .in_("road_section_id", section_ids)
        .limit(10000)
        .execute()
        .data
        or []
    )
    orders_by_section: dict[str, list[dict]] = {}
    for work_order in work_orders:
        section_id = str(work_order.get("road_section_id") or "")
        if section_id:
            orders_by_section.setdefault(section_id, []).append(work_order)

    road_ids = list({str(s["road_id"]) for s in sections if s.get("road_id")})
    roads_by_id: dict[str, dict] = {}
    if road_ids:
        roads = (
            supabase.table("roads")
            .select("id,road_code,name")
            .in_("id", road_ids)
            .execute()
            .data
            or []
        )
        roads_by_id = {str(r["id"]): r for r in roads}

    plans = (
        supabase.table("maintenance_plans")
        .select("id,name,status,fiscal_year")
        .limit(100)
        .execute()
        .data
        or []
    )

    rows = []

    for section in sections:
        orders = orders_by_section.get(str(section["id"]), [])
        priority = score_road_section(section, orders, related_plans=plans)
        road = roads_by_id.get(str(section.get("road_id") or ""), {})

        rows.append(
            RoadRankingItem(
                rank=0,
                road_section_id=section["id"],
                section_code=section.get("section_code"),
                road_id=section.get("road_id"),
                road_code=road.get("road_code"),
                road_name=road.get("name"),
                priority_score=priority.score,
                priority_level=priority.level,
                condition_rating=section.get("condition_rating"),
                status=section.get("status"),
                active_work_orders=priority.active_work_orders,
                urgent_work_orders=priority.urgent_work_orders,
                confidence=priority.confidence,
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
        for index, item in enumerate(rows[:limit], start=1)
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

    response = RoadRankingResponse(
        total_sections_analyzed=len(rows),
        rankings=enriched_rankings,
        methodology=(
            "Sections are ranked using deterministic condition, work-order urgency, "
            "maintenance-plan signals, and data-quality factors. Road metadata is "
            "joined for context. Score and rank are authoritative; AI only explains "
            "verified evidence and suggests advisory next actions."
        ),
        ai_generated=ai_generated,
    )

    org_id = resolve_organization_id(supabase, current_user["id"])
    if org_id:
        log_analysis_run(
            supabase,
            organization_id=org_id,
            analysis_type="road_ranking",
            status="completed",
            result={
                "total_sections_analyzed": len(rows),
                "returned": len(enriched_rankings),
                "ai_generated": ai_generated,
            },
            evidence={"methodology": response.methodology},
            created_by=current_user["id"],
        )

    return response


@router.post("/office-assistant", response_model=OfficeAssistantResponse)
def office_assistant(
    request: OfficeAssistantRequest,
    current_user=Depends(get_current_user),
):
    supabase = current_user["client"]

    roads = (
        supabase.table("roads")
        .select("id,road_code,name,total_length_km,status")
        .limit(100)
        .execute()
        .data
        or []
    )
    sections = (
        supabase.table("road_sections")
        .select("id,road_id,section_code,condition_rating,status")
        .limit(500)
        .execute()
        .data
        or []
    )
    plans = (
        supabase.table("maintenance_plans")
        .select("id,name,fiscal_year,plan_type,status,budget_amount,start_date,end_date")
        .limit(100)
        .execute()
        .data
        or []
    )
    work_orders = (
        supabase.table("work_orders")
        .select(
            "id,road_section_id,work_order_no,title,maintenance_type,"
            "priority,status,planned_cost,actual_cost"
        )
        .limit(500)
        .execute()
        .data
        or []
    )
    machinery = (
        supabase.table("machinery")
        .select("id,asset_code,name,machinery_type,status,current_hours")
        .limit(200)
        .execute()
        .data
        or []
    )
    employees = (
        supabase.table("employees")
        .select("id,employee_code,full_name,job_title,status")
        .limit(200)
        .execute()
        .data
        or []
    )
    budgets = (
        supabase.table("budgets")
        .select(
            "id,fiscal_year,budget_code,category,allocated_amount,"
            "spent_amount,committed_amount,status"
        )
        .limit(50)
        .execute()
        .data
        or []
    )
    expenses = (
        supabase.table("expenses")
        .select(
            "id,budget_id,work_order_id,expense_date,description,"
            "category,amount,status"
        )
        .limit(200)
        .execute()
        .data
        or []
    )
    assets = (
        supabase.table("assets")
        .select("id,asset_code,name,category,location,status,current_value")
        .limit(200)
        .execute()
        .data
        or []
    )

    active_orders = [
        item
        for item in work_orders
        if (item.get("status") or "").lower()
        not in {"completed", "closed", "cancelled"}
    ]
    critical_sections = [
        item
        for item in sections
        if item.get("condition_rating") is not None
        and float(item["condition_rating"]) >= 4
    ]
    available_machinery = [
        item
        for item in machinery
        if (item.get("status") or "").lower()
        in {"available", "ready", "operational"}
    ]
    down_machinery = [
        item
        for item in machinery
        if (item.get("status") or "").lower()
        in {"down", "under_maintenance", "broken", "unavailable"}
    ]
    active_employees = [
        item
        for item in employees
        if (item.get("status") or "").lower() == "active"
    ]
    active_assets = [
        item
        for item in assets
        if (item.get("status") or "").lower() == "active"
    ]

    total_allocated = sum(float(b.get("allocated_amount") or 0) for b in budgets)
    total_spent = sum(float(b.get("spent_amount") or 0) for b in budgets)

    evidence = [
        f"Road records available to this organization: {len(roads)}.",
        f"Road sections available to this organization: {len(sections)}.",
        f"Maintenance plans available: {len(plans)}.",
        f"Work orders available: {len(work_orders)}; active: {len(active_orders)}.",
        f"Sections with recorded condition rating >= 4: {len(critical_sections)}.",
        (
            f"Machinery records available: {len(machinery)}; "
            f"available/operational: {len(available_machinery)}; "
            f"down/under maintenance: {len(down_machinery)}."
        ),
        f"Employee records available: {len(employees)}; active: {len(active_employees)}.",
        (
            f"Budget records available: {len(budgets)}; "
            f"total allocated: {total_allocated:.2f}; total spent: {total_spent:.2f}."
        ),
        f"Expense records available: {len(expenses)}.",
        f"General asset records available: {len(assets)}; active: {len(active_assets)}.",
    ]

    settings = get_settings()
    if not settings.gemini_api_key:
        answer = (
            "Structured operational evidence was collected for this organization. "
            "Configure GEMINI_API_KEY to enable natural-language answers. "
            "Key counts: "
            f"{len(roads)} roads, {len(sections)} sections, "
            f"{len(active_orders)} active work orders, "
            f"{len(available_machinery)} available machinery units."
        )
        return OfficeAssistantResponse(
            query=request.query,
            answer=answer,
            evidence=evidence,
            ai_generated=False,
        )

    context = {
        "roads_sample": roads[:10],
        "sections_sample": sections[:15],
        "plans_sample": plans[:10],
        "work_orders_sample": work_orders[:15],
        "machinery_sample": machinery[:10],
        "employees_sample": employees[:10],
        "budgets_sample": budgets[:10],
        "expenses_sample": expenses[:10],
        "assets_sample": assets[:10],
        "summary": evidence,
    }
    prompt = (
        "Answer the office question using ONLY the supplied organization data. "
        "If the data does not contain the answer, say it is not available. "
        "Do not invent figures, road conditions, costs, or staff assignments. "
        "Do not approve spending or contracts. Keep the answer concise.\n\n"
        f"Question: {request.query}\n\n"
        f"Data:\n{json.dumps(context, default=str)}"
    )
    result = generate_text(
        prompt,
        system_instruction="You are the AI-RMMS office assistant for road maintenance.",
    )
    answer = (
        result.text
        if result
        else (
            "I could not generate an AI answer right now. "
            "Please review the structured evidence counts."
        )
    )

    org_id = resolve_organization_id(supabase, current_user["id"])
    if org_id:
        log_analysis_run(
            supabase,
            organization_id=org_id,
            analysis_type="office_assistant",
            status="completed",
            result={"ai_generated": bool(result)},
            evidence={"summary": evidence},
            created_by=current_user["id"],
        )

    return OfficeAssistantResponse(
        query=request.query,
        answer=answer,
        evidence=evidence,
        ai_generated=bool(result),
    )
