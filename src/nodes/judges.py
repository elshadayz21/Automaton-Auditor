import json
import uuid
from typing import Any
from pydantic import ValidationError
from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, JudicialOpinion, OpinionList, AuditReport, CriterionResult, Evidence


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _load_rubric_criteria(rubric_path: str = "rubric.json") -> dict[str, str]:
    """Load rubric and return a map of dimension_name -> forensic_instruction."""
    try:
        with open(rubric_path, "r", encoding="utf-8") as f:
            rubric = json.load(f)
            return {
                dim.get("dimension_name", "General"): dim.get("forensic_instruction", "")
                for dim in rubric.get("dimensions", [])
            }
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _safe_invoke_judge(llm, messages: list, agent_name: str, dimensions: list[str]) -> list[JudicialOpinion]:
    """
    Invoke judge LLM with schema validation and retry/fallback.
    - Attempt 1: Normal invoke.
    - Attempt 2: Retry on ValidationError.
    - Fallback: Return score-1 fallback opinions for all dimensions.
    """
    for attempt in range(2):
        try:
            result = llm.invoke(messages)
            # Validate each opinion in the list
            validated = []
            for op in result.opinions:
                if not op.opinion_id:
                    op.opinion_id = f"{agent_name.lower()}-{uuid.uuid4().hex[:8]}"
                if not op.dimension_name or op.dimension_name not in dimensions:
                    op.dimension_name = dimensions[0] if dimensions else "General"
                validated.append(op)
            return validated
        except (ValidationError, AttributeError, Exception) as e:
            if attempt == 0:
                print(f"  ⚠️ {agent_name}: Malformed output (attempt {attempt+1}), retrying... ({type(e).__name__})")
                continue
            else:
                print(f"  ❌ {agent_name}: Retry failed. Generating fallback opinions. ({type(e).__name__}: {e})")
                return [
                    JudicialOpinion(
                        opinion_id=f"{agent_name.lower()}-fallback-{uuid.uuid4().hex[:6]}",
                        dimension_name=dim,
                        agent_name=agent_name,
                        score=1,
                        argument=f"Malformed output from {agent_name}. Could not parse structured response after 2 attempts.",
                        evidence_refs=[]
                    )
                    for dim in dimensions
                ]
    return []


def _build_judge_prompt(persona_description: str, agent_name: str, score_guide: str,
                        evidence_text: str, dimensions: list[str],
                        rubric_criteria: dict[str, str]) -> str:
    """Build a judge prompt with dynamic rubric criteria injected per dimension."""
    criteria_block = "\n".join([
        f"- **{dim}**: {rubric_criteria.get(dim, 'Evaluate based on available evidence.')}"
        for dim in dimensions
    ])

    return f"""You are the {persona_description}.

EVIDENCE COLLECTED:
{evidence_text}

RUBRIC CRITERIA (evaluate each dimension against its specific criterion):
{criteria_block}

Provide exactly ONE opinion for EACH of these dimensions:
{', '.join(dimensions)}

For each opinion:
1. opinion_id: "{agent_name.lower()}-" followed by a unique string
2. dimension_name: The exact name of the dimension you are judging.
3. agent_name: "{agent_name}"
4. score: An integer from 1 to 5 ({score_guide}).
5. argument: Your synthesis for this dimension based on its rubric criterion above. Mention specific evidence IDs.
6. evidence_refs: List of evidence IDs you are basing this opinion on.
"""


# ─────────────────────────────────────────────
# Judge Nodes
# ─────────────────────────────────────────────

def Prosecutor(state: AgentState) -> dict[str, Any]:
    """Prosecutor persona: Critical, looks for flaws, vulnerabilities, and missing guards."""
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": []}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(OpinionList)
    rubric_criteria = _load_rubric_criteria()
    dimensions = list(set([ev.dimension_name for ev in evidences.values()]))

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nDimension: {ev.dimension_name}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])

    prompt = _build_judge_prompt(
        persona_description="Prosecutor Analyst. Your role is strictly critical. Identify flaws, vulnerabilities, missing guards, non-compliance, and logic flaws",
        agent_name="Prosecutor",
        score_guide="1 = critical flaw/failure, 5 = perfect/no issues",
        evidence_text=evidence_text,
        dimensions=dimensions,
        rubric_criteria=rubric_criteria,
    )

    opinions = _safe_invoke_judge(llm, [HumanMessage(content=prompt)], "Prosecutor", dimensions)
    for op in opinions:
        print(f"  ⚖️ Prosecutor opinion: {op.opinion_id} [{op.dimension_name}] score: {op.score}")
    return {"opinions": opinions}


