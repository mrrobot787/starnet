"""
Agent Registry Service

High-level service for managing agent registrations with validation,
database persistence, and lifecycle management.
"""

from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
import json

from .models import AgentRegistration, AgentStatus, Tool
from .validator import AgentValidator
from .database import AgentRegistryDB


class AgentRegistryService:
    """Service for managing agent registrations"""

    def __init__(
        self,
        db_path: str = "agent_registry.db",
        schema_path: Optional[str] = None
    ):
        """
        Initialize service
        
        Args:
            db_path: Path to SQLite database
            schema_path: Path to JSON schema (optional)
        """
        self.db = AgentRegistryDB(db_path)
        self.validator = AgentValidator(schema_path)

    def register_agent(
        self,
        agent_data: Dict[str, Any],
        created_by: str = "",
        skip_validation: bool = False
    ) -> Tuple[bool, Optional[int], List[str]]:
        """
        Register a new agent
        
        Args:
            agent_data: Agent registration dictionary
            created_by: User creating the registration
            skip_validation: Skip validation (not recommended)
            
        Returns:
            Tuple of (success, db_id, errors)
        """
        errors = []

        # Validate
        if not skip_validation:
            is_valid, validation_errors = self.validator.validate(agent_data)
            if not is_valid:
                return False, None, validation_errors

        # Check if agent already exists
        existing = self.db.get_agent(agent_data['agent_id'])
        if existing:
            errors.append(f"Agent {agent_data['agent_id']} already exists")
            return False, None, errors

        # Register
        try:
            db_id = self.db.register_agent(agent_data, created_by)
            return True, db_id, []
        except Exception as e:
            return False, None, [f"Database error: {str(e)}"]

    def register_from_file(
        self,
        filepath: str,
        created_by: str = ""
    ) -> Tuple[bool, Optional[int], List[str]]:
        """
        Register agent from JSON file
        
        Args:
            filepath: Path to agent registration JSON
            created_by: User creating the registration
            
        Returns:
            Tuple of (success, db_id, errors)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                agent_data = json.load(f)
            return self.register_agent(agent_data, created_by)
        except Exception as e:
            return False, None, [f"Error reading file: {str(e)}"]

    def register_from_directory(
        self,
        dirpath: str,
        created_by: str = ""
    ) -> Dict[str, Tuple[bool, Optional[int], List[str]]]:
        """
        Register all agents from a directory
        
        Args:
            dirpath: Directory containing agent registration JSONs
            created_by: User creating the registrations
            
        Returns:
            Dictionary mapping filename to result
        """
        results = {}
        dir_path = Path(dirpath)
        
        for json_file in dir_path.glob("*.json"):
            results[json_file.name] = self.register_from_file(
                str(json_file),
                created_by
            )
        
        return results

    def get_agent(self, agent_id: str) -> Optional[AgentRegistration]:
        """
        Get agent registration
        
        Args:
            agent_id: Agent identifier
            
        Returns:
            AgentRegistration or None
        """
        data = self.db.get_agent(agent_id)
        if data:
            return AgentRegistration.from_dict(data['registration_data'])
        return None

    def list_agents(
        self,
        status: Optional[str] = None,
        environment: Optional[str] = None,
        autonomy_level: Optional[int] = None
    ) -> List[AgentRegistration]:
        """
        List agents with filters
        
        Args:
            status: Filter by status
            environment: Filter by environment
            autonomy_level: Filter by autonomy level
            
        Returns:
            List of AgentRegistration objects
        """
        rows = self.db.list_agents(status, environment, autonomy_level)
        return [
            AgentRegistration.from_dict(row['registration_data'])
            for row in rows
        ]

    def update_status(
        self,
        agent_id: str,
        new_status: str,
        user: str = ""
    ) -> Tuple[bool, List[str]]:
        """
        Update agent status
        
        Args:
            agent_id: Agent identifier
            new_status: New status value
            user: User making the change
            
        Returns:
            Tuple of (success, errors)
        """
        # Validate status
        try:
            AgentStatus(new_status)
        except ValueError:
            return False, [f"Invalid status: {new_status}"]

        # Check agent exists
        agent = self.db.get_agent(agent_id)
        if not agent:
            return False, [f"Agent not found: {agent_id}"]

        # Update
        try:
            self.db.update_agent_status(agent_id, new_status, user)
            return True, []
        except Exception as e:
            return False, [f"Database error: {str(e)}"]

    def approve_agent(self, agent_id: str, user: str = "") -> Tuple[bool, List[str]]:
        """Approve agent (draft -> review -> active)"""
        agent = self.db.get_agent(agent_id)
        if not agent:
            return False, [f"Agent not found: {agent_id}"]
        
        current_status = agent['status']
        
        if current_status == 'draft':
            return self.update_status(agent_id, 'review', user)
        elif current_status == 'review':
            return self.update_status(agent_id, 'active', user)
        else:
            return False, [f"Cannot approve agent in status: {current_status}"]

    def deprecate_agent(self, agent_id: str, user: str = "") -> Tuple[bool, List[str]]:
        """Deprecate an active agent"""
        return self.update_status(agent_id, 'deprecated', user)

    def retire_agent(self, agent_id: str, user: str = "") -> Tuple[bool, List[str]]:
        """Retire an agent"""
        return self.update_status(agent_id, 'retired', user)

    def rotate_agent(
        self,
        agent_id: str,
        new_environment: str,
        new_tools: List[Dict[str, Any]],
        user: str = ""
    ) -> Tuple[bool, List[str]]:
        """
        Rotate agent to new environment (hospital ward rotation)
        
        Args:
            agent_id: Agent to rotate
            new_environment: New environment name
            new_tools: New tool set for the environment
            user: User performing rotation
            
        Returns:
            Tuple of (success, errors)
        """
        agent = self.get_agent(agent_id)
        if not agent:
            return False, [f"Agent not found: {agent_id}"]

        # Update environment and tools
        agent.environment.name = new_environment
        agent.tools = [Tool(**t) if isinstance(t, dict) else t for t in new_tools]

        # Increment version (rotation is a significant change)
        version_parts = agent.version.split('.')
        version_parts[1] = str(int(version_parts[1]) + 1)
        agent.version = '.'.join(version_parts)

        # Update metadata
        if agent.metadata:
            agent.metadata.updated_at = datetime.utcnow().isoformat()

        # Validate the rotated configuration
        is_valid, errors = self.validator.validate(agent.to_dict())
        if not is_valid:
            return False, errors

        # Log the rotation
        self.db.log_audit_event(
            agent_id,
            'rotation',
            {
                'new_environment': new_environment,
                'new_version': agent.version
            },
            user
        )

        return True, []

    def get_agent_health(self, agent_id: str, days: int = 30) -> Dict[str, Any]:
        """
        Get agent health metrics
        
        Args:
            agent_id: Agent identifier
            days: Number of days to look back
            
        Returns:
            Health metrics dictionary
        """
        metrics = self.db.get_agent_metrics(agent_id, days=days)
        violations = self.db.get_violations(agent_id=agent_id, resolved=False)
        
        return {
            'agent_id': agent_id,
            'metrics_count': len(metrics),
            'violations_count': len(violations),
            'unresolved_violations': violations,
            'recent_metrics': metrics[:10],  # Most recent 10
        }

    def get_environment_roster(self, environment_name: str) -> List[AgentRegistration]:
        """Get all agents in an environment (ward roster)"""
        return self.list_agents(environment=environment_name, status='active')

    def get_high_risk_agents(self) -> List[Dict[str, Any]]:
        """Get agents with high autonomy + internet access"""
        all_agents = self.list_agents(status='active')
        high_risk = []
        
        for agent in all_agents:
            if agent.autonomy.level >= 2:
                if 'internet' in agent.environment.network.egress:
                    high_risk.append({
                        'agent_id': agent.agent_id,
                        'title': agent.title,
                        'autonomy_level': agent.autonomy.level,
                        'environment': agent.environment.name,
                    })
        
        return high_risk

    def validate_registry(self) -> Dict[str, Tuple[bool, List[str]]]:
        """Validate all registered agents"""
        results = {}
        agents = self.list_agents()
        
        for agent in agents:
            is_valid, errors = self.validator.validate(agent.to_dict())
            results[agent.agent_id] = (is_valid, errors)
        
        return results

    def export_agent(self, agent_id: str, filepath: str) -> bool:
        """Export agent registration to file"""
        agent = self.get_agent(agent_id)
        if not agent:
            return False
        
        try:
            agent.save_to_file(filepath)
            return True
        except Exception:
            return False

    def close(self):
        """Close database connection"""
        self.db.close()
