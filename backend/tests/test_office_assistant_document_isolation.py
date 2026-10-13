from types import SimpleNamespace

from app.api.routes import ai
from app.schemas.office_assistant import OfficeAssistantRequest
from app.services.cross_module_context import CrossModuleContext
from app.services.semantic_search import SemanticSearchMatch


class DocumentQuery:
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
            ids = {str(value) for value in self.filters["id"]}
            rows = [row for row in rows if str(row.get("id")) in ids]
        return SimpleNamespace(data=rows)


class Client:
    def __init__(self, rows):
        self.query = DocumentQuery(rows)

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


def test_office_assistant_only_sends_verified_same_org_document_evidence(monkeypatch):
    client = Client([
        {"id": "same-org-doc", "organization_id": "org-1"},
        {"id": "foreign-doc", "organization_id": "org-2"},
    ])
    monkeypatch.setattr(ai, "collect_cross_module_context", lambda *_args, **_kwargs: CrossModuleContext())
    monkeypatch.setattr(ai, "_best_effort_organization_id", lambda *_args: "org-1")
    monkeypatch.setattr(
        ai,
        "search_document_chunks",
        lambda *_args, **_kwargs: [
            _match("same-org-doc", "VERIFIED_DOCUMENT_SNIPPET"),
            _match("foreign-doc", "CROSS_ORG_SECRET"),
            _match("missing-doc", "MISSING_PARENT_SECRET"),
        ],
    )
    monkeypatch.setattr(ai, "get_settings", lambda: SimpleNamespace(gemini_api_key=None))

    response = ai.office_assistant(
        OfficeAssistantRequest(question="Summarize the maintenance plan"),
        current_user={"id": "admin-1", "client": client, "access_token": "jwt"},
    )

    assert len(response.document_evidence) == 1
    assert "VERIFIED_DOCUMENT_SNIPPET" in response.document_evidence[0]
    serialized = str(response.model_dump())
    assert "CROSS_ORG_SECRET" not in serialized
    assert "MISSING_PARENT_SECRET" not in serialized


def test_office_assistant_fails_closed_when_document_metadata_lookup_fails(monkeypatch):
    class FailingClient(Client):
        def table(self, name):
            raise RuntimeError("metadata database unavailable")

    client = FailingClient([])
    monkeypatch.setattr(ai, "collect_cross_module_context", lambda *_args, **_kwargs: CrossModuleContext())
    monkeypatch.setattr(ai, "_best_effort_organization_id", lambda *_args: "org-1")
    monkeypatch.setattr(
        ai,
        "search_document_chunks",
        lambda *_args, **_kwargs: [_match("same-org-doc", "DO_NOT_SEND_UNVERIFIED")],
    )
    monkeypatch.setattr(ai, "get_settings", lambda: SimpleNamespace(gemini_api_key=None))

    response = ai.office_assistant(
        OfficeAssistantRequest(question="Summarize the maintenance plan"),
        current_user={"id": "admin-1", "client": client, "access_token": "jwt"},
    )

    assert response.document_evidence == []
    assert "DO_NOT_SEND_UNVERIFIED" not in str(response.model_dump())
