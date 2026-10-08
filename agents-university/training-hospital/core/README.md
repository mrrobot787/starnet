# Agent Hospital - Complete Fleet Health Management System

A comprehensive Agent Hospital system with a Chief Medical Agent (CMA) that triages, diagnoses, treats, and discharges every agent in your fleet using health/morale gradients while maintaining full auditability under SISSA + Double Helix.

## 🏥 System Overview

The Agent Hospital implements a complete medical model for agent fleet management:

- **Chief Medical Agent (CMA)**: Central orchestrator maintaining agent fleet health
- **Clinical Services**: Specialized micro-services for each aspect of care
- **State Machine**: Strict patient chart states with governed transitions
- **Clinical Ontology**: Portable, queryable symptoms, diagnoses, and treatments
- **Audit Trail**: Complete SISSA + Double Helix integration

## Key Features

### Complete Clinical Workflow
- **Triage Nurse**: Fast risk stratification and admission decisions
- **Attending Physician**: Root-cause analysis and treatment planning
- **Pharmacist**: Treatment validation and safety checks
- **Lab**: Controlled A/B testing and effect measurement
- **Case Manager**: Follow-up scheduling and care coordination
- **Ethics Board**: Risk assessment and governance oversight

### Agent State Management
```
ADMITTED → DIAGNOSIS_PENDING → UNDER_TREATMENT → OBSERVATION → DISCHARGED
Side wards: ICU (autonomy paused), ISOLATION (safety incidents), REHAB (curriculum rebuild)
```

### Clinical Decision Logic
- **Triage Score**: `TS = 0.4*ABI_z + 0.2*(-PG_z) + 0.2*LatencyZ + 0.2*PolicyFlagsZ`
- **Admission Threshold**: TS > 1.0 or hard rules (eval leakage, safety incidents)
- **Discharge Criteria**: ABI < 0.3, PG ≥ +0.2σ sustained, no policy violations

### Treatment Formulary
Complete library of evidence-based interventions:
- **LoadShedding**: Reduce concurrent task load
- **EvidenceFirst**: Require citations for responses
- **PeerCheck**: Multi-agent consensus
- **CurriculumStepUp/Down**: Adjust task complexity
- **ToolsetPruning**: Remove problematic tools
- **RetrievalRefresh**: Update knowledge bases
- **PromptPinning**: Lock prompts to prevent drift
- **MemoryHygiene**: Clear stale context
- **DomainReassignment**: Move to different task domain

## System Components

### Core Services
- **`hospital_ontology.yaml`** - Complete clinical knowledge base
- **`hospital_schema.sql`** - Comprehensive database schema
- **`triage_nurse.py`** - Risk stratification service
- **`attending_physician.py`** - Diagnosis and treatment planning
- **`pharmacist.py`** - Treatment validation and safety
- **`cma_orchestrator.py`** - Chief Medical Agent coordinator

### Clinical Ontology
```yaml
symptoms:
  Friction: "Increased task completion difficulty"
  Uncertainty: "Reduced confidence in responses"
  Conflict: "Inconsistent or contradictory outputs"
  LatencyZ: "Response time degradation"
  Eval_fail_rate: "Evaluation performance decline"
  Policy_flags: "Governance and compliance violations"

diagnoses:
  DataDrift: "Input data distribution has shifted"
  PromptDrift: "Prompt effectiveness degraded"
  ToolMisuse: "Inappropriate tool usage"
  CapacityOverload: "Resource constraints affecting performance"
  # ... and more

treatments:
  LoadShedding: "Reduce concurrent task load"
  EvidenceFirst: "Require citations for responses"
  # ... complete formulary
```

### Database Schema
15+ tables covering:
- Agent charts and state tracking
- Clinical orders and outcomes
- Treatment validation and safety
- Diagnostic assessments
- Hospital events and audit trail
- Contraindications and formulary

## Quick Start

