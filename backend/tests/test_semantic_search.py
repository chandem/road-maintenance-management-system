from types import SimpleNamespace

import pytest

from app.services.semantic_search import build_embedding_query


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
