"""Format-specific document parser using PyMuPDF (fitz) and structured text readers."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import pymupdf as fitz
from pydantic import BaseModel, Field

from utils.hashing import calculate_file_sha256
from utils.config import resolve_path


class ParsedPage(BaseModel):
    page_number: int
    text: str
    char_count: int


class ParsedDocument(BaseModel):
    doc_id: str
    title: str
    filename: str
    file_path: str
    classification: str
    total_pages: int
    sha256_hash: str
    pages: List[ParsedPage] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


def infer_classification(filename: str, sample_text: str = "") -> str:
    """Classify document category based on filename and header content."""
    lower_fn = filename.lower()
    lower_txt = sample_text.lower()

    if any(k in lower_fn for k in ["msa", "agreement", "contract", "sla", "ppa"]):
        return "LEGAL_COMMERCIAL"
    elif any(k in lower_fn for k in ["spec", "standard", "guide", "architecture"]):
        return "TECHNICAL_SPEC"
    elif any(k in lower_fn for k in ["attestation", "conformity", "policy", "c5", "nis2", "audit"]):
        return "COMPLIANCE_AUDIT"
    elif any(k in lower_fn for k in ["advisory", "report", "bulletin", "update", "disruption"]):
        return "DISRUPTION_BULLETIN"
    return "GENERAL"


def parse_pdf(file_path: str | Path) -> ParsedDocument:
    """Extract text, page numbers, and metadata from a PDF file using PyMuPDF."""
    path = resolve_path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    file_hash = calculate_file_sha256(path)
    doc = fitz.open(str(path))
    total_pages = len(doc)
    pages: List[ParsedPage] = []
    full_text_list = []

    for page_idx in range(total_pages):
        page = doc.load_page(page_idx)
        text = page.get_text("text").strip()
        pages.append(
            ParsedPage(
                page_number=page_idx + 1,
                text=text,
                char_count=len(text),
            )
        )
        full_text_list.append(text)

    # Infer doc_id from stem
    doc_id = path.stem.lower().replace(" ", "_")
    first_page_text = pages[0].text if pages else ""
    title = path.stem.replace("_", " ")

    # Check for title in first line
    if first_page_text:
        first_line = first_page_text.split("\n")[0].strip()
        if len(first_line) > 5 and len(first_line) < 100:
            title = first_line

    classification = infer_classification(path.name, first_page_text)

    parsed_doc = ParsedDocument(
        doc_id=doc_id,
        title=title,
        filename=path.name,
        file_path=str(path),
        classification=classification,
        total_pages=total_pages,
        sha256_hash=file_hash,
        pages=pages,
        metadata={
            "pdf_metadata": doc.metadata,
            "format": "PDF",
        },
    )
    doc.close()
    return parsed_doc


def parse_txt(file_path: str | Path) -> ParsedDocument:
    """Extract text and metadata from a plain text file."""
    path = resolve_path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"TXT file not found: {path}")

    file_hash = calculate_file_sha256(path)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().strip()

    title = path.stem.replace("_", " ")
    lines = text.split("\n")
    if lines and len(lines[0].strip()) > 5:
        title = lines[0].strip()

    classification = infer_classification(path.name, text)

    return ParsedDocument(
        doc_id=path.stem.lower().replace(" ", "_"),
        title=title,
        filename=path.name,
        file_path=str(path),
        classification=classification,
        total_pages=1,
        sha256_hash=file_hash,
        pages=[ParsedPage(page_number=1, text=text, char_count=len(text))],
        metadata={"format": "TXT"},
    )


def parse_document(file_path: str | Path) -> ParsedDocument:
    """Dispatches parsing based on file extension."""
    path = resolve_path(file_path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return parse_pdf(path)
    elif ext in (".txt", ".md"):
        return parse_txt(path)
    else:
        raise ValueError(f"Unsupported file format for parser: {ext}")