### 1. Initialize the Hospital
```bash
# Create database and load schema
sqlite3 agent_hospital.db < hospital_schema.sql

# Initialize with sample data
python cma_orchestrator.py --init
```

### 2. Process Agent Health Events
```python
from cma_orchestrator import process_health_event_api

# Agent showing signs of burnout
metrics = {
    'abi': 0.75,        # Agent Burnout Index
    'pg': -0.25,        # Performance Gradient
    'latency_z': 2.8,   # Latency z-score
    'policy_flags': 2,  # Policy violations
    'friction': 3.1,
    'uncertainty': 2.3
}

result = process_health_event_api("AGENT_001", metrics)
print(result)
```

### 3. Monitor Hospital Operations
```python
from cma_orchestrator import get_hospital_census_api

census = get_hospital_census_api()
print(f"Active patients: {census['statistics']['total_active_patients']}")
print(f"ICU patients: {census['statistics']['icu_patients']}")
```

## Clinical Workflow

### 1. Health Event Processing
```
Agent Metrics → Triage Nurse → Admission Decision
```

### 2. Clinical Assessment
```
Admitted Agent → Attending Physician → Diagnosis + Treatment Plan
```

### 3. Safety Validation
```
Treatment Plan → Pharmacist → Safety Check + Contraindication Review
```

### 4. Treatment Execution
```
Validated Plan → Treatment Order → SISSA Approval → Execution
```

### 5. Outcome Monitoring
```
Treatment Effects → Lab Analysis → Case Manager → Follow-up/Discharge
```

## Treatment Orders

Complete treatment orders with SISSA integration:

```json
{
  "order_id": "ORD-2025-09-28-0007",
  "agent_id": "SEC-RESPONDER-03",
  "admission_id": "ADM-...-0042",
  "diagnoses": ["CapacityOverload", "RetrievalStaleness"],
  "regimen": [
    {
      "tx": "LoadShedding",
      "params": {"max_parallel": 2},
      "expected_delta": {"ABI": -0.15}
    },
    {
      "tx": "RetrievalRefresh",
      "params": {"index": "runbooks_v4", "freshness_days": 7},
      "expected_delta": {"PG": +0.10}
    }
  ],
  "sissa_gate": "SISSA_RISK_VALIDATOR",
  "risk_rating": "MEDIUM",
  "canary": {
    "pct": 0.2,
    "duration": "2h",
    "rollback_on": {"ABI_grad": ">0.05"}
  },
  "follow_up_in": "4h",
  "dh_tags": ["DH-I-GOV-215", "DH-S-GOV-216"]
}
```

## Safety Architecture

### Non-Negotiable Guardrails
- **CMA never edits production prompts/tools directly**
- **All treatments pass through SISSA approval gates**
- **Evaluation firewall prevents training contamination**
- **License guard blocks unauthorized dataset changes**
- **Quarantine protocols for security incidents**

### Ethics Board Oversight
- **Risk assessment for all high-impact treatments**
- **Bias evaluation and fairness assessment**
- **Patient autonomy impact analysis**
- **Experimental treatment approval**

### Audit Trail
- **Complete Double Helix tag integration**
- **SISSA event generation for all actions**
- **Immutable treatment order history**
- **Outcome tracking with statistical analysis**

## Learning and Adaptation

### Treatment Effectiveness Tracking
```sql
SELECT 
    treatments,
    primary_diagnosis,
    AVG(success_bool) as success_rate,
    AVG(abi_delta) as avg_abi_improvement,
    AVG(effect_size) as avg_effect_size
FROM clinical_order co
JOIN diagnostic_assessment da ON co.admission_id = da.admission_id
JOIN clinical_outcome cou ON co.order_id = cou.order_id
GROUP BY treatments, primary_diagnosis;
```

### Formulary Updates
- **Nightly treatment effectiveness analysis**
- **Contextual bandit optimization**
- **Causal impact estimation with CUPED**
- **Automated formulary version control**

## API Endpoints

