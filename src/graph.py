r"""
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
   / | \
  ▼  ▼  ▼
pros def tech      (fan-out: parallel judicial personas)
  \  |  /
   ▼ ▼ ▼
 ChiefJustice       (final synthesis, no LLM)
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
from src.nodes.judges import Prosecutor, DefenseAttorney, TechLeadJudge, ChiefJustice


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
    print(f"[Graph] Aggregation complete — {total} evidence item(s) merged. Fanning out to Judicial Bench...")
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
    
    # Judicial Bench Personsas
    builder.add_node("Prosecutor",      Prosecutor)
    builder.add_node("DefenseAttorney", DefenseAttorney)
    builder.add_node("TechLeadJudge",   TechLeadJudge)
    
    builder.add_node("ChiefJustice",    ChiefJustice)

    # 1. Dispatch to Detectives
    builder.add_edge(START, "dispatch")
    builder.add_edge("dispatch", "RepoInvestigator")
    builder.add_edge("dispatch", "DocAnalyst")
    builder.add_edge("dispatch", "VisionInspector")

    # 2. Fan-in Detectives -> Aggregate
    builder.add_edge("RepoInvestigator",  "aggregate_evidences")
    builder.add_edge("DocAnalyst",        "aggregate_evidences")
    builder.add_edge("VisionInspector",   "aggregate_evidences")

    # 3. Fan-out Aggregate -> Judicial Bench
    builder.add_edge("aggregate_evidences", "Prosecutor")
    builder.add_edge("aggregate_evidences", "DefenseAttorney")
    builder.add_edge("aggregate_evidences", "TechLeadJudge")

    # 4. Fan-in Judicial Bench -> ChiefJustice
    builder.add_edge("Prosecutor",      "ChiefJustice")
    builder.add_edge("DefenseAttorney", "ChiefJustice")
    builder.add_edge("TechLeadJudge",   "ChiefJustice")
    
    # 5. End
    builder.add_edge("ChiefJustice",    END)

    return builder.compile()

graph = build_graph()
