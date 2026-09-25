"""Adaptive Intent Router classifying queries into 6 GraphRAG architectural patterns."""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Optional
from pydantic import BaseModel

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ports.registry import AdapterRegistry
from utils.prompt_loader import get_prompt


class RoutingDecision(BaseModel):
    pattern: str
    pattern_name: str
    confidence: float
    tools_selected: list[str]
    rationale: str


class IntentRouter:
    """Classifies user queries into one of the 6 GraphRAG Architectural Patterns (Sarkar, 2026)."""

    PATTERNS = {
        "P1": "P1: Deterministic Text-to-Cypher",
        "P2": "P2: Parallel Hybrid",
        "P3": "P3: Sequential Graph-First",
        "P4": "P4: Sequential Table-First",
        "P5": "P5: Adaptive Router (Vector-Primary)",
        "P6": "P6: Agentic Multi-Step Loop",
    }

    def __init__(self):
        self.llm = AdapterRegistry.get_llm_provider()

    def route(self, query: str) -> RoutingDecision:
        # 1. Primary: Cognitive LLM Intent Classifier (if LLM is available)
        try:
            prompt = get_prompt("intent_classification.txt", {"question": query})
            system_prompt = (
                "You are an intent classifier for an enterprise Tri-Modal GraphRAG engine. "
                "Classify the question into one of the 6 GraphRAG patterns: P1, P2, P3, P4, P5, or P6."
            )
            llm_res = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.0).strip()
            for p_code, p_name in self.PATTERNS.items():
                if p_code in llm_res or p_name.lower() in llm_res.lower():
                    tools = self._get_tools_for_pattern(p_code)
                    return RoutingDecision(
                        pattern=p_code,
                        pattern_name=p_name,
                        confidence=0.92,
                        tools_selected=tools,
                        rationale=f"Classified via Dynamic LLM Classifier ({p_code}).",
                    )
        except Exception:
            # LLM key missing or call failed; proceed to semantic rule classification
            pass

        # 2. Secondary: Semantic Domain Heuristics
        lower = query.lower()

        # Pure Graph Topology (Single Points of Failure, Software Dependency Chains)
        if (
            "single point of failure" in lower
            or "only one" in lower
            or "single supplier" in lower
            or "single-source" in lower
            or "dependency" in lower
            or "cuda" in lower
            or "rocm" in lower
        ):
            return RoutingDecision(
                pattern="P1",
                pattern_name="P1: Deterministic Text-to-Cypher",
                confidence=0.88,
                tools_selected=["graph_query", "vector_search"],
                rationale="Graph topology audit detecting dependency chains and single-source relationships.",
            )

        # Blast Radius & Cascade (Geopolitical route blocks, upstream supplier halts)
        if any(k in lower for k in ["disrupt", "freight", "route", "bottleneck", "cascade", "blast radius", "taiwan"]):
            return RoutingDecision(
                pattern="P3",
                pattern_name="P3: Sequential Graph-First",
                confidence=0.89,
                tools_selected=["graph_query", "sql_query"],
                rationale="Geopolitical blast radius: graph traversal to find affected sub-tier nodes, followed by SQL financial impact aggregation.",
            )

        # Quantitative Comparisons (Side-by-side specs, unit costs)
        if any(k in lower for k in ["compare", "vs", "difference", "unit cost", "cheaper", "cost increase"]):
            return RoutingDecision(
                pattern="P4",
                pattern_name="P4: Sequential Table-First",
                confidence=0.87,
                tools_selected=["sql_query", "graph_query", "vector_search"],
                rationale="Quantitative aggregation across inventory tables followed by hardware specification context.",
            )

        # Compliance, Certifications & Legal Interpretation
        if any(k in lower for k in ["bsi", "c5", "eu ai act", "nis2", "conformity", "attestation", "residency", "audit"]):
            return RoutingDecision(
                pattern="P5",
                pattern_name="P5: Adaptive Router (Vector-Primary)",
                confidence=0.88,
                tools_selected=["vector_search", "graph_query"],
                rationale="Vector-primary search across sovereign compliance attestations and physical security boundaries.",
            )

        # Contractual Penalty & Purchase Order Joint Queries
        if any(k in lower for k in ["force majeure", "liquidated damages", "penalty", "late delivery", "breach", "ppa"]):
            return RoutingDecision(
                pattern="P2",
                pattern_name="P2: Parallel Hybrid",
                confidence=0.86,
                tools_selected=["vector_search", "sql_query"],
                rationale="Parallel retrieval: legal contractual penalty clauses cross-referenced with ERP purchase order values.",
            )

        # Default: Agentic Multi-Step Reflection Loop
        return RoutingDecision(
            pattern="P6",
            pattern_name="P6: Agentic Multi-Step Loop",
            confidence=0.80,
            tools_selected=["graph_query", "sql_query", "vector_search"],
            rationale="Complex scenario inquiry routed to full tri-modal agentic reflection loop.",
        )

    def _get_tools_for_pattern(self, pattern_code: str) -> list[str]:
        mapping = {
            "P1": ["graph_query"],
            "P2": ["vector_search", "sql_query"],
            "P3": ["graph_query", "sql_query"],
            "P4": ["sql_query", "graph_query", "vector_search"],
            "P5": ["vector_search", "graph_query"],
            "P6": ["graph_query", "sql_query", "vector_search"],
        }
        return mapping.get(pattern_code, ["graph_query", "sql_query", "vector_search"])
