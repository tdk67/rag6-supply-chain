"""Tab 4: Document Ingestion & Lifecycle Manager.

Enables drag-and-drop file ingestion, document registration, version deprecation,
and real-time ChromaDB vector indexing.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional
import streamlit as st
import pandas as pd

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.embedder import DocumentEmbedder
from ingestion.lifecycle import DocumentLifecycleManager
from utils.config import resolve_path, load_config


ALLOWED_EXTENSIONS = {".pdf", ".txt", ".csv", ".xlsx", ".xls"}
MAX_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


def handle_file_upload(uploaded_file, version: str = "1.0") -> dict:
    """Process uploaded file safely, save to data/documents/, register in SQLite, and index in ChromaDB."""
    # 1. Sanitize filename (strictly strip directory paths)
    raw_name = getattr(uploaded_file, "name", "")
    safe_name = Path(raw_name).name
    if not safe_name or ".." in raw_name or "/" in raw_name or "\\" in raw_name:
        return {"status": "ERROR", "message": "Invalid filename: path traversal characters detected."}

    # 2. Extension allowlist check
    suffix = Path(safe_name).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return {
            "status": "ERROR",
            "message": f"Unsupported file type '{suffix}'. Allowed types: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        }

    # 3. File size cap
    file_bytes = uploaded_file.getbuffer()
    if len(file_bytes) > MAX_FILE_SIZE_BYTES:
        return {
            "status": "ERROR",
            "message": f"File size ({len(file_bytes) / 1024 / 1024:.1f} MB) exceeds maximum allowed limit of 25 MB.",
        }

    # 4. Version string validation
    v_clean = version.strip()
    if not re.match(r"^v?\d+(\.\d+)*(-[a-zA-Z0-9.]+)?$", v_clean):
        v_clean = "1.0"

    cfg = load_config()
    docs_dir = resolve_path(cfg["paths"]["documents_dir"])
    docs_dir.mkdir(parents=True, exist_ok=True)

    dest_path = (docs_dir / safe_name).resolve()
    # Confirm dest_path is strictly within docs_dir
    if not str(dest_path).startswith(str(docs_dir.resolve())):
        return {"status": "ERROR", "message": "Security error: resolved path outside documents directory."}

    with open(dest_path, "wb") as f:
        f.write(file_bytes)

    lm = DocumentLifecycleManager()
    reg_res = lm.register_document(dest_path, version=v_clean)

    embedder = DocumentEmbedder()
    chunks_count = embedder.index_document(dest_path)

    return {
        "status": "SUCCESS",
        "doc_id": reg_res.get("doc_id"),
        "filename": safe_name,
        "version": v_clean,
        "chunks_indexed": chunks_count,
    }


def render_tab_ingestion():
    """Render Document Ingestion & Lifecycle Manager tab."""
    st.markdown("### 📥 Sovereign Knowledge Ingestion & Lifecycle Manager")
    st.caption("Upload new contracts, rotate versions, deprecate obsolete specifications, and update ChromaDB vector indices.")

    col_up, col_actions = st.columns([2, 1])

    with col_up:
        st.markdown("#### Upload Document")
        from utils.config import get_secret
        if get_secret("DISABLE_UPLOADS", "false").lower() in ("true", "1"):
            st.warning("🔒 Document uploads are disabled in this public demonstration environment for safety.")
            uploaded = None
        else:
            uploaded = st.file_uploader(
                "Select Document or Spreadsheet to Ingest (PDF, TXT, CSV, Excel)",
                type=["pdf", "txt", "csv", "xlsx", "xls"],
                key="file_uploader_widget",
            )
            version_input = st.text_input("Document Version", value="1.0", key="ingest_version_input")

        if uploaded is not None:
            # Show preview for spreadsheet files
            if uploaded.name.endswith(".csv"):
                try:
                    df_preview = pd.read_csv(uploaded)
                    uploaded.seek(0)
                    st.caption(f"📊 Previewing CSV: `{uploaded.name}` ({len(df_preview)} rows, {len(df_preview.columns)} cols)")
                    st.dataframe(df_preview.head(5), use_container_width=True)
                except Exception:
                    pass
            elif uploaded.name.endswith((".xlsx", ".xls")):
                try:
                    df_preview = pd.read_excel(uploaded)
                    uploaded.seek(0)
                    st.caption(f"📊 Previewing Excel: `{uploaded.name}` ({len(df_preview)} rows, {len(df_preview.columns)} cols)")
                    st.dataframe(df_preview.head(5), use_container_width=True)
                except Exception:
                    pass

            if st.button("⚡ Parse, Register & Embed into ChromaDB", type="primary"):
                with st.spinner(f"Ingesting {uploaded.name}..."):
                    try:
                        res = handle_file_upload(uploaded, version=version_input)
                        if res.get("status") == "ERROR":
                            st.error(f"Ingestion rejected: {res.get('message')}")
                        else:
                            st.success(f"Successfully indexed '{res['filename']}' ({res['chunks_indexed']} chunks) into ChromaDB!")
                    except Exception as e:
                        st.error(f"Ingestion failed: {e}")

    with col_actions:
        st.markdown("#### Document Deprecation")
        lm = DocumentLifecycleManager()
        all_docs = lm.list_documents(include_deprecated=False)
        doc_options = {d["title"]: d["doc_id"] for d in all_docs}

        if doc_options:
            selected_title = st.selectbox("Select Active Document to Deprecate", list(doc_options.keys()))
            if st.button("🚫 Deprecate Document", help="Retires chunks from active ChromaDB queries"):
                doc_id_to_dep = doc_options[selected_title]
                lm.deprecate_document(doc_id_to_dep)
                st.warning(f"Document '{selected_title}' marked DEPRECATED. Chunks will be omitted from future searches.")

    st.markdown("---")
    st.markdown("#### 📋 Document Lifecycle Registry")

    docs = lm.list_documents(include_deprecated=True)
    if docs:
        df = pd.DataFrame(docs)
        display_cols = ["doc_id", "title", "version", "is_active", "classification", "effective_date", "replaced_by"]
        valid_cols = [c for c in display_cols if c in df.columns]
        st.dataframe(df[valid_cols], use_container_width=True)
    else:
        st.info("No documents currently registered.")
