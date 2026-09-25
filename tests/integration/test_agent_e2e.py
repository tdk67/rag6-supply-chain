"""End-to-End integration tests for Agent Orchestrator across benchmark queries."""

from agent.orchestrator import AgentOrchestrator


def test_agent_e2e_benchmark_q1():
    orch = AgentOrchestrator()
    q1 = "If geopolitical conflict disrupts freight routes out of Taiwan, which Tier-1 hardware components are directly or indirectly blocked, which sub-tier suppliers are the bottlenecks, and what is our total affected order value?"
    resp = orch.process_query(q1, persona="PROCUREMENT")

    assert resp.is_complete is True
    assert resp.confidence_score >= 85
    assert resp.pattern_selected == "P3: Sequential Graph-First"
    assert "graph_query" in resp.tools_used
    assert len(resp.citations) >= 1
    assert resp.diagram is not None


def test_agent_e2e_benchmark_q2():
    orch = AgentOrchestrator()
    q2 = "Vendor Supermicro is 10 weeks late on delivering 64 liquid-cooled GPU chassis modules. Does our MSA allow them to claim Force Majeure, or are we entitled to liquidated damages, and what is the maximum penalty cap?"
    resp = orch.process_query(q2, persona="LEGAL")

    assert resp.is_complete is True
    assert "P2: Parallel Hybrid" in resp.pattern_selected
    assert "Force Majeure" in resp.answer_markdown
    assert "59,200" in resp.answer_markdown or "1,184,000" in resp.answer_markdown
    assert len(resp.citations) >= 1


def test_agent_e2e_discrepancy_detection():
    orch = AgentOrchestrator()
    q_disc = "Check purchase order PO-8821 delivery status and verify dock receipts for discrepancies."
    resp = orch.process_query(q_disc, persona="PROCUREMENT")

    assert len(resp.discrepancies_detected) >= 1
    disc = resp.discrepancies_detected[0]
    assert "PO-8821" in disc.description
    assert disc.severity == "HIGH"
