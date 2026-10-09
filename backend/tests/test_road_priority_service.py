from decimal import Decimal

from app.services.road_priority import baseline_action, calculate_priority


def test_service_urgent_poor_condition_is_critical():
    result = calculate_priority(
        {"condition_rating": 5, "status": "poor"},
        [{"priority": "high", "status": "open"}],
    )
    assert result.score == Decimal("100.00")
    assert result.level == "critical"
    assert result.urgent_work_orders == 1


def test_service_active_plan_raises_planning_signal():
    without = calculate_priority({"condition_rating": 3, "status": "fair"}, [])
    with_plan = calculate_priority(
        {"condition_rating": 3, "status": "fair"},
        [],
        related_plans=[{"status": "active", "name": "FY plan"}],
    )
    assert with_plan.score >= without.score


def test_baseline_actions_cover_all_levels():
    for level in ("critical", "high", "medium", "low"):
        assert isinstance(baseline_action(level), str)
        assert len(baseline_action(level)) > 10
