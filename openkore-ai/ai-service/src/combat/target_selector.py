"""
Enhanced Target Selection - opkAI Priority 1
Multi-factor target scoring with XP/zeny efficiency optimization
Prevents target hopping and maximizes farming efficiency
"""

from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Optional
from loguru import logger


@dataclass
class TargetScore:
    """Target evaluation result"""
    monster_id: int
    monster_name: str
    score: float
    distance: float
    xp_efficiency: float      # XP per second
    zeny_efficiency: float    # Zeny per second
    time_to_kill: float       # Estimated seconds
    reasons: List[str]        # Scoring breakdown
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        return asdict(self)


class TargetSelector:
    """
    Enhanced target selection with XP/zeny efficiency from opkAI.
    
    Scoring factors (opkAI PHASE 2):
    1. XP Efficiency (XP per second)
    2. Zeny Efficiency (loot value per second)
    3. Priority targets (MVP, Boss, Quest, Aggressive)
    4. Level optimization (±5 levels optimal)
    5. Distance penalty
    6. Element advantage
    7. Low HP finishing bonus
    8. Anti-hopping (50% better required to switch)
    """
    
    # Priority weights from opkAI
    WEIGHT_MVP = 1000.0
    WEIGHT_BOSS = 500.0
    WEIGHT_AGGRESSIVE = 200.0
    WEIGHT_QUEST = 150.0
    WEIGHT_OPTIMAL_LEVEL = 100.0
    WEIGHT_NEARBY = 50.0
    WEIGHT_LOW_HP = 75.0
    WEIGHT_ELEMENT = 120.0
    WEIGHT_PASSIVE = 10.0
    
    # Element advantage matrix
    ELEMENT_MATRIX = {
        'neutral': {'fire': 0, 'water': 0, 'earth': 0, 'wind': 0},
        'fire': {'water': -1, 'earth': 1, 'wind': 1},
        'water': {'fire': 1, 'earth': -1, 'wind': 0},
        'earth': {'fire': -1, 'water': 1, 'wind': -1},
        'wind': {'water': 1, 'earth': 1, 'fire': 0},
        'holy': {'shadow': 1, 'undead': 1},
        'shadow': {'holy': -1},
        'poison': {'neutral': 0.25},
        'ghost': {'ghost': 1},
        'undead': {'holy': -1}
    }
    
    # Loot value database (sample - from opkAI monster_db)
    LOOT_VALUES = {
        1002: 50,    # Poring (Jellopy)
        1007: 150,   # Fabre (Fluff)
        1031: 300,   # Poporing (Sticky Mucus)
        1113: 5000,  # Drops (Old Card Album)
        1115: 50000, # Eddga (MVP drops)
        1511: 80000, # Amon Ra (MVP drops)
    }
    
    def __init__(self):
        """Initialize target selector with opkAI parameters"""
        self.current_target: Optional[int] = None
        self.target_lock_time: float = 0.0
        
        # Performance tracking
        self.selection_count = 0
        self.target_switches = 0
        
        logger.info("TargetSelector initialized with XP/zeny efficiency optimization")
    
    def select_best_target(
        self,
        monsters: List[Dict[str, Any]],
        character: Dict[str, Any],
        quest_targets: Optional[List[int]] = None
    ) -> Optional[TargetScore]:
        """
        Select best target using multi-factor scoring.
        
        Args:
            monsters: List of visible monsters with stats
            character: Character state (level, pos, attack, etc)
            quest_targets: Optional list of quest target IDs
        
        Returns:
            TargetScore for best target, or None if no valid targets
        """
        if not monsters:
            return None
        
        self.selection_count += 1
        quest_targets = quest_targets or []
        
        # Score all monsters
        scored = []
        for monster in monsters:
            score = self._calculate_score(monster, character, quest_targets)
            scored.append(score)
        
        # Sort by score descending
        scored.sort(key=lambda x: x.score, reverse=True)
        
        # Anti-hopping logic (opkAI): Only switch if new target is 50% better
        if self.current_target is not None:
            current_score = next(
                (s for s in scored if s.monster_id == self.current_target),
                None
            )
            if current_score is not None:
                best_score = scored[0]
                
                # Require 50% improvement to switch targets
                if best_score.score < current_score.score * 1.50:
                    logger.debug(f"Target locked: {current_score.monster_name} "
                               f"(score={current_score.score:.0f} vs {best_score.score:.0f})")
                    return current_score
                else:
                    self.target_switches += 1
                    logger.debug(f"Target switch: {current_score.monster_name} -> {best_score.monster_name} "
                               f"(improvement: {(best_score.score/current_score.score - 1)*100:.0f}%)")
        
        # Select best target
        best = scored[0]
        self.current_target = best.monster_id
        
        return best
    
    def _calculate_score(
        self,
        monster: Dict[str, Any],
        character: Dict[str, Any],
        quest_targets: List[int]
    ) -> TargetScore:
        """
        Multi-factor scoring from opkAI.
        
        Monster dict expected keys:
        - id, name, level, hp, hp_max, pos
        - base_exp, job_exp, element, race, size
        - aggressive, targeting_us, is_mvp, is_boss
        """
        total_score = 0.0
        reasons = []
        
        # Calculate distance
        char_pos = character.get('pos', (0, 0))
        monster_pos = monster.get('pos', (0, 0))
        distance = self._calculate_distance(char_pos, monster_pos)
        
        # Calculate combat metrics
        character_dps = self._estimate_dps(character)
        monster_hp = monster.get('hp_max', monster.get('hp', 1000))
        time_to_kill = max(1.0, monster_hp / max(1, character_dps))
        
        # Factor 1: XP Efficiency (opkAI PHASE 2)
        base_exp = monster.get('base_exp', 0)
        xp_per_second = base_exp / time_to_kill
        
        # Factor 2: Loot Value Efficiency
        loot_value = self._estimate_loot_value(monster)
        zeny_per_second = loot_value / time_to_kill
        
        # Combined efficiency score (60% XP, 40% Zeny)
        efficiency = (xp_per_second * 0.6 + zeny_per_second * 0.4) / 10.0
        total_score += efficiency
        if efficiency > 10:
            reasons.append(f"High efficiency: {efficiency:.1f}")
        
        # Factor 3: Priority bonuses (opkAI weights)
        if monster.get('is_mvp', False):
            total_score += self.WEIGHT_MVP
            reasons.append("MVP +1000")
        
        if monster.get('is_boss', False):
            total_score += self.WEIGHT_BOSS
            reasons.append("Boss +500")
        
        if monster.get('targeting_us', False):
            total_score += self.WEIGHT_AGGRESSIVE
            reasons.append("Targeting us +200")
        
        if monster.get('id') in quest_targets:
            total_score += self.WEIGHT_QUEST
            reasons.append("Quest target +150")
        
        # Factor 4: Optimal level range (±5 levels from opkAI)
        char_level = character.get('level', 1)
        monster_level = monster.get('level', 1)
        level_diff = abs(char_level - monster_level)
        
        if level_diff <= 5:
            level_score = self.WEIGHT_OPTIMAL_LEVEL * (1.0 - level_diff / 10)
            total_score += level_score
            reasons.append(f"Level optimal +{level_score:.0f}")
        elif level_diff > 10:
            penalty = min(50.0, (level_diff - 10) * 5.0)
            total_score -= penalty
            reasons.append(f"Level penalty -{penalty:.0f}")
        
        # Factor 7: Low HP finishing bonus (opkAI logic)
        hp_percent = monster.get('hp', monster_hp) / max(1, monster_hp)
        if hp_percent <= 0.30:
            bonus = self.WEIGHT_LOW_HP * (1.0 - hp_percent)
            total_score += bonus
            reasons.append(f"Low HP +{bonus:.0f}")
        
        # Factor 6: Element advantage (opkAI)
        element_mod = self._element_modifier(character, monster)
        if element_mod > 1.0:
            bonus = self.WEIGHT_ELEMENT * (element_mod - 1.0)
            total_score += bonus
            reasons.append(f"Element advantage +{bonus:.0f}")
        elif element_mod < 1.0:
            penalty = self.WEIGHT_ELEMENT * (1.0 - element_mod)
            total_score -= penalty
            reasons.append(f"Element disadvantage -{penalty:.0f}")
        
        # Factor 5: Distance penalty (opkAI: 2 points per cell)
        distance_penalty = distance * 2.0
        total_score -= distance_penalty
        
        # Aggro type bonus (opkAI)
        if monster.get('aggressive', False):
            total_score += 50.0
        else:
            total_score += self.WEIGHT_PASSIVE
        
        # Add base reasons if none
        if not reasons:
            reasons.append(f"Standard target (dist={distance:.1f})")
        
        return TargetScore(
            monster_id=monster.get('id', 0),
            monster_name=monster.get('name', 'Unknown'),
            score=total_score,
            distance=distance,
            xp_efficiency=xp_per_second,
            zeny_efficiency=zeny_per_second,
            time_to_kill=time_to_kill,
            reasons=reasons
        )
    
    def _estimate_dps(self, character: Dict[str, Any]) -> float:
        """
        Estimate character DPS (damage per second).
        
        Factors:
        - Attack or MATK (whichever is higher)
        - Attack speed (ASPD)
        - Buffs
        """
        attack = character.get('attack', 0)
        matk = character.get('matk', 0)
        aspd = character.get('aspd', 150)  # Default ASPD 150
        
        # Use higher damage type
        base_damage = max(attack, matk)
        
        # ASPD to attacks per second (approximate)
        # ASPD 190 = ~2 attacks/sec, ASPD 150 = ~1 attack/sec
        attacks_per_sec = (aspd - 100) / 50.0
        attacks_per_sec = max(0.5, min(3.0, attacks_per_sec))
        
        # Apply buff multipliers
        buffs = character.get('buffs', [])
        buff_mult = 1.0
        if 'blessing' in buffs or 'AL_BLESSING' in buffs:
            buff_mult *= 1.20
        if 'increase_agi' in buffs or 'AL_INCAGI' in buffs:
            buff_mult *= 1.10
        
        dps = base_damage * attacks_per_sec * buff_mult
        return dps
    
    def _estimate_loot_value(self, monster: Dict[str, Any]) -> float:
        """
        Estimate loot value in zeny (opkAI monster_db values).
        """
        monster_id = monster.get('id', 0)
        
        # Use database if available
        if monster_id in self.LOOT_VALUES:
            return self.LOOT_VALUES[monster_id]
        
        # Fallback: estimate from level
        level = monster.get('level', 1)
        base_value = level * 10
        
        # MVP/Boss bonus
        if monster.get('is_mvp', False):
            base_value *= 100
        elif monster.get('is_boss', False):
            base_value *= 10
        
        return base_value
    
    def _element_modifier(
        self,
        character: Dict[str, Any],
        monster: Dict[str, Any]
    ) -> float:
        """
        Calculate element damage modifier (opkAI element matrix).
        
        Returns:
            Multiplier (0.5 = -50%, 1.0 = neutral, 2.0 = +100%)
        """
        char_element = character.get('element', 'neutral').lower()
        monster_element = monster.get('element', 'neutral').lower()
        
        if char_element not in self.ELEMENT_MATRIX:
            return 1.0
        
        advantages = self.ELEMENT_MATRIX[char_element]
        modifier = advantages.get(monster_element, 0)
        
        # Convert to multiplier: -1 = 0.5x, 0 = 1.0x, +1 = 2.0x
        if modifier == -1:
            return 0.5
        elif modifier == 0:
            return 1.0
        elif modifier == 1:
            return 2.0
        else:
            return 1.0 + modifier * 0.25  # Fractional advantages
    
    def _calculate_distance(
        self,
        pos1: tuple,
        pos2: tuple
    ) -> float:
        """Calculate Euclidean distance"""
        import math
        dx = pos1[0] - pos2[0]
        dy = pos1[1] - pos2[1]
        return math.sqrt(dx * dx + dy * dy)
    
    def clear_target(self):
        """Clear current target (e.g., when target dies)"""
        self.current_target = None
        self.target_lock_time = 0.0
    
    def get_metrics(self) -> Dict[str, int]:
        """Get targeting metrics"""
        return {
            'selection_count': self.selection_count,
            'target_switches': self.target_switches,
            'switch_rate': (self.target_switches / max(1, self.selection_count)) * 100
        }
    
    def force_target(self, monster_id: int):
        """Force lock to specific target (e.g., quest target)"""
        self.current_target = monster_id
        logger.info(f"Target force-locked to {monster_id}")


# Utility function for priority override
def should_prioritize_mvp(monsters: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Check if any MVP is present and should be prioritized.
    
    Returns:
        MVP monster dict if found, None otherwise
    """
    for monster in monsters:
        if monster.get('is_mvp', False):
            return monster
    return None
