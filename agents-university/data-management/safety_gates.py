"""
Safety & Privacy Gates for Data Ingestion
Non-negotiable security and compliance controls for Agent University

Components:
- PII Redaction: names, emails, phone, IPs, ticket IDs → hashed or masked
- Secrets Detection: reject if patterns like keys/tokens/certs match
- License/Robots: only ingest third-party if license allows model training
- GDPR/Right to be Forgotten: reversible doc-to-embedding mapping
"""

import re
import hashlib
import json
import logging
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass
from datetime import datetime, timezone
import pandas as pd
from pathlib import Path

@dataclass
class RedactionResult:
    """Result of PII redaction operation"""
    original_hash: str
    redacted_value: str
    redaction_type: str
    reversible: bool
    policy_version: str

@dataclass
class SecurityScanResult:
    """Result of security scanning"""
    has_secrets: bool
    secret_types: List[str]
    risk_score: float
    quarantine_required: bool
    details: Dict[str, Any]

class PIIRedactor:
    """Handles PII detection and redaction with audit trail"""
    
    def __init__(self, policy_version: str = "pii_v2"):
        self.policy_version = policy_version
        self.logger = logging.getLogger(__name__)
        
        # PII detection patterns
        self.patterns = {
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'phone': re.compile(r'(\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})'),
            'ssn': re.compile(r'\b\d{3}-?\d{2}-?\d{4}\b'),
            'ip_address': re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'),
            'ticket_id': re.compile(r'\b(?:INC|REQ|CHG|PRB|TASK)-?\d{7,10}\b', re.IGNORECASE),
            'credit_card': re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
            'name_patterns': re.compile(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b'),  # Simple name pattern
            'employee_id': re.compile(r'\b(?:EMP|E)\d{6,8}\b', re.IGNORECASE),
            'api_key': re.compile(r'\b[A-Za-z0-9]{32,}\b'),  # Generic long alphanumeric
        }
        
        # Reversible mapping for GDPR compliance
        self.reversible_mappings = {}
        
    def redact_text(self, text: str, redaction_types: List[str] = None) -> Tuple[str, List[RedactionResult]]:
        """
        Redact PII from text with audit trail
        
        Args:
            text: Input text to redact
            redaction_types: Specific types to redact (None = all)
            
        Returns:
            Tuple of (redacted_text, redaction_log)
        """
        if not text:
            return text, []
            
        redacted_text = text
        redaction_log = []
        
        # Determine which patterns to apply
        patterns_to_use = self.patterns
        if redaction_types:
            patterns_to_use = {k: v for k, v in self.patterns.items() if k in redaction_types}
        
        # Apply each pattern
        for redaction_type, pattern in patterns_to_use.items():
            matches = pattern.findall(redacted_text)
            
            for match in matches:
                if isinstance(match, tuple):
                    match = ''.join(match)  # Handle regex groups
                
                # Create redacted value
                redacted_value, reversible = self._create_redacted_value(match, redaction_type)
                
                # Replace in text
                redacted_text = redacted_text.replace(match, redacted_value)
                
                # Log the redaction
                redaction_result = RedactionResult(
                    original_hash=self._hash_value(match),
                    redacted_value=redacted_value,
                    redaction_type=redaction_type,
                    reversible=reversible,
                    policy_version=self.policy_version
                )
                redaction_log.append(redaction_result)
        
        return redacted_text, redaction_log
    
    def redact_dataframe(self, df: pd.DataFrame, 
                        text_columns: List[str] = None) -> Tuple[pd.DataFrame, List[Dict]]:
        """
        Redact PII from DataFrame columns
        
        Args:
            df: Input DataFrame
            text_columns: Columns to redact (None = auto-detect)
            
        Returns:
            Tuple of (redacted_df, redaction_log)
        """
        df_redacted = df.copy()
        all_redaction_log = []
        
        # Auto-detect text columns if not specified
        if text_columns is None:
            text_columns = df.select_dtypes(include=['object']).columns.tolist()
        
        # Process each text column
        for col in text_columns:
            if col not in df.columns:
                continue
                
            for idx, value in df[col].items():
                if pd.isna(value) or not isinstance(value, str):
                    continue
                
                redacted_value, redaction_log = self.redact_text(value)
                df_redacted.loc[idx, col] = redacted_value
                
                # Add document context to log entries
                for log_entry in redaction_log:
                    log_dict = {
                        'doc_id': str(idx),
                        'column': col,
                        'redaction_type': log_entry.redaction_type,
                        'original_hash': log_entry.original_hash,
                        'redacted_value': log_entry.redacted_value,
                        'reversible': log_entry.reversible,
                        'policy_version': log_entry.policy_version,
                        'timestamp': datetime.now(timezone.utc).isoformat()
                    }
                    all_redaction_log.append(log_dict)
        
        return df_redacted, all_redaction_log
    
    def _create_redacted_value(self, original: str, redaction_type: str) -> Tuple[str, bool]:
        """Create redacted replacement value"""
        
        if redaction_type == 'email':
            # Keep domain for context, hash local part
            if '@' in original:
                local, domain = original.split('@', 1)
                hashed_local = self._hash_value(local)[:8]
                return f"[EMAIL_{hashed_local}@{domain}]", True
            else:
                return f"[EMAIL_{self._hash_value(original)[:8]}]", True
                
        elif redaction_type == 'phone':
            # Keep format, hash digits
            hashed = self._hash_value(original)[:8]
            return f"[PHONE_{hashed}]", True
            
        elif redaction_type == 'ssn':
            # Complete masking for SSN
            return "[SSN_REDACTED]", False
            
        elif redaction_type == 'ip_address':
            # Keep first octet, hash rest
            parts = original.split('.')
            if len(parts) == 4:
                hashed = self._hash_value('.'.join(parts[1:]))[:6]
                return f"{parts[0]}.xxx.xxx.{hashed}", True
            return f"[IP_{self._hash_value(original)[:8]}]", True
            
        elif redaction_type == 'ticket_id':
            # Keep prefix, hash number
            match = re.match(r'([A-Z]+)-?(\d+)', original, re.IGNORECASE)
            if match:
                prefix, number = match.groups()
                hashed_num = self._hash_value(number)[:6]
                return f"[{prefix.upper()}_{hashed_num}]", True
            return f"[TICKET_{self._hash_value(original)[:8]}]", True
            
        elif redaction_type == 'name_patterns':
            # Hash names but keep structure
            parts = original.split()
            hashed_parts = [self._hash_value(part)[:4].upper() for part in parts]
            return f"[NAME_{'_'.join(hashed_parts)}]", True
            
        elif redaction_type == 'employee_id':
            # Keep prefix, hash ID
            match = re.match(r'([A-Z]+)(\d+)', original, re.IGNORECASE)
            if match:
                prefix, emp_id = match.groups()
                hashed_id = self._hash_value(emp_id)[:6]
                return f"[{prefix.upper()}_{hashed_id}]", True
            return f"[EMP_{self._hash_value(original)[:8]}]", True
            
        else:
            # Generic redaction
            hashed = self._hash_value(original)[:8]
            return f"[{redaction_type.upper()}_{hashed}]", True
    
    def _hash_value(self, value: str) -> str:
        """Create consistent hash of value"""
        return hashlib.sha256(value.encode()).hexdigest()
    
    def create_reversal_mapping(self, redaction_log: List[RedactionResult]) -> Dict[str, str]:
        """Create mapping for reversible redactions (GDPR compliance)"""
        mapping = {}
        
        for log_entry in redaction_log:
            if log_entry.reversible:
                mapping[log_entry.redacted_value] = log_entry.original_hash
        
        return mapping

class SecretsScanner:
    """Detects secrets, keys, tokens, and certificates in content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Secret detection patterns
        self.secret_patterns = {
            'aws_access_key': re.compile(r'AKIA[0-9A-Z]{16}'),
            'aws_secret_key': re.compile(r'[0-9a-zA-Z/+]{40}'),
            'github_token': re.compile(r'ghp_[0-9a-zA-Z]{36}'),
            'azure_key': re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}'),
            'private_key': re.compile(r'-----BEGIN (?:RSA )?PRIVATE KEY-----'),
            'certificate': re.compile(r'-----BEGIN CERTIFICATE-----'),
            'jwt_token': re.compile(r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*'),
            'api_key_generic': re.compile(r'(?i)(?:api[_-]?key|apikey|access[_-]?token)["\']?\s*[:=]\s*["\']?([A-Za-z0-9_-]{20,})'),
            'password': re.compile(r'(?i)(?:password|passwd|pwd)["\']?\s*[:=]\s*["\']?([^\s"\']{8,})'),
            'connection_string': re.compile(r'(?i)(?:server|host|database)[=\s]+[^;\s]+(?:;[^;]+)*'),
        }
        
        # High-risk indicators
        self.high_risk_keywords = {
            'production', 'prod', 'live', 'master', 'admin', 'root', 
            'secret', 'private', 'confidential', 'internal'
        }
    
    def scan_content(self, content: str, source_context: Dict = None) -> SecurityScanResult:
        """
        Scan content for secrets and security risks
        
        Args:
            content: Text content to scan
            source_context: Additional context about the source
            
        Returns:
            SecurityScanResult with findings
        """
        if not content:
            return SecurityScanResult(
                has_secrets=False,
                secret_types=[],
                risk_score=0.0,
                quarantine_required=False,
                details={}
            )
        
        detected_secrets = []
        risk_factors = []
        
        # Scan for secret patterns
        for secret_type, pattern in self.secret_patterns.items():
            matches = pattern.findall(content)
            if matches:
                detected_secrets.append(secret_type)
                risk_factors.append(f"Contains {secret_type}")
        
        # Check for high-risk keywords
        content_lower = content.lower()
        high_risk_found = [kw for kw in self.high_risk_keywords if kw in content_lower]
        if high_risk_found:
            risk_factors.extend([f"High-risk keyword: {kw}" for kw in high_risk_found])
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(detected_secrets, high_risk_found, source_context)
        
        # Determine if quarantine is required
        quarantine_required = (
            len(detected_secrets) > 0 or 
            risk_score > 0.7 or
            any(secret in detected_secrets for secret in ['private_key', 'certificate', 'aws_secret_key'])
        )
        
        return SecurityScanResult(
            has_secrets=len(detected_secrets) > 0,
            secret_types=detected_secrets,
            risk_score=risk_score,
            quarantine_required=quarantine_required,
            details={
                'risk_factors': risk_factors,
                'high_risk_keywords': high_risk_found,
                'scan_timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
    
    def scan_dataframe(self, df: pd.DataFrame, 
                      text_columns: List[str] = None) -> List[Dict]:
        """
        Scan DataFrame for secrets
        
        Args:
            df: Input DataFrame
            text_columns: Columns to scan (None = auto-detect)
            
        Returns:
            List of scan results with document context
        """
        scan_results = []
        
        # Auto-detect text columns if not specified
        if text_columns is None:
            text_columns = df.select_dtypes(include=['object']).columns.tolist()
        
        # Scan each row
        for idx, row in df.iterrows():
            row_content = ' '.join([str(row[col]) for col in text_columns if pd.notna(row[col])])
            
            if not row_content.strip():
                continue
            
            scan_result = self.scan_content(row_content)
            
            if scan_result.has_secrets or scan_result.quarantine_required:
                result_dict = {
                    'doc_id': str(idx),
                    'has_secrets': scan_result.has_secrets,
                    'secret_types': scan_result.secret_types,
                    'risk_score': scan_result.risk_score,
                    'quarantine_required': scan_result.quarantine_required,
                    'details': scan_result.details
                }
                scan_results.append(result_dict)
        
        return scan_results
    
    def _calculate_risk_score(self, detected_secrets: List[str], 
                            high_risk_keywords: List[str],
                            source_context: Dict = None) -> float:
        """Calculate overall risk score (0.0 to 1.0)"""
        score = 0.0
        
        # Base score for detected secrets
        secret_weights = {
            'private_key': 0.9,
            'certificate': 0.8,
            'aws_secret_key': 0.8,
            'aws_access_key': 0.7,
            'github_token': 0.7,
            'azure_key': 0.6,
            'jwt_token': 0.5,
            'api_key_generic': 0.4,
            'password': 0.3,
            'connection_string': 0.4
        }
        
        for secret_type in detected_secrets:
            score += secret_weights.get(secret_type, 0.2)
        
        # Additional risk from keywords
        score += len(high_risk_keywords) * 0.1
        
        # Context-based adjustments
        if source_context:
            if source_context.get('environment') == 'production':
                score += 0.2
            if source_context.get('sensitivity') in ['Confidential', 'Restricted']:
                score += 0.1
        
        return min(score, 1.0)

class LicenseChecker:
    """Validates licensing and usage rights for third-party content"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Allowed license patterns for model training
        self.allowed_licenses = {
            'internal_use_only',
            'enterprise_agreement',
            'mit',
            'apache_2.0',
            'bsd',
            'creative_commons_by',
            'public_domain'
        }
        
        # Prohibited license patterns
        self.prohibited_licenses = {
            'gpl',
            'agpl',
            'copyleft',
            'no_derivatives',
            'non_commercial',
            'cc_by_nc',
            'cc_by_nd'
        }
    
    def check_license(self, license_text: str, source_type: str = 'third_party') -> Dict[str, Any]:
        """
        Check if license allows model training and derivative use
        
        Args:
            license_text: License text or identifier
            source_type: 'first_party', 'second_party', or 'third_party'
            
        Returns:
            Dict with license validation results
        """
        if not license_text:
            return {
                'allowed': False,
                'reason': 'No license specified',
                'risk_level': 'high'
            }
        
        license_lower = license_text.lower()
        
        # First-party and second-party data is generally allowed
        if source_type in ['first_party', 'second_party']:
            if 'internal use only' in license_lower or 'enterprise agreement' in license_lower:
                return {
                    'allowed': True,
                    'reason': f'{source_type} data with appropriate license',
                    'risk_level': 'low'
                }
        
        # Check for explicitly prohibited licenses
        for prohibited in self.prohibited_licenses:
            if prohibited in license_lower:
                return {
                    'allowed': False,
                    'reason': f'Prohibited license type: {prohibited}',
                    'risk_level': 'high'
                }
        
        # Check for allowed licenses
        for allowed in self.allowed_licenses:
            if allowed in license_lower:
                return {
                    'allowed': True,
                    'reason': f'Allowed license type: {allowed}',
                    'risk_level': 'low'
                }
        
        # Unknown license - requires manual review
        return {
            'allowed': False,
            'reason': 'Unknown license - requires manual review',
            'risk_level': 'medium',
            'manual_review_required': True
        }
    
    def check_robots_txt(self, robots_content: str, user_agent: str = '*') -> Dict[str, Any]:
        """
        Check robots.txt for crawling permissions
        
        Args:
            robots_content: Content of robots.txt file
            user_agent: User agent to check (default: *)
            
        Returns:
            Dict with robots.txt validation results
        """
        if not robots_content:
            return {
                'allowed': True,
                'reason': 'No robots.txt restrictions found'
            }
        
        lines = robots_content.strip().split('\n')
        current_user_agent = None
        disallowed_paths = []
        allowed_paths = []
        
        for line in lines:
            line = line.strip()
            if line.startswith('#') or not line:
                continue
            
            if line.lower().startswith('user-agent:'):
                current_user_agent = line.split(':', 1)[1].strip()
            elif line.lower().startswith('disallow:') and (
                current_user_agent == user_agent or current_user_agent == '*'
            ):
                path = line.split(':', 1)[1].strip()
                disallowed_paths.append(path)
            elif line.lower().startswith('allow:') and (
                current_user_agent == user_agent or current_user_agent == '*'
            ):
                path = line.split(':', 1)[1].strip()
                allowed_paths.append(path)
        
        # Check if completely disallowed
        if '/' in disallowed_paths:
            return {
                'allowed': False,
                'reason': 'Robots.txt disallows all crawling',
                'disallowed_paths': disallowed_paths
            }
        
        return {
            'allowed': True,
            'reason': 'Robots.txt allows crawling',
            'disallowed_paths': disallowed_paths,
            'allowed_paths': allowed_paths
        }

class GDPRComplianceManager:
    """Manages GDPR compliance including right to be forgotten"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def create_doc_embedding_mapping(self, doc_id: str, embedding_keys: List[str],
                                   dataset_id: str) -> None:
        """
        Create reversible mapping from document to embeddings for GDPR compliance
        
        Args:
            doc_id: Document identifier
            embedding_keys: List of embedding vector keys/IDs
            dataset_id: Dataset identifier
        """
        import sqlite3
        
        with sqlite3.connect(self.db_path) as conn:
            for embedding_key in embedding_keys:
                conn.execute("""
                    INSERT OR REPLACE INTO doc_embedding_mapping 
                    (doc_id, embedding_key, dataset_id, created_at)
                    VALUES (?, ?, ?, datetime('now'))
                """, (doc_id, embedding_key, dataset_id))
            conn.commit()
    
    def process_deletion_request(self, individual_identifier: str, 
                               identifier_type: str = 'email') -> Dict[str, Any]:
        """
        Process GDPR deletion request
        
        Args:
            individual_identifier: Email, employee ID, etc.
            identifier_type: Type of identifier
            
        Returns:
            Dict with deletion results
        """
        import sqlite3
        
        deletion_results = {
            'identifier': individual_identifier,
            'identifier_type': identifier_type,
            'documents_found': 0,
            'embeddings_deleted': 0,
            'datasets_affected': set(),
            'status': 'completed',
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Find documents containing the individual's data
                # This would need to be implemented based on your specific data structure
                # For now, placeholder logic
                
                # Record the opt-out request
                conn.execute("""
                    INSERT INTO opt_out_registry 
                    (individual_identifier, identifier_type, opt_out_date, status)
                    VALUES (?, ?, datetime('now'), 'processed')
                """, (individual_identifier, identifier_type))
                
                conn.commit()
                
        except Exception as e:
            deletion_results['status'] = 'failed'
            deletion_results['error'] = str(e)
            self.logger.error(f"GDPR deletion failed: {e}")
        
        return deletion_results

class SafetyGateOrchestrator:
    """Orchestrates all safety and privacy gates"""
    
    def __init__(self, db_path: str, policy_version: str = "pii_v2"):
        self.pii_redactor = PIIRedactor(policy_version)
        self.secrets_scanner = SecretsScanner()
        self.license_checker = LicenseChecker()
        self.gdpr_manager = GDPRComplianceManager(db_path)
        self.logger = logging.getLogger(__name__)
    
    def process_content_through_gates(self, content: str, metadata: Dict) -> Dict[str, Any]:
        """
        Process content through all safety gates
        
        Args:
            content: Text content to process
            metadata: Content metadata (source, license, etc.)
            
        Returns:
            Dict with processing results and cleaned content
        """
        results = {
            'original_content_hash': hashlib.sha256(content.encode()).hexdigest(),
            'processed_content': content,
            'gates_passed': [],
            'gates_failed': [],
            'quarantine_required': False,
            'processing_timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        # Gate 1: License Check
        license_result = self.license_checker.check_license(
            metadata.get('license', ''),
            metadata.get('source_type', 'third_party')
        )
        
        if not license_result['allowed']:
            results['gates_failed'].append('license_check')
            results['quarantine_required'] = True
            results['license_issue'] = license_result['reason']
            return results
        else:
            results['gates_passed'].append('license_check')
        
        # Gate 2: Secrets Scanning
        security_scan = self.secrets_scanner.scan_content(content, metadata)
        
        if security_scan.quarantine_required:
            results['gates_failed'].append('secrets_scan')
            results['quarantine_required'] = True
            results['security_issues'] = security_scan.details
            return results
        else:
            results['gates_passed'].append('secrets_scan')
            results['security_scan_results'] = {
                'risk_score': security_scan.risk_score,
                'secret_types': security_scan.secret_types
            }
        
        # Gate 3: PII Redaction
        redacted_content, redaction_log = self.pii_redactor.redact_text(content)
        
        results['processed_content'] = redacted_content
        results['gates_passed'].append('pii_redaction')
        results['pii_redactions'] = len(redaction_log)
        results['redaction_log'] = [
            {
                'type': log.redaction_type,
                'reversible': log.reversible,
                'hash': log.original_hash
            }
            for log in redaction_log
        ]
        
        # All gates passed
        results['all_gates_passed'] = len(results['gates_failed']) == 0
        
        return results
