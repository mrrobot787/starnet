# Agents University / AML University Training Hospital

Consolidated snapshot of the Agents University, Agent Hospital, and AML University Training Hospital assets that were previously spread across several repositories and local folders. Files were copied as-is (no git history) and deduplicated; the originals are still in place.

Databases (`*.db`), logs, `.env` files, and `__pycache__` were intentionally excluded. Recreate databases from the `.sql` schemas and setup scripts.

## Layout

| Folder | Contents | Source |
| --- | --- | --- |
| `training-hospital/core` | Agent Hospital roles (triage nurse, attending physician, pharmacist, CMA orchestrator), ontology, schema | `ClosedLoopSystem_AML_Ops_PitCrew/AgentHospital` |
| `training-hospital/service` | Hospital policy service (FastAPI app, middleware, signed policy tickets) | `ClosedLoopSystem_AML_Ops_PitCrew/services/hospital` |
| `training-hospital/integration` | Feature pipeline to hospital integration | `ClosedLoopSystem_AML_Ops_PitCrew/agents/pipeline_hospital_integration.py` |
| `training-hospital/scripts` | Demo, DB setup, and smoke tests | `ClosedLoopSystem_AML_Ops_PitCrew` root and `ClosedLoop_SISSA_Workspace/04_Testing/Demo_Scripts` |
| `data-management` | Agent University data manager: orchestrator, governance, scoring, safety gates, storage layers, data source configs | `ClosedLoopSystem_AML_Ops_PitCrew/DataManagement` |
| `agent-registry` | AML University agent registry package, schema, examples | `ClosedLoopSystem_AML_Ops_PitCrew/agents/registry`, `schemas/`, `examples/` |
| `launchers` | AML University launcher, test runner, desktop shortcut, `university.ps1` | `ClosedLoopSystem_AML_Ops_PitCrew` root and `scripts/` |
| `triage-agent` | Agents University triage agent, tests, Streamlit dashboard | `mrrobot787/AML` |
| `docs` | Rebranding summary, verifier architecture, replication reports, execution-ready pack | `ClosedLoopSystem_AML_Ops_PitCrew`, local drafts |
| `deploy/nginx` | `aml-university-site.conf` | `ClosedLoopSystem_AML_Ops_PitCrew/nginx` |

Import paths inside the copied code still reflect the original repository layouts and have not been rewired.
