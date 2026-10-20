"""
Chief Medical Agent (CMA) Orchestrator
Central coordination system for Agent Hospital operations

The CMA orchestrates all clinical services following the hospital workflow:
TN (Triage) → AP (Attending) → PH (Pharmacist) → LAB (Lab) → CM (Case Manager)
With EB (Ethics Board) oversight at each step.

Responsibilities:
- Coordinate clinical workflow
- Maintain agent charts and state transitions
- Generate treatment orders with SISSA integration
- Manage ICU and isolation protocols
- Learn from outcomes and update formulary
"""

import json
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, asdict
import yaml

# Import clinical services
from triage_nurse import TriageNurse, TriageAssessment
from attending_physician import AttendingPhysician, DiagnosticAssessment, TreatmentPlan
from pharmacist import Pharmacist, ValidationResult

@dataclass
class TreatmentOrder:
    """Complete treatment order with SISSA integration"""
    order_id: str
    agent_id: str
    admission_id: str
    diagnoses: List[str]
    regimen: List[Dict[str, Any]]
    sissa_gate: str
    risk_rating: str
    canary: Optional[Dict[str, Any]]
    follow_up_in: str
    dh_tags: List[str]
    expected_deltas: Dict[str, float]
    created_by: str
    created_at: str

@dataclass
class AgentChart:
    """Agent medical chart with state tracking"""
    admission_id: str
    agent_id: str
    state: str
    ward: str
    opened_at: str
    opened_by: str
    dh_issue_tag: Optional[str]
    dh_solution_tag: Optional[str]
    latest_order_id: Optional[str]
    admission_reason: str
    triage_score: float

