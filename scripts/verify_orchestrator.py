"""Verification script for Action Point 4.3: Agent Orchestrator & Glass Box Trace."""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.orchestrator import AgentOrchestrator

def run_benchmark_q3():
    orch = AgentOrchestrator()
    q3 = "Which components in our Open Rack v3 BOM currently have ONLY ONE qualified supplier, creating a single point of failure?"
    resp = orch.process_query(q3, persona="CTO")

    print("=" * 60)
    print("GLASS BOX EXECUTION TRACE (Benchmark Q3)")
    print("=" * 60)
    for step in resp.execution_trace:
        print(f"[{step['timestamp_ms']:6.1f}ms] {step['step']:20s}: {step.get('summary', '')}")

    print("\n" + "=" * 60)
    print("STRUCTURED RESPONSE OUTPUT")
    print("=" * 60)
    print(f"Pattern Selected:   {resp.pattern_selected}")
    print(f"Confidence Score:   {resp.confidence_score}% ({resp.confidence_level})")
    print(f"Tools Executed:     {resp.tools_used}")
    print(f"Reflection Passes:  {resp.reflection_passes}")
    print(f"Citations ({len(resp.citations)}):")
    for c in resp.citations:
        print(f"  {c.ref_id} {c.source_file} ({c.section or c.table}): {c.excerpt}")

    if resp.diagram:
        print(f"\nDiagram Type: {resp.diagram.type}")
        print("Diagram Content:\n" + resp.diagram.content)

    print("\nAnswer Markdown Preview:")
    print(resp.answer_markdown)
    print("=" * 60)

if __name__ == "__main__":
    run_benchmark_q3()
