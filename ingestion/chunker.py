"""Format-aware chunking pipeline preserving semantic boundaries and metadata.

Implements:
1. Section-aware chunking for legal agreements (MSAs, SLAs, PPAs) with token caps & overlap.
2. Heading-based hierarchical chunking for engineering specs with token caps & overlap.
3. Paragraph-level chunking for disruption bulletins with token caps & overlap.
4. Tabular data chunking with structured markdown preservation.
Enriches every chunk with source_file, page_number, section_heading, classification, and keywords.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional
from ingestion.parser import ParsedDocument
from ports.base import VectorChunk
from utils.config import load_config


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


def split_text_with_overlap(text: str, max_tokens: int = 800, overlap_tokens: int = 150) -> List[str]:
    """Split text into chunks capped at max_tokens with overlap_tokens sliding window."""
    words = text.split()
    if not words:
        return []
    if len(words) <= max_tokens:
        return [text]

    chunks = []
    step = max(1, max_tokens - overlap_tokens)
    for i in range(0, len(words), step):
        chunk_words = words[i : i + max_tokens]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        if i + max_tokens >= len(words):
            break
    return chunks


def _get_chunk_params(doc_type: str) -> tuple[int, int]:
    """Retrieve chunk_size and chunk_overlap from config.json with safe fallbacks."""
    try:
        cfg = load_config()
        chunk_cfg = cfg.get("chunking", {})
    except Exception:
        chunk_cfg = {}

    defaults = {
        "contracts": (800, 150),
        "specifications": (600, 100),
        "tables": (500, 100),
        "general": (500, 100),
    }
    params = chunk_cfg.get(doc_type, {})
    default_size, default_overlap = defaults.get(doc_type, (500, 100))
    chunk_size = params.get("chunk_size", default_size)
    chunk_overlap = params.get("chunk_overlap", default_overlap)
    return chunk_size, chunk_overlap


def chunk_legal_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Split legal documents along numbered Section headers to preserve atomic legal clauses with size caps & overlap."""
    max_tokens, overlap = _get_chunk_params("contracts")
    chunks: List[VectorChunk] = []
    section_pattern = re.compile(r"(Section\s+\d+[^:\n]*[:\n][^\n]*)", re.IGNORECASE)

    chunk_seq = 1
    for page in doc.pages:
        text = page.text
        splits = section_pattern.split(text)
        current_heading = "Preamble"

        if len(splits) <= 1:
            if text.strip():
                sub_chunks = split_text_with_overlap(text.strip(), max_tokens, overlap)
                for sub_text in sub_chunks:
                    cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                    chunks.append(
                        VectorChunk(
                            chunk_id=cid,
                            doc_id=doc.doc_id,
                            text=sub_text,
                            metadata={
                                "source_file": doc.filename,
                                "page_number": page.page_number,
                                "section_heading": current_heading,
                                "classification": doc.classification,
                                "is_active": True,
                                "keywords": extract_keywords(sub_text),
                            },
                        )
                    )
                    chunk_seq += 1
            continue

        i = 0
        if splits[0].strip():
            sub_chunks = split_text_with_overlap(splits[0].strip(), max_tokens, overlap)
            for sub_text in sub_chunks:
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=sub_text,
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": current_heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(sub_text),
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
                sub_chunks = split_text_with_overlap(combined_text, max_tokens, overlap)
                for sub_text in sub_chunks:
                    cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                    chunks.append(
                        VectorChunk(
                            chunk_id=cid,
                            doc_id=doc.doc_id,
                            text=sub_text,
                            metadata={
                                "source_file": doc.filename,
                                "page_number": page.page_number,
                                "section_heading": heading,
                                "classification": doc.classification,
                                "is_active": True,
                                "keywords": extract_keywords(sub_text),
                            },
                        )
                    )
                    chunk_seq += 1
            i += 2

    return chunks


