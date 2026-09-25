"""Vector indexing pipeline that embeds chunks into ChromaDB collections."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ingestion.parser import parse_document
from ingestion.chunker import chunk_document
from ports.base import VectorChunk, VectorSearchResult
from ports.registry import AdapterRegistry
from utils.config import resolve_path, load_config


COLLECTION_MAP = {
    "LEGAL_COMMERCIAL": "legal_contracts",
    "TECHNICAL_SPEC": "technical_specs",
    "COMPLIANCE_AUDIT": "compliance_docs",
    "DISRUPTION_BULLETIN": "disruption_bulletins",
    "GENERAL": "table_summaries",
}


class DocumentEmbedder:
    """Manages document chunking, collection routing, and ChromaDB vector indexing."""

    def __init__(self):
        self.vector_store = AdapterRegistry.get_vector_store()

    def index_document(self, file_path: str | Path) -> int:
        """Parse, chunk, and index a single document into its target collection."""
        parsed = parse_document(file_path)
        chunks = chunk_document(parsed)
        col_name = COLLECTION_MAP.get(parsed.classification, "table_summaries")
        inserted = self.vector_store.upsert_chunks(col_name, chunks)
        return inserted

    def index_directory(self, docs_dir: Optional[str | Path] = None) -> Dict[str, int]:
        """Index all PDF and TXT documents in the documents directory."""
        if docs_dir is None:
            cfg = load_config()
            docs_dir = resolve_path(cfg["paths"]["documents_dir"])
        else:
            docs_dir = resolve_path(docs_dir)

        summary: Dict[str, int] = {}
        pdf_files = list(docs_dir.glob("*.pdf"))

        for pdf in pdf_files:
            try:
                cnt = self.index_document(pdf)
                summary[pdf.name] = cnt
            except Exception as e:
                print(f"Error indexing {pdf.name}: {e}")

        return summary

    def query(
        self,
        query_text: str,
        collection_name: str = "legal_contracts",
        top_k: int = 5,
        where_filter: Optional[Dict] = None,
    ) -> List[VectorSearchResult]:
        """Query top_k similar chunks in a specific collection."""
        return self.vector_store.query(
            collection_name=collection_name,
            query_text=query_text,
            top_k=top_k,
            where_filter=where_filter,
        )


def index_all():
    """Convenience CLI function to index all documents."""
    embedder = DocumentEmbedder()
    res = embedder.index_directory()
    print(f"Indexed {len(res)} documents into ChromaDB:")
    for fn, count in res.items():
        print(f"  - {fn}: {count} chunks")
    stats = embedder.vector_store.get_collection_stats()
    print("Collection counts:", stats)


if __name__ == "__main__":
    index_all()
