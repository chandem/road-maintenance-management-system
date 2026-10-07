from app.services.document_chunking import chunk_document_text


def test_empty_document_returns_no_chunks():
    assert chunk_document_text("   ") == []


def test_short_document_is_one_chunk():
    chunks = chunk_document_text("Road maintenance is planned for Section A.")
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0
    assert chunks[0].text == "Road maintenance is planned for Section A."


def test_long_document_prefers_paragraph_boundaries():
    text = (
        "Paragraph one contains road inspection findings. " * 8
        + "\n\n"
        + "Paragraph two contains maintenance recommendations. " * 8
    )
    chunks = chunk_document_text(text, max_chars=300, overlap_chars=50)
    assert len(chunks) > 1
    assert all(len(chunk.text) <= 300 for chunk in chunks)
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))


def test_chunks_keep_source_offsets_and_overlap():
    text = "Road condition findings. " * 40
    chunks = chunk_document_text(text, max_chars=200, overlap_chars=40)
    assert len(chunks) > 1
    for previous, current in zip(chunks, chunks[1:]):
        assert previous.start_char < previous.end_char
        assert current.start_char < current.end_char
        assert current.start_char < previous.end_char


def test_invalid_chunk_configuration_is_rejected():
    try:
        chunk_document_text("test", max_chars=100, overlap_chars=100)
    except ValueError:
        return
    raise AssertionError("overlap_chars must be smaller than max_chars")
