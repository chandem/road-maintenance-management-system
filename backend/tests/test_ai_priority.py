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
    assert confidence == Decimal("0.45")
    assert any("neutral score" in item for item in reasons)
    assert any("data_quality=0" in item for item in evidence)



def test_recent_inspection_critical_hazard_raises_priority():
    data = {
        "condition_rating": 4,
        "status": "active",
        "inspection_surface_condition": "fair",
        "inspection_defects_summary": "Road washout near the culvert",
    }

    score, level, confidence, reasons, evidence = calculate_priority(data, [])

    assert score >= Decimal("85.00")
    assert level == "critical"
    assert any("critical road hazard" in reason for reason in reasons)
    assert any("critical defect keyword" in item for item in evidence)


def test_recent_inspection_poor_surface_raises_priority():
    data = {
        "condition_rating": 4,
        "status": "active",
        "inspection_surface_condition": "poor",
        "inspection_defects_summary": None,
    }

    score, level, confidence, reasons, evidence = calculate_priority(data, [])

    assert score >= Decimal("60.00")
    assert level == "high"
    assert any("poor surface condition" in reason for reason in reasons)
