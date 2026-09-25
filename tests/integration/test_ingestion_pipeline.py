"""Integration tests for document ingestion and lifecycle management."""

from pathlib import Path
from ingestion.parser import parse_document
from ingestion.chunker import chunk_document
from ingestion.embedder import DocumentEmbedder
from ingestion.lifecycle import DocumentLifecycleManager


def test_pdf_parsing_and_chunking():
    pdf_path = Path("data/documents/Supermicro_GPU_Nodes_MSA.pdf")
    assert pdf_path.exists()

    parsed = parse_document(pdf_path)
    assert parsed.total_pages >= 1
    assert parsed.classification == "LEGAL_COMMERCIAL"

    chunks = chunk_document(parsed)
    assert len(chunks) >= 3
    for c in chunks:
        assert c.metadata["source_file"] == pdf_path.name
        assert c.metadata["is_active"] is True


def test_embedder_query():
    embedder = DocumentEmbedder()
    results = embedder.query("Liquidated damages delay penalty", collection_name="legal_contracts", top_k=2)
    assert len(results) >= 1
    assert results[0].score > 0.3


def test_lifecycle_manager():
    lm = DocumentLifecycleManager()
    docs = lm.list_documents(include_deprecated=True)
    assert len(docs) >= 10
