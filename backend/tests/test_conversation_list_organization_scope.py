from types import SimpleNamespace

from app.api.routes import conversations


class Query:
    def __init__(self, client):
        self.client = client
        self.filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        self.client.filters = dict(self.filters)
        return SimpleNamespace(data=[])


class Client:
    def __init__(self):
        self.filters = None

    def table(self, name):
        assert name == "ai_conversations"
        return Query(self)


def test_conversation_list_queries_organization_and_leaves_row_filtering_to_rls(monkeypatch):
    client = Client()
    monkeypatch.setattr(conversations, "_org_id", lambda _user: "org-1")

    result = conversations.list_conversations(
        current_user={"id": "admin-user", "client": client},
        limit=20,
    )

    assert result == []
    assert client.filters == {"organization_id": "org-1"}
    assert "created_by" not in client.filters
