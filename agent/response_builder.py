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
