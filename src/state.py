import operator
from typing import Annotated, TypedDict
from pydantic import BaseModel, Field

class Evidence(BaseModel):
    """
    Schema representing a piece of evidence collected during the audit.
    Enriched with forensic-grade fields for traceability.
    """
    evidence_id: str = Field(description="Unique identifier for the evidence")
    goal: str = Field(description="What the rubric dimension was looking for")
    found: str = Field(description="What was actually observed in the source artifact")
    location: str = Field(description="Where in the codebase or document this was found (file path, section, commit, etc.)")
    rationale: str = Field(description="Why this observation is significant as evidence")
    content: str = Field(description="Full detailed content or raw description of the evidence")
    source: str = Field(description="Source of the evidence — URL, file path, or document name")
    reliability_score: float = Field(description="Confidence score for this evidence (0.0 = uncertain, 1.0 = definitive)", ge=0.0, le=1.0)

class JudicialOpinion(BaseModel):
    """
    Schema representing a judicial opinion or argument provided by an agent.
    """
    opinion_id: str = Field(description="Unique identifier for the judicial opinion")
    agent_name: str = Field(description="Name of the agent or role providing this opinion")
    argument: str = Field(description="The core argument or judicial reasoning")
    evidence_refs: list[str] = Field(default_factory=list, description="List of evidence IDs referenced in this opinion")

class CriterionResult(BaseModel):
    """
    Schema representing the result of evaluating a specific audit criterion.
    """
    criterion_name: str = Field(description="Name of the audit criterion being evaluated")
    passed: bool = Field(description="Whether the criterion was met")
    justification: str = Field(description="Explanation of why it passed or failed")

class AuditReport(BaseModel):
    """
    Schema representing the final audit report aggregating all findings.
    """
    report_id: str = Field(description="Unique identifier for the report")
    summary: str = Field(description="Executive summary of the audit findings")
    criteria_results: list[CriterionResult] = Field(default_factory=list, description="Results for all evaluated criteria")
    final_decision: str = Field(description="Final audit decision or conclusion")

class AgentState(TypedDict):
    """
    LangGraph AgentState using TypedDict with annotated reducers.
    Reducers ensure that separate nodes updating the state correctly merge values 
    instead of overwriting them.
    """
    # operator.ior merges dictionary updates, crucial for parallel data collection
    evidences: Annotated[dict[str, Evidence], operator.ior]
    
    # operator.add appends to lists, preventing parallel opinions from overwriting one another
    opinions: Annotated[list[JudicialOpinion], operator.add]
    
    # A single audit report that can be overwritten or generated at the end
    report: AuditReport | None
