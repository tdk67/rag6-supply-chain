"""Unit tests for format-aware chunker."""

from ingestion.parser import ParsedDocument, ParsedPage
from ingestion.chunker import chunk_document, extract_keywords


def test_extract_keywords():
    text = "The liquidated damages clause applies to supplier delay under Force Majeure."
    kws = extract_keywords(text)
    assert "liquidated damages" in kws
    assert "force majeure" in kws


def test_chunk_legal_document():
    doc = ParsedDocument(
        doc_id="test_legal",
        title="Test Agreement",
        filename="test.pdf",
        file_path="test.pdf",
        classification="LEGAL_COMMERCIAL",
        total_pages=1,
        sha256_hash="abc",
        pages=[
            ParsedPage(
                page_number=1,
                text="Preamble text.\n\nSection 1: Scope\nSupplier agrees to deliver parts.\n\nSection 18: Delays\nLiquidated damages apply at 0.5% per week.",
                char_count=130,
            )
        ],
    )
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    sections = [c.metadata.get("section_heading") for c in chunks]
    assert any("Section 1" in s for s in sections)
    assert any("Section 18" in s for s in sections)


def test_chunk_technical_document():
    doc = ParsedDocument(
        doc_id="test_tech",
        title="Test Spec",
        filename="test_spec.pdf",
        file_path="test_spec.pdf",
        classification="TECHNICAL_SPEC",
        total_pages=1,
        sha256_hash="def",
        pages=[
            ParsedPage(
                page_number=1,
                text="Chapter 1: Overview\nStandard ORV3 48V power busbar.\n\nChapter 2: Thermal\nMax inlet water temperature 32C.",
                char_count=100,
            )
        ],
    )
    chunks = chunk_document(doc)
    assert len(chunks) >= 1
    assert chunks[0].metadata["classification"] == "TECHNICAL_SPEC"


def test_chunk_bulletin_document():
    doc = ParsedDocument(
        doc_id="test_bull",
        title="Test Advisory",
        filename="advisory.txt",
        file_path="advisory.txt",
        classification="DISRUPTION_BULLETIN",
        total_pages=1,
        sha256_hash="ghi",
        pages=[
            ParsedPage(
                page_number=1,
                text="Section 1: Situation Assessment\nNaval blockade in Taiwan Strait.\n\nSection 2: Impact\nComponent lead times delayed by 16 weeks.",
                char_count=120,
            )
        ],
    )
    chunks = chunk_document(doc)
    assert len(chunks) >= 2
    assert chunks[0].metadata["classification"] == "DISRUPTION_BULLETIN"
