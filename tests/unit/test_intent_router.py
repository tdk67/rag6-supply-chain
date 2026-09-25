"""Unit tests for Intent Router pattern selection."""

from agent.intent_router import IntentRouter


def test_intent_router_patterns():
    router = IntentRouter()

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
