from types import SimpleNamespace

from app.services.document_ingestion import ingest_document_chunks


def test_ingest_document_chunks_persists_embedded_chunks(monkeypatch):
    monkeypatch.setattr(
        "app.services.document_ingestion.generate_embeddings",
        lambda texts: [
            SimpleNamespace(
                values=[0.1, 0.2],
                model="gemini-embedding-2",
                provider="gemini",
                dimension=2,
            )
            for _ in texts
        ],
    )

    calls = []

    class FakeTable:
        def upsert(self, rows, on_conflict):
            calls.append((rows, on_conflict))
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    class FakeClient:
        def table(self, name):
            assert name == "document_chunks"
            return FakeTable()

    result = ingest_document_chunks(
        FakeClient(),
        document_id="doc-1",
        organization_id="org-1",
        extracted_text="Road maintenance is required.\n\nPriority is high.",
    )

    assert result.chunk_count == 1
    assert result.embedded_count == 1
    assert result.embedding_status == "completed"
    assert calls[0][1] == "document_id,chunk_index"
    assert calls[0][0][0]["document_id"] == "doc-1"
    assert calls[0][0][0]["organization_id"] == "org-1"
    assert calls[0][0][0]["embedding_status"] == "completed"


def test_ingest_document_chunks_marks_pending_without_embeddings(monkeypatch):
    monkeypatch.setattr(
        "app.services.document_ingestion.generate_embeddings",
        lambda texts: [None for _ in texts],
    )

    calls = []

    class FakeTable:
        def upsert(self, rows, on_conflict):
            calls.append(rows)
            return self

        def execute(self):
            return SimpleNamespace(data=[])

    class FakeClient:
        def table(self, name):
            return FakeTable()

    result = ingest_document_chunks(
        FakeClient(),
        document_id="doc-2",
        organization_id="org-1",
        extracted_text="A maintenance plan exists.",
    )

    assert result.embedding_status == "pending"
    assert result.embedded_count == 0
    assert calls[0][0]["embedding_status"] == "pending"
