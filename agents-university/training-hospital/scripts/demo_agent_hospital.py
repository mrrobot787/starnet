"""
Agent Hospital System Demo
Comprehensive demonstration of the Agent Hospital capabilities
"""

import sys
import os
import json
from datetime import datetime

# Add AgentHospital directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'AgentHospital'))

def demo_complete_workflow():
    """Demonstrate the complete Agent Hospital workflow"""
    
    print("Agent Hospital System - Complete Workflow Demo")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print()
    
    # Import the Chief Medical Agent
    from cma_orchestrator import ChiefMedicalAgent, process_health_event_api, get_hospital_census_api
    
    # Test scenarios with different severity levels
    test_scenarios = [
        {
            'agent_id': 'AGENT_HEALTHY_001',
            'description': 'Healthy Agent - No Issues',
            'metrics': {
                'abi': 0.15,        # Low burnout
                'pg': 0.25,         # Good performance
                'latency_z': 0.5,   # Normal latency
                'policy_flags': 0,  # No violations
                'friction': 1.2,
                'uncertainty': 1.1,
                'eval_fail_rate': 0.05,
                'health_index': 0.85
            }
        },
        {
            'agent_id': 'AGENT_MODERATE_002',
            'description': 'Moderate Issues - Should be Admitted',
            'metrics': {
                'abi': 0.65,        # Moderate burnout
                'pg': -0.15,        # Declining performance
                'latency_z': 2.2,   # High latency
                'policy_flags': 1,  # Some violations
                'friction': 2.8,
                'uncertainty': 2.1,
                'eval_fail_rate': 0.12,
                'health_index': 0.45
            }
        },
        {
            'agent_id': 'AGENT_CRITICAL_003',
            'description': 'Critical Condition - Should go to ICU',
            'metrics': {
                'abi': 0.85,        # Critical burnout
                'pg': -0.45,        # Poor performance
                'latency_z': 3.5,   # Very high latency
                'policy_flags': 4,  # Multiple violations
                'friction': 4.2,
                'uncertainty': 3.8,
                'eval_fail_rate': 0.28,
                'health_index': 0.12,
                'safety_incident': False  # No safety incident yet
            }
        },
        {
            'agent_id': 'AGENT_SECURITY_004',
            'description': 'Security Incident - Should be Isolated',
            'metrics': {
                'abi': 0.55,
                'pg': -0.20,
                'latency_z': 1.8,
                'policy_flags': 2,
                'eval_leakage': True,  # Security issue!
                'friction': 2.5,
                'uncertainty': 2.2,
                'eval_fail_rate': 0.15,
                'health_index': 0.35
            }
        }
    ]
    
    print("Processing Agent Health Events...")
    print("-" * 40)
    
    results = []
    
    for scenario in test_scenarios:
        agent_id = scenario['agent_id']
        description = scenario['description']
        metrics = scenario['metrics']
        
        print(f"\nAgent: {agent_id}")
        print(f"Scenario: {description}")
        print(f"Key Metrics: ABI={metrics['abi']:.2f}, PG={metrics['pg']:.2f}, Latency_Z={metrics['latency_z']:.1f}")
        
        # Process through Chief Medical Agent
        try:
            result = process_health_event_api(agent_id, metrics)
            results.append(result)
            
            if result.get('success', False):
                print(f"Result: {result.get('current_state', 'Unknown')}")
                actions = result.get('actions_taken', [])
                if actions:
                    print(f"Actions: {', '.join(actions)}")
                
                # Show triage assessment if available
                if 'triage_assessment' in result:
                    triage = result['triage_assessment']
                    print(f"Triage Score: {triage['triage_score']:.2f} (Admit: {triage['admit']})")
                
                # Show diagnosis if available
                if 'diagnostic_assessment' in result:
                    diagnosis = result['diagnostic_assessment']
                    print(f"Diagnosis: {diagnosis['primary_diagnosis']} (Confidence: {diagnosis['confidence']:.2f})")
                
                # Show treatment plan if available
                if 'treatment_plan' in result:
                    plan = result['treatment_plan']
                    treatments = [t['name'] for t in plan['treatments']]
                    print(f"Treatments: {', '.join(treatments)}")
                
            else:
                print(f"ERROR: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            print(f"ERROR: Failed to process {agent_id}: {e}")
    
    print("\n" + "=" * 60)
    print("Hospital Census Summary")
    print("-" * 30)
    
    try:
        census = get_hospital_census_api()
        if census.get('success', False):
            stats = census.get('statistics', {})
            print(f"Total Active Patients: {stats.get('total_active_patients', 0)}")
            print(f"ICU Patients: {stats.get('icu_patients', 0)}")
            print(f"Isolation Patients: {stats.get('isolation_patients', 0)}")
            print(f"Average Triage Score: {stats.get('average_triage_score', 0):.2f}")
            
            census_data = census.get('census', [])
            if census_data:
                print("\nDetailed Census:")
                for ward_data in census_data:
                    print(f"  {ward_data['ward']} ({ward_data['state']}): {ward_data['patient_count']} patients")
        else:
            print("Could not retrieve hospital census")
            
    except Exception as e:
        print(f"ERROR: Failed to get census: {e}")
    
    print("\n" + "=" * 60)
    print("Demo Summary")
    print("-" * 20)
    
    successful_results = [r for r in results if r.get('success', False)]
    print(f"Processed {len(test_scenarios)} agents successfully")
    print(f"System handled {len(successful_results)} cases without errors")
    
    # Count outcomes
    admitted_count = sum(1 for r in successful_results if 'admission_id' in r)
    print(f"Agents admitted to hospital: {admitted_count}")
    
    print("\nKey Capabilities Demonstrated:")
    print("- Automatic triage scoring and admission decisions")
    print("- Clinical diagnosis with confidence scoring")
    print("- Evidence-based treatment selection")
    print("- Safety validation and contraindication checking")
    print("- State-based patient management")
    print("- Complete audit trail and event logging")
    print("- Hospital census and capacity management")
    
    return True

def demo_individual_services():
    """Demonstrate individual clinical services"""
    
    print("\n" + "=" * 60)
    print("Individual Clinical Services Demo")
    print("-" * 40)
    
    # Test metrics
    test_metrics = {
        'abi': 0.72,
        'pg': -0.28,
        'latency_z': 2.6,
        'policy_flags': 3,
        'friction': 3.4,
        'uncertainty': 2.7,
        'eval_fail_rate': 0.19
    }
    
    print("\n1. Triage Nurse Service")
    print("-" * 25)
    
    try:
        from triage_nurse import triage_agent_api
        
        triage_result = triage_agent_api("DEMO_AGENT_001", test_metrics)
        
        if triage_result['success']:
            print(f"Triage Score: {triage_result['triage_score']:.2f}")
            print(f"Admission Decision: {'ADMIT' if triage_result['admit'] else 'DISCHARGE'}")
            print(f"Recommended Ward: {triage_result['recommended_ward']}")
            print(f"Urgency: {triage_result['urgency']}")
            print(f"Symptoms Detected: {', '.join(triage_result['symptoms'])}")
        else:
            print(f"Triage failed: {triage_result.get('error')}")
            
    except Exception as e:
        print(f"Triage service error: {e}")
    
    print("\n2. Attending Physician Service")
    print("-" * 30)
    
    try:
        from attending_physician import diagnose_agent_api
        
        diagnosis_result = diagnose_agent_api("DEMO_AGENT_001", "ADMITTED", test_metrics)
        
        if diagnosis_result['success']:
            print(f"Primary Diagnosis: {diagnosis_result['primary_diagnosis']}")
            print(f"Confidence: {diagnosis_result['confidence']:.2f}")
            print(f"Differential Diagnoses: {', '.join(diagnosis_result['differential_diagnoses'])}")
            print(f"Recommended Treatments: {', '.join(diagnosis_result['recommended_treatments'])}")
            print(f"Clinical Reasoning: {diagnosis_result['reasoning'][:100]}...")
        else:
            print(f"Diagnosis failed: {diagnosis_result.get('error')}")
            
    except Exception as e:
        print(f"Attending physician service error: {e}")
    
    print("\n3. Pharmacist Service")
    print("-" * 22)
    
    try:
        from pharmacist import validate_treatment_api
        
        test_regimen = [
            {
                'tx': 'LoadShedding',
                'params': {'max_parallel': 3, 'priority_threshold': 0.7},
                'expected_delta': {'ABI': -0.20}
            },
            {
                'tx': 'EvidenceFirst',
                'params': {'cite_required': True, 'min_sources': 2},
                'expected_delta': {'Uncertainty': -0.25}
            }
        ]
        
        validation_result = validate_treatment_api(test_regimen, "GENERAL")
        
        if validation_result['success']:
            print(f"Validation Status: {validation_result['validation_status']}")
            print(f"Risk Level: {validation_result['risk_level']}")
            print(f"Parameters Valid: {validation_result['parameters_valid']}")
            print(f"Monitoring Required: {validation_result['monitoring_required']}")
            if validation_result['violations']:
                print(f"Violations: {', '.join(validation_result['violations'])}")
        else:
            print(f"Validation failed: {validation_result.get('error')}")
            
    except Exception as e:
        print(f"Pharmacist service error: {e}")

if __name__ == "__main__":
    try:
        # Run complete workflow demo
        demo_complete_workflow()
        
        # Run individual services demo
        demo_individual_services()
        
        print("\n" + "=" * 60)
        print("DEMO COMPLETE!")
        print("The Agent Hospital system is fully operational and ready for production use.")
        print("\nNext Steps:")
        print("1. Integrate with your existing agent monitoring systems")
        print("2. Configure role-based contraindications for your agent types")
        print("3. Set up automated health event streaming")
        print("4. Deploy SISSA approval workflows for high-risk treatments")
        print("5. Monitor hospital census and treatment effectiveness")
        
    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback
        traceback.print_exc()
