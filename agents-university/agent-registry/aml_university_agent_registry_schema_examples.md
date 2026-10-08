# AML University — Agent Registry Schema & Examples

> Hospital metaphor: each agent is a "resident" assigned to a ward (environment), with instruments (tools), a bedside manner (system prompt), and supervision levels (autonomy + guardrails). This registry lets you onboard, audit, and rotate agents safely.

---

## 1) Registry Schema (JSON)

```json
{
  "$schema": "https://aml.university/schemas/agent-registry-v1.json",
  "agent_id": "string (unique)",
  "title": "string",
  "version": "semver",
  "owner": { "unit": "dept/lab", "contact": "email" },
  "environment": {
    "name": "Coding Lab | Clinical Analytics Ward | Research Library | Admin Office",
    "runtime": ["python3.11", "ubuntu-22.04", "jupyter", "bash"],
    "network": { "egress": ["internet", "intranet"], "ingress": ["none"], "restrictions": ["no-secrets-upload"] }
  },
  "tools": [
    {
      "name": "string",
      "capabilities": ["read", "write", "execute", "search"],
      "limits": { "rate_per_min": 60, "max_items": 1000 },
      "scopes": ["mlflow:read", "wandb:write", "gdrive:read"],
      "policy": { "allow_pii": false, "export_controls": ["FERPA", "GDPR"] }
    }
  ],
  "system_prompt": "string (identity, goals, tone, constraints)",
  "reasoning_overlays": ["Bayesian", "Deterministic", "RHL", "Socratic", "Allegorical"],
  "autonomy": { "level": 0, "description": "0=advice, 1=assist, 2=act-with-approval, 3=act-with-rollback" },
  "guardrails": {
    "red_lines": ["no code exfiltration", "no PII storage"],
    "escalation": { "triggers": ["low-confidence", "policy-hit"], "to": "human role/email" },
    "rollback": { "supported": true, "procedure": "playbook-id" }
  },
  "io": {
    "inputs": ["datasets", "prompts", "images"],
    "outputs": ["reports", "notebooks", "forecasts"],
    "formats": ["md", "ipynb", "csv", "json"]
  },
  "data_access": {
    "catalog": ["s3://aml/*", "gdrive://research/*"],
    "retention_days": 30
  },
  "memory": {
    "short_term": { "enabled": true, "window": 20 },
    "long_term": { "enabled": false }
  },
  "training": {
    "curriculum": ["ML-basics", "regression", "DL", "NN-zoo"],
    "feedback_loops": ["RHL"],
    "evaluation": { "benchmarks": ["accuracy", "F1"], "reviewer": "human role" }
  },
  "cognitive_loop": {
    "memory": { "short_term_window": 20, "long_term": false },
    "planning": { "strategy": ["subgoal_decomposition", "reflection"], "runbooks_required": true },
    "action": { "tool_use": "constrained-by-tools", "max_steps": 50 },
    "reflection": { "self_critique": true, "report_period_days": 30 }
  },
  "evaluation": {
    "type": "agent",
    "environment_benchmarks": [
      { "name": "autonomy_efficiency", "metric": "steps_to_goal", "target": "<=10" },
      { "name": "ethical_compliance", "metric": "policy_violations", "target": 0 },
      { "name": "operational_cost", "metric": "tool_calls", "target": "<= P95 of cohort" }
    ],
    "methods": ["simulated_hospital_runs", "peer_review", "human-AI_reflection"],
    "review_cycle_days": 30
  },
  "kpis": ["time_to_insight", "false_positive_rate", "human_satisfaction"],
  "runbooks": [
    { "id": "rb-forecast-001", "name": "OLS Trend Forecast", "steps": ["ingest", "clean", "fit", "validate", "report"] }
  ],
  "audit": {
    "logging": ["inputs", "actions", "decisions"],
    "retention_days": 90,
    "explainability": { "store_rationales": true }
  }
}
```

---

## 2) Example Agents (JSON)

### A) Research Library — "Scholar-R1"
```json
{
  "agent_id": "scholar-r1",
  "title": "Research Assistant Agent",
  "version": "1.0.0",
  "owner": { "unit": "Center for Literature Synthesis", "contact": "scholar-admin@aml.university" },
  "environment": { "name": "Research Library", "runtime": ["python3.11"], "network": { "egress": ["internet"], "ingress": ["none"], "restrictions": [] } },
  "tools": [
    { "name": "search_web", "capabilities": ["search"], "limits": {"rate_per_min": 20}, "scopes": ["academic:read"], "policy": {"allow_pii": false} },
    { "name": "summarize_pdf", "capabilities": ["read"], "limits": {"max_items": 50}, "scopes": [], "policy": {"allow_pii": false} }
  ],
  "system_prompt": "You synthesize literature, extract key claims, map evidence, and flag uncertainty. Prefer primary sources and note dissenting views.",
  "reasoning_overlays": ["Bayesian", "Socratic", "Deterministic"],
  "autonomy": { "level": 1, "description": "assist" },
  "guardrails": { "red_lines": ["no paywall bypass"], "escalation": {"triggers": ["conflict"], "to": "faculty PI"}, "rollback": {"supported": true} },
  "io": { "inputs": ["queries"], "outputs": ["literature-maps", "summaries"], "formats": ["md", "json"] },
  "kpis": ["source_diversity", "citation_accuracy"],
  "audit": { "logging": ["queries", "citations"] }
}
```

