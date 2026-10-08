from __future__ import annotations

from dataclasses import dataclass

from app.services.document_chunking import chunk_document_text
from app.services.document_embeddings import generate_embeddings


@dataclass(frozen=True)
class DocumentIngestionResult:
    chunk_count: int
    embedded_count: int
    embedding_status: str


def ingest_document_chunks(
    client,
    *,
    document_id: str,
    organization_id: str,
    extracted_text: str,
) -> DocumentIngestionResult:
    """Chunk a document and persist embeddings when the provider is available."""
    chunks = chunk_document_text(extracted_text)
    if not chunks:
        return DocumentIngestionResult(0, 0, "empty")

    embeddings = generate_embeddings([chunk.text for chunk in chunks])
    rows = []

    for chunk, embedding in zip(chunks, embeddings):
        row = {
            "document_id": document_id,
            "organization_id": organization_id,
            "chunk_index": chunk.chunk_index,
            "content": chunk.text,
            "start_char": chunk.start_char,
            "end_char": chunk.end_char,
            "embedding_status": "pending",
        }
        if embedding is not None:
            row.update(
                {
                    "embedding": embedding.values,
                    "embedding_model": embedding.model,
                    "embedding_provider": embedding.provider,
                    "embedding_dimension": embedding.dimension,
                    "embedding_status": "completed",
                }
            )
        rows.append(row)

    client.table("document_chunks").upsert(
        rows,
        on_conflict="document_id,chunk_index",
    ).execute()

    embedded_count = sum(1 for item in embeddings if item is not None)
    status = "completed" if embedded_count == len(chunks) else "pending"

    return DocumentIngestionResult(
        chunk_count=len(chunks),
        embedded_count=embedded_count,
        embedding_status=status,
    )
