# Agent University Data Management System

A comprehensive, end-to-end data management system for Agent University / ClosedLoopSecuritySystem that makes "all relevant data sources" concrete, legal, and model-ready.

## Overview

This system implements a complete data ingestion and management pipeline with:

- **4-axis scoring rubric** for data source prioritization
- **Bronze/Silver/Gold storage layers** for data lake architecture
- **PII redaction and security scanning** for compliance
- **Double Helix tagging integration** with SISSA overlays
- **Comprehensive governance framework** for GDPR/compliance
- **Evaluation firewall** to prevent data leakage

## Quick Start

### 1. Initialize the System

```bash
python main_orchestrator.py init --config config.json
```

### 2. Score Data Sources

```bash
python main_orchestrator.py score
```

### 3. Ingest Data

```bash
python main_orchestrator.py ingest --source-id sharepoint_engineering --data-file sample_data.json
```

### 4. Run Governance Checks

```bash
python main_orchestrator.py governance
```

### 5. Check System Status

```bash
python main_orchestrator.py status
```

## Architecture

### Data Source Registry

The system maintains a comprehensive registry of all data sources with:

- **Scoring**: 4-axis rubric (Value, Legality, Effort, Risk)
- **Metadata**: Legal basis, PII levels, retention policies
- **Configuration**: Refresh schedules, quality controls, processing rules
- **Integration**: Double Helix sections, SISSA overlays

### Storage Layers

**Bronze Layer (Raw)**
- Append-only, immutable storage
- Compressed Parquet with metadata
- Complete audit trail

**Silver Layer (Cleaned)**
- PII redacted and normalized
- Deduplicated and quality-filtered
- Structured for analysis

**Gold Layer (Model-Ready)**
- Task-specific datasets (RAG, training, evaluation)
- Feature engineering applied
- Vector embeddings generated

### Safety Gates

All content passes through non-negotiable safety gates:

1. **License Check**: Validates usage rights for model training
2. **Secrets Scanning**: Detects and quarantines sensitive data
3. **PII Redaction**: Masks/hashes personal information
4. **GDPR Compliance**: Maintains reversible mappings for deletion

### Double Helix Integration

Automatic tagging system that:
- Classifies content into sections (HW/SW/NET/SEC/GOV/MEM/GEN)
- Identifies strands (Issues vs Solutions)
- Assigns SISSA overlays for AI processing
- Creates bidirectional links between related content

### Governance Framework

Comprehensive compliance management:
- Data Processing Agreements (DPA) tracking
- PII policy versioning and enforcement
- Evaluation firewall to prevent data leakage
- Data subject rights management (GDPR Articles 12-22)
- Automated compliance reporting

## Data Sources

The system includes 8 pre-configured high-priority data sources:

1. **SharePoint Engineering** - Internal documentation and procedures
2. **Jira Incidents** - Resolved incident tickets for supervised learning
3. **GitHub Organization** - Code context and development knowledge
4. **SIEM Alerts** - Security intelligence for classification training
5. **OneNote Runbooks** - Operational procedures for RAG
6. **CMDB Assets** - Asset inventory for entity linking
7. **CI/CD Pipelines** - Build logs for failure prediction
8. **Knowledge Base Wiki** - General knowledge for RAG baseline

Each source is scored and prioritized using the 4-axis rubric.

## Configuration

### Data Source Configuration (YAML)

```yaml
id: example_source
name: "Example Data Source"
type: sharepoint
owner: DataTeam
system_of_record: true
scope: "Sites/Example/**/*"

legal:
  basis: legitimate_interests
  pii: possible
  license: "Internal use only"

governance:
  retention_days: 365
  redaction: "pii_v2"
  sensitivity: "Confidential"

sissa_overlay: SISSA_ACTION_PLANNER
double_helix_tags:
  section: GOV
  strand_default: S

scoring:
  value: 4
  legality: 5
  effort: 2
  risk: 2
```

### System Configuration (JSON)

```json
{
  "database_path": "agent_university.db",
  "data_lake_path": "data_lake",
  "datasources_dir": "datasources",
  "log_level": "INFO",
  "safety_gates_enabled": true,
  "double_helix_enabled": true,
  "governance_enabled": true
}
```

