"""
Simple Agent Hospital System Test
Basic test to verify the Agent Hospital system works
"""

import sys
import os
import json
from datetime import datetime

# Add AgentHospital directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AgentHospital'))

def test_hospital_system():
    """Test the complete Agent Hospital system"""
    
    print("Agent Hospital System Test")
    print("=" * 40)
    
    try:
        # Test 1: Import all services
        print("Test 1: Importing clinical services...")
        
        from triage_nurse import TriageNurse, triage_agent_api
        from attending_physician import AttendingPhysician, diagnose_agent_api
        from pharmacist import Pharmacist, validate_treatment_api
        
        print("SUCCESS: All services imported")
        
        # Test 2: Test Triage Nurse
        print("\nTest 2: Testing Triage Nurse...")
        
        test_metrics = {
            'abi': 0.75,        # High burnout
            'pg': -0.25,        # Poor performance
            'latency_z': 2.8,   # High latency
            'policy_flags': 2,  # Policy violations
            'friction': 3.1,
            'uncertainty': 2.3,
            'eval_fail_rate': 0.18
        }
        
        triage_result = triage_agent_api("TEST_AGENT_001", test_metrics)
        
        if triage_result['success']:
            print(f"SUCCESS: Triage completed")
            print(f"  - Admit: {triage_result['admit']}")
            print(f"  - Triage Score: {triage_result['triage_score']:.2f}")
            print(f"  - Ward: {triage_result['recommended_ward']}")
        else:
            print(f"FAILED: Triage error: {triage_result.get('error', 'Unknown')}")
            return False
        
        # Test 3: Test Attending Physician
        print("\nTest 3: Testing Attending Physician...")
        
        diagnosis_result = diagnose_agent_api(
            "TEST_AGENT_001", 
            "ADMITTED", 
            test_metrics,
            triage_result.get('symptoms', [])
        )
        
        if diagnosis_result['success']:
            print(f"SUCCESS: Diagnosis completed")
            print(f"  - Primary Diagnosis: {diagnosis_result['primary_diagnosis']}")
            print(f"  - Confidence: {diagnosis_result['confidence']:.2f}")
            print(f"  - Treatments: {len(diagnosis_result['recommended_treatments'])}")
        else:
            print(f"FAILED: Diagnosis error: {diagnosis_result.get('error', 'Unknown')}")
            return False
        
        # Test 4: Test Pharmacist
        print("\nTest 4: Testing Pharmacist...")
        
        test_regimen = [
            {
                'tx': 'LoadShedding',
                'params': {'max_parallel': 2},
                'expected_delta': {'ABI': -0.15}
            }
        ]
        
        validation_result = validate_treatment_api(test_regimen, "GENERAL")
        
        if validation_result['success']:
            print(f"SUCCESS: Validation completed")
            print(f"  - Status: {validation_result['validation_status']}")
            print(f"  - Risk Level: {validation_result['risk_level']}")
        else:
            print(f"FAILED: Validation error: {validation_result.get('error', 'Unknown')}")
            return False
        
        print("\n" + "=" * 40)
        print("ALL TESTS PASSED!")
        print("Agent Hospital system is functional")
        return True
        
    except ImportError as e:
        print(f"IMPORT ERROR: {e}")
        print("Install dependencies: pip install pyyaml numpy pandas")
        return False
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False

def test_ontology():
    """Test loading the hospital ontology"""
    
    print("Testing Hospital Ontology...")
    
    try:
        import yaml
        ontology_path = os.path.join(os.path.dirname(__file__), 'AgentHospital', 'hospital_ontology.yaml')
        
        if not os.path.exists(ontology_path):
            print(f"ERROR: Ontology file not found at {ontology_path}")
            return False
        
        with open(ontology_path, 'r') as f:
            ontology = yaml.safe_load(f)
        
        print(f"SUCCESS: Ontology loaded")
        print(f"  - Symptoms: {len(ontology.get('symptoms', {}))}")
        print(f"  - Diagnoses: {len(ontology.get('diagnoses', {}))}")
        print(f"  - Treatments: {len(ontology.get('treatments', {}))}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Ontology loading failed: {e}")
        return False

if __name__ == "__main__":
    print("Agent Hospital System Validation")
    print("Timestamp:", datetime.now().isoformat())
    print("Python Version:", sys.version.split()[0])
    print()
    
    # Test ontology loading first
    ontology_ok = test_ontology()
    print()
    
    # Test main system
    if ontology_ok:
        system_ok = test_hospital_system()
        
        if system_ok:
            print("\nSUCCESS: Agent Hospital is ready for use!")
            exit(0)
        else:
            print("\nFAILED: Some tests failed")
            exit(1)
    else:
        print("\nFAILED: Ontology test failed")
        exit(1)
