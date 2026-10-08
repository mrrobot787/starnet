"""
Attending Physician Service - Root Cause Analysis and Treatment Planning
Performs comprehensive diagnostic assessment and selects appropriate interventions

Responsibilities:
- Analyze agent symptoms and metrics for root cause diagnosis
- Select appropriate treatments from formulary
- Set expected deltas and success criteria
- Create comprehensive treatment plans
- Coordinate with other clinical services
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
class DiagnosticAssessment:
    """Comprehensive diagnostic assessment"""
    agent_id: str
    admission_id: str
    primary_diagnosis: str
    differential_diagnoses: List[str]
    confidence: float
    symptoms_present: List[str]
    risk_factors: List[str]
    timeline: str
    reasoning: str
    recommended_treatments: List[str]

@dataclass
class TreatmentPlan:
    """Complete treatment plan with expected outcomes"""
    agent_id: str
    admission_id: str
    diagnoses: List[str]
    treatments: List[Dict[str, Any]]
    expected_deltas: Dict[str, float]
    risk_rating: str
    contraindications_checked: bool
    follow_up_hours: int
    success_criteria: List[str]

class AttendingPhysician:
    """Attending Physician service for diagnosis and treatment planning"""
    
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
        
        # Extract clinical knowledge
        self.diagnoses = self.ontology['diagnoses']
        self.treatments = self.ontology['treatments']
        self.symptoms = self.ontology['symptoms']
        
        self.logger.info("Attending Physician service initialized")
    
    def diagnose_agent(self, agent_id: str, chart_state: str, metrics: Dict[str, float], 
                      symptoms: List[str] = None, admission_id: str = None) -> DiagnosticAssessment:
        """
        Perform comprehensive diagnostic assessment
        
        Args:
            agent_id: Agent identifier
            chart_state: Current chart state
            metrics: Latest agent metrics
            symptoms: Identified symptoms from triage
            admission_id: Admission ID if available
            
        Returns:
            DiagnosticAssessment with diagnosis and recommendations
        """
        self.logger.info(f"Diagnosing agent {agent_id}")
        
        # Get historical context
        historical_context = self._get_historical_context(agent_id)
        
        # Identify symptoms if not provided
        if symptoms is None:
            symptoms = self._identify_symptoms(metrics)
        
        # Assess risk factors
        risk_factors = self._assess_risk_factors(agent_id, metrics, historical_context)
        
        # Generate differential diagnoses
        differential_diagnoses = self._generate_differential_diagnoses(symptoms, risk_factors, metrics)
        
        # Select primary diagnosis
        primary_diagnosis, confidence = self._select_primary_diagnosis(
            differential_diagnoses, symptoms, risk_factors, metrics, historical_context
        )
        
        # Analyze timeline
        timeline = self._analyze_timeline(agent_id, symptoms, historical_context)
        
        # Generate clinical reasoning
        reasoning = self._generate_reasoning(primary_diagnosis, symptoms, risk_factors, metrics)
        
        # Recommend treatments
        recommended_treatments = self._recommend_treatments(primary_diagnosis, symptoms, metrics)
        
        assessment = DiagnosticAssessment(
            agent_id=agent_id,
            admission_id=admission_id or f"ADM_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{agent_id}",
            primary_diagnosis=primary_diagnosis,
            differential_diagnoses=differential_diagnoses,
            confidence=confidence,
            symptoms_present=symptoms,
            risk_factors=risk_factors,
            timeline=timeline,
            reasoning=reasoning,
            recommended_treatments=recommended_treatments
        )
        
        # Store assessment
        self._store_assessment(assessment)
        
        # Log diagnostic event
        self._log_diagnostic_event(assessment, metrics)
        
        self.logger.info(f"Diagnosis complete for {agent_id}: {primary_diagnosis} (confidence: {confidence:.2f})")
        return assessment
    
    def create_treatment_plan(self, assessment: DiagnosticAssessment, 
                            agent_role: str = None) -> TreatmentPlan:
        """
        Create comprehensive treatment plan based on diagnosis
        
        Args:
            assessment: Diagnostic assessment
            agent_role: Agent role for contraindication checking
            
        Returns:
            TreatmentPlan with detailed treatment orders
        """
        self.logger.info(f"Creating treatment plan for {assessment.agent_id}")
        
        # Get agent role if not provided
        if agent_role is None:
            agent_role = self._get_agent_role(assessment.agent_id)
        
        # Select treatments based on diagnosis and symptoms
        selected_treatments = self._select_treatments(
            assessment.primary_diagnosis, 
            assessment.symptoms_present,
            agent_role
        )
        
        # Calculate expected deltas
        expected_deltas = self._calculate_expected_deltas(selected_treatments, assessment)
        
        # Assess risk rating
        risk_rating = self._assess_treatment_risk(selected_treatments, agent_role)
        
        # Determine follow-up schedule
        follow_up_hours = self._determine_follow_up_schedule(
            assessment.primary_diagnosis, 
            selected_treatments, 
            risk_rating
        )
        
        # Define success criteria
        success_criteria = self._define_success_criteria(assessment, expected_deltas)
        
        treatment_plan = TreatmentPlan(
            agent_id=assessment.agent_id,
            admission_id=assessment.admission_id,
            diagnoses=[assessment.primary_diagnosis] + assessment.differential_diagnoses[:2],
            treatments=selected_treatments,
            expected_deltas=expected_deltas,
            risk_rating=risk_rating,
            contraindications_checked=True,
            follow_up_hours=follow_up_hours,
            success_criteria=success_criteria
        )
        
        self.logger.info(f"Treatment plan created for {assessment.agent_id}: {len(selected_treatments)} treatments")
        return treatment_plan
    
    def _get_historical_context(self, agent_id: str) -> Dict[str, Any]:
        """Get historical context for the agent"""
        context = {
            'previous_admissions': [],
            'previous_diagnoses': [],
            'treatment_history': [],
            'baseline_metrics': {}
        }
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Previous admissions
                cursor = conn.execute("""
                    SELECT admission_id, state, opened_at, closed_at, admission_reason
                    FROM agent_chart 
                    WHERE agent_id = ? 
                    ORDER BY opened_at DESC 
                    LIMIT 5
                """, (agent_id,))
                
                context['previous_admissions'] = [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in cursor.fetchall()
                ]
                
                # Previous diagnoses
                cursor = conn.execute("""
                    SELECT da.primary_diagnosis, da.confidence, da.assessed_at
                    FROM diagnostic_assessment da
                    JOIN agent_chart ac ON da.admission_id = ac.admission_id
                    WHERE ac.agent_id = ?
                    ORDER BY da.assessed_at DESC
                    LIMIT 10
                """, (agent_id,))
                
                context['previous_diagnoses'] = [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in cursor.fetchall()
                ]
                
                # Treatment history
                cursor = conn.execute("""
                    SELECT co.treatments, cou.success_bool, cou.abi_delta, cou.pg_delta
                    FROM clinical_order co
                    JOIN clinical_outcome cou ON co.order_id = cou.order_id
                    WHERE co.agent_id = ? AND cou.window_hours = 24
                    ORDER BY co.created_at DESC
                    LIMIT 10
                """, (agent_id,))
                
                context['treatment_history'] = [
                    dict(zip([col[0] for col in cursor.description], row))
                    for row in cursor.fetchall()
                ]
                
                # Baseline metrics (30-day average)
                cursor = conn.execute("""
                    SELECT AVG(abi) as avg_abi, AVG(pg) as avg_pg, 
                           AVG(health_index) as avg_health_index,
                           AVG(friction) as avg_friction, AVG(uncertainty) as avg_uncertainty
                    FROM agent_health_metrics
                    WHERE agent_id = ? AND measured_at > datetime('now', '-30 days')
                """, (agent_id,))
                
                row = cursor.fetchone()
                if row:
                    context['baseline_metrics'] = dict(zip([col[0] for col in cursor.description], row))
                
        except Exception as e:
            self.logger.warning(f"Could not get historical context for {agent_id}: {e}")
        
        return context
    
    def _identify_symptoms(self, metrics: Dict[str, float]) -> List[str]:
        """Identify symptoms from metrics (enhanced version of triage logic)"""
        symptoms = []
        
        # More sophisticated symptom detection
        symptom_thresholds = {
            'Friction': {'metrics': ['friction', 'task_retry_rate'], 'threshold': 2.0},
            'Uncertainty': {'metrics': ['uncertainty', 'confidence_score'], 'threshold': -1.5},
            'Conflict': {'metrics': ['conflict', 'policy_violations'], 'threshold': 1.5},
            'LatencyZ': {'metrics': ['latency_z', 'response_time_p95'], 'threshold': 2.0},
            'Eval_fail_rate': {'metrics': ['eval_fail_rate', 'eval_accuracy'], 'threshold': 2.0},
            'Policy_flags': {'metrics': ['policy_flags', 'policy_violations'], 'threshold': 0.5}
        }
        
        for symptom, config in symptom_thresholds.items():
            for metric_name in config['metrics']:
                if metric_name in metrics:
                    value = metrics[metric_name]
                    
                    # Apply threshold logic
                    if symptom in ['Uncertainty'] and 'confidence' in metric_name:
                        if value < config['threshold']:
                            symptoms.append(symptom)
                            break
                    elif value > config['threshold']:
                        symptoms.append(symptom)
                        break
        
        return symptoms
    
    def _assess_risk_factors(self, agent_id: str, metrics: Dict[str, float], 
                           historical_context: Dict[str, Any]) -> List[str]:
        """Assess comprehensive risk factors"""
        risk_factors = []
        
        # Historical risk factors
        if len(historical_context['previous_admissions']) > 2:
            risk_factors.append('frequent_admissions')
        
        if len(set(d['primary_diagnosis'] for d in historical_context['previous_diagnoses'])) > 3:
            risk_factors.append('multiple_diagnoses')
        
        # Treatment resistance
        failed_treatments = [t for t in historical_context['treatment_history'] if not t.get('success_bool', True)]
        if len(failed_treatments) > 2:
            risk_factors.append('treatment_resistance')
        
        # Current metric-based risk factors
        if metrics.get('abi', 0) > 0.7:
            risk_factors.append('high_burnout_risk')
        
        if metrics.get('policy_flags', 0) > 2:
            risk_factors.append('compliance_risk')
        
        if metrics.get('eval_fail_rate', 0) > 0.2:
            risk_factors.append('performance_decline')
        
        # Baseline deviation
        baseline = historical_context.get('baseline_metrics', {})
        if baseline.get('avg_abi'):
            abi_change = metrics.get('abi', 0) - baseline['avg_abi']
            if abi_change > 0.3:
                risk_factors.append('rapid_deterioration')
        
        return risk_factors
    
    def _generate_differential_diagnoses(self, symptoms: List[str], risk_factors: List[str], 
                                       metrics: Dict[str, float]) -> List[str]:
        """Generate differential diagnoses based on symptoms and risk factors"""
        differential = []
        
        for diagnosis_name, diagnosis_config in self.diagnoses.items():
            score = self._calculate_diagnosis_score(
                diagnosis_name, diagnosis_config, symptoms, risk_factors, metrics
            )
            
            if score > 0.3:  # Threshold for consideration
                differential.append((diagnosis_name, score))
        
        # Sort by score and return top candidates
        differential.sort(key=lambda x: x[1], reverse=True)
        return [d[0] for d in differential[:5]]
    
    def _calculate_diagnosis_score(self, diagnosis_name: str, diagnosis_config: Dict,
                                 symptoms: List[str], risk_factors: List[str], 
                                 metrics: Dict[str, float]) -> float:
        """Calculate likelihood score for a diagnosis"""
        score = 0.0
        
        # Primary symptoms match
        primary_symptoms = diagnosis_config.get('primary_symptoms', [])
        primary_matches = len(set(symptoms) & set(primary_symptoms))
        score += primary_matches * 0.4
        
        # Secondary symptoms match
        secondary_symptoms = diagnosis_config.get('secondary_symptoms', [])
        secondary_matches = len(set(symptoms) & set(secondary_symptoms))
        score += secondary_matches * 0.2
        
        # Risk factors match
        diagnosis_risk_factors = diagnosis_config.get('risk_factors', [])
        risk_matches = len(set(risk_factors) & set(diagnosis_risk_factors))
        score += risk_matches * 0.3
        
        # Specific metric patterns
        if diagnosis_name == 'CapacityOverload' and metrics.get('latency_z', 0) > 2:
            score += 0.3
        elif diagnosis_name == 'DataDrift' and metrics.get('eval_fail_rate', 0) > 0.15:
            score += 0.3
        elif diagnosis_name == 'PromptDrift' and metrics.get('uncertainty', 0) > 2:
            score += 0.3
        
        return min(score, 1.0)
    
    def _select_primary_diagnosis(self, differential_diagnoses: List[str], symptoms: List[str],
                                risk_factors: List[str], metrics: Dict[str, float],
                                historical_context: Dict[str, Any]) -> Tuple[str, float]:
        """Select primary diagnosis with confidence score"""
        
        if not differential_diagnoses:
            return "UnspecifiedAgentDistress", 0.5
        
        primary = differential_diagnoses[0]
        
        # Calculate confidence based on symptom clarity and historical consistency
        confidence = 0.6  # Base confidence
        
        # Boost confidence for clear symptom patterns
        primary_config = self.diagnoses.get(primary, {})
        primary_symptoms = primary_config.get('primary_symptoms', [])
        symptom_match_ratio = len(set(symptoms) & set(primary_symptoms)) / max(len(primary_symptoms), 1)
        confidence += symptom_match_ratio * 0.3
        
        # Boost confidence for historical consistency
        previous_diagnoses = [d['primary_diagnosis'] for d in historical_context['previous_diagnoses']]
        if primary in previous_diagnoses:
            confidence += 0.1
        
        # Reduce confidence if multiple strong differentials
        if len(differential_diagnoses) > 1:
            confidence -= 0.1
        
        return primary, min(confidence, 0.95)
    
    def _analyze_timeline(self, agent_id: str, symptoms: List[str], 
                         historical_context: Dict[str, Any]) -> str:
        """Analyze symptom onset and progression timeline"""
        
        # Simple timeline analysis based on historical data
        if historical_context['previous_admissions']:
            last_admission = historical_context['previous_admissions'][0]
            days_since_last = (datetime.now() - datetime.fromisoformat(last_admission['opened_at'].replace('Z', '+00:00'))).days
            
            if days_since_last < 7:
                return f"Acute onset - {days_since_last} days since last admission"
            elif days_since_last < 30:
                return f"Subacute progression - {days_since_last} days since last admission"
            else:
                return "Chronic or new onset - no recent admissions"
        
        return "New onset - no previous admission history"
    
    def _generate_reasoning(self, primary_diagnosis: str, symptoms: List[str],
                          risk_factors: List[str], metrics: Dict[str, float]) -> str:
        """Generate clinical reasoning for the diagnosis"""
        
        reasoning_parts = []
        
        # Primary diagnosis rationale
        diagnosis_config = self.diagnoses.get(primary_diagnosis, {})
        reasoning_parts.append(f"Primary diagnosis of {primary_diagnosis} based on:")
        
        # Symptom evidence
        primary_symptoms = diagnosis_config.get('primary_symptoms', [])
        matching_symptoms = set(symptoms) & set(primary_symptoms)
        if matching_symptoms:
            reasoning_parts.append(f"- Primary symptoms present: {', '.join(matching_symptoms)}")
        
        # Risk factor evidence
        diagnosis_risk_factors = diagnosis_config.get('risk_factors', [])
        matching_risk_factors = set(risk_factors) & set(diagnosis_risk_factors)
        if matching_risk_factors:
            reasoning_parts.append(f"- Risk factors present: {', '.join(matching_risk_factors)}")
        
        # Metric evidence
        if metrics.get('abi', 0) > 0.6:
            reasoning_parts.append(f"- Elevated burnout index: {metrics.get('abi', 0):.3f}")
        
        if metrics.get('latency_z', 0) > 2:
            reasoning_parts.append(f"- Performance degradation: latency z-score {metrics.get('latency_z', 0):.2f}")
        
        return "\n".join(reasoning_parts)
    
    def _recommend_treatments(self, primary_diagnosis: str, symptoms: List[str], 
                            metrics: Dict[str, float]) -> List[str]:
        """Recommend treatments based on diagnosis and symptoms"""
        
        # Treatment selection logic based on diagnosis
        treatment_map = {
            'CapacityOverload': ['LoadShedding', 'PeerCheck'],
            'DataDrift': ['RetrievalRefresh', 'EvidenceFirst'],
            'PromptDrift': ['PromptPinning', 'EvidenceFirst'],
            'ToolMisuse': ['ToolsetPruning', 'CurriculumStepDown'],
            'UnderChallenge': ['CurriculumStepUp'],
            'Misrouting': ['DomainReassignment'],
            'EvaluationLeakage': ['MemoryHygiene', 'CanaryGating'],
            'RetrievalStaleness': ['RetrievalRefresh']
        }
        
        recommended = treatment_map.get(primary_diagnosis, ['EvidenceFirst', 'LoadShedding'])
        
        # Add symptom-specific treatments
        if 'LatencyZ' in symptoms:
            recommended.append('LoadShedding')
        
        if 'Policy_flags' in symptoms:
            recommended.append('EvidenceFirst')
        
        if 'Uncertainty' in symptoms:
            recommended.append('PeerCheck')
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(recommended))
    
    def _select_treatments(self, primary_diagnosis: str, symptoms: List[str], 
                         agent_role: str) -> List[Dict[str, Any]]:
        """Select and configure specific treatments"""
        
        recommended_names = self._recommend_treatments(primary_diagnosis, symptoms, {})
        selected_treatments = []
        
        for treatment_name in recommended_names:
            if treatment_name in self.treatments:
                treatment_config = self.treatments[treatment_name]
                
                # Check contraindications
                if self._check_contraindications(treatment_name, agent_role):
                    continue
                
                # Configure treatment parameters
                treatment = {
                    'name': treatment_name,
                    'description': treatment_config['description'],
                    'parameters': self._configure_treatment_parameters(treatment_name, treatment_config),
                    'expected_effects': treatment_config.get('expected_effects', {}),
                    'risk_level': treatment_config.get('risk_level', 'medium'),
                    'duration': treatment_config.get('duration', 'varies')
                }
                
                selected_treatments.append(treatment)
        
        return selected_treatments
    
    def _check_contraindications(self, treatment_name: str, agent_role: str) -> bool:
        """Check if treatment is contraindicated for agent role"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT rule FROM contraindication
                    WHERE agent_role = ? AND treatment_name = ?
                """, (agent_role, treatment_name))
                
                contraindication = cursor.fetchone()
                if contraindication and contraindication[0] == 'forbidden':
                    return True
                    
        except Exception as e:
            self.logger.warning(f"Could not check contraindications: {e}")
        
        return False
    
    def _configure_treatment_parameters(self, treatment_name: str, 
                                      treatment_config: Dict) -> Dict[str, Any]:
        """Configure treatment parameters within safe bounds"""
        
        parameters = {}
        param_config = treatment_config.get('parameters', {})
        
        for param_name, param_spec in param_config.items():
            if isinstance(param_spec, dict):
                if 'default' in param_spec:
                    parameters[param_name] = param_spec['default']
                elif 'min' in param_spec and 'max' in param_spec:
                    # Use middle of range as default
                    parameters[param_name] = (param_spec['min'] + param_spec['max']) / 2
            else:
                parameters[param_name] = param_spec
        
        return parameters
    
    def _calculate_expected_deltas(self, treatments: List[Dict[str, Any]], 
                                 assessment: DiagnosticAssessment) -> Dict[str, float]:
        """Calculate expected metric deltas from treatments"""
        
        expected_deltas = {
            'abi': 0.0,
            'pg': 0.0,
            'health_index': 0.0,
            'friction': 0.0,
            'uncertainty': 0.0,
            'latency_z': 0.0,
            'policy_flags': 0.0
        }
        
        for treatment in treatments:
            expected_effects = treatment.get('expected_effects', {})
            
            for metric, effect in expected_effects.items():
                if isinstance(effect, dict) and 'delta' in effect:
                    expected_deltas[metric.lower()] += effect['delta']
                elif isinstance(effect, (int, float)):
                    expected_deltas[metric.lower()] += effect
        
        return expected_deltas
    
    def _assess_treatment_risk(self, treatments: List[Dict[str, Any]], agent_role: str) -> str:
        """Assess overall risk rating for treatment plan"""
        
        risk_levels = {'low': 1, 'medium': 2, 'high': 3, 'critical': 4}
        max_risk = 1
        
        for treatment in treatments:
            risk_level = treatment.get('risk_level', 'medium')
            max_risk = max(max_risk, risk_levels.get(risk_level, 2))
        
        # Increase risk for sensitive roles
        if agent_role in ['SEC', 'FINANCIAL']:
            max_risk = min(max_risk + 1, 4)
        
        risk_names = {1: 'LOW', 2: 'MEDIUM', 3: 'HIGH', 4: 'CRITICAL'}
        return risk_names[max_risk]
    
    def _determine_follow_up_schedule(self, primary_diagnosis: str, treatments: List[Dict[str, Any]], 
                                    risk_rating: str) -> int:
        """Determine follow-up schedule in hours"""
        
        # Base schedule by risk
        base_hours = {'LOW': 12, 'MEDIUM': 6, 'HIGH': 4, 'CRITICAL': 2}
        follow_up_hours = base_hours.get(risk_rating, 6)
        
        # Adjust for diagnosis
        if primary_diagnosis in ['EvaluationLeakage', 'CapacityOverload']:
            follow_up_hours = min(follow_up_hours, 2)  # More frequent monitoring
        
        return follow_up_hours
    
    def _define_success_criteria(self, assessment: DiagnosticAssessment, 
                               expected_deltas: Dict[str, float]) -> List[str]:
        """Define success criteria for treatment plan"""
        
        criteria = []
        
        # ABI improvement
        if expected_deltas.get('abi', 0) < -0.1:
            criteria.append(f"ABI reduction of at least {abs(expected_deltas['abi']):.2f}")
        
        # Performance improvement
        if expected_deltas.get('pg', 0) > 0.1:
            criteria.append(f"Performance gradient improvement of at least {expected_deltas['pg']:.2f}")
        
        # Symptom resolution
        if 'Policy_flags' in assessment.symptoms_present:
            criteria.append("Policy violations reduced to zero")
        
        if 'LatencyZ' in assessment.symptoms_present:
            criteria.append("Latency z-score below 1.0")
        
        # General criteria
        criteria.extend([
            "No new symptoms emergence",
            "Stable metrics for 24 hours",
            "No adverse treatment effects"
        ])
        
        return criteria
    
    def _get_agent_role(self, agent_id: str) -> str:
        """Get agent role (placeholder - would integrate with agent registry)"""
        # This would integrate with your agent registry system
        # For now, return a default
        return "GENERAL"
    
    def _store_assessment(self, assessment: DiagnosticAssessment):
        """Store diagnostic assessment in database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                assessment_id = f"ASSESS_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{assessment.agent_id}"
                
                conn.execute("""
                    INSERT INTO diagnostic_assessment
                    (assessment_id, agent_id, admission_id, primary_diagnosis, 
                     differential_diagnoses, confidence, symptoms_present, risk_factors,
                     timeline, reasoning, recommended_treatments, assessed_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'attending_physician')
                """, (
                    assessment_id,
                    assessment.agent_id,
                    assessment.admission_id,
                    assessment.primary_diagnosis,
                    json.dumps(assessment.differential_diagnoses),
                    assessment.confidence,
                    json.dumps(assessment.symptoms_present),
                    json.dumps(assessment.risk_factors),
                    assessment.timeline,
                    assessment.reasoning,
                    json.dumps(assessment.recommended_treatments)
                ))
                
                conn.commit()
                self.logger.info(f"Stored diagnostic assessment {assessment_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to store assessment for {assessment.agent_id}: {e}")
    
    def _log_diagnostic_event(self, assessment: DiagnosticAssessment, metrics: Dict[str, float]):
        """Log diagnostic event for audit trail"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                event_id = f"DIAG_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{assessment.agent_id}"
                
                payload = {
                    'assessment': asdict(assessment),
                    'input_metrics': metrics,
                    'diagnostic_reasoning': assessment.reasoning
                }
                
                conn.execute("""
                    INSERT INTO hospital_event 
                    (event_id, event_type, agent_id, admission_id, payload_json, 
                     created_by, source_system)
                    VALUES (?, 'diagnosis', ?, ?, ?, 'attending_physician', 'agent_hospital')
                """, (
                    event_id,
                    assessment.agent_id,
                    assessment.admission_id,
                    json.dumps(payload)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to log diagnostic event for {assessment.agent_id}: {e}")

# API endpoint functions
def diagnose_agent_api(agent_id: str, chart_state: str, metrics: Dict[str, float],
                      symptoms: List[str] = None, admission_id: str = None,
                      db_path: str = "agent_hospital.db") -> Dict[str, Any]:
    """
    API endpoint for agent diagnosis
    
    POST /diagnose
    { agent_id, chart_state, metrics{} } → { diagnoses[], differential[], confidence }
    """
    
    try:
        attending = AttendingPhysician(db_path)
        assessment = attending.diagnose_agent(agent_id, chart_state, metrics, symptoms, admission_id)
        
        return {
            'success': True,
            'primary_diagnosis': assessment.primary_diagnosis,
            'differential_diagnoses': assessment.differential_diagnoses,
            'confidence': assessment.confidence,
            'symptoms_present': assessment.symptoms_present,
            'risk_factors': assessment.risk_factors,
            'timeline': assessment.timeline,
            'reasoning': assessment.reasoning,
            'recommended_treatments': assessment.recommended_treatments,
            'admission_id': assessment.admission_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Diagnosis API error for {agent_id}: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

def create_treatment_plan_api(assessment_data: Dict[str, Any], agent_role: str = None,
                             db_path: str = "agent_hospital.db") -> Dict[str, Any]:
    """
    API endpoint for treatment plan creation
    
    POST /treatment_plan
    { assessment_data, agent_role } → { treatment_plan }
    """
    
    try:
        attending = AttendingPhysician(db_path)
        
        # Reconstruct assessment from data
        assessment = DiagnosticAssessment(**assessment_data)
        
        treatment_plan = attending.create_treatment_plan(assessment, agent_role)
        
        return {
            'success': True,
            'treatment_plan': asdict(treatment_plan),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Treatment plan API error: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    # Test the attending physician
    logging.basicConfig(level=logging.INFO)
    
    # Sample metrics and symptoms for testing
    test_metrics = {
        'abi': 0.75,
        'pg': -0.25,
        'latency_z': 2.8,
        'policy_flags': 2,
        'friction': 3.1,
        'uncertainty': 2.3,
        'eval_fail_rate': 0.18
    }
    
    test_symptoms = ['LatencyZ', 'Policy_flags', 'Uncertainty']
    
    # Test diagnosis
    result = diagnose_agent_api("TEST_AGENT_001", "ADMITTED", test_metrics, test_symptoms)
    print("Diagnostic Assessment Result:")
    print(json.dumps(result, indent=2))
