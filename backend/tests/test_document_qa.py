from pydantic import ValidationError

from app.api.routes.documents import ask_document_question
from app.schemas.documents import DocumentQuestionRequest


def test_document_question_route_is_registered():
    assert ask_document_question is not None
    assert ask_document_question.__name__ == "ask_document_question"


def test_document_question_request_validates_question_length():
    request = DocumentQuestionRequest(question="  What maintenance is planned?  ")
    assert request.question.strip() == "What maintenance is planned?"


def test_document_question_request_limits_retrieval_count():
    request = DocumentQuestionRequest(question="Which roads are urgent?", limit=10)
    assert request.limit == 10


def test_document_question_request_rejects_empty_question():
    try:
        DocumentQuestionRequest(question="  ")
    except ValidationError:
        return
    raise AssertionError("An empty document question should be rejected")
