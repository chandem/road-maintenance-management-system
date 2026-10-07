from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class DocumentChunk:
    """A searchable, evidence-preserving section of extracted document text."""

    chunk_index: int
    text: str
    start_char: int
    end_char: int


def _normalize_text(text: str) -> str:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_document_text(
    text: str,
    *,
    max_chars: int = 1600,
    overlap_chars: int = 200,
) -> list[DocumentChunk]:
    """Split extracted document text into bounded, overlapping chunks.

    Paragraph boundaries are preferred when possible. Character offsets are
    retained so retrieved chunks can always be traced back to source text.
    """

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    if overlap_chars < 0 or overlap_chars >= max_chars:
        raise ValueError("overlap_chars must be >= 0 and smaller than max_chars")

    normalized = _normalize_text(text)
    if not normalized:
        return []

    chunks: list[DocumentChunk] = []
    start = 0
    text_length = len(normalized)

    while start < text_length:
        remaining = normalized[start:]
        if len(remaining) <= max_chars:
            end = text_length
        else:
            candidate_end = start + max_chars
            boundary = normalized.rfind("\n\n", start, candidate_end + 1)
            if boundary > start:
                end = boundary
            else:
                space_boundary = normalized.rfind(" ", start, candidate_end + 1)
                end = space_boundary if space_boundary > start else candidate_end

        chunk_text = normalized[start:end].strip()
        if chunk_text:
            actual_start = start
            actual_end = end
            chunks.append(
                DocumentChunk(
                    chunk_index=len(chunks),
                    text=chunk_text,
                    start_char=actual_start,
                    end_char=actual_end,
                )
            )

        if end >= text_length:
            break

        next_start = max(end - overlap_chars, start + 1)
        while next_start < text_length and normalized[next_start].isspace():
            next_start += 1
        start = next_start

    return chunks
