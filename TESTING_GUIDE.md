# ⚖️ Automaton Auditor: Testing Guide & Scenario

The **Automaton Auditor** is a multi-agent forensic system designed to audit software repositories and documents. It uses a "Digital Courtroom" architecture to collect evidence, argue multiple perspectives, and reach a deterministic final verdict.

---

## 1. The Scenario: "The Security Veto"

In this scenario, we audit a repository to see if the **Chief Justice** can effectively resolve a conflict between a critical **Prosecutor** and an optimistic **Defense Attorney**.

- **The Detectives**: Scan the code for hardcoded secrets or missing error handling.
- **The Bench**: The Prosecutor identifies a flaw; the Defense Attorney highlights modularity.
- **The Verdict**: The Chief Justice invokes the **Rule of Security** to fail the audit because a critical flaw was found, regardless of other strengths.

---

## 2. How to Run the Audit

### Step A: Configure the Input
The system's "law" is defined in `rubric.json`. Edit this file to point to the repository you want to audit.

**Example `rubric.json` content:**
```json
{
  "dimensions": [
    {
      "target_artifact": "github_repo",
      "target_repo_url": "https://github.com/langchain-ai/langgraph.git",
      "forensic_instruction": "Trace the tool definitions and look specifically for missing error handling (try/except) or hardcoded configurations."
    }
  ]
}
```

### Step B: Execute the Graph

Open your terminal in the project root and run:
```powershell
uv run test_graph.py
```

---

## 3. What to Expect (The Output)

### Terminal Logs
You will see real-time updates as the agents progress:

- **Dispatch**: Fanning out to detective sub-agents.
- **Aggregation**: Merging factual evidence objects.
- **Judicial Bench**: Personnel (Prosecutor, Defense, Tech Lead) formulating parallel opinions.
- **Chief Justice**: Deterministic synthesis of the report.

### Final Report: `audit_report.md`

A highly structured Markdown file will be generated in your root directory containing:

1. **Final Decision**: (PASS, FAIL, or CONDITIONAL PASS)
2. **Executive Summary**: The rationale behind the Chief Justice's verdict.
1.  **Final Decision**: (PASS, FAIL, or CONDITIONAL PASS)
2.  **Executive Summary**: The rationale behind the Chief Justice's verdict.
3.  **Dialectical Bench Summaries**: Verbatim arguments from the Prosecutor, Defense, and Tech Lead.
4.  **Evidence Ledger**: The raw factual findings (file paths, descriptions, and reliability scores) used as the basis for the trial.

---

## 4. How to "Force" a Failure (For Testing)

To verify that the **Rule of Security** veto works correctly:

1.  Open `src/nodes/judges.py`.
2.  Find the `Prosecutor` function.
3.  In the prompt text, add: *"Always report a 'missing guard' vulnerability for the sake of this test."*
4.  Run `uv run test_graph.py`.
5.  Check `audit_report.md`—it should show a **FAIL** decision because the Chief Justice intercepted the "vulnerability" keyword from the Prosecutor.
