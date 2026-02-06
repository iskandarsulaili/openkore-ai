"""
Goal Representation Model

Defines the TemporalGoal data structure with comprehensive temporal reasoning
and contingency planning capabilities.

Enhanced with:
- Multi-tiered time scales (short/medium/long)
- Milestone tracking
- Resource allocation management
- Conflict resolution
- Party/multi-agent coordination
- Persistence capabilities
"""

from pydantic import BaseModel, Field, field_validator, model_serializer, ConfigDict
from typing import List, Optional, Dict, Any, Literal
from enum import Enum
from datetime import datetime, timedelta
import uuid


class GoalStatus(str, Enum):
    """Goal execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ABANDONED = "abandoned"
    EMERGENCY_ABORTED = "emergency_aborted"


class GoalPriority(int, Enum):
    """Goal priority levels (higher = more important)"""
    CRITICAL = 5    # Survival (HP < 20%)
    HIGH = 4        # Important objectives (quest completion)
    MEDIUM = 3      # Normal activities (farming)
    LOW = 2         # Optional tasks (socializing)
    TRIVIAL = 1     # Non-essential (exploration)


class PlanType(str, Enum):
    """Execution plan types"""
    PRIMARY = "primary"      # Plan A: Optimal approach
    ALTERNATIVE = "alternative"  # Plan B: Balanced approach
    CONSERVATIVE = "conservative"  # Plan C: Safe approach
    EMERGENCY = "emergency"  # Plan D: Emergency abort


class ContingencyPlan(BaseModel):
    """
    Fallback plan if primary approach fails
    
    Each contingency plan represents an alternative execution strategy
    with decreasing risk and increasing safety guarantees.
    """
    
    name: str = Field(..., description="Plan name (e.g., 'Plan B: Defensive Farming')")
    plan_type: PlanType = Field(..., description="Plan type classification")
    description: str = Field(..., description="Detailed description of the plan")
    
    # Activation conditions
    activation_conditions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Conditions that trigger this plan (e.g., {'primary_failed': True})"
    )
    
    # Execution details
    actions: List[str] = Field(
        default_factory=list,
        description="Ordered list of actions to execute"
    )
    
    action_details: Dict[str, Any] = Field(
        default_factory=dict,
        description="Detailed parameters for each action"
    )
    
    # Predictions
    success_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Expected success probability (0.0-1.0)"
    )
    
    estimated_duration: int = Field(
        gt=0,
        description="Estimated execution time in seconds"
    )
    
    risk_level: str = Field(
        default="MEDIUM",
        description="Risk level: LOW, MEDIUM, HIGH, CRITICAL"
    )
    
    # Resource requirements
    required_resources: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resources needed (HP, SP, items, etc.)"
    )
    
    # Failure handling
    max_retries: int = Field(
        default=1,
        ge=0,
        description="Maximum retry attempts for this plan"
    )
    
    timeout_seconds: int = Field(
        default=300,
        gt=0,
        description="Maximum execution time before timing out"
    )
    
    model_config = ConfigDict(
        use_enum_values=True
    )
    
    @model_serializer
    def serialize_model(self):
        """Custom serializer to handle datetime objects"""
        data = self.__dict__.copy()
        # Convert datetime objects to ISO format strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data


class TemporalGoal(BaseModel):
    """
    Goal with temporal reasoning and comprehensive contingency planning
    
    This represents a complete goal with:
    - Past context (historical data)
    - Present state (current game state)
    - Future predictions (expected outcomes)
    - Multiple execution plans (A, B, C, D)
    - Comprehensive tracking and metrics
    """
    
    # ===== Identity =====
    id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique goal identifier"
    )
    
    name: str = Field(..., description="Goal name (e.g., 'farm_poring')")
    description: str = Field(..., description="Human-readable goal description")
    goal_type: str = Field(..., description="Goal category (farming, questing, etc.)")
    
    # ===== Temporal Attributes =====
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="When the goal was created"
    )
    
    started_at: Optional[datetime] = Field(
        default=None,
        description="When execution started"
    )
    
    completed_at: Optional[datetime] = Field(
        default=None,
        description="When execution completed"
    )
    
    deadline: Optional[datetime] = Field(
        default=None,
        description="Optional deadline for completion"
    )
    
    estimated_duration: int = Field(
        default=300,
        gt=0,
        description="Estimated execution time in seconds"
    )
    
    # ===== Intelligence Attributes =====
    priority: GoalPriority = Field(
        default=GoalPriority.MEDIUM,
        description="Goal priority level"
    )
    
    status: GoalStatus = Field(
        default=GoalStatus.PENDING,
        description="Current execution status"
    )
    
    # ===== Temporal Reasoning =====
    past_context: Dict[str, Any] = Field(
        default_factory=dict,
        description="Historical data from similar goals"
    )
    
    present_state: Dict[str, Any] = Field(
        default_factory=dict,
        description="Current game state snapshot"
    )
    
    future_predictions: Dict[str, Any] = Field(
        default_factory=dict,
        description="Predicted outcomes and probabilities"
    )
    
    # ===== Execution Plans =====
    primary_plan: Dict[str, Any] = Field(
        ...,
        description="Plan A: Optimal execution strategy"
    )
    
    fallback_plans: List[ContingencyPlan] = Field(
        default_factory=list,
        description="Plans B, C, D: Contingency strategies"
    )
    
    active_plan: str = Field(
        default="primary",
        description="Currently executing plan (primary, alternative, conservative, emergency)"
    )
    
    # ===== Execution Tracking =====
    attempt_count: int = Field(
        default=0,
        ge=0,
        description="Total execution attempts"
    )
    
    failure_count: int = Field(
        default=0,
        ge=0,
        description="Number of failures"
    )
    
    plan_execution_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="History of which plans were tried and their results"
    )
    
    # ===== Success Criteria =====
    success_conditions: Dict[str, Any] = Field(
        ...,
        description="Conditions that indicate goal completion"
    )
    
    failure_threshold: int = Field(
        default=3,
        ge=1,
        description="Attempts before switching to fallback plan"
    )
    
    # ===== Dependencies =====
    parent_goal_id: Optional[str] = Field(
        default=None,
        description="Parent goal ID if this is a sub-goal"
    )
    
    sub_goals: List[str] = Field(
        default_factory=list,
        description="List of sub-goal IDs"
    )
    
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Goals that must complete before this one"
    )
    
    # ===== Metadata =====
    tags: List[str] = Field(
        default_factory=list,
        description="Tags for categorization and search"
    )
    
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata"
    )
    
    # ===== NEW ENHANCED FEATURES =====
    
    # Time Scale Management
    time_scale: Literal['short', 'medium', 'long'] = Field(
        default='short',
        description="Time scale: short=hours, medium=days, long=endgame/continuous"
    )
    
    # Milestone Tracking
    milestones: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Progress milestones: [{'name': '...', 'progress': 0.25, 'completed': False, 'timestamp': None}]"
    )
    
    # Resource Allocation
    resource_allocation: Dict[str, Any] = Field(
        default_factory=dict,
        description="Allocated resources: {'cpu_percent': 10, 'memory_mb': 256, 'api_calls_per_min': 5, 'potions': 20, 'zeny': 10000}"
    )
    
    # Conflict Management
    conflicts: List[str] = Field(
        default_factory=list,
        description="List of conflicting goal IDs (goals that compete for same resources/location)"
    )
    
    # Party/Multi-Agent Coordination
    party_coordination: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Party coordination data: {'party_id': '...', 'role': 'tank|healer|dps', 'members': [...], 'shared_progress': {...}}"
    )
    
    # Persistence
    persistence_key: Optional[str] = Field(
        default=None,
        description="Unique key for save/load persistence (e.g., 'farm_poring_session_20260206')"
    )
    
    last_saved_at: Optional[datetime] = Field(
        default=None,
        description="When goal state was last persisted to disk"
    )
    
    # ===== Validators =====
    @field_validator('fallback_plans')
    @classmethod
    def validate_fallback_plans(cls, v):
        """Ensure we have at least 3 fallback plans (B, C, D)"""
        if len(v) < 3:
            # Auto-generate emergency abort plan if missing
            while len(v) < 3:
                plan_type = [PlanType.ALTERNATIVE, PlanType.CONSERVATIVE, PlanType.EMERGENCY][len(v)]
                v.append(ContingencyPlan(
                    name=f"Auto-generated {plan_type.value} plan",
                    plan_type=plan_type,
                    description=f"Automatically generated {plan_type.value} fallback",
                    actions=["abort", "teleport_to_safety", "heal_full"],
                    success_probability=0.99 if plan_type == PlanType.EMERGENCY else 0.85,
                    estimated_duration=30
                ))
        return v
    
    @field_validator('priority', mode='before')
    @classmethod
    def validate_priority(cls, v):
        """Convert priority to enum if it's an int"""
        if isinstance(v, int):
            return GoalPriority(v)
        return v
    
    # ===== Helper Methods =====
    def start_execution(self) -> None:
        """Mark goal as started"""
        self.status = GoalStatus.IN_PROGRESS
        self.started_at = datetime.now()
        self.attempt_count += 1
    
    def complete_success(self) -> None:
        """Mark goal as successfully completed"""
        self.status = GoalStatus.COMPLETED
        self.completed_at = datetime.now()
    
    def complete_failure(self, reason: str) -> None:
        """Mark goal as failed"""
        self.status = GoalStatus.FAILED
        self.completed_at = datetime.now()
        self.failure_count += 1
        self.metadata['failure_reason'] = reason
    
    def emergency_abort(self, reason: str) -> None:
        """Emergency abort with safety guarantee"""
        self.status = GoalStatus.EMERGENCY_ABORTED
        self.completed_at = datetime.now()
        self.active_plan = "emergency"
        self.metadata['abort_reason'] = reason
    
    def switch_to_fallback(self, plan_type: str, reason: str) -> bool:
        """
        Switch to next fallback plan
        
        Returns:
            bool: True if switch successful, False if no more fallbacks
        """
        plan_order = ["primary", "alternative", "conservative", "emergency"]
        
        try:
            current_idx = plan_order.index(self.active_plan)
            if current_idx < len(plan_order) - 1:
                next_plan = plan_order[current_idx + 1]
                
                # Log the switch
                self.plan_execution_history.append({
                    'from_plan': self.active_plan,
                    'to_plan': next_plan,
                    'reason': reason,
                    'timestamp': datetime.now().isoformat(),
                    'attempt_count': self.attempt_count
                })
                
                self.active_plan = next_plan
                return True
            return False
        except ValueError:
            return False
    
    def get_active_plan_details(self) -> Optional[Dict[str, Any]]:
        """Get details of currently active plan"""
        if self.active_plan == "primary":
            return self.primary_plan
        
        plan_type_map = {
            "alternative": PlanType.ALTERNATIVE,
            "conservative": PlanType.CONSERVATIVE,
            "emergency": PlanType.EMERGENCY
        }
        
        target_type = plan_type_map.get(self.active_plan)
        if target_type:
            for plan in self.fallback_plans:
                if plan.plan_type == target_type:
                    return plan.dict()
        
        return None
    
    def get_execution_duration(self) -> Optional[int]:
        """Get actual execution duration in seconds"""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds())
        return None
    
    def is_overdue(self) -> bool:
        """Check if goal has passed its deadline"""
        if self.deadline:
            return datetime.now() > self.deadline
        return False
    
    def get_time_remaining(self) -> Optional[int]:
        """Get seconds remaining until deadline"""
        if self.deadline:
            delta = self.deadline - datetime.now()
            return max(0, int(delta.total_seconds()))
        return None
    
    # ===== NEW ENHANCED METHODS =====
    
    def add_milestone(self, name: str, target_progress: float, description: str = "") -> None:
        """Add a progress milestone"""
        self.milestones.append({
            'name': name,
            'target_progress': target_progress,
            'description': description,
            'completed': False,
            'completed_at': None,
            'created_at': datetime.now().isoformat()
        })
    
    def complete_milestone(self, name: str) -> bool:
        """Mark a milestone as completed"""
        for milestone in self.milestones:
            if milestone['name'] == name and not milestone['completed']:
                milestone['completed'] = True
                milestone['completed_at'] = datetime.now().isoformat()
                return True
        return False
    
    def get_progress_percentage(self) -> float:
        """Calculate overall progress based on completed milestones"""
        if not self.milestones:
            return 0.0
        
        completed = sum(1 for m in self.milestones if m['completed'])
        return (completed / len(self.milestones)) * 100
    
    def allocate_resource(self, resource_type: str, amount: Any) -> None:
        """Allocate a specific resource to this goal"""
        self.resource_allocation[resource_type] = amount
    
    def get_allocated_resource(self, resource_type: str) -> Optional[Any]:
        """Get allocated amount for a resource type"""
        return self.resource_allocation.get(resource_type)
    
    def add_conflict(self, goal_id: str) -> None:
        """Register a conflicting goal"""
        if goal_id not in self.conflicts:
            self.conflicts.append(goal_id)
    
    def remove_conflict(self, goal_id: str) -> None:
        """Remove a goal conflict"""
        if goal_id in self.conflicts:
            self.conflicts.remove(goal_id)
    
    def has_conflicts(self) -> bool:
        """Check if goal has any conflicts"""
        return len(self.conflicts) > 0
    
    def set_party_role(self, party_id: str, role: str, members: List[str]) -> None:
        """Configure party coordination"""
        self.party_coordination = {
            'party_id': party_id,
            'role': role,
            'members': members,
            'shared_progress': {},
            'assigned_at': datetime.now().isoformat()
        }
    
    def update_shared_progress(self, member_id: str, progress: Dict[str, Any]) -> None:
        """Update progress from a party member"""
        if self.party_coordination:
            if 'shared_progress' not in self.party_coordination:
                self.party_coordination['shared_progress'] = {}
            self.party_coordination['shared_progress'][member_id] = {
                **progress,
                'updated_at': datetime.now().isoformat()
            }
    
    def generate_persistence_key(self) -> str:
        """Generate unique persistence key for save/load"""
        if not self.persistence_key:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            self.persistence_key = f"{self.name}_{timestamp}_{self.id[:8]}"
        return self.persistence_key
    
    model_config = ConfigDict(
        use_enum_values=True
    )
    
    @model_serializer
    def serialize_model(self):
        """Custom serializer to handle datetime objects"""
        data = self.__dict__.copy()
        # Convert datetime objects to ISO format strings
        for key, value in data.items():
            if isinstance(value, datetime):
                data[key] = value.isoformat()
        return data


