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
from utils.config import load_config, get_secret

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

    # Optional Deployment Authentication Gate (PRD §13.4, Review #2 P0-6)
    app_token = get_secret("APP_ACCESS_TOKEN")
    if app_token:
        if st.session_state.get("authenticated_token") != app_token:
            st.markdown("### 🔒 Aethelgard Infra-GraphRAG — Deployment Access Gate")
            st.info("This instance is secured with an environment access token. Please enter the token to proceed.")
            token_input = st.text_input("Access Token:", type="password", key="app_auth_token_input")
            if st.button("Authenticate", type="primary"):
                if token_input == app_token:
                    st.session_state["authenticated_token"] = token_input
                    st.rerun()
                else:
                    st.error("Invalid access token. Access denied.")
            return

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
        st.markdown("### 🔑 OpenRouter API Configuration")
        from utils.config import get_secret
        from ports.llm_provider.openrouter_adapter import OpenRouterAdapter

        stored_env_key = get_secret("OPENROUTER_API_KEY") or ""
        has_env_key = bool(stored_env_key and stored_env_key.strip() not in ("", "placeholder_key", "sk-or-your-key-here"))

        if has_env_key:
            masked_env = f"sk-or-••••{stored_env_key[-4:]}" if len(stored_env_key) > 8 else "sk-or-••••"
            st.caption(f"🔒 **Server Key Configured:** `{masked_env}`")

        session_key = st.session_state.get("session_llm_key", "")

        api_key_input = st.text_input(
            "Session API Key Override:",
            value=session_key,
            type="password",
            placeholder="sk-or-v1-... (optional)",
            help="Enter a personal OpenRouter key for this browser session. If left blank, server defaults are used.",
            key="ui_session_api_key_input",
        )

        col_val1, col_val2 = st.columns(2)
        with col_val1:
            if st.button("🔌 Verify Key", key="btn_validate_key", use_container_width=True):
                check_key = api_key_input.strip() or stored_env_key
                with st.spinner("Connecting to OpenRouter..."):
                    valid, msg = OpenRouterAdapter.validate_api_key(check_key)
                    if valid:
                        if api_key_input.strip():
                            st.session_state["session_llm_key"] = api_key_input.strip()
                        st.success("Verified!")
                        st.caption(msg)
                    else:
                        st.error("Validation Failed")
                        st.caption(msg)
        with col_val2:
            if api_key_input.strip():
                if st.button("💾 Apply Key", key="btn_apply_key", use_container_width=True):
                    valid, msg = OpenRouterAdapter.validate_api_key(api_key_input.strip())
                    if valid:
                        st.session_state["session_llm_key"] = api_key_input.strip()
                        st.success("Applied to session!")
                    else:
                        st.error(f"Cannot apply: {msg}")

        active_has_key = bool(st.session_state.get("session_llm_key") or has_env_key)
        if active_has_key:
            st.markdown("🟢 **Status:** Dynamic LLM Active")
        else:
            st.markdown("🟡 **Status:** Synthesis Offline (Retrieval active; enter key above)")

        st.markdown("---")
        st.markdown("### ⚙️ Engine Health & Models")
        g_stats = AdapterRegistry.get_graph_store().get_stats()
        st.info(
            f"**LLM Model:** `{cfg['llm']['model']}`\n\n"
            f"**Vector Store:** `ChromaDB (In-Process)`\n\n"
            f"**Knowledge Graph:** `NetworkX ({g_stats['total_nodes']} Nodes, {g_stats['total_edges']} Edges)`\n\n"
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
