"""Pre-retrieval and post-retrieval safety guardrails.

Protects against prompt injection, out-of-domain queries, ABAC violations,
and verifies grounding and mathematical fidelity on generated outputs.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ports.base import LLMProviderPort
from ports.registry import AdapterRegistry
from utils.prompt_loader import get_prompt
from utils.logging_setup import setup_logger

logger = setup_logger("agent.guardrails")


class GuardrailCheckResult(BaseModel):
    is_safe: bool
    status: str  # "PASS", "BLOCKED_INJECTION", "BLOCKED_OUT_OF_DOMAIN", "BLOCKED_ABAC"
    warning_message: Optional[str] = None
    confidence: float = 1.0


class GroundingCheckResult(BaseModel):
    is_grounded: bool
    confidence_score: int
    unsupported_claims: List[str] = Field(default_factory=list)
    math_verified: bool = True
    discrepancies: List[str] = Field(default_factory=list)


class SafetyGuardrails:
    """Enforces pre-retrieval security and post-retrieval grounding checks."""

    # Fast deterministic injection heuristics
    INJECTION_PATTERNS = [
        r"ignore\s+(all\s+)?(previous\s+)?instructions",
        r"disregard\s+(all\s+)?prior",
        r"reveal\s+(the\s+)?system\s+prompt",
        r"output\s+(your\s+)?system\s+instructions",
        r"you\s+are\s+now\s+an\s+unrestricted",
        r"jailbreak",
        r"dan\s+mode",
        r"bypass\s+safety",
        r"show\s+secret_key",
        r"drop\s+table",
    ]

    OUT_OF_DOMAIN_PATTERNS = [
        r"who\s+won\s+the\s+.*championship",
        r"who\s+won\s+the\s+.*football",
        r"who\s+won\s+the\s+.*cup",
        r"what\s+is\s+the\s+weather",
        r"personal\s+home\s+address",
        r"celebrity\s+gossip",
        r"recipe\s+for",
    ]

    def __init__(self, llm_provider: Optional[LLMProviderPort] = None):
        self.llm = llm_provider or AdapterRegistry.get_llm_provider()

    def check_pre_retrieval(self, query: str, persona: str = "LEGAL") -> GuardrailCheckResult:
        """Run pre-retrieval safety scan for injection and out-of-domain topics."""
        lower = query.lower()

        # 1. Deterministic Injection Pattern Check
        for pat in self.INJECTION_PATTERNS:
            if re.search(pat, lower):
                logger.warning("Deterministic guardrail blocked injection query: %s", query[:50])
                return GuardrailCheckResult(
                    is_safe=False,
                    status="BLOCKED_INJECTION",
                    warning_message="This query has been flagged as a potential prompt injection attempt and cannot be processed.",
                    confidence=1.0,
                )

        # 2. Out-of-Domain Pattern Check
        for pat in self.OUT_OF_DOMAIN_PATTERNS:
            if re.search(pat, lower):
                logger.warning("Deterministic guardrail blocked out-of-domain query: %s", query[:50])
                return GuardrailCheckResult(
                    is_safe=False,
                    status="BLOCKED_OUT_OF_DOMAIN",
                    warning_message="This query is outside the scope of the Sovereign Infrastructure Knowledge Base. No relevant contracts, inventory data, or architectural specifications exist for this topic.",
                    confidence=1.0,
                )

        # 3. Cognitive LLM Classifier (PRD §5.1.1)
        try:
            prompt = get_prompt("guardrail_injection.txt", {"query": query})
            res_str = self.llm.generate(prompt=prompt, temperature=0.0).strip()
            if "{" in res_str and "}" in res_str:
                j_match = re.search(r"\{.*?\}", res_str, re.DOTALL)
                if j_match:
                    data = json.loads(j_match.group(0))
                    if data.get("is_injection") or not data.get("is_safe", True):
                        logger.warning("Cognitive LLM guardrail blocked injection query: %s", query[:50])
                        return GuardrailCheckResult(
                            is_safe=False,
                            status="BLOCKED_INJECTION",
                            warning_message=data.get("reason", "Flagged as potential injection by cognitive safety classifier."),
                            confidence=0.95,
                        )
                    if data.get("is_out_of_domain"):
                        logger.warning("Cognitive LLM guardrail blocked out-of-domain query: %s", query[:50])
                        return GuardrailCheckResult(
                            is_safe=False,
                            status="BLOCKED_OUT_OF_DOMAIN",
                            warning_message=data.get("reason", "Query determined to be outside data center and supply chain domain."),
                            confidence=0.95,
                        )
        except Exception as e:
            logger.debug("Cognitive guardrail check passed through: %s", str(e))

        return GuardrailCheckResult(
            is_safe=True,
            status="PASS",
            warning_message=None,
            confidence=1.0,
        )

    def check_post_retrieval_grounding(
        self, draft_answer: str, context_chunks: List[str], sql_results: Optional[List[Dict[str, Any]]] = None
    ) -> GroundingCheckResult:
        """Verify that claims in draft answer are backed by retrieved context and mathematically faithful to SQL rows."""
        discrepancies: List[str] = []
        unsupported_claims: List[str] = []
        combined_context = " ".join(context_chunks).lower()

        # 1. Cross-check cited purchase orders & exact numerical values against SQL records or context chunks
        math_verified = True
        po_matches = set(re.findall(r"\b(PO-\d+)\b", draft_answer, re.IGNORECASE))
        for po_num in po_matches:
            verified_in_sql = False
            if sql_results:
                matching_rows = [r for r in sql_results if str(r.get("po_number", "")).upper() == po_num.upper()]
                if matching_rows:
                    verified_in_sql = True
                    expected_val = matching_rows[0].get("total_val_eur")
                    if expected_val is not None:
                        val_float = float(expected_val)
                        val_str1 = f"{val_float:,.2f}"
                        val_str2 = f"{int(val_float):,}"
                        val_str3 = str(int(val_float))
                        if not any(v in draft_answer for v in (val_str1, val_str2, val_str3)):
                            discrepancies.append(
                                f"Financial value mismatch for {po_num}: Expected €{val_float:,.2f} based on SQL SSOT record."
                            )
                            math_verified = False

            # Cross-verify against retrieved context chunks if not verified via SQL
            if not verified_in_sql and context_chunks:
                relevant_chunks = [c for c in context_chunks if po_num.lower() in c.lower()]
                for chunk in relevant_chunks:
                    chunk_currencies = re.findall(r"[€$£]\s*([0-9,]+(?:\.[0-9]{2})?)", chunk)
                    draft_currencies = re.findall(r"[€$£]\s*([0-9,]+(?:\.[0-9]{2})?)", draft_answer)
                    if chunk_currencies and draft_currencies:
                        norm_chunk = {re.sub(r"\.00$", "", c.replace(",", "")) for c in chunk_currencies}
                        norm_draft = {re.sub(r"\.00$", "", d.replace(",", "")) for d in draft_currencies}
                        if not norm_draft.intersection(norm_chunk):
                            discrepancies.append(
                                f"Financial value mismatch for {po_num}: Draft claims {draft_currencies} but context records {chunk_currencies}."
                            )
                            math_verified = False

        # 2. Cross-check component SKUs mentioned in draft against context & SQL
        sku_matches = re.findall(r"\b(SKU-[A-Z0-9-]+)\b", draft_answer, re.IGNORECASE)
        for sku in set(sku_matches):
            sku_upper = sku.upper()
            found_in_chunks = sku_upper.lower() in combined_context
            found_in_sql = False
            if sql_results:
                found_in_sql = any(str(r.get("sku", "")).upper() == sku_upper for r in sql_results)
            if not found_in_chunks and not found_in_sql:
                unsupported_claims.append(f"Unverified SKU '{sku_upper}' not found in retrieved grounding context.")

        total_checks = max(1, len(set(re.findall(r"\b(PO-\d+|SKU-[A-Z0-9-]+)\b", draft_answer, re.IGNORECASE))))
        failures = len(discrepancies) + len(unsupported_claims)
        confidence_score = max(30, int(100 * (1 - (failures / total_checks)))) if total_checks else 90

        is_grounded = len(discrepancies) == 0 and len(unsupported_claims) == 0
        return GroundingCheckResult(
            is_grounded=is_grounded,
            confidence_score=confidence_score,
            unsupported_claims=unsupported_claims,
            math_verified=math_verified,
            discrepancies=discrepancies,
        )
