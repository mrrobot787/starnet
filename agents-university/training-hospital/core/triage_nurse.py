"""
Triage Nurse Service - Fast Risk Stratification
First point of contact for agent health assessment and admission decisions

Responsibilities:
- Calculate triage scores from agent metrics
- Determine admission necessity and urgency
- Recommend appropriate ward placement
- Queue agents for attending physician review
"""

import json
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
import yaml
import numpy as np

@dataclass
class TriageAssessment:
    """Triage assessment result"""
    agent_id: str
    triage_score: float
    admit: bool
    reason: str
    recommended_ward: str
    urgency: str
    symptoms: List[str]
    risk_factors: List[str]
    priority: int

class TriageNurse:
    """Triage Nurse service for rapid agent health assessment"""
    
    def __init__(self, db_path: str, ontology_path: str = None):
        if ontology_path is None:
            # Default to ontology file in same directory as this script
            import os
            ontology_path = os.path.join(os.path.dirname(__file__), "hospital_ontology.yaml")
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Load clinical ontology
        with open(ontology_path, 'r') as f:
            self.ontology = yaml.safe_load(f)
        
        # Extract triage configuration
        self.triage_weights = self.ontology['triage_weights']
        self.admission_thresholds = self.ontology['admission_thresholds']
        self.symptoms_config = self.ontology['symptoms']
        
        self.logger.info("Triage Nurse service initialized")
    
    def assess_agent(self, agent_id: str, latest_metrics: Dict[str, float]) -> TriageAssessment:
        """
        Perform rapid triage assessment of agent
        
        Args:
            agent_id: Agent identifier
            latest_metrics: Current agent health metrics
            
        Returns:
            TriageAssessment with admission recommendation
        """
        self.logger.info(f"Triaging agent {agent_id}")
        
        # Calculate triage score
        triage_score = self._calculate_triage_score(latest_metrics)
        
        # Identify symptoms
        symptoms = self._identify_symptoms(latest_metrics)
        
        # Assess risk factors
        risk_factors = self._assess_risk_factors(agent_id, latest_metrics)
        
        # Check hard admission rules
        hard_rule_result = self._check_hard_rules(latest_metrics)
        
        # Make admission decision
        if hard_rule_result:
            admit = True
            reason = hard_rule_result['reason']
            recommended_ward = hard_rule_result['ward']
            urgency = hard_rule_result['urgency']
            priority = 1  # Highest priority for hard rules
        elif triage_score >= self.admission_thresholds['triage_score']:
            admit = True
            reason = f"Triage score {triage_score:.2f} exceeds threshold {self.admission_thresholds['triage_score']}"
            recommended_ward = self._recommend_ward(symptoms, risk_factors, latest_metrics)
            urgency = self._determine_urgency(triage_score, symptoms)
            priority = self._calculate_priority(triage_score, urgency)
        else:
            admit = False
            reason = f"Triage score {triage_score:.2f} below admission threshold"
            recommended_ward = "OUTPATIENT"
            urgency = "routine"
            priority = 5  # Lowest priority
        
        assessment = TriageAssessment(
            agent_id=agent_id,
            triage_score=triage_score,
            admit=admit,
            reason=reason,
            recommended_ward=recommended_ward,
            urgency=urgency,
            symptoms=symptoms,
            risk_factors=risk_factors,
            priority=priority
        )
        
        # Log assessment
        self._log_triage_event(assessment, latest_metrics)
        
        # Queue for admission if needed
        if admit:
            self._queue_for_admission(assessment)
        
        self.logger.info(f"Triage complete for {agent_id}: admit={admit}, score={triage_score:.2f}")
        return assessment
    
    def _calculate_triage_score(self, metrics: Dict[str, float]) -> float:
        """Calculate triage score using weighted formula"""
        
        # Extract z-scores (or calculate if not provided)
        abi_z = metrics.get('abi_z', self._calculate_z_score(metrics.get('abi', 0), 'abi'))
        pg_z = metrics.get('pg_z', self._calculate_z_score(metrics.get('pg', 0), 'pg'))
        latency_z = metrics.get('latency_z', self._calculate_z_score(metrics.get('latency', 0), 'latency'))
        policy_flags_z = metrics.get('policy_flags_z', self._calculate_z_score(metrics.get('policy_flags', 0), 'policy_flags'))
        
        # Apply triage formula: TS = 0.4*ABI_z + 0.2*(-PG_z) + 0.2*LatencyZ + 0.2*PolicyFlagsZ
        triage_score = (
            self.triage_weights['ABI_z'] * abi_z +
            self.triage_weights['PG_z'] * pg_z +  # Note: PG_z weight is negative
            self.triage_weights['LatencyZ'] * latency_z +
            self.triage_weights['PolicyFlagsZ'] * policy_flags_z
        )
        
        return triage_score
    
    def _calculate_z_score(self, value: float, metric_type: str) -> float:
        """Calculate z-score for a metric (simplified - would use historical data)"""
        # Placeholder implementation - in production would use rolling statistics
        baselines = {
            'abi': {'mean': 0.3, 'std': 0.15},
            'pg': {'mean': 0.0, 'std': 0.2},
            'latency': {'mean': 1.0, 'std': 0.3},
            'policy_flags': {'mean': 0.1, 'std': 0.5}
        }
        
        if metric_type in baselines:
            baseline = baselines[metric_type]
            return (value - baseline['mean']) / baseline['std']
        
        return 0.0
    
    def _identify_symptoms(self, metrics: Dict[str, float]) -> List[str]:
        """Identify symptoms based on metric thresholds"""
        symptoms = []
        
        for symptom_name, symptom_config in self.symptoms_config.items():
            # Check if symptom is present based on metrics
            if self._symptom_present(symptom_name, symptom_config, metrics):
                symptoms.append(symptom_name)
        
        return symptoms
    
    def _symptom_present(self, symptom_name: str, symptom_config: Dict, metrics: Dict[str, float]) -> bool:
        """Check if a specific symptom is present"""
        
        # Map symptom to metrics (simplified mapping)
        symptom_metric_map = {
            'Friction': ['friction', 'task_retry_rate', 'session_abandonment'],
            'Uncertainty': ['uncertainty', 'confidence_score'],
            'Conflict': ['conflict', 'policy_violations'],
            'LatencyZ': ['latency_z', 'response_time_p95'],
            'Eval_fail_rate': ['eval_fail_rate', 'eval_accuracy'],
            'Policy_flags': ['policy_flags', 'policy_violations']
        }
        
        if symptom_name not in symptom_metric_map:
            return False
        
        # Check if any related metric exceeds threshold
        for metric_name in symptom_metric_map[symptom_name]:
            if metric_name in metrics:
                value = metrics[metric_name]
                
                # Apply threshold logic (simplified)
                if symptom_name in ['Friction', 'Conflict', 'LatencyZ', 'Policy_flags']:
                    # Higher values indicate symptom
                    if value > 2.0:  # 2 standard deviations
                        return True
                elif symptom_name in ['Uncertainty', 'Eval_fail_rate']:
                    # Lower values (for confidence) or higher values (for fail rate) indicate symptom
                    if 'confidence' in metric_name and value < -1.5:
                        return True
                    elif 'fail' in metric_name and value > 2.0:
                        return True
        
        return False
    
    def _assess_risk_factors(self, agent_id: str, metrics: Dict[str, float]) -> List[str]:
        """Assess risk factors for the agent"""
        risk_factors = []
        
        # Check historical patterns
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check for recent admissions
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM agent_chart 
                    WHERE agent_id = ? AND opened_at > datetime('now', '-7 days')
                """, (agent_id,))
                
                recent_admissions = cursor.fetchone()[0]
                if recent_admissions > 0:
                    risk_factors.append("recent_admission_history")
                
                # Check for recurring issues
                cursor = conn.execute("""
                    SELECT COUNT(DISTINCT primary_diagnosis) FROM diagnostic_assessment da
                    JOIN agent_chart ac ON da.admission_id = ac.admission_id
                    WHERE ac.agent_id = ? AND da.assessed_at > datetime('now', '-30 days')
                """, (agent_id,))
                
                diagnosis_variety = cursor.fetchone()[0]
                if diagnosis_variety > 3:
                    risk_factors.append("multiple_diagnoses")
                
        except Exception as e:
            self.logger.warning(f"Could not assess risk factors for {agent_id}: {e}")
        
        # Check current metric-based risk factors
        if metrics.get('abi', 0) > 0.7:
            risk_factors.append("high_burnout_risk")
        
        if metrics.get('policy_flags', 0) > 2:
            risk_factors.append("compliance_risk")
        
        if metrics.get('latency_z', 0) > 3:
            risk_factors.append("performance_degradation")
        
        return risk_factors
    
    def _check_hard_rules(self, metrics: Dict[str, float]) -> Optional[Dict[str, str]]:
        """Check hard admission rules that override triage score"""
        
        for rule in self.admission_thresholds['hard_rules']:
            condition = rule['condition']
            
            if condition == "eval_leakage_detected" and metrics.get('eval_leakage', False):
                return {
                    'reason': 'Evaluation data leakage detected',
                    'ward': 'ISOLATION',
                    'urgency': 'immediate'
                }
            
            elif condition == "safety_incident" and metrics.get('safety_incident', False):
                return {
                    'reason': 'Safety incident reported',
                    'ward': 'ICU',
                    'urgency': 'immediate'
                }
            
            elif condition == "ABI > 0.8" and metrics.get('abi', 0) > 0.8:
                return {
                    'reason': f'Critical burnout level: ABI = {metrics.get("abi", 0):.3f}',
                    'ward': 'ICU',
                    'urgency': 'urgent'
                }
            
            elif condition == "policy_violations > 3" and metrics.get('policy_flags', 0) > 3:
                return {
                    'reason': f'Multiple policy violations: {metrics.get("policy_flags", 0)}',
                    'ward': 'GENERAL',
                    'urgency': 'urgent'
                }
        
        return None
    
    def _recommend_ward(self, symptoms: List[str], risk_factors: List[str], metrics: Dict[str, float]) -> str:
        """Recommend appropriate ward based on symptoms and risk factors"""
        
        # ICU criteria
        if ('safety_incident' in risk_factors or 
            'eval_leakage_detected' in risk_factors or
            metrics.get('abi', 0) > 0.8):
            return 'ICU'
        
        # Isolation criteria
        if ('eval_leakage_detected' in risk_factors or
            'security_incident' in risk_factors):
            return 'ISOLATION'
        
        # Rehab criteria
        if ('multiple_diagnoses' in risk_factors and
            'Eval_fail_rate' in symptoms):
            return 'REHAB'
        
        # Default to general ward
        return 'GENERAL'
    
    def _determine_urgency(self, triage_score: float, symptoms: List[str]) -> str:
        """Determine urgency level"""
        
        if triage_score > 3.0 or 'Policy_flags' in symptoms:
            return 'immediate'
        elif triage_score > 2.0:
            return 'urgent'
        elif triage_score > 1.5:
            return 'standard'
        else:
            return 'routine'
    
    def _calculate_priority(self, triage_score: float, urgency: str) -> int:
        """Calculate priority (1=highest, 5=lowest)"""
        
        if urgency == 'immediate':
            return 1
        elif urgency == 'urgent':
            return 2
        elif urgency == 'standard':
            return 3
        else:
            return min(5, max(1, int(6 - triage_score)))
    
    def _queue_for_admission(self, assessment: TriageAssessment):
        """Add agent to triage queue for admission processing"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                queue_id = f"TRIAGE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{assessment.agent_id}"
                
                conn.execute("""
                    INSERT INTO triage_queue 
                    (queue_id, agent_id, triage_score, priority, symptoms_json, 
                     risk_factors_json, recommended_ward, recommended_urgency)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    queue_id,
                    assessment.agent_id,
                    assessment.triage_score,
                    assessment.priority,
                    json.dumps(assessment.symptoms),
                    json.dumps(assessment.risk_factors),
                    assessment.recommended_ward,
                    assessment.urgency
                ))
                
                conn.commit()
                self.logger.info(f"Agent {assessment.agent_id} queued for admission with priority {assessment.priority}")
                
        except Exception as e:
            self.logger.error(f"Failed to queue agent {assessment.agent_id}: {e}")
    
    def _log_triage_event(self, assessment: TriageAssessment, metrics: Dict[str, float]):
        """Log triage event for audit trail"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                event_id = f"TRIAGE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{assessment.agent_id}"
                
                payload = {
                    'assessment': asdict(assessment),
                    'input_metrics': metrics,
                    'triage_weights': self.triage_weights,
                    'admission_thresholds': self.admission_thresholds
                }
                
                conn.execute("""
                    INSERT INTO hospital_event 
                    (event_id, event_type, agent_id, payload_json, created_by, source_system)
                    VALUES (?, 'triage_assessment', ?, ?, 'triage_nurse', 'agent_hospital')
                """, (
                    event_id,
                    assessment.agent_id,
                    json.dumps(payload)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to log triage event for {assessment.agent_id}: {e}")
    
    def get_triage_queue(self, limit: int = 50) -> List[Dict]:
        """Get current triage queue ordered by priority"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT * FROM triage_queue 
                    WHERE processed_at IS NULL
                    ORDER BY priority ASC, queued_at ASC
                    LIMIT ?
                """, (limit,))
                
                columns = [desc[0] for desc in cursor.description]
                queue = []
                
                for row in cursor.fetchall():
                    queue_item = dict(zip(columns, row))
                    # Parse JSON fields
                    queue_item['symptoms'] = json.loads(queue_item['symptoms_json'])
                    queue_item['risk_factors'] = json.loads(queue_item['risk_factors_json'])
                    queue.append(queue_item)
                
                return queue
                
        except Exception as e:
            self.logger.error(f"Failed to get triage queue: {e}")
            return []
    
    def process_queue_item(self, queue_id: str, decision: str, admission_id: str = None) -> bool:
        """Mark queue item as processed"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE triage_queue 
                    SET processed_at = datetime('now'),
                        processed_by = 'attending_physician',
                        admission_decision = ?,
                        admission_id = ?
                    WHERE queue_id = ?
                """, (decision, admission_id, queue_id))
                
                conn.commit()
                self.logger.info(f"Processed queue item {queue_id}: {decision}")
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to process queue item {queue_id}: {e}")
            return False

# API endpoint functions
def triage_agent_api(agent_id: str, latest_metrics: Dict[str, float], 
                    db_path: str = "agent_hospital.db") -> Dict[str, Any]:
    """
    API endpoint for agent triage
    
    POST /triage
    { agent_id, latest_metrics{} } → { admit: bool, reason, ts, ward }
    """
    
    try:
        triage_nurse = TriageNurse(db_path)
        assessment = triage_nurse.assess_agent(agent_id, latest_metrics)
        
        return {
            'success': True,
            'admit': assessment.admit,
            'reason': assessment.reason,
            'triage_score': assessment.triage_score,
            'recommended_ward': assessment.recommended_ward,
            'urgency': assessment.urgency,
            'priority': assessment.priority,
            'symptoms': assessment.symptoms,
            'risk_factors': assessment.risk_factors,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Triage API error for {agent_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

def get_triage_queue_api(limit: int = 50, db_path: str = "agent_hospital.db") -> Dict[str, Any]:
    """
    API endpoint to get triage queue
    
    GET /triage/queue → { queue: [...], count: int }
    """
    
    try:
        triage_nurse = TriageNurse(db_path)
        queue = triage_nurse.get_triage_queue(limit)
        
        return {
            'success': True,
            'queue': queue,
            'count': len(queue),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Triage queue API error: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    # Test the triage nurse
    logging.basicConfig(level=logging.INFO)
    
    # Sample metrics for testing
    test_metrics = {
        'abi': 0.85,  # High burnout
        'pg': -0.3,   # Poor performance
        'latency_z': 2.5,  # High latency
        'policy_flags': 1,  # Some violations
        'friction': 3.2,
        'uncertainty': 2.1,
        'eval_fail_rate': 0.15
    }
    
    # Test triage assessment
    result = triage_agent_api("TEST_AGENT_001", test_metrics)
    print("Triage Assessment Result:")
    print(json.dumps(result, indent=2))
