"""End-to-End integration tests for Agent Orchestrator across benchmark queries."""

from typing import Dict, List, Optional
import pytest

from agent.orchestrator import AgentOrchestrator
from ports.base import LLMProviderPort
from ports.registry import AdapterRegistry


class DeterministicTestLLM(LLMProviderPort):
    """Deterministic LLM mock for end-to-end integration testing without external API calls."""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.generate_chat(messages, temperature=temperature, max_tokens=max_tokens)

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        full_text = " ".join([m.get("content", "") for m in messages])
        lower = full_text.lower()

        # Intent classification prompt check
        if "classify" in lower or "graphrag architectural patterns" in lower:
            if "taiwan" in lower:
                return '{"pattern": "P3", "confidence": 0.95, "reasoning": "Sequential graph-first dependency cascade"}'
            if "supermicro" in lower or "force majeure" in lower:
                return '{"pattern": "P2", "confidence": 0.95, "reasoning": "Parallel hybrid document and contract audit"}'
            if "po-" in lower or "dock" in lower or "receipt" in lower or "discrepanc" in lower:
                return '{"pattern": "P4", "confidence": 0.95, "reasoning": "Sequential table-first purchase order and receipt verification"}'
            return '{"pattern": "P1", "confidence": 0.85, "reasoning": "Standard direct lookup"}'

        # Answer synthesis: Q1 Taiwan
        if "taiwan" in lower and ("freight" in lower or "disrupt" in lower or "order value" in lower):
            return (
                "### Sovereign Supply Chain Risk Assessment: Taiwan Freight Corridor Disruptions\n\n"
                "Geopolitical disruption along the Taiwan shipping corridor directly impacts Tier-1 server assembly. "
                "The primary bottlenecks trace to advanced packaging and substrate facilities. "
                "Based on SQLite order records, the total affected order value is approximately €5,864,000.00.\n\n"
                "```mermaid\n"
                "graph TD\n"
                "  TSMC[TSMC Taiwan] --> Substrate[ABF Substrate]\n"
                "  Substrate --> GPU[MI300X Accelerator]\n"
                "  GPU --> Server[HPC Blade Server]\n"
                "```\n\n"
                "### Suggested Follow-ups:\n"
                "- What are alternative packaging suppliers in the EU?\n"
                "- How much safety buffer stock is available for MI300X?\n"
            )

        # Answer synthesis: Q2 Supermicro & Force Majeure
        if "supermicro" in lower or "force majeure" in lower or "liquidated damages" in lower:
            return (
                "### Contractual & Legal Liability Assessment: Supermicro Delay\n\n"
                "Under MSA Section 14 (Force Majeure), component shortages and commercial delays do not constitute Force Majeure. "
                "Under Section 8.2 (Liquidated Damages), the buyer is entitled to 0.5% per week of delay up to a 5.0% cap. "
                "For PO-8821 with total value €1,184,000.00, the calculated liquidated damages penalty is capped at €59,200.00."
            )

        return "Synthesized executive response grounded in retrieved context."


class FailingTestLLM(LLMProviderPort):
    """LLM provider that simulates API failure or missing keys."""

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        raise RuntimeError("OpenRouter API error (HTTP 429): Rate limit exceeded or insufficient credits")

    def generate_chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        raise RuntimeError("OpenRouter API error (HTTP 429): Rate limit exceeded or insufficient credits")


@pytest.fixture(autouse=True)
def setup_test_llm():
    """Ensure tests run with deterministic LLM provider by default."""
    original_llm = AdapterRegistry._llm_provider
    AdapterRegistry.set_llm_provider(DeterministicTestLLM())
    yield
    AdapterRegistry._llm_provider = original_llm


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
    assert "Taiwan" in resp.answer_markdown


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


def test_agent_e2e_surfaces_real_error_when_llm_fails():
    """Verifies strict 'no fakes/no fallbacks' rule: real errors are surfaced with real context."""
    AdapterRegistry.set_llm_provider(FailingTestLLM())
    orch = AgentOrchestrator()
    q = "Vendor Supermicro is late on delivering liquid-cooled GPU chassis modules."
    resp = orch.process_query(q, persona="LEGAL")

    # Synthesis must not pretend or silently return fake success
    assert resp.is_complete is False
    assert "OpenRouter API error (HTTP 429)" in (resp.incompleteness_reason or "")
    assert "OpenRouter API error (HTTP 429)" in resp.answer_markdown
    # But real retrieved context and citations must still be transparently present
    assert len(resp.citations) >= 1
