"""
Agent Registry Data Models
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
import json


class AgentStatus(Enum):
    """Agent lifecycle status"""
    DRAFT = "draft"
    REVIEW = "review"
    ACTIVE = "active"
    PARKED = "parked"  # Timeout/circuit breaker hold
    DEPRECATED = "deprecated"
    RETIRED = "retired"


class AutonomyLevel(Enum):
    """Agent autonomy levels following hospital residency model"""
    ADVICE = 0  # Can only provide advice
    ASSIST = 1  # Can assist but not act independently
    ACT_WITH_APPROVAL = 2  # Can act but requires approval
    ACT_WITH_ROLLBACK = 3  # Can act independently with rollback capability


@dataclass
class Owner:
    """Agent ownership information"""
    unit: str
    contact: str


@dataclass
class NetworkConfig:
    """Network access configuration"""
    egress: List[str]
    ingress: List[str]
    restrictions: List[str] = field(default_factory=list)


@dataclass
class Environment:
    """Agent runtime environment"""
    name: str
    runtime: List[str]
    network: NetworkConfig


@dataclass
class ToolPolicy:
    """Tool usage policy"""
    allow_pii: bool = False
    export_controls: List[str] = field(default_factory=list)


@dataclass
class Tool:
    """Agent tool definition"""
    name: str
    capabilities: List[str]
    limits: Dict[str, Any] = field(default_factory=dict)
    scopes: List[str] = field(default_factory=list)
    policy: Optional[ToolPolicy] = None

    def __post_init__(self):
        if self.policy and isinstance(self.policy, dict):
            self.policy = ToolPolicy(**self.policy)


@dataclass
class Autonomy:
    """Agent autonomy configuration"""
    level: int
    description: str = ""

    def __post_init__(self):
        if self.level not in [0, 1, 2, 3]:
            raise ValueError(f"Invalid autonomy level: {self.level}")


@dataclass
class Escalation:
    """Escalation configuration"""
    triggers: List[str]
    to: str


@dataclass
class Rollback:
    """Rollback configuration"""
    supported: bool
    procedure: str = ""


@dataclass
class Guardrails:
    """Agent guardrails and safety constraints"""
    red_lines: List[str]
    escalation: Optional[Escalation] = None
    rollback: Optional[Rollback] = None

    def __post_init__(self):
        if self.escalation and isinstance(self.escalation, dict):
            self.escalation = Escalation(**self.escalation)
        if self.rollback and isinstance(self.rollback, dict):
            self.rollback = Rollback(**self.rollback)


@dataclass
class IO:
    """Input/Output configuration"""
    inputs: List[str] = field(default_factory=list)
    outputs: List[str] = field(default_factory=list)
    formats: List[str] = field(default_factory=list)


@dataclass
class DataAccess:
    """Data access configuration"""
    catalog: List[str] = field(default_factory=list)
    retention_days: int = 30


@dataclass
class Memory:
    """Memory configuration"""
    short_term: Dict[str, Any] = field(default_factory=dict)
    long_term: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Training:
    """Training configuration"""
    curriculum: List[str] = field(default_factory=list)
    feedback_loops: List[str] = field(default_factory=list)
    evaluation: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CognitiveLoop:
    """Cognitive loop configuration"""
    memory: Dict[str, Any] = field(default_factory=dict)
    planning: Dict[str, Any] = field(default_factory=dict)
    action: Dict[str, Any] = field(default_factory=dict)
    reflection: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Evaluation:
    """Evaluation configuration"""
    type: str = "agent"
    environment_benchmarks: List[Dict[str, str]] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    review_cycle_days: int = 30


@dataclass
class Runbook:
    """Runbook definition"""
    id: str
    name: str
    steps: List[str]


@dataclass
class Audit:
    """Audit configuration"""
    logging: List[str]
    retention_days: int = 90
    explainability: Dict[str, bool] = field(default_factory=dict)


@dataclass
class Metadata:
    """Registration metadata"""
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    created_by: str = ""
    status: str = "draft"
    tags: List[str] = field(default_factory=list)


@dataclass
class AgentRegistration:
    """Complete agent registration"""
    agent_id: str
    title: str
    version: str
    owner: Owner
    environment: Environment
    tools: List[Tool]
    system_prompt: str
    autonomy: Autonomy
    guardrails: Guardrails
    
    # Optional fields
    reasoning_overlays: List[str] = field(default_factory=list)
    io: Optional[IO] = None
    data_access: Optional[DataAccess] = None
    memory: Optional[Memory] = None
    training: Optional[Training] = None
    cognitive_loop: Optional[CognitiveLoop] = None
    evaluation: Optional[Evaluation] = None
    kpis: List[str] = field(default_factory=list)
    runbooks: List[Runbook] = field(default_factory=list)
    audit: Optional[Audit] = None
    metadata: Optional[Metadata] = None

    def __post_init__(self):
        """Convert dict fields to proper dataclass instances"""
        if isinstance(self.owner, dict):
            self.owner = Owner(**self.owner)
        
        if isinstance(self.environment, dict):
            env_data = self.environment.copy()
            if isinstance(env_data.get('network'), dict):
                env_data['network'] = NetworkConfig(**env_data['network'])
            self.environment = Environment(**env_data)
        
        if self.tools and isinstance(self.tools[0], dict):
            self.tools = [Tool(**t) if isinstance(t, dict) else t for t in self.tools]
        
        if isinstance(self.autonomy, dict):
            self.autonomy = Autonomy(**self.autonomy)
        
        if isinstance(self.guardrails, dict):
            self.guardrails = Guardrails(**self.guardrails)
        
        if self.io and isinstance(self.io, dict):
            self.io = IO(**self.io)
        
        if self.data_access and isinstance(self.data_access, dict):
            self.data_access = DataAccess(**self.data_access)
        
        if self.memory and isinstance(self.memory, dict):
            self.memory = Memory(**self.memory)
        
        if self.training and isinstance(self.training, dict):
            self.training = Training(**self.training)
        
        if self.cognitive_loop and isinstance(self.cognitive_loop, dict):
            self.cognitive_loop = CognitiveLoop(**self.cognitive_loop)
        
        if self.evaluation and isinstance(self.evaluation, dict):
            self.evaluation = Evaluation(**self.evaluation)
        
        if self.runbooks and isinstance(self.runbooks[0], dict):
            self.runbooks = [Runbook(**r) if isinstance(r, dict) else r for r in self.runbooks]
        
        if self.audit and isinstance(self.audit, dict):
            self.audit = Audit(**self.audit)
        
        if not self.metadata:
            self.metadata = Metadata()
        elif isinstance(self.metadata, dict):
            self.metadata = Metadata(**self.metadata)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary, omitting unset optional fields (None) so the result validates against the schema"""
        return asdict(self, dict_factory=lambda items: {k: v for k, v in items if v is not None})

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentRegistration':
        """Create from dictionary"""
        return cls(**data)

    @classmethod
    def from_json(cls, json_str: str) -> 'AgentRegistration':
        """Create from JSON string"""
        data = json.loads(json_str)
        return cls.from_dict(data)

    @classmethod
    def from_file(cls, filepath: str) -> 'AgentRegistration':
        """Load from JSON file"""
        with open(filepath, 'r', encoding='utf-8') as f:
            return cls.from_json(f.read())

    def save_to_file(self, filepath: str):
        """Save to JSON file"""
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(self.to_json())

    def get_autonomy_level(self) -> AutonomyLevel:
        """Get autonomy level enum"""
        return AutonomyLevel(self.autonomy.level)

    def get_status(self) -> AgentStatus:
        """Get status enum"""
        if self.metadata:
            return AgentStatus(self.metadata.status)
        return AgentStatus.DRAFT

    def can_use_tool(self, tool_name: str, capability: str) -> bool:
        """Check if agent can use a tool with specific capability"""
        for tool in self.tools:
            if tool.name == tool_name:
                return capability in tool.capabilities
        return False

    def get_red_lines(self) -> List[str]:
        """Get all guardrail red lines"""
        return self.guardrails.red_lines

    def requires_approval(self) -> bool:
        """Check if agent requires approval for actions"""
        return self.autonomy.level == AutonomyLevel.ACT_WITH_APPROVAL.value

    def supports_rollback(self) -> bool:
        """Check if agent supports rollback"""
        return (
            self.guardrails.rollback is not None and
            self.guardrails.rollback.supported
        )
