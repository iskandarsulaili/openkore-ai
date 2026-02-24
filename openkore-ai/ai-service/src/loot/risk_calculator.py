"""
Risk Assessment Calculator

Calculates risk levels for loot retrieval based on game state.
"""

import logging
import math
from typing import Dict, List, Any, Tuple

logger = logging.getLogger(__name__)


class RiskCalculator:
    """
    Calculates risk levels (0-100) for loot retrieval attempts.
    
    Risk Levels:
    - 0-30: Safe (systematic collection)
    - 31-60: Moderate (tactical retrieval required)
    - 61-100: High (sacrifice calculation needed)
    """
    
    # Weight factors for risk calculation
    WEIGHTS = {
        "hp_percent": 0.30,         # HP percentage: 30%
        "enemy_count": 0.25,        # Enemy count: 25%
        "distance_to_item": 0.15,   # Distance to item: 15%
        "distance_to_safety": 0.15, # Distance to safety: 15%
        "escape_ready": 0.10,       # Escape skills: 10%
        "party_support": 0.05       # Party nearby: 5%
    }
    
    def __init__(self):
        """Initialize the risk calculator."""
        logger.info("RiskCalculator initialized")
    
    def calculate_loot_risk(self, game_state: Dict[str, Any], item_position: Dict[str, int]) -> int:
        """
        Calculate risk level (0-100) for attempting to loot an item.
        
        Args:
            game_state: Current game state
            item_position: Position of target item {x, y}
        
        Returns:
            Risk level 0-100
        """
        character = game_state.get("character", {})
        
        # Extract risk factors
        hp_percent = character.get("hp_percent", 100)
        sp_percent = character.get("sp_percent", 100)
        char_position = character.get("position", {})
        
        # Count nearby threats
        nearby_enemies = self._count_nearby_threats(game_state, item_position)
        
        # Calculate distances
        distance_to_item = self._calculate_distance(char_position, item_position)
        distance_to_safety = self._find_distance_to_safety(game_state, char_position)
        
        # Check escape options
        escape_ready = self._check_escape_skills_ready(game_state)
        
        # Check party support
        party_nearby = self._check_party_nearby(game_state, item_position)
        
        # Calculate risk score
        risk_score = self._calculate_risk_score(
            hp_percent=hp_percent,
            sp_percent=sp_percent,
            nearby_enemies=nearby_enemies,
            distance_to_item=distance_to_item,
            distance_to_safety=distance_to_safety,
            escape_ready=escape_ready,
            party_nearby=party_nearby
        )
        
        # Clamp to 0-100
        risk_score = max(0, min(100, int(risk_score)))
        
        logger.debug(f"Risk assessment: {risk_score} (HP: {hp_percent}%, Enemies: {nearby_enemies}, Dist: {distance_to_item})")
        
        return risk_score
    
    def _calculate_risk_score(
        self,
        hp_percent: float,
        sp_percent: float,
        nearby_enemies: int,
        distance_to_item: float,
        distance_to_safety: float,
        escape_ready: bool,
        party_nearby: bool
    ) -> float:
        """
        Calculate weighted risk score.
        
        Risk formula:
        risk = (100 - hp) * 0.30 +
               (enemies * 10) * 0.25 +
               (dist_item / max_range * 100) * 0.15 +
               (dist_safety / max_range * 100) * 0.15 +
               (0 if escape_ready else 50) * 0.10 +
               (0 if party_nearby else 30) * 0.05
        """
        max_range = 20.0  # Maximum reasonable distance
        
        # HP factor (0-100)
        hp_risk = (100 - hp_percent)
        
        # Enemy count factor (0-100+)
        enemy_risk = min(100, nearby_enemies * 10)
        
        # Distance to item factor (0-100)
        item_distance_risk = min(100, (distance_to_item / max_range) * 100)
        
        # Distance to safety factor (0-100)
        safety_distance_risk = min(100, (distance_to_safety / max_range) * 100)
        
        # Escape availability factor (0 or 50)
        escape_risk = 0 if escape_ready else 50
        
        # Party support factor (0 or 30)
        party_risk = 0 if party_nearby else 30
        
        # Weighted sum
        total_risk = (
            hp_risk * self.WEIGHTS["hp_percent"] +
            enemy_risk * self.WEIGHTS["enemy_count"] +
            item_distance_risk * self.WEIGHTS["distance_to_item"] +
            safety_distance_risk * self.WEIGHTS["distance_to_safety"] +
            escape_risk * self.WEIGHTS["escape_ready"] +
            party_risk * self.WEIGHTS["party_support"]
        )
        
        # SP penalty if too low
        if sp_percent < 20:
            total_risk += 15
        
        logger.debug(
            f"Risk components: HP={hp_risk:.1f}, Enemies={enemy_risk:.1f}, "
            f"ItemDist={item_distance_risk:.1f}, SafetyDist={safety_distance_risk:.1f}, "
            f"Escape={escape_risk}, Party={party_risk} -> Total={total_risk:.1f}"
        )
        
        return total_risk
    
    def _count_nearby_threats(self, game_state: Dict[str, Any], position: Dict[str, int]) -> int:
        """
        Count enemies near a position.
        
        Args:
            game_state: Current game state
            position: Target position
        
        Returns:
            Number of nearby enemies
        """
        threat_range = 10  # Consider enemies within 10 cells as threats
        
        enemies = game_state.get("monsters", [])
        if not enemies:
            return 0
        
        nearby = 0
        for enemy in enemies:
            if not self._is_aggressive_enemy(enemy):
                continue
            
            enemy_pos = enemy.get("pos", {})
            distance = self._calculate_distance(position, enemy_pos)
            
            if distance <= threat_range:
                nearby += 1
        
        return nearby
    
    def _is_aggressive_enemy(self, enemy: Dict[str, Any]) -> bool:
        """Check if enemy is aggressive/threatening."""
        # Consider enemy aggressive if:
        # - Has aggro on player
        # - Is boss/MVP
        # - Is within attack range and not fleeing
        
        if enemy.get("target") == "player":
            return True
        
        if enemy.get("isBoss") or enemy.get("isMVP"):
            return True
        
        # Default: assume enemy is potentially aggressive
        return True
    
    def _calculate_distance(self, pos1: Dict[str, int], pos2: Dict[str, int]) -> float:
        """Calculate Euclidean distance between two positions."""
        if not pos1 or not pos2:
            return 999.0
        
        x1, y1 = pos1.get("x", 0), pos1.get("y", 0)
        x2, y2 = pos2.get("x", 0), pos2.get("y", 0)
        
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def _find_distance_to_safety(self, game_state: Dict[str, Any], current_pos: Dict[str, int]) -> float:
        """
        Find distance to nearest safe location.
        
        Safe locations:
        - Safe spots (predefined)
        - Areas with no enemies
        - Near warp portals
        - Near party members
        
        Returns:
            Distance to nearest safe location
        """
        min_distance = 20.0  # Default: assume safety is far
        
        # Check safe spots
        safe_spots = game_state.get("safe_spots", [])
        for spot in safe_spots:
            distance = self._calculate_distance(current_pos, spot)
            min_distance = min(min_distance, distance)
        
        # Check warp portals
        portals = game_state.get("portals", [])
        for portal in portals:
            portal_pos = portal.get("pos", {})
            distance = self._calculate_distance(current_pos, portal_pos)
            min_distance = min(min_distance, distance)
        
        # Check party members
        party = game_state.get("party_members", [])
        for member in party:
            member_pos = member.get("pos", {})
            if member_pos:
                distance = self._calculate_distance(current_pos, member_pos)
                min_distance = min(min_distance, distance)
        
        # If character HP is high and no immediate threats, current position might be safe
        character = game_state.get("character", {})
        if character.get("hp_percent", 0) > 70:
            nearby_threats = self._count_nearby_threats(game_state, current_pos)
            if nearby_threats == 0:
                min_distance = 0  # Already safe
        
        return min_distance
    
    def _check_escape_skills_ready(self, game_state: Dict[str, Any]) -> bool:
        """
        Check if escape skills are available.
        
        Escape skills:
        - Fly Wing (item)
        - Butterfly Wing (item)
        - Teleport (skill)
        - Hiding (skill)
        - Cloaking (skill)
        - Backslide (skill)
        
        Returns:
            True if at least one escape option is ready
        """
        character = game_state.get("character", {})
        inventory = game_state.get("inventory", [])
        skills = character.get("skills", {})
        
        # Check for Fly Wing
        for item in inventory:
            if item.get("name") in ["Fly Wing", "Butterfly Wing"]:
                if item.get("amount", 0) > 0:
                    return True
        
        # Check escape skills
        escape_skills = ["AL_TELEPORT", "TF_HIDING", "AS_CLOAKING", "TF_BACKSLIDING"]
        for skill in escape_skills:
            skill_info = skills.get(skill, {})
            if skill_info.get("level", 0) > 0:
                # Check if skill is off cooldown
                cooldown = skill_info.get("cooldown", 0)
                if cooldown <= 0:
                    return True
        
        return False
    
    def _check_party_nearby(self, game_state: Dict[str, Any], position: Dict[str, int]) -> bool:
        """
        Check if party members are nearby for support.
        
        Args:
            game_state: Current game state
            position: Target position
        
        Returns:
            True if party member within support range
        """
        support_range = 15.0  # Party members within 15 cells provide support
        
        party = game_state.get("party_members", [])
        if not party:
            return False
        
        for member in party:
            member_pos = member.get("pos", {})
            if not member_pos:
                continue
            
            distance = self._calculate_distance(position, member_pos)
            if distance <= support_range:
                # Check if member is alive and capable
                if member.get("hp_percent", 0) > 30:
                    return True
        
        return False
    
    def estimate_time_to_loot(
        self,
        character_pos: Dict[str, int],
        item_pos: Dict[str, int],
        enemy_positions: List[Dict[str, int]]
    ) -> float:
        """
        Estimate seconds needed to reach and grab item.
        
        Args:
            character_pos: Character position
            item_pos: Item position
            enemy_positions: List of enemy positions
        
        Returns:
            Estimated time in seconds
        """
        distance = self._calculate_distance(character_pos, item_pos)
        
        # Assume movement speed: 7 cells/second (base speed)
        base_speed = 7.0
        base_time = distance / base_speed
        
        # Add time penalty for enemy obstacles
        obstacles = 0
        for enemy_pos in enemy_positions:
            # Check if enemy is in the path
            if self._is_in_path(character_pos, item_pos, enemy_pos):
                obstacles += 1
        
        # Each obstacle adds 1 second (need to kite around)
        total_time = base_time + obstacles * 1.0
        
        # Add pickup time
        pickup_time = 0.5
        total_time += pickup_time
        
        return total_time
    
    def estimate_time_to_death(self, game_state: Dict[str, Any]) -> float:
        """
        Estimate seconds until character death based on current DPS taken.
        
        Args:
            game_state: Current game state
        
        Returns:
            Estimated time in seconds (999 if safe)
        """
        character = game_state.get("character", {})
        
        current_hp = character.get("hp", 1000)
        max_hp = character.get("max_hp", 1000)
        hp_percent = character.get("hp_percent", 100)
        
        # Check recent damage taken
        damage_history = game_state.get("damage_history", [])
        if not damage_history:
            # No recent damage, assume safe
            return 999.0
        
        # Calculate average DPS from recent damage
        recent_damage = damage_history[-10:]  # Last 10 hits
        total_damage = sum(hit.get("damage", 0) for hit in recent_damage)
        time_span = max(1.0, len(recent_damage) * 0.5)  # Assume 0.5s per hit
        
        dps = total_damage / time_span
        
        if dps <= 0:
            return 999.0
        
        # Time to death = current_hp / dps
        time_to_death = current_hp / dps
        
        logger.debug(f"Time to death estimate: {time_to_death:.1f}s (HP: {current_hp}/{max_hp}, DPS: {dps:.1f})")
        
        return time_to_death
    
    def _is_in_path(
        self,
        start: Dict[str, int],
        end: Dict[str, int],
        obstacle: Dict[str, int]
    ) -> bool:
        """
        Check if obstacle is in the path between start and end.
        
        Uses simple line-to-point distance check.
        """
        if not all([start, end, obstacle]):
            return False
        
        x1, y1 = start.get("x", 0), start.get("y", 0)
        x2, y2 = end.get("x", 0), end.get("y", 0)
        x0, y0 = obstacle.get("x", 0), obstacle.get("y", 0)
        
        # Calculate perpendicular distance from obstacle to line
        line_length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if line_length == 0:
            return False
        
        distance = abs((x2 - x1) * (y1 - y0) - (x1 - x0) * (y2 - y1)) / line_length
        
        # Obstacle blocks path if within 2 cells of the line
        return distance < 2.0
    
    def get_risk_category(self, risk_level: int) -> str:
        """
        Get risk category name.
        
        Args:
            risk_level: Risk level 0-100
        
        Returns:
            "safe", "moderate", or "high"
        """
        if risk_level <= 30:
            return "safe"
        elif risk_level <= 60:
            return "moderate"
        else:
            return "high"
