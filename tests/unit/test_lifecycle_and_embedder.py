"""Unit tests for DocumentLifecycleManager and DocumentEmbedder."""

from pathlib import Path
import pytest
from ingestion.lifecycle import DocumentLifecycleManager
from ingestion.embedder import DocumentEmbedder


def test_lifecycle_registration_and_deprecation():
    lm = DocumentLifecycleManager()
    sample_file = Path("data/documents/Taiwan_Strait_Freight_Advisory.txt")
    if not sample_file.exists():
        pytest.skip("Test sample document not found")

    # 1. Register document
    reg = lm.register_document(
        file_path=sample_file,
        version="2.0",
        classification="DISRUPTION_BULLETIN",
    )
    assert reg["status"] == "REGISTERED"
    doc_id = reg["doc_id"]
    assert doc_id is not None

    # 2. List documents
    docs = lm.list_documents(include_deprecated=True)
    assert len(docs) >= 1
    assert any(d["doc_id"] == doc_id for d in docs)

    # 3. Deprecate document
    success = lm.deprecate_document(doc_id, replaced_by="SUPERSESSION_TEST_ID")
    assert success is True

    # 4. Verify deprecated status
    active_docs = lm.list_documents(include_deprecated=False)
    assert all(d["doc_id"] != doc_id for d in active_docs)


def test_embedder_index_document():
    embedder = DocumentEmbedder()
    test_csv = Path("data/documents/Supplier_Tier1_Pricing_Matrix.csv")
    if test_csv.exists():
        count = embedder.index_document(test_csv)
        assert count >= 1
    stats = embedder.vector_store.get_collection_stats()
    assert "table_summaries" in stats
    assert stats["table_summaries"] >= 1
