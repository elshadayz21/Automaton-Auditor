import json
from typing import Any
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, JudicialOpinion, AuditReport, CriterionResult, Evidence

def JudicialAnalyst(state: AgentState) -> dict[str, Any]:
    """
    Judicial analyst node.
    Consumes all collected Evidence and produces a JudicialOpinion.
    """
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": [JudicialOpinion(
            opinion_id="error-no-evidence",
            agent_name="JudicialAnalyst",
            argument="No evidence was collected during the investigation phase.",
            evidence_refs=[]
        )]}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(JudicialOpinion)

    # Convert evidences to a readable format for the LLM
    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])

    prompt = f"""You are a Lead Judicial Analyst. Your role is to evaluate the collected evidence and provide a formal judicial opinion.

EVIDENCE COLLECTED:
{evidence_text}

Provide your opinion:
1. opinion_id: a unique ID
2. agent_name: "JudicialAnalyst"
3. argument: A comprehensive synthesis of the findings. Mention specific evidence IDs.
4. evidence_refs: List of evidence IDs you are basing this opinion on.
"""
    opinion = llm.invoke([HumanMessage(content=prompt)])
    print(f"  ⚖️ Formulated judicial opinion: {opinion.opinion_id}")
    return {"opinions": [opinion]}


def Reporter(state: AgentState) -> dict[str, Any]:
    """
    Reporter node.
    Consumes judicial opinions and generates the final AuditReport.
    """
    opinions = state.get("opinions", [])
    if not opinions:
        return {"report": AuditReport(
            report_id="err-no-opinion",
            summary="Audit aborted: No judicial opinions were generated.",
            criteria_results=[],
            final_decision="Incomplete"
        )}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(AuditReport)

    opinion_text = "\n\n".join([f"Agent: {op.agent_name}\nArgument: {op.argument}" for op in opinions])

    prompt = f"""You are the Chief Auditor. Your role is to compile the final official Audit Report based on judicial opinions.

JUDICIAL OPINIONS:
{opinion_text}

Generate a structured AuditReport:
1. report_id: unique ID
2. summary: Top-level summary of the audit
3. criteria_results: A list of checklist items (CriterionResult) with specific pass/fail and justification.
4. final_decision: "Pass", "Conditional Pass", or "Fail".
"""
    report = llm.invoke([HumanMessage(content=prompt)])
    print(f"  📜 Generated final audit report: {report.report_id}")
    return {"report": report}
