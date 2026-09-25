"""Format-aware chunking pipeline preserving semantic boundaries and metadata.

Implements:
1. Section-aware chunking for legal agreements (MSAs, SLAs, PPAs).
2. Heading-based hierarchical chunking for engineering specs.
3. Paragraph-level chunking for disruption bulletins.
Enriches every chunk with source_file, page_number, section_heading, classification, and keywords.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List
from ingestion.parser import ParsedDocument
from ports.base import VectorChunk


def extract_keywords(text: str) -> List[str]:
    """Extract domain keywords from chunk text for downstream search indexing."""
    target_terms = [
        "liquidated damages", "force majeure", "penalty cap", "warranty",
        "insolvency", "restructuring", "taiwan", "embargo", "lead time",
        "power busbar", "48v", "cooling loop", "liquid cooling", "district heating",
        "bsi c5", "eu ai act", "nis2", "rocm", "cuda", "tomahawk", "800g",
        "osfp", "mi300x", "h200", "molex", "supermicro", "wiwynn", "submer"
    ]
    lower_txt = text.lower()
    found = [term for term in target_terms if term in lower_txt]
    return found[:5]


def chunk_legal_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Split legal documents along numbered Section headers to preserve atomic legal clauses."""
    chunks: List[VectorChunk] = []
    section_pattern = re.compile(r"(Section\s+\d+[^:\n]*[:\n][^\n]*)", re.IGNORECASE)

    chunk_seq = 1
    for page in doc.pages:
        text = page.text
        # Split along sections
        splits = section_pattern.split(text)
        current_heading = "Preamble"

        if len(splits) <= 1:
            # No section header on this page
            if text.strip():
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=text.strip(),
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": current_heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(text),
                        },
                    )
                )
                chunk_seq += 1
            continue

        # splits alternate: [before, heading1, body1, heading2, body2, ...]
        i = 0
        if splits[0].strip():
            cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
            chunks.append(
                VectorChunk(
                    chunk_id=cid,
                    doc_id=doc.doc_id,
                    text=splits[0].strip(),
                    metadata={
                        "source_file": doc.filename,
                        "page_number": page.page_number,
                        "section_heading": current_heading,
                        "classification": doc.classification,
                        "is_active": True,
                        "keywords": extract_keywords(splits[0]),
                    },
                )
            )
            chunk_seq += 1
            i = 1

        while i < len(splits):
            heading = splits[i].strip()
            body = splits[i + 1].strip() if i + 1 < len(splits) else ""
            combined_text = f"{heading}\n{body}".strip()
            if combined_text:
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=combined_text,
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(combined_text),
                        },
                    )
                )
                chunk_seq += 1
            i += 2

    return chunks


def chunk_technical_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Split technical documents along Chapter / Heading markers."""
    chunks: List[VectorChunk] = []
    chapter_pattern = re.compile(r"(Chapter\s+\d+[^:\n]*[:\n][^\n]*)", re.IGNORECASE)

    chunk_seq = 1
    for page in doc.pages:
        text = page.text
        splits = chapter_pattern.split(text)
        current_heading = "Chapter 1: Overview"

        if len(splits) <= 1:
            if text.strip():
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=text.strip(),
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": current_heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(text),
                        },
                    )
                )
                chunk_seq += 1
            continue

        i = 0
        if splits[0].strip():
            cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
            chunks.append(
                VectorChunk(
                    chunk_id=cid,
                    doc_id=doc.doc_id,
                    text=splits[0].strip(),
                    metadata={
                        "source_file": doc.filename,
                        "page_number": page.page_number,
                        "section_heading": current_heading,
                        "classification": doc.classification,
                        "is_active": True,
                        "keywords": extract_keywords(splits[0]),
                    },
                )
            )
            chunk_seq += 1
            i = 1

        while i < len(splits):
            heading = splits[i].strip()
            body = splits[i + 1].strip() if i + 1 < len(splits) else ""
            combined_text = f"{heading}\n{body}".strip()
            if combined_text:
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=combined_text,
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(combined_text),
                        },
                    )
                )
                chunk_seq += 1
            i += 2

    return chunks


def chunk_bulletin_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Split bulletins and general documents by section or paragraph."""
    chunks: List[VectorChunk] = []
    section_pattern = re.compile(r"(Section\s+\d+[^:\n]*[:\n][^\n]*)", re.IGNORECASE)

    chunk_seq = 1
    for page in doc.pages:
        text = page.text
        splits = section_pattern.split(text)
        current_heading = "Executive Summary"

        if len(splits) <= 1:
            paras = [p.strip() for p in text.split("\n\n") if p.strip()]
            for p in paras:
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=p,
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": current_heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(p),
                        },
                    )
                )
                chunk_seq += 1
            continue

        i = 0
        if splits[0].strip():
            cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
            chunks.append(
                VectorChunk(
                    chunk_id=cid,
                    doc_id=doc.doc_id,
                    text=splits[0].strip(),
                    metadata={
                        "source_file": doc.filename,
                        "page_number": page.page_number,
                        "section_heading": current_heading,
                        "classification": doc.classification,
                        "is_active": True,
                        "keywords": extract_keywords(splits[0]),
                    },
                )
            )
            chunk_seq += 1
            i = 1

        while i < len(splits):
            heading = splits[i].strip()
            body = splits[i + 1].strip() if i + 1 < len(splits) else ""
            combined_text = f"{heading}\n{body}".strip()
            if combined_text:
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=combined_text,
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(combined_text),
                        },
                    )
                )
                chunk_seq += 1
            i += 2

    return chunks


def chunk_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Format-aware chunking dispatcher."""
    if doc.classification == "LEGAL_COMMERCIAL":
        return chunk_legal_document(doc)
    elif doc.classification == "TECHNICAL_SPEC":
        return chunk_technical_document(doc)
    else:
        return chunk_bulletin_document(doc)
