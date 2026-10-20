"""
Agent Runtime Wrapper

Wraps agent execution with guardrail enforcement, audit logging,
and metric collection.
"""

import time
from typing import Any, Callable, Optional, Dict, List
from datetime import datetime
from functools import wraps

from .models import AgentRegistration, AutonomyLevel
from .database import AgentRegistryDB


class GuardrailViolation(Exception):
    """Raised when an agent violates a guardrail"""
    
    def __init__(self, agent_id: str, red_line: str, context: str = ""):
        self.agent_id = agent_id
        self.red_line = red_line
        self.context = context
        super().__init__(f"Guardrail violation by {agent_id}: {red_line}")


class EscalationRequired(Exception):
    """Raised when agent needs to escalate to human"""
    
    def __init__(self, agent_id: str, trigger: str, escalate_to: str):
        self.agent_id = agent_id
        self.trigger = trigger
        self.escalate_to = escalate_to
        super().__init__(
            f"Escalation required for {agent_id}: {trigger} -> {escalate_to}"
        )


class AgentRuntime:
    """Runtime wrapper for agent execution with guardrails"""

    def __init__(
        self,
        agent: AgentRegistration,
        db_path: str = "agent_registry.db"
    ):
        """
        Initialize runtime
        
        Args:
            agent: Agent registration
            db_path: Database path for logging
        """
        self.agent = agent
        self.db = AgentRegistryDB(db_path)
        self.execution_count = 0
        self.violation_count = 0

    def check_guardrails(self, action: str, context: Dict[str, Any]) -> bool:
        """
        Check if action violates guardrails
        
        Args:
            action: Action being attempted
            context: Action context
            
        Returns:
            True if action is allowed
            
        Raises:
            GuardrailViolation: If action violates a red line
        """
        # Check each red line
        for red_line in self.agent.get_red_lines():
            if self._violates_red_line(action, context, red_line):
                self.violation_count += 1
                
                # Log violation
                self.db.log_violation(
                    self.agent.agent_id,
                    'action_blocked',
                    red_line,
                    f"Action: {action}, Context: {context}",
                    'high'
                )
                
                raise GuardrailViolation(
                    self.agent.agent_id,
                    red_line,
                    f"Action '{action}' violates guardrail"
                )
        
        return True

    def _violates_red_line(
        self,
        action: str,
        context: Dict[str, Any],
        red_line: str
    ) -> bool:
        """
        Check if specific red line is violated
        
        This is a simplified implementation. In production, you'd have
        more sophisticated pattern matching and policy evaluation.
        """
        action_lower = action.lower()
        red_line_lower = red_line.lower()
        
        # Simple keyword matching
        if any(keyword in action_lower for keyword in red_line_lower.split()):
            return True
        
        # Check for specific violation patterns
        if "pii" in red_line_lower:
            # Check if PII is being handled without proper authorization
            if context.get('contains_pii') and not context.get('pii_authorized'):
                return True
        
        if "exfiltration" in red_line_lower:
            # Check for data export attempts
            if any(word in action_lower for word in ['export', 'send', 'upload', 'transmit']):
                if context.get('destination') == 'external':
                    return True
        
        if "internet" in red_line_lower or "external" in red_line_lower:
            # Check for network access
            if context.get('network_access') == 'internet':
                return True
        
        return False

    def check_tool_permission(self, tool_name: str, capability: str) -> bool:
        """Check if agent has permission to use tool with capability"""
        if not self.agent.can_use_tool(tool_name, capability):
            self.db.log_violation(
                self.agent.agent_id,
                'unauthorized_tool_use',
                f"Tool: {tool_name}, Capability: {capability}",
                f"Agent attempted to use {tool_name} with {capability}",
                'medium'
            )
            return False
        return True

    def check_escalation_triggers(
        self,
        context: Dict[str, Any]
    ) -> Optional[str]:
        """
        Check if escalation is triggered
        
        Returns:
            Escalation target if triggered, None otherwise
        """
        if not self.agent.guardrails.escalation:
            return None
        
        triggers = self.agent.guardrails.escalation.triggers
        
        for trigger in triggers:
            if self._trigger_matches(trigger, context):
                return self.agent.guardrails.escalation.to
        
        return None

    def _trigger_matches(self, trigger: str, context: Dict[str, Any]) -> bool:
        """Check if escalation trigger matches context"""
        trigger_lower = trigger.lower()
        
        if "confidence" in trigger_lower:
            confidence = context.get('confidence', 1.0)
            return confidence < 0.5
        
        if "policy" in trigger_lower:
            return context.get('policy_hit', False)
        
        if "error" in trigger_lower:
            return context.get('error_occurred', False)
        
        return False

    def execute_with_guardrails(
        self,
        func: Callable,
        *args,
        action_name: str = "",
        context: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Any:
        """
        Execute function with guardrail checks
        
        Args:
            func: Function to execute
            action_name: Name of the action
            context: Execution context
            *args, **kwargs: Function arguments
            
        Returns:
            Function result
            
        Raises:
            GuardrailViolation: If guardrails are violated
            EscalationRequired: If escalation is needed
        """
        if context is None:
            context = {}
        
        if not action_name:
            action_name = func.__name__
        
        self.execution_count += 1
        
        # Pre-execution checks
        self.check_guardrails(action_name, context)
        
        # Check autonomy level
        if self.agent.requires_approval():
            # In production, this would trigger an approval workflow
            approval = context.get('approval_granted', False)
            if not approval:
                self.db.log_audit_event(
                    self.agent.agent_id,
                    'approval_required',
                    {'action': action_name}
                )
                raise EscalationRequired(
                    self.agent.agent_id,
                    'requires_approval',
                    self.agent.owner.contact
                )
        
        # Check escalation triggers
        escalate_to = self.check_escalation_triggers(context)
        if escalate_to:
            self.db.log_escalation(
                self.agent.agent_id,
                'pre_execution_trigger',
                escalate_to,
                f"Action: {action_name}"
            )
            raise EscalationRequired(
                self.agent.agent_id,
                'escalation_trigger',
                escalate_to
            )
        
        # Execute with timing
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
            error = None
        except Exception as e:
            success = False
            error = str(e)
            result = None
            
            # Log error
            self.db.log_audit_event(
                self.agent.agent_id,
                'execution_error',
                {
                    'action': action_name,
                    'error': error
                }
            )
            
            # Check if error triggers escalation
            error_context = {**context, 'error_occurred': True, 'error': error}
            escalate_to = self.check_escalation_triggers(error_context)
            if escalate_to:
                self.db.log_escalation(
                    self.agent.agent_id,
                    'execution_error',
                    escalate_to,
                    error
                )
            
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log metrics
            self.db.log_metric(
                self.agent.agent_id,
                'execution_time',
                duration_ms,
                'ms'
            )
            
            self.db.log_metric(
                self.agent.agent_id,
                'execution_count',
                self.execution_count,
                'count'
            )
            
            # Log audit event
            self.db.log_audit_event(
                self.agent.agent_id,
                'execution',
                {
                    'action': action_name,
                    'success': success,
                    'duration_ms': duration_ms,
                    'error': error
                }
            )
        
        return result

    def execute_tool(
        self,
        tool_name: str,
        capability: str,
        func: Callable,
        *args,
        **kwargs
    ) -> Any:
        """Execute tool with permission and usage logging"""
        # Check permission
        if not self.check_tool_permission(tool_name, capability):
            raise GuardrailViolation(
                self.agent.agent_id,
                f"unauthorized tool use: {tool_name}.{capability}",
                "Agent does not have permission for this tool/capability"
            )
        
        # Execute with timing
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            success = True
        except Exception:
            success = False
            raise
        finally:
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Log tool usage
            self.db.log_tool_usage(
                self.agent.agent_id,
                tool_name,
                capability,
                success,
                duration_ms
            )
        
        return result

    def with_guardrails(self, action_name: str = "", context: Optional[Dict[str, Any]] = None):
        """
        Decorator for wrapping functions with guardrails
        
        Usage:
            @runtime.with_guardrails(action_name="process_data")
            def my_function(data):
                return processed_data
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.execute_with_guardrails(
                    func,
                    *args,
                    action_name=action_name or func.__name__,
                    context=context,
                    **kwargs
                )
            return wrapper
        return decorator

    def get_stats(self) -> Dict[str, Any]:
        """Get runtime statistics"""
        return {
            'agent_id': self.agent.agent_id,
            'execution_count': self.execution_count,
            'violation_count': self.violation_count,
            'autonomy_level': self.agent.autonomy.level,
            'environment': self.agent.environment.name,
        }

    def close(self):
        """Close database connection"""
        self.db.close()
