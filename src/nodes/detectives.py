import json
import uuid
import time
from typing import Any
from dotenv import load_dotenv
load_dotenv()  # Load .env before any OpenAI client is created

from langchain_core.messages import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI
import google.api_core.exceptions
from src.state import AgentState, Evidence
from src.tools.repo_tools import clone_repository, analyze_graph_structure, extract_git_history
from src.tools.doc_tools import ingest_pdf

# Helper to load and filter rubric instructions
def get_rubric_instructions(target_artifact: str, rubric_path: str = "rubric.json") -> list[dict]:
    """
    Loads the rubric and returns dimensions matching the target_artifact.
    """
    try:
        with open(rubric_path, "r", encoding="utf-8") as f:
            rubric = json.load(f)
            return [dim for dim in rubric.get("dimensions", []) if dim.get("target_artifact") == target_artifact]
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        print(f"Warning: {rubric_path} is not valid JSON.")
        return []

def RepoInvestigator(state: AgentState) -> dict[str, Any]:
    """
    Analyzes a GitHub repository based on rubric dimensions.
    Outputs factual Evidence to the state.
    """
    instructions = get_rubric_instructions("github_repo")
    if not instructions:
        return {"evidences": {}}
        
    # We expect a repo URL to be passed in some way. For this implementation, 
    # we assume the first instruction contains the repo URL to audit.
    # In a real system, the repo URL might come from the state or external config.
    target_repo_url = instructions[0].get("target_repo_url")
    if not target_repo_url:
        target_repo_url = "https://github.com/langchain-ai/langgraph.git" # Fallback for testing
        print(f"No target_repo_url found in rubric. Using fallback: {target_repo_url}")
        
    evidences = {}
    
    # Strictly factual data collection using LLM with structured output
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(Evidence)
    
    try:
        # Step 1: Clone the repository safely
        with clone_repository(target_repo_url) as repo_dir:
            
            # Step 2: Use AST Parser to analyze the structure
            structure = analyze_graph_structure(repo_dir)
            structure_str = json.dumps(structure, indent=2)[:2000] # Truncate for context window
            
            # Step 3: Extract Git History (limit commits to reduce token usage)
            history = extract_git_history(repo_dir, max_commits=10)
            history_str = json.dumps(history, indent=2)[:2000]
            
            # Step 4: Evaluate each matching rubric instruction
            for instruction in instructions:
                prompt_text = f"""
                You are a Forensic Code Investigator. Your mandate is strictly factual observation.
                Do NOT provide opinions, rulings, or final decisions.
                
                Forensic Instruction: {instruction.get('forensic_instruction')}
                
                Repository Source: {target_repo_url}
                
                AST Class/Function Structure:
                {structure_str}
                
                Recent Commit History:
                {history_str}
                
                Based *only* on the factual data above, generate a formal Evidence record reflecting your findings.
                The evidence_id MUST be uniquely generated.
                The reliability_score MUST be a float between 0.0 and 1.0 based on how clear the evidence is in the AST/History.
                """
                
                # Retry up to 3 times with exponential backoff on rate-limit errors
                for attempt in range(3):
                    try:
                        evidence = llm.invoke([HumanMessage(content=prompt_text)])
                        break
                    except Exception as retry_err:
                        if "RESOURCE_EXHAUSTED" in str(retry_err) and attempt < 2:
                            wait = 30 * (attempt + 1)
                            print(f"Rate limited. Retrying in {wait}s...")
                            time.sleep(wait)
                        else:
                            raise
                
                # Ensure a unique ID if the LLM failed to generate a random one
                if not evidence.evidence_id or evidence.evidence_id == "uuid":
                    evidence.evidence_id = f"repo-ev-{uuid.uuid4().hex[:8]}"
                    
                # Merge into the dict
                evidences[evidence.evidence_id] = evidence
                
    except Exception as e:
        print(f"RepoInvestigator failed: {str(e)}")
        
    # LangGraph updates the state dictated by the reducer (operator.ior for evidences)
    return {"evidences": evidences}

def DocAnalyst(state: AgentState) -> dict[str, Any]:
    """
    Ingests PDF documents using Docling and RAG-lite methodology.
    Outputs factual Evidence to the state.
    """
    instructions = get_rubric_instructions("pdf_report")
    if not instructions:
        return {"evidences": {}}
        
    # Assume the first instruction contains the path to the PDF to audit
    target_pdf_path = instructions[0].get("target_pdf_path")
    if not target_pdf_path:
        print("No target_pdf_path found in rubric for doc analyst.")
        return {"evidences": {}}
        
    evidences = {}
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0).with_structured_output(Evidence)
    
    try:
        # Step 1: Ingest and chunk the PDF
        document_chunks = ingest_pdf(target_pdf_path)
        
        # Step 2: Evaluate each matching rubric instruction against chunks
        for instruction in instructions:
            query = instruction.get('forensic_instruction', '')
            
            # RAG-Lite: We pass chunks to the LLM to pull facts.
            # In a full RAG system, we would embed and search. Here we use the first few chunks
            # or pass the relevant text if the document is small enough.
            context_text = "\\n---\\n".join(document_chunks[:3]) # Limit to first 3 chunks for brevity
            
            prompt_text = f"""
            You are a Document Analyst. Your mandate is strictly factual observation.
            Do NOT provide opinions, rulings, or final decisions.
            
            Forensic Instruction: {query}
            
            Document Source: {target_pdf_path}
            
            Extracted Document Text (Chunked):
            {context_text}
            
            Based *only* on the factual text provided, generate a formal Evidence record reflecting your findings.
            The evidence_id MUST be uniquely generated.
            The reliability_score MUST be a float between 0.0 and 1.0 based on how clear the evidence is in the text.
            """
            
            evidence = llm.invoke([HumanMessage(content=prompt_text)])
            
            # Ensure unique ID
            if not evidence.evidence_id or evidence.evidence_id == "uuid":
                evidence.evidence_id = f"doc-ev-{uuid.uuid4().hex[:8]}"
                
            # Merge into the dict
            evidences[evidence.evidence_id] = evidence
            
    except Exception as e:
        print(f"DocAnalyst failed: {str(e)}")

    # Returning exactly the partial state update (the 'evidences' dict)
    return {"evidences": evidences}
