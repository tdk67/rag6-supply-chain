"""Document lifecycle manager: registration, hashing, versioning, and deprecation."""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.parser import parse_document
from ports.registry import AdapterRegistry
from utils.config import resolve_path, load_config
from utils.hashing import calculate_file_sha256


class DocumentLifecycleManager:
    """Manages document versions, SHA-256 deduplication, and deprecation in SQLite & ChromaDB."""

    def __init__(self, db_path: Optional[str | Path] = None):
        if db_path is not None:
            self.db_path = resolve_path(db_path)
        else:
            cfg = load_config()
            self.db_path = resolve_path(cfg["paths"]["sqlite_db"])

        self.vector_store = AdapterRegistry.get_vector_store()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def register_document(
        self,
        file_path: str | Path,
        version: str = "1.0",
        classification: Optional[str] = None,
        effective_date: Optional[str] = None,
        total_chunks: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Register a new document in the SQLite SSOT registry with duplicate SHA-256 check."""
        path = resolve_path(file_path)
        parsed = parse_document(path)
        file_hash = parsed.sha256_hash
        cls_val = classification or parsed.classification
        eff_date = effective_date or datetime.now(timezone.utc).strftime("%Y-%m-%d")

        if total_chunks is None:
            from ingestion.chunker import chunk_document
            actual_chunks = len(chunk_document(parsed))
        else:
            actual_chunks = int(total_chunks)

        conn = self._get_connection()
        cur = conn.cursor()

        # Check duplicate hash
        existing = cur.execute(
            "SELECT doc_id, filename, version, is_active FROM document_registry WHERE sha256_hash = ?",
            (file_hash,),
        ).fetchone()

        if existing and existing["is_active"]:
            conn.close()
            return {
                "status": "DUPLICATE",
                "message": f"Identical file already registered under doc_id '{existing['doc_id']}' (v{existing['version']}).",
                "doc_id": existing["doc_id"],
            }

        doc_id = parsed.doc_id
        now_iso = datetime.now(timezone.utc).isoformat()

        cur.execute(
            """
            INSERT OR REPLACE INTO document_registry
            (doc_id, title, filename, version, effective_date, is_active, classification,
             sha256_hash, total_pages, total_chunks, deprecated_at, replaced_by, ingested_at)
            VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, NULL, NULL, ?)
            """,
            (
                doc_id,
                parsed.title,
                parsed.filename,
                version,
                eff_date,
                cls_val,
                file_hash,
                parsed.total_pages,
                actual_chunks,
                now_iso,
            ),
        )
        conn.commit()
        conn.close()

        return {
            "status": "REGISTERED",
            "doc_id": doc_id,
            "filename": parsed.filename,
            "version": version,
            "classification": cls_val,
            "sha256_hash": file_hash,
        }

    def deprecate_document(self, doc_id: str, replaced_by: Optional[str] = None) -> bool:
        """Mark a document as DEPRECATED in SQLite and update vector store chunk flags."""
        conn = self._get_connection()
        cur = conn.cursor()

        row = cur.execute("SELECT * FROM document_registry WHERE doc_id = ?", (doc_id,)).fetchone()
        if not row:
            conn.close()
            return False

        now_iso = datetime.now(timezone.utc).isoformat()
        cur.execute(
            "UPDATE document_registry SET is_active = 0, deprecated_at = ?, replaced_by = ? WHERE doc_id = ?",
            (now_iso, replaced_by, doc_id),
        )
        conn.commit()
        conn.close()

        # Update ChromaDB chunk metadata
        self.vector_store.deprecate_by_doc_id(doc_id)
        return True

    def replace_version(self, old_doc_id: str, new_file_path: str | Path, new_version: str) -> Dict[str, Any]:
        """Upload a new version of an existing document, automatically deprecating the older version."""
        reg_result = self.register_document(new_file_path, version=new_version)
        new_doc_id = reg_result["doc_id"]
        self.deprecate_document(old_doc_id, replaced_by=new_doc_id)
        reg_result["replaces"] = old_doc_id
        return reg_result

    def list_documents(self, include_deprecated: bool = True) -> List[Dict[str, Any]]:
        """List all registered documents."""
        conn = self._get_connection()
        cur = conn.cursor()
        query = "SELECT * FROM document_registry"
        if not include_deprecated:
            query += " WHERE is_active = 1"
        query += " ORDER BY ingested_at DESC"

        rows = cur.execute(query).fetchall()
        docs = [dict(r) for r in rows]
        conn.close()
        return docs
