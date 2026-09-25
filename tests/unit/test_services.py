"""Unit tests for services layer (AnalyticsService and SimulationService)."""

from services.analytics_service import AnalyticsService
from services.simulation_service import SimulationService


def test_analytics_service_metrics():
    service = AnalyticsService()
    metrics = service.get_operational_metrics()
    assert metrics["total_components"] > 0
    assert metrics["total_val_eur"] > 0
    assert metrics["total_docs"] > 0
    assert metrics["graph_nodes"] > 0
    assert metrics["graph_edges"] > 0

    feed = service.get_discrepancy_feed(limit=5)
    assert not feed.empty
    assert "receipt_id" in feed.columns
    assert "po_number" in feed.columns


def test_simulation_service_scenarios():
    sim = SimulationService()

    # 1. Previews
    comps = sim.get_components_preview(limit=5)
    assert not comps.empty
    pos = sim.get_purchase_orders_preview(limit=5)
    assert not pos.empty
    discs = sim.get_dock_discrepancies_preview(limit=5)
    assert not discs.empty

    # 2. Apply Taiwan Embargo scenario
    res_taiwan = sim.apply_scenario("Scenario A: Taiwan Freight Embargo")
    assert res_taiwan["status"] == "MUTATED"
    assert "Taiwan" in res_taiwan["scenario"]

    # 3. Apply Submer Insolvency scenario
    res_submer = sim.apply_scenario("Scenario B: Submer Manifold Insolvency")
    assert res_submer["status"] == "MUTATED"
    assert "Submer" in res_submer["scenario"]

    # 4. Reset to Baseline
    res_base = sim.apply_scenario("Baseline (No Disruptions)")
    assert res_base["status"] == "RESET"

