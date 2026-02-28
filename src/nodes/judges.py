import json
from typing import Any
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, JudicialOpinion, AuditReport, CriterionResult, Evidence

def Prosecutor(state: AgentState) -> dict[str, Any]:
    """
    Prosecutor persona: Critical, looks for flaws, vulnerabilities, and missing guards.
    """
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": []}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(JudicialOpinion)

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])

    prompt = f"""You are the Prosecutor Analyst. Your role is strictly critical. Review the evidence and identify flaws, vulnerabilities, missing guards, non-compliance, and logic flaws.

EVIDENCE COLLECTED:
{evidence_text}

Provide your opinion:
1. opinion_id: "prosecutor-" followed by a unique string
2. agent_name: "Prosecutor"
3. argument: A highly critical synthesis of the findings, focusing on what is missing or wrong. Mention specific evidence IDs.
4. evidence_refs: List of evidence IDs you are basing this opinion on.
"""
    opinion = llm.invoke([HumanMessage(content=prompt)])
    print(f"  ⚖️ Formulated Prosecutor opinion: {opinion.opinion_id}")
    return {"opinions": [opinion]}


def DefenseAttorney(state: AgentState) -> dict[str, Any]:
    """
    Defense Attorney persona: Optimistic, rewards effort, looks for mitigating factors.
    """
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": []}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(JudicialOpinion)

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])

    prompt = f"""You are the Defense Attorney Analyst. Your role is optimistic. Review the evidence and identify mitigating factors, robust error handling, stylistic justifications, and system strengths.

EVIDENCE COLLECTED:
{evidence_text}

Provide your opinion:
1. opinion_id: "defense-" followed by a unique string
2. agent_name: "DefenseAttorney"
3. argument: A highly optimistic synthesis of the findings, focusing on what was done right and mitigating any flaws. Mention specific evidence IDs.
4. evidence_refs: List of evidence IDs you are basing this opinion on.
"""
    opinion = llm.invoke([HumanMessage(content=prompt)])
    print(f"  ⚖️ Formulated Defense opinion: {opinion.opinion_id}")
    return {"opinions": [opinion]}


def TechLeadJudge(state: AgentState) -> dict[str, Any]:
    """
    Tech Lead Judge persona: Pragmatic, focuses on maintainability, and resolves conflicts.
    This replaces the generic JudicialAnalyst.
    """
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": [JudicialOpinion(
            opinion_id="error-no-evidence",
            agent_name="TechLeadJudge",
            argument="No evidence was collected during the investigation phase.",
            evidence_refs=[]
        )]}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(JudicialOpinion)

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])

    # In a full Phase 2 of the Judicial Expansion plan, this node might read the Prosecutor/Defense opinions.
    # For now, it runs in parallel (or just after) and focuses on Pragmatism as requested in Step 3 Phase 3.
    prompt = f"""You are the Tech Lead Judge. Your role is pragmatic, focusing on maintainability, engineering tradeoffs, and system synthesis.

EVIDENCE COLLECTED:
{evidence_text}

Provide your opinion:
1. opinion_id: "techlead-" followed by a unique string
2. agent_name: "TechLeadJudge"
3. argument: A balanced, pragmatic synthesis of the findings, focusing on maintainability and best practices. Resolve any potential technical conflicts in the evidence. Mention specific evidence IDs.
4. evidence_refs: List of evidence IDs you are basing this opinion on.
"""
    opinion = llm.invoke([HumanMessage(content=prompt)])
    print(f"  ⚖️ Formulated Tech Lead opinion: {opinion.opinion_id}")
    return {"opinions": [opinion]}