# ===== Helper Functions =====

def create_farming_goal(
    monster_name: str,
    quantity: int = 100,
    map_name: str = None,
    duration_minutes: int = 30
) -> TemporalGoal:
    """
    Factory function to create a farming goal with standard contingency plans
    
    Args:
        monster_name: Target monster to farm
        quantity: Number of kills target
        map_name: Optional specific map
        duration_minutes: Maximum farming duration
    
    Returns:
        TemporalGoal: Fully configured farming goal
    """
    
    # Plan A: Aggressive farming
    primary_plan = {
        'strategy': 'aggressive',
        'actions': [
            'teleport_to_farming_spot',
            'attack_monsters',
            'loot_items',
            'heal_when_needed'
        ],
        'parameters': {
            'attack_style': 'aggressive',
            'heal_threshold': 40,
            'loot_priority': 'high_value_first'
        }
    }
    
    # Plan B: Defensive farming
    plan_b = ContingencyPlan(
        name="Plan B: Defensive Farming",
        plan_type=PlanType.ALTERNATIVE,
        description="More defensive approach with frequent healing",
        activation_conditions={'primary_failed': True, 'hp_drops_too_fast': True},
        actions=[
            'teleport_to_farming_spot',
            'attack_monsters_carefully',
            'heal_frequently',
            'loot_items'
        ],
        action_details={
            'attack_style': 'defensive',
            'heal_threshold': 60,
            'retreat_on_multiple_aggro': True
        },
        success_probability=0.90,
        estimated_duration=duration_minutes * 60 + 300,
        risk_level="MEDIUM"
    )
    
    # Plan C: Ultra-safe farming
    plan_c = ContingencyPlan(
        name="Plan C: Ultra-Safe Farming",
        plan_type=PlanType.CONSERVATIVE,
        description="Maximum safety with constant monitoring",
        activation_conditions={'plan_b_failed': True, 'high_risk_detected': True},
        actions=[
            'teleport_to_safe_farming_spot',
            'attack_single_monster',
            'heal_immediately',
            'teleport_on_danger',
            'loot_when_safe'
        ],
        action_details={
            'attack_style': 'ultra_defensive',
            'heal_threshold': 80,
            'max_monsters': 1,
            'teleport_on_hp_below': 50
        },
        success_probability=0.98,
        estimated_duration=duration_minutes * 60 + 600,
        risk_level="LOW"
    )
    
    # Plan D: Emergency abort
    plan_d = ContingencyPlan(
        name="Plan D: Emergency Abort",
        plan_type=PlanType.EMERGENCY,
        description="Abort farming and ensure character safety",
        activation_conditions={'all_plans_failed': True},
        actions=[
            'stop_all_actions',
            'use_emergency_teleport',
            'heal_to_full',
            'save_to_storage',
            'log_failure_report'
        ],
        action_details={
            'teleport_method': 'fly_wing_or_skill',
            'safe_zone': 'nearest_town',
            'heal_to_percent': 100
        },
        success_probability=0.999,
        estimated_duration=60,
        risk_level="MINIMAL"
    )
    
    return TemporalGoal(
        name=f"farm_{monster_name}",
        description=f"Farm {quantity} {monster_name} on {map_name or 'optimal map'}",
        goal_type="farming",
        priority=GoalPriority.MEDIUM,
        estimated_duration=duration_minutes * 60,
        primary_plan=primary_plan,
        fallback_plans=[plan_b, plan_c, plan_d],
        success_conditions={
            'kills': quantity,
            'minimum_success_rate': 0.7
        },
        tags=['farming', monster_name, map_name] if map_name else ['farming', monster_name]
    )


