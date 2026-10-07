from app.services.document_intelligence import classify_document


def test_classifies_maintenance_plan_from_filename():
    result = classify_document("Soda-Shakiso Maintenance Plan 2019.xlsx")

    assert result.document_type == "maintenance_plan"
    assert result.confidence > 0


def test_classifies_work_order_from_content():
    result = classify_document(
        "document.pdf",
        "Work Order No. 14. Repair the failed drainage section at chainage 12+500.",
    )

    assert result.document_type == "work_order"
    assert any("work order" in reason.lower() for reason in result.reasons)


def test_classifies_bill_of_quantities():
    result = classify_document(
        "project-cost.pdf",
        "Bill of Quantities BOQ for routine road maintenance works.",
    )

    assert result.document_type == "bill_of_quantities"


def test_unknown_document_has_zero_confidence():
    result = classify_document("notes.txt", "This document contains unrelated notes.")

    assert result.document_type == "unknown"
    assert result.confidence == 0.0


def test_filename_and_content_can_strengthen_classification():
    result = classify_document(
        "monthly-report.pdf",
        "Monthly report for road inspection and road condition survey activities.",
    )

    assert result.document_type == "road_inspection_report"
    assert result.confidence >= 0.65