def chunk_technical_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Split technical documents along specification headers with size caps & overlap."""
    max_tokens, overlap = _get_chunk_params("specifications")
    chunks: List[VectorChunk] = []
    heading_pattern = re.compile(r"(\d+\.\d+\s+[A-Za-z\s]+[:\n])", re.IGNORECASE)

    chunk_seq = 1
    for page in doc.pages:
        text = page.text
        splits = heading_pattern.split(text)
        current_heading = "Overview"

        if len(splits) <= 1:
            if text.strip():
                sub_chunks = split_text_with_overlap(text.strip(), max_tokens, overlap)
                for sub_text in sub_chunks:
                    cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                    chunks.append(
                        VectorChunk(
                            chunk_id=cid,
                            doc_id=doc.doc_id,
                            text=sub_text,
                            metadata={
                                "source_file": doc.filename,
                                "page_number": page.page_number,
                                "section_heading": current_heading,
                                "classification": doc.classification,
                                "is_active": True,
                                "keywords": extract_keywords(sub_text),
                            },
                        )
                    )
                    chunk_seq += 1
            continue

        i = 0
        if splits[0].strip():
            sub_chunks = split_text_with_overlap(splits[0].strip(), max_tokens, overlap)
            for sub_text in sub_chunks:
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=sub_text,
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": current_heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(sub_text),
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
                sub_chunks = split_text_with_overlap(combined_text, max_tokens, overlap)
                for sub_text in sub_chunks:
                    cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                    chunks.append(
                        VectorChunk(
                            chunk_id=cid,
                            doc_id=doc.doc_id,
                            text=sub_text,
                            metadata={
                                "source_file": doc.filename,
                                "page_number": page.page_number,
                                "section_heading": heading,
                                "classification": doc.classification,
                                "is_active": True,
                                "keywords": extract_keywords(sub_text),
                            },
                        )
                    )
                    chunk_seq += 1
            i += 2

    return chunks


def chunk_bulletin_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Split bulletins and general documents by section or paragraph with size caps & overlap."""
    max_tokens, overlap = _get_chunk_params("general")
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
                sub_chunks = split_text_with_overlap(p, max_tokens, overlap)
                for sub_text in sub_chunks:
                    cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                    chunks.append(
                        VectorChunk(
                            chunk_id=cid,
                            doc_id=doc.doc_id,
                            text=sub_text,
                            metadata={
                                "source_file": doc.filename,
                                "page_number": page.page_number,
                                "section_heading": current_heading,
                                "classification": doc.classification,
                                "is_active": True,
                                "keywords": extract_keywords(sub_text),
                            },
                        )
                    )
                    chunk_seq += 1
            continue

        i = 0
        if splits[0].strip():
            sub_chunks = split_text_with_overlap(splits[0].strip(), max_tokens, overlap)
            for sub_text in sub_chunks:
                cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                chunks.append(
                    VectorChunk(
                        chunk_id=cid,
                        doc_id=doc.doc_id,
                        text=sub_text,
                        metadata={
                            "source_file": doc.filename,
                            "page_number": page.page_number,
                            "section_heading": current_heading,
                            "classification": doc.classification,
                            "is_active": True,
                            "keywords": extract_keywords(sub_text),
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
                sub_chunks = split_text_with_overlap(combined_text, max_tokens, overlap)
                for sub_text in sub_chunks:
                    cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
                    chunks.append(
                        VectorChunk(
                            chunk_id=cid,
                            doc_id=doc.doc_id,
                            text=sub_text,
                            metadata={
                                "source_file": doc.filename,
                                "page_number": page.page_number,
                                "section_heading": heading,
                                "classification": doc.classification,
                                "is_active": True,
                                "keywords": extract_keywords(sub_text),
                            },
                        )
                    )
                    chunk_seq += 1
            i += 2

    return chunks


def chunk_tabular_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Convert spreadsheet / tabular parsed pages into searchable vector chunks with size caps & overlap."""
    max_tokens, overlap = _get_chunk_params("tables")
    chunks: List[VectorChunk] = []
    chunk_seq = 1
    for page in doc.pages:
        text = page.text.strip()
        if not text:
            continue
        sub_chunks = split_text_with_overlap(text, max_tokens, overlap)
        for sub_text in sub_chunks:
            cid = f"{doc.doc_id}_chunk_{chunk_seq:03d}"
            chunks.append(
                VectorChunk(
                    chunk_id=cid,
                    doc_id=doc.doc_id,
                    text=sub_text,
                    metadata={
                        "source_file": doc.filename,
                        "page_number": page.page_number,
                        "section_heading": f"Sheet / Table Page {page.page_number}",
                        "classification": "TABLE_DATA",
                        "is_active": True,
                        "keywords": extract_keywords(sub_text),
                    },
                )
            )
            chunk_seq += 1
    return chunks


def chunk_document(doc: ParsedDocument) -> List[VectorChunk]:
    """Format-aware chunking dispatcher."""
    if doc.classification == "LEGAL_COMMERCIAL":
        return chunk_legal_document(doc)
    elif doc.classification == "TECHNICAL_SPEC":
        return chunk_technical_document(doc)
    elif doc.classification == "TABLE_DATA":
        return chunk_tabular_document(doc)
    else:
        return chunk_bulletin_document(doc)
