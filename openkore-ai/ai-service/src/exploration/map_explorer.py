"""
Map exploration strategy for autonomous bot

This module provides intelligent map exploration to increase bot autonomy.
It tracks explored positions, generates smart movement targets, and includes
unstuck logic to prevent getting trapped.
"""
import random
import math
from typing import Dict, List, Tuple, Optional, Set
import logging
import time

logger = logging.getLogger(__name__)

class MapExplorer:
    """
    Intelligent map exploration engine
    
    Features:
    - Tracks explored positions to avoid revisiting
    - Generates exploration targets using spiral patterns
    - Unstuck logic when position doesn't change
    - Considers character state (HP/SP/combat) before exploring
    """
    
    def __init__(self):
        self.explored_positions: Set[Tuple[int, int]] = set()  # Track visited positions
        self.exploration_target: Optional[Dict[str, int]] = None
        self.stuck_count: int = 0
        self.last_position: Optional[Tuple[int, int]] = None
        self.last_target_time: float = 0
        self.current_map: str = ""
        
    def should_explore(self, game_state: Dict) -> bool:
        """
        Determine if bot should explore vs farm/quest
        
        Args:
            game_state: Current game state
        
        Returns:
            True if bot should explore
        """
        character = game_state.get("character", {})
        
        # Get HP/SP percentages
        current_hp = int(character.get("hp", 0) or 0)
        max_hp = int(character.get("max_hp", 1) or 1)
        hp_percent = (current_hp / max_hp * 100) if max_hp > 0 else 0
        
        current_sp = int(character.get("sp", 0) or 0)
        max_sp = int(character.get("max_sp", 1) or 1)
        sp_percent = (current_sp / max_sp * 100) if max_sp > 0 else 0
        
        # Don't explore if low resources
        if hp_percent < 60 or sp_percent < 40:
            logger.debug(f"[EXPLORE] Not exploring - low resources (HP: {hp_percent:.1f}%, SP: {sp_percent:.1f}%)")
            return False
        
        # Don't explore if monsters nearby (farm instead)
        monsters = game_state.get("monsters", [])
        if isinstance(monsters, list) and len(monsters) > 0:
            logger.debug("[EXPLORE] Not exploring - monsters nearby")
            return False
        
        logger.debug("[EXPLORE] Conditions met for exploration")
        return True
    
    def get_exploration_target(self, current_map: str, current_pos: Dict) -> Dict:
        """
        Generate exploration target based on map and current position
        
        Args:
            current_map: Current map name
            current_pos: Current character position {x, y}
        
        Returns:
            Target position dict {x, y, reason}
        """
        current_x = int(current_pos.get("x", 0) or 0)
        current_y = int(current_pos.get("y", 0) or 0)
        
        # Reset explored positions if map changed
        if current_map != self.current_map:
            logger.info(f"[EXPLORE] Map changed from '{self.current_map}' to '{current_map}' - resetting explored positions")
            self.explored_positions.clear()
            self.exploration_target = None
            self.current_map = current_map
            self.stuck_count = 0
        
        # Check if stuck (same position as last check)
        if self.last_position == (current_x, current_y):
            self.stuck_count += 1
            logger.debug(f"[EXPLORE] Stuck count: {self.stuck_count}")
        else:
            self.stuck_count = 0
        
        self.last_position = (current_x, current_y)
        
        # If stuck, try completely random direction to break free
        if self.stuck_count > 3:
            logger.warning("[EXPLORE] Stuck detected, choosing random direction to escape")
            angle = random.uniform(0, 2 * math.pi)
            distance = random.randint(20, 50)
            target_x = int(current_x + distance * math.cos(angle))
            target_y = int(current_y + distance * math.sin(angle))
            self.stuck_count = 0
            self.exploration_target = None  # Clear target to force new one next time
            return {"x": target_x, "y": target_y, "reason": "unstuck"}
        
        # Mark current position as explored
        self.explored_positions.add((current_x, current_y))
        
        # Generate new target if none exists or target reached
        if not self.exploration_target:
            # Use spiral pattern from current position
            angle = random.uniform(0, 2 * math.pi)
            distance = random.randint(20, 40)
            target_x = int(current_x + distance * math.cos(angle))
            target_y = int(current_y + distance * math.sin(angle))
            
            self.exploration_target = {"x": target_x, "y": target_y}
            self.last_target_time = time.time()
            logger.info(f"[EXPLORE] New target: ({target_x}, {target_y})")
        
        # Check if target is reached (within 5 cells)
        target_x = self.exploration_target["x"]
        target_y = self.exploration_target["y"]
        distance_to_target = math.sqrt((current_x - target_x)**2 + (current_y - target_y)**2)
        
        if distance_to_target < 5:
            logger.info(f"[EXPLORE] Target reached! Distance: {distance_to_target:.1f}")
            self.exploration_target = None  # Clear to generate new target next time
            return self.get_exploration_target(current_map, current_pos)  # Recursively get new target
        
        # Check if target has been active too long (30 seconds) - might be unreachable
        if time.time() - self.last_target_time > 30:
            logger.warning(f"[EXPLORE] Target timeout (30s), generating new target")
            self.exploration_target = None
            return self.get_exploration_target(current_map, current_pos)
        
        return self.exploration_target
    
    def reset_target(self):
        """Clear current exploration target"""
        self.exploration_target = None
        logger.debug("[EXPLORE] Target reset")
    
    def reset_map_data(self):
        """Reset all exploration data (e.g., when returning to town)"""
        self.explored_positions.clear()
        self.exploration_target = None
        self.stuck_count = 0
        self.last_position = None
        self.current_map = ""
        logger.info("[EXPLORE] All exploration data reset")
    
    def get_stats(self) -> Dict:
        """Get exploration statistics"""
        return {
            "explored_positions": len(self.explored_positions),
            "current_target": self.exploration_target,
            "stuck_count": self.stuck_count,
            "current_map": self.current_map
        }

# Global explorer instance
map_explorer = MapExplorer()
