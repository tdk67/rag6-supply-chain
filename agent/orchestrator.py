"""Agent Orchestrator executing the Action-Inspection-Correction reflection loop."""

from __future__ import annotations

import json
import re
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ports.base import LLMProviderPort
from agent.guardrails import SafetyGuardrails
from agent.intent_router import IntentRouter
from agent.response_builder import (
    AgentResponse,
    Citation,
    Diagram,
    Discrepancy,
    calculate_confidence_level,
    format_context_for_llm,
    extract_mermaid_and_followups,
)
from retrieval.graph_query import GraphQueryTool
from retrieval.sql_query import SQLQueryTool
from retrieval.vector_search import VectorSearchTool
from ports.registry import AdapterRegistry
from utils.config import load_config
from utils.prompt_loader import get_prompt
from utils.logging_setup import setup_logger

logger = setup_logger("agent.orchestrator")


class AgentOrchestrator:
    """Coordinates tri-modal retrieval, multi-step reflection, and citation synthesis."""

    def __init__(
        self,
        llm_provider: Optional[LLMProviderPort] = None,
        guardrails: Optional[SafetyGuardrails] = None,
        router: Optional[IntentRouter] = None,
        sql_tool: Optional[SQLQueryTool] = None,
        graph_tool: Optional[GraphQueryTool] = None,
        vector_tool: Optional[VectorSearchTool] = None,
    ):
        self.llm = llm_provider or AdapterRegistry.get_llm_provider()
        self.guardrails = guardrails or SafetyGuardrails(llm_provider=self.llm)
        self.router = router or IntentRouter(llm_provider=self.llm)
        self.sql_tool = sql_tool or SQLQueryTool(llm_provider=self.llm)
        self.graph_tool = graph_tool or GraphQueryTool(llm_provider=self.llm)
        self.vector_tool = vector_tool or VectorSearchTool()

    def process_query(
        self,
        query: str,
        persona: str = "LEGAL",
        status_callback: Optional[Callable[[str], None]] = None,
    ) -> AgentResponse:
        """Execute the end-to-end tri-modal GraphRAG reflection loop."""
        query_id = f"q-{uuid.uuid4().hex[:8]}"
        trace: List[Dict[str, Any]] = []
        t0 = time.perf_counter()

        def log_step(step_name: str, details: Dict[str, Any]):
            elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
            item = {"timestamp_ms": elapsed_ms, "step": step_name, **details}
            trace.append(item)
            if status_callback:
                status_callback(f"[{elapsed_ms}ms] {step_name}: {details.get('summary', '')}")

        # -------------------------------------------------------------
        # STEP 1: Pre-Retrieval Guardrails (Injection & Scope Check)
        # -------------------------------------------------------------
        log_step("Pre-Guardrail", {"summary": "Validating input safety and scope"})
        guard_res = self.guardrails.check_pre_retrieval(query, persona=persona)
        if not guard_res.is_safe:
            log_step("Pre-Guardrail-Blocked", {"status": guard_res.status, "summary": guard_res.warning_message})
            return AgentResponse(
                answer_markdown=f"> ⚠️ **Security Warning**: {guard_res.warning_message}",
                confidence_score=0,
                confidence_level="REFUSED",
                is_complete=False,
                incompleteness_reason=guard_res.warning_message,
                tools_used=[],
                pattern_selected="BLOCKED",
                reflection_passes=0,
                suggested_followups=["Please submit a query related to sovereign data center hardware, contracts, or compliance."],
                citations=[],
                execution_trace=trace,
            )

        # -------------------------------------------------------------
        # STEP 2: Intent Classification & Pattern Selection (6 Patterns)
        # -------------------------------------------------------------
        log_step("Intent-Router", {"summary": "Classifying query into GraphRAG architectural patterns"})
        routing = self.router.route(query)
        log_step(
            "Pattern-Selected",
            {
                "pattern": routing.pattern_name,
                "confidence": routing.confidence,
                "tools": routing.tools_selected,
                "summary": f"Selected {routing.pattern_name} (Confidence: {routing.confidence*100:.0f}%)",
            },
        )

        # -------------------------------------------------------------
        # STEP 3: Pass 1 Execution (Tri-Modal Retrieval)
        # -------------------------------------------------------------
        tools_executed = []
        citations: List[Citation] = []
        discrepancies: List[Discrepancy] = []
        retrieved_texts: List[str] = []
        diagram_obj: Optional[Diagram] = None

        # Execute Graph Tool if selected
        graph_data = None
        if "graph_query" in routing.tools_selected or routing.pattern in ("P1", "P3", "P4", "P6"):
            log_step("Tool-Graph", {"summary": "Executing knowledge graph traversal"})
            g_res = self.graph_tool.query(query)
            graph_data = g_res.data
            tools_executed.append("graph_query")
            citations.append(
                Citation(
                    ref_id=f"[{len(citations)+1}]",
                    source_type="graph",
                    source_file="Sovereign Infrastructure Knowledge Graph",
                    section=f"Topology Traversal: {g_res.pattern_used}",
                    excerpt=f"Matched {g_res.nodes_found} nodes, {g_res.edges_found} edges. {g_res.summary}",
                    full_text=f"Graph Traversal: {g_res.pattern_used}\nSummary: {g_res.summary}\n\nTraversed Entities:\n{json.dumps(graph_data, indent=2) if isinstance(graph_data, (dict, list)) else str(graph_data)}",
                    metadata={"nodes_found": g_res.nodes_found, "edges_found": g_res.edges_found},
                )
            )

        # Execute SQL Tool if selected
        sql_data = None
        if "sql_query" in routing.tools_selected or routing.pattern in ("P2", "P3", "P4", "P6"):
            log_step("Tool-SQL", {"summary": "Executing read-only structured SQLite query"})
            s_res = self.sql_tool.text_to_sql_query(query)
            sql_data = s_res.rows
            tools_executed.append("sql_query")
            if s_res.rows:
                citations.append(
                    Citation(
                        ref_id=f"[{len(citations)+1}]",
                        source_type="table",
                        source_file="SQLite SSOT Database (infrastructure.db)",
                        table=getattr(s_res, "table_name", None) or "purchase_orders / components",
                        row_id=str(s_res.rows[0].get("po_number") or s_res.rows[0].get("sku") or "ROW-1"),
                        excerpt=f"SQL Query: {s_res.query_executed} -> Matched {len(s_res.rows)} records.",
                        full_text=f"SQL Query Executed:\n{s_res.query_executed}\n\nReturned Records ({len(s_res.rows)}):\n{json.dumps(s_res.rows, indent=2)}",
                        metadata={"row_count": len(s_res.rows), "query": s_res.query_executed},
                    )
                )

        # Execute Vector Tool if selected
        vector_chunks = []
        if "vector_search" in routing.tools_selected or routing.pattern in ("P2", "P5", "P6"):
            log_step("Tool-Vector", {"summary": f"Executing semantic search with ABAC ({persona})"})
            v_res = self.vector_tool.search(query, persona=persona)
            tools_executed.append("vector_search")
            if v_res.abac_blocked:
                log_step("ABAC-Warning", {"summary": v_res.message})
            else:
                vector_chunks = v_res.chunks
                for c in vector_chunks[:4]:
                    citations.append(
                        Citation(
                            ref_id=f"[{len(citations)+1}]",
                            source_type="document",
                            source_file=c.metadata.get("source_file", "document.pdf"),
                            page_number=c.metadata.get("page_number", 1),
                            section=c.metadata.get("section_heading", "Clause / Section"),
                            excerpt=c.text[:220] + ("..." if len(c.text) > 220 else ""),
                            full_text=c.text,
                            metadata=c.metadata,
                        )
                    )
                    retrieved_texts.append(c.text)

        # -------------------------------------------------------------
        # STEP 4: OOD & Zero Evidence Check (PRD §5.1.3)
        # -------------------------------------------------------------
        has_graph_evidence = bool(graph_data) and (
            not isinstance(graph_data, dict)
            or graph_data.get("count", 0) > 0
            or graph_data.get("suppliers")
            or graph_data.get("compatible_stacks")
            or graph_data.get("total_racks_affected", 0) > 0
        )
        has_sql_evidence = bool(sql_data) and len(sql_data) > 0
        has_vector_evidence = bool(vector_chunks) and len(vector_chunks) > 0

        if not has_graph_evidence and not has_sql_evidence and not has_vector_evidence:
            log_step("OOD-Refusal", {"summary": "Zero evidence found in local SSOT - refusing out-of-domain query"})
            return AgentResponse(
                answer_markdown=(
                    "### 🚫 Query Out of Domain\n\n"
                    "No relevant data center hardware, contracts, inventory, or compliance records were found in the Sovereign Infrastructure Knowledge Base for this query.\n\n"
                    "**Supported Domain Areas:**\n"
                    "- Sovereign AI data center hardware (MI300X, H200, chassis, transceivers, cooling loops)\n"
                    "- Multi-tier supply chains and geopolitical freight corridor risk (Taiwan, TSMC, Amphenol)\n"
                    "- Commercial contracts, Force Majeure clauses, and liquidated damages penalties\n"
                    "- Regulatory standards (BSI C5:2024, EU AI Act, NIS2 Directive)"
                ),
                confidence_score=15,
                confidence_level="REFUSED",
                is_complete=False,
                incompleteness_reason="Out of domain: zero grounding evidence found in SSOT databases.",
                tools_used=tools_executed,
                pattern_selected=routing.pattern_name,
                reflection_passes=1,
                suggested_followups=[
                    "Which components in our Open Rack v3 BOM have only one qualified supplier?",
                    "If geopolitical conflict disrupts freight routes out of Taiwan, what is our total affected order value?",
                ],
                citations=[],
                execution_trace=trace,
            )

        # -------------------------------------------------------------
        # STEP 5: Pass 2 Inspection & Data-Driven Discrepancy Auditing (Trap 2)
        # -------------------------------------------------------------
        log_step("Pass-2-Inspection", {"summary": "Auditing data discrepancies and checking math consistency"})

        # General ERP vs Dock Receipt reconciliation
        disc_check = self.sql_tool.execute_raw(
            "SELECT d.receipt_id, d.po_number, po.sku, po.quantity, d.units_received, d.discrepancy_notes "
            "FROM dock_receipts d JOIN purchase_orders po ON d.po_number = po.po_number "
            "WHERE d.discrepancy_flag = 1 OR d.units_received < po.quantity"
        )
        if disc_check.rows:
            relevant_pos = set()
            if sql_data:
                for r in sql_data:
                    if r.get("po_number"):
                        relevant_pos.add(str(r["po_number"]).upper())
            for row in disc_check.rows:
                row_po = str(row["po_number"]).upper()
                # Attach if query explicitly mentions discrepancies/orders or if matched in SQL data
                if (
                    row_po in relevant_pos
                    or row_po in query.upper()
                    or any(k in query.lower() for k in ("discrepan", "receipt", "dock", "shortfall", "late", "supermicro", "8821", "audit"))
                ):
                    discrepancies.append(
                        Discrepancy(
                            description=f"Purchase Order {row['po_number']} ({row.get('sku', '')}) specifies {row['quantity']} units, but Dock Receipt {row['receipt_id']} records only {row['units_received']} units received ({row.get('discrepancy_notes', 'Delivery discrepancy flagged')}).",
                            severity="HIGH",
                            recommendation="Audit physical inventory in Frankfurt DC-1 Cold Storage before executing final liquidated damages deductions.",
                        )
                    )

        # -------------------------------------------------------------
        # STEP 6: Pass 3 Synthesis & Multi-Pass Reflection Loop (PRD §5.3)
        # -------------------------------------------------------------
        log_step("Pass-3-Synthesis", {"summary": "Synthesizing executive answer via LLM with context grounding"})

        cfg = load_config()
        max_reflection_passes = int(cfg.get("agent", {}).get("max_reflection_passes", 3))
        query_timeout_seconds = float(cfg.get("agent", {}).get("query_timeout_seconds", 60.0))
        reflection_passes_count = 1
        correction_feedback = None

        try:
            answer_text, diagram_obj, followups = self._synthesize_answer(
                query=query,
                persona=persona,
                pattern=routing.pattern_name,
                graph_data=graph_data,
                sql_data=sql_data,
                vector_chunks=vector_chunks,
                discrepancies=discrepancies,
                feedback=correction_feedback,
            )

            # Post-retrieval grounding & math verification (PRD §5.1.2)
            grounding_res = self.guardrails.check_post_retrieval_grounding(
                draft_answer=answer_text,
                context_chunks=retrieved_texts,
                sql_results=sql_data,
            )
            log_step(
                "Post-Grounding-Check",
                {
                    "math_verified": grounding_res.math_verified,
                    "discrepancies": grounding_res.discrepancies,
                    "unsupported_claims": grounding_res.unsupported_claims,
                    "computed_confidence": grounding_res.confidence_score,
                },
            )

            # Multi-pass reflection loop with timeout enforcement (PRD §5.3, §13.2)
            while not grounding_res.is_grounded and reflection_passes_count < max_reflection_passes:
                elapsed = time.perf_counter() - t0
                if elapsed >= query_timeout_seconds:
                    log_step("Timeout-Breaker", {"elapsed_s": round(elapsed, 2), "timeout_s": query_timeout_seconds})
                    break

                reflection_passes_count += 1
                correction_feedback = (
                    "Please correct the following factual or numerical mismatches in your final response:\n"
                    + "\n".join(grounding_res.discrepancies + grounding_res.unsupported_claims)
                )
                log_step("Reflection-Correction-Pass", {"pass": reflection_passes_count, "feedback": correction_feedback})
                answer_text, diagram_obj, followups = self._synthesize_answer(
                    query=query,
                    persona=persona,
                    pattern=routing.pattern_name,
                    graph_data=graph_data,
                    sql_data=sql_data,
                    vector_chunks=vector_chunks,
                    discrepancies=discrepancies,
                    feedback=correction_feedback,
                )
                grounding_res = self.guardrails.check_post_retrieval_grounding(
                    draft_answer=answer_text,
                    context_chunks=retrieved_texts,
                    sql_results=sql_data,
                )

            confidence_score = grounding_res.confidence_score if citations else min(grounding_res.confidence_score, 65)
            confidence_level = calculate_confidence_level(confidence_score)
            is_complete = True
            incompleteness_reason = None
            log_step("Complete", {"summary": f"Generated final response ({confidence_level}, {confidence_score}%)"})

        except Exception as e:
            # NO SILENT FAKES. Stop at the error - show exactly what went wrong, no simulated result.
            error_msg = str(e)
            logger.warning(f"Synthesis failed, surfacing error: {error_msg}")
            log_step("Synthesis-Error", {"error": error_msg})

            steps_summary = ", ".join(
                f"{item.get('step', '?')} ({item.get('summary', '')[:60]})" for item in trace
            ).strip() or "(no steps recorded)"
            context_summary = format_context_for_llm(graph_data, sql_data, vector_chunks, discrepancies)
            answer_text = (
                "### ⛔ Synthesis Failed\n\n"
                "> **Error:** "
                + error_msg.replace("\n", " ")  # single-line, no markdown abuse
                + "\n\n"
                "### ⚠️ LLM Synthesis Required\n"
                "The retrieval layer succeeded, but executive answer synthesis requires a configured and reachable OpenRouter LLM provider (no offline/local template fallback is used).\n\n"
                "**How to resolve:**\n"
                "1. **Streamlit UI** → sidebar → enter a valid **OpenRouter API Key** and click **Verify Key**, or\n"
                "2. **Environment File** → add `OPENROUTER_API_KEY=your_key_here` to your local `.env`, restart, retry.\n\n"
                f"**Steps completed before failure:** {steps_summary}"
            )
            diagram_obj = None
            followups = [
                "How do I enter my OpenRouter API Key in the UI sidebar?",
                "Which LLM provider is configured and how do I verify it?",
            ]
            confidence_score = 0
            confidence_level = "REFUSED"
            is_complete = False
            incompleteness_reason = error_msg

        return AgentResponse(
            answer_markdown=answer_text,
            confidence_score=confidence_score,
            confidence_level=confidence_level,
            is_complete=is_complete,
            incompleteness_reason=incompleteness_reason,
            tools_used=tools_executed,
            pattern_selected=routing.pattern_name,
            reflection_passes=reflection_passes_count,
            suggested_followups=followups,
            citations=citations,
            diagram=diagram_obj,
            discrepancies_detected=discrepancies,
            execution_trace=trace,
        )

    def _synthesize_answer(
        self,
        query: str,
        persona: str,
        pattern: str,
        graph_data: Any,
        sql_data: Any,
        vector_chunks: List[Any],
        discrepancies: List[Discrepancy],
        feedback: Optional[str] = None,
    ) -> tuple[str, Optional[Diagram], List[str]]:
        """Genuinely synthesize an executive grounded answer using the LLM and retrieved context."""
        context_str = format_context_for_llm(graph_data, sql_data, vector_chunks, discrepancies)
        discrepancy_str = (
            "\n".join([f"- {d.description} (Severity: {d.severity})" for d in discrepancies])
            if discrepancies
            else "None detected."
        )

        prompt = get_prompt(
            "answer_synthesis.txt",
            {
                "query": query,
                "persona": persona,
                "pattern": pattern,
                "context": context_str,
                "discrepancies": discrepancy_str,
            },
        )
        if feedback:
            prompt += f"\n\n[INSPECTION CORRECTION DIRECTIVE]:\n{feedback}\nPlease adjust your previous claims to accurately align with the SSOT records above."

        try:
            system_prompt = get_prompt("system_prompt.txt")
        except Exception:
            system_prompt = (
                "You are Aethelgard Infra-GraphRAG, an autonomous intelligence engine for European sovereign AI data centers.\n"
                "Strict Instructions:\n"
                "1. Ground all numbers, supplier names, component SKUs, and legal clauses strictly in the provided context.\n"
                "2. Never invent or hallucinate facts not present in the context.\n"
                "3. Embed numeric footnote citations like [1], [2] next to every specific claim.\n"
                "4. Structure your response with executive markdown headings and bullet points.\n"
                "5. If helpful, include a concise Mermaid diagram illustrating the relationship, failure cascade, or topology inside ```mermaid ... ``` code blocks.\n"
                "6. End with a '### Suggested Follow-ups' section containing 2 logical next questions."
            )

        # Call the LLM provider
        raw_output = self.llm.generate(prompt=prompt, system_prompt=system_prompt, temperature=0.1)
        return extract_mermaid_and_followups(raw_output)

    def _format_context_for_llm(self, *args, **kwargs) -> str:
        """Backward-compatible delegate to response_builder.format_context_for_llm."""
        return format_context_for_llm(*args, **kwargs)


