from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.routes import conversations


CONVERSATION_ID = UUID("33333333-3333-3333-3333-333333333333")


class Query:
    def __init__(self, client, table):
        self.client = client
        self.table = table
        self.filters = {}

    def select(self, *_args, **_kwargs):
        return self

    def eq(self, key, value):
        self.filters[key] = value
        return self

    def maybe_single(self):
        return self

    def order(self, *_args, **_kwargs):
        return self

    def limit(self, *_args, **_kwargs):
        return self

    def execute(self):
        self.client.calls.append((self.table, dict(self.filters)))
        if self.table == "ai_conversations":
            return SimpleNamespace(data=None)
        pytest.fail("Messages must not be queried when the conversation is inaccessible")


class Client:
    def __init__(self):
        self.calls = []

    def table(self, name):
        return Query(self, name)


def test_inaccessible_conversation_messages_return_404_without_reading_messages():
    client = Client()

    with pytest.raises(HTTPException) as exc:
        conversations.list_messages(
            conversation_id=CONVERSATION_ID,
            current_user={"id": "user-1", "client": client},
        )

    assert exc.value.status_code == 404
    assert [table for table, _ in client.calls] == ["ai_conversations"]
