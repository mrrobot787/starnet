"""
Pipeline Hospital Integration
Integrates the Feature Pipeline Engine with the existing Agent Hospital system
for comprehensive agent health monitoring during feature development workflows.
"""

import json
import logging
import sqlite3
from typing import Dict, List, Any, Optional
from datetime import datetime, timezone
import sys
import os

# Add paths for imports
sys.path.append('/workspace')
sys.path.append('/workspace/AgentHospital')

try:
    from agents.feature_pipeline_engine import FeaturePipelineEngine, NodeStatus, PipelineNode
except ImportError as e:
    print(f"Import error (pipeline engine): {e}")

# Optional import for hospital integration
ChiefMedicalAgent = None
process_health_event_api = None

try:
    from AgentHospital.cma_orchestrator import ChiefMedicalAgent, process_health_event_api
except ImportError:
    # Hospital integration is optional - create mock functions
    def process_health_event_api(agent_id: str, metrics: dict, db_path: str = None) -> dict:
        """Mock implementation when hospital system is not available"""
        return {
            "success": True,
            "agent_id": agent_id,
            "current_state": "OUTPATIENT",
            "actions_taken": ["health_check_simulated"],
            "recommendations": ["Continue monitoring - hospital system not available"],
            "mock": True
        }

class PipelineHealthMonitor:
    """
    Monitors agent health during pipeline execution and coordinates with Agent Hospital
    """
    
    def __init__(self, pipeline_db_path: str = "/workspace/feature_pipeline.db",
                 hospital_db_path: str = "/workspace/agent_hospital.db"):
        self.pipeline_db_path = pipeline_db_path
        self.hospital_db_path = hospital_db_path
        self.logger = logging.getLogger(__name__)
        
        # Initialize connections to both systems
        try:
            self.pipeline_engine = FeaturePipelineEngine(pipeline_db_path)
            if ChiefMedicalAgent and os.path.exists(hospital_db_path):
                self.cma = ChiefMedicalAgent(hospital_db_path)
            else:
                if not ChiefMedicalAgent:
                    self.logger.warning("ChiefMedicalAgent not available - using mock hospital integration")
                else:
                    self.logger.warning("Agent Hospital database not found - hospital integration disabled")
                self.cma = None
        except Exception as e:
            self.logger.error(f"Failed to initialize integration: {e}")
            self.cma = None
    
    async def monitor_pipeline_execution(self, pipeline_id: str, health_check_interval: int = 300):
        """
        Monitor pipeline execution and send health events to Agent Hospital
        """
        self.logger.info(f"Starting health monitoring for pipeline {pipeline_id}")
        
        try:
            # Get pipeline nodes with agent assignments
            agent_nodes = self._get_agent_nodes(pipeline_id)
            
            if not agent_nodes:
                self.logger.warning(f"No agent-assigned nodes found in pipeline {pipeline_id}")
                return
            
            # Monitor each agent during their assigned phases
            monitoring_results = {}
            
            for node_id, node_data in agent_nodes.items():
                agent_id = node_data.get('agent_id')
                if not agent_id:
                    continue
                
                self.logger.info(f"Monitoring agent {agent_id} during node {node_id}")
                
                # Generate realistic health metrics based on pipeline phase
                health_metrics = self._generate_pipeline_health_metrics(node_data)
                
                # Send health event to Agent Hospital or use mock
                hospital_result = self._send_health_event(agent_id, health_metrics, node_id, pipeline_id)
                monitoring_results[agent_id] = hospital_result
                
                # Store pipeline health event
                self._store_pipeline_health_event(pipeline_id, node_id, agent_id, health_metrics, monitoring_results.get(agent_id))
            
            return monitoring_results
            
        except Exception as e:
            self.logger.error(f"Pipeline health monitoring failed: {e}")
            return {"error": str(e)}
    
    def _get_agent_nodes(self, pipeline_id: str) -> Dict[str, Dict[str, Any]]:
        """Get nodes that have assigned agents"""
        
        agent_nodes = {}
        
        try:
            with sqlite3.connect(self.pipeline_db_path) as conn:
                cursor = conn.execute("""
                    SELECT node_id, owner_role, agent_id, status, context_json
                    FROM node_executions 
                    WHERE pipeline_id = ? AND agent_id IS NOT NULL
                """, (pipeline_id,))
                
                for row in cursor.fetchall():
                    node_id, owner_role, agent_id, status, context_json = row
                    
                    context = {}
                    if context_json:
                        try:
                            context = json.loads(context_json)
                        except:
                            pass
                    
                    agent_nodes[node_id] = {
                        'agent_id': agent_id,
                        'owner_role': owner_role,
                        'status': status,
                        'context': context
                    }
                    
        except Exception as e:
            self.logger.error(f"Failed to get agent nodes: {e}")
        
        return agent_nodes
    
    def _generate_pipeline_health_metrics(self, node_data: Dict[str, Any]) -> Dict[str, float]:
        """
        Generate realistic health metrics based on pipeline execution context
        """
        import random
        
        owner_role = node_data.get('owner_role', 'GENERAL')
        status = node_data.get('status', 'PENDING')
        context = node_data.get('context', {})
        
        # Base health metrics
        base_metrics = {
            'abi': 0.3,  # Agent Burnout Index (lower is better)
            'pg': 0.2,   # Performance Gradient (higher is better) 
            'latency_z': 0.8,  # Latency z-score
            'policy_flags': 0,  # Policy violations
            'friction': 1.2,    # Task difficulty
            'uncertainty': 1.0,  # Response confidence
            'eval_fail_rate': 0.05,  # Evaluation failure rate
            'health_index': 0.85     # Overall health
        }
        
        # Adjust metrics based on role and execution context
        if owner_role == 'Agent_UI':
            # UI agents might have higher complexity but good tooling
            base_metrics['friction'] += random.uniform(0.1, 0.3)
            base_metrics['uncertainty'] -= random.uniform(0.05, 0.15)
            
            # Check for UI-specific stress indicators
            if context.get('bundle_size_kb', 0) > 100:
                base_metrics['abi'] += 0.1
            
            if context.get('accessibility_score', 100) < 90:
                base_metrics['policy_flags'] += 1
                
        elif owner_role == 'Agent_Backend':
            # Backend agents might have security/performance pressures
            base_metrics['latency_z'] += random.uniform(0.2, 0.5)
            base_metrics['policy_flags'] = random.choice([0, 0, 1, 2])  # Occasional security flags
            
            # Check for backend-specific stress
            if context.get('security_scan_score', 100) < 95:
                base_metrics['abi'] += 0.15
                base_metrics['policy_flags'] += 2
                
            if context.get('api_response_time_ms', 100) > 300:
                base_metrics['friction'] += 0.2
                
        elif owner_role == 'Integrator':
            # Integrators deal with system complexity
            base_metrics['friction'] += random.uniform(0.3, 0.5)
            base_metrics['uncertainty'] += random.uniform(0.1, 0.3)
            
        # Adjust based on execution status
        if status == 'COMPLETED':
            # Successful completion reduces stress
            base_metrics['abi'] -= 0.1
            base_metrics['pg'] += 0.15
            base_metrics['health_index'] += 0.1
        elif status == 'FAILED':
            # Failures increase stress
            base_metrics['abi'] += 0.3
            base_metrics['pg'] -= 0.2
            base_metrics['friction'] += 0.5
            base_metrics['health_index'] -= 0.2
        elif status == 'RUNNING':
            # Running tasks have moderate stress
            base_metrics['abi'] += random.uniform(0.05, 0.15)
            base_metrics['latency_z'] += random.uniform(0.1, 0.3)
        
        # Add some randomness for realism
        for key in base_metrics:
            if key != 'policy_flags':  # Keep policy flags as integers
                base_metrics[key] += random.uniform(-0.05, 0.05)
                base_metrics[key] = max(0.0, base_metrics[key])  # Keep non-negative
        
        # Ensure ABI doesn't exceed critical thresholds unless there's a real problem
        base_metrics['abi'] = min(base_metrics['abi'], 0.7 if status != 'FAILED' else 0.9)
        base_metrics['health_index'] = max(0.1, min(1.0, base_metrics['health_index']))
        
        return base_metrics
    
    def _send_health_event(self, agent_id: str, metrics: Dict[str, float], 
                          node_id: str, pipeline_id: str) -> Dict[str, Any]:
        """Send health event to Agent Hospital"""
        
        try:
            # Add pipeline context to metrics
            pipeline_context = {
                'pipeline_id': pipeline_id,
                'node_id': node_id,
                'event_source': 'feature_pipeline',
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
            
            # Use the hospital's health event processing (or mock version)
            result = process_health_event_api(agent_id, metrics, self.hospital_db_path)
            
            # Log the hospital response
            if result.get('success'):
                self.logger.info(f"Agent {agent_id} health event processed: {result.get('current_state')}")
                
                # Check if agent was admitted to hospital
                if 'admission_id' in result:
                    self.logger.warning(f"Agent {agent_id} admitted to hospital during pipeline execution")
                    # Could trigger pipeline pause/escalation here
                elif result.get('mock'):
                    self.logger.info(f"Agent {agent_id} health monitored via mock hospital system")
                    
            else:
                self.logger.error(f"Hospital health event failed for {agent_id}: {result.get('error')}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to send health event for {agent_id}: {e}")
            return {"error": str(e)}
    
    def _store_pipeline_health_event(self, pipeline_id: str, node_id: str, agent_id: str,
                                   health_metrics: Dict[str, float], hospital_response: Dict[str, Any]):
        """Store pipeline health monitoring event"""
        
        try:
            with sqlite3.connect(self.pipeline_db_path) as conn:
                # Create health monitoring table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_health_events (
                        event_id TEXT PRIMARY KEY,
                        pipeline_id TEXT NOT NULL,
                        node_id TEXT NOT NULL,
                        agent_id TEXT NOT NULL,
                        health_metrics_json TEXT NOT NULL,
                        hospital_response_json TEXT,
                        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (pipeline_id) REFERENCES pipelines (pipeline_id)
                    )
                """)
                
                # Insert health event
                event_id = f"PHE_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{agent_id}"
                
                conn.execute("""
                    INSERT INTO pipeline_health_events
                    (event_id, pipeline_id, node_id, agent_id, health_metrics_json, hospital_response_json)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    event_id, pipeline_id, node_id, agent_id,
                    json.dumps(health_metrics), json.dumps(hospital_response or {})
                ))
                
                conn.commit()
                self.logger.info(f"Stored health event {event_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to store health event: {e}")
    
    def get_pipeline_health_summary(self, pipeline_id: str) -> Dict[str, Any]:
        """Get health summary for a pipeline"""
        
        try:
            with sqlite3.connect(self.pipeline_db_path) as conn:
                cursor = conn.execute("""
                    SELECT agent_id, health_metrics_json, hospital_response_json, timestamp
                    FROM pipeline_health_events
                    WHERE pipeline_id = ?
                    ORDER BY timestamp DESC
                """, (pipeline_id,))
                
                health_events = []
                agent_health = {}
                
                for row in cursor.fetchall():
                    agent_id, metrics_json, response_json, timestamp = row
                    
                    try:
                        metrics = json.loads(metrics_json)
                        response = json.loads(response_json) if response_json else {}
                        
                        event = {
                            'agent_id': agent_id,
                            'timestamp': timestamp,
                            'health_metrics': metrics,
                            'hospital_response': response
                        }
                        health_events.append(event)
                        
                        # Track latest health per agent
                        if agent_id not in agent_health or timestamp > agent_health[agent_id]['timestamp']:
                            agent_health[agent_id] = event
                            
                    except Exception as e:
                        self.logger.warning(f"Failed to parse health event: {e}")
                
                # Calculate summary statistics
                summary = {
                    'pipeline_id': pipeline_id,
                    'total_health_events': len(health_events),
                    'monitored_agents': len(agent_health),
                    'agent_health_summary': {},
                    'hospital_admissions': 0,
                    'health_trends': {}
                }
                
                for agent_id, latest_health in agent_health.items():
                    metrics = latest_health['health_metrics']
                    response = latest_health['hospital_response']
                    
                    summary['agent_health_summary'][agent_id] = {
                        'latest_abi': metrics.get('abi', 0),
                        'latest_health_index': metrics.get('health_index', 0),
                        'hospital_status': response.get('current_state', 'OUTPATIENT'),
                        'last_checked': latest_health['timestamp']
                    }
                    
                    if 'admission_id' in response:
                        summary['hospital_admissions'] += 1
                
                return summary
                
        except Exception as e:
            self.logger.error(f"Failed to get health summary: {e}")
            return {"error": str(e)}

