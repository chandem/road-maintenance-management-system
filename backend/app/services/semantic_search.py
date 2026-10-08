from __future__ import annotations

from dataclasses import dataclass

from app.services.document_embeddings import EmbeddingProviderError, generate_embedding


@dataclass(frozen=True)
class SemanticSearchMatch:
    chunk_id: str
    document_id: str
    content: str
    similarity: float


def build_embedding_query(
    query: str,
    *,
    limit: int = 5,
    minimum_similarity: float = 0.0,
) -> tuple[list[float], int, float] | None:
    """Create the vector-search inputs for a document query."""
    normalized = query.strip()
    if not normalized:
        return None
    if limit < 1:
        raise ValueError("limit must be positive")
    if not 0.0 <= minimum_similarity <= 1.0:
        raise ValueError("minimum_similarity must be between 0 and 1")

    try:
        result = generate_embedding(normalized)
    except EmbeddingProviderError:
        return None

    if result is None:
        return None

    return result.values, min(limit, 50), minimum_similarity