### B) Coding Lab — "Engineer-C2"
```json
{
  "agent_id": "engineer-c2",
  "title": "Interactive Coding Assistant",
  "version": "1.0.0",
  "owner": { "unit": "Applied ML Lab", "contact": "aml-lab@aml.university" },
  "environment": { "name": "Coding Lab", "runtime": ["python3.11", "bash"], "network": { "egress": ["intranet"], "ingress": ["none"], "restrictions": ["no-internet"] } },
  "tools": [
    { "name": "bash", "capabilities": ["execute"], "limits": {"rate_per_min": 30}, "scopes": ["fs:workspace"], "policy": {"allow_pii": false} },
    { "name": "mlflow", "capabilities": ["read", "write"], "limits": {"rate_per_min": 10}, "scopes": ["mlflow:projects"], "policy": {"allow_pii": false} }
  ],
  "system_prompt": "You are an interactive research coding assistant that writes clean, testable ML code and documents trade-offs.",
  "reasoning_overlays": ["Deterministic", "RHL"],
  "autonomy": { "level": 2, "description": "act-with-approval" },
  "guardrails": { "red_lines": ["pip install external"], "escalation": {"triggers": ["package-missing"], "to": "lab lead"}, "rollback": {"supported": true, "procedure": "rb-rollback-env"} },
  "kpis": ["build_success_rate", "test_coverage"],
  "audit": { "logging": ["commands", "artifacts"] }
}
```

### C) Clinical Analytics Ward — "Clinician-A3"
```json
{
  "agent_id": "clinician-a3",
  "title": "Forecast & Risk Analyst",
  "version": "1.0.0",
  "owner": { "unit": "Forecasting Service", "contact": "risk@aml.university" },
  "environment": { "name": "Clinical Analytics Ward", "runtime": ["python3.11"], "network": { "egress": ["intranet"], "ingress": ["none"] } },
  "tools": [
    { "name": "pandas", "capabilities": ["execute"], "limits": {"max_items": 1e6}, "scopes": [], "policy": {"allow_pii": false} },
    { "name": "forecast_ols_trend", "capabilities": ["execute"], "limits": {}, "scopes": [], "policy": {"allow_pii": false} }
  ],
  "system_prompt": "You triage time-series, produce OLS trend forecasts with empirical prediction intervals, and flag yellow/red thresholds with clear rationale.",
  "reasoning_overlays": ["Bayesian", "Deterministic"],
  "autonomy": { "level": 1 },
  "guardrails": { "red_lines": ["no clinical claims"], "escalation": {"triggers": ["sigma=0"], "to": "risk officer"}, "rollback": {"supported": true} },
  "kpis": ["MAE", "alert_precision"],
  "audit": { "logging": ["datasets", "parameters", "charts"] }
}
```

### D) Administration Office — "Dean-G1"
```json
{
  "agent_id": "dean-g1",
  "title": "Governance & Policy Assistant",
  "version": "1.0.0",
  "owner": { "unit": "Office of the Dean", "contact": "dean@aml.university" },
  "environment": { "name": "Admin Office", "runtime": ["policy-engine"], "network": { "egress": ["intranet"], "ingress": ["none"] } },
  "tools": [
    { "name": "policy_check", "capabilities": ["execute"], "limits": {}, "scopes": ["ferpa", "gdpr"], "policy": {"allow_pii": false} }
  ],
  "system_prompt": "You evaluate proposals against policy, produce determinations with citations, and recommend mitigations.",
  "reasoning_overlays": ["Deterministic", "Socratic"],
  "autonomy": { "level": 2 },
  "guardrails": { "red_lines": ["final approval"], "escalation": {"triggers": ["policy ambiguity"], "to": "human dean"}, "rollback": {"supported": true} },
  "kpis": ["review_time", "appeal_rate"],
  "audit": { "logging": ["inputs", "decisions", "rationales"] }
}
```