## API Usage

### Python API

```python
from main_orchestrator import AgentUniversityDataManager

# Initialize system
manager = AgentUniversityDataManager("config.json")

# Initialize database and directories
init_results = manager.initialize_system()

# Score data sources
scoring_results = manager.run_data_source_scoring()

# Ingest data
data_records = [{"content": "Sample content", "metadata": {}}]
ingestion_results = manager.ingest_data_source("source_id", data_records)

# Run governance checks
governance_results = manager.run_governance_checks()

# Get system status
status = manager.get_system_status()
```

### Individual Components

```python
# Data source scoring
from scoring_system import DataSourceRegistry
registry = DataSourceRegistry("database.db", "datasources/")
scores = registry.load_and_score_all_sources()

# Safety gates
from safety_gates import SafetyGateOrchestrator
safety = SafetyGateOrchestrator("database.db")
result = safety.process_content_through_gates(content, metadata)

# Double Helix integration
from double_helix_sissa_integration import DataIngestionOrchestrator
dh_sissa = DataIngestionOrchestrator("database.db")
result = dh_sissa.process_content_with_dh_sissa(content, metadata)

# Governance
from governance_framework import GovernanceOrchestrator
governance = GovernanceOrchestrator("database.db")
compliance_report = governance.compliance_monitor.assess_gdpr_compliance()
```

## Database Schema

The system uses SQLite with comprehensive schemas for:

- **datasource_registry**: Data source configurations and scores
- **dataset_registry**: Processed dataset tracking
- **doc_chunks**: Document chunks for RAG
- **pii_redaction_log**: PII redaction audit trail
- **data_lineage**: Dataset transformation lineage
- **opt_out_registry**: GDPR opt-out tracking
- **ingestion_audit**: Complete ingestion audit trail
- **data_processing_agreements**: DPA tracking
- **compliance_reports**: Automated compliance assessments
- **evaluation_firewall**: Prevents training on evaluation data

## Compliance Features

### GDPR Compliance

- **Article 6**: Legal basis tracking for all data processing
- **Article 13-14**: Transparent data collection with DPAs
- **Article 15**: Data subject access request handling
- **Article 17**: Right to be forgotten with reversible redaction
- **Article 25**: Privacy by design with built-in PII protection
- **Article 30**: Records of processing activities

### Security Controls

- **Encryption**: All data encrypted at rest and in transit
- **Access Control**: Role-based access to sensitive data
- **Audit Trail**: Complete audit log of all data operations
- **Secrets Detection**: Automatic detection and quarantine of secrets
- **Data Minimization**: Only collect and retain necessary data

## Monitoring and Alerting

The system provides comprehensive monitoring:

- **Data freshness**: Alerts when data sources become stale
- **Quality metrics**: Monitors data quality scores and completeness
- **Compliance status**: Tracks compliance scores and violations
- **Processing errors**: Alerts on ingestion or processing failures
- **Governance issues**: Notifications for overdue requests or expired DPAs

## Extensibility

The system is designed for easy extension:

- **New Data Sources**: Add YAML configurations in `datasources/`
- **Custom Processors**: Implement new transformation logic
- **Additional Safety Gates**: Add new security or compliance checks
- **Custom Scoring**: Modify the 4-axis scoring rubric
- **Integration Points**: Connect to external systems via APIs

## Dependencies

Core dependencies:
- `sqlite3` - Database operations
- `pandas` - Data processing
- `pyarrow` - Parquet file handling
- `pyyaml` - Configuration parsing
- `hashlib` - Content hashing
- `re` - Pattern matching
- `pathlib` - File system operations

Optional dependencies:
- `langdetect` - Language detection
- `simhash` - Near-duplicate detection
- `sentence-transformers` - Text embeddings
- `requests` - API integrations

## License

Internal use only - Agent University / ClosedLoopSecuritySystem

## Support

For questions or issues:
1. Check the logs in `agent_university_data_manager.log`
2. Run system status check: `python main_orchestrator.py status`
3. Review governance dashboard for compliance issues
4. Consult the data source priority report for optimization recommendations
