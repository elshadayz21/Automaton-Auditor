import sys
import os

# Ensure the src module can be imported
sys.path.insert(0, os.path.abspath("."))

from src.nodes.detectives import RepoInvestigator
from src.state import AgentState

# Initial empty state
initial_state: AgentState = {
    "evidences": {},
    "opinions": [],
    "report": None
}

print("Running RepoInvestigator (with dummy fallback URL in implementation)...")
result_state = RepoInvestigator(initial_state)

print("\\nReturned Evidences dict:")
for ev_id, evidence in result_state.get("evidences", {}).items():
    print(f"\\nID: {ev_id}")
    print(f"Source: {evidence.source}")
    print(f"Reliability: {evidence.reliability_score}")
    print(f"Content: {evidence.content[:500]}...") # truncate for display
