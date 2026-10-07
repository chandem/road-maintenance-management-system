from types import SimpleNamespace

import pytest

from app.services.document_embeddings import (
    EmbeddingProviderError,
    generate_embedding,
    generate_embeddings,
)


def test_empty_text_returns_no_embedding():
    assert generate_embedding("   ") is None


def test_missing_api_key_returns_no_embedding(monkeypatch):
    monkeypatch.setattr(
        "app.services.document_embeddings.get_settings",
        lambda: SimpleNamespace(gemini_api_key=None),
    )
    assert generate_embedding("Road maintenance") is None


def test_invalid_dimension_is_rejected():
    with pytest.raises(ValueError):
        generate_embedding("Road maintenance", output_dimensionality=0)


def test_embedding_response_is_normalized(monkeypatch):
    class FakeClient:
        class Models:
            def embed_content(self, **kwargs):
                assert kwargs["model"] == "gemini-embedding-2"
                assert kwargs["contents"] == "Road maintenance"
                return SimpleNamespace(
                    embeddings=[SimpleNamespace(values=[0.1, 0.2, 0.3])]
                )

        models = Models()

    class FakeGenAI:
        Client = lambda **kwargs: FakeClient()

    class FakeTypes:
        class EmbedContentConfig:
            def __init__(self, **kwargs):
                assert kwargs["output_dimensionality"] == 768

    import sys

    monkeypatch.setitem(sys.modules, "google.genai", FakeGenAI)
    monkeypatch.setitem(sys.modules, "google.genai.types", FakeTypes)
    monkeypatch.setattr(
        "app.services.document_embeddings.get_settings",
        lambda: SimpleNamespace(gemini_api_key="test-key"),
    )

    result = generate_embedding("Road maintenance")
    assert result is not None
    assert result.values == [0.1, 0.2, 0.3]
    assert result.dimension == 3
    assert result.provider == "gemini"


def test_provider_failure_is_wrapped(monkeypatch):
    class FakeClient:
        class Models:
            def embed_content(self, **kwargs):
                raise RuntimeError("provider unavailable")

        models = Models()

    class FakeGenAI:
        Client = lambda **kwargs: FakeClient()

    class FakeTypes:
        class EmbedContentConfig:
            def __init__(self, **kwargs):
                pass

    import sys

    monkeypatch.setitem(sys.modules, "google.genai", FakeGenAI)
    monkeypatch.setitem(sys.modules, "google.genai.types", FakeTypes)
    monkeypatch.setattr(
        "app.services.document_embeddings.get_settings",
        lambda: SimpleNamespace(gemini_api_key="test-key"),
    )

    with pytest.raises(EmbeddingProviderError):
        generate_embedding("Road maintenance")


def test_batch_preserves_input_order(monkeypatch):
    monkeypatch.setattr(
        "app.services.document_embeddings.generate_embedding",
        lambda text, **kwargs: None if not text.strip() else SimpleNamespace(values=[1.0]),
    )
    result = generate_embeddings(["first", " ", "third"])
    assert len(result) == 3
    assert result[0].values == [1.0]
    assert result[1] is None
    assert result[2].values == [1.0]
