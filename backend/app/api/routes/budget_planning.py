from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import require_department_access
from app.schemas.budget_planner import (
    BudgetPlanItem,
    BudgetPlanRequest,
    BudgetPlanResponse,
)
from app.services.budget_planner import (
    MaintenanceCandidate,
    build_budget_plan,
)
from app.services.road_priority import calculate_priority as score_road_section

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/budget-plan", response_model=BudgetPlanResponse)
def create_budget_constrained_plan(
    request: BudgetPlanRequest,
    current_user=Depends(
        require_department_access("road_asset", ["department_manager", "officer"])
    ),
):
    """Build an advisory plan from authorized road data and explicitly supplied costs.

    The caller must provide a documented cost basis for each candidate and the
    available planning budget. This endpoint does not read or modify Finance
    records, approve spending, or treat historical work-order costs as estimates.
    """
    supabase = current_user["client"]
    requested_ids = [str(item.road_section_id) for item in request.candidates]

    sections = (
        supabase.table("road_sections")
        .select(
            "id,road_id,section_code,start_chainage_km,end_chainage_km,"
            "length_km,condition_rating,status"
        )
        .in_("id", requested_ids)
        .limit(100)
        .execute()
        .data
        or []
    )
    sections_by_id = {str(section["id"]): section for section in sections}
    missing_ids = [section_id for section_id in requested_ids if section_id not in sections_by_id]
    if missing_ids:
        # Do not disclose whether an unavailable ID is nonexistent or outside RLS.
        raise HTTPException(
            status_code=404,
            detail="One or more road sections were not found or are not accessible.",
        )

    inspections = (
        supabase.table("road_inspections")
        .select(
            "road_section_id,inspection_date,surface_condition,"
            "defects_summary,condition_rating"
        )
        .in_("road_section_id", requested_ids)
        .order("inspection_date", desc=True)
        .limit(1000)
        .execute()
        .data
        or []
    )
    latest_inspection_by_section: dict[str, dict] = {}
    for inspection in inspections:
        section_id = str(inspection.get("road_section_id") or "")
        if section_id and section_id not in latest_inspection_by_section:
            latest_inspection_by_section[section_id] = inspection

    work_orders = (
        supabase.table("work_orders")
        .select("id,road_section_id,priority,status")
        .in_("road_section_id", requested_ids)
        .limit(5000)
        .execute()
        .data
        or []
    )
    orders_by_section: dict[str, list[dict]] = {}
    for order in work_orders:
        section_id = str(order.get("road_section_id") or "")
        if section_id:
            orders_by_section.setdefault(section_id, []).append(order)

    road_ids = list(
        {str(section["road_id"]) for section in sections if section.get("road_id")}
    )
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
        roads_by_id = {str(road["id"]): road for road in roads}

    candidates: list[MaintenanceCandidate] = []
    metadata: dict[str, dict] = {}
    for supplied in request.candidates:
        section_id = str(supplied.road_section_id)
        section = dict(sections_by_id[section_id])
        inspection = latest_inspection_by_section.get(section_id)
        if inspection:
            section["inspection_surface_condition"] = inspection.get("surface_condition")
            section["inspection_defects_summary"] = inspection.get("defects_summary")
            if inspection.get("condition_rating") is not None:
                section["condition_rating"] = inspection["condition_rating"]

        priority = score_road_section(section, orders_by_section.get(section_id, []))
        road = roads_by_id.get(str(section.get("road_id") or ""), {})
        code = str(section.get("section_code") or section_id)
        candidates.append(
            MaintenanceCandidate(
                section_id=section_id,
                section_code=code,
                priority_score=priority.score,
                estimated_cost=supplied.estimated_cost,
                cost_basis=supplied.cost_basis.strip(),
            )
        )
        metadata[section_id] = {
            "section_code": section.get("section_code"),
            "road_code": road.get("road_code"),
            "road_name": road.get("name"),
            "priority_score": priority.score,
            "priority_level": priority.level,
            "confidence": priority.confidence,
            "estimated_cost": supplied.estimated_cost,
            "cost_basis": supplied.cost_basis.strip(),
        }

    try:
        plan = build_budget_plan(request.budget, candidates)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    def serialize(items):
        results = []
        for planned in items:
            candidate = planned.candidate
            info = metadata[candidate.section_id]
            results.append(
                BudgetPlanItem(
                    road_section_id=UUID(candidate.section_id),
                    section_code=info["section_code"],
                    road_code=info["road_code"],
                    road_name=info["road_name"],
                    priority_score=info["priority_score"],
                    priority_level=info["priority_level"],
                    confidence=info["confidence"],
                    estimated_cost=info["estimated_cost"],
                    cost_basis=info["cost_basis"],
                    reason=planned.reason,
                )
            )
        return results

    return BudgetPlanResponse(
        budget=plan.budget,
        selected=serialize(plan.selected),
        deferred=serialize(plan.deferred),
        selected_total=plan.selected_total,
        remaining_budget=plan.remaining_budget,
        method=plan.method,
        limitations=[
            "Priority-first heuristic; not guaranteed to be globally cost-optimal.",
            "Costs are user-supplied estimates; verify the stated BOQ or estimate basis.",
            "Priority scores depend on available condition, inspection, and work-order data.",
            "Recommendations are advisory and do not approve spending or contracts.",
        ],
    )
