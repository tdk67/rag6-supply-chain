"""Unit tests for out-of-domain (OOD) refusal and SQL empty evidence behavior."""

from agent.orchestrator import AgentOrchestrator
from retrieval.sql_query import SQLQueryTool


def test_sql_query_tool_returns_empty_on_unknown_domain():
    """Verify P0 fix: failed SQL text-to-translation does NOT launder arbitrary rows."""
    tool = SQLQueryTool()
    res = tool.query("What is the recipe for chocolate chip cookies in Paris?")
    assert res.success is False
    assert res.row_count == 0
    assert len(res.rows) == 0


def test_orchestrator_ood_refusal_when_no_evidence():
    """Verify that an out-of-domain query with zero evidence returns REFUSED."""
    orch = AgentOrchestrator()
    # Query completely outside infrastructure, supplier, and contract domain
    resp = orch.process_query("What is the best technique to bake artisanal sourdough bread?")
    assert resp.confidence_score <= 30
    assert resp.confidence_level in ("REFUSED", "LOW")
    assert resp.is_complete is False or "REFUSED" in resp.confidence_level
