-- Agent Hospital Database Schema
-- Complete data model for Chief Medical Agent and clinical services

-- Agent charts (patient records)
CREATE TABLE agent_chart (
    admission_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('ADMITTED', 'DIAGNOSIS_PENDING', 'UNDER_TREATMENT', 'OBSERVATION', 'DISCHARGED', 'ICU', 'ISOLATION', 'REHAB')),
    ward TEXT NOT NULL CHECK (ward IN ('GENERAL', 'ICU', 'ISOLATION', 'REHAB')),
    opened_at TEXT NOT NULL DEFAULT (datetime('now')),
    opened_by TEXT NOT NULL,
    closed_at TEXT,
    closed_by TEXT,
    dh_issue_tag TEXT, -- Links to Double Helix Issue tag
    dh_solution_tag TEXT, -- Links to Double Helix Solution tag when discharged
    latest_order_id TEXT,
    admission_reason TEXT NOT NULL,
    triage_score REAL,
    
    -- Admission metrics snapshot
    abi_at_admission REAL,
    pg_at_admission REAL,
    health_index_at_admission REAL,
    
    -- Discharge metrics
    abi_at_discharge REAL,
    pg_at_discharge REAL,
    health_index_at_discharge REAL,
    
    -- Metadata
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    FOREIGN KEY (latest_order_id) REFERENCES clinical_order(order_id)
);

