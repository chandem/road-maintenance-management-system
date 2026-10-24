from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.schemas.budget_planner import (
    BudgetPlanCandidateRequest,
    BudgetPlanRequest,
    BudgetPlanResponse,
)


def test_budget_plan_request_requires_documented_cost_basis():
    with pytest.raises(ValidationError):
        BudgetPlanCandidateRequest(
            road_section_id=uuid4(),
            estimated_cost=Decimal("125000"),
        )


def test_budget_plan_request_rejects_duplicate_sections():
    section_id = uuid4()
    candidate = {
        "road_section_id": section_id,
        "estimated_cost": "125000.00",
        "cost_basis": "Engineer estimate Rev 1",
    }
    with pytest.raises(ValidationError, match="Each road section may appear only once"):
        BudgetPlanRequest(budget="200000", candidates=[candidate, candidate])


def test_budget_plan_request_accepts_zero_budget_and_cost():
    payload = BudgetPlanRequest(
        budget="0",
        candidates=[
            {
                "road_section_id": uuid4(),
                "estimated_cost": "0",
                "cost_basis": "Verified BOQ item total",
            }
        ],
    )
    assert payload.budget == Decimal("0")
    assert payload.candidates[0].estimated_cost == Decimal("0")


def test_budget_plan_response_defaults_to_advisory_only():
    response = BudgetPlanResponse(
        budget=Decimal("100"),
        selected=[],
        deferred=[],
        selected_total=Decimal("0"),
        remaining_budget=Decimal("100"),
        method="priority-first, budget-feasible heuristic",
        limitations=["Advisory only"],
    )
    assert response.advisory_only is True
