-- Data Source Registry Schema for Agent University / ClosedLoopSecuritySystem
-- Implements the 4-axis scoring rubric and complete data governance framework

-- Core registry table for all data sources
CREATE TABLE datasource_registry (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('sharepoint', 'github', 'jira', 'siem', 'onenote', 'teams', 'cmdb', 'cicd', 'logs', 'api', 'database', 'file')),
    owner TEXT NOT NULL,
    system_of_record BOOLEAN DEFAULT FALSE,
    scope TEXT NOT NULL,
    
    -- Legal and compliance
    legal_basis TEXT NOT NULL CHECK (legal_basis IN ('legitimate_interests', 'consent', 'contract', 'legal_obligation', 'vital_interests', 'public_task')),
    pii_level TEXT NOT NULL CHECK (pii_level IN ('none', 'possible', 'present', 'high')),
    data_processing_agreement_date TEXT,
    license TEXT NOT NULL,
    
    -- Governance
    retention_days INTEGER DEFAULT 365,
    redaction_policy TEXT DEFAULT 'pii_v2',
    sensitivity TEXT CHECK (sensitivity IN ('Public', 'Internal', 'Confidential', 'Restricted')),
    
    -- Double Helix integration
    sissa_overlay TEXT CHECK (sissa_overlay IN ('SISSA_ACTION_PLANNER', 'SISSA_DECISION_SUPPORT', 'SISSA_RISK_VALIDATOR', 'SISSA_VALIDATOR')),
    dh_section TEXT CHECK (dh_section IN ('HW', 'SW', 'NET', 'SEC', 'GOV', 'MEM', 'GEN')),
    dh_strand_default TEXT CHECK (dh_strand_default IN ('I', 'S')),
    
    -- Security
    auth_method TEXT NOT NULL,
    secret_name TEXT,
    
    -- Storage paths
    path_bronze TEXT NOT NULL,
    path_silver TEXT NOT NULL,
    path_gold TEXT NOT NULL,
    vector_store_path TEXT,
    
    -- Refresh configuration
    refresh_schedule TEXT DEFAULT 'PT6H', -- ISO 8601 duration
    refresh_mode TEXT DEFAULT 'incremental' CHECK (refresh_mode IN ('full', 'incremental', 'delta')),
    
    -- Quality controls
    min_doc_length INTEGER DEFAULT 400,
    dedup_method TEXT DEFAULT 'simhash_64@0.92',
    
    -- Scoring (0-5 scale)
    score_value INTEGER CHECK (score_value >= 0 AND score_value <= 5),
    score_legality INTEGER CHECK (score_legality >= 0 AND score_legality <= 5),
    score_effort INTEGER CHECK (score_effort >= 0 AND score_effort <= 5), -- inverse scored
    score_risk INTEGER CHECK (score_risk >= 0 AND score_risk <= 5), -- inverse scored
    priority_score REAL GENERATED ALWAYS AS (
        2.0 * score_value + 
        2.0 * score_legality + 
        CASE WHEN score_effort > 0 THEN 5.0 / score_effort ELSE 0 END +
        CASE WHEN score_risk > 0 THEN 5.0 / score_risk ELSE 0 END
    ) STORED,
    
    -- Metadata
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    last_ingestion TEXT,
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'inactive', 'deprecated', 'error')),
    notes TEXT
);

-- Dataset registry for tracking processed datasets
CREATE TABLE dataset_registry (
    dataset_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES datasource_registry(id),
    version TEXT NOT NULL,
    purpose TEXT NOT NULL CHECK (purpose IN ('rag', 'ft', 'eval', 'policy', 'synthetic')),
    license TEXT NOT NULL,
    pii_level TEXT NOT NULL CHECK (pii_level IN ('none', 'possible', 'present', 'high')),
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    dh_tag_id TEXT, -- Links to Double Helix tagging system
    sissa_overlay TEXT,
    path_bronze TEXT,
    path_silver TEXT,
    path_gold TEXT,
    record_count INTEGER DEFAULT 0,
    size_bytes INTEGER DEFAULT 0,
    checksum TEXT,
    lineage_hash TEXT, -- For reproducibility
    
    -- Quality metrics
    quality_score REAL,
    completeness_pct REAL,
    accuracy_pct REAL,
    
    -- Usage tracking
    last_accessed TEXT,
    access_count INTEGER DEFAULT 0,
    
    UNIQUE(source_id, version)
);

-- Document chunks for RAG and vector storage
CREATE TABLE doc_chunks (
    chunk_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES dataset_registry(dataset_id),
    source_doc_id TEXT NOT NULL,
    chunk_order INTEGER NOT NULL,
    token_count INTEGER,
    char_count INTEGER,
    dh_tag_id TEXT,
    embedding_key TEXT, -- External vector store reference
    metadata_json TEXT, -- JSON blob for flexible metadata
    content_hash TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    UNIQUE(dataset_id, source_doc_id, chunk_order)
);

