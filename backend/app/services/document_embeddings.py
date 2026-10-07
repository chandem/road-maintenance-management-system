from __future__ import annotations

from dataclasses import dataclass

from app.core.config import get_settings


DEFAULT_EMBEDDING_MODEL = "gemini-embedding-2"
DEFAULT_OUTPUT_DIMENSIONALITY = 768


@dataclass(frozen=True)
class EmbeddingResult:
    values: list[float]
    model: str
    dimension: int
    provider: str


class EmbeddingProviderError(Exception):
    """Raised when an embedding provider cannot generate a valid embedding."""


def generate_embedding(
    text: str,
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    output_dimensionality: int = DEFAULT_OUTPUT_DIMENSIONALITY,
) -> EmbeddingResult | None:
    """Generate a semantic embedding for one document chunk.

    Returns None when Gemini is not configured so local tests and ingestion can
    remain usable without an external AI service.
    """

    normalized = text.strip()
    if not normalized:
        return None

    if output_dimensionality <= 0:
        raise ValueError("output_dimensionality must be positive")

    settings = get_settings()
    if not settings.gemini_api_key:
        return None

    try:
        from google import genai

        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.embed_content(
            model=model,
            contents=normalized,
            config=genai.types.EmbedContentConfig(
                output_dimensionality=output_dimensionality,
            ),
        )
        embeddings = response.embeddings or []
        if not embeddings or not embeddings[0].values:
            raise EmbeddingProviderError("Embedding provider returned no vector.")

        values = [float(value) for value in embeddings[0].values]
        return EmbeddingResult(
            values=values,
            model=model,
            dimension=len(values),
            provider="gemini",
        )
    except EmbeddingProviderError:
        raise
    except Exception as exc:
        raise EmbeddingProviderError("Failed to generate document embedding.") from exc


def generate_embeddings(
    texts: list[str],
    *,
    model: str = DEFAULT_EMBEDDING_MODEL,
    output_dimensionality: int = DEFAULT_OUTPUT_DIMENSIONALITY,
) -> list[EmbeddingResult | None]:
    """Generate embeddings independently for a batch of document chunks."""

    return [
        generate_embedding(
            text,
            model=model,
            output_dimensionality=output_dimensionality,
        )
        for text in texts
    ]
