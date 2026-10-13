from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.routes import conversations
from app.schemas.conversations import MessageCreate


CONVERSATION_ID = UUID("22222222-2222-2222-2222-222222222222")


class Query:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.filters = {}
        self.operation = "select"

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def maybe_single(self):
        return self

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def execute(self):
        self.client.calls.append((self.table, self.operation, dict(self.filters)))
        if self.table == "ai_conversations" and self.operation == "select":
            if not self.client.conversation:
                return SimpleNamespace(data=None)
            return SimpleNamespace(data={
                "id": str(CONVERSATION_ID),
                "organization_id": "org-1",
                "status": self.client.status,
            })
        return SimpleNamespace(data=[])


class Client:
    def __init__(self, *, conversation=True, status="active"):
        self.conversation = conversation
        self.status = status
        self.calls = []

    def table(self, name):
        return Query(self, name)


def _post(client, monkeypatch):
    monkeypatch.setattr(
        conversations,
        "get_service_client",
        lambda: pytest.fail("trusted client must not be requested before conversation authorization"),
    )
    return conversations.post_message(
        conversation_id=CONVERSATION_ID,
        body=MessageCreate(content="Please summarize the road condition."),
        current_user={"id": "user-1", "client": client},
    )


def test_inaccessible_conversation_returns_not_found_before_any_message_write(monkeypatch):
    client = Client(conversation=False)

    with pytest.raises(HTTPException) as exc:
        _post(client, monkeypatch)

    assert exc.value.status_code == 404
    assert not any(table == "ai_messages" for table, _, _ in client.calls)


def test_closed_conversation_rejects_message_before_any_message_write(monkeypatch):
    client = Client(status="closed")

    with pytest.raises(HTTPException) as exc:
        _post(client, monkeypatch)

    assert exc.value.status_code == 409
    assert not any(table == "ai_messages" for table, _, _ in client.calls)