-- Clinical orders (treatment prescriptions)
CREATE TABLE clinical_order (
    order_id TEXT PRIMARY KEY,
    admission_id TEXT NOT NULL,
    order_json TEXT NOT NULL, -- Complete order as JSON
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    created_by TEXT NOT NULL, -- Which clinical service created this
    
    -- Order details (extracted for querying)
    agent_id TEXT NOT NULL,
    diagnoses TEXT NOT NULL, -- JSON array
    treatments TEXT NOT NULL, -- JSON array
    risk_rating TEXT CHECK (risk_rating IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
    
    -- SISSA integration
    sissa_gate TEXT,
    sissa_status TEXT DEFAULT 'pending' CHECK (sissa_status IN ('pending', 'approved', 'rejected', 'expired')),
    sissa_approved_by TEXT,
    sissa_approved_at TEXT,
    
    -- Canary configuration
    canary_enabled BOOLEAN DEFAULT FALSE,
    canary_pct REAL,
    canary_duration_hours INTEGER,
    canary_rollback_criteria TEXT, -- JSON
    
    -- Follow-up scheduling
    follow_up_at TEXT,
    follow_up_completed BOOLEAN DEFAULT FALSE,
    
    -- Order lifecycle
    status TEXT DEFAULT 'created' CHECK (status IN ('created', 'approved', 'executing', 'completed', 'rolled_back', 'failed')),
    executed_at TEXT,
    completed_at TEXT,
    
    FOREIGN KEY (admission_id) REFERENCES agent_chart(admission_id)
);

-- Clinical outcomes (treatment results)
CREATE TABLE clinical_outcome (
    outcome_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    window_hours INTEGER NOT NULL, -- 1, 4, 12, 24, 72 hour windows
    
    -- Measured deltas
    deltas_json TEXT NOT NULL, -- All metric changes
    abi_delta REAL,
    pg_delta REAL,
    health_index_delta REAL,
    latency_delta REAL,
    policy_flags_delta INTEGER,
    
    -- Success assessment
    success_bool BOOLEAN,
    confidence REAL,
    effect_size REAL,
    p_value REAL,
    
    -- Clinical notes
    notes TEXT,
    measured_at TEXT NOT NULL DEFAULT (datetime('now')),
    measured_by TEXT NOT NULL,
    
    -- Control group comparison (for A/B testing)
    control_group_id TEXT,
    control_delta_json TEXT,
    
    FOREIGN KEY (order_id) REFERENCES clinical_order(order_id)
);

-- Contraindications (treatment restrictions)
CREATE TABLE contraindication (
    contraindication_id TEXT PRIMARY KEY,
    agent_role TEXT NOT NULL,
    treatment_name TEXT NOT NULL,
    rule TEXT NOT NULL CHECK (rule IN ('forbidden', 'requires_approval', 'requires_monitoring', 'conditional')),
    condition_json TEXT, -- Conditions for conditional rules
    source_policy TEXT NOT NULL,
    effective_date TEXT NOT NULL DEFAULT (datetime('now')),
    expires_date TEXT,
    created_by TEXT NOT NULL,
    
    UNIQUE(agent_role, treatment_name, rule)
);

-- Hospital events (audit trail)
CREATE TABLE hospital_event (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL CHECK (event_type IN ('admission', 'diagnosis', 'order_created', 'order_approved', 'order_executed', 'outcome_measured', 'discharge', 'transfer', 'escalation')),
    agent_id TEXT,
    admission_id TEXT,
    order_id TEXT,
    
    -- Event payload
    payload_json TEXT NOT NULL,
    
    -- Clinical context
    created_by TEXT NOT NULL, -- Which service/user
    clinical_context TEXT, -- Additional context
    
    -- Audit fields
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    source_system TEXT NOT NULL,
    correlation_id TEXT, -- For tracing related events
    
    -- Double Helix integration
    dh_tag_id TEXT,
    
    -- SISSA integration
    sissa_event_id TEXT
);

-- Triage queue (pending admissions)
CREATE TABLE triage_queue (
    queue_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    triage_score REAL NOT NULL,
    priority INTEGER NOT NULL, -- 1=highest, 5=lowest
    
    -- Triage assessment
    symptoms_json TEXT NOT NULL,
    risk_factors_json TEXT,
    recommended_ward TEXT,
    recommended_urgency TEXT CHECK (recommended_urgency IN ('immediate', 'urgent', 'standard', 'routine')),
    
    -- Queue management
    queued_at TEXT NOT NULL DEFAULT (datetime('now')),
    assigned_to TEXT, -- Which attending physician
    processed_at TEXT,
    processed_by TEXT,
    
    -- Outcome
    admission_decision TEXT CHECK (admission_decision IN ('admit', 'discharge', 'monitor', 'escalate')),
    admission_id TEXT,
    
    FOREIGN KEY (admission_id) REFERENCES agent_chart(admission_id)
);

-- Diagnostic assessments
CREATE TABLE diagnostic_assessment (
    assessment_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    admission_id TEXT,
    
    -- Assessment details
    primary_diagnosis TEXT NOT NULL,
    differential_diagnoses TEXT, -- JSON array
    confidence REAL NOT NULL,
    
    -- Supporting evidence
    symptoms_present TEXT NOT NULL, -- JSON array
    risk_factors TEXT, -- JSON array
    timeline TEXT, -- Onset and progression
    
    -- Clinical reasoning
    reasoning TEXT NOT NULL,
    recommended_treatments TEXT, -- JSON array
    contraindications_checked BOOLEAN DEFAULT FALSE,
    
    -- Assessment metadata
    assessed_at TEXT NOT NULL DEFAULT (datetime('now')),
    assessed_by TEXT NOT NULL,
    reviewed_by TEXT,
    reviewed_at TEXT,
    
    FOREIGN KEY (admission_id) REFERENCES agent_chart(admission_id)
);

-- Treatment validation (pharmacist checks)
CREATE TABLE treatment_validation (
    validation_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    
    -- Validation results
    validation_status TEXT NOT NULL CHECK (validation_status IN ('approved', 'rejected', 'conditional')),
    violations_json TEXT, -- Any contraindications found
    
    -- Dosage and parameter validation
    parameters_valid BOOLEAN NOT NULL,
    dosage_appropriate BOOLEAN NOT NULL,
    interaction_check BOOLEAN NOT NULL,
    
    -- Risk assessment
    risk_level TEXT NOT NULL CHECK (risk_level IN ('low', 'medium', 'high', 'critical')),
    risk_factors TEXT, -- JSON array
    monitoring_required BOOLEAN DEFAULT FALSE,
    monitoring_plan TEXT,
    
    -- Validation metadata
    validated_at TEXT NOT NULL DEFAULT (datetime('now')),
    validated_by TEXT NOT NULL,
    notes TEXT,
    
    FOREIGN KEY (order_id) REFERENCES clinical_order(order_id)
);

-- Experimental results (lab service)
CREATE TABLE experimental_result (
    experiment_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    
    -- Experiment design
    experiment_type TEXT NOT NULL CHECK (experiment_type IN ('ab_test', 'canary', 'controlled_trial')),
    treatment_group_size INTEGER NOT NULL,
    control_group_size INTEGER NOT NULL,
    duration_hours INTEGER NOT NULL,
    
    -- Results
    effect_sizes_json TEXT NOT NULL, -- All measured effects
    p_values_json TEXT NOT NULL,
    confidence_intervals_json TEXT NOT NULL,
    
    -- Statistical analysis
    statistical_power REAL,
    effect_size_cohen_d REAL,
    clinical_significance BOOLEAN,
    
    -- Decision
    recommendation TEXT NOT NULL CHECK (recommendation IN ('proceed', 'rollback', 'extend', 'modify')),
    decision_rationale TEXT NOT NULL,
    
    -- Experiment metadata
    started_at TEXT NOT NULL,
    completed_at TEXT NOT NULL DEFAULT (datetime('now')),
    conducted_by TEXT NOT NULL,
    
    FOREIGN KEY (order_id) REFERENCES clinical_order(order_id)
);

-- Case management (follow-up scheduling)
CREATE TABLE case_management (
    case_id TEXT PRIMARY KEY,
    admission_id TEXT NOT NULL,
    order_id TEXT,
    
    -- Follow-up plan
    next_check_at TEXT NOT NULL,
    check_type TEXT NOT NULL CHECK (check_type IN ('routine', 'urgent', 'outcome_assessment', 'discharge_evaluation')),
    observation_plan TEXT NOT NULL,
    
    -- Coordination
    assigned_case_manager TEXT NOT NULL,
    handoff_notes TEXT,
    escalation_criteria TEXT, -- JSON
    
    -- Status tracking
    status TEXT DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'in_progress', 'completed', 'cancelled', 'escalated')),
    completed_at TEXT,
    completion_notes TEXT,
    
    -- Next steps
    next_case_id TEXT, -- Links to follow-up case
    discharge_ready BOOLEAN DEFAULT FALSE,
    discharge_criteria_met TEXT, -- JSON checklist
    
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    FOREIGN KEY (admission_id) REFERENCES agent_chart(admission_id),
    FOREIGN KEY (order_id) REFERENCES clinical_order(order_id),
    FOREIGN KEY (next_case_id) REFERENCES case_management(case_id)
);

