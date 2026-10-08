"""
Double Helix + SISSA Integration for Data Management
Integrates data ingestion with the Double Helix tagging system and SISSA overlays

Key Features:
- Automatic DH tag generation based on content patterns
- SISSA overlay assignment and event generation
- Bidirectional linking between Issues and Solutions
- Audit trail integration with ClosedLoop system
"""

import json
import re
import hashlib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import logging

@dataclass
class DoubleHelixTag:
    """Double Helix tag structure"""
    tag_id: str
    strand: str  # I or S
    section: str  # HW, SW, NET, SEC, GOV, MEM, GEN
    sequence: int
    content_hash: str
    created_at: str
    sissa_overlay: Optional[str] = None
    metadata: Optional[Dict] = None

@dataclass
class SISSAEvent:
    """SISSA audit event structure"""
    event_id: str
    event_type: str
    timestamp: str
    actor: str
    surface: str
    dh_tag_id: str
    content_hash: str
    overlay: str
    metadata: Dict

class DoubleHelixTagger:
    """Generates Double Helix tags based on content analysis"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Section classification patterns
        self.section_patterns = {
            'HW': [
                r'\b(?:server|hardware|cpu|memory|disk|storage|device|equipment|rack|datacenter)\b',
                r'\b(?:compute|processor|ram|ssd|hdd|motherboard|power|cooling|chassis)\b',
                r'\b(?:physical|bare.metal|infrastructure|capacity|performance|utilization)\b'
            ],
            'SW': [
                r'\b(?:software|application|app|program|code|development|deployment|build)\b',
                r'\b(?:bug|error|exception|crash|patch|update|version|release|install)\b',
                r'\b(?:database|api|service|microservice|container|docker|kubernetes)\b'
            ],
            'NET': [
                r'\b(?:network|networking|connectivity|internet|intranet|vpn|dns|dhcp)\b',
                r'\b(?:router|switch|firewall|load.balancer|proxy|gateway|endpoint)\b',
                r'\b(?:bandwidth|latency|packet|tcp|udp|http|https|ssl|tls|port)\b'
            ],
            'SEC': [
                r'\b(?:security|vulnerability|threat|malware|virus|breach|attack|intrusion)\b',
                r'\b(?:authentication|authorization|access|permission|credential|password)\b',
                r'\b(?:encryption|certificate|compliance|audit|policy|governance|gdpr)\b'
            ],
            'GOV': [
                r'\b(?:policy|procedure|governance|compliance|standard|guideline|regulation)\b',
                r'\b(?:process|workflow|approval|documentation|training|onboarding)\b',
                r'\b(?:management|oversight|control|framework|methodology|best.practice)\b'
            ],
            'MEM': [
                r'\b(?:memory|storage|backup|recovery|archive|retention|lifecycle)\b',
                r'\b(?:data|database|repository|warehouse|lake|mart|analytics)\b',
                r'\b(?:knowledge|information|content|document|record|artifact)\b'
            ]
        }
        
        # Strand classification patterns (Issue vs Solution)
        self.issue_patterns = [
            r'\b(?:problem|issue|error|failure|bug|incident|outage|down|broken)\b',
            r'\b(?:alert|warning|critical|urgent|emergency|escalation|trouble)\b',
            r'\b(?:investigate|diagnose|troubleshoot|analyze|examine|review)\b',
            r'\b(?:failed|failing|timeout|crash|exception|denied|blocked)\b'
        ]
        
        self.solution_patterns = [
            r'\b(?:solution|fix|resolve|repair|patch|update|upgrade|implement)\b',
            r'\b(?:procedure|guide|howto|tutorial|documentation|runbook|playbook)\b',
            r'\b(?:success|successful|completed|resolved|fixed|working|stable)\b',
            r'\b(?:recommendation|best.practice|standard|guideline|template)\b'
        ]
        
        # SISSA overlay mapping
        self.sissa_overlay_mapping = {
            'HW': 'SISSA_ACTION_PLANNER',
            'SW': 'SISSA_ACTION_PLANNER', 
            'NET': 'SISSA_DECISION_SUPPORT',
            'SEC': 'SISSA_RISK_VALIDATOR',
            'GOV': 'SISSA_VALIDATOR',
            'MEM': 'SISSA_ACTION_PLANNER',
            'GEN': 'SISSA_DECISION_SUPPORT'
        }
        
        # Sequence counters (would be persisted in real implementation)
        self.sequence_counters = {}
    
    def analyze_content_and_generate_tag(self, content: str, metadata: Dict = None) -> DoubleHelixTag:
        """
        Analyze content and generate appropriate Double Helix tag
        
        Args:
            content: Text content to analyze
            metadata: Additional metadata for context
            
        Returns:
            DoubleHelixTag with appropriate classification
        """
        if not content:
            return None
            
        # Determine section based on content patterns
        section = self._classify_section(content, metadata)
        
        # Determine strand (Issue vs Solution)
        strand = self._classify_strand(content, metadata)
        
        # Generate sequence number
        sequence = self._get_next_sequence(section, strand)
        
        # Create tag ID
        tag_id = f"DH-{strand}-{section}-{sequence:03d}"
        
        # Calculate content hash
        content_hash = hashlib.sha256(content.encode()).hexdigest()
        
        # Assign SISSA overlay
        sissa_overlay = self.sissa_overlay_mapping.get(section, 'SISSA_DECISION_SUPPORT')
        
        # Create tag
        tag = DoubleHelixTag(
            tag_id=tag_id,
            strand=strand,
            section=section,
            sequence=sequence,
            content_hash=content_hash,
            created_at=datetime.now(timezone.utc).isoformat(),
            sissa_overlay=sissa_overlay,
            metadata=metadata or {}
        )
        
        self.logger.info(f"Generated DH tag: {tag_id} for content hash {content_hash[:8]}")
        return tag
    
    def _classify_section(self, content: str, metadata: Dict = None) -> str:
        """Classify content into Double Helix section"""
        content_lower = content.lower()
        section_scores = {}
        
        # Score each section based on pattern matches
        for section, patterns in self.section_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, content_lower, re.IGNORECASE))
                score += matches
            section_scores[section] = score
        
        # Use metadata hints if available
        if metadata:
            source_type = metadata.get('type', '').lower()
            if 'jira' in source_type or 'incident' in source_type:
                section_scores['SEC'] = section_scores.get('SEC', 0) + 2
            elif 'github' in source_type or 'code' in source_type:
                section_scores['SW'] = section_scores.get('SW', 0) + 2
            elif 'siem' in source_type or 'security' in source_type:
                section_scores['SEC'] = section_scores.get('SEC', 0) + 3
            elif 'cmdb' in source_type or 'asset' in source_type:
                section_scores['HW'] = section_scores.get('HW', 0) + 2
        
        # Return section with highest score, default to GEN
        if not section_scores or max(section_scores.values()) == 0:
            return 'GEN'
        
        return max(section_scores, key=section_scores.get)
    
    def _classify_strand(self, content: str, metadata: Dict = None) -> str:
        """Classify content as Issue (I) or Solution (S)"""
        content_lower = content.lower()
        
        # Count issue vs solution indicators
        issue_score = sum(len(re.findall(pattern, content_lower, re.IGNORECASE)) 
                         for pattern in self.issue_patterns)
        solution_score = sum(len(re.findall(pattern, content_lower, re.IGNORECASE)) 
                           for pattern in self.solution_patterns)
        
        # Use metadata hints
        if metadata:
            source_type = metadata.get('type', '').lower()
            status = metadata.get('status', '').lower()
            
            # Runbooks and procedures are typically solutions
            if any(keyword in source_type for keyword in ['runbook', 'procedure', 'wiki', 'guide']):
                solution_score += 3
            
            # Resolved incidents are solutions
            if any(keyword in status for keyword in ['resolved', 'closed', 'fixed', 'completed']):
                solution_score += 2
            
            # Open incidents are issues
            if any(keyword in status for keyword in ['open', 'new', 'active', 'investigating']):
                issue_score += 2
        
        # Default to Issue if no clear indicators
        return 'S' if solution_score > issue_score else 'I'
    
    def _get_next_sequence(self, section: str, strand: str) -> int:
        """Get next sequence number for section/strand combination"""
        key = f"{section}_{strand}"
        if key not in self.sequence_counters:
            self.sequence_counters[key] = 0
        self.sequence_counters[key] += 1
        return self.sequence_counters[key]

class SISSAIntegrator:
    """Integrates with SISSA overlays and generates audit events"""
    
    def __init__(self, audit_db_path: str = None):
        self.audit_db_path = audit_db_path
        self.logger = logging.getLogger(__name__)
        
        # SISSA overlay configurations
        self.overlay_configs = {
            'SISSA_ACTION_PLANNER': {
                'description': 'Plans and coordinates actions for hardware, software, and memory issues',
                'ai_tier': 'T2',
                'capabilities': ['action_planning', 'resource_coordination', 'timeline_management']
            },
            'SISSA_DECISION_SUPPORT': {
                'description': 'Provides decision support for network and general issues',
                'ai_tier': 'T1',
                'capabilities': ['decision_analysis', 'option_evaluation', 'risk_assessment']
            },
            'SISSA_RISK_VALIDATOR': {
                'description': 'Validates and assesses security risks',
                'ai_tier': 'T3',
                'capabilities': ['risk_validation', 'threat_assessment', 'compliance_checking']
            },
            'SISSA_VALIDATOR': {
                'description': 'Validates governance and policy compliance',
                'ai_tier': 'T2',
                'capabilities': ['policy_validation', 'compliance_checking', 'governance_oversight']
            }
        }
    
    def generate_sissa_event(self, dh_tag: DoubleHelixTag, actor: str, 
                           surface: str, additional_metadata: Dict = None) -> SISSAEvent:
        """
        Generate SISSA audit event for Double Helix tag
        
        Args:
            dh_tag: Double Helix tag
            actor: Who/what generated the tag
            surface: Which system surface triggered the event
            additional_metadata: Additional event metadata
            
        Returns:
            SISSAEvent for audit trail
        """
        event_id = f"SISSA_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{dh_tag.tag_id}"
        
        # Determine event type based on strand and section
        event_type = self._determine_event_type(dh_tag)
        
        # Prepare metadata
        event_metadata = {
            'dh_tag': asdict(dh_tag),
            'overlay_config': self.overlay_configs.get(dh_tag.sissa_overlay, {}),
            'classification': {
                'section': dh_tag.section,
                'strand': dh_tag.strand,
                'ai_tier': self.overlay_configs.get(dh_tag.sissa_overlay, {}).get('ai_tier', 'T1')
            }
        }
        
        if additional_metadata:
            event_metadata.update(additional_metadata)
        
        sissa_event = SISSAEvent(
            event_id=event_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc).isoformat(),
            actor=actor,
            surface=surface,
            dh_tag_id=dh_tag.tag_id,
            content_hash=dh_tag.content_hash,
            overlay=dh_tag.sissa_overlay,
            metadata=event_metadata
        )
        
        # Store in audit trail
        self._store_audit_event(sissa_event)
        
        self.logger.info(f"Generated SISSA event: {event_id}")
        return sissa_event
    
    def _determine_event_type(self, dh_tag: DoubleHelixTag) -> str:
        """Determine SISSA event type based on tag characteristics"""
        base_type = f"{dh_tag.section}_{dh_tag.strand}"
        
        event_type_mapping = {
            'HW_I': 'hardware_issue_detected',
            'HW_S': 'hardware_solution_documented',
            'SW_I': 'software_issue_detected', 
            'SW_S': 'software_solution_documented',
            'NET_I': 'network_issue_detected',
            'NET_S': 'network_solution_documented',
            'SEC_I': 'security_issue_detected',
            'SEC_S': 'security_solution_documented',
            'GOV_I': 'governance_issue_detected',
            'GOV_S': 'governance_solution_documented',
            'MEM_I': 'memory_issue_detected',
            'MEM_S': 'memory_solution_documented',
            'GEN_I': 'general_issue_detected',
            'GEN_S': 'general_solution_documented'
        }
        
        return event_type_mapping.get(base_type, 'unknown_event')
    
    def _store_audit_event(self, event: SISSAEvent):
        """Store SISSA event in audit trail"""
        if self.audit_db_path:
            try:
                import sqlite3
                with sqlite3.connect(self.audit_db_path) as conn:
                    conn.execute("""
                        INSERT INTO ingestion_audit 
                        (audit_id, source_id, ingestion_start, records_processed, 
                         dh_tags_assigned, sissa_events_generated, status, actor, surface, content_hash)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        event.event_id,
                        'dh_sissa_integration',
                        event.timestamp,
                        1,
                        json.dumps([event.dh_tag_id]),
                        1,
                        'success',
                        event.actor,
                        event.surface,
                        event.content_hash
                    ))
                    conn.commit()
            except Exception as e:
                self.logger.error(f"Failed to store audit event: {e}")

