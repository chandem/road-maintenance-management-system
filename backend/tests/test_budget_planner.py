from decimal import Decimal

import pytest

from app.services.budget_planner import (
    MaintenanceCandidate,
    build_budget_plan,
)


def candidate(section_id, score, cost, cost_basis="BOQ estimate"):
    return MaintenanceCandidate(
        section_id=section_id,
        section_code=section_id.upper(),
        priority_score=Decimal(str(score)),
        estimated_cost=Decimal(str(cost)),
        cost_basis=cost_basis,
    )


def test_plan_selects_high_priority_works_without_exceeding_budget():
    plan = build_budget_plan(
        "1000",
        [
            candidate("a", 90, 800),
            candidate("b", 80, 400),
            candidate("c", 70, 200),
        ],
    )

    assert [item.candidate.section_id for item in plan.selected] == ["a", "c"]
    assert [item.candidate.section_id for item in plan.deferred] == ["b"]
    assert plan.selected_total == Decimal("1000")
    assert plan.remaining_budget == Decimal("0")
    assert all("Deferred" in item.reason for item in plan.deferred)


def test_plan_handles_zero_budget_and_zero_cost():
    plan = build_budget_plan(
        0,
        [candidate("free", 20, 0), candidate("costly", 100, 1)],
    )

    assert [item.candidate.section_id for item in plan.selected] == ["free"]
    assert [item.candidate.section_id for item in plan.deferred] == ["costly"]
    assert plan.selected_total == Decimal("0")
    assert plan.remaining_budget == Decimal("0")


@pytest.mark.parametrize("budget", [-1, "NaN", "Infinity", "not-money"])
def test_rejects_invalid_budget(budget):
    with pytest.raises(ValueError):
        build_budget_plan(budget, [])


@pytest.mark.parametrize(
    "items",
    [
        [candidate("a", 50, 10), candidate("a", 40, 20)],
        [candidate("a", 101, 10)],
        [candidate("a", 50, -1)],
        [candidate(" ", 50, 10)],
    ],
)
def test_rejects_invalid_candidates(items):
    with pytest.raises(ValueError):
        build_budget_plan(100, items)


def test_equal_priority_is_stable_and_prefers_lower_cost():
    plan = build_budget_plan(
        100,
        [candidate("z", 60, 80), candidate("b", 60, 20)],
    )

    assert [item.candidate.section_id for item in plan.selected] == ["b", "z"]
    assert plan.remaining_budget == Decimal("0")
