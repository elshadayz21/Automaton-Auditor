import json
import uuid
import time
import base64
from pathlib import Path
from typing import Any
from dotenv import load_dotenv
load_dotenv()  # Load .env before any LLM client is created

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from src.state import AgentState, Evidence, EvidenceList
from src.tools.repo_tools import clone_repository, analyze_graph_structure, extract_git_history
from src.tools.doc_tools import ingest_pdf


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def get_rubric_instructions(target_artifact: str, rubric_path: str = "rubric.json") -> list[dict]:
    """Loads the rubric and returns dimensions matching the target_artifact."""
    try:
        with open(rubric_path, "r", encoding="utf-8") as f:
            rubric = json.load(f)
            return [dim for dim in rubric.get("dimensions", []) if dim.get("target_artifact") == target_artifact]
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print(f"Warning: {rubric_path} is not valid JSON.")
        return []


def _invoke_with_retry(llm, messages: list, label: str = "") -> Any:
    """Invoke LLM with exponential backoff on RESOURCE_EXHAUSTED."""
    for attempt in range(3):
        try:
            return llm.invoke(messages)
        except Exception as err:
            if "RESOURCE_EXHAUSTED" in str(err) and attempt < 2:
                wait = 30 * (attempt + 1)
                print(f"Rate limited{' (' + label + ')' if label else ''}. Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise


def _ensure_id(evidence: Evidence, prefix: str) -> Evidence:
    """Guarantee the LLM populated a real unique evidence_id."""
    if not evidence.evidence_id or evidence.evidence_id in ("uuid", ""):
        evidence.evidence_id = f"{prefix}-{uuid.uuid4().hex[:8]}"
    return evidence


# ─────────────────────────────────────────────
# Node 1: RepoInvestigator
# ─────────────────────────────────────────────

# Three distinct forensic lenses applied to every repo
_REPO_CHECKS = [
    {
        "key": "graph_wiring",
        "goal": "Verify that LangGraph nodes are correctly wired — edges defined, entry/exit points set, and the graph compiles without errors.",
        "instruction": (
            "Inspect the AST structure and commit history for LangGraph graph definitions. "
            "Look for StateGraph instantiation, add_node / add_edge / set_entry_point calls, "
            "and graph.compile() usage. Report exactly which files/functions contain these constructs."
        ),
    },
    {
        "key": "state_design",
        "goal": "Verify the AgentState uses TypedDict with annotated reducers (operator.add / operator.ior) for safe parallel state merging.",
        "instruction": (
            "Inspect the AST for TypedDict subclasses and Annotated type hints. "
            "Look for operator.add or operator.ior as reducer annotations. "
            "Report which state fields use reducers and which do not."
        ),
    },
    {
        "key": "tool_safety",
        "goal": "Verify that tool functions include input validation, try/except error handling, and do not expose secrets or raw exceptions to callers.",
        "instruction": (
            "Inspect function definitions in the tools directory from the AST. "
            "Check for try/except blocks, parameter type hints, and any hardcoded credentials or bare `except` clauses. "
            "Report specific findings per function."
        ),
    },
]


def RepoInvestigator(state: AgentState) -> dict[str, Any]:
    """
    Forensic repository investigator.
    Produces three distinct Evidence items per repo in a single batched LLM call:
      1. graph_wiring  — node/edge connectivity
      2. state_design  — TypedDict + reducer usage
      3. tool_safety   — error handling & input validation
    """
    instructions = get_rubric_instructions("github_repo")
    if not instructions:
        return {"evidences": {}}

    target_repo_url = instructions[0].get("target_repo_url")
    if not target_repo_url:
        target_repo_url = "https://github.com/langchain-ai/langgraph.git"
        print(f"No target_repo_url in rubric. Using fallback: {target_repo_url}")

    evidences: dict[str, Evidence] = {}
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(EvidenceList)

    try:
        with clone_repository(target_repo_url) as repo_dir:
            structure = analyze_graph_structure(repo_dir)
            structure_str = json.dumps(structure, indent=2)[:3000]
            history = extract_git_history(repo_dir, max_commits=10)
            history_str = json.dumps(history, indent=2)[:2000]

            combined_instruction = "\n\n".join([f"CHECK {i+1}: {c['goal']}\n{c['instruction']}" for i, c in enumerate(_REPO_CHECKS)])

            prompt_text = f"""You are a Forensic Code Investigator. Your mandate is strictly factual observation.
Do NOT provide opinions, rulings, or final decisions.

Your task is to perform THREE distinct forensic checks in this single response.

---
{combined_instruction}
---

Repository Source: {target_repo_url}

AST Class/Function Structure (truncated):
{structure_str}

Recent Commit History (truncated):
{history_str}

For EACH check, populate a full Evidence record in the 'evidences' list:
- goal: restate the specific check's goal
- found: exactly what you observed for that check
- location: file paths / function names for that check
- rationale: why this matters forensically
- content: detailed raw notes for this check
- source: {target_repo_url}
- reliability_score: 0.0–1.0 based on how clearly the AST/history confirms your finding
- evidence_id: generate a unique ID like 'repo-wiring', 'repo-state', 'repo-safety'
"""
            batch_result = _invoke_with_retry(llm, [HumanMessage(content=prompt_text)], label="repo-batch")
            
            for ev in batch_result.evidences:
                # Basic validation/cleanup
                if not ev.evidence_id:
                    ev.evidence_id = f"repo-{uuid.uuid4().hex[:8]}"
                evidences[ev.evidence_id] = ev
                print(f"  ✓ Collected batched evidence: {ev.evidence_id}")

    except Exception as e:
        print(f"RepoInvestigator failed: {e}")

    return {"evidences": evidences}


# ─────────────────────────────────────────────
# Node 2: DocAnalyst
# ─────────────────────────────────────────────

def DocAnalyst(state: AgentState) -> dict[str, Any]:
    """
    Forensic PDF document analyst (RAG-lite).
    Produces Evidence items from structured document chunks.
    """
    instructions = get_rubric_instructions("pdf_report")
    if not instructions:
        return {"evidences": {}}

    target_pdf_path = instructions[0].get("target_pdf_path")
    if not target_pdf_path:
        print("No target_pdf_path found in rubric for DocAnalyst.")
        return {"evidences": {}}

    evidences: dict[str, Evidence] = {}
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(Evidence)

    try:
        document_chunks = ingest_pdf(target_pdf_path)
        context_text = "\n---\n".join(document_chunks[:3])

        for instruction in instructions:
            goal = instruction.get("forensic_instruction", "")
            prompt_text = f"""You are a Forensic Document Analyst. Your mandate is strictly factual observation.
Do NOT provide opinions, rulings, or final decisions.

GOAL (what to look for): {goal}

Document Source: {target_pdf_path}

Extracted Document Text (first 3 chunks):
{context_text}

Populate EVERY field of the Evidence record:
- goal: restate what you were looking for
- found: exactly what you found in the text (quotes preferred)
- location: section title, page hint, or chunk index where it appears
- rationale: why this is significant as forensic evidence
- content: full verbatim extract or summary
- source: {target_pdf_path}
- reliability_score: 0.0–1.0
- evidence_id: generate a unique UUID string
"""
            evidence = _invoke_with_retry(llm, [HumanMessage(content=prompt_text)], label="doc")
            evidence = _ensure_id(evidence, "doc-ev")
            evidences[evidence.evidence_id] = evidence
            print(f"  ✓ Collected doc evidence: {evidence.evidence_id}")

    except Exception as e:
        print(f"DocAnalyst failed: {e}")

    return {"evidences": evidences}


# ─────────────────────────────────────────────
# Node 3: VisionInspector (third-modality)
# ─────────────────────────────────────────────

def VisionInspector(state: AgentState) -> dict[str, Any]:
    """
    Third-modality forensic investigator using Gemini's vision capability.
    Inspects image artifacts (diagrams, screenshots, architecture charts)
    referenced in the rubric under target_artifact: 'image'.
    Falls back gracefully if no image path is provided or file is missing.
    """
    instructions = get_rubric_instructions("image")
    if not instructions:
        print("VisionInspector: No 'image' dimensions in rubric — skipping.")
        return {"evidences": {}}

    evidences: dict[str, Evidence] = {}
    # Use a plain (non-structured-output) LLM for multimodal input,
    # then parse the response into Evidence manually via a second structured call
    vision_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)
    struct_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(Evidence)

    for instruction in instructions:
        image_path = instruction.get("target_image_path", "")
        goal = instruction.get("forensic_instruction", "Identify visual elements, structures, and anomalies.")

        if not image_path or not Path(image_path).exists():
            print(f"VisionInspector: Image not found at '{image_path}' — skipping this dimension.")
            continue

        try:
            # Encode image as base64 for Gemini multimodal
            with open(image_path, "rb") as img_file:
                image_data = base64.b64encode(img_file.read()).decode("utf-8")

            # Determine MIME type from extension
            ext = Path(image_path).suffix.lower()
            mime_map = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                        ".gif": "image/gif", ".webp": "image/webp"}
            mime_type = mime_map.get(ext, "image/png")

            # Step 1: Get raw factual description from Gemini Vision
            vision_message = HumanMessage(content=[
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:{mime_type};base64,{image_data}"},
                },
                {
                    "type": "text",
                    "text": (
                        f"You are a Forensic Visual Analyst. Observe this image with strict factual accuracy.\n\n"
                        f"GOAL: {goal}\n\n"
                        "Describe ONLY what you observe:\n"
                        "1. Visual elements present (shapes, labels, arrows, boxes)\n"
                        "2. Any identifiable structures (flowcharts, architecture diagrams, graphs)\n"
                        "3. Text visible in the image\n"
                        "4. Notable anomalies or gaps\n"
                        "Do NOT interpret or make judgments — facts only."
                    ),
                },
            ])
            raw_description = _invoke_with_retry(vision_llm, [vision_message], label="vision-raw")
            raw_text = raw_description.content if hasattr(raw_description, "content") else str(raw_description)

            # Step 2: Wrap raw description into a structured Evidence record
            struct_prompt = f"""Convert the following forensic visual observation into a structured Evidence record.

GOAL: {goal}
IMAGE SOURCE: {image_path}
RAW VISUAL OBSERVATION:
{raw_text}

Populate EVERY field:
- goal: restate what you were asked to observe
- found: key visual elements and structures observed
- location: image file path and any visible labels/sections
- rationale: why this visual evidence is forensically relevant
- content: the full raw observation text above
- source: {image_path}
- reliability_score: 0.0–1.0 (1.0 if image is clear and directly relevant)
- evidence_id: generate a unique UUID string
"""
            evidence = _invoke_with_retry(struct_llm, [HumanMessage(content=struct_prompt)], label="vision-struct")
            evidence = _ensure_id(evidence, "vision-ev")
            evidences[evidence.evidence_id] = evidence
            print(f"  ✓ Collected vision evidence: {evidence.evidence_id}")

        except Exception as e:
            print(f"VisionInspector failed for '{image_path}': {e}")

    return {"evidences": evidences}
