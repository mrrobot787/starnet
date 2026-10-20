"""
Human Checkpoint System

Enforces human-in-the-loop decision points throughout the agent registry lifecycle.
This module makes the safety culture operational, not just aspirational.
"""

import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field


class CheckpointType(Enum):
    """Types of human checkpoints"""
    REGISTRATION_REVIEW = "registration_review"
    APPROVAL_REQUIRED = "approval_required"
    VIOLATION_ADJUDICATION = "violation_adjudication"
    DEPRECATION_APPROVAL = "deprecation_approval"
    EMERGENCY_SHUTDOWN = "emergency_shutdown"
    MM_REVIEW = "mm_review"
    ESCALATION = "escalation"


class CheckpointStatus(Enum):
    """Status of checkpoint"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    TIMEOUT = "timeout"


class ApprovalAuthority(Enum):
    """Approval authority levels"""
    ANY_OPERATOR = "any_operator"
    SENIOR_OPERATOR = "senior_operator"
    REVIEWER = "reviewer"
    SENIOR_REVIEWER = "senior_reviewer"
    SECURITY_OFFICER = "security_officer"
    COMPLIANCE_OFFICER = "compliance_officer"
    DEAN = "dean"


@dataclass
class CheckpointRecord:
    """Record of a human checkpoint"""
    checkpoint_id: str
    checkpoint_type: CheckpointType
    agent_id: str
    status: CheckpointStatus
    required_authority: List[ApprovalAuthority]
    created_at: str
    created_by: str
    
    # Context
    context: Dict[str, Any] = field(default_factory=dict)
    
    # Decision
    decided_by: Optional[str] = None
    decided_at: Optional[str] = None
    decision_rationale: Optional[str] = None
    
    # Metadata
    expires_at: Optional[str] = None
    escalated_to: Optional[str] = None
    escalation_reason: Optional[str] = None


class HumanCheckpointSystem:
    """Enforces human checkpoints in the agent registry"""

    def __init__(self, db_path: str = "agent_registry.db"):
        from .database import AgentRegistryDB
        self.db = AgentRegistryDB(db_path)
        self._init_checkpoint_table()

    def _init_checkpoint_table(self):
        """Initialize checkpoint tracking table"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS human_checkpoints (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                checkpoint_id TEXT UNIQUE NOT NULL,
                checkpoint_type TEXT NOT NULL,
                agent_id TEXT NOT NULL,
                status TEXT DEFAULT 'pending',
                required_authority TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by TEXT,
                context TEXT,
                decided_by TEXT,
                decided_at TIMESTAMP,
                decision_rationale TEXT,
                expires_at TIMESTAMP,
                escalated_to TEXT,
                escalation_reason TEXT
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoint_status 
            ON human_checkpoints(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoint_agent 
            ON human_checkpoints(agent_id)
        """)
        
        self.db.conn.commit()

    def require_checkpoint(
        self,
        checkpoint_type: CheckpointType,
        agent_id: str,
        required_authority: List[ApprovalAuthority],
        context: Dict[str, Any],
        created_by: str,
        timeout_hours: int = 24
    ) -> str:
        """
        Create a required human checkpoint
        
        Returns:
            checkpoint_id for tracking
        """
        checkpoint_id = f"checkpoint-{agent_id}-{checkpoint_type.value}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        expires_at = (datetime.now() + timedelta(hours=timeout_hours)).isoformat()
        
        cursor = self.db.conn.cursor()
        cursor.execute("""
            INSERT INTO human_checkpoints
            (checkpoint_id, checkpoint_type, agent_id, status, required_authority,
             created_by, context, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            checkpoint_id,
            checkpoint_type.value,
            agent_id,
            CheckpointStatus.PENDING.value,
            json.dumps([a.value for a in required_authority]),
            created_by,
            json.dumps(context),
            expires_at
        ))
        self.db.conn.commit()
        
        # Send notifications
        self._notify_checkpoint_required(
            checkpoint_id,
            checkpoint_type,
            agent_id,
            required_authority,
            context,
            timeout_hours
        )
        
        return checkpoint_id

    def resolve_checkpoint(
        self,
        checkpoint_id: str,
        decided_by: str,
        decision: CheckpointStatus,
        rationale: str
    ) -> bool:
        """
        Resolve a checkpoint with human decision
        
        Returns:
            True if successful, False if checkpoint not found or invalid
        """
        # Verify checkpoint exists and is pending
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT status, required_authority, expires_at
            FROM human_checkpoints
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        row = cursor.fetchone()
        if not row:
            return False
        
        current_status, required_auth_json, expires_at = row
        
        if current_status != CheckpointStatus.PENDING.value:
            return False
        
        # Check if expired
        if expires_at and datetime.fromisoformat(expires_at) < datetime.now():
            cursor.execute("""
                UPDATE human_checkpoints
                SET status = ?
                WHERE checkpoint_id = ?
            """, (CheckpointStatus.TIMEOUT.value, checkpoint_id))
            self.db.conn.commit()
            return False
        
        # TODO: Verify decided_by has required authority
        # In production, this would check against user roles database
        
        # Record decision
        cursor.execute("""
            UPDATE human_checkpoints
            SET status = ?,
                decided_by = ?,
                decided_at = CURRENT_TIMESTAMP,
                decision_rationale = ?
            WHERE checkpoint_id = ?
        """, (decision.value, decided_by, rationale, checkpoint_id))
        
        self.db.conn.commit()
        
        # Log audit event
        cursor.execute("""
            SELECT agent_id, checkpoint_type FROM human_checkpoints
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        agent_id, checkpoint_type = cursor.fetchone()
        
        self.db.log_audit_event(
            agent_id,
            f'checkpoint_{decision.value}',
            {
                'checkpoint_id': checkpoint_id,
                'checkpoint_type': checkpoint_type,
                'decided_by': decided_by,
                'rationale': rationale
            }
        )
        
        return True

    def check_approval_required(
        self,
        agent_id: str,
        autonomy_level: int,
        has_internet: bool = False,
        has_pii: bool = False
    ) -> Tuple[bool, List[ApprovalAuthority]]:
        """
        Determine if approval is required and by whom
        
        Returns:
            (requires_approval, list_of_required_authorities)
        """
        required = []
        
        if autonomy_level == 0:
            required = [ApprovalAuthority.ANY_OPERATOR]
        elif autonomy_level == 1:
            required = [ApprovalAuthority.SENIOR_OPERATOR]
        elif autonomy_level == 2:
            required = [ApprovalAuthority.SENIOR_REVIEWER, ApprovalAuthority.SECURITY_OFFICER]
        elif autonomy_level == 3:
            required = [
                ApprovalAuthority.DEAN,
                ApprovalAuthority.SECURITY_OFFICER,
                ApprovalAuthority.COMPLIANCE_OFFICER
            ]
        
        # Special cases
        if has_internet and autonomy_level >= 2:
            if ApprovalAuthority.DEAN not in required:
                required.append(ApprovalAuthority.DEAN)
        
        if has_pii:
            if ApprovalAuthority.COMPLIANCE_OFFICER not in required:
                required.append(ApprovalAuthority.COMPLIANCE_OFFICER)
        
        return len(required) > 0, required

    def get_pending_checkpoints(
        self,
        authority: Optional[ApprovalAuthority] = None
    ) -> List[Dict[str, Any]]:
        """Get all pending checkpoints, optionally filtered by authority"""
        cursor = self.db.conn.cursor()
        
        query = """
            SELECT * FROM human_checkpoints
            WHERE status = 'pending'
            AND (expires_at IS NULL OR expires_at > datetime('now'))
        """
        
        if authority:
            query += " AND required_authority LIKE ?"
            cursor.execute(query, (f'%{authority.value}%',))
        else:
            cursor.execute(query)
        
        checkpoints = []
        for row in cursor.fetchall():
            checkpoint = dict(row)
            checkpoint['required_authority'] = json.loads(checkpoint['required_authority'])
            checkpoint['context'] = json.loads(checkpoint['context']) if checkpoint['context'] else {}
            checkpoints.append(checkpoint)
        
        return checkpoints

    def escalate_checkpoint(
        self,
        checkpoint_id: str,
        escalated_to: str,
        escalation_reason: str
    ) -> bool:
        """Escalate checkpoint to higher authority"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            UPDATE human_checkpoints
            SET status = ?,
                escalated_to = ?,
                escalation_reason = ?
            WHERE checkpoint_id = ?
            AND status = 'pending'
        """, (CheckpointStatus.ESCALATED.value, escalated_to, escalation_reason, checkpoint_id))
        
        self.db.conn.commit()
        
        # Send escalation notification
        cursor.execute("""
            SELECT agent_id, checkpoint_type, context
            FROM human_checkpoints
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        row = cursor.fetchone()
        if row:
            agent_id, checkpoint_type, context = row
            self._notify_escalation(
                checkpoint_id,
                agent_id,
                checkpoint_type,
                escalated_to,
                escalation_reason,
                json.loads(context) if context else {}
            )
        
        return cursor.rowcount > 0

    def _notify_checkpoint_required(
        self,
        checkpoint_id: str,
        checkpoint_type: CheckpointType,
        agent_id: str,
        required_authority: List[ApprovalAuthority],
        context: Dict[str, Any],
        timeout_hours: int
    ):
        """Send notification that checkpoint is required"""
        # In production, this would send actual emails/Slack messages
        # For now, we log to console and audit log
        
        message = f"""
╔══════════════════════════════════════════════════════════════╗
║           🚨 HUMAN CHECKPOINT REQUIRED 🚨                    ║
╚══════════════════════════════════════════════════════════════╝

Checkpoint ID: {checkpoint_id}
Type: {checkpoint_type.value}
Agent: {agent_id}

Required Approvers:
{chr(10).join(f'  - {auth.value}' for auth in required_authority)}

Timeout: {timeout_hours} hours
Expires: {(datetime.now() + timedelta(hours=timeout_hours)).strftime('%Y-%m-%d %H:%M')}

Context:
{json.dumps(context, indent=2)}

To review and approve:
  python -m agents.registry.cli show {agent_id}
  python approve_checkpoint.py {checkpoint_id}

────────────────────────────────────────────────────────────────
        """
        
        print(message)
        
        # Log to audit
        self.db.log_audit_event(
            agent_id,
            'checkpoint_required',
            {
                'checkpoint_id': checkpoint_id,
                'checkpoint_type': checkpoint_type.value,
                'required_authority': [a.value for a in required_authority],
                'timeout_hours': timeout_hours
            }
        )

    def _notify_escalation(
        self,
        checkpoint_id: str,
        agent_id: str,
        checkpoint_type: str,
        escalated_to: str,
        reason: str,
        context: Dict[str, Any]
    ):
        """Send escalation notification"""
        message = f"""
╔══════════════════════════════════════════════════════════════╗
║           ⬆️  CHECKPOINT ESCALATED ⬆️                        ║
╚══════════════════════════════════════════════════════════════╝

Checkpoint ID: {checkpoint_id}
Type: {checkpoint_type}
Agent: {agent_id}
Escalated To: {escalated_to}

Reason for Escalation:
{reason}

Original Context:
{json.dumps(context, indent=2)}

Action Required:
This decision now requires your review and approval.

  python -m agents.registry.cli show {agent_id}
  python approve_checkpoint.py {checkpoint_id}

────────────────────────────────────────────────────────────────
        """
        
        print(message)

    def get_checkpoint_status(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get current status of a checkpoint"""
        cursor = self.db.conn.cursor()
        cursor.execute("""
            SELECT * FROM human_checkpoints
            WHERE checkpoint_id = ?
        """, (checkpoint_id,))
        
        row = cursor.fetchone()
        if row:
            checkpoint = dict(row)
            checkpoint['required_authority'] = json.loads(checkpoint['required_authority'])
            checkpoint['context'] = json.loads(checkpoint['context']) if checkpoint['context'] else {}
            return checkpoint
        return None

    def close(self):
        """Close database connection"""
        self.db.close()


# Convenience functions for common checkpoint scenarios

def require_registration_approval(
    agent_id: str,
    agent_data: Dict[str, Any],
    requester: str,
    db_path: str = "agent_registry.db"
) -> str:
    """Require human approval for agent registration"""
    checkpoint_system = HumanCheckpointSystem(db_path)
    
    autonomy_level = agent_data.get('autonomy', {}).get('level', 0)
    has_internet = 'internet' in agent_data.get('environment', {}).get('network', {}).get('egress', [])
    has_pii = any(
        tool.get('policy', {}).get('allow_pii', False)
        for tool in agent_data.get('tools', [])
    )
    
    requires_approval, required_authority = checkpoint_system.check_approval_required(
        agent_id,
        autonomy_level,
        has_internet,
        has_pii
    )
    
    if not requires_approval:
        checkpoint_system.close()
        return ""  # No checkpoint needed
    
    # Determine timeout based on autonomy
    timeout_hours = {
        0: 4,
        1: 24,
        2: 48,
        3: 120  # 5 days
    }.get(autonomy_level, 24)
    
    checkpoint_id = checkpoint_system.require_checkpoint(
        CheckpointType.REGISTRATION_REVIEW,
        agent_id,
        required_authority,
        {
            'agent_data': agent_data,
            'autonomy_level': autonomy_level,
            'has_internet': has_internet,
            'has_pii': has_pii
        },
        requester,
        timeout_hours
    )
    
    checkpoint_system.close()
    return checkpoint_id


def require_violation_review(
    agent_id: str,
    violation_id: int,
    violation_details: Dict[str, Any],
    reporter: str,
    db_path: str = "agent_registry.db"
) -> str:
    """Require human review of high/critical severity violation"""
    checkpoint_system = HumanCheckpointSystem(db_path)
    
    severity = violation_details.get('severity', 'medium')
    
    if severity in ['high', 'critical']:
        required_authority = [ApprovalAuthority.SENIOR_REVIEWER, ApprovalAuthority.SECURITY_OFFICER]
        timeout_hours = 4
    else:
        checkpoint_system.close()
        return ""  # No checkpoint for low/medium violations
    
    checkpoint_id = checkpoint_system.require_checkpoint(
        CheckpointType.VIOLATION_ADJUDICATION,
        agent_id,
        required_authority,
        {
            'violation_id': violation_id,
            'violation_details': violation_details
        },
        reporter,
        timeout_hours
    )
    
    checkpoint_system.close()
    return checkpoint_id


def require_deprecation_approval(
    agent_id: str,
    reason: str,
    requester: str,
    db_path: str = "agent_registry.db"
) -> str:
    """Require approval for agent deprecation"""
    checkpoint_system = HumanCheckpointSystem(db_path)
    
    checkpoint_id = checkpoint_system.require_checkpoint(
        CheckpointType.DEPRECATION_APPROVAL,
        agent_id,
        [ApprovalAuthority.SENIOR_OPERATOR],
        {
            'reason': reason
        },
        requester,
        24  # 24 hour timeout
    )
    
    checkpoint_system.close()
    return checkpoint_id
