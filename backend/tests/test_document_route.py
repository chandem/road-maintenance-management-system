from app.api.routes.documents import classify_uploaded_document


def test_document_classification_route_function_is_registered():
    assert classify_uploaded_document is not None
    assert classify_uploaded_document.__name__ == "classify_uploaded_document"
