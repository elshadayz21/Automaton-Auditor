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
      │
  evidence_gate     (conditional edge: checks if evidence exists)
   / YES \  NO \
  ▼  ▼  ▼      ▼
pros def tech  ChiefJustice  (skip bench if no evidence)
  \  |  /
   ▼ ▼ ▼
 ChiefJustice       (final synthesis, no LLM)
      │
      ▼
     END
"""
from dotenv import load_dotenv
load_dotenv()

from typing import Any, Literal
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
    print(f"[Graph] Aggregation complete — {total} evidence item(s) merged.")
    for ev_id, ev in state.get("evidences", {}).items():
        print(f"  • {ev_id}: {ev.goal[:60]}... | confidence={ev.reliability_score:.2f}")
    return {}


# ─────────────────────────────────────────────
# Conditional Router: evidence_gate
# ─────────────────────────────────────────────
def evidence_gate(state: AgentState) -> Literal["has_evidence", "no_evidence"]:
    """
    Conditional edge: checks if any evidence was collected by detectives.
    If no evidence exists (e.g., due to clone failures, missing PDFs, API errors),
    route directly to ChiefJustice, skipping the Judicial Bench entirely.
    """
    evidences = state.get("evidences", {})
    if evidences:
        print(f"[Gate] ✅ Evidence found ({len(evidences)} items). Fanning out to Judicial Bench...")
        return "has_evidence"
    else:
        print("[Gate] ⚠️ No evidence collected. Skipping Judicial Bench → routing to ChiefJustice.")
        return "no_evidence"


# ─────────────────────────────────────────────
# Judicial fan-out node
# ─────────────────────────────────────────────
def judicial_dispatch(state: AgentState) -> dict[str, Any]:
    print("[Graph] Judicial dispatch: fanning out to all 3 judge personas...")
    return {}


# ─────────────────────────────────────────────
# Build the compiled graph
# ─────────────────────────────────────────────
def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("dispatch",            dispatch)
    builder.add_node("RepoInvestigator",    RepoInvestigator)
    builder.add_node("DocAnalyst",          DocAnalyst)
    builder.add_node("VisionInspector",     VisionInspector)
    builder.add_node("aggregate_evidences", aggregate_evidences)
    builder.add_node("judicial_dispatch",   judicial_dispatch)

    # Judicial Bench Personas
    builder.add_node("Prosecutor",      Prosecutor)
    builder.add_node("DefenseAttorney", DefenseAttorney)
    builder.add_node("TechLeadJudge",   TechLeadJudge)

    builder.add_node("ChiefJustice",    ChiefJustice)

    # 1. Dispatch to Detectives (fan-out)
    builder.add_edge(START, "dispatch")
    builder.add_edge("dispatch", "RepoInvestigator")
    builder.add_edge("dispatch", "DocAnalyst")
    builder.add_edge("dispatch", "VisionInspector")

    # 2. Fan-in Detectives -> Aggregate
    builder.add_edge("RepoInvestigator",  "aggregate_evidences")
    builder.add_edge("DocAnalyst",        "aggregate_evidences")
    builder.add_edge("VisionInspector",   "aggregate_evidences")

    # 3. Conditional Edge: Evidence Gate
    #    has_evidence -> judicial_dispatch -> fan-out to all 3 judges
    #    no_evidence  -> ChiefJustice (skip bench entirely)
    builder.add_conditional_edges(
        "aggregate_evidences",
        evidence_gate,
        {
            "has_evidence": "judicial_dispatch",
            "no_evidence":  "ChiefJustice",
        }
    )

    # 4. Fan-out judicial_dispatch -> all 3 judges
    builder.add_edge("judicial_dispatch", "Prosecutor")
    builder.add_edge("judicial_dispatch", "DefenseAttorney")
    builder.add_edge("judicial_dispatch", "TechLeadJudge")

    # 5. Fan-in Judicial Bench -> ChiefJustice
    builder.add_edge("Prosecutor",      "ChiefJustice")
    builder.add_edge("DefenseAttorney", "ChiefJustice")
    builder.add_edge("TechLeadJudge",   "ChiefJustice")

    # 6. End
    builder.add_edge("ChiefJustice",    END)

    return builder.compile()

graph = build_graph()