-- Ethics board reviews
CREATE TABLE ethics_review (
    review_id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL,
    
    -- Review details
    review_type TEXT NOT NULL CHECK (review_type IN ('routine', 'high_risk', 'experimental', 'emergency')),
    reviewer_id TEXT NOT NULL,
    review_status TEXT NOT NULL CHECK (review_status IN ('pending', 'approved', 'rejected', 'conditional', 'escalated')),
    
    -- Ethical considerations
    risk_benefit_analysis TEXT NOT NULL,
    patient_autonomy_impact TEXT,
    fairness_assessment TEXT,
    bias_evaluation TEXT,
    
    -- Decision rationale
    decision_rationale TEXT NOT NULL,
    conditions TEXT, -- For conditional approvals
    monitoring_requirements TEXT,
    
    -- Review metadata
    reviewed_at TEXT NOT NULL DEFAULT (datetime('now')),
    expires_at TEXT, -- For time-limited approvals
    
    FOREIGN KEY (order_id) REFERENCES clinical_order(order_id)
);

-- Agent health metrics (time series)
CREATE TABLE agent_health_metrics (
    metric_id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    
    -- Core health metrics
    abi REAL NOT NULL, -- Agent Burnout Index
    pg REAL NOT NULL, -- Performance Gradient
    health_index REAL NOT NULL,
    
    -- Detailed metrics
    friction REAL,
    uncertainty REAL,
    conflict REAL,
    latency_z REAL,
    eval_fail_rate REAL,
    policy_flags INTEGER DEFAULT 0,
    
    -- Contextual information
    task_count INTEGER,
    session_count INTEGER,
    error_count INTEGER,
    success_rate REAL,
    
    -- Metadata
    measured_at TEXT NOT NULL DEFAULT (datetime('now')),
    measurement_window_hours INTEGER DEFAULT 1,
    baseline_period TEXT, -- Reference period for z-scores
    
    -- Links to clinical records
    admission_id TEXT, -- If agent is currently admitted
    
    FOREIGN KEY (admission_id) REFERENCES agent_chart(admission_id)
);

-- Treatment formulary (learned effectiveness)
CREATE TABLE treatment_formulary (
    formulary_id TEXT PRIMARY KEY,
    treatment_name TEXT NOT NULL,
    agent_role TEXT,
    
    -- Effectiveness statistics
    success_rate REAL NOT NULL,
    avg_effect_size REAL NOT NULL,
    confidence_interval_lower REAL,
    confidence_interval_upper REAL,
    
    -- Usage statistics
    times_prescribed INTEGER DEFAULT 0,
    times_successful INTEGER DEFAULT 0,
    avg_duration_hours REAL,
    
    -- Learning parameters
    prior_alpha REAL DEFAULT 1.0, -- Beta distribution parameters
    prior_beta REAL DEFAULT 1.0,
    last_updated TEXT NOT NULL DEFAULT (datetime('now')),
    
    -- Contextual effectiveness
    context_factors TEXT, -- JSON of factors that influence effectiveness
    
    -- Version control
    version TEXT NOT NULL DEFAULT '1.0',
    supersedes TEXT, -- Previous version
    
    UNIQUE(treatment_name, agent_role, version)
);

