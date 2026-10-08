"""
Safety Guards - Integration Fixes for Production Readiness

Implements:
1. No-Op After Timeout guard
2. PII detection in rationales
3. Two-person rule enforcement
4. Standardized event schema
"""

import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass


# ============================================================================
# 1. NO-OP AFTER TIMEOUT GUARD
# ============================================================================

def enforce_timeout_guard(checkpoint_system, service):
    """
    Expired checkpoints auto-set agent to 'parked', not 'active'
    
    Run this periodically (e.g., hourly cron job)
    """
    cursor = checkpoint_system.db.conn.cursor()
    
    # Find expired checkpoints
    cursor.execute("""
        SELECT checkpoint_id, agent_id, checkpoint_type
        FROM human_checkpoints
        WHERE status = 'pending'
        AND expires_at < datetime('now')
    """)
    
    expired = cursor.fetchall()
    
    for checkpoint_id, agent_id, checkpoint_type in expired:
        # Mark checkpoint as timeout
        cursor.execute("""
            UPDATE human_checkpoints
            SET status = 'timeout'
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        # Park the agent (not active)
        try:
            service.update_status(agent_id, 'parked', 'system-timeout-guard')
            
            # Log
            checkpoint_system.db.log_audit_event(
                agent_id,
                'auto_parked_timeout',
                {
                    'checkpoint_id': checkpoint_id,
                    'checkpoint_type': checkpoint_type,
                    'reason': 'Approval timeout exceeded'
                },
                'system-timeout-guard'
            )
            
            print(f"⏸️  Agent {agent_id} auto-parked due to timeout: {checkpoint_id}")
        except Exception as e:
            print(f"⚠️  Failed to park agent {agent_id}: {e}")
    
    checkpoint_system.db.conn.commit()
    
    return len(expired)


# ============================================================================
# 2. PII DETECTION IN RATIONALES
# ============================================================================

class PIIDetector:
    """Detect and redact PII in free-text rationales"""
    
    # Patterns for common PII
    PATTERNS = {
        'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
        'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
        'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
        'credit_card': re.compile(r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b'),
        'ip_address': re.compile(r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'),
    }
    
    @classmethod
    def detect(cls, text: str) -> List[Dict[str, Any]]:
        """
        Detect PII in text
        
        Returns:
            List of detections with type and location
        """
        detections = []
        
        for pii_type, pattern in cls.PATTERNS.items():
            matches = pattern.finditer(text)
            for match in matches:
                detections.append({
                    'type': pii_type,
                    'value': match.group(),
                    'start': match.start(),
                    'end': match.end()
                })
        
        return detections
    
    @classmethod
    def redact(cls, text: str) -> Tuple[str, List[Dict]]:
        """
        Redact PII from text
        
        Returns:
            (redacted_text, list_of_redactions)
        """
        detections = cls.detect(text)
        
        if not detections:
            return text, []
        
        # Sort by position (reverse) to maintain indices
        detections.sort(key=lambda x: x['start'], reverse=True)
        
        redacted = text
        for detection in detections:
            redaction = f"[{detection['type'].upper()}_REDACTED]"
            redacted = redacted[:detection['start']] + redaction + redacted[detection['end']:]
        
        return redacted, detections
    
    @classmethod
    def validate_rationale(cls, rationale: str, allow_pii: bool = False) -> Tuple[bool, str, List[Dict]]:
        """
        Validate rationale for PII
        
        Returns:
            (is_valid, safe_rationale, detections)
        """
        detections = cls.detect(rationale)
        
        if not detections:
            return True, rationale, []
        
        if not allow_pii:
            # Redact PII
            redacted, detections = cls.redact(rationale)
            return True, redacted, detections
        else:
            # PII allowed but warn
            return True, rationale, detections


# ============================================================================
# 3. TWO-PERSON RULE ENFORCEMENT
# ============================================================================

class TwoPersonRuleEnforcer:
    """Enforce cryptographic two-person rule for high-risk approvals"""
    
    @staticmethod
    def hash_approver(approver_id: str, checkpoint_id: str) -> str:
        """
        Generate cryptographic hash of approver for this checkpoint
        
        Prevents same person from approving twice
        """
        combined = f"{approver_id}:{checkpoint_id}".encode('utf-8')
        return hashlib.sha256(combined).hexdigest()
    
    @classmethod
    def check_distinct_approvers(
        cls,
        checkpoint_id: str,
        new_approver: str,
        existing_approvers: List[str]
    ) -> Tuple[bool, Optional[str]]:
        """
        Check if new approver is distinct from existing
        
        Returns:
            (is_distinct, error_message)
        """
        new_hash = cls.hash_approver(new_approver, checkpoint_id)
        
        for existing in existing_approvers:
            existing_hash = cls.hash_approver(existing, checkpoint_id)
            if new_hash == existing_hash:
                return False, f"Same approver cannot approve multiple times: {new_approver}"
        
        return True, None
    
    @classmethod
    def enforce_two_person_rule(
        cls,
        checkpoint_system,
        checkpoint_id: str,
        new_approver: str,
        required_count: int = 2
    ) -> Tuple[bool, Optional[str]]:
        """
        Enforce two-person rule for checkpoint
        
        Returns:
            (is_allowed, error_message)
        """
        # Get checkpoint
        checkpoint = checkpoint_system.get_checkpoint_status(checkpoint_id)
        if not checkpoint:
            return False, "Checkpoint not found"
        
        # Get existing approvals from audit log
        cursor = checkpoint_system.db.conn.cursor()
        cursor.execute("""
            SELECT user FROM audit_logs
            WHERE agent_id = ?
            AND event_type = 'checkpoint_approved'
            AND event_data LIKE ?
        """, (checkpoint['agent_id'], f'%{checkpoint_id}%'))
        
        existing_approvers = [row[0] for row in cursor.fetchall()]
        
        # Check if new approver is distinct
        is_distinct, error = cls.check_distinct_approvers(
            checkpoint_id,
            new_approver,
            existing_approvers
        )
        
        if not is_distinct:
            return False, error
        
        # Check if required count met
        total_approvers = len(existing_approvers) + 1
        if total_approvers < required_count:
            return False, f"Requires {required_count} distinct approvers, only {total_approvers} provided"
        
        return True, None


# ============================================================================
# 4. STANDARDIZED EVENT SCHEMA
# ============================================================================

@dataclass
class StandardEvent:
    """
    Standardized event schema for all registry operations
    
    Ensures consistent logging across all systems
    """
    # Core fields
    event_id: str
    timestamp: str
    event_type: str
    
    # Context
    agent_id: str
    stage: str  # registration, approval, runtime, violation, etc.
    actor: str  # who performed the action
    
    # Decision tracking
    rationale: Optional[str] = None
    policy_flags: List[str] = None  # policy violations, concerns
    
    # Performance
    latency_ms: Optional[int] = None
    
    # Reliability contract fields
    redundancy_level: Optional[int] = None
    circuit_breaker_state: Optional[str] = None
    stochastic_tolerance: Optional[float] = None
    
    # Outcome
    success: bool = True
    error_message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging"""
        return {
            'event_id': self.event_id,
            'timestamp': self.timestamp,
            'event_type': self.event_type,
            'agent_id': self.agent_id,
            'stage': self.stage,
            'actor': self.actor,
            'rationale': self.rationale,
            'policy_flags': self.policy_flags or [],
            'latency_ms': self.latency_ms,
            'redundancy_level': self.redundancy_level,
            'circuit_breaker_state': self.circuit_breaker_state,
            'stochastic_tolerance': self.stochastic_tolerance,
            'success': self.success,
            'error_message': self.error_message
        }
    
    def emit_to_mlflow(self):
        """Emit event to MLflow"""
        try:
            import mlflow
            mlflow.log_dict(self.to_dict(), f"events/{self.event_id}.json")
        except ImportError:
            pass
    
    def emit_to_wandb(self):
        """Emit event to W&B"""
        try:
            import wandb
            wandb.log(self.to_dict())
        except ImportError:
            pass


class EventLogger:
    """Centralized event logger with standardized schema"""
    
    def __init__(self, db):
        self.db = db
    
    def log_event(
        self,
        event_type: str,
        agent_id: str,
        stage: str,
        actor: str,
        rationale: Optional[str] = None,
        policy_flags: Optional[List[str]] = None,
        latency_ms: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Log standardized event
        
        Returns:
            event_id
        """
        event_id = f"evt-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Create event
        event = StandardEvent(
            event_id=event_id,
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            agent_id=agent_id,
            stage=stage,
            actor=actor,
            rationale=rationale,
            policy_flags=policy_flags,
            latency_ms=latency_ms,
            success=success,
            error_message=error_message,
            **kwargs
        )
        
        # Log to database
        self.db.log_audit_event(
            agent_id,
            event_type,
            event.to_dict(),
            actor
        )
        
        # Emit to tracking systems
        event.emit_to_mlflow()
        event.emit_to_wandb()
        
        return event_id


# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

def bind_reliability_contract(checkpoint_system, agent_id: str, contract: Dict[str, Any]):
    """
    Bind checkpoint to reliability contract
    
    Links checkpoint state to redundancy, circuit breaker, stochastic tolerance
    """
    cursor = checkpoint_system.db.conn.cursor()
    
    # Add reliability contract fields to audit
    checkpoint_system.db.log_audit_event(
        agent_id,
        'reliability_contract_bound',
        {
            'redundancy_level': contract.get('redundancy_level', 1),
            'circuit_breaker_enabled': contract.get('circuit_breaker', False),
            'stochastic_tolerance': contract.get('stochastic_tolerance', 0.0),
            'bounded_runtime': contract.get('bounded_runtime', True)
        },
        'system-reliability'
    )


def circuit_breaker_check(agent_id: str, checkpoint_system) -> Tuple[bool, str]:
    """
    Check if circuit breaker should open for agent
    
    Opens circuit if:
    - Too many failures recently
    - Checkpoint timeout
    - Violations exceed threshold
    
    Returns:
        (is_open, reason)
    """
    cursor = checkpoint_system.db.conn.cursor()
    
    # Check recent failures (last hour)
    cursor.execute("""
        SELECT COUNT(*) FROM audit_logs
        WHERE agent_id = ?
        AND timestamp >= datetime('now', '-1 hour')
        AND event_type LIKE '%error%'
    """, (agent_id,))
    
    error_count = cursor.fetchone()[0]
    
    if error_count >= 5:
        return True, f"Circuit breaker opened: {error_count} errors in last hour"
    
    # Check for pending expired checkpoints
    cursor.execute("""
        SELECT COUNT(*) FROM human_checkpoints
        WHERE agent_id = ?
        AND status = 'pending'
        AND expires_at < datetime('now')
    """, (agent_id,))
    
    expired_count = cursor.fetchone()[0]
    
    if expired_count > 0:
        return True, f"Circuit breaker opened: {expired_count} expired checkpoint(s)"
    
    # Check unresolved violations
    violations = checkpoint_system.db.get_violations(agent_id=agent_id, resolved=False)
    
    if len(violations) >= 3:
        return True, f"Circuit breaker opened: {len(violations)} unresolved violations"
    
    return False, ""


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def safe_resolve_checkpoint(
    checkpoint_system,
    checkpoint_id: str,
    decided_by: str,
    decision,
    rationale: str,
    enforce_two_person: bool = True
) -> Tuple[bool, Optional[str]]:
    """
    Safely resolve checkpoint with all guards
    
    Returns:
        (success, error_message)
    """
    # 1. PII check in rationale
    is_valid, safe_rationale, pii_detections = PIIDetector.validate_rationale(rationale)
    
    if pii_detections:
        print(f"⚠️  PII detected and redacted in rationale: {len(pii_detections)} occurrence(s)")
        rationale = safe_rationale
    
    # 2. Two-person rule (if Level 2+)
    if enforce_two_person:
        checkpoint = checkpoint_system.get_checkpoint_status(checkpoint_id)
        if checkpoint:
            required_auth = checkpoint['required_authority']
            if any(auth in ['senior_reviewer', 'security_officer', 'dean'] 
                   for auth in required_auth):
                # Enforce two-person rule
                is_allowed, error = TwoPersonRuleEnforcer.enforce_two_person_rule(
                    checkpoint_system,
                    checkpoint_id,
                    decided_by,
                    required_count=2
                )
                
                if not is_allowed:
                    return False, error
    
    # 3. Circuit breaker check
    checkpoint = checkpoint_system.get_checkpoint_status(checkpoint_id)
    if checkpoint:
        is_open, reason = circuit_breaker_check(checkpoint['agent_id'], checkpoint_system)
        if is_open:
            return False, f"Circuit breaker open: {reason}"
    
    # 4. Resolve with safe rationale
    success = checkpoint_system.resolve_checkpoint(
        checkpoint_id,
        decided_by,
        decision,
        rationale
    )
    
    if not success:
        return False, "Checkpoint resolution failed (may be already resolved or expired)"
    
    return True, None


def periodic_maintenance(checkpoint_system, service):
    """
    Run periodic maintenance tasks
    
    Call this hourly via cron
    """
    print("🔧 Running periodic maintenance...")
    
    # 1. Enforce timeout guards
    parked_count = enforce_timeout_guard(checkpoint_system, service)
    print(f"   Parked {parked_count} agent(s) due to timeout")
    
    # 2. Check circuit breakers
    cursor = checkpoint_system.db.conn.cursor()
    cursor.execute("""
        SELECT DISTINCT agent_id FROM human_checkpoints
        WHERE status = 'pending'
    """)
    
    agents_with_pending = [row[0] for row in cursor.fetchall()]
    
    circuit_breaks = 0
    for agent_id in agents_with_pending:
        is_open, reason = circuit_breaker_check(agent_id, checkpoint_system)
        if is_open:
            print(f"   ⚠️  {agent_id}: {reason}")
            service.update_status(agent_id, 'parked', 'system-circuit-breaker')
            circuit_breaks += 1
    
    print(f"   Circuit breaker triggered for {circuit_breaks} agent(s)")
    
    # 3. Clean up old resolved checkpoints (older than 365 days)
    cursor.execute("""
        DELETE FROM human_checkpoints
        WHERE status IN ('approved', 'rejected')
        AND decided_at < datetime('now', '-365 days')
    """)
    deleted = cursor.rowcount
    checkpoint_system.db.conn.commit()
    
    print(f"   Cleaned up {deleted} old checkpoint(s)")
    
    print("✅ Maintenance complete\n")


if __name__ == "__main__":
    # Example usage
    from agents.registry import HumanCheckpointSystem, AgentRegistryService
    
    checkpoint_system = HumanCheckpointSystem()
    service = AgentRegistryService()
    
    periodic_maintenance(checkpoint_system, service)
    
    checkpoint_system.close()
    service.close()
