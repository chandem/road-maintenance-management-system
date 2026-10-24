"""Transparent, deterministic budget-constrained maintenance selection.

This is a planning heuristic, not a financial approval or a claim of globally
optimal knapsack selection. Callers must supply verified priority scores and
clearly identified cost estimates.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation


@dataclass(frozen=True)
class MaintenanceCandidate:
    section_id: str
    section_code: str
    priority_score: Decimal
    estimated_cost: Decimal
    cost_basis: str = "estimate"


@dataclass(frozen=True)
class PlannedCandidate:
    candidate: MaintenanceCandidate
    reason: str


@dataclass(frozen=True)
class BudgetPlan:
    budget: Decimal
    selected: list[PlannedCandidate]
    deferred: list[PlannedCandidate]
    selected_total: Decimal
    remaining_budget: Decimal
    method: str = "priority-first, budget-feasible heuristic"


def build_budget_plan(
    budget: Decimal | int | float | str,
    candidates: list[MaintenanceCandidate],
) -> BudgetPlan:
    """Select candidates by descending priority without exceeding the budget.

    Ties are resolved by lower cost, then stable section ID. Duplicate IDs,
    invalid scores, negative costs, and negative budgets are rejected.
    """
    try:
        available = Decimal(str(budget))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError("Budget must be a valid non-negative number.") from exc
    if not available.is_finite() or available < 0:
        raise ValueError("Budget must be a valid non-negative number.")

    seen: set[str] = set()
    normalized: list[MaintenanceCandidate] = []
    for item in candidates:
        section_id = str(item.section_id).strip()
        if not section_id:
            raise ValueError("Every candidate must have a section ID.")
        if section_id in seen:
            raise ValueError(f"Duplicate road section ID: {section_id}")
        seen.add(section_id)
        try:
            score = Decimal(str(item.priority_score))
            cost = Decimal(str(item.estimated_cost))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Invalid score or cost for section {section_id}.") from exc
        if not score.is_finite() or score < 0 or score > 100:
            raise ValueError(f"Priority score for section {section_id} must be 0–100.")
        if not cost.is_finite() or cost < 0:
            raise ValueError(f"Cost for section {section_id} must be non-negative.")
        normalized.append(
            MaintenanceCandidate(
                section_id=section_id,
                section_code=str(item.section_code or section_id),
                priority_score=score,
                estimated_cost=cost,
                cost_basis=str(item.cost_basis or "estimate"),
            )
        )

    ordered = sorted(
        normalized,
        key=lambda item: (-item.priority_score, item.estimated_cost, item.section_id),
    )
    selected: list[PlannedCandidate] = []
    deferred: list[PlannedCandidate] = []
    remaining = available
    for item in ordered:
        if item.estimated_cost <= remaining:
            selected.append(
                PlannedCandidate(
                    candidate=item,
                    reason=(
                        f"Selected: priority score {item.priority_score}; cost "
                        f"{item.estimated_cost} fits within the remaining budget."
                    ),
                )
            )
            remaining -= item.estimated_cost
        else:
            deferred.append(
                PlannedCandidate(
                    candidate=item,
                    reason=(
                        f"Deferred: priority score {item.priority_score}, but cost "
                        f"{item.estimated_cost} exceeds remaining budget {remaining}."
                    ),
                )
            )

    total = available - remaining
    return BudgetPlan(
        budget=available,
        selected=selected,
        deferred=deferred,
        selected_total=total,
        remaining_budget=remaining,
    )
