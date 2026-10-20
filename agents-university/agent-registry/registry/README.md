  # AML University Agent Registry System

A comprehensive agent registry and governance system using a **hospital metaphor**: each AI agent is a "resident" assigned to a ward (environment), with instruments (tools), a bedside manner (system prompt), and supervision levels (autonomy + guardrails).

## 🏥 Core Concepts

- **Wards (Environments)**: Research Library, Coding Lab, Clinical Analytics Ward, Admin Office, Search Desk, Training Ground, Emergency Response Unit, Data Engineering Bay
- **Residents (Agents)**: AI agents with specific roles, capabilities, and autonomy levels
- **Instruments (Tools)**: Capabilities agents can use (read, write, execute, search)
- **Supervision (Autonomy)**: 0=advice, 1=assist, 2=act-with-approval, 3=act-with-rollback
- **Red Lines (Guardrails)**: Absolute prohibitions that trigger violations
- **M&M Reviews**: Monthly "morbidity & mortality" reviews for incidents and near-misses

## 📁 Structure

```
agents/registry/
├── __init__.py           # Package exports
├── models.py             # Data models (AgentRegistration, etc.)
├── validator.py          # JSON schema and business rule validation
├── database.py           # SQLite database layer
├── service.py            # High-level service with CRUD operations
├── runtime.py            # Runtime wrapper with guardrail enforcement
├── monitoring.py         # Monitoring and audit system
├── mm_dashboard.py       # M&M review dashboard
├── cli.py                # Command-line interface
├── api.py                # REST API (FastAPI)
└── README.md             # This file

schemas/
└── agent_registry_v1.json  # JSON Schema for validation

examples/agents/          # Example agent registrations
├── research_library/
│   ├── scholar_r1.json
│   └── data_curator_r2.json
├── coding_lab/
│   ├── engineer_c2.json
│   └── test_engineer_c3.json
├── clinical_analytics/
│   ├── clinician_a3.json
│   └── anomaly_detector_a4.json
├── admin_office/
│   ├── dean_g1.json
│   └── compliance_monitor_g2.json
├── search_desk/
│   └── scout_s1.json
├── training_ground/
│   └── trainer_t1.json
├── data_engineering/
│   └── etl_e1.json
└── emergency_response/
    └── responder_er1.json

tests/
└── test_agent_registry.py  # Integration tests
```

## 🚀 Quick Start

### 1. Register Example Agents

```bash
# Register a single agent
python -m agents.registry.cli register examples/agents/research_library/scholar_r1.json --user admin

# Register all agents from a directory
python -m agents.registry.cli register-dir examples/agents/ --user admin
```

### 2. List and Inspect Agents

```bash
# List all agents
python -m agents.registry.cli list

# Filter by environment
python -m agents.registry.cli list --environment "Coding Lab"

# Show details
python -m agents.registry.cli show scholar-r1
```

### 3. Validate Agents

```bash
# Validate a single file
python -m agents.registry.cli validate --file examples/agents/research_library/scholar_r1.json

# Validate all agents in a directory
python -m agents.registry.cli validate --dir examples/agents/
```

### 4. Monitor Health

```bash
# Get agent health metrics (last 30 days)
python -m agents.registry.cli health scholar-r1 --days 30

# Show ward roster
python -m agents.registry.cli roster "Research Library"

# Show high-risk agents
python -m agents.registry.cli high-risk
```

### 5. Manage Agent Lifecycle

```bash
# Approve agent (draft -> review -> active)
python -m agents.registry.cli approve scholar-r1 --user admin

# Update status directly
python -m agents.registry.cli update-status scholar-r1 active --user admin

# Deprecate agent
python -m agents.registry.cli deprecate scholar-r1 --user admin
```

## 🔌 REST API

Start the API server:

```bash
python -m agents.registry.api
# Or with custom host/port
python -c "from agents.registry.api import run_server; run_server(host='0.0.0.0', port=8080)"
```

API Documentation available at: `http://localhost:8000/docs`

### Key Endpoints

- `GET /agents` - List agents (with filters)
- `GET /agents/{agent_id}` - Get agent details
- `POST /agents` - Register new agent
- `PUT /agents/{agent_id}/status` - Update status
- `POST /agents/{agent_id}/approve` - Approve agent
- `GET /agents/{agent_id}/health` - Health metrics
- `GET /agents/{agent_id}/violations` - Violations
- `GET /agents/{agent_id}/audit` - Audit trail
- `GET /environments/{name}/roster` - Ward roster
- `GET /high-risk` - High-risk agents
- `GET /monitoring/dashboard` - Performance dashboard
- `GET /mm-review/candidates` - Agents needing review
- `GET /mm-review/{agent_id}` - M&M review report

## 🐍 Python API

```python
from agents.registry import AgentRegistryService, AgentRuntime

# Initialize service
service = AgentRegistryService("agent_registry.db")

# Register an agent
success, db_id, errors = service.register_from_file("agent.json", user="admin")

# Get agent
agent = service.get_agent("scholar-r1")

# List agents
agents = service.list_agents(status="active", environment="Research Library")

# Update status
service.update_status("scholar-r1", "active", user="admin")

# Get health
health = service.get_agent_health("scholar-r1", days=30)

# Use runtime with guardrails
runtime = AgentRuntime(agent)

@runtime.with_guardrails(action_name="process_data")
def my_function(data):
    return process(data)

result = my_function(data)
```

