import sys
import os

# Ensure the src module can be imported
sys.path.insert(0, os.path.abspath("."))

from src.nodes.detectives import RepoInvestigator, DocAnalyst, VisionInspector
from src.state import AgentState

# Initial empty state
initial_state: AgentState = {
    "evidences": {},
    "opinions": [],
    "report": None
}

def print_evidences(label: str, result: dict):
    evidences = result.get("evidences", {})
    print(f"\n{'='*60}")
    print(f"{label} — {len(evidences)} evidence item(s) collected")
    print('='*60)
    for ev_id, ev in evidences.items():
        print(f"\n  ID       : {ev.evidence_id}")
        print(f"  Goal     : {ev.goal}")
        print(f"  Found    : {ev.found[:200]}...")
        print(f"  Location : {ev.location}")
        print(f"  Rationale: {ev.rationale[:150]}...")
        print(f"  Source   : {ev.source}")
        print(f"  Confidence: {ev.reliability_score:.2f}")

# ── Test 1: RepoInvestigator ────────────────────────────────
print("\n[1] Running RepoInvestigator (graph wiring, state design, tool safety)...")
repo_result = RepoInvestigator(initial_state)
print_evidences("RepoInvestigator", repo_result)

# ── Test 2: DocAnalyst ──────────────────────────────────────
print("\n[2] Running DocAnalyst (PDF — expected to skip if sample.pdf missing)...")
doc_result = DocAnalyst(initial_state)
print_evidences("DocAnalyst", doc_result)

# ── Test 3: VisionInspector ─────────────────────────────────
print("\n[3] Running VisionInspector (image — expected to skip if sample_diagram.png missing)...")
vision_result = VisionInspector(initial_state)
print_evidences("VisionInspector", vision_result)

print("\n✅ All detective nodes completed.")
