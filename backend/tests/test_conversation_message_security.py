from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException

from app.api.routes import conversations
from app.schemas.conversations import MessageCreate


CONVERSATION_ID = UUID("11111111-1111-1111-1111-111111111111")


class FakeQuery:
    def __init__(self, client, table):
        self.client = client
        self.table_name = table
        self.operation = "select"
        self.payload = None
        self.filters = {}

    def select(self, *_args, **_kwargs):
        self.operation = "select"
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

    def insert(self, payload):
        self.operation = "insert"
        self.payload = payload
        return self

    def update(self, payload):
        self.operation = "update"
        self.payload = payload
        return self

    def execute(self):
        self.client.calls.append({
            "table": self.table_name,
            "operation": self.operation,
            "payload": self.payload,
            "filters": dict(self.filters),
        })
        if (
            self.table_name in self.client.fail_count_tables
            and self.operation == "select"
        ):
            raise RuntimeError(f"{self.table_name} count query failed")
        if (
            self.client.fail_assistant_insert
            and self.table_name == "ai_messages"
            and self.operation == "insert"
            and self.payload.get("role") == "assistant"
        ):
            raise RuntimeError("assistant message insert failed")
        if (
            self.client.fail_timestamp_update
            and self.table_name == "ai_conversations"
            and self.operation == "update"
        ):
            raise RuntimeError("timestamp update failed")
        if self.table_name == "ai_conversations" and self.operation == "select":
            return SimpleNamespace(data={
                "id": str(CONVERSATION_ID),
                "organization_id": "org-1",
                "status": "active",
            })
        if self.table_name == "ai_messages" and self.operation == "insert":
            row = {
                "id": f"message-{len(self.client.calls)}",
                "conversation_id": str(CONVERSATION_ID),
                **self.payload,
            }
            return SimpleNamespace(data=[row])
        return SimpleNamespace(data=[], count=0)


class FakeClient:
    def __init__(self):
        self.calls = []
        self.fail_count_tables = set()
        self.fail_timestamp_update = False
        self.fail_assistant_insert = False

    def table(self, name):
        return FakeQuery(self, name)


def test_user_message_uses_user_client_and_assistant_uses_trusted_client(monkeypatch):
    user_client = FakeClient()
    trusted_client = FakeClient()
    monkeypatch.setattr(conversations, "get_service_client", lambda: trusted_client)
    monkeypatch.setattr(conversations, "generate_text", lambda _prompt: None)

    result = conversations.post_message(
        conversation_id=CONVERSATION_ID,
        body=MessageCreate(content="What is the road condition?"),
        current_user={"id": "user-1", "client": user_client},
    )

    user_inserts = [
        call for call in user_client.calls
        if call["table"] == "ai_messages" and call["operation"] == "insert"
    ]
    trusted_inserts = [
        call for call in trusted_client.calls
        if call["table"] == "ai_messages" and call["operation"] == "insert"
    ]

    assert len(user_inserts) == 1
    assert user_inserts[0]["payload"]["role"] == "user"
    assert len(trusted_inserts) == 1
    assert trusted_inserts[0]["payload"]["role"] == "assistant"
    assert result["role"] == "assistant"

    timestamp_updates = [
        call for call in trusted_client.calls
        if call["table"] == "ai_conversations" and call["operation"] == "update"
    ]
    assert len(timestamp_updates) == 1
    updated_at = datetime.fromisoformat(timestamp_updates[0]["payload"]["updated_at"])
    assert updated_at.tzinfo is not None
    assert updated_at.utcoffset().total_seconds() == 0


def test_missing_trusted_client_fails_before_persisting_user_message(monkeypatch):
    user_client = FakeClient()

    def missing_service_client():
        raise RuntimeError("service role is not configured")

    monkeypatch.setattr(conversations, "get_service_client", missing_service_client)

    with pytest.raises(HTTPException) as exc:
        conversations.post_message(
            conversation_id=CONVERSATION_ID,
            body=MessageCreate(content="Check this road."),
            current_user={"id": "user-1", "client": user_client},
        )

    assert exc.value.status_code == 503
    assert not any(
        call["table"] == "ai_messages" and call["operation"] == "insert"
        for call in user_client.calls
    )



