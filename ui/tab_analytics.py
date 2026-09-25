"""Tab 3: Knowledge Base Analytics Dashboard.

Displays system-wide operational metrics, RAG pattern distributions,
discrepancy alert feeds, and interactive PyVis / Mermaid knowledge graph visualizations.
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
from pathlib import Path
from typing import Dict, Any

from ports.registry import AdapterRegistry
from services.analytics_service import AnalyticsService
from utils.config import resolve_path, load_config


def generate_pyvis_network_html(max_nodes: int = 50) -> str:
    """Generate an interactive HTML network representation using pyvis."""
    try:
        from pyvis.network import Network
    except ImportError:
        return "<p>PyVis not installed.</p>"

    graph_adapter = AdapterRegistry.get_graph_store()
    G = graph_adapter.graph

    net = Network(height="500px", width="100%", bgcolor="#0F172A", font_color="#F8FAFC", directed=True)

    # Color palette by label
    color_map = {
        "Facility": "#3B82F6",  # Blue
        "Rack": "#10B981",      # Emerald
        "Chassis": "#06B6D4",   # Cyan
        "Component": "#8B5CF6", # Purple
        "Supplier": "#F59E0B",  # Amber
        "SubTierManufacturer": "#EC4899", # Pink
        "Country": "#EF4444",   # Red
        "CoolingLoop": "#0EA5E9", # Sky
        "ComplianceStandard": "#84CC16", # Lime
    }

    # Add priority nodes
    nodes_added = 0
    subgraph_nodes = set()

    # Pick key nodes first: Facility, Loops, Key Suppliers, Key GPUs
    priority_nodes = [
        "Facility-DC1-Frankfurt", "Loop-A", "Loop-B", "SUP-001", "SUP-002", "SUP-003",
        "SUP-004", "SUP-009", "SUP-010", "SKU-GPU-MI300X", "SKU-GPU-H200",
        "Rack-01", "Rack-12", "Country-Taiwan", "Country-Germany", "Country-France"
    ]

    for p in priority_nodes:
        if p in G:
            subgraph_nodes.add(p)
            for succ in G.successors(p):
                subgraph_nodes.add(succ)
                if len(subgraph_nodes) >= max_nodes:
                    break
        if len(subgraph_nodes) >= max_nodes:
            break

    for n in list(subgraph_nodes)[:max_nodes]:
        data = G.nodes[n]
        label = data.get("label", "Node")
        name = data.get("name") or data.get("part_name") or n
        color = color_map.get(label, "#94A3B8")
        net.add_node(n, label=f"{label}: {name[:20]}", title=f"ID: {n}\nType: {label}\nName: {name}", color=color)

    # Add edges between added nodes
    for u in net.nodes:
        u_id = u["id"]
        for v_id in G.successors(u_id):
            if any(n["id"] == v_id for n in net.nodes):
                edges = G.get_edge_data(u_id, v_id)
                rel = list(edges.values())[0].get("relation", "") if edges else ""
                net.add_edge(u_id, v_id, title=rel, label=rel)

    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravitationalConstant": -3000,
          "centralGravity": 0.3,
          "springLength": 95
        }
      }
    }
    """)

    html_content = net.generate_html()
    return html_content


def get_analytics_metrics() -> Dict[str, Any]:
    """Retrieve operational KPIs via AnalyticsService."""
    return AnalyticsService().get_operational_metrics()


def render_tab_analytics():
    """Render the Knowledge Base Analytics Dashboard tab."""
    st.markdown("### 📊 Sovereign Infrastructure & RAG Analytics")
    st.caption("Live operational intelligence, hardware topology metrics, and supply chain telemetry.")

    analytics_svc = AnalyticsService()
    metrics = analytics_svc.get_operational_metrics()

    # Top Metric Tiles (Hero section)
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("Total Active BOM SKUs", f"{metrics['total_components']:,}", "100% OCP Catalog")
    with c2:
        st.metric("Total Capital Exposure", f"€{metrics['total_val_eur']:,.2f}", "85 Active POs")
    with c3:
        st.metric("Graph Topology", f"{metrics['graph_nodes']} Nodes", f"{metrics['graph_edges']} Edges")
    with c4:
        st.metric("Sovereign Contracts", f"{metrics['total_docs']} Active", "BSI C5 & FIDIC")

    st.markdown("---")

    # Main Visualizations
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown("#### 🕸️ Hardware & Supplier Knowledge Graph")
        st.caption("Interactive multi-tier network (Zoom and pan to explore dependencies).")
        html_net = generate_pyvis_network_html(max_nodes=40)
        import streamlit.components.v1 as components
        components.html(html_net, height=520, scrolling=False)

    with col_right:
        st.markdown("#### 🎯 GraphRAG Pattern Distribution")
        pattern_data = pd.DataFrame({
            "Pattern": [
                "P1: Text-to-Cypher",
                "P2: Parallel Hybrid",
                "P3: Sequential Graph-First",
                "P4: Sequential Table-First",
                "P5: Adaptive Router",
                "P6: Agentic Loop",
            ],
            "Benchmark Queries": [2, 2, 1, 1, 1, 3],
        })
        st.bar_chart(pattern_data.set_index("Pattern"), color="#3B82F6")

        st.markdown("#### ⚠️ Discrepancy Alert Feed (Trap 2 Auditing)")
        disc_df = analytics_svc.get_discrepancy_feed(limit=4)
        for _, row in disc_df.iterrows():
            st.warning(f"**{row['receipt_id']} ({row['po_number']})**: {row['discrepancy_notes']}")
