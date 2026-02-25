"""
test_graph.py — Run the full compiled Automaton Auditor LangGraph

Tests the complete fan-out → fan-in graph:
    START → dispatch → [RepoInvestigator | DocAnalyst | VisionInspector]
          → aggregate_evidences → END
"""
import sys
import os
sys.path.insert(0, os.path.abspath("."))

from src.graph import graph
from src.state import AgentState

# Initial empty state
initial_state: AgentState = {
    "evidences": {},
    "opinions": [],
    "report": None,
}

print("=" * 60)
print("  Automaton Auditor — Full Graph Run")
print("=" * 60)

# Compile and invoke the full graph
final_state = graph.invoke(initial_state)

# ── Print merged evidences ──────────────────────────────────
evidences = final_state.get("evidences", {})
print(f"\n✅ Graph completed. {len(evidences)} total evidence item(s) merged.\n")

for ev_id, ev in evidences.items():
    print(f"{'─'*55}")
    print(f"  ID         : {ev.evidence_id}")
    print(f"  Goal       : {ev.goal}")
    print(f"  Found      : {ev.found[:200]}...")
    print(f"  Location   : {ev.location}")
    print(f"  Rationale  : {ev.rationale[:150]}...")
    print(f"  Source     : {ev.source}")
    print(f"  Confidence : {ev.reliability_score:.2f}")

print(f"\n{'='*60}")
print("  Ready for judicial processing.")
print("=" * 60)
