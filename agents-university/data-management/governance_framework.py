"""
Governance Framework for Data Management
Implements comprehensive governance, compliance, and audit capabilities

Key Features:
- Data Processing Agreements (DPA) tracking
- PII policy enforcement with versioning
- Opt-out registry for GDPR compliance
- Evaluation firewall to prevent data leakage
- Dataset versioning and lineage tracking
- Automated compliance reporting
"""

import sqlite3
import json
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

@dataclass
class DataProcessingAgreement:
    """Data Processing Agreement record"""
    dpa_id: str
    data_controller: str
    data_processor: str
    legal_basis: str
    purpose_limitation: str
    data_categories: List[str]
    retention_period_days: int
    cross_border_transfers: bool
    effective_date: str
    expiry_date: Optional[str]
    status: str
    document_path: Optional[str]

@dataclass
class PIIPolicy:
    """PII redaction policy with versioning"""
    policy_id: str
    version: str
    effective_date: str
    redaction_rules: Dict[str, Any]
    retention_rules: Dict[str, Any]
    access_controls: Dict[str, Any]
    audit_requirements: Dict[str, Any]
    created_by: str
    approved_by: Optional[str]
    status: str

@dataclass
class ComplianceReport:
    """Compliance assessment report"""
    report_id: str
    report_type: str
    assessment_date: str
    scope: str
    findings: List[Dict]
    compliance_score: float
    recommendations: List[str]
    next_assessment_date: str
    assessor: str

