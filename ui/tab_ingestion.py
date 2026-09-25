"""Tab 4: Document Ingestion & Lifecycle Manager.

Enables drag-and-drop file ingestion, document registration, version deprecation,
and real-time ChromaDB vector indexing.
"""

from __future__ import annotations

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


def handle_file_upload(uploaded_file, version: str = "1.0") -> dict:
    """Process uploaded file, save to data/documents/, register in SQLite, and index in ChromaDB."""
    cfg = load_config()
    docs_dir = resolve_path(cfg["paths"]["documents_dir"])
    docs_dir.mkdir(parents=True, exist_ok=True)

    dest_path = docs_dir / uploaded_file.name
    with open(dest_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    lm = DocumentLifecycleManager()
    reg_res = lm.register_document(dest_path, version=version)

    embedder = DocumentEmbedder()
    chunks_count = embedder.index_document(dest_path)

    return {
        "status": "SUCCESS",
        "doc_id": reg_res.get("doc_id"),
        "filename": uploaded_file.name,
        "version": version,
        "chunks_indexed": chunks_count,
    }


def render_tab_ingestion():
    """Render Document Ingestion & Lifecycle Manager tab."""
    st.markdown("### 📥 Sovereign Knowledge Ingestion & Lifecycle Manager")
    st.caption("Upload new contracts, rotate versions, deprecate obsolete specifications, and update ChromaDB vector indices.")

    col_up, col_actions = st.columns([2, 1])

    with col_up:
        st.markdown("#### Upload Document")
        uploaded = st.file_uploader(
            "Select PDF or TXT Document to Ingest",
            type=["pdf", "txt"],
            key="file_uploader_widget",
        )
        version_input = st.text_input("Document Version", value="1.0", key="ingest_version_input")

        if uploaded is not None:
            if st.button("⚡ Parse, Register & Embed into ChromaDB", type="primary"):
                with st.spinner(f"Ingesting {uploaded.name}..."):
                    try:
                        res = handle_file_upload(uploaded, version=version_input)
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