-- PII redaction audit trail
CREATE TABLE pii_redaction_log (
    log_id TEXT PRIMARY KEY,
    dataset_id TEXT NOT NULL REFERENCES dataset_registry(dataset_id),
    doc_id TEXT NOT NULL,
    redaction_type TEXT NOT NULL CHECK (redaction_type IN ('name', 'email', 'phone', 'ip', 'ticket_id', 'ssn', 'custom')),
    original_hash TEXT NOT NULL, -- Hash of original text
    redacted_value TEXT NOT NULL, -- Masked/hashed replacement
    policy_version TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    reversible BOOLEAN DEFAULT FALSE -- For GDPR right to be forgotten
);

-- Data lineage tracking
CREATE TABLE data_lineage (
    lineage_id TEXT PRIMARY KEY,
    source_dataset_id TEXT NOT NULL REFERENCES dataset_registry(dataset_id),
    target_dataset_id TEXT NOT NULL REFERENCES dataset_registry(dataset_id),
    transformation_type TEXT NOT NULL CHECK (transformation_type IN ('clean', 'normalize', 'chunk', 'embed', 'label', 'augment')),
    transformation_config TEXT, -- JSON config used
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    
    UNIQUE(source_dataset_id, target_dataset_id, transformation_type)
);

-- Opt-out registry for GDPR compliance
CREATE TABLE opt_out_registry (
    opt_out_id TEXT PRIMARY KEY,
    individual_identifier TEXT NOT NULL, -- Email, employee ID, etc.
    identifier_type TEXT NOT NULL CHECK (identifier_type IN ('email', 'employee_id', 'name', 'phone')),
    opt_out_date TEXT NOT NULL DEFAULT (datetime('now')),
    scope TEXT DEFAULT 'all', -- Which datasets/purposes to exclude from
    status TEXT DEFAULT 'active' CHECK (status IN ('active', 'processed', 'expired')),
    notes TEXT
);

-- Ingestion audit log (integrates with ClosedLoop audit system)
CREATE TABLE ingestion_audit (
    audit_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES datasource_registry(id),
    ingestion_start TEXT NOT NULL,
    ingestion_end TEXT,
    records_processed INTEGER DEFAULT 0,
    records_success INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    bytes_processed INTEGER DEFAULT 0,
    dh_tags_assigned TEXT, -- JSON array of assigned tags
    sissa_events_generated INTEGER DEFAULT 0,
    status TEXT DEFAULT 'running' CHECK (status IN ('running', 'success', 'failed', 'partial')),
    error_message TEXT,
    actor TEXT NOT NULL, -- Who/what initiated the ingestion
    surface TEXT, -- Which system surface triggered it
    content_hash TEXT -- Hash of processed content for integrity
);

-- Indexes for performance
CREATE INDEX idx_datasource_priority ON datasource_registry(priority_score DESC);
CREATE INDEX idx_datasource_type ON datasource_registry(type);
CREATE INDEX idx_datasource_sissa ON datasource_registry(sissa_overlay);
CREATE INDEX idx_dataset_source ON dataset_registry(source_id);
CREATE INDEX idx_dataset_purpose ON dataset_registry(purpose);
CREATE INDEX idx_chunks_dataset ON doc_chunks(dataset_id);
CREATE INDEX idx_chunks_tag ON doc_chunks(dh_tag_id);
CREATE INDEX idx_audit_source ON ingestion_audit(source_id);
CREATE INDEX idx_audit_date ON ingestion_audit(ingestion_start);

-- Views for common queries
CREATE VIEW v_high_priority_sources AS
SELECT * FROM datasource_registry 
WHERE status = 'active' AND priority_score >= 10.0
ORDER BY priority_score DESC;

CREATE VIEW v_dataset_summary AS
SELECT 
    dr.source_id,
    ds.name as source_name,
    ds.type as source_type,
    COUNT(*) as dataset_count,
    SUM(dr.record_count) as total_records,
    SUM(dr.size_bytes) as total_size_bytes,
    MAX(dr.created_at) as latest_dataset
FROM dataset_registry dr
JOIN datasource_registry ds ON dr.source_id = ds.id
GROUP BY dr.source_id, ds.name, ds.type;

CREATE VIEW v_pii_compliance_status AS
SELECT 
    ds.id,
    ds.name,
    ds.pii_level,
    COUNT(prl.log_id) as redactions_applied,
    COUNT(DISTINCT prl.redaction_type) as redaction_types_used,
    MAX(prl.created_at) as last_redaction
FROM datasource_registry ds
LEFT JOIN dataset_registry dr ON ds.id = dr.source_id
LEFT JOIN pii_redaction_log prl ON dr.dataset_id = prl.dataset_id
GROUP BY ds.id, ds.name, ds.pii_level;
