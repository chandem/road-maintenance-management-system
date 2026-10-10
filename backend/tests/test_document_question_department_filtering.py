from types import SimpleNamespace

from app.api.routes import documents as document_routes
from app.schemas.documents import DocumentQuestionRequest
from app.services.semantic_search import SemanticSearchMatch


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows
        self.filters = {}
        self.limit_count = None

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, key, values):
        self.filters[key] = list(values)
        return self

    def or_(self, _expression):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, count):
        self.limit_count = count
        return self

    def execute(self):
        rows = self.rows
        if "organization_id" in self.filters:
            rows = [r for r in rows if str(r.get("organization_id")) == str(self.filters["organization_id"])]
        if "id" in self.filters:
            ids = {str(v) for v in self.filters["id"]}
            rows = [r for r in rows if str(r.get("id")) in ids]
        if "department_code" in self.filters:
            rows = [r for r in rows if r.get("department_code") == self.filters["department_code"]]
        if "document_type" in self.filters:
            rows = [r for r in rows if r.get("document_type") == self.filters["document_type"]]
        return SimpleNamespace(data=rows[:self.limit_count] if self.limit_count else rows)


class FakeClient:
    def __init__(self, rows):
        self.query = FakeQuery(rows)

    def table(self, name):
        assert name == "documents"
        return self.query


def _match(document_id, content):
    return SemanticSearchMatch(
        chunk_id=f"chunk-{document_id}",
        document_id=document_id,
        content=content,
        similarity=0.88,
    )


def _documents():
    return [
        {"id": "road-doc", "organization_id": "org-1", "department_code": "road_asset", "title": "Road plan", "document_type": "plan", "extracted_text": "Road maintenance plan evidence"},
        {"id": "finance-doc", "organization_id": "org-1", "department_code": "finance", "title": "Finance report", "document_type": "report", "extracted_text": "Finance confidential evidence"},
        {"id": "legacy-doc", "organization_id": "org-1", "department_code": None, "title": "Legacy file", "document_type": "plan", "extracted_text": "Unclassified confidential evidence"},
        {"id": "foreign-doc", "organization_id": "org-2", "department_code": "road_asset", "title": "Foreign plan", "document_type": "plan", "extracted_text": "Other organization evidence"},
    ]


def test_document_question_semantic_evidence_is_department_filtered(monkeypatch):
    client = FakeClient(_documents())
    monkeypatch.setattr(
        document_routes,
        "_authorize_department",
        lambda _user, department_code: "org-1" if department_code == "road_asset" else (_ for _ in ()).throw(AssertionError("wrong department")),
    )
    monkeypatch.setattr(
        document_routes,
        "search_document_chunks",
        lambda *args, **kwargs: [
            _match("road-doc", "ROAD_ALLOWED_EVIDENCE"),
            _match("finance-doc", "FINANCE_SECRET_EVIDENCE"),
            _match("legacy-doc", "LEGACY_SECRET_EVIDENCE"),
            _match("foreign-doc", "FOREIGN_SECRET_EVIDENCE"),
            _match("missing-doc", "MISSING_METADATA_EVIDENCE"),
        ],
    )
    monkeypatch.setattr(document_routes, "get_settings", lambda: SimpleNamespace(gemini_api_key=""))
    user = {"id": "road-user", "access_token": "jwt", "client": client}

    response = document_routes.ask_document_question(
        DocumentQuestionRequest(question="What is the road maintenance plan?", department_code="road_asset"),
        current_user=user,
    )

    assert [item.document_id for item in response.evidence] == ["road-doc"]
    serialized = str(response.model_dump())
    for secret in (
        "FINANCE_SECRET_EVIDENCE",
        "LEGACY_SECRET_EVIDENCE",
        "FOREIGN_SECRET_EVIDENCE",
        "MISSING_METADATA_EVIDENCE",
    ):
        assert secret not in serialized


def test_document_question_keyword_fallback_keeps_department_filter(monkeypatch):
    client = FakeClient(_documents())
    monkeypatch.setattr(
        document_routes,
        "_authorize_department",
        lambda _user, department_code: "org-1" if department_code == "road_asset" else (_ for _ in ()).throw(AssertionError("wrong department")),
    )
    monkeypatch.setattr(
        document_routes,
        "search_document_chunks",
        lambda *args, **kwargs: [],
    )
    monkeypatch.setattr(document_routes, "get_settings", lambda: SimpleNamespace(gemini_api_key=""))
    user = {"id": "road-user", "access_token": "jwt", "client": client}

    response = document_routes.ask_document_question(
        DocumentQuestionRequest(question="maintenance plan", department_code="road_asset"),
        current_user=user,
    )

    assert all(item.document_id == "road-doc" for item in response.evidence)
    serialized = str(response.model_dump())
    assert "Finance report" not in serialized
    assert "Legacy file" not in serialized
    assert "Foreign plan" not in serialized
