import json
from typing import Any
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, JudicialOpinion, OpinionList, AuditReport, CriterionResult, Evidence

def Prosecutor(state: AgentState) -> dict[str, Any]:
    """
    Prosecutor persona: Critical, looks for flaws, vulnerabilities, and missing guards.
    """
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": []}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(OpinionList)

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nDimension: {ev.dimension_name}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])
    
    dimensions = list(set([ev.dimension_name for ev in evidences.values()]))

    prompt = f"""You are the Prosecutor Analyst. Your role is strictly critical. Review the evidence and identify flaws, vulnerabilities, missing guards, non-compliance, and logic flaws.

EVIDENCE COLLECTED:
{evidence_text}

Provide exactly ONE opinion for EACH of these dimensions:
{', '.join(dimensions)}

For each opinion:
1. opinion_id: "prosecutor-" followed by a unique string
2. dimension_name: The exact name of the dimension you are judging.
3. agent_name: "Prosecutor"
4. score: An integer from 1 to 5 (1 = critical flaw/failure, 5 = perfect/no issues).
5. argument: A highly critical synthesis of the findings for this dimension, focusing on what is missing or wrong. Mention specific evidence IDs.
6. evidence_refs: List of evidence IDs you are basing this opinion on.
"""
    result = llm.invoke([HumanMessage(content=prompt)])
    for op in result.opinions:
        print(f"  ⚖️ Formulated Prosecutor opinion: {op.opinion_id} [{op.dimension_name}] score: {op.score}")
    return {"opinions": result.opinions}


def DefenseAttorney(state: AgentState) -> dict[str, Any]:
    """
    Defense Attorney persona: Optimistic, rewards effort, looks for mitigating factors.
    """
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": []}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(OpinionList)

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nDimension: {ev.dimension_name}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])
    
    dimensions = list(set([ev.dimension_name for ev in evidences.values()]))

    prompt = f"""You are the Defense Attorney Analyst. Your role is optimistic. Review the evidence and identify mitigating factors, robust error handling, stylistic justifications, and system strengths.

EVIDENCE COLLECTED:
{evidence_text}

Provide exactly ONE opinion for EACH of these dimensions:
{', '.join(dimensions)}

For each opinion:
1. opinion_id: "defense-" followed by a unique string
2. dimension_name: The exact name of the dimension you are judging.
3. agent_name: "DefenseAttorney"
4. score: An integer from 1 to 5 (1 = no redeeming qualities, 5 = excellent/perfect).
5. argument: A highly optimistic synthesis of the findings for this dimension, focusing on what was done right and mitigating any flaws. Mention specific evidence IDs.
6. evidence_refs: List of evidence IDs you are basing this opinion on.
"""
    result = llm.invoke([HumanMessage(content=prompt)])
    for op in result.opinions:
        print(f"  ⚖️ Formulated Defense opinion: {op.opinion_id} [{op.dimension_name}] score: {op.score}")
    return {"opinions": result.opinions}


def TechLeadJudge(state: AgentState) -> dict[str, Any]:
    """
    Tech Lead Judge persona: Pragmatic, focuses on maintainability, and resolves conflicts.
    This replaces the generic JudicialAnalyst.
    """
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": [JudicialOpinion(
            opinion_id="error-no-evidence",
            dimension_name="General",
            agent_name="TechLeadJudge",
            score=1,
            argument="No evidence was collected during the investigation phase.",
            evidence_refs=[]
        )]}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(OpinionList)

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nDimension: {ev.dimension_name}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])
    
    dimensions = list(set([ev.dimension_name for ev in evidences.values()]))

    prompt = f"""You are the Tech Lead Judge. Your role is pragmatic, focusing on maintainability, engineering tradeoffs, and system synthesis.

EVIDENCE COLLECTED:
{evidence_text}

Provide exactly ONE opinion for EACH of these dimensions:
{', '.join(dimensions)}

For each opinion:
1. opinion_id: "techlead-" followed by a unique string
2. dimension_name: The exact name of the dimension you are judging.
3. agent_name: "TechLeadJudge"
4. score: An integer from 1 to 5 (1 = unmaintainable/broken, 5 = production-ready).
5. argument: A balanced, pragmatic synthesis of the findings for this dimension, focusing on maintainability and best practices. Resolve any potential technical conflicts in the evidence. Mention specific evidence IDs.
6. evidence_refs: List of evidence IDs you are basing this opinion on.
"""
    result = llm.invoke([HumanMessage(content=prompt)])
    for op in result.opinions:
        print(f"  ⚖️ Formulated Tech Lead opinion: {op.opinion_id} [{op.dimension_name}] score: {op.score}")
    return {"opinions": result.opinions}


