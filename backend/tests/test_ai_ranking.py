from decimal import Decimal

from app.api.routes.ai import calculate_priority


def test_ranking_prefers_worse_condition():
    poor = {"condition_rating": 5, "status": "poor"}
    good = {"condition_rating": 1, "status": "good"}

    poor_score, *_ = calculate_priority(poor, [])
    good_score, *_ = calculate_priority(good, [])

    assert poor_score > good_score


def test_urgent_work_order_increases_priority():
    data = {"condition_rating": 3, "status": "fair"}

    without_order, *_ = calculate_priority(data, [])
    with_order, *_ = calculate_priority(
        data, [{"priority": "high", "status": "open"}]
    )

    assert with_order > without_order


def test_closed_work_order_does_not_count_as_active():
    data = {"condition_rating": 3, "status": "fair"}

    score, level, confidence, reasons, evidence = calculate_priority(
        data,
        [{"priority": "high", "status": "closed"}],
    )

    assert "0 active work order(s)" in reasons
    assert any("active: 0" in item and "urgent/high: 0" in item for item in evidence)
    assert score == Decimal("44.12")


def test_priority_score_stays_within_bounds():
    data = {"condition_rating": 5, "status": "critical"}
    orders = [{"priority": "urgent", "status": "open"} for _ in range(10)]

    score, level, confidence, _, _ = calculate_priority(data, orders)

    assert Decimal("0") <= score <= Decimal("100")
    assert level == "critical"
    assert confidence == Decimal("0.90")