def DefenseAttorney(state: AgentState) -> dict[str, Any]:
    """Defense Attorney persona: Optimistic, rewards effort, looks for mitigating factors."""
    evidences = state.get("evidences", {})
    if not evidences:
        return {"opinions": []}

    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(OpinionList)
    rubric_criteria = _load_rubric_criteria()
    dimensions = list(set([ev.dimension_name for ev in evidences.values()]))

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nDimension: {ev.dimension_name}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])

    prompt = _build_judge_prompt(
        persona_description="Defense Attorney Analyst. Your role is optimistic. Identify mitigating factors, robust error handling, stylistic justifications, and system strengths",
        agent_name="DefenseAttorney",
        score_guide="1 = no redeeming qualities, 5 = excellent/perfect",
        evidence_text=evidence_text,
        dimensions=dimensions,
        rubric_criteria=rubric_criteria,
    )

    opinions = _safe_invoke_judge(llm, [HumanMessage(content=prompt)], "DefenseAttorney", dimensions)
    for op in opinions:
        print(f"  ⚖️ Defense opinion: {op.opinion_id} [{op.dimension_name}] score: {op.score}")
    return {"opinions": opinions}


def TechLeadJudge(state: AgentState) -> dict[str, Any]:
    """Tech Lead Judge persona: Pragmatic, focuses on maintainability, and resolves conflicts."""
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
    rubric_criteria = _load_rubric_criteria()
    dimensions = list(set([ev.dimension_name for ev in evidences.values()]))

    evidence_text = "\n\n".join([
        f"ID: {ev.evidence_id}\nDimension: {ev.dimension_name}\nGoal: {ev.goal}\nFound: {ev.found}\nRationale: {ev.rationale}"
        for ev in evidences.values()
    ])

    prompt = _build_judge_prompt(
        persona_description="Tech Lead Judge. Your role is pragmatic, focusing on maintainability, engineering tradeoffs, and system synthesis. Resolve any potential technical conflicts",
        agent_name="TechLeadJudge",
        score_guide="1 = unmaintainable/broken, 5 = production-ready",
        evidence_text=evidence_text,
        dimensions=dimensions,
        rubric_criteria=rubric_criteria,
    )

    opinions = _safe_invoke_judge(llm, [HumanMessage(content=prompt)], "TechLeadJudge", dimensions)
    for op in opinions:
        print(f"  ⚖️ TechLead opinion: {op.opinion_id} [{op.dimension_name}] score: {op.score}")
    return {"opinions": opinions}


# ─────────────────────────────────────────────
# ChiefJustice — Named Rule Blocks
# ─────────────────────────────────────────────