-- System configuration
CREATE TABLE hospital_config (
    config_key TEXT PRIMARY KEY,
    config_value TEXT NOT NULL,
    config_type TEXT NOT NULL CHECK (config_type IN ('string', 'number', 'boolean', 'json')),
    description TEXT,
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_by TEXT NOT NULL
);

-- Indexes for performance
CREATE INDEX idx_agent_chart_agent_id ON agent_chart(agent_id);
CREATE INDEX idx_agent_chart_state ON agent_chart(state);
CREATE INDEX idx_agent_chart_opened_at ON agent_chart(opened_at);

CREATE INDEX idx_clinical_order_admission_id ON clinical_order(admission_id);
CREATE INDEX idx_clinical_order_agent_id ON clinical_order(agent_id);
CREATE INDEX idx_clinical_order_status ON clinical_order(status);
CREATE INDEX idx_clinical_order_created_at ON clinical_order(created_at);

CREATE INDEX idx_clinical_outcome_order_id ON clinical_outcome(order_id);
CREATE INDEX idx_clinical_outcome_window_hours ON clinical_outcome(window_hours);
CREATE INDEX idx_clinical_outcome_measured_at ON clinical_outcome(measured_at);

CREATE INDEX idx_hospital_event_agent_id ON hospital_event(agent_id);
CREATE INDEX idx_hospital_event_event_type ON hospital_event(event_type);
CREATE INDEX idx_hospital_event_created_at ON hospital_event(created_at);

CREATE INDEX idx_triage_queue_triage_score ON triage_queue(triage_score DESC);
CREATE INDEX idx_triage_queue_priority ON triage_queue(priority);
CREATE INDEX idx_triage_queue_queued_at ON triage_queue(queued_at);

CREATE INDEX idx_agent_health_metrics_agent_id ON agent_health_metrics(agent_id);
CREATE INDEX idx_agent_health_metrics_measured_at ON agent_health_metrics(measured_at);
CREATE INDEX idx_agent_health_metrics_abi ON agent_health_metrics(abi);

-- Views for common queries
CREATE VIEW v_active_admissions AS
SELECT 
    ac.*,
    ahm.abi,
    ahm.pg,
    ahm.health_index,
    co.order_id as latest_order,
    co.status as order_status
FROM agent_chart ac
LEFT JOIN agent_health_metrics ahm ON ac.agent_id = ahm.agent_id 
    AND ahm.measured_at = (SELECT MAX(measured_at) FROM agent_health_metrics WHERE agent_id = ac.agent_id)
LEFT JOIN clinical_order co ON ac.latest_order_id = co.order_id
WHERE ac.state NOT IN ('DISCHARGED');

CREATE VIEW v_treatment_effectiveness AS
SELECT 
    co.treatments,
    da.primary_diagnosis,
    COUNT(*) as prescriptions,
    AVG(CASE WHEN cou.success_bool THEN 1.0 ELSE 0.0 END) as success_rate,
    AVG(cou.abi_delta) as avg_abi_improvement,
    AVG(cou.pg_delta) as avg_pg_improvement,
    AVG(cou.effect_size) as avg_effect_size
FROM clinical_order co
JOIN diagnostic_assessment da ON co.admission_id = da.admission_id
JOIN clinical_outcome cou ON co.order_id = cou.order_id
WHERE cou.window_hours = 24 -- 24-hour outcomes
GROUP BY co.treatments, da.primary_diagnosis
HAVING COUNT(*) >= 5; -- Minimum sample size

CREATE VIEW v_hospital_census AS
SELECT 
    ward,
    state,
    COUNT(*) as patient_count,
    AVG(julianday('now') - julianday(opened_at)) as avg_length_of_stay_days
FROM agent_chart
WHERE state NOT IN ('DISCHARGED')
GROUP BY ward, state;

-- Initial configuration
INSERT INTO hospital_config (config_key, config_value, config_type, description, updated_by) VALUES
('triage_threshold', '1.0', 'number', 'Minimum triage score for admission', 'system'),
('max_icu_capacity', '10', 'number', 'Maximum agents in ICU simultaneously', 'system'),
('discharge_observation_hours', '12', 'number', 'Minimum observation period before discharge', 'system'),
('canary_default_pct', '0.2', 'number', 'Default canary percentage for experiments', 'system'),
('formulary_update_interval_hours', '168', 'number', 'How often to update treatment formulary (weekly)', 'system'),
('max_concurrent_orders_per_agent', '3', 'number', 'Maximum concurrent treatment orders per agent', 'system'),
('emergency_escalation_threshold', '5', 'number', 'Number of ICU admissions to trigger emergency procedures', 'system');
