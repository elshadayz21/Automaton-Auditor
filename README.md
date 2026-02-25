# Automaton Auditor

A multi-agent forensic auditing system built with LangGraph and Google Gemini. This system systematically analyzes software repositories, documentation, and visual artifacts to collect factual evidence based on an extensible rubric.

## Features

- **Multi-modality Auditing**:
    - **RepoInvestigator**: Analyzes code structure (AST), git history, graph wiring, and tool safety.
    - **DocAnalyst**: Performs RAG-lite analysis on PDF documents.
    - **VisionInspector**: USes Gemini Vision to analyze architecture diagrams and screenshots.
- **Enriched Evidence Schema**: Every finding includes a goal, factual observation, location, rationale, and confidence score.
- **Resilient Orchestration**: Built with LangGraph, utilizing parallel fan-out/fan-in patterns and automatic state merging.
- **Robustness**: Includes exponential backoff retry logic to handle Gemini API rate limits.

## Getting Started

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (recommended for dependency management)

### Environment Setup

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd Automaton-Auditor
   ```

2. **Configure environment variables**:
   Create a `.env` file from the example:
   ```bash
   cp .env.example .env
   ```
   Edit `.env` and provide your `GOOGLE_API_KEY` (Gemini API key).

3. **Install dependencies**:
   Using `uv`:
   ```bash
   uv sync
   ```

## Running the Auditor

The system uses a `rubric.json` file to define what should be audited. You can configure target repository URLs, PDF paths, and image paths there.

### Run the Full Detective Graph

To execute the complete auditing workflow (dispatch -> parallel detectives -> aggregation):

```bash
uv run python test_graph.py
```

### Run Node-Specific Tests

To test the detective nodes in isolation:

```bash
uv run python test_detectives.py
```

## Project Structure

- `src/graph.py`: The compiled LangGraph `StateGraph` definition.
- `src/state.py`: Shared `AgentState` and `Evidence` Pydantic models.
- `src/nodes/detectives.py`: Implementation of all detective agents.
- `src/tools/`: Specialized tools for repo cloning, AST parsing, and document ingestion.
- `rubric.json`: The source of truth for audit dimensions and targets.

## Validation for Engineers

To validate the system after setup:
1. Ensure `.env` has a valid `GOOGLE_API_KEY`.
2. Run `uv run python test_graph.py`.
3. Check the output for "Aggregation complete" and ensure evidence items from `RepoInvestigator` are correctly merged.
4. Note: `DocAnalyst` and `VisionInspector` will skip if `sample.pdf` or `sample_diagram.png` are not present, which is expected for a clean setup.
