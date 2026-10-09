import pytest
from pydantic import ValidationError

from app.schemas.office_assistant import OfficeAssistantRequest, OfficeAssistantResponse


def test_accepts_question_field():
    req = OfficeAssistantRequest(question="Which roads need work?")
    assert req.question == "Which roads need work?"
    assert req.query == "Which roads need work?"


def test_accepts_legacy_query_field():
    req = OfficeAssistantRequest(query="How many active work orders?")
    assert req.question == "How many active work orders?"


def test_rejects_empty_question():
    with pytest.raises(ValidationError):
        OfficeAssistantRequest(question="ab")


def test_response_includes_module_fields():
    resp = OfficeAssistantResponse(
        query="status?",
        answer="Not available from records.",
        evidence=["No matching data."],
        modules_consulted=["RAMS", "MMMS"],
        document_evidence=[],
        advisory=True,
        ai_generated=False,
    )
    assert resp.modules_consulted == ["RAMS", "MMMS"]
    assert resp.advisory is True
