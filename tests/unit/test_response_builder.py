"""Unit tests for response builder and citation schema."""

from agent.response_builder import (
    AgentResponse,
    Citation,
    Diagram,
    Discrepancy,
    calculate_confidence_level,
)


def test_confidence_level_thresholds():
    assert calculate_confidence_level(95) == "HIGH"
    assert calculate_confidence_level(85) == "HIGH"
    assert calculate_confidence_level(75) == "MEDIUM"
    assert calculate_confidence_level(50) == "LOW"
    assert calculate_confidence_level(20) == "REFUSED"


def test_agent_response_serialization():
    resp = AgentResponse(
        answer_markdown="### Test Assessment\nClaim grounded in contract [1].",
        confidence_score=92,
        confidence_level="HIGH",
        is_complete=True,
        tools_used=["vector_search", "sql_query"],
        pattern_selected="P2: Parallel Hybrid",
        citations=[
            Citation(
                ref_id="[1]",
                source_type="document",
                source_file="Supermicro_GPU_Nodes_MSA.pdf",
                page_number=1,
                section="Section 18.2",
                excerpt="Liquidated damages 0.5% per week",
            )
        ],
        diagram=Diagram(type="mermaid", content="graph TD; A-->B;"),
        discrepancies_detected=[
            Discrepancy(
                description="PO ordered 64, dock receipt 32",
                severity="HIGH",
                recommendation="Audit physical inventory",
            )
        ],
    )

    json_str = resp.to_json()
    assert "Supermicro_GPU_Nodes_MSA.pdf" in json_str
    assert "PO ordered 64, dock receipt 32" in json_str
    assert resp.confidence_level == "HIGH"
