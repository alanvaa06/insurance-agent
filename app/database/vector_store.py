"""ChromaDB vector store with OpenAI embeddings.

The store is created lazily via ``get_policy_store()`` rather than at import
time, so importing the agent does not require an API key or a ChromaDB on disk
(important for tests and for clean failure messages).
"""
import re
import threading
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from app.utils.config import config
from app.utils.logger import logger


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks, dropping fragments under 50 chars.

    Pure and module-level so it is unit-testable without a ChromaDB client.
    """
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    chunks = []
    for i in range(0, len(text), chunk_size - overlap):
        chunk = text[i : i + chunk_size].strip()
        if len(chunk) > 50:
            chunks.append(chunk)
    return chunks


def extract_pdf_chunks(pdf_path: str) -> list[str]:
    """Return all text chunks from a PDF, or [] if it cannot be read."""
    if not Path(pdf_path).exists():
        logger.error(f"Policy PDF not found: {pdf_path}")
        return []
    chunks: list[str] = []
    try:
        reader = PdfReader(pdf_path)
        for page in reader.pages:
            chunks.extend(chunk_text(page.extract_text() or ""))
    except Exception as e:  # noqa: BLE001
        logger.error(f"Error reading PDF {pdf_path}: {e}")
    return chunks


def _keyword_score(query: str, chunk: str) -> int:
    """Number of distinct query words present in the chunk (case-insensitive)."""
    q_words = {w for w in re.findall(r"[a-z0-9]+", query.lower()) if len(w) > 2}
    if not q_words:
        return 0
    c_words = set(re.findall(r"[a-z0-9]+", chunk.lower()))
    return len(q_words & c_words)


class KeywordPolicyStore:
    """Demo retriever: keyword overlap over PDF chunks. No API key, no model."""

    def __init__(self):
        self._chunks: list[str] = []

    def populate_from_pdf(self, pdf_path: str | None = None) -> None:
        if self._chunks:
            return
        self._chunks = extract_pdf_chunks(pdf_path or config.policy_pdf_path)
        logger.info(f"Demo keyword store loaded {len(self._chunks)} chunks")

    def count(self) -> int:
        return len(self._chunks)

    def retrieve(self, query: str, top_k: int = 5) -> str:
        if not self._chunks:
            self.populate_from_pdf()
        scored = sorted(
            self._chunks, key=lambda c: _keyword_score(query, c), reverse=True
        )
        top = [c for c in scored if _keyword_score(query, c) > 0][:top_k]
        if not top:  # fall back to the first chunks so retrieval is never empty
            top = self._chunks[:top_k]
        return "\n\n".join(top)


class PolicyVectorStore:
    """Manages a ChromaDB collection of insurance policy chunks."""

    def __init__(self):
        if not config.is_api_key_configured():
            raise RuntimeError(
                "OPENAI_API_KEY is not set; cannot create embeddings. "
                "See .env.example."
            )

        import chromadb
        from chromadb.config import Settings
        from chromadb.utils import embedding_functions

        logger.info("Initializing ChromaDB vector store")
        self.client = chromadb.PersistentClient(
            path=config.chroma_persist_directory,
            settings=Settings(anonymized_telemetry=False),
        )
        self.embedding_function = embedding_functions.OpenAIEmbeddingFunction(
            api_key=config.openai_api_key,
            model_name=config.embedding_model,
        )
        self.collection = self.client.get_or_create_collection(
            name=config.chroma_collection_name,
            embedding_function=self.embedding_function,
            metadata={"description": "Insurance policy documents"},
        )
        logger.info(
            f"ChromaDB collection '{config.chroma_collection_name}' ready "
            f"({self.collection.count()} docs)"
        )

    def load_pdf_policy(self, pdf_path: str) -> list[dict[str, Any]]:
        """Extract overlapping text chunks from the policy PDF."""
        logger.info(f"Loading policy PDF: {pdf_path}")
        if not Path(pdf_path).exists():
            logger.error(f"Policy PDF not found: {pdf_path}")
            return []

        chunks: list[dict[str, Any]] = []
        try:
            reader = PdfReader(pdf_path)
            logger.info(f"PDF has {len(reader.pages)} pages")
            for page_num, page in enumerate(reader.pages, 1):
                text = page.extract_text() or ""
                for chunk in chunk_text(text):
                    chunks.append({"text": chunk, "page": page_num, "source": pdf_path})
            logger.info(f"Extracted {len(chunks)} chunks from PDF")
            return chunks
        except Exception as e:
            logger.error(f"Error loading PDF: {e}")
            return []

    def populate_from_pdf(self, pdf_path: str | None = None) -> None:
        """Load the policy PDF into the vector store if not already populated."""
        pdf_path = pdf_path or config.policy_pdf_path
        if self.collection.count() > 0:
            logger.info("Collection already populated; skipping.")
            return

        chunks = self.load_pdf_policy(pdf_path)
        if not chunks:
            logger.warning("No chunks extracted from PDF; nothing to index.")
            return

        self.collection.add(
            documents=[c["text"] for c in chunks],
            metadatas=[{"page": c["page"], "source": c["source"]} for c in chunks],
            ids=[f"chunk_{i}" for i in range(len(chunks))],
        )
        logger.info(f"Indexed {len(chunks)} chunks into vector store")

    def retrieve(self, query: str, top_k: int = 5) -> str:
        """Return concatenated policy passages most relevant to ``query``."""
        results = self.collection.query(query_texts=[query], n_results=top_k)
        docs = results.get("documents") or [[]]
        if not docs or not docs[0]:
            logger.warning("No relevant policy documents found")
            return ""
        logger.info(f"Retrieved {len(docs[0])} chunks for query")
        return "\n\n".join(docs[0])


_policy_store: PolicyVectorStore | KeywordPolicyStore | None = None
_policy_store_lock = threading.Lock()


def get_policy_store() -> PolicyVectorStore | KeywordPolicyStore:
    """Return a lazily-created, process-wide policy store singleton.

    Demo mode (no API key) uses the keyword store; otherwise the ChromaDB store.
    Double-checked locking avoids two concurrent Streamlit sessions each building
    a store.
    """
    global _policy_store
    if _policy_store is None:
        with _policy_store_lock:
            if _policy_store is None:
                _policy_store = (
                    KeywordPolicyStore() if config.demo_mode else PolicyVectorStore()
                )
    return _policy_store