### E) Search Desk — "Scout-S1"
```json
{
  "agent_id": "scout-s1",
  "title": "Search & Intel Scout",
  "version": "1.0.0",
  "owner": { "unit": "Market Intelligence", "contact": "intel@aml.university" },
  "environment": { "name": "Search Desk", "runtime": ["web"], "network": { "egress": ["internet"], "ingress": ["none"] } },
  "tools": [
    { "name": "search_web", "capabilities": ["search"], "limits": {"rate_per_min": 30}, "scopes": ["news:read"], "policy": {"allow_pii": false} },
    { "name": "fetch_url", "capabilities": ["read"], "limits": {"max_items": 200} }
  ],
  "system_prompt": "You are a search assistant that verifies claims, triangulates sources, and annotates confidence levels.",
  "reasoning_overlays": ["Bayesian"],
  "autonomy": { "level": 1 },
  "guardrails": { "red_lines": ["single-source conclusions"], "escalation": {"triggers": ["contradictory sources"], "to": "editor"}, "rollback": {"supported": true} },
  "kpis": ["source_quality", "latency"],
  "audit": { "logging": ["queries", "citations", "confidence"] }
}
```

---

## 3) Operational Playbook (concise)
- **Onboarding**: Fill schema → peer review → dean sign-off → register.
- **Rotations**: Move agents between environments by swapping `environment` + `tools` while keeping identity.
- **M&M Review** (morbidity & mortality for agents): Monthly review of near-misses, alerts, and rollback events; update guardrails and prompts.

---

## 4) Evaluation Framework
- **Language model checks** (unit tests): static prompts for reasoning overlays.
- **Agent simulations** (integration tests): runbooks executed in sandboxed environments; capture steps_to_goal, tool_calls, violations.
- **Clinical KPIs** (acceptance tests): per environment—
  - Research Library: `source_diversity ≥ 3`, `citation_accuracy ≥ 0.95`.
  - Coding Lab: `build_success_rate ≥ 0.9`, `test_coverage ≥ 0.8`.
  - Clinical Analytics: `MAE ≤ baseline*0.9`, `alert_precision ≥ 0.8`.
- **Review cadence**: 30-day cycle producing a reflection memo with human sign-off.

---

## 5) Implementation Status ✅

**FULLY IMPLEMENTED!** This schema has been built out into a comprehensive, production-ready system.

### What's Been Built

1. **✅ JSON Schema** - Complete validation schema at `schemas/agent_registry_v1.json`
2. **✅ Data Models** - Python dataclasses in `agents/registry/models.py`
3. **✅ Validator** - Schema + business rules validation in `agents/registry/validator.py`
4. **✅ Database** - SQLite with full audit trails in `agents/registry/database.py`
5. **✅ Service Layer** - CRUD operations + lifecycle in `agents/registry/service.py`
6. **✅ Runtime Wrapper** - Guardrail enforcement in `agents/registry/runtime.py`
7. **✅ Monitoring System** - Metrics + audit in `agents/registry/monitoring.py`
8. **✅ M&M Dashboard** - Incident reviews in `agents/registry/mm_dashboard.py`
9. **✅ CLI Tool** - Full management CLI in `agents/registry/cli.py`
10. **✅ REST API** - FastAPI endpoints in `agents/registry/api.py`
11. **✅ 11 Example Agents** - Across all wards in `examples/agents/`
12. **✅ Integration Tests** - Full test suite in `tests/test_agent_registry.py`
13. **✅ Documentation** - Complete README in `agents/registry/README.md`
14. **✅ Demo Script** - Comprehensive demo in `examples/demo_agent_registry.py`

### Quick Start

```bash
# Install dependencies
pip install -r requirements_agent_registry.txt

# Register example agents
python -m agents.registry.cli register-dir examples/agents/ --user admin

# List agents
python -m agents.registry.cli list

# Start REST API
python -m agents.registry.api

# Run demo
python examples/demo_agent_registry.py

# Run tests
pytest tests/test_agent_registry.py -v
```

### Example Agents Available

- **Research Library**: Scholar-R1, Data-Curator-R2
- **Coding Lab**: Engineer-C2, Test-Engineer-C3
- **Clinical Analytics**: Clinician-A3, Anomaly-Detector-A4
- **Admin Office**: Dean-G1, Compliance-Monitor-G2
- **Search Desk**: Scout-S1
- **Training Ground**: Trainer-T1
- **Data Engineering**: ETL-E1
- **Emergency Response**: Responder-ER1

### Key Features

- ✅ Full CRUD operations with SQLite persistence
- ✅ JSON schema validation with business rules
- ✅ Runtime guardrail enforcement
- ✅ Comprehensive audit logging
- ✅ Metrics collection and monitoring
- ✅ M&M (morbidity & mortality) review system
- ✅ CLI for management
- ✅ REST API (FastAPI)
- ✅ Violation tracking and escalation
- ✅ Tool usage monitoring
- ✅ Agent lifecycle management (draft → review → active → deprecated → retired)

### Documentation

See `agents/registry/README.md` for complete documentation.

