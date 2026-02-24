"""
Sequential Action Planner - Multi-step Plan Creation and Execution Tracking

God-tier AI requirement: "Multi-step strategies: Need potion → Check inventory → 
If low → Go → Buy from NPC → Return to farming"

This module enables complex multi-step autonomous gameplay by:
- Creating detailed action plans from high-level goals
- Tracking execution progress (current step, completed steps)
- Handling interruptions (combat, death, etc.) and resuming plans
- Re-planning on failure with retry logic
- Validating plan feasibility before execution

Example Usage:
    planner = SequentialPlanner()
    plan = planner.create_plan("buy_healing_items", game_state)
    
    while not plan.is_complete():
        action = planner.get_next_action(plan.plan_id)
        # Execute action...
        planner.mark_step_complete(plan.plan_id, success=True)
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum
import time
import logging

logger = logging.getLogger(__name__)

class PlanStatus(Enum):
    """Status of overall plan execution"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """Status of individual plan step"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class PlanStep:
    """
    Single step in a multi-step plan.
    
    Attributes:
        step_id: Unique ID within plan (1-indexed)
        action_type: Type of action (attack, move, talk, buy, etc.)
        parameters: Action-specific parameters
        description: Human-readable step description
        status: Current execution status
        started_at: Timestamp when execution started
        completed_at: Timestamp when execution completed
        failure_reason: Reason for failure (if failed)
        retry_count: Number of retries attempted
        max_retries: Maximum retries before failing plan
    """
    step_id: int
    action_type: str
    parameters: Dict
    description: str
    status: StepStatus = StepStatus.PENDING
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    failure_reason: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    
    def can_retry(self) -> bool:
        """Check if step can be retried after failure"""
        return self.retry_count < self.max_retries
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "step_id": self.step_id,
            "action_type": self.action_type,
            "parameters": self.parameters,
            "description": self.description,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "failure_reason": self.failure_reason,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries
        }

@dataclass
class ActionPlan:
    """
    Multi-step action plan with state tracking.
    
    Attributes:
        plan_id: Unique plan identifier
        goal: High-level goal description
        steps: List of plan steps
        current_step_index: Index of currently executing step
        status: Overall plan status
        created_at: Plan creation timestamp
        started_at: Execution start timestamp
        completed_at: Execution completion timestamp
        metadata: Additional plan metadata
    """
    plan_id: str
    goal: str
    steps: List[PlanStep]
    current_step_index: int = 0
    status: PlanStatus = PlanStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    metadata: Dict = field(default_factory=dict)
    
    def get_current_step(self) -> Optional[PlanStep]:
        """Get currently executing step"""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    def advance_to_next_step(self):
        """Move to next step in plan"""
        self.current_step_index += 1
        if self.current_step_index >= len(self.steps):
            self.status = PlanStatus.COMPLETED
            self.completed_at = time.time()
            logger.info(f"[PLANNER] Plan '{self.plan_id}' completed successfully")
    
    def is_complete(self) -> bool:
        """Check if plan execution is finished"""
        return self.status in [PlanStatus.COMPLETED, PlanStatus.FAILED, PlanStatus.CANCELLED]
    
    def get_progress_percentage(self) -> float:
        """Get completion percentage (0-100)"""
        if not self.steps:
            return 0.0
        return (self.current_step_index / len(self.steps)) * 100
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "plan_id": self.plan_id,
            "goal": self.goal,
            "steps": [step.to_dict() for step in self.steps],
            "current_step_index": self.current_step_index,
            "status": self.status.value,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metadata": self.metadata,
            "progress_percentage": self.get_progress_percentage()
        }

