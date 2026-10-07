from app.api.routes.documents import _document_snippet, search_documents


def test_document_search_route_is_registered():
    assert search_documents is not None
    assert search_documents.__name__ == "search_documents"


def test_document_snippet_centers_query_match():
    text = "The Magado-Shakiso section requires urgent routine maintenance because the road is highly deteriorated."

    snippet = _document_snippet(text, "urgent routine maintenance", max_length=80)

    assert "urgent routine maintenance" in snippet
    assert len(snippet) <= 83


def test_document_snippet_returns_start_when_query_is_missing():
    text = "Monthly road maintenance progress report for the Soda-Shakiso segment."

    snippet = _document_snippet(text, "budget", max_length=30)

    assert snippet == text[:30]
