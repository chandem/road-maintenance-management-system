from types import SimpleNamespace

import pytest

from app.services.semantic_search import (
    build_embedding_query,
    search_document_chunks,
)


def test_empty_query_returns_none(monkeypatch):
    monkeypatch.setattr(
        "app.services.semantic_search.generate_embedding",
        lambda text: None,
    )
    assert build_embedding_query("   ") is None


def test_embedding_query_returns_vector_and_limits(monkeypatch):
    monkeypatch.setattr(
        "app.services.semantic_search.generate_embedding",
        lambda text: SimpleNamespace(values=[0.1, 0.2, 0.3]),
    )

    result = build_embedding_query("Which road needs maintenance?", limit=60)

    assert result == ([0.1, 0.2, 0.3], 50, 0.0)


def test_similarity_range_is_validated(monkeypatch):
    monkeypatch.setattr(
        "app.services.semantic_search.generate_embedding",
        lambda text: SimpleNamespace(values=[0.1]),
    )

    with pytest.raises(ValueError):
        build_embedding_query("road", minimum_similarity=1.1)


def test_provider_failure_returns_none(monkeypatch):
    from app.services.document_embeddings import EmbeddingProviderError

    def fail(text):
        raise EmbeddingProviderError("unavailable")

    monkeypatch.setattr("app.services.semantic_search.generate_embedding", fail)

    assert build_embedding_query("road") is None


def test_search_document_chunks_calls_org_scoped_rpc(monkeypatch):
    monkeypatch.setattr(
        "app.services.semantic_search.generate_embedding",
        lambda text: SimpleNamespace(values=[0.1, 0.2, 0.3]),
    )

    calls = []

    class FakeRpc:
        def execute(self):
            return SimpleNamespace(
                data=[
                    {
                        "id": "chunk-1",
                        "document_id": "document-1",
                        "content": "The Soda-Shakiso road requires grading.",
                        "similarity": 0.91,
                    }
                ]
            )

    class FakeClient:
        def rpc(self, name, params):
            calls.append((name, params))
            return FakeRpc()

    monkeypatch.setattr(
        "app.services.semantic_search.get_supabase_client",
        lambda token: FakeClient(),
    )

    result = search_document_chunks(
        "road maintenance",
        organization_id="org-1",
        access_token="token-1",
        limit=3,
        minimum_similarity=0.75,
    )

    assert result[0].chunk_id == "chunk-1"
    assert result[0].document_id == "document-1"
    assert result[0].similarity == 0.91
    assert calls == [
        (
            "match_document_chunks",
            {
                "query_embedding": [0.1, 0.2, 0.3],
                "match_threshold": 0.75,
                "match_count": 3,
                "filter_organization_id": "org-1",
            },
        )
    ]
