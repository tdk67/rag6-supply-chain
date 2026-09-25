"""Tool 1: Semantic Vector Search Tool with Role-Based ABAC Persona filtering."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ports.base import VectorSearchResult
from ports.registry import AdapterRegistry
from utils.config import load_config


# Attribute-Based Access Control (ABAC) persona clearance mappings
PERSONA_PERMISSIONS = {
    "LEGAL": ["legal_contracts", "compliance_docs", "disruption_bulletins", "technical_specs"],
    "PROCUREMENT": ["legal_contracts", "disruption_bulletins", "technical_specs"],
    "CTO": ["technical_specs", "compliance_docs", "disruption_bulletins"],
    "SRE": ["technical_specs", "disruption_bulletins"],  # SRE restricted: NO legal_contracts!
}


class VectorSearchToolResult(BaseModel):
    success: bool
    persona: str
    collections_searched: List[str]
    total_chunks_found: int
    chunks: List[VectorSearchResult] = Field(default_factory=list)
    execution_time_ms: float = 0.0
    abac_blocked: bool = False
    message: Optional[str] = None


class VectorSearchTool:
    """Executes semantic similarity queries against ChromaDB with ABAC clearance enforcement."""

    def __init__(self):
        self.vector_store = AdapterRegistry.get_vector_store()
        cfg = load_config()
        self.default_top_k = int(cfg.get("retrieval", {}).get("top_k", 5))
        self.similarity_threshold = float(cfg.get("retrieval", {}).get("similarity_threshold", 0.35))

    def search(
        self,
        query_text: str,
        persona: str = "LEGAL",
        target_collection: Optional[str] = None,
        top_k: Optional[int] = None,
        where_filter: Optional[Dict[str, Any]] = None,
    ) -> VectorSearchToolResult:
        """Search collections permitted for active persona."""
        start_time = time.perf_counter()
        normalized_persona = persona.upper().strip()
        allowed_collections = PERSONA_PERMISSIONS.get(normalized_persona, ["technical_specs", "disruption_bulletins"])

        # If user/agent specifies a collection, verify ABAC clearance
        if target_collection:
            if target_collection not in allowed_collections:
                elapsed = round((time.perf_counter() - start_time) * 1000, 2)
                return VectorSearchToolResult(
                    success=False,
                    persona=normalized_persona,
                    collections_searched=[],
                    total_chunks_found=0,
                    execution_time_ms=elapsed,
                    abac_blocked=True,
                    message=f"ABAC Clearance Violation: Persona '{normalized_persona}' does not possess security clearance for collection '{target_collection}'. Access denied.",
                )
            collections_to_search = [target_collection]
        else:
            collections_to_search = allowed_collections

        k = top_k or self.default_top_k
        all_results: List[VectorSearchResult] = []

        for col in collections_to_search:
            col_results = self.vector_store.query(
                collection_name=col,
                query_text=query_text,
                top_k=k,
                where_filter=where_filter,
            )
            # Filter by threshold
            for res in col_results:
                if res.score >= self.similarity_threshold:
                    all_results.append(res)

        # Sort combined results by score descending
        all_results.sort(key=lambda x: x.score, reverse=True)
        top_results = all_results[:k]

        elapsed = round((time.perf_counter() - start_time) * 1000, 2)
        return VectorSearchToolResult(
            success=True,
            persona=normalized_persona,
            collections_searched=collections_to_search,
            total_chunks_found=len(top_results),
            chunks=top_results,
            execution_time_ms=elapsed,
            abac_blocked=False,
        )