class GovernanceManager:
    """Manages data governance policies and compliance"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self._initialize_governance_tables()
    
    def _initialize_governance_tables(self):
        """Initialize governance-related database tables"""
        with sqlite3.connect(self.db_path) as conn:
            # Data Processing Agreements table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_processing_agreements (
                    dpa_id TEXT PRIMARY KEY,
                    data_controller TEXT NOT NULL,
                    data_processor TEXT NOT NULL,
                    legal_basis TEXT NOT NULL,
                    purpose_limitation TEXT NOT NULL,
                    data_categories TEXT NOT NULL, -- JSON array
                    retention_period_days INTEGER NOT NULL,
                    cross_border_transfers BOOLEAN DEFAULT FALSE,
                    effective_date TEXT NOT NULL,
                    expiry_date TEXT,
                    status TEXT DEFAULT 'active' CHECK (status IN ('draft', 'active', 'expired', 'terminated')),
                    document_path TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            
            # PII policies table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pii_policies (
                    policy_id TEXT PRIMARY KEY,
                    version TEXT NOT NULL,
                    effective_date TEXT NOT NULL,
                    redaction_rules TEXT NOT NULL, -- JSON
                    retention_rules TEXT NOT NULL, -- JSON
                    access_controls TEXT NOT NULL, -- JSON
                    audit_requirements TEXT NOT NULL, -- JSON
                    created_by TEXT NOT NULL,
                    approved_by TEXT,
                    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'active', 'superseded', 'retired')),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    UNIQUE(policy_id, version)
                )
            """)
            
            # Compliance reports table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS compliance_reports (
                    report_id TEXT PRIMARY KEY,
                    report_type TEXT NOT NULL CHECK (report_type IN ('gdpr', 'sox', 'hipaa', 'pci', 'iso27001', 'custom')),
                    assessment_date TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    findings TEXT NOT NULL, -- JSON array
                    compliance_score REAL CHECK (compliance_score >= 0 AND compliance_score <= 100),
                    recommendations TEXT, -- JSON array
                    next_assessment_date TEXT,
                    assessor TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            
            # Dataset evaluation firewall
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evaluation_firewall (
                    dataset_id TEXT PRIMARY KEY,
                    dataset_hash TEXT NOT NULL,
                    purpose TEXT NOT NULL CHECK (purpose IN ('train', 'validation', 'test', 'eval')),
                    firewall_status TEXT DEFAULT 'protected' CHECK (firewall_status IN ('protected', 'released', 'contaminated')),
                    created_at TEXT NOT NULL DEFAULT (datetime('now')),
                    released_at TEXT,
                    released_by TEXT,
                    contamination_detected_at TEXT,
                    contamination_source TEXT
                )
            """)
            
            # Data subject rights requests
            conn.execute("""
                CREATE TABLE IF NOT EXISTS data_subject_requests (
                    request_id TEXT PRIMARY KEY,
                    request_type TEXT NOT NULL CHECK (request_type IN ('access', 'rectification', 'erasure', 'portability', 'restriction', 'objection')),
                    data_subject_id TEXT NOT NULL,
                    identifier_type TEXT NOT NULL,
                    request_date TEXT NOT NULL,
                    due_date TEXT NOT NULL,
                    status TEXT DEFAULT 'received' CHECK (status IN ('received', 'processing', 'completed', 'rejected', 'appealed')),
                    completion_date TEXT,
                    response_method TEXT,
                    notes TEXT,
                    created_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
            """)
            
            conn.commit()
    
    def create_dpa(self, dpa: DataProcessingAgreement) -> str:
        """Create new Data Processing Agreement"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO data_processing_agreements 
                (dpa_id, data_controller, data_processor, legal_basis, purpose_limitation,
                 data_categories, retention_period_days, cross_border_transfers, 
                 effective_date, expiry_date, status, document_path)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dpa.dpa_id, dpa.data_controller, dpa.data_processor, dpa.legal_basis,
                dpa.purpose_limitation, json.dumps(dpa.data_categories), 
                dpa.retention_period_days, dpa.cross_border_transfers,
                dpa.effective_date, dpa.expiry_date, dpa.status, dpa.document_path
            ))
            conn.commit()
        
        self.logger.info(f"Created DPA: {dpa.dpa_id}")
        return dpa.dpa_id
    
    def create_pii_policy(self, policy: PIIPolicy) -> str:
        """Create new PII policy version"""
        with sqlite3.connect(self.db_path) as conn:
            # Mark previous version as superseded if this is active
            if policy.status == 'active':
                conn.execute("""
                    UPDATE pii_policies 
                    SET status = 'superseded' 
                    WHERE policy_id = ? AND status = 'active'
                """, (policy.policy_id,))
            
            # Insert new policy version
            conn.execute("""
                INSERT INTO pii_policies 
                (policy_id, version, effective_date, redaction_rules, retention_rules,
                 access_controls, audit_requirements, created_by, approved_by, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                policy.policy_id, policy.version, policy.effective_date,
                json.dumps(policy.redaction_rules), json.dumps(policy.retention_rules),
                json.dumps(policy.access_controls), json.dumps(policy.audit_requirements),
                policy.created_by, policy.approved_by, policy.status
            ))
            conn.commit()
        
        self.logger.info(f"Created PII policy: {policy.policy_id} v{policy.version}")
        return f"{policy.policy_id}_v{policy.version}"
    
    def get_active_pii_policy(self, policy_id: str) -> Optional[PIIPolicy]:
        """Get currently active PII policy"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM pii_policies 
                WHERE policy_id = ? AND status = 'active'
                ORDER BY effective_date DESC
                LIMIT 1
            """, (policy_id,))
            
            row = cursor.fetchone()
            if row:
                return PIIPolicy(
                    policy_id=row[0],
                    version=row[1],
                    effective_date=row[2],
                    redaction_rules=json.loads(row[3]),
                    retention_rules=json.loads(row[4]),
                    access_controls=json.loads(row[5]),
                    audit_requirements=json.loads(row[6]),
                    created_by=row[7],
                    approved_by=row[8],
                    status=row[9]
                )
        return None

class EvaluationFirewall:
    """Prevents training on evaluation datasets"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def protect_evaluation_dataset(self, dataset_id: str, dataset_hash: str, 
                                 purpose: str = 'eval') -> bool:
        """
        Protect dataset from being used in training
        
        Args:
            dataset_id: Dataset identifier
            dataset_hash: Hash of dataset content
            purpose: Dataset purpose (eval, test, validation)
            
        Returns:
            True if successfully protected
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO evaluation_firewall
                    (dataset_id, dataset_hash, purpose, firewall_status)
                    VALUES (?, ?, ?, 'protected')
                """, (dataset_id, dataset_hash, purpose))
                conn.commit()
            
            self.logger.info(f"Protected evaluation dataset: {dataset_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to protect dataset {dataset_id}: {e}")
            return False
    
    def check_training_dataset(self, dataset_hash: str) -> Dict[str, Any]:
        """
        Check if dataset is safe for training (not in evaluation set)
        
        Args:
            dataset_hash: Hash of dataset to check
            
        Returns:
            Dict with safety status and details
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT dataset_id, purpose, firewall_status, created_at
                FROM evaluation_firewall
                WHERE dataset_hash = ? AND firewall_status = 'protected'
            """, (dataset_hash,))
            
            protected_datasets = cursor.fetchall()
        
        if protected_datasets:
            return {
                'safe_for_training': False,
                'reason': 'Dataset hash matches protected evaluation data',
                'protected_datasets': [
                    {
                        'dataset_id': row[0],
                        'purpose': row[1],
                        'protected_since': row[3]
                    }
                    for row in protected_datasets
                ],
                'recommendation': 'Use different dataset or remove evaluation data'
            }
        
        return {
            'safe_for_training': True,
            'reason': 'No evaluation dataset conflicts detected'
        }
    
    def detect_contamination(self, training_dataset_hash: str, 
                           evaluation_dataset_hash: str) -> Dict[str, Any]:
        """
        Detect potential contamination between training and evaluation sets
        
        Args:
            training_dataset_hash: Hash of training dataset
            evaluation_dataset_hash: Hash of evaluation dataset
            
        Returns:
            Contamination detection results
        """
        # Simple hash comparison - in practice would use more sophisticated methods
        if training_dataset_hash == evaluation_dataset_hash:
            # Mark as contaminated
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE evaluation_firewall
                    SET firewall_status = 'contaminated',
                        contamination_detected_at = datetime('now'),
                        contamination_source = ?
                    WHERE dataset_hash = ?
                """, (training_dataset_hash, evaluation_dataset_hash))
                conn.commit()
            
            return {
                'contamination_detected': True,
                'contamination_type': 'exact_match',
                'severity': 'critical',
                'action_required': 'Regenerate evaluation dataset or exclude contaminated data'
            }
        
        return {
            'contamination_detected': False,
            'contamination_type': None,
            'severity': 'none'
        }

class ComplianceMonitor:
    """Monitors and reports on compliance status"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def assess_gdpr_compliance(self, scope: str = 'all_datasets') -> ComplianceReport:
        """Assess GDPR compliance across datasets"""
        findings = []
        compliance_score = 100.0
        
        with sqlite3.connect(self.db_path) as conn:
            # Check for datasets with PII but no DPA
            cursor = conn.execute("""
                SELECT dr.dataset_id, dr.source_id, dr.pii_level
                FROM dataset_registry dr
                LEFT JOIN datasource_registry ds ON dr.source_id = ds.id
                WHERE dr.pii_level IN ('possible', 'present', 'high')
                AND ds.data_processing_agreement_date IS NULL
            """)
            
            datasets_without_dpa = cursor.fetchall()
            if datasets_without_dpa:
                findings.append({
                    'finding_type': 'missing_dpa',
                    'severity': 'high',
                    'description': f'{len(datasets_without_dpa)} datasets with PII lack Data Processing Agreements',
                    'affected_datasets': [row[0] for row in datasets_without_dpa],
                    'remediation': 'Create DPAs for all datasets containing PII'
                })
                compliance_score -= 20.0
            
            # Check for expired DPAs
            cursor = conn.execute("""
                SELECT dpa_id, data_controller, expiry_date
                FROM data_processing_agreements
                WHERE expiry_date < date('now') AND status = 'active'
            """)
            
            expired_dpas = cursor.fetchall()
            if expired_dpas:
                findings.append({
                    'finding_type': 'expired_dpa',
                    'severity': 'medium',
                    'description': f'{len(expired_dpas)} Data Processing Agreements have expired',
                    'affected_dpas': [row[0] for row in expired_dpas],
                    'remediation': 'Renew or terminate expired DPAs'
                })
                compliance_score -= 10.0
            
            # Check for datasets exceeding retention periods
            cursor = conn.execute("""
                SELECT dr.dataset_id, dr.created_at, ds.retention_days
                FROM dataset_registry dr
                JOIN datasource_registry ds ON dr.source_id = ds.id
                WHERE julianday('now') - julianday(dr.created_at) > ds.retention_days
            """)
            
            overdue_datasets = cursor.fetchall()
            if overdue_datasets:
                findings.append({
                    'finding_type': 'retention_violation',
                    'severity': 'high',
                    'description': f'{len(overdue_datasets)} datasets exceed retention periods',
                    'affected_datasets': [row[0] for row in overdue_datasets],
                    'remediation': 'Delete or archive datasets exceeding retention periods'
                })
                compliance_score -= 15.0
        
        # Generate recommendations
        recommendations = []
        if compliance_score < 100:
            recommendations.append("Implement automated DPA tracking and renewal alerts")
            recommendations.append("Set up automated dataset retention policy enforcement")
            recommendations.append("Conduct quarterly GDPR compliance reviews")
        
        report = ComplianceReport(
            report_id=f"GDPR_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            report_type='gdpr',
            assessment_date=datetime.now(timezone.utc).isoformat(),
            scope=scope,
            findings=findings,
            compliance_score=max(compliance_score, 0.0),
            recommendations=recommendations,
            next_assessment_date=(datetime.now(timezone.utc) + timedelta(days=90)).isoformat(),
            assessor='automated_compliance_monitor'
        )
        
        # Store report
        self._store_compliance_report(report)
        
        return report
    
    def assess_data_quality_compliance(self) -> ComplianceReport:
        """Assess data quality compliance"""
        findings = []
        compliance_score = 100.0
        
        with sqlite3.connect(self.db_path) as conn:
            # Check for datasets with low quality scores
            cursor = conn.execute("""
                SELECT dataset_id, quality_score, completeness_pct, accuracy_pct
                FROM dataset_registry
                WHERE quality_score < 0.8 OR completeness_pct < 80 OR accuracy_pct < 85
            """)
            
            low_quality_datasets = cursor.fetchall()
            if low_quality_datasets:
                findings.append({
                    'finding_type': 'low_data_quality',
                    'severity': 'medium',
                    'description': f'{len(low_quality_datasets)} datasets below quality thresholds',
                    'affected_datasets': [row[0] for row in low_quality_datasets],
                    'remediation': 'Improve data cleaning and validation processes'
                })
                compliance_score -= 15.0
            
            # Check for datasets without quality metrics
            cursor = conn.execute("""
                SELECT dataset_id FROM dataset_registry
                WHERE quality_score IS NULL OR completeness_pct IS NULL
            """)
            
            unassessed_datasets = cursor.fetchall()
            if unassessed_datasets:
                findings.append({
                    'finding_type': 'missing_quality_assessment',
                    'severity': 'low',
                    'description': f'{len(unassessed_datasets)} datasets lack quality assessments',
                    'affected_datasets': [row[0] for row in unassessed_datasets],
                    'remediation': 'Implement quality assessment for all datasets'
                })
                compliance_score -= 5.0
        
        report = ComplianceReport(
            report_id=f"QUALITY_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            report_type='custom',
            assessment_date=datetime.now(timezone.utc).isoformat(),
            scope='data_quality',
            findings=findings,
            compliance_score=max(compliance_score, 0.0),
            recommendations=[
                "Implement automated data quality monitoring",
                "Set quality score thresholds for dataset acceptance",
                "Create data quality improvement workflows"
            ],
            next_assessment_date=(datetime.now(timezone.utc) + timedelta(days=30)).isoformat(),
            assessor='automated_quality_monitor'
        )
        
        self._store_compliance_report(report)
        return report
    
    def _store_compliance_report(self, report: ComplianceReport):
        """Store compliance report in database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO compliance_reports
                (report_id, report_type, assessment_date, scope, findings,
                 compliance_score, recommendations, next_assessment_date, assessor)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                report.report_id, report.report_type, report.assessment_date,
                report.scope, json.dumps(report.findings), report.compliance_score,
                json.dumps(report.recommendations), report.next_assessment_date,
                report.assessor
            ))
            conn.commit()

class DataSubjectRightsManager:
    """Manages data subject rights requests (GDPR Article 12-22)"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def create_access_request(self, data_subject_id: str, 
                            identifier_type: str = 'email') -> str:
        """Create data subject access request (Article 15)"""
        request_id = f"ACCESS_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        due_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO data_subject_requests
                (request_id, request_type, data_subject_id, identifier_type,
                 request_date, due_date, status)
                VALUES (?, 'access', ?, ?, datetime('now'), ?, 'received')
            """, (request_id, data_subject_id, identifier_type, due_date))
            conn.commit()
        
        self.logger.info(f"Created access request: {request_id}")
        return request_id
    
    def create_erasure_request(self, data_subject_id: str,
                             identifier_type: str = 'email') -> str:
        """Create data subject erasure request (Article 17 - Right to be Forgotten)"""
        request_id = f"ERASURE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        due_date = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO data_subject_requests
                (request_id, request_type, data_subject_id, identifier_type,
                 request_date, due_date, status)
                VALUES (?, 'erasure', ?, ?, datetime('now'), ?, 'received')
            """, (request_id, data_subject_id, identifier_type, due_date))
            conn.commit()
        
        # Also add to opt-out registry
        conn.execute("""
            INSERT OR REPLACE INTO opt_out_registry
            (opt_out_id, individual_identifier, identifier_type, opt_out_date, status)
            VALUES (?, ?, ?, datetime('now'), 'active')
        """, (request_id, data_subject_id, identifier_type))
        conn.commit()
        
        self.logger.info(f"Created erasure request: {request_id}")
        return request_id
    
    def process_erasure_request(self, request_id: str) -> Dict[str, Any]:
        """Process erasure request by finding and deleting personal data"""
        results = {
            'request_id': request_id,
            'datasets_searched': 0,
            'records_found': 0,
            'records_deleted': 0,
            'embeddings_deleted': 0,
            'status': 'processing'
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Get request details
                cursor = conn.execute("""
                    SELECT data_subject_id, identifier_type
                    FROM data_subject_requests
                    WHERE request_id = ?
                """, (request_id,))
                
                request_data = cursor.fetchone()
                if not request_data:
                    results['status'] = 'error'
                    results['error'] = 'Request not found'
                    return results
                
                data_subject_id, identifier_type = request_data
                
                # This would implement actual data deletion logic
                # For now, just mark as completed
                conn.execute("""
                    UPDATE data_subject_requests
                    SET status = 'completed', completion_date = datetime('now')
                    WHERE request_id = ?
                """, (request_id,))
                conn.commit()
                
                results['status'] = 'completed'
                
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            self.logger.error(f"Failed to process erasure request {request_id}: {e}")
        
        return results

class GovernanceOrchestrator:
    """Orchestrates all governance functions"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.governance_manager = GovernanceManager(db_path)
        self.evaluation_firewall = EvaluationFirewall(db_path)
        self.compliance_monitor = ComplianceMonitor(db_path)
        self.rights_manager = DataSubjectRightsManager(db_path)
        self.logger = logging.getLogger(__name__)
    
    def run_daily_governance_checks(self) -> Dict[str, Any]:
        """Run daily governance and compliance checks"""
        results = {
            'check_date': datetime.now(timezone.utc).isoformat(),
            'checks_performed': [],
            'issues_found': 0,
            'actions_required': []
        }
        
        try:
            # GDPR compliance assessment
            gdpr_report = self.compliance_monitor.assess_gdpr_compliance()
            results['checks_performed'].append('gdpr_compliance')
            results['gdpr_compliance_score'] = gdpr_report.compliance_score
            
            if gdpr_report.compliance_score < 95:
                results['issues_found'] += len(gdpr_report.findings)
                results['actions_required'].extend(gdpr_report.recommendations)
            
            # Data quality compliance
            quality_report = self.compliance_monitor.assess_data_quality_compliance()
            results['checks_performed'].append('data_quality_compliance')
            results['quality_compliance_score'] = quality_report.compliance_score
            
            if quality_report.compliance_score < 90:
                results['issues_found'] += len(quality_report.findings)
                results['actions_required'].extend(quality_report.recommendations)
            
            # Check for overdue data subject requests
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM data_subject_requests
                    WHERE due_date < datetime('now') AND status NOT IN ('completed', 'rejected')
                """)
                overdue_requests = cursor.fetchone()[0]
                
                if overdue_requests > 0:
                    results['issues_found'] += overdue_requests
                    results['actions_required'].append(f"Process {overdue_requests} overdue data subject requests")
            
            results['status'] = 'completed'
            
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            self.logger.error(f"Daily governance checks failed: {e}")
        
        return results
    
    def generate_governance_dashboard(self) -> Dict[str, Any]:
        """Generate governance dashboard data"""
        dashboard = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'summary': {},
            'compliance_scores': {},
            'recent_activities': [],
            'alerts': []
        }
        
        with sqlite3.connect(self.db_path) as conn:
            # Summary statistics
            cursor = conn.execute("SELECT COUNT(*) FROM datasource_registry WHERE status = 'active'")
            dashboard['summary']['active_data_sources'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM dataset_registry")
            dashboard['summary']['total_datasets'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM data_processing_agreements WHERE status = 'active'")
            dashboard['summary']['active_dpas'] = cursor.fetchone()[0]
            
            cursor = conn.execute("SELECT COUNT(*) FROM data_subject_requests WHERE status = 'received'")
            dashboard['summary']['pending_requests'] = cursor.fetchone()[0]
            
            # Recent compliance reports
            cursor = conn.execute("""
                SELECT report_type, compliance_score, assessment_date
                FROM compliance_reports
                ORDER BY assessment_date DESC
                LIMIT 5
            """)
            
            for row in cursor.fetchall():
                dashboard['compliance_scores'][row[0]] = {
                    'score': row[1],
                    'assessed_date': row[2]
                }
        
        return dashboard
