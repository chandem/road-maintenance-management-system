"""Deterministic road-section priority scoring for AI-RMMS.

Engineering-first: verified data drives the score. The LLM only explains.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


def clamp(value: Decimal) -> Decimal:
    return max(Decimal("0"), min(Decimal("100"), value))


@dataclass(frozen=True)
class PriorityResult:
    score: Decimal
    level: str
    confidence: Decimal
    reasons: list[str]
    evidence: list[str]
    active_work_orders: int
    urgent_work_orders: int


def calculate_priority(
    data: dict,
    work_orders: list[dict],
    *,
    related_plans: list[dict] | None = None,
) -> PriorityResult:
    """Score a road section from condition, work orders, and optional plans."""
    reasons: list[str] = []
    evidence: list[str] = []
    plans = related_plans or []

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

    reasons.append(
        f"{len(open_orders)} active work order(s) are linked to this section."
    )
    evidence.append(
        f"Linked work orders: {len(work_orders)}; active: {len(open_orders)}; "
        f"urgent/high: {len(urgent_orders)}."
    )

    active_plans = [
        p
        for p in plans
        if (p.get("status") or "").lower() not in {"completed", "cancelled", "closed"}
    ]
    if active_plans:
        evidence.append(
            f"Related active maintenance plan(s): {len(active_plans)}."
        )

    planning = (
        Decimal("100")
        if open_orders
        else Decimal("80")
        if active_plans
        else Decimal("70")
        if str(data.get("status") or "").lower()
        in {"critical", "poor", "failed"}
        else Decimal("0")
    )

    status = str(data.get("status") or "").lower()
    if rating is None:
        data_points = 2
        data_quality = Decimal("0")
    else:
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

    if urgent_orders and (
        rating is None
        or float(rating) >= 4
        or status in {"critical", "poor", "failed"}
    ):
        score = Decimal("100.00")
    else:
        raw_score = (
            condition * Decimal("0.50")
            + urgency * Decimal("0.20")
            + planning * Decimal("0.10")
            + data_quality * Decimal("0.05")
        )
        score = clamp(raw_score / Decimal("0.85"))

    # Recent field observations add deterministic risk signals. The language model
    # explains these results but never changes the numeric score.
    inspection_text = " ".join(
        str(data.get(key) or "")
        for key in ("inspection_surface_condition", "inspection_defects_summary")
    ).lower()
    critical_defects = (
        "washout", "road blocked", "bridge failure", "collapse",
        "landslide", "road collapsed", "major flood"
    )
    high_risk_defects = (
        "pothole", "erosion", "blocked drainage", "drainage blocked",
        "cracking", "rutting", "shoulder failure", "flooding",
        "scouring", "deep rut"
    )
    if any(term in inspection_text for term in critical_defects):
        score = max(score, Decimal("85.00"))
        reasons.append("Latest inspection records a potentially critical road hazard.")
        evidence.append("Inspection hazard signal: critical defect keyword recorded.")
    elif any(term in inspection_text for term in high_risk_defects):
        score = max(score, Decimal("65.00"))
        reasons.append("Latest inspection records a defect requiring prompt review.")
        evidence.append("Inspection hazard signal: significant defect keyword recorded.")

    surface_condition = str(data.get("inspection_surface_condition") or "").lower()
    if surface_condition in {"failed", "very poor"}:
        score = max(score, Decimal("80.00"))
        reasons.append(f"Latest inspection surface condition is {surface_condition}.")
        evidence.append(f"Latest inspection surface condition: {surface_condition}.")
    elif surface_condition == "poor":
        score = max(score, Decimal("60.00"))
        reasons.append("Latest inspection records poor surface condition.")
        evidence.append("Latest inspection surface condition: poor.")

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
        if data_points >= 2
        else Decimal("0.45")
    )

    evidence.append(
        f"Score components: condition={condition}, urgency={urgency}, "
        f"planning={planning}, data_quality={data_quality}."
    )

    return PriorityResult(
        score=score.quantize(Decimal("0.01")),
        level=level,
        confidence=confidence,
        reasons=reasons,
        evidence=evidence,
        active_work_orders=len(open_orders),
        urgent_work_orders=len(urgent_orders),
    )


def baseline_action(level: str) -> str:
    return {
        "critical": "Prioritize field verification and maintenance action.",
        "high": (
            "Schedule field verification and include in near-term "
            "maintenance planning."
        ),
        "medium": "Monitor the section and address it through planned maintenance.",
        "low": (
            "Continue routine monitoring and update condition data when available."
        ),
    }[level]
