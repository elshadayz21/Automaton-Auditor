"""
test_graph.py — Run the full compiled Automaton Auditor LangGraph

Tests the complete fan-out → fan-in graph:
    START → dispatch → [RepoInvestigator | DocAnalyst | VisionInspector]
          → aggregate_evidences 
          → [Prosecutor | DefenseAttorney | TechLeadJudge]
          → ChiefJustice
          → END
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

# ── Print judicial opinions ─────────────────────────────────
opinions = final_state.get("opinions", [])
print(f"\n✅ Judicial Bench completed. {len(opinions)} opinion(s) formulated.\n")
for op in opinions:
    print(f"{'─'*55}")
    print(f"  Agent    : {op.agent_name}")
    print(f"  ID       : {op.opinion_id}")
    print(f"  Argument : {op.argument[:300]}...")

# ── Print final report ──────────────────────────────────────
report = final_state.get("report")
if report:
    print(f"\n✅ Final Report Generated (Chief Justice Verdict): {report.report_id}")
    print(f"  Summary : {report.summary[:300]}...")
    print(f"  Decision: {report.final_decision}")
    print(f"  Full Markdown report saved directly to 'audit_report.md'.")
else:
    print("\n❌ Final Report missing.")

print(f"\n{'='*60}")
print("  Audit Complete.")
print("=" * 60)