class BidirectionalLinker:
    """Manages bidirectional linking between Issues and Solutions"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
    
    def create_issue_solution_link(self, issue_tag: DoubleHelixTag, 
                                 solution_tag: DoubleHelixTag, 
                                 link_type: str = 'resolves') -> Dict:
        """
        Create bidirectional link between Issue and Solution tags
        
        Args:
            issue_tag: Issue tag (strand = I)
            solution_tag: Solution tag (strand = S)
            link_type: Type of relationship
            
        Returns:
            Link metadata
        """
        if issue_tag.strand != 'I' or solution_tag.strand != 'S':
            raise ValueError("Invalid strand types for Issue-Solution linking")
        
        link_id = f"LINK_{issue_tag.tag_id}_{solution_tag.tag_id}"
        
        link_metadata = {
            'link_id': link_id,
            'issue_tag_id': issue_tag.tag_id,
            'solution_tag_id': solution_tag.tag_id,
            'link_type': link_type,
            'created_at': datetime.now(timezone.utc).isoformat(),
            'confidence_score': self._calculate_link_confidence(issue_tag, solution_tag),
            'section_match': issue_tag.section == solution_tag.section,
            'content_similarity': self._calculate_content_similarity(
                issue_tag.content_hash, solution_tag.content_hash
            )
        }
        
        # Store link in database
        self._store_link(link_metadata)
        
        self.logger.info(f"Created bidirectional link: {link_id}")
        return link_metadata
    
    def find_potential_solutions(self, issue_tag: DoubleHelixTag, 
                               limit: int = 5) -> List[Dict]:
        """
        Find potential solution tags for an issue tag
        
        Args:
            issue_tag: Issue tag to find solutions for
            limit: Maximum number of solutions to return
            
        Returns:
            List of potential solution matches with scores
        """
        # This would query the database for solution tags in the same section
        # For now, return placeholder structure
        potential_solutions = []
        
        # Implementation would:
        # 1. Query solution tags in same section
        # 2. Calculate similarity scores
        # 3. Rank by relevance
        # 4. Return top matches
        
        return potential_solutions
    
    def _calculate_link_confidence(self, issue_tag: DoubleHelixTag, 
                                 solution_tag: DoubleHelixTag) -> float:
        """Calculate confidence score for Issue-Solution link"""
        confidence = 0.0
        
        # Section match increases confidence
        if issue_tag.section == solution_tag.section:
            confidence += 0.4
        
        # Temporal proximity (would need actual timestamps)
        # confidence += temporal_proximity_score
        
        # Content similarity (would need actual content comparison)
        # confidence += content_similarity_score
        
        # Metadata alignment
        if issue_tag.sissa_overlay == solution_tag.sissa_overlay:
            confidence += 0.2
        
        return min(confidence, 1.0)
    
    def _calculate_content_similarity(self, hash1: str, hash2: str) -> float:
        """Calculate content similarity between two content hashes"""
        # Placeholder - would implement actual similarity calculation
        return 0.5
    
    def _store_link(self, link_metadata: Dict):
        """Store bidirectional link in database"""
        try:
            import sqlite3
            with sqlite3.connect(self.db_path) as conn:
                # Create links table if not exists
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS dh_bidirectional_links (
                        link_id TEXT PRIMARY KEY,
                        issue_tag_id TEXT NOT NULL,
                        solution_tag_id TEXT NOT NULL,
                        link_type TEXT NOT NULL,
                        confidence_score REAL,
                        created_at TEXT NOT NULL,
                        metadata_json TEXT
                    )
                """)
                
                # Insert link
                conn.execute("""
                    INSERT OR REPLACE INTO dh_bidirectional_links
                    (link_id, issue_tag_id, solution_tag_id, link_type, 
                     confidence_score, created_at, metadata_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    link_metadata['link_id'],
                    link_metadata['issue_tag_id'],
                    link_metadata['solution_tag_id'],
                    link_metadata['link_type'],
                    link_metadata['confidence_score'],
                    link_metadata['created_at'],
                    json.dumps(link_metadata)
                ))
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to store bidirectional link: {e}")

class DataIngestionOrchestrator:
    """Orchestrates data ingestion with Double Helix and SISSA integration"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.tagger = DoubleHelixTagger()
        self.sissa_integrator = SISSAIntegrator(db_path)
        self.linker = BidirectionalLinker(db_path)
        self.logger = logging.getLogger(__name__)
    
    def process_content_with_dh_sissa(self, content: str, source_metadata: Dict,
                                    actor: str = 'data_ingestion_system',
                                    surface: str = 'data_pipeline') -> Dict:
        """
        Process content through complete DH+SISSA pipeline
        
        Args:
            content: Content to process
            source_metadata: Metadata about the content source
            actor: Who/what is processing the content
            surface: Which system surface is processing
            
        Returns:
            Complete processing results
        """
        results = {
            'processing_timestamp': datetime.now(timezone.utc).isoformat(),
            'content_hash': hashlib.sha256(content.encode()).hexdigest(),
            'source_metadata': source_metadata
        }
        
        try:
            # Generate Double Helix tag
            dh_tag = self.tagger.analyze_content_and_generate_tag(content, source_metadata)
            if dh_tag:
                results['dh_tag'] = asdict(dh_tag)
                
                # Generate SISSA event
                sissa_event = self.sissa_integrator.generate_sissa_event(
                    dh_tag, actor, surface, source_metadata
                )
                results['sissa_event'] = asdict(sissa_event)
                
                # Look for potential bidirectional links
                if dh_tag.strand == 'I':
                    potential_solutions = self.linker.find_potential_solutions(dh_tag)
                    results['potential_solutions'] = potential_solutions
                elif dh_tag.strand == 'S':
                    # Could look for related issues this solution might address
                    pass
                
                results['status'] = 'success'
                
            else:
                results['status'] = 'no_tag_generated'
                results['reason'] = 'Content did not meet tagging criteria'
                
        except Exception as e:
            results['status'] = 'error'
            results['error'] = str(e)
            self.logger.error(f"DH+SISSA processing failed: {e}")
        
        return results
    
    def batch_process_dataset(self, dataset_records: List[Dict], 
                            source_id: str) -> Dict:
        """
        Process entire dataset through DH+SISSA pipeline
        
        Args:
            dataset_records: List of records to process
            source_id: Source identifier
            
        Returns:
            Batch processing results
        """
        batch_results = {
            'source_id': source_id,
            'total_records': len(dataset_records),
            'processed_records': 0,
            'tags_generated': 0,
            'sissa_events_generated': 0,
            'links_created': 0,
            'processing_start': datetime.now(timezone.utc).isoformat(),
            'errors': []
        }
        
        for i, record in enumerate(dataset_records):
            try:
                content = record.get('content', record.get('body_text', ''))
                if not content:
                    continue
                
                # Process through pipeline
                result = self.process_content_with_dh_sissa(
                    content, 
                    record,
                    actor='batch_processor',
                    surface=f'data_pipeline_{source_id}'
                )
                
                if result['status'] == 'success':
                    batch_results['tags_generated'] += 1
                    if 'sissa_event' in result:
                        batch_results['sissa_events_generated'] += 1
                
                batch_results['processed_records'] += 1
                
                # Progress logging
                if (i + 1) % 100 == 0:
                    self.logger.info(f"Processed {i + 1}/{len(dataset_records)} records")
                    
            except Exception as e:
                batch_results['errors'].append({
                    'record_index': i,
                    'error': str(e)
                })
        
        batch_results['processing_end'] = datetime.now(timezone.utc).isoformat()
        
        self.logger.info(f"Batch processing complete: {batch_results['tags_generated']} tags generated")
        return batch_results