def test_count_query_failure_is_reported_as_unavailable_without_failing_turn(monkeypatch):
    user_client = FakeClient()
    user_client.fail_count_tables.add("roads")
    trusted_client = FakeClient()
    captured_prompts = []

    monkeypatch.setattr(conversations, "get_service_client", lambda: trusted_client)
    monkeypatch.setattr(
        conversations,
        "generate_text",
        lambda prompt: (captured_prompts.append(prompt) or None),
    )

    result = conversations.post_message(
        conversation_id=CONVERSATION_ID,
        body=MessageCreate(content="Summarize the road network."),
        current_user={"id": "user-1", "client": user_client},
    )

    assert len(captured_prompts) == 1
    assert "Roads: unavailable" in captured_prompts[0]
    assert "Roads: 0" not in captured_prompts[0]
    assert "Sections: 0" in captured_prompts[0]
    assert "Work orders: 0" in captured_prompts[0]
    assert result["role"] == "assistant"
    assert any(
        call["table"] == "ai_messages"
        and call["operation"] == "insert"
        and call["payload"]["role"] == "user"
        for call in user_client.calls
    )



def test_ai_provider_exception_returns_saved_fallback_reply(monkeypatch):
    user_client = FakeClient()
    trusted_client = FakeClient()

    monkeypatch.setattr(conversations, "get_service_client", lambda: trusted_client)

    def provider_failure(_prompt):
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(conversations, "generate_text", provider_failure)

    result = conversations.post_message(
        conversation_id=CONVERSATION_ID,
        body=MessageCreate(content="What should we inspect?"),
        current_user={"id": "user-1", "client": user_client},
    )

    assert result["role"] == "assistant"
    assert result["model"] is None
    assert "temporarily unavailable" in result["content"]
    assert any(
        call["table"] == "ai_messages"
        and call["operation"] == "insert"
        and call["payload"]["role"] == "user"
        for call in user_client.calls
    )
    assert any(
        call["table"] == "ai_messages"
        and call["operation"] == "insert"
        and call["payload"]["role"] == "assistant"
        for call in trusted_client.calls
    )


def test_timestamp_update_failure_does_not_hide_saved_assistant_reply(monkeypatch):
    user_client = FakeClient()
    trusted_client = FakeClient()
    trusted_client.fail_timestamp_update = True

    monkeypatch.setattr(conversations, "get_service_client", lambda: trusted_client)
    monkeypatch.setattr(conversations, "generate_text", lambda _prompt: None)

    result = conversations.post_message(
        conversation_id=CONVERSATION_ID,
        body=MessageCreate(content="Give me a brief update."),
        current_user={"id": "user-1", "client": user_client},
    )

    assert result["role"] == "assistant"
    assert any(
        call["table"] == "ai_messages"
        and call["operation"] == "insert"
        and call["payload"]["role"] == "assistant"
        for call in trusted_client.calls
    )



def test_assistant_storage_failure_returns_clear_recovery_message(monkeypatch):
    user_client = FakeClient()
    trusted_client = FakeClient()
    trusted_client.fail_assistant_insert = True

    monkeypatch.setattr(conversations, "get_service_client", lambda: trusted_client)
    monkeypatch.setattr(conversations, "generate_text", lambda _prompt: None)

    with pytest.raises(HTTPException) as exc:
        conversations.post_message(
            conversation_id=CONVERSATION_ID,
            body=MessageCreate(content="Check road maintenance status."),
            current_user={"id": "user-1", "client": user_client},
        )

    assert exc.value.status_code == 503
    assert "Your message was saved" in exc.value.detail
    assert "Refresh the conversation" in exc.value.detail
    assert any(
        call["table"] == "ai_messages"
        and call["operation"] == "insert"
        and call["payload"]["role"] == "user"
        for call in user_client.calls
    )
    assert any(
        call["table"] == "ai_messages"
        and call["operation"] == "insert"
        and call["payload"]["role"] == "assistant"
        for call in trusted_client.calls
    )
