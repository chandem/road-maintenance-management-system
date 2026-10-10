from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.routes import conversations
from app.schemas.conversations import MessageCreate


CONVERSATION_ID = UUID("44444444-4444-4444-4444-444444444444")


class Query:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.operation = "select"
        self.filters = {}
        self.payload = None

    def select(self, *_args, **_kwargs):
        self.operation = "select"
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
        self.client.calls.append(
            {
                "table": self.table_name,
                "operation": self.operation,
                "filters": dict(self.filters),
                "payload": self.payload,
            }
        )
        if self.table_name == "ai_conversations":
            return SimpleNamespace(data=self.client.conversation)
        if self.table_name == "ai_messages" and self.operation == "insert":
            pytest.fail("No message should be persisted for an inactive conversation")
        return SimpleNamespace(data=[])


class Client:
    def __init__(self, conversation):
        self.conversation = conversation
        self.calls = []

    def table(self, name):
        return Query(self, name)


def test_inactive_conversation_rejects_message_before_trusted_client_or_persistence(monkeypatch):
    client = Client(
        {
            "id": str(CONVERSATION_ID),
            "organization_id": "org-1",
            "status": "archived",
        }
    )

    def trusted_client_must_not_be_requested():
        pytest.fail("Trusted client must not be requested for an archived conversation")

    monkeypatch.setattr(conversations, "get_service_client", trusted_client_must_not_be_requested)

    with pytest.raises(HTTPException) as exc:
        conversations.post_message(
            conversation_id=CONVERSATION_ID,
            body=MessageCreate(content="Check this road."),
            current_user={"id": "user-1", "client": client},
        )

    assert exc.value.status_code == 409
    assert exc.value.detail == "Conversation is not active."
    assert [call["table"] for call in client.calls] == ["ai_conversations"]


def test_missing_conversation_rejects_message_before_trusted_client_or_persistence(monkeypatch):
    client = Client(None)

    def trusted_client_must_not_be_requested():
        pytest.fail("Trusted client must not be requested for a missing conversation")

    monkeypatch.setattr(conversations, "get_service_client", trusted_client_must_not_be_requested)

    with pytest.raises(HTTPException) as exc:
        conversations.post_message(
            conversation_id=CONVERSATION_ID,
            body=MessageCreate(content="Check this road."),
            current_user={"id": "user-1", "client": client},
        )

    assert exc.value.status_code == 404
    assert [call["table"] for call in client.calls] == ["ai_conversations"]
