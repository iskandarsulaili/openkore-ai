"""
Kiting Engine - opkAI Priority 1
5-state kiting system for ranged combat classes
Manages optimal combat distance to maximize damage while minimizing risk
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Tuple, Optional, Dict, Any
import math
import random
from loguru import logger


class KitingState(Enum):
    """5 kiting states from opkAI"""
    IDLE = "IDLE"
    APPROACH = "APPROACH"
    ATTACK = "ATTACK"
    RETREAT = "RETREAT"
    EMERGENCY_FLEE = "EMERGENCY_FLEE"


@dataclass
class KitingConfig:
    """Job-specific kiting parameters from opkAI"""
    job_class: str
    min_distance: int           # Minimum safe distance
    optimal_distance: int       # Preferred attack distance
    max_distance: int           # Maximum effective range
    emergency_distance: int     # Distance for emergency flee
    emergency_hp_threshold: float  # HP% to trigger emergency


@dataclass
class KitingUpdate:
    """Kiting state machine update result"""
    state: KitingState
    movement_position: Optional[Tuple[int, int]]
    reason: str
    distance: float
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return {
            'state': self.state.value,
            'movement_position': self.movement_position,
            'reason': self.reason,
            'distance': self.distance
        }


class KitingEngine:
    """
    5-state kiting system from opkAI.
    Manages combat distance for ranged classes.
    
    States:
    1. IDLE - No target, waiting
    2. APPROACH - Target too far, moving closer
    3. ATTACK - Optimal range, attacking
    4. RETREAT - Too close or HP low, backing away
    5. EMERGENCY_FLEE - Critical HP, fleeing immediately
    """
    
    # Class-specific configurations from opkAI
    KITING_CONFIGS = {
        "archer": KitingConfig("archer", 5, 7, 9, 3, 0.20),
        "hunter": KitingConfig("hunter", 7, 9, 11, 4, 0.20),
        "dancer": KitingConfig("dancer", 6, 8, 10, 3, 0.20),
        "bard": KitingConfig("bard", 6, 8, 10, 3, 0.20),
        "mage": KitingConfig("mage", 6, 8, 10, 4, 0.20),
        "wizard": KitingConfig("wizard", 7, 9, 11, 4, 0.20),
        "sage": KitingConfig("sage", 6, 8, 10, 4, 0.20),
        "professor": KitingConfig("professor", 6, 8, 10, 4, 0.20),
        "gunslinger": KitingConfig("gunslinger", 4, 6, 8, 2, 0.20),
        "ranger": KitingConfig("ranger", 8, 10, 12, 5, 0.20),
        "warlock": KitingConfig("warlock", 7, 9, 11, 5, 0.20),
        "sorcerer": KitingConfig("sorcerer", 6, 8, 10, 4, 0.20),
        "genetic": KitingConfig("genetic", 5, 7, 9, 3, 0.25),
        "shadow_chaser": KitingConfig("shadow_chaser", 4, 6, 8, 2, 0.25),
    }
    
    def __init__(self, job_class: str):
        """
        Initialize kiting engine for specific job class.
        
        Args:
            job_class: Job class name (e.g., "archer", "wizard")
        """
        job_key = job_class.lower().replace(' ', '_')
        self.config = self.KITING_CONFIGS.get(
            job_key,
            KitingConfig("default", 5, 7, 9, 3, 0.20)
        )
        
        self.current_state = KitingState.IDLE
        self.previous_state = KitingState.IDLE
        
        # State metrics for performance tracking
        self.state_metrics = {
            "retreats": 0,
            "emergency_flees": 0,
            "attacks": 0,
            "approaches": 0,
            "state_changes": 0,
            "total_updates": 0
        }
        
        # For anti-stuck detection
        self.last_position: Optional[Tuple[int, int]] = None
        self.stuck_counter = 0
        
        logger.info(f"KitingEngine initialized for {self.config.job_class}: "
                   f"optimal={self.config.optimal_distance}, range={self.config.min_distance}-{self.config.max_distance}")
    
    def update(
        self,
        char_pos: Tuple[int, int],
        enemy_pos: Tuple[int, int],
        hp_percent: float,
        enemy_targeting_us: bool = True
    ) -> KitingUpdate:
        """
        Update kiting state machine.
        
        Args:
            char_pos: Character position (x, y)
            enemy_pos: Enemy position (x, y)
            hp_percent: Current HP percentage (0.0-1.0)
            enemy_targeting_us: Is enemy actively targeting us?
        
        Returns:
            KitingUpdate with state and movement position
        """
        self.state_metrics["total_updates"] += 1
        
        # Calculate current distance
        distance = self._calculate_distance(char_pos, enemy_pos)
        
        # Determine new state
        new_state = self._determine_state(distance, hp_percent, enemy_targeting_us)
        
        # Track state changes
        if new_state != self.current_state:
            self.state_metrics["state_changes"] += 1
            self.previous_state = self.current_state
            self.current_state = new_state
            logger.debug(f"Kiting state: {self.previous_state.value} -> {new_state.value} (dist={distance:.1f}, HP={hp_percent:.1%})")
        
        # Calculate movement position based on state
        movement_pos, reason = self._execute_state(
            new_state, char_pos, enemy_pos, distance, hp_percent
        )
        
        # Anti-stuck detection
        if movement_pos == self.last_position:
            self.stuck_counter += 1
            if self.stuck_counter > 3:
                # Add random offset to unstuck
                movement_pos = self._add_random_offset(movement_pos)
                reason += " (unstuck)"
                self.stuck_counter = 0
        else:
            self.stuck_counter = 0
        
        self.last_position = movement_pos
        
        return KitingUpdate(
            state=new_state,
            movement_position=movement_pos,
            reason=reason,
            distance=distance
        )
    
    def _determine_state(
        self,
        distance: float,
        hp_percent: float,
        enemy_targeting_us: bool
    ) -> KitingState:
        """
        Determine kiting state based on distance and HP (opkAI logic).
        
        Priority:
        1. Emergency flee (critical HP)
        2. Retreat (low HP or too close)
        3. Approach (too far)
        4. Attack (optimal range)
        5. Idle (no action needed)
        """
        
        # Priority 1: Emergency flee (opkAI logic)
        if hp_percent <= self.config.emergency_hp_threshold:
            return KitingState.EMERGENCY_FLEE
        
        # Priority 2: Retreat (too close or low HP)
        if distance < self.config.min_distance:
            return KitingState.RETREAT
        
        # Retreat if HP is low (40% threshold from opkAI)
        if hp_percent <= 0.40 and enemy_targeting_us:
            return KitingState.RETREAT
        
        # Priority 3: Approach (too far)
        if distance > self.config.max_distance:
            return KitingState.APPROACH
        
        # Priority 4: Attack (in optimal range and healthy)
        if (self.config.min_distance <= distance <= self.config.max_distance and
            hp_percent > 0.40):
            return KitingState.ATTACK
        
        # Priority 5: Idle (edge case)
        return KitingState.IDLE
    
    def _execute_state(
        self,
        state: KitingState,
        char_pos: Tuple[int, int],
        enemy_pos: Tuple[int, int],
        distance: float,
        hp_percent: float
    ) -> Tuple[Optional[Tuple[int, int]], str]:
        """
        Execute state action and return movement position.
        
        Returns:
            (movement_position, reason) - position is None if no movement needed
        """
        
        if state == KitingState.EMERGENCY_FLEE:
            self.state_metrics["emergency_flees"] += 1
            # Flee far away (emergency_distance + 3 cells)
            flee_distance = self.config.emergency_distance + 3
            movement_pos = self._calculate_retreat_position(
                char_pos, enemy_pos, distance=flee_distance
            )
            return movement_pos, f"EMERGENCY FLEE: HP={hp_percent:.1%}"
        
        elif state == KitingState.RETREAT:
            self.state_metrics["retreats"] += 1
            # Retreat 3 cells (opkAI standard)
            movement_pos = self._calculate_retreat_position(
                char_pos, enemy_pos, distance=3
            )
            return movement_pos, f"Retreating: too close ({distance:.1f} < {self.config.min_distance})"
        
        elif state == KitingState.APPROACH:
            self.state_metrics["approaches"] += 1
            # Approach to optimal distance
            movement_pos = self._calculate_approach_position(
                char_pos, enemy_pos, target_distance=self.config.optimal_distance
            )
            return movement_pos, f"Approaching: too far ({distance:.1f} > {self.config.max_distance})"
        
        elif state == KitingState.ATTACK:
            self.state_metrics["attacks"] += 1
            # Stay and attack - no movement
            return None, f"Attacking: optimal range ({distance:.1f})"
        
        else:  # IDLE
            return None, "Idle: no action needed"
    
    def _calculate_retreat_position(
        self,
        char_pos: Tuple[int, int],
        enemy_pos: Tuple[int, int],
        distance: int = 3
    ) -> Tuple[int, int]:
        """
        Calculate retreat position (away from enemy).
        
        opkAI enhancement: Add angle variance for human-like movement
        """
        dx = char_pos[0] - enemy_pos[0]
        dy = char_pos[1] - enemy_pos[1]
        
        # Normalize direction
        magnitude = math.sqrt(dx * dx + dy * dy)
        if magnitude == 0:
            magnitude = 1
        
        dx = dx / magnitude
        dy = dy / magnitude
        
        # Add angle variance (opkAI: ±1-2 cells for human-like movement)
        angle_variance = random.uniform(-1.5, 1.5)
        
        # Calculate new position
        new_x = int(char_pos[0] + dx * distance + angle_variance)
        new_y = int(char_pos[1] + dy * distance + angle_variance)
        
        return (new_x, new_y)
    
    def _calculate_approach_position(
        self,
        char_pos: Tuple[int, int],
        enemy_pos: Tuple[int, int],
        target_distance: int
    ) -> Tuple[int, int]:
        """
        Calculate approach position (toward enemy to target distance).
        """
        dx = enemy_pos[0] - char_pos[0]
        dy = enemy_pos[1] - char_pos[1]
        
        # Normalize direction
        magnitude = math.sqrt(dx * dx + dy * dy)
        if magnitude == 0:
            return char_pos
        
        dx = dx / magnitude
        dy = dy / magnitude
        
        # Move to target distance
        move_distance = magnitude - target_distance
        
        # Add slight variance
        angle_variance = random.uniform(-0.5, 0.5)
        
        new_x = int(char_pos[0] + dx * move_distance + angle_variance)
        new_y = int(char_pos[1] + dy * move_distance + angle_variance)
        
        return (new_x, new_y)
    
    def _calculate_distance(
        self,
        pos1: Tuple[int, int],
        pos2: Tuple[int, int]
    ) -> float:
        """Calculate Euclidean distance between two positions"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def _add_random_offset(
        self,
        pos: Optional[Tuple[int, int]]
    ) -> Optional[Tuple[int, int]]:
        """Add random offset to position (anti-stuck)"""
        if pos is None:
            return None
        
        offset_x = random.randint(-2, 2)
        offset_y = random.randint(-2, 2)
        
        return (pos[0] + offset_x, pos[1] + offset_y)
    
    def get_metrics(self) -> Dict[str, int]:
        """Get current state metrics"""
        return self.state_metrics.copy()
    
    def reset_metrics(self):
        """Reset state metrics"""
        self.state_metrics = {
            "retreats": 0,
            "emergency_flees": 0,
            "attacks": 0,
            "approaches": 0,
            "state_changes": 0,
            "total_updates": 0
        }
    
    def get_recommended_skill_range(self) -> int:
        """Get recommended skill range for this job"""
        return self.config.optimal_distance
    
    def is_in_attack_range(self, distance: float) -> bool:
        """Check if distance is within attack range"""
        return self.config.min_distance <= distance <= self.config.max_distance
    
    def should_use_skill(self, distance: float, hp_percent: float) -> bool:
        """Determine if we should use skills at current distance/HP"""
        # Don't use skills if too close or HP too low
        if distance < self.config.min_distance or hp_percent < 0.30:
            return False
        
        # Use skills in optimal range
        return self.config.min_distance <= distance <= self.config.max_distance


# Factory function for easy instantiation
def create_kiting_engine(job_class: str) -> KitingEngine:
    """
    Factory function to create kiting engine for job class.
    
    Args:
        job_class: Job class name
    
    Returns:
        Configured KitingEngine
    """
    return KitingEngine(job_class)