def ChiefJustice(state: AgentState) -> dict[str, Any]:
    """
    Chief Justice node: Acts as the Synthesis Engine.
    Implements a quantitative scoring system, mathematical dissent detection, 
    and generates the final Markdown report in the requested format.
    """
    opinions = state.get("opinions", [])
    evidences = state.get("evidences", {})

    # Group opinions by dimension
    dimension_groups: dict[str, list[JudicialOpinion]] = {}
    for op in opinions:
        if op.dimension_name not in dimension_groups:
            dimension_groups[op.dimension_name] = []
        dimension_groups[op.dimension_name].append(op)

    criteria_results = []
    total_score = 0
    calculated_dimensions = 0

    # Process each dimension
    for dim_name, ops in dimension_groups.items():
        # Mathematical Scorer
        scores = [op.score for op in ops]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        # Tech Lead Weighting (Pragmatic Override)
        tech_lead_op = next((op for op in ops if op.agent_name == "TechLeadJudge"), None)
        final_dim_score = tech_lead_op.score if tech_lead_op else avg_score
        
        # Dissent Detection (Variance >= 2)
        variance = max(scores) - min(scores) if len(scores) > 1 else 0
        dissent_text = None
        if variance >= 2:
            score_summary = ", ".join([f"{op.agent_name} {op.score}" for op in ops])
            dissent_text = f"Variance {variance}: {score_summary}. Re-evaluation applied (Tech Lead weight)."

        # Remediation Formulation
        # Note: In a production system, this could be another LLM call or extracted from Tech Lead.
        # Here we extract it from the Tech Lead's argument as a base.
        remediation = tech_lead_op.argument if tech_lead_op else "Follow best practices for this dimension."

        criteria_results.append(
            CriterionResult(
                criterion_name=dim_name,
                score=final_dim_score,
                dissent_summary=dissent_text,
                remediation=remediation,
                opinions_dict={op.agent_name: op for op in ops}
            )
        )
        total_score += final_dim_score
        calculated_dimensions += 1

    overall_score = round(total_score / calculated_dimensions, 1) if calculated_dimensions > 0 else 0

    # --- Generate Report Markdown ---
    import uuid
    report_id = f"audit-{uuid.uuid4().hex[:8]}"
    
    md_lines = [
        f"# Audit Report",
        f"",
        f"## Executive Summary",
        f"",
        f"Audit of the target repository: {len(criteria_results)} criteria evaluated. Overall score: {overall_score}/5. "
        f"{sum(1 for c in criteria_results if c.dissent_summary)} dissent recorded.",
        f"",
        f"**Overall Score:** {overall_score}/5",
        f"",
        f"---",
        f"",
        f"## Criterion Breakdown",
    ]

    for res in criteria_results:
        md_lines.extend([
            f"",
            f"### {res.criterion_name}",
            f"",
            f"- **Final Score:** {int(res.score)}/5",
            f"",
            f"**Judge opinions:**"
        ])
        
        for agent_name, op in res.opinions_dict.items():
            # Truncate argument for the breakdown section
            arg_preview = op.argument[:250] + "..." if len(op.argument) > 250 else op.argument
            md_lines.append(f"- **{agent_name}** (score {op.score}): {arg_preview}")

        if res.dissent_summary:
            md_lines.extend([
                f"",
                f"**Dissent summary:** {res.dissent_summary}"
            ])
            
        md_lines.extend([
            f"",
            f"**Remediation:** {res.remediation}"
        ])

    md_lines.extend([
        f"",
        f"---",
        f"",
        f"## Remediation Plan",
        f""
    ])

    for res in criteria_results:
        md_lines.append(f"**{res.criterion_name}**: {res.remediation}")
        md_lines.append("")

    markdown_report = "\n".join(md_lines)
    
    # Write to disk
    with open("audit_report.md", "w", encoding="utf-8") as f:
        f.write(markdown_report)

    # Construct internal state object
    report_obj = AuditReport(
        report_id=report_id,
        summary=f"Audit finished with {overall_score}/5 across {calculated_dimensions} dimensions.",
        criteria_results=criteria_results,
        final_decision="Pass" if overall_score >= 3.0 else "Fail"
    )

    print(f"  📜 Chief Justice authored final report: {report_id} (saved to audit_report.md)")
    return {"report": report_obj}

