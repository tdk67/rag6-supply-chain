"""Structured response builder formatting agent outputs with citations and diagrams."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class Citation(BaseModel):
    ref_id: str
    source_type: str  # "document" | "table" | "graph"
    source_file: str
    page_number: Optional[int] = None
    section: Optional[str] = None
    table: Optional[str] = None
    row_id: Optional[str] = None
    excerpt: str
    full_text: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Diagram(BaseModel):
    type: str = "mermaid"
    content: str


class Discrepancy(BaseModel):
    description: str
    severity: str  # "HIGH", "MEDIUM", "LOW"
    recommendation: str


class AgentResponse(BaseModel):
    answer_markdown: str
    confidence_score: int
    confidence_level: str  # "HIGH", "MEDIUM", "LOW", "REFUSED"
    is_complete: bool
    incompleteness_reason: Optional[str] = None
    tools_used: List[str] = Field(default_factory=list)
    pattern_selected: str
    reflection_passes: int = 1
    suggested_followups: List[str] = Field(default_factory=list)
    citations: List[Citation] = Field(default_factory=list)
    diagram: Optional[Diagram] = None
    discrepancies_detected: List[Discrepancy] = Field(default_factory=list)
    execution_trace: List[Dict[str, Any]] = Field(default_factory=list)

    def to_json(self) -> str:
        return json.dumps(self.model_dump(), indent=2)


def calculate_confidence_level(score: int) -> str:
    if score >= 85:
        return "HIGH"
    elif score >= 60:
        return "MEDIUM"
    elif score >= 30:
        return "LOW"
    return "REFUSED"


def format_context_for_llm(
    graph_data: Any,
    sql_data: Any,
    vector_chunks: List[Any],
    discrepancies: List[Discrepancy],
) -> str:
    """Format tri-modal context into structured, clearly labeled prompt sections."""
    parts = []

    if sql_data:
        parts.append(
            f"[RELATIONAL SQL SSOT DATA] ({len(sql_data)} records returned):\n"
            f"{json.dumps(sql_data, indent=2)}"
        )

    if graph_data:
        parts.append(
            f"[KNOWLEDGE GRAPH TOPOLOGY DATA]:\n"
            f"{json.dumps(graph_data, indent=2) if isinstance(graph_data, (dict, list)) else str(graph_data)}"
        )

    if vector_chunks:
        chunk_sections = []
        for idx, c in enumerate(vector_chunks, start=1):
            src = c.metadata.get("source_file", "document")
            sec = c.metadata.get("section_heading", "General")
            pg = c.metadata.get("page_number", 1)
            chunk_sections.append(f"Source [{idx}] ({src}, {sec}, Page {pg}):\n{c.text}")
        parts.append("[DOCUMENT & CONTRACTUAL CHUNKS]:\n" + "\n\n".join(chunk_sections))

    if discrepancies:
        disc_lines = [f"- {d.description} (Action: {d.recommendation})" for d in discrepancies]
        parts.append("[DETECTED INVENTORY DISCREPANCIES (ERP vs Dock Receipt)]:\n" + "\n".join(disc_lines))

    return "\n\n".join(parts) if parts else "No relevant context retrieved from database."


def extract_mermaid_and_followups(raw_llm_text: str) -> tuple[str, Optional[Diagram], List[str]]:
    """Extract optional mermaid diagram and suggested follow-up questions from LLM response."""
    import re

    diagram = None
    followups = []

    # Extract ```mermaid ... ``` blocks
    mermaid_match = re.search(r"```mermaid\s*(.*?)```", raw_llm_text, re.DOTALL)
    if mermaid_match:
        diagram_content = mermaid_match.group(1).strip()
        diagram = Diagram(type="mermaid", content=diagram_content)

    # Extract follow-up questions (bullet points ending in ? or under a follow-up header)
    followup_section = re.search(
        r"(?:Suggested Follow-ups?|Follow-up Questions?|Next Steps?)[:\n]+(.*?)(?=\n###|\Z)",
        raw_llm_text,
        re.DOTALL | re.IGNORECASE,
    )
    if followup_section:
        lines = followup_section.group(1).strip().split("\n")
        for line in lines:
            cleaned = re.sub(r"^[-*0-9.]+\s*", "", line).strip()
            if cleaned and len(cleaned) > 10:
                followups.append(cleaned)
                if len(followups) >= 2:
                    break

    if not followups:
        # Fallback search for lines with questions
        q_candidates = re.findall(r"[-*]\s*([^\n]+\?)", raw_llm_text)
        followups = [q.strip() for q in q_candidates if len(q.strip()) > 10][:2]

    return raw_llm_text, diagram, followups
