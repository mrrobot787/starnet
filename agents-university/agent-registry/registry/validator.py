"""
Agent Registry Validator

Validates agent registrations against the JSON schema and business rules.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

try:
    import jsonschema
    from jsonschema import validate, ValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    ValidationError = Exception


class AgentValidator:
    """Validates agent registrations"""

    def __init__(self, schema_path: Optional[str] = None):
        """
        Initialize validator with schema
        
        Args:
            schema_path: Path to JSON schema file
        """
        if schema_path is None:
            # Default to schema in project
            schema_path = Path(__file__).parent.parent.parent / "schemas" / "agent_registry_v1.json"
        
        self.schema_path = Path(schema_path)
        self.schema = self._load_schema()

    def _load_schema(self) -> Dict[str, Any]:
        """Load JSON schema"""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"Schema not found: {self.schema_path}")
        
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def validate(self, agent_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate agent registration
        
        Args:
            agent_data: Agent registration dictionary
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # JSON Schema validation
        if JSONSCHEMA_AVAILABLE:
            try:
                validate(instance=agent_data, schema=self.schema)
            except ValidationError as e:
                errors.append(f"Schema validation failed: {e.message}")
                # Continue to check business rules
        else:
            errors.append("Warning: jsonschema not installed, skipping schema validation")

        # Business rules validation
        errors.extend(self._validate_business_rules(agent_data))

        return len(errors) == 0, errors

    def _validate_business_rules(self, agent_data: Dict[str, Any]) -> List[str]:
        """Validate business rules beyond schema"""
        errors = []

        # Rule 1: agent_id must be kebab-case
        agent_id = agent_data.get('agent_id', '')
        if not re.match(r'^[a-z0-9-]+$', agent_id):
            errors.append(f"agent_id must be kebab-case: {agent_id}")

        # Rule 2: version must be semver
        version = agent_data.get('version', '')
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            errors.append(f"version must be semantic version (X.Y.Z): {version}")

        # Get common fields once
        autonomy = agent_data.get('autonomy', {})
        level = autonomy.get('level', 0)
        guardrails = agent_data.get('guardrails', {})
        tools = agent_data.get('tools', [])
        environment = agent_data.get('environment', {})
        network = environment.get('network', {})
        egress = network.get('egress', [])
        restrictions = network.get('restrictions', [])
        
        # Rule 3: Autonomy level must match capabilities
        if level >= 2:  # ACT_WITH_APPROVAL or higher
            if not guardrails.get('red_lines'):
                errors.append(f"Autonomy level {level} requires red_lines in guardrails")

        # Rule 4: If PII allowed, must have export controls
        for tool in tools:
            policy = tool.get('policy', {})
            if policy.get('allow_pii', False):
                export_controls = policy.get('export_controls', [])
                if not export_controls:
                    errors.append(
                        f"Tool '{tool.get('name')}' allows PII but has no export_controls"
                    )

        # Rule 5: Internet egress requires restrictions
        if 'internet' in egress and not restrictions:
            errors.append("Internet egress requires network restrictions")

        # Rule 6: High autonomy + internet = extra scrutiny
        if level >= 2 and 'internet' in egress:
            if not guardrails.get('escalation'):
                errors.append(
                    "High autonomy + internet access requires escalation config"
                )

        # Rule 7: Audit logging required for all agents
        audit = agent_data.get('audit')
        if not audit or not audit.get('logging'):
            errors.append("Audit logging is required for all agents")

        # Rule 8: System prompt must be substantial
        system_prompt = agent_data.get('system_prompt', '')
        if len(system_prompt) < 20:
            errors.append("system_prompt must be at least 20 characters")

        # Rule 9: Tools must have at least one capability
        for tool in tools:
            capabilities = tool.get('capabilities', [])
            if not capabilities:
                errors.append(f"Tool '{tool.get('name')}' has no capabilities")

        # Rule 10: Rollback procedure required if rollback supported
        rollback = guardrails.get('rollback', {})
        if rollback.get('supported', False) and not rollback.get('procedure'):
            errors.append("Rollback is supported but no procedure specified")

        return errors

    def validate_file(self, filepath: str) -> Tuple[bool, List[str]]:
        """
        Validate agent registration from file
        
        Args:
            filepath: Path to agent registration JSON file
            
        Returns:
            Tuple of (is_valid, error_messages)
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                agent_data = json.load(f)
            return self.validate(agent_data)
        except json.JSONDecodeError as e:
            return False, [f"Invalid JSON: {e}"]
        except Exception as e:
            return False, [f"Error reading file: {e}"]

    def validate_directory(self, dirpath: str) -> Dict[str, Tuple[bool, List[str]]]:
        """
        Validate all agent registrations in a directory
        
        Args:
            dirpath: Path to directory containing agent registration files
            
        Returns:
            Dictionary mapping filename to validation result
        """
        results = {}
        dir_path = Path(dirpath)
        
        for json_file in dir_path.glob("*.json"):
            results[json_file.name] = self.validate_file(str(json_file))
        
        return results

    def get_validation_summary(self, results: Dict[str, Tuple[bool, List[str]]]) -> str:
        """
        Generate human-readable validation summary
        
        Args:
            results: Validation results from validate_directory
            
        Returns:
            Formatted summary string
        """
        total = len(results)
        valid = sum(1 for is_valid, _ in results.values() if is_valid)
        invalid = total - valid

        lines = [
            "=" * 60,
            "Agent Registry Validation Summary",
            "=" * 60,
            f"Total: {total} | Valid: {valid} | Invalid: {invalid}",
            ""
        ]

        if invalid > 0:
            lines.append("ERRORS:")
            lines.append("-" * 60)
            for filename, (is_valid, errors) in results.items():
                if not is_valid:
                    lines.append(f"\n{filename}:")
                    for error in errors:
                        lines.append(f"  ❌ {error}")

        if valid > 0:
            lines.append("\n" + "=" * 60)
            lines.append("VALID REGISTRATIONS:")
            lines.append("-" * 60)
            for filename, (is_valid, _) in results.items():
                if is_valid:
                    lines.append(f"  ✅ {filename}")

        return "\n".join(lines)
