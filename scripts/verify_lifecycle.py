"""Verification script for Action Point 2.4: Document Lifecycle & Deprecation."""

import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.lifecycle import DocumentLifecycleManager

def verify():
    lm = DocumentLifecycleManager()
    # Register new version
    lm.register_document("data/documents/Wiwynn_Chassis_MSA.pdf", version="1.0")
    # Deprecate the old one
    lm.deprecate_document("doc-msa-wiwynn", replaced_by="wiwynn_chassis_msa")

    conn = sqlite3.connect("data/generated/infrastructure.db")
    cur = conn.cursor()
    rows = cur.execute(
        "SELECT doc_id, version, is_active, deprecated_at, replaced_by FROM document_registry WHERE doc_id IN ('doc-msa-wiwynn', 'wiwynn_chassis_msa')"
    ).fetchall()

    print("Document Registry Dump:")
    for r in rows:
        status = "ACTIVE" if r[2] == 1 else "DEPRECATED"
        print(f"DocID: {r[0]} | Version: {r[1]} | Status: {status} | ReplacedBy: {r[4]}")
    conn.close()

if __name__ == "__main__":
    verify()
