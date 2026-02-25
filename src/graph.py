"""
graph.py — Automaton Auditor LangGraph Definition

Architecture:
    START
      │
      ▼
  dispatch          (entry node — routes to all detectives)
   / | \
  ▼  ▼  ▼
repo doc vision    (fan-out: parallel detective nodes)
  \  |  /
   ▼ ▼ ▼
 aggregate          (fan-in: merges all Evidence dicts)
      │
      ▼
JudicialAnalyst     (evaluates evidence)
      │
      ▼
   Reporter         (final audit report)
      │
      ▼
     END
"""
from dotenv import load_dotenv
load_dotenv()

from typing import Any
from langgraph.graph import StateGraph, START, END

from src.state import AgentState
from src.nodes.detectives import RepoInvestigator, DocAnalyst, VisionInspector
from src.nodes.judges import JudicialAnalyst, Reporter


# ─────────────────────────────────────────────
# Entry node: dispatch
# ─────────────────────────────────────────────
def dispatch(state: AgentState) -> dict[str, Any]:
    print("[Graph] Dispatch node: fanning out to all detectives...")
    return {}


# ─────────────────────────────────────────────
# Fan-in node: aggregate_evidences
# ─────────────────────────────────────────────
def aggregate_evidences(state: AgentState) -> dict[str, Any]:
    total = len(state.get("evidences", {}))
    print(f"[Graph] Aggregation complete — {total} evidence item(s) merged.")
    for ev_id, ev in state.get("evidences", {}).items():
        print(f"  • {ev_id}: {ev.goal[:60]}... | confidence={ev.reliability_score:.2f}")
    return {}


# ─────────────────────────────────────────────
# Build the compiled graph
# ─────────────────────────────────────────────
def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("dispatch",          dispatch)
    builder.add_node("RepoInvestigator",  RepoInvestigator)
    builder.add_node("DocAnalyst",        DocAnalyst)
    builder.add_node("VisionInspector",   VisionInspector)
    builder.add_node("aggregate_evidences", aggregate_evidences)
    builder.add_node("JudicialAnalyst",     JudicialAnalyst)
    builder.add_node("Reporter",            Reporter)

    builder.add_edge(START, "dispatch")
    builder.add_edge("dispatch", "RepoInvestigator")
    builder.add_edge("dispatch", "DocAnalyst")
    builder.add_edge("dispatch", "VisionInspector")

    builder.add_edge("RepoInvestigator",  "aggregate_evidences")
    builder.add_edge("DocAnalyst",        "aggregate_evidences")
    builder.add_edge("VisionInspector",   "aggregate_evidences")

    builder.add_edge("aggregate_evidences", "JudicialAnalyst")
    builder.add_edge("JudicialAnalyst",     "Reporter")
    builder.add_edge("Reporter",            END)

    return builder.compile()

graph = build_graph()