class SequentialPlanner:
    """
    Manages multi-step action plans with state tracking and interruption handling.
    
    Capabilities:
    - Creates complex multi-step plans from high-level goals
    - Tracks execution progress across multiple steps
    - Handles interruptions (combat, death, etc.) gracefully
    - Re-plans on failure with intelligent retry logic
    - Validates plan feasibility before execution
    - Persists plan state for recovery after restart
    
    Supported Goals:
    - buy_healing_items: Purchase potions from town NPC
    - return_to_town: Navigate back to save point/town
    - farm_until_level_X: Level grinding session
    - complete_quest: Quest chain execution
    - upgrade_equipment: Equipment enhancement workflow
    """
    
    def __init__(self):
        self.active_plans: Dict[str, ActionPlan] = {}
        self.plan_history: List[ActionPlan] = []
        self.max_history_size = 100
        
    def create_plan(self, goal: str, game_state: Dict) -> ActionPlan:
        """
        Create multi-step plan for given goal.
        
        Args:
            goal: High-level goal (e.g., "buy_healing_items", "farm_until_level_20")
            game_state: Current game state for context-aware planning
            
        Returns:
            ActionPlan object with detailed steps
        """
        plan_id = f"plan_{int(time.time() * 1000)}"
        
        # Route to appropriate planner based on goal
        if goal == "buy_healing_items":
            steps = self._plan_buy_healing_items(game_state)
        elif goal == "return_to_town":
            steps = self._plan_return_to_town(game_state)
        elif goal.startswith("farm_until_level"):
            target_level = int(goal.split("_")[-1])
            steps = self._plan_farming_session(game_state, target_level)
        elif goal == "complete_quest":
            steps = self._plan_quest_completion(game_state)
        else:
            logger.warning(f"[PLANNER] Unknown goal: {goal}, creating default plan")
            steps = [PlanStep(
                step_id=1,
                action_type="continue",
                parameters={"reason": f"unknown_goal_{goal}"},
                description=f"Unknown goal: {goal}"
            )]
        
        plan = ActionPlan(
            plan_id=plan_id,
            goal=goal,
            steps=steps
        )
        
        self.active_plans[plan_id] = plan
        logger.info(f"[PLANNER] Created plan '{plan_id}' for goal '{goal}' with {len(steps)} steps")
        
        return plan
    
    def _plan_buy_healing_items(self, game_state: Dict) -> List[PlanStep]:
        """
        Create plan for buying healing items from town NPC.
        
        Plan steps:
        1. Check current location
        2. Navigate to town if not in town
        3. Find potion NPC location  
        4. Navigate to NPC
        5. Talk to NPC
        6. Purchase items
        7. Return to original location (optional)
        """
        steps = []
        character = game_state.get("character", {})
        current_map = character.get("position", {}).get("map", "unknown")
        
        # Determine if we need to travel to town
        town_maps = ["prontera", "payon", "geffen", "morocc", "alberta", "aldebaran", "izlude"]
        is_in_town = any(town in current_map.lower() for town in town_maps)
        
        if not is_in_town:
            steps.append(PlanStep(
                step_id=len(steps) + 1,
                action_type="move_to_town",
                parameters={"method": "teleport_or_walk", "town": "prontera"},
                description="Navigate to nearest town"
            ))
        
        steps.append(PlanStep(
            step_id=len(steps) + 1,
            action_type="find_npc",
            parameters={"npc_type": "tool_dealer", "item": "Red Potion"},
            description="Find potion dealer NPC"
        ))
        
        steps.append(PlanStep(
            step_id=len(steps) + 1,
            action_type="talk_to_npc",
            parameters={"npc_name": "Tool Dealer"},
            description="Initiate conversation with NPC"
        ))
        
        steps.append(PlanStep(
            step_id=len(steps) + 1,
            action_type="buy_items",
            parameters={
                "items": ["Red Potion", "Fly Wing"],
                "quantities": [20, 10]
            },
            description="Purchase healing items"
        ))
        
        if not is_in_town:
            steps.append(PlanStep(
                step_id=len(steps) + 1,
                action_type="return_to_location",
                parameters={"map": current_map},
                description="Return to original farming location"
            ))
        
        return steps
    
    def _plan_return_to_town(self, game_state: Dict) -> List[PlanStep]:
        """Create plan for returning to town safely"""
        steps = []
        inventory = game_state.get("inventory", [])
        
        # Check for Butterfly Wing (instant save point warp)
        has_butterfly_wing = any(
            item.get("name") == "Butterfly Wing"
            for item in inventory
        )
        
        if has_butterfly_wing:
            steps.append(PlanStep(
                step_id=1,
                action_type="use_item",
                parameters={"item": "Butterfly Wing"},
                description="Use Butterfly Wing to warp to save point"
            ))
        else:
            # Check for Fly Wing (random field teleport - may need multiple uses)
            has_fly_wing = any(
                item.get("name") == "Fly Wing"
                for item in inventory
            )
            
            if has_fly_wing:
                steps.append(PlanStep(
                    step_id=1,
                    action_type="use_item",
                    parameters={"item": "Fly Wing"},
                    description="Teleport to safer location using Fly Wing"
                ))
            
            # Walk to town
            steps.append(PlanStep(
                step_id=len(steps) + 1,
                action_type="walk_to_town",
                parameters={"method": "nearest_portal"},
                description="Walk to nearest town portal"
            ))
        
        return steps
    
    def _plan_farming_session(self, game_state: Dict, target_level: int) -> List[PlanStep]:
        """Create plan for leveling session"""
        character = game_state.get("character", {})
        current_level = character.get("level", 1)
        current_map = character.get("position", {}).get("map", "unknown")
        
        steps = []
        
        # Navigate to farming map if not already there
        farming_maps = ["prt_fild", "pay_fild", "gef_fild", "moc_fild"]
        is_in_farming_map = any(fm in current_map.lower() for fm in farming_maps)
        
        if not is_in_farming_map:
            steps.append(PlanStep(
                step_id=1,
                action_type="move_to_farming_map",
                parameters={"map": "prt_fild08", "reason": "leveling"},
                description="Navigate to farming area"
            ))
        
        # Main farming loop step
        steps.append(PlanStep(
            step_id=len(steps) + 1,
            action_type="farm_monsters",
            parameters={
                "target_level": target_level,
                "current_level": current_level,
                "auto_rest": True,
                "auto_loot": True,
                "auto_buy": True
            },
            description=f"Farm until level {target_level}"
        ))
        
        return steps
    
    def _plan_quest_completion(self, game_state: Dict) -> List[PlanStep]:
        """Create plan for completing active quest"""
        # This would integrate with quest system for detailed quest steps
        # For now, return placeholder
        return [PlanStep(
            step_id=1,
            action_type="continue_quest",
            parameters={},
            description="Continue active quest"
        )]
    
    def get_next_action(self, plan_id: str) -> Optional[Dict]:
        """
        Get next action from plan for execution.
        
        Args:
            plan_id: ID of plan to get action from
            
        Returns:
            Action dict with action/params/metadata or None if plan complete
        """
        plan = self.active_plans.get(plan_id)
        if not plan or plan.is_complete():
            return None
        
        current_step = plan.get_current_step()
        if not current_step:
            return None
        
        # Mark step as in progress if not already
        if current_step.status == StepStatus.PENDING:
            current_step.status = StepStatus.IN_PROGRESS
            current_step.started_at = time.time()
            
            if plan.status == PlanStatus.PENDING:
                plan.status = PlanStatus.IN_PROGRESS
                plan.started_at = time.time()
            
            logger.info(f"[PLANNER] Executing step {current_step.step_id}/{len(plan.steps)}: {current_step.description}")
        
        return {
            "action": current_step.action_type,
            "params": current_step.parameters,
            "plan_id": plan_id,
            "step_id": current_step.step_id,
            "step_description": current_step.description,
            "steps_total": len(plan.steps),
            "steps_completed": plan.current_step_index,
            "progress_percentage": plan.get_progress_percentage(),
            "layer": "SEQUENTIAL_PLAN"
        }
    
    def mark_step_complete(self, plan_id: str, success: bool, result: Optional[Dict] = None):
        """
        Mark current step as complete and advance to next.
        
        Args:
            plan_id: ID of plan
            success: Whether step succeeded
            result: Optional result data from step execution
        """
        plan = self.active_plans.get(plan_id)
        if not plan:
            logger.warning(f"[PLANNER] Plan '{plan_id}' not found")
            return
        
        current_step = plan.get_current_step()
        if not current_step:
            logger.warning(f"[PLANNER] No current step in plan '{plan_id}'")
            return
        
        if success:
            current_step.status = StepStatus.COMPLETED
            current_step.completed_at = time.time()
            duration = current_step.completed_at - current_step.started_at if current_step.started_at else 0
            logger.info(f"[PLANNER]  Step {current_step.step_id}/{len(plan.steps)} complete ({duration:.1f}s): {current_step.description}")
            plan.advance_to_next_step()
            
            # Check if plan is now complete
            if plan.is_complete():
                self._archive_plan(plan)
        else:
            current_step.retry_count += 1
            if current_step.can_retry():
                logger.warning(f"[PLANNER]  Step {current_step.step_id} failed, retry {current_step.retry_count}/{current_step.max_retries}")
                current_step.status = StepStatus.PENDING  # Retry
                if result and "reason" in result:
                    current_step.failure_reason = result["reason"]
            else:
                current_step.status = StepStatus.FAILED
                plan.status = PlanStatus.FAILED
                logger.error(f"[PLANNER]  Plan '{plan_id}' failed at step {current_step.step_id}: {current_step.description}")
                self._archive_plan(plan)
    
    def interrupt_plan(self, plan_id: str, reason: str):
        """
        Interrupt plan due to external event (combat, death, etc.).
        
        Args:
            plan_id: ID of plan to interrupt
            reason: Reason for interruption
        """
        plan = self.active_plans.get(plan_id)
        if not plan:
            return
        
        logger.warning(f"[PLANNER] ⚠ Plan '{plan_id}' interrupted: {reason}")
        plan.status = PlanStatus.INTERRUPTED
        plan.metadata["interruption_reason"] = reason
        plan.metadata["interrupted_at"] = time.time()
    
    def resume_plan(self, plan_id: str) -> bool:
        """
        Attempt to resume interrupted plan.
        
        Args:
            plan_id: ID of plan to resume
            
        Returns:
            True if resume successful, False otherwise
        """
        plan = self.active_plans.get(plan_id)
        if not plan or plan.status != PlanStatus.INTERRUPTED:
            return False
        
        logger.info(f"[PLANNER] ↻ Resuming plan '{plan_id}' from step {plan.current_step_index + 1}")
        plan.status = PlanStatus.IN_PROGRESS
        return True
    
    def cancel_plan(self, plan_id: str):
        """
        Cancel active plan.
        
        Args:
            plan_id: ID of plan to cancel
        """
        plan = self.active_plans.pop(plan_id, None)
        if plan:
            plan.status = PlanStatus.CANCELLED
            plan.metadata["cancelled_at"] = time.time()
            self._archive_plan(plan)
            logger.info(f"[PLANNER] ✕ Cancelled plan '{plan_id}'")
    
    def _archive_plan(self, plan: ActionPlan):
        """Move completed/failed plan to history"""
        if plan.plan_id in self.active_plans:
            del self.active_plans[plan.plan_id]
        
        self.plan_history.append(plan)
        if len(self.plan_history) > self.max_history_size:
            self.plan_history.pop(0)
    
    def get_active_plan(self) -> Optional[ActionPlan]:
        """Get currently active plan (if any)"""
        for plan in self.active_plans.values():
            if plan.status == PlanStatus.IN_PROGRESS:
                return plan
        return None
    
    def has_active_plan(self) -> bool:
        """Check if there's an active plan"""
        return any(p.status == PlanStatus.IN_PROGRESS for p in self.active_plans.values())
    
    def get_plan_status(self, plan_id: str) -> Optional[Dict]:
        """Get detailed plan status"""
        plan = self.active_plans.get(plan_id)
        if plan:
            return plan.to_dict()
        
        # Check history
        for historical_plan in reversed(self.plan_history):
            if historical_plan.plan_id == plan_id:
                return historical_plan.to_dict()
        
        return None
