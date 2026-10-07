from decimal import Decimal

from app.api.routes.ai import calculate_priority


def test_calculate_priority_with_urgent_work_order():
    data = {
        "condition_rating": 5,
        "status": "poor",
    }
    work_orders = [
        {"priority": "high", "status": "open"},
    ]

    score, level, confidence, reasons, evidence = calculate_priority(
        data, work_orders
    )

    assert score == Decimal("100.00")
    assert level == "critical"
    assert confidence == Decimal("0.90")
    assert "Recorded condition rating is 5." in reasons
    assert any("urgent/high: 1" in item for item in evidence)


def test_calculate_priority_without_condition_data():
    data = {
        "condition_rating": None,
        "status": "good",
    }

    score, level, confidence, reasons, evidence = calculate_priority(data, [])

    assert score == Decimal("29.41")
    assert level == "low"
    assert confidence == Decimal("0.70")
    assert any("neutral score" in item for item in reasons)
