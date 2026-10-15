# AML University Agent Registry System 🏥

**Version:** 1.0.0  
**Status:** ✅ Production Ready  
**Last Updated:** October 7, 2025

> Hospital-grade governance for AI agents: Stochastic brains wrapped in deterministic bureaucracy (the good kind).

---

## 🎯 What Is This?

A **complete agent registry and governance system** using a hospital metaphor:
- **Wards** (Environments): Research Library, Coding Lab, Clinical Analytics, etc.
- **Residents** (Agents): AI agents with specific roles and capabilities
- **Instruments** (Tools): Capabilities agents can use
- **Supervision** (Autonomy): 4 levels from advice-only to act-with-rollback
- **Rounds** (M&M Reviews): Medical-style incident reviews for continuous improvement

---

## 🚀 Quick Start

```bash
# Install dependencies
pip install -r requirements_agent_registry.txt

# Validate everything works
python scripts/test_hygiene_check.py

# Register example agents
python -m agents.registry.cli register-dir examples/agents/ --user admin

# List agents
python -m agents.registry.cli list

# Start REST API
python -m agents.registry.api

# Run comprehensive demo
python examples/demo_agent_registry.py
```

---

## 📁 Project Structure

```
agents/registry/           # Core system (12 files, ~4,500 lines)
├── __init__.py           # Package exports
├── models.py             # Data models (20+ dataclasses)
├── validator.py          # Schema + business rule validation
├── database.py           # SQLite with 7 tables
├── service.py            # High-level API
├── runtime.py            # Guardrail enforcement wrapper
├── monitoring.py         # Metrics & audit
├── mm_dashboard.py       # M&M review system
├── cli.py                # Command-line tool
├── api.py                # REST API (FastAPI)
├── checkpoints.py        # Human-in-the-loop enforcement
├── observability.py      # KPI dashboard
├── safety_guards.py      # Reliability integrations
└── README.md             # Documentation

schemas/
└── agent_registry_v1.json  # JSON Schema

examples/agents/          # 12 example agents across 8 wards
├── research_library/     # Scholar-R1, Data-Curator-R2
├── coding_lab/           # Engineer-C2, Test-Engineer-C3
├── clinical_analytics/   # Clinician-A3, Anomaly-Detector-A4
├── admin_office/         # Dean-G1, Compliance-Monitor-G2
├── search_desk/          # Scout-S1
├── training_ground/      # Trainer-T1
├── data_engineering/     # ETL-E1
└── emergency_response/   # Responder-ER1

docs/                     # Operational documentation (3,173 lines)
├── OPERATOR_RUNBOOK.md          # Complete ops procedures
├── REVIEWER_HANDBOOK.md         # Complete review procedures
└── SAFETY_CULTURE_IMPLEMENTATION.md  # Integration guide

config/
└── alerts.yaml           # Alert rules and routing

tests/                    # Test suites
├── test_agent_registry.py       # Integration tests (15 tests)
└── test_reliability_ivy_4d.py   # Reliability tests (19 tests)

scripts/
├── approve_checkpoint.py        # Interactive approval tool
├── run_ivy_4d_review.py         # Reliability review runner
└── test_hygiene_check.py        # Quick validation script
```

---

## 🔑 Key Features

### Agent Management
- ✅ Full CRUD with validation
- ✅ Lifecycle: draft → review → active → parked → deprecated → retired
- ✅ Ward rotation (transfer between environments)
- ✅ Import/export

### Governance & Safety
- ✅ 4-level autonomy system
- ✅ Runtime guardrail enforcement
- ✅ Tool permission checking
- ✅ Escalation triggers
- ✅ Rollback procedures
- ✅ PII protection with auto-redaction

### Human Checkpoints (11 Types)
- ✅ Registration review (by autonomy level)
- ✅ Approval decisions
- ✅ Violation adjudication
- ✅ Deprecation approval
- ✅ Emergency shutdown documentation
- ✅ Weekly M&M reviews
- ✅ Monthly health reviews

### Safety Guards
- ✅ Timeout guard (auto-parks expired agents)
- ✅ PII detector (redacts emails, SSNs, etc.)
- ✅ Two-person rule (cryptographic enforcement)
- ✅ Circuit breaker (opens on failures)
- ✅ Standardized event schema

### Monitoring & Observability
- ✅ System health dashboard
- ✅ Checkpoint funnel tracking
- ✅ Policy health metrics
- ✅ SLO monitoring (≥98% target)
- ✅ Violation summaries
- ✅ Tool usage analytics
- ✅ MLflow/W&B export

---

## 📖 Usage

### CLI Commands

```bash
# Register agent
python -m agents.registry.cli register agent.json --user operator-1

# List agents (with filters)
python -m agents.registry.cli list --status active --environment "Coding Lab"

# Show details
python -m agents.registry.cli show scholar-r1

# Validate before registering
python -m agents.registry.cli validate --file agent.json

# Approve agent
python -m agents.registry.cli approve scholar-r1 --user reviewer-1

# Health check
python -m agents.registry.cli health scholar-r1 --days 30

# Ward roster
python -m agents.registry.cli roster "Research Library"

# High-risk agents
python -m agents.registry.cli high-risk

# Deprecate agent
python -m agents.registry.cli deprecate scholar-r1 --user operator-1
```

### Python API

```python
from agents.registry import (
    AgentRegistryService,
    AgentRuntime,
    HumanCheckpointSystem
)

# Service
service = AgentRegistryService()
agent = service.get_agent("scholar-r1")
health = service.get_agent_health("scholar-r1", days=30)

# Runtime with guardrails
runtime = AgentRuntime(agent)

@runtime.with_guardrails(action_name="process_data")
def my_function(data):
    return process(data)

# Human checkpoints
checkpoint_system = HumanCheckpointSystem()
pending = checkpoint_system.get_pending_checkpoints()
```

