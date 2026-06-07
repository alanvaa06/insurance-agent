"""Tests for the pure chunking logic (no ChromaDB / API key required)."""
import pytest

from app.database.vector_store import chunk_text


def test_short_text_dropped():
    assert chunk_text("too short") == []


def test_long_text_chunked():
    text = "A" * 1200
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    assert len(chunks) >= 2
    assert all(len(c) <= 500 for c in chunks)


def test_chunks_overlap():
    text = "".join(str(i % 10) for i in range(1000))
    chunks = chunk_text(text, chunk_size=500, overlap=50)
    # Step is chunk_size - overlap = 450, so chunk 2 starts at index 450.
    assert chunks[1].startswith(text[450:455])


def test_invalid_overlap_raises():
    with pytest.raises(ValueError):
        chunk_text("x" * 100, chunk_size=50, overlap=50)