def ChiefJustice(state: AgentState) -> dict[str, Any]:
    """
    Chief Justice node: Acts as the Synthesis Engine.
    Uses hardcoded, deterministic Python logic to resolve disputes between the Judges,
    rather than relying on an LLM prompt. Generates a highly structured Markdown AuditReport.
    """
    opinions = state.get("opinions", [])
    evidences = state.get("evidences", {})

    # Start with a pristine list of valid opinions
    valid_opinions = []
    
    # --- Rule of Evidence ---
    # Disregard any opinion that references no evidence.
    for op in opinions:
        if not op.evidence_refs:
            print(f"  ⚖️ Chief Justice: Disregarding opinion {op.opinion_id} due to Rule of Evidence (no refs).")
        else:
            valid_opinions.append(op)

    # --- Rule of Security ---
    # If the Prosecutor raises severe issues (mapped to specific keywords) across their valid opinions,
    # the audit automatically fails, overriding the Defense and Tech Lead.
    critical_flags = ["vulnerabilit", "missing guard", "unsafe", "hardcoded", "exposure"]
    security_breach = False
    fatal_reason = ""

    for op in valid_opinions:
        if op.agent_name == "Prosecutor":
            for flag in critical_flags:
                if flag in op.argument.lower():
                    security_breach = True
                    fatal_reason = f"Critical security flaw identified by Prosecutor: {flag}"
                    break
        if security_breach:
            break

    # Determine Final Decision
    final_decision = "Pass"
    if security_breach:
        final_decision = "Fail"
    elif len(valid_opinions) < len(opinions):
        # We had to discard opinions
        final_decision = "Conditional Pass"
    elif not valid_opinions:
        final_decision = "Incomplete (No Valid Opinions)"

    # Build criteria results
    criteria_results = []
    for op in valid_opinions:
        criteria_results.append(
            CriterionResult(
                criterion_name=f"{op.agent_name} Review",
                passed=(not security_breach),
                justification=op.argument[:200] + "..." if len(op.argument) > 200 else op.argument
            )
        )

    # Generate Highly Structured Markdown Report
    import uuid
    report_id = f"audit-{uuid.uuid4().hex[:8]}"
    
    md_lines = [
        f"# ⚖️ Automaton Auditor: Supreme Court Verdict",
        f"**Report ID:** `{report_id}`",
        f"**Final Decision:** **{final_decision.upper()}**",
        f"",
        f"## 1. Executive Summary",
    ]
    
    if security_breach:
        md_lines.append(f"> ❌ **AUDIT FAILED:** The Rule of Security was invoked. {fatal_reason}")
    else:
        md_lines.append(f"> ✅ **AUDIT PASSED:** The system meets the required threshold of security and maintainability.")
        
    md_lines.extend([
        f"",
        f"## 2. Dialectical Bench Summaries",
        f"The findings of the parallel judicial bench are synthesized below."
    ])

    for op in valid_opinions:
        md_lines.extend([
            f"",
            f"### {op.agent_name}'s Opinion",
            f"- **Argument:** {op.argument}",
            f"- **Citations:** {', '.join(op.evidence_refs)}"
        ])

    md_lines.extend([
        f"",
        f"## 3. Evidence Ledger",
        f"The following raw factual evidence was collected by the Detective Layer and reviewed by the bench:"
    ])

    for ev_id, ev in evidences.items():
        md_lines.extend([
            f"",
            f"#### Evidence `[{ev_id}]`",
            f"- **Goal:** {ev.goal}",
            f"- **Found:** {ev.found}",
            f"- **Reliability:** {ev.reliability_score:.2f}"
        ])

    markdown_report = "\n".join(md_lines)
    
    # Write to disk
    with open("audit_report.md", "w", encoding="utf-8") as f:
        f.write(markdown_report)

    # Construct internal state object
    report_obj = AuditReport(
        report_id=report_id,
        summary=f"Audit finished with {len(valid_opinions)} valid opinions. Decision: {final_decision}",
        criteria_results=criteria_results,
        final_decision=final_decision
    )

    print(f"  📜 Chief Justice authored final report: {report_id} (saved to audit_report.md)")
    return {"report": report_obj}

