from types import SimpleNamespace

from app.api.routes.ai import _road_document_evidence
from app.services.semantic_search import SemanticSearchMatch


class FakeDocumentQuery:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def in_(self, key, values):
        self.filters[key] = values
        return self

    def execute(self):
        if self.error:
            raise self.error
        return SimpleNamespace(data=[
            row for row in self.rows
            if str(row.get("organization_id")) == str(self.filters.get("organization_id"))
            and str(row.get("id")) in {str(value) for value in self.filters.get("id", [])}
        ])


class FakeClient:
    def __init__(self, rows=None, error=None):
        self.query = FakeDocumentQuery(rows, error)

    def table(self, name):
        assert name == "documents"
        return self.query


def _match(document_id, content):
    return SemanticSearchMatch(
        chunk_id=f"chunk-{document_id}",
        document_id=document_id,
        content=content,
        similarity=0.91,
    )


def _setup(monkeypatch, matches, client):
    monkeypatch.setattr(
        "app.api.routes.ai.search_document_chunks",
        lambda *args, **kwargs: matches,
    )
    user = {"id": "user-1", "access_token": "user-jwt", "client": client}
    return _road_document_evidence(client, user, "org-1", "road maintenance")


def test_road_priority_includes_only_verified_road_department_documents(monkeypatch):
    client = FakeClient([
        {"id": "road-doc", "organization_id": "org-1", "department_code": "road_asset"},
        {"id": "finance-doc", "organization_id": "org-1", "department_code": "finance"},
        {"id": "hr-doc", "organization_id": "org-1", "department_code": "human_resources"},
        {"id": "legacy-doc", "organization_id": "org-1", "department_code": None},
        {"id": "other-org-doc", "organization_id": "org-2", "department_code": "road_asset"},
    ])
    matches = [
        _match("road-doc", "ROAD_SAFE_SNIPPET"),
        _match("finance-doc", "FINANCE_SECRET_SNIPPET"),
        _match("hr-doc", "HR_SECRET_SNIPPET"),
        _match("legacy-doc", "UNCLASSIFIED_SNIPPET"),
        _match("other-org-doc", "OTHER_ORG_SNIPPET"),
        _match("missing-doc", "MISSING_METADATA_SNIPPET"),
    ]

    evidence = _setup(monkeypatch, matches, client)

    assert len(evidence) == 1
    assert "ROAD_SAFE_SNIPPET" in evidence[0]
    assert all(
        secret not in " ".join(evidence)
        for secret in (
            "FINANCE_SECRET_SNIPPET",
            "HR_SECRET_SNIPPET",
            "UNCLASSIFIED_SNIPPET",
            "OTHER_ORG_SNIPPET",
            "MISSING_METADATA_SNIPPET",
        )
    )


def test_road_priority_returns_no_evidence_when_metadata_lookup_fails(monkeypatch):
    client = FakeClient(error=RuntimeError("database unavailable"))
    evidence = _setup(
        monkeypatch,
        [_match("road-doc", "DO_NOT_RETURN_WITHOUT_METADATA")],
        client,
    )

    assert evidence == []


def test_road_priority_returns_no_evidence_without_user_access_token(monkeypatch):
    client = FakeClient([
        {"id": "road-doc", "organization_id": "org-1", "department_code": "road_asset"},
    ])
    monkeypatch.setattr(
        "app.api.routes.ai.search_document_chunks",
        lambda *args, **kwargs: [_match("road-doc", "ROAD_SAFE_SNIPPET")],
    )

    evidence = _road_document_evidence(
        client, {"id": "user-1", "client": client}, "org-1", "road maintenance"
    )

    assert evidence == []