def create_emergency_heal_goal() -> TemporalGoal:
    """Factory function for critical healing goal"""
    
    return TemporalGoal(
        name="emergency_heal",
        description="Emergency healing to prevent death",
        goal_type="survival",
        priority=GoalPriority.CRITICAL,
        estimated_duration=5,
        primary_plan={
            'actions': ['use_best_healing_item'],
            'parameters': {'item_preference': 'red_potion'}
        },
        fallback_plans=[
            ContingencyPlan(
                name="Plan B: Alternative Healing",
                plan_type=PlanType.ALTERNATIVE,
                description="Use alternative healing method",
                actions=['use_alternate_healing_item'],
                success_probability=0.95,
                estimated_duration=5
            ),
            ContingencyPlan(
                name="Plan C: Sit and Recover",
                plan_type=PlanType.CONSERVATIVE,
                description="Sit down to recover HP",
                actions=['sit_down', 'wait_for_recovery'],
                success_probability=0.98,
                estimated_duration=30
            ),
            ContingencyPlan(
                name="Plan D: Emergency Teleport",
                plan_type=PlanType.EMERGENCY,
                description="Teleport to safety immediately",
                actions=['emergency_teleport', 'heal_in_safety'],
                success_probability=0.999,
                estimated_duration=10
            )
        ],
        success_conditions={
            'hp_percent': 80,
            'safe_location': True
        }
    )
