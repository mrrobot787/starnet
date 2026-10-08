# University Triage Agent

This agent reads the latest University "next steps" request and emits a prioritized analysis with actionable recommendations.

- Script: `scripts/agents_university_triage.py`
- Inputs: `.mm-out/agents/requests/university_next_steps_request.json` (optional)
- Outputs:
  - `.mm-out/agents/triage/university_next_steps_analysis.json`
  - `.mm-out/agents/evidence.jsonl` (kind: `university_next_steps_analyzed`)

How to run:
- Via VS Code task: "agents: University triage (analyze next steps)"
- Direct: `python scripts/agents_university_triage.py --originator Operator`

Notes:
- If no request exists, the agent writes a minimal analysis with `status=no_request`.
- Use the task "agents: University next steps request" first to generate the request.