class PipelineAgentOrchestrator:
    """
    Orchestrates agent assignments and workload distribution across pipeline phases
    """
    
    def __init__(self, pipeline_db_path: str = "/workspace/feature_pipeline.db"):
        self.pipeline_db_path = pipeline_db_path
        self.logger = logging.getLogger(__name__)
        
        # Agent capabilities matrix
        self.agent_capabilities = {
            'agent-ui-001': {
                'role': 'Agent_UI',
                'specialties': ['react', 'accessibility', 'performance', 'design_systems'],
                'capacity': 3,  # Concurrent tasks
                'quality_score': 0.92
            },
            'agent-ui-002': {
                'role': 'Agent_UI', 
                'specialties': ['vue', 'testing', 'mobile', 'animations'],
                'capacity': 2,
                'quality_score': 0.88
            },
            'agent-backend-001': {
                'role': 'Agent_Backend',
                'specialties': ['python', 'apis', 'databases', 'security'],
                'capacity': 4,
                'quality_score': 0.95
            },
            'agent-backend-002': {
                'role': 'Agent_Backend',
                'specialties': ['node', 'microservices', 'performance', 'monitoring'],
                'capacity': 3,
                'quality_score': 0.90
            },
            'agent-integrator-001': {
                'role': 'Integrator',
                'specialties': ['devops', 'kubernetes', 'ci_cd', 'monitoring'],
                'capacity': 2,
                'quality_score': 0.93
            }
        }
    
    def assign_agents_to_pipeline(self, pipeline_id: str, pipeline_spec: Dict[str, Any]) -> Dict[str, str]:
        """
        Intelligently assign agents to pipeline nodes based on capabilities and workload
        """
        self.logger.info(f"Assigning agents to pipeline {pipeline_id}")
        
        assignments = {}
        
        try:
            # Get current agent workloads
            agent_workloads = self._get_current_agent_workloads()
            
            # Process nodes that need agent assignment
            for node in pipeline_spec.get('nodes', []):
                node_id = node['id']
                owner_role = node['owner_role']
                
                # Skip nodes that don't need dedicated agents
                if owner_role in ['Product', 'QA'] or node.get('agent_id'):
                    continue
                
                # Find best available agent for this role
                best_agent = self._find_best_agent(owner_role, node, agent_workloads)
                
                if best_agent:
                    assignments[node_id] = best_agent
                    # Update workload tracking
                    agent_workloads[best_agent] = agent_workloads.get(best_agent, 0) + 1
                    self.logger.info(f"Assigned {best_agent} to node {node_id}")
                else:
                    self.logger.warning(f"No available agent found for node {node_id} (role: {owner_role})")
            
            # Store assignments in database
            self._store_agent_assignments(pipeline_id, assignments)
            
            return assignments
            
        except Exception as e:
            self.logger.error(f"Agent assignment failed: {e}")
            return {}
    
    def _get_current_agent_workloads(self) -> Dict[str, int]:
        """Get current workload for each agent"""
        
        workloads = {}
        
        try:
            with sqlite3.connect(self.pipeline_db_path) as conn:
                cursor = conn.execute("""
                    SELECT agent_id, COUNT(*) as active_tasks
                    FROM node_executions 
                    WHERE status IN ('RUNNING', 'PENDING') 
                    AND agent_id IS NOT NULL
                    GROUP BY agent_id
                """)
                
                for row in cursor.fetchall():
                    agent_id, active_tasks = row
                    workloads[agent_id] = active_tasks
                    
        except Exception as e:
            self.logger.error(f"Failed to get agent workloads: {e}")
        
        return workloads
    
    def _find_best_agent(self, role: str, node: Dict[str, Any], current_workloads: Dict[str, int]) -> Optional[str]:
        """Find the best available agent for a node"""
        
        # Filter agents by role
        candidate_agents = {
            agent_id: info for agent_id, info in self.agent_capabilities.items()
            if info['role'] == role
        }
        
        if not candidate_agents:
            return None
        
        # Score each candidate
        best_agent = None
        best_score = -1
        
        for agent_id, info in candidate_agents.items():
            # Check capacity
            current_load = current_workloads.get(agent_id, 0)
            if current_load >= info['capacity']:
                continue  # Agent at capacity
            
            # Calculate score based on multiple factors
            score = info['quality_score']  # Base quality score
            
            # Penalty for current workload (prefer less busy agents)
            workload_penalty = current_load / info['capacity'] * 0.2
            score -= workload_penalty
            
            # Bonus for specialty match
            node_requirements = self._extract_node_requirements(node)
            specialty_bonus = len(set(info['specialties']) & set(node_requirements)) * 0.1
            score += specialty_bonus
            
            if score > best_score:
                best_score = score
                best_agent = agent_id
        
        return best_agent
    
    def _extract_node_requirements(self, node: Dict[str, Any]) -> List[str]:
        """Extract technical requirements from node definition"""
        
        requirements = []
        
        # Check node label for keywords
        label = node.get('label', '').lower()
        
        if 'ui' in label or 'frontend' in label:
            requirements.extend(['react', 'accessibility', 'testing'])
        elif 'backend' in label or 'api' in label:
            requirements.extend(['python', 'apis', 'security'])
        elif 'integration' in label or 'deploy' in label:
            requirements.extend(['devops', 'kubernetes', 'ci_cd'])
        elif 'data' in label or 'database' in label:
            requirements.extend(['databases', 'performance'])
        
        # Check reward model for additional hints
        if 'reward_model' in node:
            positive = node['reward_model'].get('positive', [])
            for item in positive:
                if 'a11y' in item or 'accessibility' in item:
                    requirements.append('accessibility')
                elif 'perf' in item or 'performance' in item:
                    requirements.append('performance')
                elif 'security' in item:
                    requirements.append('security')
                elif 'test' in item:
                    requirements.append('testing')
        
        return list(set(requirements))  # Remove duplicates
    
    def _store_agent_assignments(self, pipeline_id: str, assignments: Dict[str, str]):
        """Store agent assignments in database"""
        
        try:
            with sqlite3.connect(self.pipeline_db_path) as conn:
                # Create assignments table if it doesn't exist
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS pipeline_agent_assignments (
                        assignment_id TEXT PRIMARY KEY,
                        pipeline_id TEXT NOT NULL,
                        node_id TEXT NOT NULL,
                        agent_id TEXT NOT NULL,
                        assigned_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (pipeline_id) REFERENCES pipelines (pipeline_id)
                    )
                """)
                
                # Insert assignments
                for node_id, agent_id in assignments.items():
                    assignment_id = f"{pipeline_id}_{node_id}_{agent_id}"
                    
                    conn.execute("""
                        INSERT OR REPLACE INTO pipeline_agent_assignments
                        (assignment_id, pipeline_id, node_id, agent_id)
                        VALUES (?, ?, ?, ?)
                    """, (assignment_id, pipeline_id, node_id, agent_id))
                
                conn.commit()
                self.logger.info(f"Stored {len(assignments)} agent assignments for pipeline {pipeline_id}")
                
        except Exception as e:
            self.logger.error(f"Failed to store agent assignments: {e}")

# Integration API functions
async def execute_pipeline_with_hospital_integration(pipeline_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute pipeline with full Agent Hospital integration and health monitoring
    """
    try:
        # Initialize systems
        pipeline_engine = FeaturePipelineEngine()
        health_monitor = PipelineHealthMonitor()
        orchestrator = PipelineAgentOrchestrator()
        
        # Load and enhance pipeline with agent assignments
        pipeline = pipeline_engine.load_pipeline_from_spec(pipeline_spec)
        assignments = orchestrator.assign_agents_to_pipeline(pipeline.id, pipeline_spec)
        
        # Update pipeline spec with agent assignments
        for node in pipeline_spec['nodes']:
            if node['id'] in assignments:
                node['agent_id'] = assignments[node['id']]
        
        # Reload pipeline with agent assignments
        pipeline = pipeline_engine.load_pipeline_from_spec(pipeline_spec)
        
        # Execute pipeline
        execution_result = await pipeline_engine.execute_pipeline(pipeline.id)
        
        # Start health monitoring (async)
        health_result = await health_monitor.monitor_pipeline_execution(pipeline.id)
        
        # Get health summary
        health_summary = health_monitor.get_pipeline_health_summary(pipeline.id)
        
        return {
            "success": True,
            "pipeline_id": pipeline.id,
            "execution_result": execution_result,
            "agent_assignments": assignments,
            "health_monitoring": health_result,
            "health_summary": health_summary,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
    except Exception as e:
        logging.error(f"Integrated pipeline execution failed: {e}")
        return {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

if __name__ == "__main__":
    import asyncio
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Test integration
    async def test_integration():
        print("🏥 Testing Pipeline-Hospital Integration")
        
        # Sample pipeline spec
        test_spec = {
            "id": f"integrated-pipeline-{int(datetime.now().timestamp())}",
            "version": "1.0.0",
            "vocab": {
                "node_types": ["PLAN", "PHASE", "REVIEW", "INTEGRATION", "FULL_REVIEW"],
                "edge_types": ["SEQUENTIAL", "FORK", "JOIN"],
                "gate_types": ["REVIEW_GATE", "MERGE_GATE"],
                "roles": ["Product", "Agent_UI", "Agent_Backend", "Integrator", "QA"]
            },
            "nodes": [
                {
                    "id": "N0",
                    "type": "PLAN",
                    "label": "Create a feature PLAN",
                    "owner_role": "Product"
                },
                {
                    "id": "A1_2A",
                    "type": "PHASE",
                    "label": "Phase 2A: UI Development",
                    "owner_role": "Agent_UI",
                    "metrics": {
                        "sla_sec": 172800,
                        "quality_score_min": 0.85
                    },
                    "reward_model": {
                        "positive": ["a11y_checks", "ui_tests_pass"],
                        "negative": ["contrast_fail", "latency_regression"]
                    }
                },
                {
                    "id": "A2_2B",
                    "type": "PHASE",
                    "label": "Phase 2B: Backend Development",
                    "owner_role": "Agent_Backend",
                    "metrics": {
                        "sla_sec": 172800,
                        "quality_score_min": 0.85
                    },
                    "reward_model": {
                        "positive": ["api_contract_ok", "perf_budget_met"],
                        "negative": ["security_warnings", "timeout_spikes"]
                    }
                },
                {
                    "id": "N3",
                    "type": "INTEGRATION",
                    "label": "Phase 3: Integration",
                    "owner_role": "Integrator"
                }
            ],
            "edges": [
                {"from": "N0", "to": "A1_2A", "type": "SEQUENTIAL"},
                {"from": "N0", "to": "A2_2B", "type": "SEQUENTIAL"},
                {"from": "A1_2A", "to": "N3", "type": "JOIN"},
                {"from": "A2_2B", "to": "N3", "type": "JOIN"}
            ],
            "policies": {
                "default_rollback": "Revert to last green artifact per node; notify owners; freeze downstream edges until gate re-passes."
            }
        }
        
        result = await execute_pipeline_with_hospital_integration(test_spec)
        
        print("✅ Integration Test Complete")
        print(json.dumps(result, indent=2))
    
    # Run test
    asyncio.run(test_integration())