### REST API

```bash
# Start server
python -m agents.registry.api

# Use API
curl http://localhost:8000/agents
curl http://localhost:8000/agents/scholar-r1/health
curl http://localhost:8000/monitoring/dashboard
curl http://localhost:8000/mm-review/candidates
```

### Human Checkpoint Approval

```bash
# List pending checkpoints
python scripts/approve_checkpoint.py list

# Review and approve
python scripts/approve_checkpoint.py <checkpoint_id>
# Interactive workflow guides you through:
# 1. View checkpoint details
# 2. View agent details
# 3. Review checklist
# 4. Make decision (approve/reject/escalate)
# 5. Provide rationale
# 6. Confirm
```

---

## 🧪 Testing

```bash
# Quick hygiene check (7 tests)
python scripts/test_hygiene_check.py

# Integration tests (15 tests)
pytest tests/test_agent_registry.py -v

# Reliability tests (19 tests)
pytest tests/test_reliability_ivy_4d.py -v

# Full Ivy 4-D review
python scripts/run_ivy_4d_review.py

# Run demo
python examples/demo_agent_registry.py
```

---

## 📊 System Architecture

```
┌───────────────────────────────────────────────────────────┐
│                    User Interfaces                        │
├─────────────┬─────────────┬─────────────┬────────────────┤
│  CLI Tool   │  REST API   │  Python API │  Web UI        │
│  (15 cmds)  │  (25 endpts)│  (Service)  │  (Future)      │
└─────────────┴─────────────┴─────────────┴────────────────┘
                       │
┌──────────────────────┼────────────────────────────────────┐
│              Service Layer                                 │
│  ┌──────────┐  ┌───────────┐  ┌───────────────────────┐  │
│  │ Registry │  │Monitoring │  │ M&M Dashboard         │  │
│  │ Service  │  │ System    │  │                       │  │
│  └──────────┘  └───────────┘  └───────────────────────┘  │
└───────────────────────┼──────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────┐
│              Core Components                              │
│  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Models  │  │Validator │  │ Runtime  │  │ Database │  │
│  │         │  │          │  │ Wrapper  │  │          │  │
│  └─────────┘  └──────────┘  └──────────┘  └──────────┘  │
└───────────────────────┼──────────────────────────────────┘
                        │
┌───────────────────────┼──────────────────────────────────┐
│              Safety Layer                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │Checkpnts │  │Observblty│  │  Safety  │  │  Alerts  │  │
│  │          │  │          │  │  Guards  │  │          │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
└───────────────────────────────────────────────────────────┘
                        │
                   ┌────┴────┐
                   │ SQLite  │
                   └─────────┘
```

---

## 🎓 Example Use Cases

### Research Assistant (Scholar-R1)
```bash
# Register literature synthesis agent
python -m agents.registry.cli register examples/agents/research_library/scholar_r1.json --user admin

# Agent needs approval (Level 1 + internet)
# Reviewer receives alert
python scripts/approve_checkpoint.py <checkpoint_id>

# After approval, use in research
agent = service.get_agent("scholar-r1")
runtime = AgentRuntime(agent)
# Runtime enforces: no paywall bypass, no citation fabrication
```

### Coding Assistant (Engineer-C2)
```bash
# Register coding agent
python -m agents.registry.cli register examples/agents/coding_lab/engineer_c2.json --user admin

# Level 2 agent requires TWO approvers
# Senior Reviewer + Security Officer both approve

# Monitor performance
python -m agents.registry.cli health engineer-c2 --days 7
```

### Emergency Response (Responder-ER1)
```bash
# Level 3 agent - Executive approval required
# Dean + Security + Compliance all review

# Once active, can act independently
# But every action logged and reviewed weekly in M&M
```

---

## 📄 Documentation

- **[agents/registry/README.md](agents/registry/README.md)** - Complete technical docs
- **[docs/OPERATOR_RUNBOOK.md](docs/OPERATOR_RUNBOOK.md)** - Operations procedures
- **[docs/REVIEWER_HANDBOOK.md](docs/REVIEWER_HANDBOOK.md)** - Review procedures
- **[docs/SAFETY_CULTURE_IMPLEMENTATION.md](docs/SAFETY_CULTURE_IMPLEMENTATION.md)** - Integration guide
- **[IVY_4D_RELIABILITY_IMPLEMENTATION.md](IVY_4D_RELIABILITY_IMPLEMENTATION.md)** - Reliability framework
- **[HYGIENE_VALIDATION_COMPLETE.md](HYGIENE_VALIDATION_COMPLETE.md)** - Test results
- **[FINAL_DELIVERY_SUMMARY.md](FINAL_DELIVERY_SUMMARY.md)** - Complete summary

---

## 🤝 Contributing

1. Add new agents to `examples/agents/{ward}/`
2. Validate: `python -m agents.registry.cli validate --file your_agent.json`
3. Test: `pytest tests/`
4. Update docs

---

## 📄 License

Part of the AML University Training Hospital project.

---

## ✅ Certification

**System Validated:** October 7, 2025  
**Hygiene Check:** 7/7 PASSED  
**Acceptance Tests:** 3/3 PASSED  
**Production Ready:** ✅ YES

**Next Steps:**
1. Configure production alerts
2. Train operators (4h)
3. Certify reviewers (8h)
4. Deploy
5. Schedule first M&M meeting

---

**Questions?** ops@aml.university  
**Emergency:** ops-oncall@aml.university
