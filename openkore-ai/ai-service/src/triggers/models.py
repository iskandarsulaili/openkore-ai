"""
Trigger System Data Models
Defines the core data structures for the multi-layered autonomous trigger system
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime


class LayerPriority(Enum):
    """Layer priority enumeration - lower value = higher priority"""
    REFLEX = 1          # Highest priority, <1s response (emergency situations)
    TACTICAL = 2        # High priority, 1-5s response (combat decisions)
    SUBCONSCIOUS = 3    # Medium priority, 5-30s response (routine tasks)
    CONSCIOUS = 4       # Low priority, 30-300s response (strategic planning)
    SYSTEM = 5          # Background priority, variable (maintenance tasks)


@dataclass
class TriggerCondition:
    """
    Trigger condition definition
    Supports simple, compound, and custom conditions
    """
    type: str  # 'simple', 'compound', 'custom'
    
    # Simple condition fields
    field: Optional[str] = None
    operator: Optional[str] = None  # '==', '!=', '>', '<', '>=', '<=', 'in', 'contains'
    value: Optional[Any] = None
    
    # Compound condition fields
    compound_operator: Optional[str] = None  # 'AND', 'OR', 'NOT'
    checks: Optional[List['TriggerCondition']] = None
    
    # Custom condition fields
    custom_function: Optional[Callable] = None
    custom_params: Optional[Dict[str, Any]] = None


@dataclass
class TriggerAction:
    """
    Trigger action definition
    Specifies what to execute when trigger fires
    """
    handler: str  # Module path to handler function (e.g., 'autonomous.emergency.heal_emergency')
    params: Dict[str, Any] = field(default_factory=dict)
    async_execution: bool = False
    timeout: Optional[float] = None  # Timeout in seconds


@dataclass
class Trigger:
    """
    Complete trigger definition
    Combines condition, action, and metadata
    """
    trigger_id: str
    name: str
    layer: LayerPriority
    priority: int  # Within layer (1 = highest)
    condition: TriggerCondition
    action: TriggerAction
    cooldown: int  # Seconds between executions
    
    # Runtime state
    enabled: bool = True
    last_executed: Optional[datetime] = None
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    
    # Metadata
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Convert layer string to enum if needed"""
        if isinstance(self.layer, str):
            self.layer = LayerPriority[self.layer]
    
    def get_success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.execution_count == 0:
            return 0.0
        return (self.success_count / self.execution_count) * 100
    
    def can_execute(self) -> bool:
        """Check if trigger can execute (enabled + cooldown)"""
        if not self.enabled:
            return False
        
        if self.last_executed is None:
            return True
        
        # Check cooldown
        elapsed = (datetime.now() - self.last_executed).total_seconds()
        return elapsed >= self.cooldown


@dataclass
class TriggerExecutionResult:
    """Result of trigger execution"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
