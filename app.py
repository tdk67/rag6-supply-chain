"""Aethelgard Infra-GraphRAG: Main Application Shell.

A tri-modal sovereign infrastructure and supply chain intelligence engine
uniting hardware topologies (Graph DB), rigid inventory calculations (SQLite SSOT),
and unstructured legal contracts (Vector DB).
"""

from __future__ import annotations

import streamlit as st

from ui.tab_decision_console import render_tab_decision_console
from ui.tab_simulation import render_tab_simulation
from ui.tab_analytics import render_tab_analytics
from ui.tab_ingestion import render_tab_ingestion
from utils.config import load_config

# 1. Page Configuration & Theme
st.set_page_config(
    page_title="Aethelgard Infra-GraphRAG",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom Styling for Sovereign Theme
st.markdown(
    """
    <style>
    .main-header {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E3A8A;
        margin-bottom: 0px;
    }
    .sub-header {
        font-size: 1.05rem;
        color: #64748B;
        margin-bottom: 1.2rem;
    }
    .clearance-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .badge-legal { background-color: #EDE9FE; color: #5B21B6; }
    .badge-procurement { background-color: #FEF3C7; color: #92400E; }
    .badge-cto { background-color: #E0E7FF; color: #3730A3; }
    .badge-sre { background-color: #D1FAE5; color: #065F46; }
    </style>
    """,
    unsafe_allow_html=True,
)


def main():
    cfg = load_config()

    # 2. Sidebar Navigation & Persona Controls
    with st.sidebar:
        st.markdown("## 🛡️ Aethelgard")
        st.caption(f"**Version:** {cfg['app']['version']} | **Environment:** {cfg['app']['environment'].upper()}")
        st.markdown("---")

        st.markdown("### 👤 Active Persona Selector")
        persona_choice = st.selectbox(
            "Select Operational Role:",
            [
                "General Counsel / Legal",
                "Head of Procurement",
                "VP of Hardware / CTO",
                "Lead Cloud SRE",
            ],
            index=0,
            help="Enforces role-based clearance (ABAC) and filters sensitive collections.",
        )

        persona_map = {
            "General Counsel / Legal": ("LEGAL", "badge-legal", "Top Secret — Full Legal & Commercial Clearance"),
            "Head of Procurement": ("PROCUREMENT", "badge-procurement", "Financial & Supply Chain Clearance"),
            "VP of Hardware / CTO": ("CTO", "badge-cto", "Hardware Architecture & Compliance Clearance"),
            "Lead Cloud SRE": ("SRE", "badge-sre", "Operational Reliability & Telemetry Clearance (Legal Restricted)"),
        }
        role_code, badge_cls, clearance_desc = persona_map[persona_choice]

        st.markdown(
            f"<div class='clearance-badge {badge_cls}'>Clearance: {role_code}</div>",
            unsafe_allow_html=True,
        )
        st.caption(f"_{clearance_desc}_")

        st.markdown("---")
        st.markdown("### ⚙️ Engine Health & Models")
        st.info(
            f"**LLM Model:** `{cfg['llm']['model']}`\n\n"
            f"**Vector Store:** `ChromaDB (In-Process)`\n\n"
            f"**Knowledge Graph:** `NetworkX (332 Nodes)`\n\n"
            f"**SQL SSOT:** `SQLite (infrastructure.db)`"
        )
        st.caption("European Cloud Routing: Enabled (EU Data Residency)")

    # 3. Main Header
    st.markdown("<div class='main-header'>Aethelgard Infra-GraphRAG</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='sub-header'>Tri-Modal Sovereign Infrastructure & Supply Chain Disruption Intelligence Engine</div>",
        unsafe_allow_html=True,
    )

    # 4. Tab Navigation
    tab1, tab2, tab3, tab4 = st.tabs([
        "🧠 1. AI Decision Console",
        "🌐 2. Simulation & Data Studio",
        "📊 3. Knowledge Base Analytics",
        "📥 4. Ingestion & Lifecycle",
    ])

    with tab1:
        render_tab_decision_console(persona=role_code)

    with tab2:
        render_tab_simulation()

    with tab3:
        render_tab_analytics()

    with tab4:
        render_tab_ingestion()


if __name__ == "__main__":
    main()
