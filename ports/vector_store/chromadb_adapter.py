"""ChromaDB implementation of the VectorStorePort interface."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
import chromadb
from chromadb.config import Settings

from ports.base import VectorChunk, VectorSearchResult, VectorStorePort
from utils.config import resolve_path, load_config
from utils.logging_setup import setup_logger

logger = setup_logger("ports.vector_store.chromadb")


class ChromaDBAdapter(VectorStorePort):
    """Adapter for in-process persistent ChromaDB vector storage."""

    COLLECTIONS = [
        "legal_contracts",
        "technical_specs",
        "compliance_docs",
        "disruption_bulletins",
        "table_summaries",
    ]

    def __init__(self, chroma_dir: Optional[str | Path] = None):
        if chroma_dir is not None:
            self.persist_path = resolve_path(chroma_dir)
        else:
            cfg = load_config()
            self.persist_path = resolve_path(cfg["paths"]["chroma_dir"])

        self.persist_path.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=str(self.persist_path),
            settings=Settings(anonymized_telemetry=False, allow_reset=True),
        )
        self._collections: Dict[str, chromadb.Collection] = {}
        self._init_collections()

    def _init_collections(self):
        """Pre-initialize standard typed collections."""
        for col_name in self.COLLECTIONS:
            # Cosine distance space
            self._collections[col_name] = self.client.get_or_create_collection(
                name=col_name,
                metadata={"hnsw:space": "cosine"},
            )

    def get_collection(self, name: str) -> chromadb.Collection:
        if name not in self._collections:
            self._collections[name] = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]

    def upsert_chunks(self, collection_name: str, chunks: List[VectorChunk]) -> int:
        if not chunks:
            return 0

        col = self.get_collection(collection_name)
        ids = [c.chunk_id for c in chunks]
        documents = [c.text for c in chunks]
        
        # Format metadata for Chroma (primitive types only)
        metadatas = []
        for c in chunks:
            meta = dict(c.metadata)
            meta["doc_id"] = c.doc_id
            if "is_active" not in meta:
                meta["is_active"] = True
            # Convert list keywords to comma-separated string if present
            if "keywords" in meta and isinstance(meta["keywords"], list):
                meta["keywords"] = ", ".join(meta["keywords"])
            metadatas.append(meta)

        col.upsert(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    def query(
        self,
        collection_name: str,
        query_text: str,
        top_k: int = 5,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> List[VectorSearchResult]:
        output: List[VectorSearchResult] = []
        col = self.get_collection(collection_name)
        try:
            if col.count() == 0:
                return []
        except Exception:
            return []

        # Enforce is_active: True unless explicitly specified otherwise
        filter_dict = dict(where_filter) if where_filter else {}
        if "is_active" not in filter_dict:
            filter_dict["is_active"] = True

        try:
            results = col.query(
                query_texts=[query_text],
                n_results=top_k,
                where=filter_dict if filter_dict else None,
                include=["documents", "metadatas", "distances"],
            )
        except Exception as e:
            if "hnsw segment reader" in str(e).lower() or "nothing found on disk" in str(e).lower():
                try:
                    # ChromaDB 1.5.9 Windows Rust bindings sync: refresh server bindings and retry
                    if hasattr(self.client, "_server") and hasattr(self.client._server, "start"):
                        self.client._server.start()
                    fresh_col = self.client.get_collection(collection_name)
                    self._collections[collection_name] = fresh_col
                    results = fresh_col.query(
                        query_texts=[query_text],
                        n_results=top_k,
                        where=filter_dict if filter_dict else None,
                        include=["documents", "metadatas", "distances"],
                    )
                except Exception as retry_err:
                    logger.error("ChromaDB query failed on collection '%s': %s", collection_name, str(retry_err))
                    return []
            else:
                logger.error("ChromaDB query failed on collection '%s': %s", collection_name, str(e))
                return []

        if not results or not results["ids"] or not results["ids"][0]:
            return output

        ids = results["ids"][0]
        docs = results["documents"][0] if results.get("documents") else [""] * len(ids)
        metas = results["metadatas"][0] if results.get("metadatas") else [{}] * len(ids)
        distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

        for cid, doc, meta, dist in zip(ids, docs, metas, distances):
            # Chroma returns cosine distance in [0, 2]; similarity = 1 - (dist / 2) or max(0, 1 - dist)
            score = max(0.0, round(1.0 - float(dist), 4))
            doc_id = meta.get("doc_id", "")
            output.append(
                VectorSearchResult(
                    chunk_id=cid,
                    doc_id=doc_id,
                    text=doc,
                    metadata=meta,
                    score=score,
                )
            )

        return output

    def deprecate_by_doc_id(self, doc_id: str) -> int:
        count = 0
        for col_name, col in self._collections.items():
            res = col.get(where={"doc_id": doc_id}, include=["metadatas"])
            if res and res["ids"]:
                ids = res["ids"]
                updated_metas = []
                for meta in res["metadatas"]:
                    m = dict(meta)
                    m["is_active"] = False
                    updated_metas.append(m)
                col.update(ids=ids, metadatas=updated_metas)
                count += len(ids)
        return count

    def get_collection_stats(self) -> Dict[str, int]:
        stats = {}
        for col_name, col in self._collections.items():
            stats[col_name] = col.count()
        return stats
