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

class ReindexDocumentQuery:
    def __init__(self, row):
        self.row = row

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, *_args, **_kwargs):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return SimpleNamespace(data=self.row)


class ReindexDocumentClient:
    def __init__(self, row):
        self.row = row

    def table(self, name):
        assert name == "documents"
        return ReindexDocumentQuery(self.row)


def test_read_only_user_cannot_reindex_document(monkeypatch):
    from uuid import UUID

    row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "title": "Road plan",
        "organization_id": "org-1",
        "department_code": "road_asset",
        "extracted_text": "Road maintenance content",
        "extraction_status": "completed",
    }
    client = ReindexDocumentClient(row)

    def deny_write(_user, _row, *, write=False):
        assert write is True
        raise HTTPException(status_code=403, detail="Read-only role cannot reindex")

    monkeypatch.setattr(document_routes, "_authorize_document_row", deny_write)
    monkeypatch.setattr(
        document_routes,
        "ingest_document_chunks",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("reindex must not run")),
    )

    with pytest.raises(HTTPException) as error:
        document_routes.reindex_document(
            UUID(row["id"]),
            current_user={"id": "read-only-user", "client": client},
        )

    assert error.value.status_code == 403

def test_unauthorized_user_is_rejected_before_upload_is_read(monkeypatch):
    upload = OversizedUpload()

    def deny_upload(*_args, **_kwargs):
        raise HTTPException(status_code=403, detail="Department access denied")

    monkeypatch.setattr(document_routes, "_authorize_department", deny_upload)

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            document_routes.classify_uploaded_document(
                file=upload,
                department_code="finance",
                current_user={"id": "road-user", "client": object()},
            )
        )

    assert error.value.status_code == 403
    assert upload.read_size is None

