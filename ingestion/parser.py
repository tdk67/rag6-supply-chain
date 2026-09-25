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


def parse_csv(file_path: str | Path) -> ParsedDocument:
    """Extract tabular data, columns, and records from a CSV spreadsheet."""
    import pandas as pd

    path = resolve_path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {path}")

    file_hash = calculate_file_sha256(path)
    df = pd.read_csv(path)
    title = path.stem.replace("_", " ").title()

    rows_total = len(df)
    cols_total = len(df.columns)
    header_summary = (
        f"Spreadsheet Dataset: {path.name} | Records: {rows_total} rows, {cols_total} columns.\n"
        f"Columns: {', '.join(str(c) for c in df.columns)}"
    )

    chunk_size = 50
    pages: List[ParsedPage] = []
    if rows_total == 0:
        pages.append(ParsedPage(page_number=1, text=header_summary, char_count=len(header_summary)))
    else:
        for idx, start_idx in enumerate(range(0, rows_total, chunk_size), start=1):
            subset = df.iloc[start_idx : start_idx + chunk_size]
            table_md = subset.to_markdown(index=False)
            page_text = f"{header_summary}\n\n[Rows {start_idx + 1} to {min(start_idx + chunk_size, rows_total)}]:\n{table_md}"
            pages.append(ParsedPage(page_number=idx, text=page_text, char_count=len(page_text)))

    return ParsedDocument(
        doc_id=path.stem.lower().replace(" ", "_"),
        title=title,
        filename=path.name,
        file_path=str(path),
        classification="TABLE_DATA",
        total_pages=len(pages),
        sha256_hash=file_hash,
        pages=pages,
        metadata={"format": "CSV", "row_count": rows_total, "column_count": cols_total},
    )


def parse_excel(file_path: str | Path) -> ParsedDocument:
    """Extract sheets, tables, and records from an Excel workbook (.xlsx, .xls)."""
    import pandas as pd

    path = resolve_path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Excel file not found: {path}")

    file_hash = calculate_file_sha256(path)
    excel_file = pd.ExcelFile(path)
    title = path.stem.replace("_", " ").title()

    pages: List[ParsedPage] = []
    page_idx = 1
    total_rows = 0

    for sheet_name in excel_file.sheet_names:
        df = excel_file.parse(sheet_name)
        rows_count = len(df)
        cols_count = len(df.columns)
        total_rows += rows_count
        header_summary = (
            f"Workbook: {path.name} | Sheet: {sheet_name} | {rows_count} rows, {cols_count} columns.\n"
            f"Columns: {', '.join(str(c) for c in df.columns)}"
        )

        chunk_size = 50
        if rows_count == 0:
            pages.append(ParsedPage(page_number=page_idx, text=header_summary, char_count=len(header_summary)))
            page_idx += 1
        else:
            for start_idx in range(0, rows_count, chunk_size):
                subset = df.iloc[start_idx : start_idx + chunk_size]
                table_md = subset.to_markdown(index=False)
                page_text = f"{header_summary}\n\n[Rows {start_idx + 1} to {min(start_idx + chunk_size, rows_count)}]:\n{table_md}"
                pages.append(ParsedPage(page_number=page_idx, text=page_text, char_count=len(page_text)))
                page_idx += 1

    return ParsedDocument(
        doc_id=path.stem.lower().replace(" ", "_"),
        title=title,
        filename=path.name,
        file_path=str(path),
        classification="TABLE_DATA",
        total_pages=len(pages),
        sha256_hash=file_hash,
        pages=pages,
        metadata={
            "format": "EXCEL",
            "sheet_names": excel_file.sheet_names,
            "total_rows": total_rows,
        },
    )


def parse_document(file_path: str | Path) -> ParsedDocument:
    """Dispatches parsing based on file extension (PDF, TXT, CSV, Excel)."""
    path = resolve_path(file_path)
    ext = path.suffix.lower()
    if ext == ".pdf":
        return parse_pdf(path)
    elif ext in (".txt", ".md"):
        return parse_txt(path)
    elif ext == ".csv":
        return parse_csv(path)
    elif ext in (".xlsx", ".xls"):
        return parse_excel(path)
    else:
        raise ValueError(
            f"Unsupported file format for parser: {ext}. Supported formats: PDF, TXT, CSV, Excel (.xlsx, .xls)"
        )
