from types import SimpleNamespace

from app.api.routes import documents as document_routes
from app.schemas.documents import SemanticSearchRequest
from app.services.semantic_search import SemanticSearchMatch


class FakeDocumentQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, key, values):
        self.filters[key] = list(values)
        return self

    def execute(self):
        rows = self.rows
        if "organization_id" in self.filters:
            rows = [
                row for row in rows
                if str(row.get("organization_id")) == str(self.filters["organization_id"])
            ]
        if "id" in self.filters:
            allowed = {str(value) for value in self.filters["id"]}
            rows = [row for row in rows if str(row.get("id")) in allowed]
        return SimpleNamespace(data=rows)


class FakeClient:
    def __init__(self, rows):
        self.query = FakeDocumentQuery(rows)

    def table(self, name):
        assert name == "documents"
        return self.query


def _match(document_id: str, content: str) -> SemanticSearchMatch:
    return SemanticSearchMatch(
        chunk_id=f"chunk-{document_id}",
        document_id=document_id,
        content=content,
        similarity=0.9,
    )


def test_semantic_search_returns_only_requested_department_evidence(monkeypatch):
    client = FakeClient([
        {"id": "road-doc", "organization_id": "org-1", "department_code": "road_asset", "title": "Road plan", "document_type": "plan"},
        {"id": "finance-doc", "organization_id": "org-1", "department_code": "finance", "title": "Finance report", "document_type": "report"},
        {"id": "legacy-doc", "organization_id": "org-1", "department_code": None, "title": "Legacy file", "document_type": "unknown"},
        {"id": "foreign-doc", "organization_id": "org-2", "department_code": "road_asset", "title": "Foreign road plan", "document_type": "plan"},
    ])
    monkeypatch.setattr(
        document_routes,
        "_authorize_department",
        lambda _user, department_code: "org-1" if department_code == "road_asset" else (_ for _ in ()).throw(AssertionError("unexpected department")),
    )
    monkeypatch.setattr(
        document_routes,
        "search_document_chunks",
        lambda *args, **kwargs: [
            _match("road-doc", "ROAD_ALLOWED_CONTENT"),
            _match("finance-doc", "FINANCE_SECRET_CONTENT"),
            _match("legacy-doc", "LEGACY_SECRET_CONTENT"),
            _match("foreign-doc", "FOREIGN_ORG_SECRET_CONTENT"),
            _match("missing-doc", "MISSING_METADATA_SECRET_CONTENT"),
        ],
    )
    user = {"id": "road-user", "access_token": "jwt", "client": client}

    response = document_routes.semantic_search_documents(
        SemanticSearchRequest(query="road maintenance", department_code="road_asset"),
        current_user=user,
    )

    assert response.match_count == 1
    assert response.matches[0].document_id == "road-doc"
    assert response.matches[0].content == "ROAD_ALLOWED_CONTENT"
    serialized = str(response.model_dump())
    for secret in (
        "FINANCE_SECRET_CONTENT",
        "LEGACY_SECRET_CONTENT",
        "FOREIGN_ORG_SECRET_CONTENT",
        "MISSING_METADATA_SECRET_CONTENT",
    ):
        assert secret not in serialized


def test_semantic_search_fails_closed_when_department_is_not_authorized(monkeypatch):
    def deny_department(_user, _department_code):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Department access denied")

    monkeypatch.setattr(document_routes, "_authorize_department", deny_department)
    monkeypatch.setattr(
        document_routes,
        "search_document_chunks",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("retrieval must not run")),
    )

    user = {"id": "finance-user", "access_token": "jwt", "client": FakeClient([])}

    try:
        document_routes.semantic_search_documents(
            SemanticSearchRequest(query="road maintenance", department_code="road_asset"),
            current_user=user,
        )
    except Exception as exc:
        assert getattr(exc, "status_code", None) == 403
    else:
        raise AssertionError("Unauthorized department search must be rejected")
