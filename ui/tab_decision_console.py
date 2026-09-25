"""Tab 1: AI Decision Console.

Provides executive conversational interface with:
- 1-Click Benchmark Carousel (10 benchmark questions from PRD §7)
- Role-based persona selector (CTO, Procurement, Legal, SRE)
- Streaming 'Glass Box' reflection loop thought trace (st.status)
- Interactive Confidence Gauge & clickable citation pills
- Automatic Mermaid diagram rendering & discrepancy alert banners
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional
import streamlit as st

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.orchestrator import AgentOrchestrator
from agent.response_builder import AgentResponse


BENCHMARK_QUESTIONS = [
    (
        "Q1: Taiwan Geopolitical Embargo",
        "If geopolitical conflict disrupts freight routes out of Taiwan, which Tier-1 hardware components are directly or indirectly blocked, which sub-tier suppliers are the bottlenecks, and what is our total affected order value?",
    ),
    (
        "Q2: Supermicro Force Majeure & Penalty Cap",
        "Vendor Supermicro is 10 weeks late on delivering 64 liquid-cooled GPU chassis modules. Does our MSA allow them to claim Force Majeure, or are we entitled to liquidated damages, and what is the maximum penalty cap?",
    ),
    (
        "Q3: Single Point of Failure (SPOF) Audit",
        "Which components in our Open Rack v3 BOM currently have ONLY ONE qualified supplier, creating a single point of failure?",
    ),
    (
        "Q4: AMD MI300X vs NVIDIA H200 Comparison",
        "Compare AMD Instinct MI300X vs NVIDIA H200 in terms of lead time, unit cost, power draw per rack, and memory bandwidth per Euro.",
    ),
    (
        "Q5: EU AI Act & BSI C5 Sovereignty Audit",
        "An enterprise banking client requires audit proof of EU AI Act data residency and NIS2 supply chain security compliance. What certifications can we provide?",
    ),
    (
        "Q6: Hall 1 Cooling Pump Failure & District Heat PPA",
        "If Primary Coolant Loop Pump B fails in Hall 1, which server racks lose secondary cooling redundancy, and does a shutdown breach our District Heating PPA?",
    ),
    (
        "Q7: Broadcom Transceiver Price Hike",
        "Broadcom announced a 15% price increase on 800G optical transceivers. What is our total project cost increase, can our contracts lock in old pricing, and what OCP-compliant replacements exist?",
    ),
    (
        "Q8: AMD ROCm Driver Compatibility",
        "Can we run Mistral-Large and Llama-3-70B on AMD MI300X servers without CUDA dependencies, and what ROCm version is certified?",
    ),
    (
        "Q9: Submer Insolvency & Frozen Deliveries",
        "Cooling vendor Submer has entered debt restructuring. Which in-flight rack assemblies are frozen, what warranty claims are unfulfilled, and what is our contingency plan?",
    ),
    (
        "Q10: US/China Trade Embargo & Spare Runway",
        "In the event of a total US and China trade embargo, how many months can our data center operate without new imported spare parts, which components have zero European substitutes, and what is our customer SLA liability?",
    ),
]


def render_tab_decision_console(persona: str = "LEGAL"):
    """Render Tab 1: AI Decision Console."""
    st.markdown("### 🧠 Sovereign AI Infrastructure Decision Console")
    st.caption("Tri-modal agentic intelligence bridging physical hardware topologies, inventory financials, and legal contracts.")

    # 1-Click Benchmark Carousel
    st.markdown("#### ⚡ 1-Click Executive Benchmark Carousel")
    options = ["-- Select a Benchmark Question --"] + [f"{item[0]}: {item[1][:80]}..." for item in BENCHMARK_QUESTIONS]
    selected_idx = st.selectbox(
        "Choose an acceptance benchmark test query:",
        options,
        index=0,
        key="benchmark_selector",
    )

    preset_query = ""
    if selected_idx != "-- Select a Benchmark Question --":
        # Extract question index
        idx = options.index(selected_idx) - 1
        preset_query = BENCHMARK_QUESTIONS[idx][1]

    # Initialize chat history in session state
    if "chat_messages" not in st.session_state:
        st.session_state.chat_messages = []

    # Display existing chat messages
    for msg in st.session_state.chat_messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            if "response_obj" in msg:
                resp: AgentResponse = msg["response_obj"]
                _render_response_extras(resp)

    # Chat Input
    user_query = st.chat_input("Ask about data center BOM, supplier contracts, disruption cascades, or compliance...")

    # If preset was selected via dropdown button
    trigger_query = user_query
    if preset_query and st.button(f"▶️ Run Selected Benchmark: {BENCHMARK_QUESTIONS[idx][0]}", type="primary"):
        trigger_query = preset_query

    if trigger_query:
        # Display user message
        st.session_state.chat_messages.append({"role": "user", "content": trigger_query})
        with st.chat_message("user"):
            st.markdown(trigger_query)

        # Agent processing with live streaming status
        with st.chat_message("assistant"):
            orch = AgentOrchestrator()
            
            with st.status("Executing Tri-Modal GraphRAG Loop...", expanded=True) as status_box:
                def update_callback(msg: str):
                    status_box.write(msg)

                response = orch.process_query(
                    query=trigger_query,
                    persona=persona,
                    status_callback=update_callback,
                )
                status_box.update(
                    label=f"Completed via {response.pattern_selected} ({response.confidence_level}, {response.confidence_score}%)",
                    state="complete",
                    expanded=False,
                )

            # Render final answer
            st.markdown(response.answer_markdown)
            _render_response_extras(response)

            # Save assistant message to session state
            st.session_state.chat_messages.append({
                "role": "assistant",
                "content": response.answer_markdown,
                "response_obj": response,
            })


def _render_response_extras(resp: AgentResponse):
    """Render confidence meter, citations with full text preview, diagram, and discrepancies."""
    # Confidence Gauge Tile
    c_color = "#10B981" if resp.confidence_score >= 85 else ("#F59E0B" if resp.confidence_score >= 60 else "#EF4444")
    st.markdown(
        f"<div style='padding: 8px 14px; border-radius: 6px; background-color: rgba(59, 130, 246, 0.08); border-left: 4px solid {c_color}; margin: 10px 0;'>"
        f"<strong>Confidence Assessment:</strong> <span style='color:{c_color}; font-weight:bold;'>{resp.confidence_level} ({resp.confidence_score}%)</span> "
        f"| <strong>Pattern:</strong> <code>{resp.pattern_selected}</code> | <strong>Reflection Passes:</strong> {resp.reflection_passes}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # Discrepancies Alert (Trap 2 Mitigation)
    if resp.discrepancies_detected:
        for disc in resp.discrepancies_detected:
            st.error(f"🚨 **Discrepancy Audit Alert ({disc.severity})**: {disc.description}\n\n*Action Required*: {disc.recommendation}")

    # Diagram Rendering
    if resp.diagram and resp.diagram.content:
        st.markdown("#### 📐 Architecture & Blast Radius Diagram")
        st.markdown(f"```{resp.diagram.type}\n{resp.diagram.content}\n```")

    # In-Depth Verified Citations with Document Previews
    if resp.citations:
        st.markdown(f"#### 📚 Verified Evidence Citations ({len(resp.citations)} Sources Grounded)")
        for cit in resp.citations:
            source_icon = "📄" if cit.source_type == "document" else ("📊" if cit.source_type == "table" else "🕸️")
            loc_parts = [p for p in [cit.section, f"Page {cit.page_number}" if cit.page_number else None, cit.table] if p]
            loc_str = f" — {', '.join(loc_parts)}" if loc_parts else ""

            with st.expander(f"{source_icon} {cit.ref_id} **{cit.source_file}**{loc_str}", expanded=False):
                st.markdown(f"**Verified Excerpt:**\n> {cit.excerpt}")
                if cit.full_text:
                    st.markdown("**📖 Full Context / Document Text Preview:**")
                    if cit.source_type in ("table", "graph"):
                        st.code(cit.full_text, language="json" if "{" in cit.full_text or "[" in cit.full_text else "text")
                    else:
                        st.info(cit.full_text)
                if cit.metadata:
                    st.caption(f"Classification / Metadata: `{cit.metadata}`")

    # Proactive Follow-ups
    if resp.suggested_followups:
        st.markdown("💡 **Suggested Proactive Follow-up Inquiries:**")
        cols = st.columns(len(resp.suggested_followups))
        for i, q in enumerate(resp.suggested_followups):
            with cols[i]:
                st.button(f"🔍 {q[:38]}...", key=f"followup_{hash(q)}_{i}", help=q)
