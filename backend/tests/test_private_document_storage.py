from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.api.routes.documents import (
    PRIVATE_DOCUMENT_BUCKET,
    SIGNED_URL_TTL_SECONDS,
    _private_storage_path,
    get_original_document_url,
)


def test_private_storage_path_is_scoped_and_uses_generated_filename():
    organization_id = str(uuid4())
    document_id = str(uuid4())

    path = _private_storage_path(organization_id, "finance", document_id, ".pdf")

    parts = path.split("/")
    assert parts[:3] == [organization_id, "finance", document_id]
    assert parts[3].endswith(".pdf")
    assert parts[3] != "user-uploaded.pdf"


def test_private_storage_path_rejects_unknown_department():
    with pytest.raises(ValueError):
        _private_storage_path(str(uuid4()), "../other", str(uuid4()), ".pdf")


class FakeQuery:
    def __init__(self, row):
        self.row = row

    def select(self, *_args):
        return self

    def eq(self, *_args):
        return self

    def maybe_single(self):
        return self

    def execute(self):
        return type("Result", (), {"data": self.row})()


class FakeStorageBucket:
    def __init__(self, response=None):
        self.response = response or {"signedURL": "https://storage.example/signed"}
        self.calls = []

    def create_signed_url(self, path, ttl):
        self.calls.append((path, ttl))
        return self.response


class FakeClient:
    def __init__(self, row, signed_response=None):
        self.row = row
        self.bucket = FakeStorageBucket(signed_response)
        self.storage_calls = []

    def table(self, _table_name):
        return FakeQuery(self.row)

    class Storage:
        def __init__(self, parent):
            self.parent = parent

        def from_(self, bucket_name):
            self.parent.storage_calls.append(bucket_name)
            return self.parent.bucket

    @property
    def storage(self):
        return self.Storage(self)


def test_download_authorizes_row_then_returns_short_lived_url(monkeypatch):
    document_id = uuid4()
    row = {
        "id": str(document_id),
        "title": "budget.pdf",
        "organization_id": str(uuid4()),
        "department_code": "finance",
        "storage_path": "org/finance/doc/generated.pdf",
    }
    client = FakeClient(row)
    authorized = []
    monkeypatch.setattr(
        "app.api.routes.documents._authorize_document_row",
        lambda current_user, data: authorized.append(data["id"]) or row["organization_id"],
    )

    result = get_original_document_url(document_id, current_user={"client": client})

    assert authorized == [str(document_id)]
    assert client.storage_calls == [PRIVATE_DOCUMENT_BUCKET]
    assert client.bucket.calls == [(row["storage_path"], SIGNED_URL_TTL_SECONDS)]
    assert result["url"] == "https://storage.example/signed"
    assert result["expires_in"] == 60


def test_download_does_not_sign_when_document_has_no_original(monkeypatch):
    document_id = uuid4()
    row = {
        "id": str(document_id),
        "title": "legacy.pdf",
        "organization_id": str(uuid4()),
        "department_code": "finance",
        "storage_path": None,
    }
    client = FakeClient(row)
    monkeypatch.setattr(
        "app.api.routes.documents._authorize_document_row",
        lambda *_args, **_kwargs: row["organization_id"],
    )

    with pytest.raises(HTTPException) as exc:
        get_original_document_url(document_id, current_user={"client": client})

    assert exc.value.status_code == 404
    assert client.storage_calls == []



def test_download_denied_by_authorization_never_requests_signed_url(monkeypatch):
    document_id = uuid4()
    row = {
        "id": str(document_id),
        "title": "confidential.pdf",
        "organization_id": str(uuid4()),
        "department_code": "finance",
        "storage_path": "org/finance/doc/private.pdf",
    }
    client = FakeClient(row)

    def deny_access(*_args, **_kwargs):
        raise HTTPException(status_code=403, detail="Forbidden")

    monkeypatch.setattr("app.api.routes.documents._authorize_document_row", deny_access)

    with pytest.raises(HTTPException) as exc:
        get_original_document_url(document_id, current_user={"client": client})

    assert exc.value.status_code == 403
    assert client.storage_calls == []
    assert client.bucket.calls == []


def test_upload_storage_failure_clears_storage_path_and_returns_502(monkeypatch):
    import asyncio
    from io import BytesIO
    from types import SimpleNamespace
    from starlette.datastructures import UploadFile

    document_id = str(uuid4())

    class UploadQuery:
        def __init__(self, parent):
            self.parent = parent
            self.operation = None
            self.payload = None

        def insert(self, payload):
            self.operation = "insert"
            self.payload = payload
            return self

        def update(self, payload):
            self.operation = "update"
            self.payload = payload
            self.parent.cleanup_payloads.append(payload)
            return self

        def eq(self, *_args):
            return self

        def execute(self):
            if self.operation == "insert":
                self.parent.insert_payload = self.payload
                return type("Result", (), {"data": [{"id": document_id}]})()
            return type("Result", (), {"data": []})()

    class FailingStorageBucket:
        def upload(self, *_args, **_kwargs):
            raise RuntimeError("synthetic storage outage")

    class UploadClient:
        def __init__(self):
            self.insert_payload = None
            self.cleanup_payloads = []
            self.bucket = FailingStorageBucket()

        def table(self, _name):
            return UploadQuery(self)

        class Storage:
            def __init__(self, parent):
                self.parent = parent

            def from_(self, _bucket_name):
                return self.parent.bucket

        @property
        def storage(self):
            return self.Storage(self)

    client = UploadClient()
    monkeypatch.setattr(
        "app.api.routes.documents._authorize_department",
        lambda *_args, **_kwargs: str(uuid4()),
    )
    monkeypatch.setattr("app.api.routes.documents.extract_text", lambda *_args: "readable document text")
    monkeypatch.setattr(
        "app.api.routes.documents.classify_document",
        lambda *_args: SimpleNamespace(document_type="financial_report", confidence=0.9, reasons=[]),
    )

    upload = UploadFile(filename="budget.pdf", file=BytesIO(b"%PDF-1.4 test"))

    with pytest.raises(HTTPException) as exc:
        asyncio.run(
            __import__("app.api.routes.documents", fromlist=["classify_uploaded_document"])
            .classify_uploaded_document(
                file=upload,
                department_code="finance",
                current_user={"id": str(uuid4()), "client": client},
            )
        )

    assert exc.value.status_code == 502
    assert client.insert_payload["storage_path"].endswith(".pdf")
    assert client.cleanup_payloads == [{"storage_path": None}]