def ChiefJustice(state: AgentState) -> dict[str, Any]:
    """
    Chief Justice node: Deterministic Synthesis Engine.
    Applies 5 explicit named rule blocks to resolve disputes and generate the final report.
    """
    opinions = state.get("opinions", [])
    evidences = state.get("evidences", {})

    # ═══════════════════════════════════════════
    # RULE 1: Rule of Evidence
    # Discard opinions that cite no evidence.
    # ═══════════════════════════════════════════
    valid_opinions = []
    for op in opinions:
        if not op.evidence_refs:
            print(f"  📏 Rule of Evidence: Discarding {op.opinion_id} (no evidence refs)")
        else:
            valid_opinions.append(op)

    # Group valid opinions by dimension
    dimension_groups: dict[str, list[JudicialOpinion]] = {}
    for op in valid_opinions:
        if op.dimension_name not in dimension_groups:
            dimension_groups[op.dimension_name] = []
        dimension_groups[op.dimension_name].append(op)

    criteria_results = []
    total_score = 0
    calculated_dimensions = 0

    for dim_name, ops in dimension_groups.items():
        scores = [op.score for op in ops]
        avg_score = sum(scores) / len(scores) if scores else 0

        prosecutor_op = next((op for op in ops if op.agent_name == "Prosecutor"), None)
        defense_op = next((op for op in ops if op.agent_name == "DefenseAttorney"), None)
        tech_lead_op = next((op for op in ops if op.agent_name == "TechLeadJudge"), None)

        # Start with average
        final_dim_score = avg_score
        applied_rules = []

        # ═══════════════════════════════════════════
        # RULE 2: Security Override Cap
        # If Prosecutor scores ≤ 2, cap the final score at 2.
        # ═══════════════════════════════════════════
        if prosecutor_op and prosecutor_op.score <= 2:
            if final_dim_score > 2:
                final_dim_score = 2
                applied_rules.append(f"Security Override Cap applied (Prosecutor score: {prosecutor_op.score})")
                print(f"  📏 Security Override Cap: {dim_name} capped at 2 (Prosecutor={prosecutor_op.score})")

        # ═══════════════════════════════════════════
        # RULE 3: Fact Supremacy
        # If detective evidence reliability is high (>= 0.8) but
        # a judge scores low, flag the contradiction.
        # ═══════════════════════════════════════════
        dim_evidences = [ev for ev in evidences.values() if ev.dimension_name == dim_name]
        avg_reliability = (sum(e.reliability_score for e in dim_evidences) / len(dim_evidences)) if dim_evidences else 0
        if avg_reliability >= 0.8 and avg_score < 3:
            applied_rules.append(f"Fact Supremacy flagged: high-reliability evidence ({avg_reliability:.2f}) contradicts low judge scores ({avg_score:.1f})")
            print(f"  📏 Fact Supremacy: {dim_name} — evidence reliability {avg_reliability:.2f} contradicts scores")

        # ═══════════════════════════════════════════
        # RULE 4: Architecture Weighting
        # TechLead is the tiebreaker when variance ≥ 2.
        # ═══════════════════════════════════════════
        variance = max(scores) - min(scores) if len(scores) > 1 else 0
        if variance >= 2 and tech_lead_op:
            final_dim_score = tech_lead_op.score
            applied_rules.append(f"Architecture Weighting: TechLead score ({tech_lead_op.score}) used as tiebreaker (variance={variance})")
            print(f"  📏 Architecture Weighting: {dim_name} — TechLead={tech_lead_op.score} (variance={variance})")

        # Re-apply Security Override Cap after weighting
        if prosecutor_op and prosecutor_op.score <= 2 and final_dim_score > 2:
            final_dim_score = 2
            applied_rules.append("Security Override Cap re-applied after weighting")

        # ═══════════════════════════════════════════
        # RULE 5: Dissent Threshold
        # Variance ≥ 2 triggers a dissent summary.
        # ═══════════════════════════════════════════
        dissent_text = None
        if variance >= 2:
            score_summary = ", ".join([f"{op.agent_name} {op.score}" for op in ops])
            dissent_text = f"Variance {variance}: {score_summary}. " + " | ".join(applied_rules) if applied_rules else f"Variance {variance}: {score_summary}."
            print(f"  📏 Dissent Threshold: {dim_name} — variance={variance}")

        # Remediation from Tech Lead
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

    # ═══════════════════════════════════════════
    # Generate Report Markdown
    # ═══════════════════════════════════════════
    report_id = f"audit-{uuid.uuid4().hex[:8]}"

    md_lines = [
        "# Audit Report",
        "",
        "## Executive Summary",
        "",
        f"Audit of the target repository: {len(criteria_results)} criteria evaluated. Overall score: {overall_score}/5. "
        f"{sum(1 for c in criteria_results if c.dissent_summary)} dissent recorded.",
        "",
        f"**Overall Score:** {overall_score}/5",
        "",
        "---",
        "",
        "## Criterion Breakdown",
    ]

    for res in criteria_results:
        md_lines.extend([
            "",
            f"### {res.criterion_name}",
            "",
            f"- **Final Score:** {int(res.score)}/5",
            "",
            "**Judge opinions:**"
        ])

        for agent_name, op in res.opinions_dict.items():
            arg_preview = op.argument[:250] + "..." if len(op.argument) > 250 else op.argument
            md_lines.append(f"- **{agent_name}** (score {op.score}): {arg_preview}")

        if res.dissent_summary:
            md_lines.extend(["", f"**Dissent summary:** {res.dissent_summary}"])

        md_lines.extend(["", f"**Remediation:** {res.remediation}"])

    md_lines.extend(["", "---", "", "## Remediation Plan", ""])

    for res in criteria_results:
        md_lines.append(f"**{res.criterion_name}**: {res.remediation}")
        md_lines.append("")

    markdown_report = "\n".join(md_lines)

    with open("audit_report.md", "w", encoding="utf-8") as f:
        f.write(markdown_report)

    report_obj = AuditReport(
        report_id=report_id,
        summary=f"Audit finished with {overall_score}/5 across {calculated_dimensions} dimensions.",
        criteria_results=criteria_results,
        final_decision="Pass" if overall_score >= 3.0 else "Fail"
    )

    print(f"  📜 Chief Justice authored final report: {report_id} (saved to audit_report.md)")
    return {"report": report_obj}