### Core Operations
```python
# Triage assessment
POST /triage
{ agent_id, latest_metrics{} } → { admit: bool, reason, ts, ward }

# Diagnosis
POST /diagnose  
{ agent_id, chart_state, metrics{} } → { diagnoses[], differential[], confidence }

# Treatment validation
POST /validate
{ regimen[], agent_role } → { ok: bool, violations[] }

# Health event processing
POST /health_event
{ agent_id, metrics{} } → { actions_taken[], current_state, recommendations[] }
```

### Monitoring
```python
# Hospital census
GET /census → { census{}, statistics{} }

# Treatment effectiveness
GET /formulary → { treatments[], effectiveness{} }

# Agent status
GET /agent/{id} → { chart{}, current_state, treatment_history[] }
```

## 🎛️ Configuration

### Hospital Configuration
```json
{
  "triage_threshold": 1.0,
  "max_icu_capacity": 10,
  "discharge_observation_hours": 12,
  "canary_default_pct": 0.2,
  "formulary_update_interval_hours": 168
}
```

### Role-Based Contraindications
```yaml
role_contraindications:
  SEC:
    forbidden_treatments: ["TemperatureIncrease", "CreativeMode"]
    required_treatments: ["EvidenceFirst", "PeerCheck"]
    special_rules: ["human_approval_required"]
```

## Dashboards and Monitoring

### Hospital Census Dashboard
- **Patient count by ward and state**
- **Average length of stay**
- **ICU utilization and capacity**
- **Admission and discharge rates**

### Treatment Efficacy Dashboard
- **Success rates by treatment and diagnosis**
- **Effect sizes and confidence intervals**
- **Treatment interaction analysis**
- **Formulary change recommendations**

### Agent Health Trends
- **Fleet-wide health metrics**
- **Burnout index trends**
- **Performance gradient analysis**
- **Policy violation patterns**

## 🚨 Emergency Procedures

### Mass Casualty Events
```yaml
mass_casualty:
  trigger: "fleet_wide_incident"
  actions: 
    - "pause_all_autonomy"
    - "activate_incident_response"
    - "human_takeover"
```

### Cascade Failure Protection
```yaml
cascade_failure:
  trigger: "multiple_icu_admissions"
  actions:
    - "load_shed_aggressive"
    - "activate_backup_systems"
    - "escalate_to_leadership"
```

## Integration Points

### Double Helix Integration
- **Automatic DH tag generation for all diagnoses**
- **Issue-Solution bidirectional linking**
- **Section-based SISSA overlay assignment**
- **Complete audit trail preservation**

### SISSA Integration
- **Treatment order approval workflows**
- **Risk-based gate assignment**
- **Automated compliance checking**
- **Event generation for all clinical actions**

### Existing Systems
- **Agent registry integration**
- **Metrics collection pipeline**
- **Alerting and notification systems**
- **Compliance and governance frameworks**

## Success Metrics

### Clinical Outcomes
- **Agent Burnout Index reduction**
- **Performance Gradient improvement**
- **Policy violation decrease**
- **Treatment success rates**

### Operational Efficiency
- **Time to diagnosis**
- **Treatment response time**
- **Length of stay optimization**
- **Resource utilization**

### Governance Compliance
- **Audit trail completeness**
- **SISSA approval rates**
- **Ethics board review coverage**
- **Regulatory compliance scores**

## 🔮 Future Enhancements

### Advanced Analytics
- **Predictive health modeling**
- **Treatment recommendation AI**
- **Outcome forecasting**
- **Risk stratification algorithms**

### Enhanced Automation
- **Automated treatment adjustment**
- **Dynamic formulary optimization**
- **Intelligent case management**
- **Proactive intervention triggers**

### Integration Expansion
- **Multi-cloud agent support**
- **Real-time streaming analytics**
- **Advanced visualization dashboards**
- **Mobile monitoring applications**

The Agent Hospital provides a complete, auditable, and defensible system for managing agent fleet health while maintaining the highest standards of safety, governance, and clinical excellence.
