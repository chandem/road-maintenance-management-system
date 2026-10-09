from app.api.routes.documents import classify_uploaded_document


def test_document_classification_route_function_is_registered():
    assert classify_uploaded_document is not None
    assert classify_uploaded_document.__name__ == "classify_uploaded_document"

import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.routes import documents as document_routes


class OversizedUpload:
    filename = "oversized.txt"
    content_type = "text/plain"

    def __init__(self):
        self.read_size = None

    async def read(self, size=-1):
        self.read_size = size
        return b"x" * size


def test_document_upload_rejects_oversized_content_with_bounded_read(monkeypatch):
    upload = OversizedUpload()
    monkeypatch.setattr(document_routes, "_authorize_department", lambda *_args, **_kwargs: "org-1")
    monkeypatch.setattr(
        document_routes,
        "extract_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("oversized file must not be extracted")),
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            document_routes.classify_uploaded_document(
                file=upload,
                department_code="road_asset",
                current_user={"id": "user-1", "client": object()},
            )
        )

    assert error.value.status_code == 413
    assert upload.read_size == document_routes.MAX_FILE_SIZE + 1