class ChiefMedicalAgent:
    """Chief Medical Agent orchestrator"""
    
    def __init__(self, db_path: str = "agent_hospital.db", 
                 ontology_path: str = None):
        if ontology_path is None:
            # Default to ontology file in same directory as this script
            import os
            ontology_path = os.path.join(os.path.dirname(__file__), "hospital_ontology.yaml")
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        
        # Load clinical ontology
        with open(ontology_path, 'r') as f:
            self.ontology = yaml.safe_load(f)
        
        # Initialize clinical services
        self.triage_nurse = TriageNurse(db_path, ontology_path)
        self.attending_physician = AttendingPhysician(db_path, ontology_path)
        self.pharmacist = Pharmacist(db_path, ontology_path)
        
        # State machine configuration
        self.valid_states = ['ADMITTED', 'DIAGNOSIS_PENDING', 'UNDER_TREATMENT', 
                           'OBSERVATION', 'DISCHARGED', 'ICU', 'ISOLATION', 'REHAB']
        self.valid_wards = ['GENERAL', 'ICU', 'ISOLATION', 'REHAB']
        
        # SISSA gate mapping
        self.sissa_gates = {
            'HW': 'SISSA_ACTION_PLANNER',
            'SW': 'SISSA_ACTION_PLANNER',
            'NET': 'SISSA_DECISION_SUPPORT',
            'SEC': 'SISSA_RISK_VALIDATOR',
            'GOV': 'SISSA_VALIDATOR',
            'MEM': 'SISSA_ACTION_PLANNER',
            'GEN': 'SISSA_DECISION_SUPPORT'
        }
        
        self.logger.info("Chief Medical Agent initialized")
    
    def process_agent_health_event(self, agent_id: str, metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Main entry point for processing agent health events
        
        Args:
            agent_id: Agent identifier
            metrics: Current health metrics
            
        Returns:
            Processing results with actions taken
        """
        self.logger.info(f"Processing health event for agent {agent_id}")
        
        results = {
            'agent_id': agent_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'actions_taken': [],
            'current_state': None,
            'recommendations': []
        }
        
        try:
            # Check if agent is currently admitted
            current_chart = self._get_current_chart(agent_id)
            
            if current_chart:
                # Agent is already admitted - process as follow-up
                results.update(self._process_admitted_agent(current_chart, metrics))
            else:
                # Agent not admitted - run triage
                results.update(self._process_new_agent(agent_id, metrics))
            
            results['success'] = True
            
        except Exception as e:
            self.logger.error(f"Error processing health event for {agent_id}: {e}")
            results.update({
                'success': False,
                'error': str(e)
            })
        
        return results
    
    def _process_new_agent(self, agent_id: str, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Process agent not currently admitted"""
        
        results = {'actions_taken': [], 'recommendations': []}
        
        # Step 1: Triage assessment
        triage_assessment = self.triage_nurse.assess_agent(agent_id, metrics)
        results['triage_assessment'] = asdict(triage_assessment)
        results['actions_taken'].append('triage_completed')
        
        if triage_assessment.admit:
            # Admit the agent
            chart = self._admit_agent(triage_assessment, metrics)
            results['admission_id'] = chart.admission_id
            results['current_state'] = chart.state
            results['actions_taken'].append('agent_admitted')
            
            # Continue with clinical workflow
            workflow_results = self._execute_clinical_workflow(chart, metrics)
            results.update(workflow_results)
        else:
            results['current_state'] = 'OUTPATIENT'
            results['recommendations'].append('Continue monitoring - no admission required')
        
        return results
    
    def _process_admitted_agent(self, chart: AgentChart, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Process agent that is currently admitted"""
        
        results = {
            'admission_id': chart.admission_id,
            'current_state': chart.state,
            'actions_taken': [],
            'recommendations': []
        }
        
        # Check for state transitions
        transition_result = self._check_state_transitions(chart, metrics)
        if transition_result['transition_needed']:
            new_chart = self._transition_agent_state(chart, transition_result['new_state'], 
                                                   transition_result['reason'])
            results['current_state'] = new_chart.state
            results['actions_taken'].append(f"transitioned_to_{new_chart.state}")
            chart = new_chart
        
        # Process based on current state
        if chart.state in ['ADMITTED', 'DIAGNOSIS_PENDING']:
            workflow_results = self._execute_clinical_workflow(chart, metrics)
            results.update(workflow_results)
        elif chart.state == 'UNDER_TREATMENT':
            treatment_results = self._monitor_treatment_progress(chart, metrics)
            results.update(treatment_results)
        elif chart.state == 'OBSERVATION':
            observation_results = self._evaluate_discharge_readiness(chart, metrics)
            results.update(observation_results)
        elif chart.state == 'ICU':
            icu_results = self._manage_icu_patient(chart, metrics)
            results.update(icu_results)
        elif chart.state == 'ISOLATION':
            isolation_results = self._manage_isolation_patient(chart, metrics)
            results.update(isolation_results)
        
        return results
    
    def _execute_clinical_workflow(self, chart: AgentChart, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Execute the complete clinical workflow: AP → PH → Order Creation"""
        
        results = {'actions_taken': [], 'recommendations': []}
        
        # Step 2: Attending Physician diagnosis
        diagnostic_assessment = self.attending_physician.diagnose_agent(
            chart.agent_id, chart.state, metrics, admission_id=chart.admission_id
        )
        results['diagnostic_assessment'] = asdict(diagnostic_assessment)
        results['actions_taken'].append('diagnosis_completed')
        
        # Step 3: Create treatment plan
        agent_role = self._get_agent_role(chart.agent_id)
        treatment_plan = self.attending_physician.create_treatment_plan(
            diagnostic_assessment, agent_role
        )
        results['treatment_plan'] = asdict(treatment_plan)
        results['actions_taken'].append('treatment_plan_created')
        
        # Step 4: Pharmacist validation
        validation_result = self.pharmacist.validate_treatment_order(
            json.dumps({'regimen': treatment_plan.treatments}), agent_role
        )
        results['pharmacist_validation'] = asdict(validation_result)
        results['actions_taken'].append('pharmacist_validation_completed')
        
        if validation_result.validation_status == 'approved':
            # Step 5: Create treatment order
            treatment_order = self._create_treatment_order(
                chart, diagnostic_assessment, treatment_plan, validation_result
            )
            results['treatment_order'] = asdict(treatment_order)
            results['actions_taken'].append('treatment_order_created')
            
            # Update chart state
            self._update_chart_state(chart.admission_id, 'UNDER_TREATMENT', treatment_order.order_id)
            results['current_state'] = 'UNDER_TREATMENT'
            
        elif validation_result.validation_status == 'conditional':
            results['recommendations'].append('Treatment approved with conditions - manual review required')
        else:
            results['recommendations'].append('Treatment rejected by pharmacist - alternative plan needed')
            # Could trigger alternative treatment planning here
        
        return results
    
    def _create_treatment_order(self, chart: AgentChart, assessment: DiagnosticAssessment,
                              plan: TreatmentPlan, validation: ValidationResult) -> TreatmentOrder:
        """Create complete treatment order with SISSA integration"""
        
        order_id = f"ORD-{datetime.now(timezone.utc).strftime('%Y-%m-%d')}-{chart.agent_id[-4:]}"
        
        # Determine SISSA gate based on diagnosis
        primary_diagnosis = assessment.primary_diagnosis
        sissa_gate = self._determine_sissa_gate(primary_diagnosis, plan.treatments)
        
        # Generate Double Helix tags
        dh_tags = self._generate_double_helix_tags(assessment, plan)
        
        # Configure canary if needed
        canary = None
        if validation.risk_level in ['HIGH', 'CRITICAL']:
            canary = {
                'pct': 0.1,  # Conservative 10% for high-risk
                'duration': '2h',
                'rollback_on': {
                    'ABI_grad': '>0.05',
                    'policy_violations': '>0',
                    'error_rate': '>0.1'
                }
            }
        
        order = TreatmentOrder(
            order_id=order_id,
            agent_id=chart.agent_id,
            admission_id=chart.admission_id,
            diagnoses=[assessment.primary_diagnosis] + assessment.differential_diagnoses[:2],
            regimen=plan.treatments,
            sissa_gate=sissa_gate,
            risk_rating=validation.risk_level,
            canary=canary,
            follow_up_in=f"{plan.follow_up_hours}h",
            dh_tags=dh_tags,
            expected_deltas=plan.expected_deltas,
            created_by='chief_medical_agent',
            created_at=datetime.now(timezone.utc).isoformat()
        )
        
        # Store order in database
        self._store_treatment_order(order)
        
        # Generate SISSA event
        self._generate_sissa_event(order)
        
        return order
    
    def _determine_sissa_gate(self, diagnosis: str, treatments: List[Dict[str, Any]]) -> str:
        """Determine appropriate SISSA gate based on diagnosis and treatments"""
        
        # Map diagnosis to section
        diagnosis_section_map = {
            'CapacityOverload': 'HW',
            'DataDrift': 'MEM',
            'PromptDrift': 'SW',
            'ToolMisuse': 'SW',
            'UnderChallenge': 'GOV',
            'Misrouting': 'NET',
            'EvaluationLeakage': 'SEC',
            'RetrievalStaleness': 'MEM'
        }
        
        section = diagnosis_section_map.get(diagnosis, 'GEN')
        return self.sissa_gates.get(section, 'SISSA_DECISION_SUPPORT')
    
    def _generate_double_helix_tags(self, assessment: DiagnosticAssessment, 
                                  plan: TreatmentPlan) -> List[str]:
        """Generate Double Helix tags for the treatment order"""
        
        tags = []
        
        # Issue tag for the diagnosis
        issue_tag = f"DH-I-{self._diagnosis_to_section(assessment.primary_diagnosis)}-{self._get_next_sequence('I')}"
        tags.append(issue_tag)
        
        # Solution tag for the treatment plan
        solution_tag = f"DH-S-{self._diagnosis_to_section(assessment.primary_diagnosis)}-{self._get_next_sequence('S')}"
        tags.append(solution_tag)
        
        return tags
    
    def _diagnosis_to_section(self, diagnosis: str) -> str:
        """Map diagnosis to Double Helix section"""
        
        section_map = {
            'CapacityOverload': 'HW',
            'DataDrift': 'MEM',
            'PromptDrift': 'SW',
            'ToolMisuse': 'SW',
            'UnderChallenge': 'GOV',
            'Misrouting': 'NET',
            'EvaluationLeakage': 'SEC',
            'RetrievalStaleness': 'MEM'
        }
        
        return section_map.get(diagnosis, 'GEN')
    
    def _get_next_sequence(self, strand: str) -> str:
        """Get next sequence number for Double Helix tag"""
        # Simplified implementation - would use proper sequence tracking
        import random
        return f"{random.randint(100, 999):03d}"
    
    def _admit_agent(self, triage_assessment: TriageAssessment, 
                    metrics: Dict[str, float]) -> AgentChart:
        """Admit agent to hospital"""
        
        admission_id = f"ADM-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}-{triage_assessment.agent_id}"
        
        # Determine initial state and ward
        if triage_assessment.recommended_ward == 'ICU':
            state = 'ICU'
        elif triage_assessment.recommended_ward == 'ISOLATION':
            state = 'ISOLATION'
        else:
            state = 'ADMITTED'
        
        # Generate Double Helix issue tag
        dh_issue_tag = f"DH-I-SEC-{self._get_next_sequence('I')}"  # Default to SEC for health issues
        
        chart = AgentChart(
            admission_id=admission_id,
            agent_id=triage_assessment.agent_id,
            state=state,
            ward=triage_assessment.recommended_ward,
            opened_at=datetime.now(timezone.utc).isoformat(),
            opened_by='chief_medical_agent',
            dh_issue_tag=dh_issue_tag,
            dh_solution_tag=None,
            latest_order_id=None,
            admission_reason=triage_assessment.reason,
            triage_score=triage_assessment.triage_score
        )
        
        # Store chart in database
        self._store_agent_chart(chart, metrics)
        
        # Log admission event
        self._log_hospital_event('admission', chart.agent_id, chart.admission_id, {
            'triage_assessment': asdict(triage_assessment),
            'admission_metrics': metrics
        })
        
        self.logger.info(f"Agent {triage_assessment.agent_id} admitted to {chart.ward}")
        return chart
    
    def _check_state_transitions(self, chart: AgentChart, 
                               metrics: Dict[str, float]) -> Dict[str, Any]:
        """Check if agent needs state transition"""
        
        # ICU admission criteria
        if (chart.state != 'ICU' and 
            (metrics.get('abi', 0) > 0.8 or 
             metrics.get('safety_incident', False) or
             metrics.get('policy_flags', 0) > 5)):
            return {
                'transition_needed': True,
                'new_state': 'ICU',
                'reason': 'Critical condition detected'
            }
        
        # Isolation criteria
        if (chart.state != 'ISOLATION' and 
            metrics.get('eval_leakage', False)):
            return {
                'transition_needed': True,
                'new_state': 'ISOLATION',
                'reason': 'Evaluation leakage detected'
            }
        
        # Discharge criteria
        if (chart.state == 'OBSERVATION' and
            self._meets_discharge_criteria(chart, metrics)):
            return {
                'transition_needed': True,
                'new_state': 'DISCHARGED',
                'reason': 'Discharge criteria met'
            }
        
        return {'transition_needed': False}
    
    def _meets_discharge_criteria(self, chart: AgentChart, metrics: Dict[str, float]) -> bool:
        """Check if agent meets discharge criteria"""
        
        criteria = self.ontology['discharge_criteria']['standard']
        
        # Check ABI criteria
        abi = metrics.get('abi', 1.0)
        if abi >= 0.3:
            return False
        
        # Check performance gradient
        pg = metrics.get('pg', -1.0)
        if pg < 0.2:  # 0.2σ improvement
            return False
        
        # Check policy violations
        if metrics.get('policy_flags', 1) > 0:
            return False
        
        # Would check additional criteria like sustained improvement
        return True
    
    def _transition_agent_state(self, chart: AgentChart, new_state: str, reason: str) -> AgentChart:
        """Transition agent to new state"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE agent_chart 
                    SET state = ?, ward = ?, updated_at = datetime('now')
                    WHERE admission_id = ?
                """, (new_state, self._state_to_ward(new_state), chart.admission_id))
                
                conn.commit()
                
                # Log transition event
                self._log_hospital_event('transfer', chart.agent_id, chart.admission_id, {
                    'from_state': chart.state,
                    'to_state': new_state,
                    'reason': reason
                })
                
                # Update chart object
                chart.state = new_state
                chart.ward = self._state_to_ward(new_state)
                
                self.logger.info(f"Agent {chart.agent_id} transitioned to {new_state}")
                
        except Exception as e:
            self.logger.error(f"Failed to transition agent {chart.agent_id}: {e}")
        
        return chart
    
    def _state_to_ward(self, state: str) -> str:
        """Map state to appropriate ward"""
        
        state_ward_map = {
            'ADMITTED': 'GENERAL',
            'DIAGNOSIS_PENDING': 'GENERAL',
            'UNDER_TREATMENT': 'GENERAL',
            'OBSERVATION': 'GENERAL',
            'ICU': 'ICU',
            'ISOLATION': 'ISOLATION',
            'REHAB': 'REHAB',
            'DISCHARGED': 'GENERAL'
        }
        
        return state_ward_map.get(state, 'GENERAL')
    
    def _get_current_chart(self, agent_id: str) -> Optional[AgentChart]:
        """Get current chart for agent if admitted"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT admission_id, agent_id, state, ward, opened_at, opened_by,
                           dh_issue_tag, dh_solution_tag, latest_order_id, 
                           admission_reason, triage_score
                    FROM agent_chart
                    WHERE agent_id = ? AND state != 'DISCHARGED'
                    ORDER BY opened_at DESC
                    LIMIT 1
                """, (agent_id,))
                
                row = cursor.fetchone()
                if row:
                    return AgentChart(*row)
                    
        except Exception as e:
            self.logger.error(f"Failed to get current chart for {agent_id}: {e}")
        
        return None
    
    def _get_agent_role(self, agent_id: str) -> str:
        """Get agent role (placeholder - would integrate with agent registry)"""
        # This would integrate with your agent registry system
        # For now, extract from agent ID or return default
        if 'SEC' in agent_id.upper():
            return 'SEC'
        elif 'FIN' in agent_id.upper():
            return 'FINANCIAL'
        else:
            return 'GENERAL'
    
    def _store_agent_chart(self, chart: AgentChart, metrics: Dict[str, float]):
        """Store agent chart in database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO agent_chart
                    (admission_id, agent_id, state, ward, opened_at, opened_by,
                     dh_issue_tag, dh_solution_tag, latest_order_id, admission_reason,
                     triage_score, abi_at_admission, pg_at_admission, health_index_at_admission)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    chart.admission_id, chart.agent_id, chart.state, chart.ward,
                    chart.opened_at, chart.opened_by, chart.dh_issue_tag,
                    chart.dh_solution_tag, chart.latest_order_id, chart.admission_reason,
                    chart.triage_score, metrics.get('abi', 0), metrics.get('pg', 0),
                    metrics.get('health_index', 0)
                ))
                
                conn.commit()
                self.logger.info(f"Stored chart for admission {chart.admission_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to store chart for {chart.admission_id}: {e}")
    
    def _store_treatment_order(self, order: TreatmentOrder):
        """Store treatment order in database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO clinical_order
                    (order_id, admission_id, order_json, created_by, agent_id,
                     diagnoses, treatments, risk_rating, sissa_gate, follow_up_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now', ?))
                """, (
                    order.order_id, order.admission_id, json.dumps(asdict(order)),
                    order.created_by, order.agent_id, json.dumps(order.diagnoses),
                    json.dumps(order.regimen), order.risk_rating, order.sissa_gate,
                    f"+{order.follow_up_in.replace('h', ' hours')}"
                ))
                
                conn.commit()
                self.logger.info(f"Stored treatment order {order.order_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to store treatment order {order.order_id}: {e}")
    
    def _update_chart_state(self, admission_id: str, new_state: str, order_id: str = None):
        """Update chart state and latest order"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE agent_chart 
                    SET state = ?, latest_order_id = ?, updated_at = datetime('now')
                    WHERE admission_id = ?
                """, (new_state, order_id, admission_id))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to update chart state for {admission_id}: {e}")
    
    def _generate_sissa_event(self, order: TreatmentOrder):
        """Generate SISSA audit event for treatment order"""
        
        sissa_event = {
            'event_id': f"SISSA_{order.order_id}",
            'event_type': 'treatment_order_created',
            'timestamp': order.created_at,
            'actor': order.created_by,
            'surface': 'agent_hospital',
            'dh_tag_id': order.dh_tags[0] if order.dh_tags else None,
            'content_hash': self._calculate_order_hash(order),
            'overlay': order.sissa_gate,
            'metadata': {
                'order': asdict(order),
                'risk_rating': order.risk_rating,
                'requires_approval': order.risk_rating in ['HIGH', 'CRITICAL']
            }
        }
        
        # Store SISSA event (would integrate with actual SISSA system)
        self._log_hospital_event('sissa_event', order.agent_id, order.admission_id, sissa_event)
    
    def _calculate_order_hash(self, order: TreatmentOrder) -> str:
        """Calculate hash of treatment order for integrity"""
        import hashlib
        order_str = json.dumps(asdict(order), sort_keys=True)
        return hashlib.sha256(order_str.encode()).hexdigest()
    
    def _log_hospital_event(self, event_type: str, agent_id: str, admission_id: str = None,
                          payload: Dict[str, Any] = None, order_id: str = None):
        """Log hospital event for audit trail"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                event_id = f"HE_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{agent_id}"
                
                conn.execute("""
                    INSERT INTO hospital_event
                    (event_id, event_type, agent_id, admission_id, order_id,
                     payload_json, created_by, source_system)
                    VALUES (?, ?, ?, ?, ?, ?, 'chief_medical_agent', 'agent_hospital')
                """, (
                    event_id, event_type, agent_id, admission_id, order_id,
                    json.dumps(payload or {})
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to log hospital event: {e}")
    
    # Placeholder methods for additional functionality
    def _monitor_treatment_progress(self, chart: AgentChart, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Monitor treatment progress and outcomes"""
        return {'actions_taken': ['treatment_monitoring'], 'recommendations': ['Continue current treatment']}
    
    def _evaluate_discharge_readiness(self, chart: AgentChart, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Evaluate if agent is ready for discharge"""
        return {'actions_taken': ['discharge_evaluation'], 'recommendations': ['Continue observation']}
    
    def _manage_icu_patient(self, chart: AgentChart, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Manage ICU patient with enhanced monitoring"""
        return {'actions_taken': ['icu_monitoring'], 'recommendations': ['Intensive care continued']}
    
    def _manage_isolation_patient(self, chart: AgentChart, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Manage isolation patient with security protocols"""
        return {'actions_taken': ['isolation_monitoring'], 'recommendations': ['Isolation protocols active']}

# API endpoint functions
def process_health_event_api(agent_id: str, metrics: Dict[str, float],
                           db_path: str = "agent_hospital.db") -> Dict[str, Any]:
    """
    Main API endpoint for processing agent health events
    
    POST /health_event
    { agent_id, metrics{} } → { actions_taken[], current_state, recommendations[] }
    """
    
    try:
        cma = ChiefMedicalAgent(db_path)
        result = cma.process_agent_health_event(agent_id, metrics)
        return result
        
    except Exception as e:
        logging.error(f"Health event API error for {agent_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

def get_hospital_census_api(db_path: str = "agent_hospital.db") -> Dict[str, Any]:
    """
    Get current hospital census
    
    GET /census → { census{}, statistics{} }
    """
    
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("""
                SELECT ward, state, COUNT(*) as patient_count,
                       AVG(julianday('now') - julianday(opened_at)) as avg_los_days
                FROM agent_chart
                WHERE state != 'DISCHARGED'
                GROUP BY ward, state
            """)
            
            census = []
            for row in cursor.fetchall():
                census.append({
                    'ward': row[0],
                    'state': row[1],
                    'patient_count': row[2],
                    'avg_length_of_stay_days': round(row[3], 1) if row[3] else 0
                })
            
            # Get summary statistics
            cursor = conn.execute("""
                SELECT 
                    COUNT(*) as total_active,
                    SUM(CASE WHEN state = 'ICU' THEN 1 ELSE 0 END) as icu_count,
                    SUM(CASE WHEN state = 'ISOLATION' THEN 1 ELSE 0 END) as isolation_count,
                    AVG(triage_score) as avg_triage_score
                FROM agent_chart
                WHERE state != 'DISCHARGED'
            """)
            
            stats_row = cursor.fetchone()
            statistics = {
                'total_active_patients': stats_row[0],
                'icu_patients': stats_row[1],
                'isolation_patients': stats_row[2],
                'average_triage_score': round(stats_row[3], 2) if stats_row[3] else 0
            }
        
        return {
            'success': True,
            'census': census,
            'statistics': statistics,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Census API error: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    # Test the Chief Medical Agent
    logging.basicConfig(level=logging.INFO)
    
    # Sample health event for testing
    test_metrics = {
        'abi': 0.82,  # High burnout - should trigger ICU
        'pg': -0.35,  # Poor performance
        'latency_z': 3.2,  # High latency
        'policy_flags': 3,  # Multiple violations
        'friction': 3.5,
        'uncertainty': 2.8,
        'eval_fail_rate': 0.22,
        'health_index': 0.15
    }
    
    # Test health event processing
    result = process_health_event_api("TEST_AGENT_CRITICAL_001", test_metrics)
    print("Chief Medical Agent Processing Result:")
    print(json.dumps(result, indent=2))
