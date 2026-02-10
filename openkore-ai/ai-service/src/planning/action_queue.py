"""
Action Queue Manager - Conflict Prevention and Timing Management

God-tier AI requirement: "Perfect timing, no overlap/conflict. Cannot send skill 
command before skill is ready (skill delay). Cannot move while casting."

This module prevents action conflicts and manages execution timing:
- Ensures only ONE action executes at a time
- Prevents conflicting actions (moving while casting, etc.)
- Manages skill cooldowns and delays
- Tracks action execution state
- Timeout handling for stuck actions
- Priority queue support for urgent actions

Example Usage:
    queue = ActionQueue()
    
    # Enqueue actions
    action_id = await queue.enqueue("skill", {"skill_name": "Bash", "target": 123}, priority=8)
    
    # Get next executable action
    action = await queue.get_next_action()
    
    # Mark complete when done
    await queue.mark_complete(action_id, success=True)
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List
from enum import Enum
import time
import asyncio
import logging

logger = logging.getLogger(__name__)

class ActionState(Enum):
    """State of action in queue"""
    QUEUED = "queued"
    EXECUTING = "executing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class QueuedAction:
    """
    Action in execution queue with timing and state tracking.
    
    Attributes:
        action_id: Unique identifier for tracking
        action_type: Type of action (attack, skill, move, etc.)
        parameters: Action-specific parameters
        enqueued_at: Timestamp when added to queue
        started_at: Timestamp when execution started
        completed_at: Timestamp when execution finished
        state: Current execution state
        estimated_duration: Expected execution time (seconds)
        timeout: Maximum execution time before timeout (seconds)
        priority: Priority level (1-10, higher = more urgent)
    """
    action_id: str
    action_type: str
    parameters: Dict
    enqueued_at: float
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    state: ActionState = ActionState.QUEUED
    estimated_duration: float = 1.0
    timeout: float = 10.0
    priority: int = 5
    
    def is_complete(self) -> bool:
        """Check if action execution is finished"""
        return self.state in [ActionState.COMPLETED, ActionState.FAILED, ActionState.CANCELLED]
    
    def get_elapsed_time(self) -> float:
        """Get elapsed execution time"""
        if self.started_at is None:
            return 0.0
        return time.time() - self.started_at
    
    def has_timed_out(self) -> bool:
        """Check if action has exceeded timeout"""
        if self.started_at is None:
            return False
        return self.get_elapsed_time() > self.timeout
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "action_id": self.action_id,
            "action_type": self.action_type,
            "parameters": self.parameters,
            "state": self.state.value,
            "enqueued_at": self.enqueued_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "elapsed_time": self.get_elapsed_time() if self.started_at else 0.0,
            "estimated_duration": self.estimated_duration,
            "timeout": self.timeout,
            "priority": self.priority
        }

class ActionQueue:
    """
    Manages action execution queue with timing and conflict prevention.
    
    Features:
    - Single action execution (prevents overlaps)
    - Conflict detection (move + cast, attack + skill, etc.)
    - Cooldown management for skills
    - Priority queue support
    - Timeout handling for stuck actions
    - Thread-safe with asyncio.Lock
    
    Conflict Rules (based on RO game mechanics):
    - Cannot move while casting skill
    - Cannot attack while using skill
    - Cannot use item while casting
    - Cannot talk to NPC while in combat
    - Cannot rest while moving
    
    Typical Action Durations:
    - attack: 1.0s (auto-attack delay)
    - skill: 1.5s (cast time + delay)
    - move: 2.0s (walking between cells)
    - item: 0.5s (item use delay)
    - talk: 1.0s (NPC dialog)
    - rest: 5.0s (sitting recovery)
    - teleport: 1.0s (casting time)
    """
    
    def __init__(self):
        self.queue: List[QueuedAction] = []
        self.current_action: Optional[QueuedAction] = None
        self.cooldowns: Dict[str, float] = {}  # skill_name -> end_timestamp
        self.lock = asyncio.Lock()
        self.action_counter = 0
        
        # Conflict matrix: actions that cannot run together
        # Key = current action, Value = list of conflicting actions
        self.conflicts = {
            "move": ["skill", "attack", "rest", "talk", "use_item"],
            "skill": ["move", "skill", "attack", "use_item"],
            "attack": ["move", "skill", "attack", "rest"],
            "rest": ["move", "attack", "skill", "talk", "use_item"],
            "talk": ["move", "attack", "skill", "rest"],
            "use_item": ["move", "skill"],
            "teleport": ["move", "attack", "skill"]
        }
        
        # Estimated durations for action types (seconds)
        self.durations = {
            "attack": 1.0,
            "skill": 1.5,
            "move": 2.0,
            "use_item": 0.5,
            "talk": 1.0,
            "rest": 5.0,
            "teleport": 1.0,
            "buy_items": 2.0,
            "sell_items": 2.0
        }
        
        logger.info("[ACTION_QUEUE] Initialized with conflict prevention and cooldown management")
    
    async def enqueue(self, action_type: str, parameters: Dict, priority: int = 5) -> str:
        """
        Add action to queue with priority ordering.
        
        Args:
            action_type: Type of action to queue
            parameters: Action parameters
            priority: Priority level (1-10, higher = more urgent)
            
        Returns:
            action_id for tracking
        """
        async with self.lock:
            self.action_counter += 1
            action_id = f"action_{int(time.time() * 1000)}_{self.action_counter}"
            
            queued_action = QueuedAction(
                action_id=action_id,
                action_type=action_type,
                parameters=parameters,
                enqueued_at=time.time(),
                estimated_duration=self.durations.get(action_type, 1.0),
                priority=priority
            )
            
            # Insert by priority (higher priority first)
            inserted = False
            for i, existing_action in enumerate(self.queue):
                if queued_action.priority > existing_action.priority:
                    self.queue.insert(i, queued_action)
                    inserted = True
                    break
            
            if not inserted:
                self.queue.append(queued_action)
            
            logger.info(f"[ACTION_QUEUE] Enqueued '{action_type}' (ID: {action_id}, Priority: {priority}, Queue size: {len(self.queue)})")
            return action_id
    
    async def can_execute(self, action_type: str, parameters: Dict = None) -> tuple[bool, Optional[str]]:
        """
        Check if action can be executed now.
        
        Args:
            action_type: Type of action to check
            parameters: Action parameters (for cooldown checks)
            
        Returns:
            (can_execute, reason_if_not)
        """
        async with self.lock:
            # Check if another action is currently executing
            if self.current_action:
                # Check if current action has timed out
                if self.current_action.has_timed_out():
                    logger.warning(f"[ACTION_QUEUE] Current action '{self.current_action.action_type}' exceeded timeout ({self.current_action.timeout}s), allowing new action")
                    self.current_action.state = ActionState.FAILED
                    self.current_action.completed_at = time.time()
                    self.current_action = None
                else:
                    # Check for conflicts
                    if action_type in self.conflicts.get(self.current_action.action_type, []):
                        return False, f"Conflicts with current action: {self.current_action.action_type}"
                    
                    return False, f"Action in progress: {self.current_action.action_type} ({self.current_action.get_elapsed_time():.1f}s elapsed)"
            
            # Check cooldowns for skills
            if action_type == "skill" and parameters:
                skill_name = parameters.get("skill_name", "unknown")
                cooldown_end = self.cooldowns.get(skill_name, 0)
                if time.time() < cooldown_end:
                    remaining = cooldown_end - time.time()
                    return False, f"Skill '{skill_name}' on cooldown: {remaining:.1f}s remaining"
            
            return True, None
    
    async def get_next_action(self) -> Optional[Dict]:
        """
        Get next action from queue if ready to execute.
        
        Returns:
            Action dict with action/params/metadata or None if not ready
        """
        async with self.lock:
            # Check if current action is still executing
            if self.current_action and not self.current_action.is_complete():
                # Check if exceeded timeout
                if self.current_action.has_timed_out():
                    logger.error(f"[ACTION_QUEUE] ⚠ Action '{self.current_action.action_type}' TIMED OUT after {self.current_action.timeout}s")
                    self.current_action.state = ActionState.FAILED
                    self.current_action.completed_at = time.time()
                    self.current_action = None
                else:
                    # Still executing within normal duration
                    return None
            
            # Get next action from queue
            if not self.queue:
                return None
            
            next_action = self.queue[0]
            
            # Check if can execute
            can_exec, reason = await self.can_execute(next_action.action_type, next_action.parameters)
            if not can_exec:
                logger.debug(f"[ACTION_QUEUE] Cannot execute '{next_action.action_type}': {reason}")
                return None
            
            # Remove from queue and set as current
            self.queue.pop(0)
            next_action.state = ActionState.EXECUTING
            next_action.started_at = time.time()
            self.current_action = next_action
            
            logger.info(f"[ACTION_QUEUE] ▶ Executing '{next_action.action_type}' (ID: {next_action.action_id}, Est: {next_action.estimated_duration:.1f}s)")
            
            return {
                "action": next_action.action_type,
                "params": next_action.parameters,
                "action_id": next_action.action_id,
                "estimated_duration": next_action.estimated_duration,
                "timeout": next_action.timeout,
                "layer": "ACTION_QUEUE"
            }
    
    async def mark_complete(self, action_id: str, success: bool = True):
        """
        Mark action as complete and clear from current slot.
        
        Args:
            action_id: ID of action to mark complete
            success: Whether action succeeded
        """
        async with self.lock:
            if self.current_action and self.current_action.action_id == action_id:
                self.current_action.state = ActionState.COMPLETED if success else ActionState.FAILED
                self.current_action.completed_at = time.time()
                
                duration = self.current_action.get_elapsed_time()
                status_icon = "" if success else ""
                logger.info(f"[ACTION_QUEUE] {status_icon} Action '{self.current_action.action_type}' {self.current_action.state.value} (Duration: {duration:.2f}s)")
                
                # Add skill cooldown if applicable
                if self.current_action.action_type == "skill" and success:
                    skill_name = self.current_action.parameters.get("skill_name", "unknown")
                    cooldown = self.current_action.parameters.get("cooldown", 1.0)
                    self.cooldowns[skill_name] = time.time() + cooldown
                    logger.debug(f"[ACTION_QUEUE] Skill '{skill_name}' cooldown: {cooldown:.1f}s")
                
                self.current_action = None
            else:
                logger.warning(f"[ACTION_QUEUE] Attempted to mark action '{action_id}' complete, but it's not current")
    
    async def cancel_action(self, action_id: str):
        """
        Cancel queued or current action.
        
        Args:
            action_id: ID of action to cancel
        """
        async with self.lock:
            # Check current action
            if self.current_action and self.current_action.action_id == action_id:
                self.current_action.state = ActionState.CANCELLED
                self.current_action.completed_at = time.time()
                logger.info(f"[ACTION_QUEUE] ✕ Cancelled current action '{self.current_action.action_type}'")
                self.current_action = None
                return
            
            # Check queue
            for i, action in enumerate(self.queue):
                if action.action_id == action_id:
                    action.state = ActionState.CANCELLED
                    self.queue.pop(i)
                    logger.info(f"[ACTION_QUEUE] ✕ Cancelled queued action '{action.action_type}'")
                    return
            
            logger.warning(f"[ACTION_QUEUE] Action '{action_id}' not found for cancellation")
    
    async def clear_queue(self, reason: str = "manual_clear"):
        """
        Clear all queued actions (emergency clear).
        
        Args:
            reason: Reason for clearing queue
        """
        async with self.lock:
            cleared_count = len(self.queue)
            self.queue.clear()
            logger.warning(f"[ACTION_QUEUE] ⚠ Cleared {cleared_count} queued actions (reason: {reason})")
    
    async def get_status(self) -> Dict:
        """
        Get detailed queue status for monitoring.
        
        Returns:
            Status dict with current action, queue, cooldowns
        """
        async with self.lock:
            return {
                "current_action": self.current_action.to_dict() if self.current_action else None,
                "queue_size": len(self.queue),
                "queued_actions": [action.to_dict() for action in self.queue],
                "active_cooldowns": {
                    skill: round(cd_end - time.time(), 1)
                    for skill, cd_end in self.cooldowns.items()
                    if time.time() < cd_end
                },
                "total_cooldowns_tracked": len(self.cooldowns),
                "has_active_action": self.current_action is not None
            }
    
    async def force_complete_current(self):
        """Force complete current action (emergency measure)"""
        async with self.lock:
            if self.current_action:
                logger.warning(f"[ACTION_QUEUE] ⚠ Force completing current action '{self.current_action.action_type}'")
                self.current_action.state = ActionState.COMPLETED
                self.current_action.completed_at = time.time()
                self.current_action = None
