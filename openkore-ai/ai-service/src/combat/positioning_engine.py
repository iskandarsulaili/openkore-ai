"""
Positioning Engine - opkAI Priority 1
5-factor position scoring system for optimal combat positioning
Finds best tactical positions considering safety, damage, escape, terrain, and AoE
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import List, Tuple, Dict, Any, Optional
import math
from loguru import logger


class PositionType(Enum):
    """Position strategy types from opkAI"""
    OFFENSIVE = "OFFENSIVE"    # safety=0.15, damage=0.40, escape=0.15, terrain=0.15, aoe=0.15
    DEFENSIVE = "DEFENSIVE"    # safety=0.40, damage=0.15, escape=0.25, terrain=0.15, aoe=0.05
    RETREAT = "RETREAT"        # safety=0.45, escape=0.35, damage=0.05, terrain=0.10, aoe=0.05
    AOE = "AOE"                # aoe=0.35, damage=0.20, safety=0.20, escape=0.15, terrain=0.10
    BALANCED = "BALANCED"      # Even distribution


@dataclass
class PositionScore:
    """Position evaluation result"""
    x: int
    y: int
    total_score: float
    safety_score: float      # Distance from enemies, wall protection
    damage_score: float      # Can reach target, enemies in range
    escape_score: float      # Available escape routes
    terrain_score: float     # Walls, choke points, corners
    aoe_score: float        # Multiple enemies in AoE range
    position_type: str       # Strategy used
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return asdict(self)


class PositioningEngine:
    """
    5-factor position scoring from opkAI.
    Finds optimal combat positions using weighted scoring.
    
    Factors:
    1. Safety - Distance from enemies, wall protection
    2. Damage - Can reach target, enemies in range
    3. Escape - Available escape routes (walkable cells)
    4. Terrain - Walls, choke points, corner advantage
    5. AoE - Multiple enemies in AoE skill range
    """
    
    # Factor weights by position type (from opkAI)
    WEIGHTS = {
        PositionType.OFFENSIVE: {
            "safety": 0.15, "damage": 0.40, "escape": 0.15,
            "terrain": 0.15, "aoe": 0.15
        },
        PositionType.DEFENSIVE: {
            "safety": 0.40, "damage": 0.15, "escape": 0.25,
            "terrain": 0.15, "aoe": 0.05
        },
        PositionType.RETREAT: {
            "safety": 0.45, "damage": 0.05, "escape": 0.35,
            "terrain": 0.10, "aoe": 0.05
        },
        PositionType.AOE: {
            "safety": 0.20, "damage": 0.20, "escape": 0.15,
            "terrain": 0.10, "aoe": 0.35
        },
        PositionType.BALANCED: {
            "safety": 0.30, "damage": 0.25, "escape": 0.20,
            "terrain": 0.15, "aoe": 0.10
        }
    }
    
    def __init__(self):
        """Initialize positioning engine"""
        self.last_position: Optional[Tuple[int, int]] = None
        self.position_history: List[Tuple[int, int]] = []
        self.evaluations_count = 0
        
        logger.info("PositioningEngine initialized with 5-factor scoring")
    
    def find_optimal_position(
        self,
        char_pos: Tuple[int, int],
        target_pos: Tuple[int, int],
        skill_range: int,
        enemies: List[Dict[str, Any]],
        map_data: Dict[str, Any],
        hp_percent: float,
        job_class: str,
        aoe_range: int = 0
    ) -> PositionScore:
        """
        Find optimal position using 5-factor scoring.
        
        Args:
            char_pos: Current character position (x, y)
            target_pos: Primary target position (x, y)
            skill_range: Character's effective skill range
            enemies: List of enemy dicts with positions
            map_data: Map walkability data {walkable: set, walls: set}
            hp_percent: Current HP percentage (0.0-1.0)
            job_class: Job class for positioning strategy
            aoe_range: AoE skill range (0 if no AoE)
        
        Returns:
            PositionScore for optimal position
        """
        self.evaluations_count += 1
        
        # Determine position type based on context
        pos_type = self._determine_position_type(
            hp_percent, len(enemies), job_class, aoe_range
        )
        
        # Get weights for position type
        weights = self.WEIGHTS[pos_type].copy()
        
        # Adjust weights dynamically (opkAI adaptive logic)
        if hp_percent < 0.30:
            # Low HP: prioritize safety and escape
            weights["safety"] = min(1.0, weights["safety"] + 0.15)
            weights["damage"] = max(0.0, weights["damage"] - 0.10)
            weights["escape"] = min(1.0, weights["escape"] + 0.05)
            # Normalize
            weights = self._normalize_weights(weights)
        
        # Generate candidate positions (opkAI: circle around target at skill range)
        candidates = self._generate_candidates(
            target_pos, skill_range, map_data, char_pos
        )
        
        if not candidates:
            # No valid positions, stay at current
            logger.warning("No valid positioning candidates found, staying at current position")
            return self._score_position(
                char_pos, target_pos, enemies, map_data, weights, aoe_range, pos_type
            )
        
        # Score each candidate
        best_score = None
        for pos in candidates:
            score = self._score_position(
                pos, target_pos, enemies, map_data, weights, aoe_range, pos_type
            )
            if best_score is None or score.total_score > best_score.total_score:
                best_score = score
        
        # Track history
        if best_score:
            self.last_position = (best_score.x, best_score.y)
            self.position_history.append((best_score.x, best_score.y))
            if len(self.position_history) > 10:
                self.position_history.pop(0)
        
        logger.debug(f"Optimal position: ({best_score.x}, {best_score.y}) "
                    f"score={best_score.total_score:.2f} type={pos_type.value}")
        
        return best_score
    
    def _score_position(
        self,
        pos: Tuple[int, int],
        target: Tuple[int, int],
        enemies: List[Dict[str, Any]],
        map_data: Dict[str, Any],
        weights: Dict[str, float],
        aoe_range: int,
        pos_type: PositionType
    ) -> PositionScore:
        """
        5-factor position scoring from opkAI.
        
        Each factor scores 0.0-1.0, weighted by position type.
        """
        
        # Factor 1: Safety (distance from enemies, wall protection)
        safety = self._calculate_safety(pos, enemies, map_data)
        
        # Factor 2: Damage (can reach target, enemies in range)
        damage = self._calculate_damage_potential(pos, target, enemies)
        
        # Factor 3: Escape (available escape routes)
        escape = self._calculate_escape_routes(pos, map_data, enemies)
        
        # Factor 4: Terrain (walls, choke points, corners)
        terrain = self._calculate_terrain_advantage(pos, map_data)
        
        # Factor 5: AoE (enemies in AoE range)
        aoe = self._calculate_aoe_potential(pos, enemies, aoe_range)
        
        # Weighted total
        total = (
            safety * weights["safety"] +
            damage * weights["damage"] +
            escape * weights["escape"] +
            terrain * weights["terrain"] +
            aoe * weights["aoe"]
        )
        
        return PositionScore(
            x=pos[0],
            y=pos[1],
            total_score=total,
            safety_score=safety,
            damage_score=damage,
            escape_score=escape,
            terrain_score=terrain,
            aoe_score=aoe,
            position_type=pos_type.value
        )
    
    def _calculate_safety(
        self,
        pos: Tuple[int, int],
        enemies: List[Dict[str, Any]],
        map_data: Dict[str, Any]
    ) -> float:
        """
        Calculate safety score (0.0-1.0).
        
        Factors:
        - Distance from nearest enemy
        - Number of enemies in danger zone
        - Wall protection
        """
        if not enemies:
            return 1.0
        
        # Find nearest enemy
        min_distance = float('inf')
        danger_zone_count = 0
        
        for enemy in enemies:
            enemy_pos = enemy.get('pos', (0, 0))
            dist = self._distance(pos, enemy_pos)
            min_distance = min(min_distance, dist)
            
            if dist < 3:  # Danger zone = 3 cells
                danger_zone_count += 1
        
        # Distance safety (opkAI: 5+ cells is safe)
        distance_safety = min(1.0, min_distance / 5.0)
        
        # Danger zone penalty
        danger_penalty = max(0.0, 1.0 - danger_zone_count * 0.3)
        
        # Wall protection bonus
        wall_protection = self._check_wall_protection(pos, map_data)
        
        # Combined safety
        safety = (distance_safety * 0.5 + danger_penalty * 0.3 + wall_protection * 0.2)
        
        return max(0.0, min(1.0, safety))
    
    def _calculate_damage_potential(
        self,
        pos: Tuple[int, int],
        target: Tuple[int, int],
        enemies: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate damage potential score (0.0-1.0).
        
        Factors:
        - Can reach primary target
        - Number of enemies in attack range
        """
        # Can reach target?
        target_dist = self._distance(pos, target)
        if target_dist <= 12:  # Within reasonable range
            target_reachable = 1.0 - (target_dist / 12.0) * 0.5
        else:
            target_reachable = 0.0
        
        # Count enemies in range (bonus for multiple)
        enemies_in_range = 0
        for enemy in enemies:
            enemy_pos = enemy.get('pos', (0, 0))
            if self._distance(pos, enemy_pos) <= 10:
                enemies_in_range += 1
        
        range_bonus = min(0.5, enemies_in_range * 0.1)
        
        damage = target_reachable + range_bonus
        return max(0.0, min(1.0, damage))
    
    def _calculate_escape_routes(
        self,
        pos: Tuple[int, int],
        map_data: Dict[str, Any],
        enemies: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate escape route availability (0.0-1.0).
        
        Factors:
        - Number of walkable adjacent cells
        - Direction away from enemies
        """
        walkable = map_data.get('walkable', set())
        
        # Check 8 adjacent cells
        adjacent_walkable = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                adjacent = (pos[0] + dx, pos[1] + dy)
                if adjacent in walkable:
                    adjacent_walkable += 1
        
        # More walkable cells = better escape
        escape_score = adjacent_walkable / 8.0
        
        # Bonus if escape routes lead away from enemies
        if enemies:
            enemy_positions = [e.get('pos', (0, 0)) for e in enemies]
            avg_enemy_x = sum(p[0] for p in enemy_positions) / len(enemy_positions)
            avg_enemy_y = sum(p[1] for p in enemy_positions) / len(enemy_positions)
            
            # Check if we're positioned away from enemy center
            enemy_center = (avg_enemy_x, avg_enemy_y)
            dist_from_enemies = self._distance(pos, enemy_center)
            
            if dist_from_enemies > 5:
                escape_score += 0.2
        
        return max(0.0, min(1.0, escape_score))
    
    def _calculate_terrain_advantage(
        self,
        pos: Tuple[int, int],
        map_data: Dict[str, Any]
    ) -> float:
        """
        Calculate terrain advantage score (0.0-1.0).
        
        Factors:
        - Adjacent walls (protection)
        - Corner position (harder to flank)
        - Choke point (control area)
        """
        walls = map_data.get('walls', set())
        walkable = map_data.get('walkable', set())
        
        # Count adjacent walls
        adjacent_walls = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                adjacent = (pos[0] + dx, pos[1] + dy)
                if adjacent in walls:
                    adjacent_walls += 1
        
        # Wall advantage (opkAI: 2-3 walls is optimal)
        if 2 <= adjacent_walls <= 3:
            wall_score = 1.0
        elif adjacent_walls == 1 or adjacent_walls == 4:
            wall_score = 0.7
        elif adjacent_walls >= 5:
            wall_score = 0.3  # Too enclosed
        else:
            wall_score = 0.5
        
        # Corner bonus (2+ walls in L-shape)
        is_corner = self._check_corner(pos, walls)
        corner_bonus = 0.3 if is_corner else 0.0
        
        terrain = min(1.0, wall_score + corner_bonus)
        return terrain
    
    def _calculate_aoe_potential(
        self,
        pos: Tuple[int, int],
        enemies: List[Dict[str, Any]],
        aoe_range: int
    ) -> float:
        """
        Calculate AoE skill potential (0.0-1.0).
        
        Score based on number of enemies within AoE range.
        """
        if aoe_range == 0 or not enemies:
            return 0.0
        
        # Count enemies in AoE range
        enemies_in_aoe = 0
        for enemy in enemies:
            enemy_pos = enemy.get('pos', (0, 0))
            if self._distance(pos, enemy_pos) <= aoe_range:
                enemies_in_aoe += 1
        
        # Score: 3+ enemies = perfect, 2 = good, 1 = ok
        if enemies_in_aoe >= 3:
            return 1.0
        elif enemies_in_aoe == 2:
            return 0.7
        elif enemies_in_aoe == 1:
            return 0.4
        else:
            return 0.0
    
    def _check_wall_protection(
        self,
        pos: Tuple[int, int],
        map_data: Dict[str, Any]
    ) -> float:
        """Check if position has wall protection (0.0-1.0)"""
        walls = map_data.get('walls', set())
        
        # Count adjacent walls
        wall_count = 0
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx == 0 and dy == 0:
                    continue
                if (pos[0] + dx, pos[1] + dy) in walls:
                    wall_count += 1
        
        # 2-3 walls is optimal
        if 2 <= wall_count <= 3:
            return 1.0
        elif wall_count == 1 or wall_count == 4:
            return 0.6
        elif wall_count >= 5:
            return 0.2
        else:
            return 0.3
    
    def _check_corner(
        self,
        pos: Tuple[int, int],
        walls: set
    ) -> bool:
        """Check if position is a corner (L-shaped wall pattern)"""
        # Check all 4 corner patterns
        corner_patterns = [
            [(0, -1), (-1, 0)],   # Top-left
            [(0, -1), (1, 0)],    # Top-right
            [(0, 1), (-1, 0)],    # Bottom-left
            [(0, 1), (1, 0)]      # Bottom-right
        ]
        
        for pattern in corner_patterns:
            if all((pos[0] + dx, pos[1] + dy) in walls for dx, dy in pattern):
                return True
        
        return False
    
    def _generate_candidates(
        self,
        target_pos: Tuple[int, int],
        skill_range: int,
        map_data: Dict[str, Any],
        current_pos: Tuple[int, int]
    ) -> List[Tuple[int, int]]:
        """
        Generate candidate positions (opkAI: circle around target at skill range).
        
        Returns positions in a circle around target at optimal range.
        """
        walkable = map_data.get('walkable', set())
        if not walkable:
            # If no walkability data, generate grid around target
            walkable = set()
            for dx in range(-skill_range-2, skill_range+3):
                for dy in range(-skill_range-2, skill_range+3):
                    walkable.add((target_pos[0] + dx, target_pos[1] + dy))
        
        candidates = []
        
        # Generate circle points at skill_range
        num_points = 16  # 16 points around circle
        for i in range(num_points):
            angle = (2 * math.pi * i) / num_points
            x = int(target_pos[0] + skill_range * math.cos(angle))
            y = int(target_pos[1] + skill_range * math.sin(angle))
            
            if (x, y) in walkable:
                candidates.append((x, y))
        
        # Also add current position as candidate
        if current_pos in walkable:
            candidates.append(current_pos)
        
        # Add positions slightly closer/farther (±1-2 cells)
        for offset in [-2, -1, 1, 2]:
            adjusted_range = skill_range + offset
            if adjusted_range < 3:
                continue
            
            for i in range(0, num_points, 4):  # Fewer points for adjusted ranges
                angle = (2 * math.pi * i) / num_points
                x = int(target_pos[0] + adjusted_range * math.cos(angle))
                y = int(target_pos[1] + adjusted_range * math.sin(angle))
                
                if (x, y) in walkable and (x, y) not in candidates:
                    candidates.append((x, y))
        
        return candidates
    
    def _determine_position_type(
        self,
        hp_percent: float,
        enemy_count: int,
        job_class: str,
        aoe_range: int
    ) -> PositionType:
        """
        Determine positioning strategy based on context (opkAI adaptive logic).
        """
        # Emergency retreat
        if hp_percent < 0.30:
            return PositionType.RETREAT
        
        # Defensive if low HP or many enemies
        if hp_percent < 0.50 or enemy_count > 4:
            return PositionType.DEFENSIVE
        
        # AoE if we have AoE skills and multiple enemies
        if aoe_range > 0 and enemy_count >= 3:
            return PositionType.AOE
        
        # Offensive if healthy and ranged class
        ranged_classes = ['archer', 'hunter', 'mage', 'wizard', 'sage', 'gunslinger', 'ranger']
        if hp_percent > 0.70 and job_class.lower() in ranged_classes:
            return PositionType.OFFENSIVE
        
        # Default: balanced
        return PositionType.BALANCED
    
    def _normalize_weights(self, weights: Dict[str, float]) -> Dict[str, float]:
        """Normalize weights to sum to 1.0"""
        total = sum(weights.values())
        if total == 0:
            return weights
        return {k: v / total for k, v in weights.items()}
    
    def _distance(self, pos1: Tuple[int, int], pos2: Tuple[int, int]) -> float:
        """Calculate Euclidean distance"""
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get positioning metrics"""
        return {
            'evaluations_count': self.evaluations_count,
            'position_history_length': len(self.position_history),
            'last_position': self.last_position
        }
