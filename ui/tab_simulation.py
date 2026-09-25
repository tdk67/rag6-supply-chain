"""Tab 2: Simulation & Data Studio.

Provides interactive toggles for disruption scenarios (Taiwan embargo, vendor insolvency)
and updates the SQLite SSOT and Graph projections deterministically.
"""

from __future__ import annotations

import sqlite3
import streamlit as st
import pandas as pd
from pathlib import Path
from utils.config import resolve_path, load_config
from scripts.seed_graph import build_knowledge_graph


def apply_disruption_scenario(scenario_name: str) -> dict:
    """Apply deterministic disruption mutations to SQLite SSOT and compile graph."""
    cfg = load_config()
    db_path = resolve_path(cfg["paths"]["sqlite_db"])
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    if scenario_name == "Scenario A: Taiwan Freight Embargo":
        # Add 16 weeks to lead time for all Taiwan-origin components
        cur.execute(
            """
            UPDATE components
            SET lead_time_weeks = lead_time_weeks + 16
            WHERE country_of_origin = 'Taiwan' OR tier2_manufacturer LIKE '%Taiwan%' OR tier2_manufacturer LIKE '%TSMC%'
            """
        )
        affected_comps = cur.rowcount
        conn.commit()
        conn.close()

        # Recompile graph projection (CQRS)
        build_knowledge_graph()
        return {
            "scenario": scenario_name,
            "affected_components": affected_comps,
            "status": "MUTATED",
            "message": f"Applied +16 weeks lead time penalty to {affected_comps} Taiwan-dependent components.",
        }

    elif scenario_name == "Scenario B: Submer Manifold Insolvency":
        # Mark Submer as IN_RESTRUCTURING and freeze purchase orders
        cur.execute("UPDATE suppliers SET status = 'IN_RESTRUCTURING' WHERE name LIKE '%Submer%'")
        cur.execute("UPDATE purchase_orders SET status = 'DELAYED' WHERE supplier_id = 'SUP-004'")
        conn.commit()
        conn.close()

        build_knowledge_graph()
        return {
            "scenario": scenario_name,
            "status": "MUTATED",
            "message": "Submer marked as IN_RESTRUCTURING. Purchase orders frozen.",
        }

    else:  # Baseline Normal
        # Reset suppliers and regenerate baseline
        cur.execute("UPDATE suppliers SET status = 'ACTIVE' WHERE status = 'IN_RESTRUCTURING'")
        conn.commit()
        conn.close()
        from scripts.generate_bom import generate_bom_data
        generate_bom_data()
        build_knowledge_graph()
        return {
            "scenario": "Baseline Normal",
            "status": "RESET",
            "message": "System restored to baseline normal operating parameters.",
        }


def render_tab_simulation():
    """Render the Simulation & Data Studio UI tab."""
    st.markdown("### 🌐 Sovereign Supply Chain Disruption Simulator")
    st.caption("Mutate the Single Source of Truth (SSOT) to test system resilience against real-world geopolitical shocks.")

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
                res = apply_disruption_scenario(scenario)
                st.success(res["message"])

        st.markdown("---")
        st.markdown("#### Master Data Reset")
        if st.button("🔄 Regenerate Full Synthetic BOM", use_container_width=True):
            with st.spinner("Regenerating BOM and seeding Knowledge Graph..."):
                from scripts.generate_bom import generate_bom_data
                generate_bom_data()
                build_knowledge_graph()
                st.success("BOM and Knowledge Graph regenerated successfully!")

    with col2:
        st.markdown("#### Live SSOT State Preview")
        cfg = load_config()
        db_path = resolve_path(cfg["paths"]["sqlite_db"])
        conn = sqlite3.connect(db_path)

        tab_c, tab_p, tab_d = st.tabs(["📦 Components BOM", "📝 Purchase Orders", "⚠️ Dock Discrepancies"])

        with tab_c:
            df_comp = pd.read_sql_query(
                "SELECT sku, part_name, category, country_of_origin, unit_cost_eur, lead_time_weeks, current_stock FROM components LIMIT 15",
                conn,
            )
            st.dataframe(df_comp, use_container_width=True)

        with tab_p:
            df_po = pd.read_sql_query(
                "SELECT po_number, sku, supplier_id, status, quantity, total_val_eur, agreed_delivery_date FROM purchase_orders LIMIT 15",
                conn,
            )
            st.dataframe(df_po, use_container_width=True)

        with tab_d:
            df_disc = pd.read_sql_query(
                "SELECT d.receipt_id, d.po_number, po.quantity AS ordered_qty, d.units_received, d.discrepancy_notes "
                "FROM dock_receipts d JOIN purchase_orders po ON d.po_number = po.po_number "
                "WHERE d.discrepancy_flag = 1",
                conn,
            )
            st.dataframe(df_disc, use_container_width=True)

        conn.close()
