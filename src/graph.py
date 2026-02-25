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
 aggregate          (fan-in: merges all Evidence dicts via operator.ior reducer)
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


# ─────────────────────────────────────────────
# Entry node: dispatch
# ─────────────────────────────────────────────
def dispatch(state: AgentState) -> dict[str, Any]:
    """
    Entry/dispatch node. Does no work itself — exists so that
    fan-out edges from a single named node can route to all
    detective nodes in parallel.
    """
    print("[Graph] Dispatch node: fanning out to all detectives...")
    return {}   # no state mutation — pass-through


# ─────────────────────────────────────────────
# Fan-in node: aggregate_evidences
# ─────────────────────────────────────────────
def aggregate_evidences(state: AgentState) -> dict[str, Any]:
    """
    Fan-in aggregation node. By the time this node runs, LangGraph's
    operator.ior reducer has already merged all Evidence dicts from
    the parallel detective branches into state['evidences'].
    This node logs the merged result and prepares it for downstream
    judicial processing.
    """
    total = len(state.get("evidences", {}))
    print(f"[Graph] Aggregation complete — {total} evidence item(s) merged.")
    for ev_id, ev in state.get("evidences", {}).items():
        print(f"  • {ev_id}: {ev.goal[:60]}... | confidence={ev.reliability_score:.2f}")
    # Pass through unchanged — reducers already did the merge
    return {}


# ─────────────────────────────────────────────
# Build the compiled graph
# ─────────────────────────────────────────────
def build_graph():
    """
    Constructs, wires, and compiles the Automaton Auditor StateGraph.

    Fan-out pattern:
        START → dispatch → [RepoInvestigator | DocAnalyst | VisionInspector]

    Fan-in pattern:
        [RepoInvestigator | DocAnalyst | VisionInspector] → aggregate_evidences → END
    """
    builder = StateGraph(AgentState)

    # Register all nodes
    builder.add_node("dispatch",          dispatch)
    builder.add_node("RepoInvestigator",  RepoInvestigator)
    builder.add_node("DocAnalyst",        DocAnalyst)
    builder.add_node("VisionInspector",   VisionInspector)
    builder.add_node("aggregate_evidences", aggregate_evidences)

    # Wire START → dispatch (entry point)
    builder.add_edge(START, "dispatch")

    # Fan-out: dispatch → all three detective nodes (parallel branches)
    builder.add_edge("dispatch", "RepoInvestigator")
    builder.add_edge("dispatch", "DocAnalyst")
    builder.add_edge("dispatch", "VisionInspector")

    # Fan-in: all detectives → aggregate_evidences
    builder.add_edge("RepoInvestigator",  "aggregate_evidences")
    builder.add_edge("DocAnalyst",        "aggregate_evidences")
    builder.add_edge("VisionInspector",   "aggregate_evidences")

    # Wire aggregate_evidences → END
    builder.add_edge("aggregate_evidences", END)

    return builder.compile()


# Compiled graph instance — importable by other modules
graph = build_graph()
