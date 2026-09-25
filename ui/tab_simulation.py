"""Tab 2: Simulation & Data Studio.

Provides interactive toggles for disruption scenarios (Taiwan embargo, vendor insolvency)
and updates the SQLite SSOT and Graph projections deterministically via SimulationService.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from services.simulation_service import SimulationService


def render_tab_simulation():
    """Render the Disruption Simulator & Data Studio tab."""
    st.markdown("### ⚡ Sovereign Supply Chain Disruption Simulator")
    st.caption("Inject geopolitical shocks, vendor delays, and cooling failures; observe graph dependency cascades.")

    sim_service = SimulationService()
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown("#### Select Scenario")
        scenario = st.radio(
            "Disruption Condition",
            [
                "Baseline Normal",
                "Scenario A: Taiwan Freight Embargo",
                "Scenario B: Submer Manifold Insolvency",
            ],
            key="sim_scenario_radio",
        )

        if st.button("🚀 Apply Scenario to Infrastructure", type="primary", use_container_width=True):
            with st.spinner("Mutating SSOT and synchronizing Graph projections..."):
                res = sim_service.apply_scenario(scenario)
                st.success(res["message"])

        st.markdown("---")
        st.markdown("#### Master Data Reset")
        if st.button("🔄 Regenerate Full Synthetic BOM", use_container_width=True):
            with st.spinner("Regenerating BOM and seeding Knowledge Graph..."):
                res = sim_service.regenerate_master_baseline()
                st.success(res["message"])

    with col2:
        st.markdown("#### Live SSOT State Preview")
        tab_c, tab_p, tab_d = st.tabs(["📦 Components BOM", "📝 Purchase Orders", "⚠️ Dock Discrepancies"])

        with tab_c:
            df_comp = sim_service.get_components_preview(limit=15)
            st.dataframe(df_comp, use_container_width=True)

        with tab_p:
            df_po = sim_service.get_purchase_orders_preview(limit=15)
            st.dataframe(df_po, use_container_width=True)

        with tab_d:
            df_disc = sim_service.get_dock_discrepancies_preview(limit=15)
            st.dataframe(df_disc, use_container_width=True)
