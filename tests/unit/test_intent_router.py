"""Unit tests for Intent Router pattern selection."""

from agent.intent_router import IntentRouter


class OfflineMockLLM:
    """Mock LLM that simulates offline / fallback condition to verify heuristic routing."""
    def generate(self, *args, **kwargs):
        raise RuntimeError("LLM offline")


class CognitiveMockLLM:
    """Mock LLM returning deterministic pattern codes."""
    def __init__(self, pattern_code: str):
        self.code = pattern_code

    def generate(self, *args, **kwargs):
        return f"Based on analysis, the best pattern is {self.code}."


def test_intent_router_heuristic_patterns():
    """Verify heuristic routing fallback when LLM is unavailable."""
    router = IntentRouter(llm_provider=OfflineMockLLM())

    # P1: Single source
    r1 = router.route("Which components in our Open Rack v3 BOM have only one qualified supplier?")
    assert r1.pattern == "P1"

    # P2: Force majeure / penalty
    r2 = router.route("Vendor Supermicro is late on delivering PO-8821. Does Force Majeure apply or liquidated damages?")
    assert r2.pattern == "P2"

    # P3: Taiwan freight cascade
    r3 = router.route("If freight routes out of Taiwan are disrupted, what Tier-1 components are blocked?")
    assert r3.pattern == "P3"

    # P4: Compare MI300X vs H200
    r4 = router.route("Compare AMD MI300X vs NVIDIA H200 unit cost and lead time.")
    assert r4.pattern == "P4"

    # P5: Regulatory audit
    r5 = router.route("Audit proof of EU AI Act and BSI C5 data residency compliance.")
    assert r5.pattern == "P5"


def test_intent_router_cognitive_llm():
    """Verify primary cognitive LLM intent parsing."""
    router = IntentRouter(llm_provider=CognitiveMockLLM("P2"))
    r = router.route("Any ambiguous inquiry...")
    assert r.pattern == "P2"
    assert "Dynamic LLM Classifier" in r.rationale
