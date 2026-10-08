"""
AML University Agent Registry System

Hospital metaphor: manage agent 'residents' across wards with 
proper credentials, tools, autonomy levels, and guardrails.
"""

from .models import AgentRegistration, AgentStatus, AutonomyLevel
from .service import AgentRegistryService
from .validator import AgentValidator
from .runtime import AgentRuntime, GuardrailViolation
from .checkpoints import (
    HumanCheckpointSystem,
    CheckpointType,
    CheckpointStatus,
    ApprovalAuthority,
    require_registration_approval,
    require_violation_review,
    require_deprecation_approval
)
from .monitoring import MonitoringSystem
from .mm_dashboard import MMReviewDashboard

__all__ = [
    'AgentRegistration',
    'AgentStatus',
    'AutonomyLevel',
    'AgentRegistryService',
    'AgentValidator',
    'AgentRuntime',
    'GuardrailViolation',
    'HumanCheckpointSystem',
    'CheckpointType',
    'CheckpointStatus',
    'ApprovalAuthority',
    'require_registration_approval',
    'require_violation_review',
    'require_deprecation_approval',
    'MonitoringSystem',
    'MMReviewDashboard',
]