## 📊 Monitoring & Auditing

```python
from agents.registry import MonitoringSystem

monitor = MonitoringSystem()

# System health
health = monitor.get_system_health()

# Agent metrics
metrics = monitor.get_agent_metrics_summary("scholar-r1", days=30)

# Violations
violations = monitor.get_violation_summary(agent_id="scholar-r1", days=30)

# Tool usage
tool_stats = monitor.get_tool_usage_stats(agent_id="scholar-r1", days=30)

# Audit trail
audit = monitor.get_audit_trail(agent_id="scholar-r1", days=30)

# Performance dashboard
dashboard = monitor.get_performance_dashboard(days=7)

# Anomaly detection
anomalies = monitor.detect_anomalies("scholar-r1", days=30)

# Compliance report
compliance = monitor.generate_compliance_report(days=30)
```

## 🏥 M&M Reviews

```python
from agents.registry import MMReviewDashboard

mm = MMReviewDashboard()

# Get agents needing review
candidates = mm.get_review_candidates(days=30)

# Generate review report
report = mm.generate_review_report("scholar-r1", days=30)

# Print readable summary
mm.print_review_summary("scholar-r1", days=30)

# Monthly summary
summary = mm.get_monthly_summary(year=2025, month=10)

# Export review
mm.export_review("scholar-r1", "review_report.json", days=30)
```

## 🧪 Testing

```bash
# Run all tests
pytest tests/test_agent_registry.py -v

# Run specific test
pytest tests/test_agent_registry.py::test_agent_model_creation -v

# With coverage
pytest tests/test_agent_registry.py --cov=agents.registry --cov-report=html
```

## 📝 Agent Registration Schema

Key fields:

- `agent_id`: Unique identifier (kebab-case)
- `title`: Human-readable name
- `version`: Semantic version (X.Y.Z)
- `owner`: Unit and contact
- `environment`: Ward assignment, runtime, network config
- `tools`: Available tools with capabilities and limits
- `system_prompt`: Agent identity and instructions
- `reasoning_overlays`: Reasoning strategies (Bayesian, Socratic, etc.)
- `autonomy`: Level 0-3 with description
- `guardrails`: Red lines, escalation, rollback config
- `audit`: Logging requirements
- `kpis`: Performance indicators

Full schema: `schemas/agent_registry_v1.json`

## 🛡️ Guardrails & Safety

The runtime wrapper enforces:

1. **Red Line Checks**: Block actions violating guardrails
2. **Tool Permissions**: Verify agent has capability before use
3. **Autonomy Levels**: Require approval for level 2+ actions
4. **Escalation Triggers**: Auto-escalate on configured conditions
5. **Audit Logging**: Log all actions, decisions, and metrics
6. **Rollback Support**: Enable safe experimentation

Example:

```python
runtime = AgentRuntime(agent)

# This will check guardrails before execution
result = runtime.execute_with_guardrails(
    my_function,
    arg1, arg2,
    action_name="process_sensitive_data",
    context={"contains_pii": True, "pii_authorized": True}
)

# Tool execution with permission check
result = runtime.execute_tool(
    "search_web",
    "search",
    search_function,
    query="AI safety"
)
```

## 🔍 Validation Rules

1. `agent_id` must be kebab-case
2. `version` must be semantic version (X.Y.Z)
3. Autonomy level ≥2 requires red lines
4. PII-allowed tools must have export controls
5. Internet egress requires network restrictions
6. High autonomy + internet requires escalation config
7. Audit logging required for all agents
8. Rollback procedure required if rollback supported

## 🎯 Autonomy Levels

- **Level 0 (Advice)**: Can only provide recommendations
- **Level 1 (Assist)**: Can assist but not act independently
- **Level 2 (Act-with-Approval)**: Can act but requires approval
- **Level 3 (Act-with-Rollback)**: Can act independently with rollback

## 📚 Example Use Cases

### Research Library Ward

- Scholar-R1: Literature synthesis and citation mapping
- Data-Curator-R2: Dataset curation and FAIR metadata

### Coding Lab Ward

- Engineer-C2: Interactive coding assistant
- Test-Engineer-C3: Automated test generation

### Clinical Analytics Ward

- Clinician-A3: Time-series forecasting and risk analysis
- Anomaly-Detector-A4: Anomaly detection and alerting

### Admin Office Ward

- Dean-G1: Policy evaluation and compliance
- Compliance-Monitor-G2: Audit scanning and reporting

### Other Wards

- Scout-S1 (Search Desk): Web search and fact verification
- Trainer-T1 (Training Ground): ML training orchestration
- ETL-E1 (Data Engineering): Data pipeline engineering
- Responder-ER1 (Emergency Response): Incident response

## 🔧 Dependencies

```bash
pip install jsonschema  # Schema validation
pip install tabulate    # CLI table formatting
pip install fastapi     # REST API
pip install uvicorn     # ASGI server
pip install pytest      # Testing
```

## 📖 Further Reading

- See `aml_university_agent_registry_schema_examples.md` for detailed schema documentation
- Check `examples/agents/` for 11 complete agent examples
- Review `tests/test_agent_registry.py` for usage examples

## 🤝 Contributing

1. Add new agents to `examples/agents/{ward}/`
2. Ensure agents pass validation: `python -m agents.registry.cli validate --file your_agent.json`
3. Write tests for new features in `tests/`
4. Update this README with new functionality

## 📄 License

Part of the AML University Training Hospital project.
