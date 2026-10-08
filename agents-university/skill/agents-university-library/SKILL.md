---
name: Agents University Library
slug: agents-university-library
description: Find and read the Agents University / Agent Training Hospital knowledge base (hospital roles, data manager, agent registry, triage agent, docs) consolidated in mrrobot787/starnet.
category: Knowledge
version: 1.0.0
author: mrrobot787
license: MIT
---

Use this whenever the Commander asks about Agents University, AML University, the Agent Training Hospital, Agent Hospital roles (triage nurse, attending physician, pharmacist, Chief Medical Agent), the Agent University data manager, the agent registry, or the University triage agent. Look the answer up in the library instead of answering from memory, and cite the file paths you used.

The library lives in `agents-university/` of the public repo `mrrobot787/starnet`. Its index is `agents-university/catalog.json`: every file with its area, kind, title, summary, line count, and SHA-256.

## Areas

| Area | What is in it |
| --- | --- |
| `training-hospital` | Hospital roles, clinical ontology, DB schema, policy service, pipeline integration, demos |
| `data-management` | Agent University data manager: governance, scoring, safety gates, storage layers, data source configs |
| `agent-registry` | Agent registry package (models, API, CLI, checkpoints, monitoring), JSON schema, examples |
| `triage-agent` | University triage agent, tests, design doc, Streamlit dashboard |
| `launchers` | Launcher, test runner, shortcuts |
| `docs` | Rebranding summary, verifier architecture, replication reports, execution-ready pack |
| `deploy` | nginx site config |

## With the WORKBENCH (preferred)

Run the bundled finder `scripts/au.mjs` with Node (StarNet ships Node; no install needed). Run it from this skill's package folder, or pass the full path to the script. It uses a local checkout of `agents-university/` when one is found (current folder or any parent, `--root DIR`, or `AU_ROOT`), and otherwise reads the public repo over HTTPS, caching files by hash.

```bash
node scripts/au.mjs areas                                  # what exists, with sources
node scripts/au.mjs search triage nurse risk               # ranked files + matching lines
node scripts/au.mjs search registry checkpoint --area agent-registry --limit 5
node scripts/au.mjs search scoring rubric --quick          # titles/summaries only, fastest
node scripts/au.mjs show training-hospital/core/triage_nurse.py
node scripts/au.mjs show cma_orchestrator.py --lines 120:220
node scripts/au.mjs list --area docs
node scripts/au.mjs where                                  # which source and ref were used
```

Add `--json` to any command for structured output. `--ref <git ref>` pins a branch, tag, or commit (default tries `refs/heads/feat/harness-backend`, then `refs/heads/chore/import-agents-university`). `show` prints at most 400 lines at a time and tells you the next `--lines` range.

## With only WEB access

1. `web_fetch` the index: `https://raw.githubusercontent.com/mrrobot787/starnet/refs/heads/feat/harness-backend/agents-university/catalog.json`. If that returns 404, the import has not merged yet; use `refs/heads/chore/import-agents-university` in place of `refs/heads/feat/harness-backend`.
2. Pick files whose `title`, `summary`, or `path` match the question.
3. `web_fetch` each file at the same base URL plus its `path`, for example `.../agents-university/training-hospital/core/triage_nurse.py`.

## With only the CABINET (local files)

If the workspace contains a starnet checkout, `fs.read` `agents-university/catalog.json`, then `fs.read` the paths it lists (relative to `agents-university/`). Use `fs.search` for content matches.

## Working rules

- Search before reading: start with `areas` or `search`, then `show` only the files that matter.
- Quote file paths (and line numbers from `show`) in your answer so the Commander can verify.
- The library is a snapshot: code keeps the import paths of its original repos and is not wired to run from `agents-university/`. Describe it; do not claim it runs as-is.
- Databases, logs, and env files were deliberately left out. If a question needs data, say which schema or setup script would create it (for example `training-hospital/core/hospital_schema.sql`, `training-hospital/scripts/setup_hospital_db.py`).
- If `au.mjs` warns that a file differs from `catalog.json`, the local copy was edited or the catalog is stale; mention it.
