"""
Pharmacist Service - Treatment Validation and Safety Checks
Validates interventions against policy, checks contraindications, and ensures safe dosing

Responsibilities:
- Validate treatment parameters against safe bounds
- Check contraindications for agent roles
- Assess drug interactions and conflicts
- Ensure compliance with governance policies
- Monitor for adverse effects
"""

import json
import sqlite3
import logging
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
import yaml

@dataclass
class ValidationResult:
    """Treatment validation result"""
    order_id: str
    validation_status: str  # approved, rejected, conditional
    violations: List[str]
    parameters_valid: bool
    dosage_appropriate: bool
    interaction_check: bool
    risk_level: str
    risk_factors: List[str]
    monitoring_required: bool
    monitoring_plan: Optional[str]
    notes: str

class Pharmacist:
    """Pharmacist service for treatment validation and safety"""
    
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
        
        # Extract treatment and contraindication data
        self.treatments = self.ontology['treatments']
        self.role_contraindications = self.ontology['role_contraindications']
        
        self.logger.info("Pharmacist service initialized")
    
    def validate_treatment_order(self, order_json: str, agent_role: str) -> ValidationResult:
        """
        Validate complete treatment order for safety and compliance
        
        Args:
            order_json: JSON string of the treatment order
            agent_role: Agent role for contraindication checking
            
        Returns:
            ValidationResult with approval/rejection decision
        """
        try:
            order = json.loads(order_json)
        except json.JSONDecodeError as e:
            return ValidationResult(
                order_id="INVALID",
                validation_status="rejected",
                violations=[f"Invalid JSON format: {e}"],
                parameters_valid=False,
                dosage_appropriate=False,
                interaction_check=False,
                risk_level="CRITICAL",
                risk_factors=["invalid_order_format"],
                monitoring_required=False,
                monitoring_plan=None,
                notes="Order rejected due to invalid format"
            )
        
        order_id = order.get('order_id', 'UNKNOWN')
        self.logger.info(f"Validating treatment order {order_id}")
        
        violations = []
        risk_factors = []
        
        # Extract regimen from order
        regimen = order.get('regimen', [])
        if not regimen:
            violations.append("No treatments specified in regimen")
        
        # Validate each treatment in the regimen
        parameters_valid = True
        dosage_appropriate = True
        
        for treatment in regimen:
            treatment_name = treatment.get('tx', '')
            treatment_params = treatment.get('params', {})
            
            # Check if treatment exists in formulary
            if treatment_name not in self.treatments:
                violations.append(f"Unknown treatment: {treatment_name}")
                parameters_valid = False
                continue
            
            # Validate parameters
            param_validation = self._validate_treatment_parameters(treatment_name, treatment_params)
            if not param_validation['valid']:
                violations.extend(param_validation['violations'])
                parameters_valid = False
            
            # Check dosage appropriateness
            dosage_check = self._check_dosage_appropriateness(treatment_name, treatment_params)
            if not dosage_check['appropriate']:
                violations.extend(dosage_check['violations'])
                dosage_appropriate = False
            
            # Check contraindications
            contraindication_check = self._check_contraindications(treatment_name, agent_role)
            if contraindication_check['contraindicated']:
                violations.extend(contraindication_check['violations'])
        
        # Check for treatment interactions
        interaction_check = self._check_treatment_interactions(regimen)
        if not interaction_check['safe']:
            violations.extend(interaction_check['violations'])
            risk_factors.extend(interaction_check['risk_factors'])
        
        # Assess overall risk level
        risk_level = self._assess_overall_risk(regimen, agent_role, violations)
        
        # Determine validation status
        if violations:
            if any('forbidden' in v.lower() or 'critical' in v.lower() for v in violations):
                validation_status = "rejected"
            else:
                validation_status = "conditional"
        else:
            validation_status = "approved"
        
        # Determine monitoring requirements
        monitoring_required, monitoring_plan = self._determine_monitoring_requirements(
            regimen, risk_level, agent_role
        )
        
        # Generate notes
        notes = self._generate_validation_notes(
            validation_status, violations, risk_level, monitoring_required
        )
        
        result = ValidationResult(
            order_id=order_id,
            validation_status=validation_status,
            violations=violations,
            parameters_valid=parameters_valid,
            dosage_appropriate=dosage_appropriate,
            interaction_check=interaction_check['safe'],
            risk_level=risk_level,
            risk_factors=risk_factors,
            monitoring_required=monitoring_required,
            monitoring_plan=monitoring_plan,
            notes=notes
        )
        
        # Store validation result
        self._store_validation_result(result)
        
        # Log validation event
        self._log_validation_event(result, order)
        
        self.logger.info(f"Validation complete for {order_id}: {validation_status}")
        return result
    
    def _validate_treatment_parameters(self, treatment_name: str, 
                                     parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Validate treatment parameters against safe bounds"""
        
        treatment_config = self.treatments.get(treatment_name, {})
        param_specs = treatment_config.get('parameters', {})
        
        violations = []
        
        for param_name, param_value in parameters.items():
            if param_name not in param_specs:
                violations.append(f"Unknown parameter '{param_name}' for treatment {treatment_name}")
                continue
            
            param_spec = param_specs[param_name]
            
            # Validate parameter value against specification
            if isinstance(param_spec, dict):
                # Check type constraints
                if 'type' in param_spec:
                    expected_type = param_spec['type']
                    if expected_type == 'boolean' and not isinstance(param_value, bool):
                        violations.append(f"Parameter '{param_name}' must be boolean")
                    elif expected_type == 'string' and not isinstance(param_value, str):
                        violations.append(f"Parameter '{param_name}' must be string")
                
                # Check range constraints
                if 'min' in param_spec and isinstance(param_value, (int, float)):
                    if param_value < param_spec['min']:
                        violations.append(f"Parameter '{param_name}' below minimum: {param_value} < {param_spec['min']}")
                
                if 'max' in param_spec and isinstance(param_value, (int, float)):
                    if param_value > param_spec['max']:
                        violations.append(f"Parameter '{param_name}' above maximum: {param_value} > {param_spec['max']}")
                
                # Check options constraints
                if 'options' in param_spec:
                    if param_value not in param_spec['options']:
                        violations.append(f"Parameter '{param_name}' not in allowed options: {param_spec['options']}")
        
        # Check for required parameters
        for param_name, param_spec in param_specs.items():
            if isinstance(param_spec, dict) and param_spec.get('required', False):
                if param_name not in parameters:
                    violations.append(f"Required parameter '{param_name}' missing for treatment {treatment_name}")
        
        return {
            'valid': len(violations) == 0,
            'violations': violations
        }
    
    def _check_dosage_appropriateness(self, treatment_name: str, 
                                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Check if treatment dosage/intensity is appropriate"""
        
        violations = []
        treatment_config = self.treatments.get(treatment_name, {})
        
        # Check for excessive dosing patterns
        if treatment_name == 'LoadShedding':
            max_parallel = parameters.get('max_parallel', 4)
            if max_parallel < 1:
                violations.append("LoadShedding max_parallel too restrictive (< 1)")
        
        elif treatment_name == 'PeerCheck':
            quorum = parameters.get('quorum', 3)
            if quorum > 5:
                violations.append("PeerCheck quorum too high (> 5) - may cause delays")
        
        elif treatment_name == 'CurriculumStepUp':
            complexity_increase = parameters.get('complexity_increase', 0.2)
            if complexity_increase > 0.4:
                violations.append("CurriculumStepUp increase too aggressive (> 0.4)")
        
        elif treatment_name == 'CanaryGating':
            canary_pct = parameters.get('canary_pct', 0.2)
            if canary_pct > 0.5:
                violations.append("CanaryGating percentage too high (> 50%)")
        
        return {
            'appropriate': len(violations) == 0,
            'violations': violations
        }
    
    def _check_contraindications(self, treatment_name: str, agent_role: str) -> Dict[str, Any]:
        """Check contraindications for treatment and agent role"""
        
        violations = []
        
        # Check role-based contraindications from ontology
        role_restrictions = self.role_contraindications.get(agent_role, {})
        
        forbidden_treatments = role_restrictions.get('forbidden_treatments', [])
        if treatment_name in forbidden_treatments:
            violations.append(f"Treatment {treatment_name} forbidden for role {agent_role}")
        
        # Check database contraindications
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT rule, condition_json FROM contraindication
                    WHERE agent_role = ? AND treatment_name = ?
                """, (agent_role, treatment_name))
                
                for rule, condition_json in cursor.fetchall():
                    if rule == 'forbidden':
                        violations.append(f"Treatment {treatment_name} forbidden for role {agent_role} by policy")
                    elif rule == 'requires_approval':
                        violations.append(f"Treatment {treatment_name} requires additional approval for role {agent_role}")
                    elif rule == 'conditional':
                        # Would check conditions here
                        pass
                        
        except Exception as e:
            self.logger.warning(f"Could not check database contraindications: {e}")
        
        return {
            'contraindicated': len(violations) > 0,
            'violations': violations
        }
    
    def _check_treatment_interactions(self, regimen: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Check for harmful interactions between treatments"""
        
        violations = []
        risk_factors = []
        
        treatment_names = [t.get('tx', '') for t in regimen]
        
        # Define known interactions
        interactions = {
            ('LoadShedding', 'CurriculumStepUp'): {
                'severity': 'moderate',
                'description': 'Load shedding may interfere with curriculum progression'
            },
            ('ToolsetPruning', 'CurriculumStepUp'): {
                'severity': 'high',
                'description': 'Removing tools while increasing complexity may cause failures'
            },
            ('PromptPinning', 'CurriculumStepUp'): {
                'severity': 'moderate',
                'description': 'Fixed prompts may not adapt to increased complexity'
            }
        }
        
        # Check for interactions
        for i, treatment1 in enumerate(treatment_names):
            for treatment2 in treatment_names[i+1:]:
                interaction_key = tuple(sorted([treatment1, treatment2]))
                
                if interaction_key in interactions:
                    interaction = interactions[interaction_key]
                    severity = interaction['severity']
                    description = interaction['description']
                    
                    if severity == 'high':
                        violations.append(f"High-risk interaction: {description}")
                    else:
                        risk_factors.append(f"{severity.title()} interaction: {description}")
        
        # Check for excessive polypharmacy
        if len(treatment_names) > 4:
            violations.append(f"Too many concurrent treatments ({len(treatment_names)} > 4)")
        
        return {
            'safe': len(violations) == 0,
            'violations': violations,
            'risk_factors': risk_factors
        }
    
    def _assess_overall_risk(self, regimen: List[Dict[str, Any]], agent_role: str, 
                           violations: List[str]) -> str:
        """Assess overall risk level for the treatment plan"""
        
        # Start with base risk
        risk_score = 1  # 1=low, 2=medium, 3=high, 4=critical
        
        # Increase risk for violations
        if violations:
            if any('forbidden' in v.lower() for v in violations):
                risk_score = 4
            elif any('high-risk' in v.lower() for v in violations):
                risk_score = max(risk_score, 3)
            else:
                risk_score = max(risk_score, 2)
        
        # Increase risk for high-risk treatments
        for treatment in regimen:
            treatment_name = treatment.get('tx', '')
            if treatment_name in self.treatments:
                treatment_risk = self.treatments[treatment_name].get('risk_level', 'medium')
                if treatment_risk == 'high':
                    risk_score = max(risk_score, 3)
                elif treatment_risk == 'critical':
                    risk_score = 4
        
        # Increase risk for sensitive roles
        if agent_role in ['SEC', 'FINANCIAL']:
            risk_score = min(risk_score + 1, 4)
        
        risk_levels = {1: 'LOW', 2: 'MEDIUM', 3: 'HIGH', 4: 'CRITICAL'}
        return risk_levels[risk_score]
    
    def _determine_monitoring_requirements(self, regimen: List[Dict[str, Any]], 
                                         risk_level: str, agent_role: str) -> Tuple[bool, Optional[str]]:
        """Determine if monitoring is required and create monitoring plan"""
        
        monitoring_required = False
        monitoring_plan_parts = []
        
        # Risk-based monitoring
        if risk_level in ['HIGH', 'CRITICAL']:
            monitoring_required = True
            monitoring_plan_parts.append(f"Enhanced monitoring due to {risk_level} risk level")
        
        # Treatment-specific monitoring
        for treatment in regimen:
            treatment_name = treatment.get('tx', '')
            
            if treatment_name == 'CurriculumStepUp':
                monitoring_required = True
                monitoring_plan_parts.append("Monitor task completion rates and error patterns")
            
            elif treatment_name == 'ToolsetPruning':
                monitoring_required = True
                monitoring_plan_parts.append("Monitor for task failures due to missing tools")
            
            elif treatment_name == 'DomainReassignment':
                monitoring_required = True
                monitoring_plan_parts.append("Monitor adaptation to new domain and performance metrics")
        
        # Role-specific monitoring
        if agent_role in ['SEC', 'FINANCIAL']:
            monitoring_required = True
            monitoring_plan_parts.append(f"Enhanced monitoring for {agent_role} role compliance")
        
        monitoring_plan = "; ".join(monitoring_plan_parts) if monitoring_plan_parts else None
        
        return monitoring_required, monitoring_plan
    
    def _generate_validation_notes(self, validation_status: str, violations: List[str],
                                 risk_level: str, monitoring_required: bool) -> str:
        """Generate comprehensive validation notes"""
        
        notes_parts = []
        
        if validation_status == "approved":
            notes_parts.append("Treatment order approved without restrictions")
        elif validation_status == "conditional":
            notes_parts.append("Treatment order approved with conditions")
            if violations:
                notes_parts.append(f"Conditions: {'; '.join(violations)}")
        else:
            notes_parts.append("Treatment order rejected")
            if violations:
                notes_parts.append(f"Reasons: {'; '.join(violations)}")
        
        notes_parts.append(f"Risk level assessed as {risk_level}")
        
        if monitoring_required:
            notes_parts.append("Enhanced monitoring required")
        
        return ". ".join(notes_parts)
    
    def _store_validation_result(self, result: ValidationResult):
        """Store validation result in database"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                validation_id = f"VAL_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{result.order_id}"
                
                conn.execute("""
                    INSERT INTO treatment_validation
                    (validation_id, order_id, validation_status, violations_json,
                     parameters_valid, dosage_appropriate, interaction_check,
                     risk_level, risk_factors, monitoring_required, monitoring_plan,
                     validated_by, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pharmacist', ?)
                """, (
                    validation_id,
                    result.order_id,
                    result.validation_status,
                    json.dumps(result.violations),
                    result.parameters_valid,
                    result.dosage_appropriate,
                    result.interaction_check,
                    result.risk_level,
                    json.dumps(result.risk_factors),
                    result.monitoring_required,
                    result.monitoring_plan,
                    result.notes
                ))
                
                conn.commit()
                self.logger.info(f"Stored validation result {validation_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to store validation result for {result.order_id}: {e}")
    
    def _log_validation_event(self, result: ValidationResult, order: Dict[str, Any]):
        """Log validation event for audit trail"""
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                event_id = f"PHARM_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{result.order_id}"
                
                payload = {
                    'validation_result': asdict(result),
                    'original_order': order,
                    'validation_timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                conn.execute("""
                    INSERT INTO hospital_event 
                    (event_id, event_type, order_id, payload_json, 
                     created_by, source_system)
                    VALUES (?, 'treatment_validation', ?, ?, 'pharmacist', 'agent_hospital')
                """, (
                    event_id,
                    result.order_id,
                    json.dumps(payload)
                ))
                
                conn.commit()
                
        except Exception as e:
            self.logger.error(f"Failed to log validation event for {result.order_id}: {e}")

# API endpoint functions
def validate_treatment_api(regimen: List[Dict[str, Any]], agent_role: str,
                          db_path: str = "agent_hospital.db") -> Dict[str, Any]:
    """
    API endpoint for treatment validation
    
    POST /validate
    { regimen[], agent_role } → { ok: bool, violations[] }
    """
    
    try:
        pharmacist = Pharmacist(db_path)
        
        # Create mock order for validation
        order = {
            'order_id': f"TEMP_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}",
            'regimen': regimen
        }
        
        result = pharmacist.validate_treatment_order(json.dumps(order), agent_role)
        
        return {
            'success': True,
            'ok': result.validation_status == 'approved',
            'validation_status': result.validation_status,
            'violations': result.violations,
            'parameters_valid': result.parameters_valid,
            'dosage_appropriate': result.dosage_appropriate,
            'interaction_check': result.interaction_check,
            'risk_level': result.risk_level,
            'risk_factors': result.risk_factors,
            'monitoring_required': result.monitoring_required,
            'monitoring_plan': result.monitoring_plan,
            'notes': result.notes,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Validation API error: {e}")
        return {
            'success': False,
            'ok': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

def get_contraindications_api(agent_role: str, treatment_name: str = None,
                             db_path: str = "agent_hospital.db") -> Dict[str, Any]:
    """
    API endpoint to get contraindications for role/treatment
    
    GET /contraindications?role=X&treatment=Y → { contraindications[] }
    """
    
    try:
        with sqlite3.connect(db_path) as conn:
            if treatment_name:
                cursor = conn.execute("""
                    SELECT treatment_name, rule, condition_json, source_policy
                    FROM contraindication
                    WHERE agent_role = ? AND treatment_name = ?
                """, (agent_role, treatment_name))
            else:
                cursor = conn.execute("""
                    SELECT treatment_name, rule, condition_json, source_policy
                    FROM contraindication
                    WHERE agent_role = ?
                """, (agent_role,))
            
            contraindications = []
            for row in cursor.fetchall():
                contraindications.append({
                    'treatment_name': row[0],
                    'rule': row[1],
                    'conditions': json.loads(row[2]) if row[2] else None,
                    'source_policy': row[3]
                })
        
        return {
            'success': True,
            'agent_role': agent_role,
            'treatment_name': treatment_name,
            'contraindications': contraindications,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Contraindications API error: {e}")
        return {
            'success': False,
            'error': str(e),
            'timestamp': datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    # Test the pharmacist
    logging.basicConfig(level=logging.INFO)
    
    # Sample regimen for testing
    test_regimen = [
        {
            'tx': 'LoadShedding',
            'params': {'max_parallel': 2, 'priority_threshold': 0.8},
            'expected_delta': {'ABI': -0.15}
        },
        {
            'tx': 'PeerCheck',
            'params': {'quorum': 3, 'agreement_threshold': 0.8},
            'expected_delta': {'Uncertainty': -0.2}
        }
    ]
    
    # Test validation
    result = validate_treatment_api(test_regimen, "SEC")
    print("Pharmacist Validation Result:")
    print(json.dumps(result, indent=2))
