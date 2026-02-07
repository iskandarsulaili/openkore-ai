"""
Threat Assessment System - opkAI Priority 1
Pre-engagement threat evaluation with 9-factor analysis
Prevents deaths by calculating win probability before engaging enemies
"""

from enum import Enum
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
import math
from loguru import logger


class ThreatLevel(Enum):
    """Threat level classification based on win probability"""
    TRIVIAL = "TRIVIAL"           # ≥90% win chance
    MANAGEABLE = "MANAGEABLE"     # 70-90%
    CHALLENGING = "CHALLENGING"   # 50-70%
    DANGEROUS = "DANGEROUS"       # 30-50%
    DEADLY = "DEADLY"             # <30%


@dataclass
class ThreatAssessment:
    """Complete threat assessment result"""
    target_id: int
    threat_level: ThreatLevel
    win_probability: float
    should_engage: bool
    
    # Detailed breakdown
    power_ratio: float
    level_difference: int
    element_advantage: float
    consumables_adequate: bool
    escape_possible: bool
    nearby_threats: int
    equipment_quality: float
    hp_sp_adequate: bool
    
    # Resource predictions
    expected_hp_loss_percent: float
    expected_sp_cost: int
    estimated_kill_time_seconds: float
    
    # Recommendations
    recommended_strategy: str  # "ENGAGE", "AVOID", "PREPARE_FIRST", "FLEE"
    preparation_needed: List[str]  # ["Apply buffs", "Use healing item"]
    reasons: List[str]  # Human-readable explanation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API response"""
        result = asdict(self)
        result['threat_level'] = self.threat_level.value
        return result


class ThreatAssessor:
    """
    Pre-engagement threat evaluation system from opkAI.
    Calculates win probability using 9-factor assessment.
    
    Factors:
    1. Power Ratio (our damage vs enemy HP)
    2. Level Difference (±2% per level)
    3. Element Advantage (±15% per advantage level)
    4. Consumables Check (potions, fly wings)
    5. Escape Possibility (can we flee if needed?)
    6. Nearby Threats (additional enemies)
    7. Equipment Quality (gear score)
    8. HP/SP Status (resource adequacy)
    9. Support Skills (healing, buffs)
    """
    
    # MVP and Boss monster IDs from opkAI
    MVP_IDS = [
        1511,  # Amon Ra
        1039,  # Baphomet
        1046,  # Doppelganger
        1086,  # Golden Thief Bug
        1115,  # Eddga
        1150,  # Moonlight Flower
        1159,  # Phreeoni
        1190,  # Orc Lord
        1251,  # Knight of Abyss
        1252,  # Incantation Samurai
        1272,  # Dark Lord
        1312,  # Turtle General
        1373,  # Lord of Death
        1418,  # Evil Snake Lord
        1492,  # Incubus
        1630,  # Bacsojin (White Lady)
        1646,  # Assassin Cross Eremes
        1647,  # Lord Knight Seyren
        1648,  # Whitesmith Howard
        1649,  # High Priest Magaleta
        1650,  # Sniper Cecil
        1651,  # High Wizard Kathryne
        1685,  # Vesper
        1688,  # Lady Tanee
        1708,  # Thanatos
        1719,  # Detale
        1751,  # Randgris
        1768,  # Gloom Under Night
        1785,  # Atroce
        1830,  # Beelzebub
        1871,  # Fallen Bishop
        1874,  # Beelzebub (MVP)
        1917,  # Wounded Morroc
        2022,  # Nidhoggr's Shadow
        2068,  # Dark Guardian Kades
        2087,  # Queen Scaraba
        2131,  # Bijou
    ]
    
    BOSS_IDS = [
        1038,  # Osiris
        1096,  # Angeling
        1112,  # Drake
        1120,  # Ghost Ring
        1147,  # Maya
        1161,  # Pharaoh
        1163,  # Orc Hero
        1191,  # Orc Baby
        1257,  # Injustice
        1296,  # Baphomet Jr.
        1582,  # Deviling
        1583,  # Drops (Golden)
        1584,  # Ghostring (Boss)
        1623,  # RSX-0806
        1633,  # High Orc
    ]
    
    def __init__(self):
        """Initialize threat assessor with opkAI monster databases"""
        self.mvp_ids = set(self.MVP_IDS)
        self.boss_ids = set(self.BOSS_IDS)
        
        # Element advantage matrix
        self.element_matrix = {
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
        
        logger.info(f"ThreatAssessor initialized: {len(self.mvp_ids)} MVPs, {len(self.boss_ids)} Bosses tracked")
    
    def assess_threat(
        self,
        target: Dict[str, Any],
        character: Dict[str, Any],
        nearby_enemies: List[Dict[str, Any]],
        available_consumables: Dict[str, int]
    ) -> ThreatAssessment:
        """
        Comprehensive threat assessment before engagement.
        
        Args:
            target: {id, level, hp, hp_max, element, race, size, etc}
            character: {level, hp, sp, hp_max, sp_max, attack, matk, buffs, equipment, skills}
            nearby_enemies: List of nearby enemy dicts
            available_consumables: {potions: int, fly_wings: int}
        
        Returns:
            ThreatAssessment with complete analysis
        """
        
        # Calculate power ratio (Factor 1)
        our_power = self._calculate_our_power(character)
        enemy_power = self._calculate_enemy_power(target)
        power_ratio = our_power / max(1, enemy_power)
        
        # Base win probability from power ratio
        base_prob = self._power_ratio_to_probability(power_ratio)
        
        # Apply 9-factor modifiers
        win_prob = base_prob
        
        # Factor 2: Level difference modifier (±2% per level)
        level_diff = character.get('level', 1) - target.get('level', 1)
        win_prob += level_diff * 0.02
        
        # Factor 3: Element advantage modifier (±15% per advantage)
        element_adv = self._calculate_element_advantage(character, target)
        win_prob += element_adv * 0.15
        
        # Factor 4: Consumables penalty
        consumables_ok = self._check_consumables(target, available_consumables)
        if not consumables_ok:
            win_prob *= 0.70
        
        # Factor 6: Nearby threats penalty (-10% per additional enemy)
        nearby_count = len(nearby_enemies)
        win_prob -= nearby_count * 0.10
        
        # Factor 7: Equipment quality bonus
        equip_quality = self._calculate_equipment_quality(character)
        win_prob += equip_quality * 0.20
        
        # Factor 8: HP/SP penalties
        hp_percent = character.get('hp', 0) / max(1, character.get('hp_max', 1))
        sp_percent = character.get('sp', 0) / max(1, character.get('sp_max', 1))
        if hp_percent < 0.50:
            win_prob -= 0.20
        if sp_percent < 0.30:
            win_prob -= 0.15
        
        # MVP/Boss penalties
        is_mvp = target.get('id') in self.mvp_ids
        is_boss = target.get('id') in self.boss_ids
        if is_mvp:
            win_prob *= 0.40
        elif is_boss:
            win_prob *= 0.60
        
        # Factor 9: Support skills bonus
        if 'heal' in character.get('skills', []) or 'AL_HEAL' in character.get('skills', []):
            win_prob += 0.10
        
        # Factor 5: Escape possibility check
        escape_possible = self._check_escape_possibility(
            character, target, nearby_enemies, available_consumables
        )
        if not escape_possible:
            win_prob *= 0.85
        
        # Clamp win probability
        win_prob = max(0.0, min(1.0, win_prob))
        
        # Determine threat level
        threat_level = self._probability_to_threat_level(win_prob)
        
        # Engagement decision (opkAI logic)
        should_engage = (
            threat_level not in [ThreatLevel.DEADLY, ThreatLevel.DANGEROUS] and
            win_prob >= 0.50 and
            consumables_ok and
            (nearby_count < 3 or escape_possible) and
            hp_percent >= 0.30
        )
        
        # Resource predictions
        expected_hp_loss = self._predict_hp_loss(target, character, win_prob)
        expected_sp_cost = self._predict_sp_cost(target, character)
        estimated_ttk = self._estimate_kill_time(target, character)
        
        # Generate recommendations
        strategy = self._recommend_strategy(
            should_engage, threat_level, consumables_ok, hp_percent
        )
        preparation = self._recommend_preparation(character, target, win_prob)
        reasons = self._generate_reasons(
            power_ratio, level_diff, element_adv, nearby_count, is_mvp, is_boss
        )
        
        assessment = ThreatAssessment(
            target_id=target.get('id', 0),
            threat_level=threat_level,
            win_probability=win_prob,
            should_engage=should_engage,
            power_ratio=power_ratio,
            level_difference=level_diff,
            element_advantage=element_adv,
            consumables_adequate=consumables_ok,
            escape_possible=escape_possible,
            nearby_threats=nearby_count,
            equipment_quality=equip_quality,
            hp_sp_adequate=hp_percent >= 0.30 and sp_percent >= 0.15,
            expected_hp_loss_percent=expected_hp_loss,
            expected_sp_cost=expected_sp_cost,
            estimated_kill_time_seconds=estimated_ttk,
            recommended_strategy=strategy,
            preparation_needed=preparation,
            reasons=reasons
        )
        
        logger.debug(f"Threat assessment: {target.get('name', 'Unknown')} -> {threat_level.value} ({win_prob:.2%})")
        
        return assessment
    
    def _calculate_our_power(self, character: Dict[str, Any]) -> float:
        """Calculate character combat power"""
        attack = character.get('attack', 0)
        matk = character.get('matk', 0)
        
        # Use higher of physical/magical attack
        base_power = max(attack, matk)
        
        # Buff multipliers
        buffs = character.get('buffs', [])
        buff_mult = 1.0
        if 'blessing' in buffs or 'AL_BLESSING' in buffs:
            buff_mult *= 1.20
        if 'increase_agi' in buffs or 'AL_INCAGI' in buffs:
            buff_mult *= 1.15
        
        return base_power * buff_mult
    
    def _calculate_enemy_power(self, target: Dict[str, Any]) -> float:
        """Estimate enemy combat power"""
        hp = target.get('hp_max', target.get('hp', 1000))
        level = target.get('level', 1)
        
        # Base power = HP * level factor
        base_power = hp * (1 + level * 0.1)
        
        return base_power
    
    def _power_ratio_to_probability(self, power_ratio: float) -> float:
        """Convert power ratio to base win probability (opkAI formula)"""
        # Sigmoid-like mapping
        if power_ratio >= 3.0:
            return 0.95
        elif power_ratio >= 2.0:
            return 0.85
        elif power_ratio >= 1.5:
            return 0.75
        elif power_ratio >= 1.0:
            return 0.60
        elif power_ratio >= 0.75:
            return 0.45
        elif power_ratio >= 0.50:
            return 0.30
        else:
            return 0.15
    
    def _calculate_element_advantage(self, character: Dict[str, Any], target: Dict[str, Any]) -> float:
        """Calculate element advantage (-1 to +1)"""
        char_element = character.get('element', 'neutral').lower()
        target_element = target.get('element', 'neutral').lower()
        
        if char_element not in self.element_matrix:
            return 0.0
        
        advantages = self.element_matrix[char_element]
        return advantages.get(target_element, 0.0)
    
    def _check_consumables(self, target: Dict[str, Any], consumables: Dict[str, int]) -> bool:
        """Check if we have adequate consumables for this fight"""
        potions = consumables.get('potions', 0)
        fly_wings = consumables.get('fly_wings', 0)
        
        # MVP: need 10+ potions and 3+ fly wings
        if target.get('id') in self.mvp_ids:
            return potions >= 10 and fly_wings >= 3
        
        # Boss: need 5+ potions and 1+ fly wing
        if target.get('id') in self.boss_ids:
            return potions >= 5 and fly_wings >= 1
        
        # Normal: need 2+ potions
        return potions >= 2
    
    def _check_escape_possibility(
        self,
        character: Dict[str, Any],
        target: Dict[str, Any],
        nearby_enemies: List[Dict[str, Any]],
        consumables: Dict[str, int]
    ) -> bool:
        """Check if escape is possible if fight goes wrong"""
        fly_wings = consumables.get('fly_wings', 0)
        teleport_clips = consumables.get('teleport_clips', 0)
        
        # Can teleport?
        if fly_wings > 0 or teleport_clips > 0:
            return True
        
        # Can outrun? (if not trapped)
        if len(nearby_enemies) < 3:
            return True
        
        # Has teleport skill?
        if 'teleport' in character.get('skills', []):
            return True
        
        return False
    
    def _calculate_equipment_quality(self, character: Dict[str, Any]) -> float:
        """Calculate equipment quality score (0.0 to 1.0)"""
        equipment = character.get('equipment', {})
        
        if not equipment:
            return 0.3  # Basic/no equipment
        
        # Count refined and carded equipment
        refined_count = sum(1 for item in equipment.values() if item.get('refine', 0) > 0)
        carded_count = sum(1 for item in equipment.values() if item.get('cards', []))
        
        total_slots = len(equipment)
        if total_slots == 0:
            return 0.3
        
        quality = (refined_count + carded_count * 2) / (total_slots * 3)
        return min(1.0, quality)
    
    def _predict_hp_loss(self, target: Dict[str, Any], character: Dict[str, Any], win_prob: float) -> float:
        """Predict expected HP loss percentage"""
        # Base loss inversely proportional to win probability
        base_loss = (1.0 - win_prob) * 0.8
        
        # MVP/Boss factor
        if target.get('id') in self.mvp_ids:
            base_loss *= 1.5
        elif target.get('id') in self.boss_ids:
            base_loss *= 1.2
        
        return min(1.0, base_loss)
    
    def _predict_sp_cost(self, target: Dict[str, Any], character: Dict[str, Any]) -> int:
        """Predict expected SP cost"""
        target_hp = target.get('hp_max', target.get('hp', 1000))
        
        # Estimate skills needed
        matk = character.get('matk', 0)
        if matk > 0:
            skills_needed = target_hp / max(1, matk * 3)
            return int(skills_needed * 20)  # ~20 SP per skill
        
        return 0
    
    def _estimate_kill_time(self, target: Dict[str, Any], character: Dict[str, Any]) -> float:
        """Estimate time to kill in seconds"""
        target_hp = target.get('hp_max', target.get('hp', 1000))
        our_power = self._calculate_our_power(character)
        
        # Damage per second (with attack speed factor)
        dps = our_power * 0.5  # Assume 0.5 attacks/sec base
        
        if dps == 0:
            return 999.0
        
        ttk = target_hp / dps
        return min(999.0, ttk)
    
    def _recommend_strategy(
        self,
        should_engage: bool,
        threat_level: ThreatLevel,
        consumables_ok: bool,
        hp_percent: float
    ) -> str:
        """Recommend engagement strategy"""
        if not should_engage:
            if threat_level == ThreatLevel.DEADLY:
                return "FLEE"
            elif not consumables_ok:
                return "PREPARE_FIRST"
            elif hp_percent < 0.30:
                return "PREPARE_FIRST"
            else:
                return "AVOID"
        
        return "ENGAGE"
    
    def _recommend_preparation(
        self,
        character: Dict[str, Any],
        target: Dict[str, Any],
        win_prob: float
    ) -> List[str]:
        """Recommend preparation steps before engagement"""
        preparations = []
        
        hp_percent = character.get('hp', 0) / max(1, character.get('hp_max', 1))
        sp_percent = character.get('sp', 0) / max(1, character.get('sp_max', 1))
        
        if hp_percent < 0.80:
            preparations.append("Heal to >80% HP")
        
        if sp_percent < 0.50:
            preparations.append("Restore SP to >50%")
        
        buffs = character.get('buffs', [])
        if 'blessing' not in buffs and 'AL_BLESSING' not in buffs:
            preparations.append("Apply Blessing buff")
        
        if 'increase_agi' not in buffs and 'AL_INCAGI' not in buffs:
            preparations.append("Apply Increase AGI buff")
        
        if target.get('id') in self.mvp_ids:
            preparations.append("Stock 10+ potions and 3+ Fly Wings")
            preparations.append("Notify party members")
        
        return preparations
    
    def _generate_reasons(
        self,
        power_ratio: float,
        level_diff: int,
        element_adv: float,
        nearby_count: int,
        is_mvp: bool,
        is_boss: bool
    ) -> List[str]:
        """Generate human-readable explanation"""
        reasons = []
        
        if power_ratio >= 2.0:
            reasons.append(f"High power advantage ({power_ratio:.1f}x)")
        elif power_ratio < 0.75:
            reasons.append(f"Power disadvantage ({power_ratio:.1f}x)")
        
        if level_diff >= 5:
            reasons.append(f"Level advantage (+{level_diff})")
        elif level_diff <= -5:
            reasons.append(f"Level disadvantage ({level_diff})")
        
        if element_adv > 0:
            reasons.append("Element advantage")
        elif element_adv < 0:
            reasons.append("Element disadvantage")
        
        if nearby_count > 2:
            reasons.append(f"Multiple enemies nearby ({nearby_count})")
        
        if is_mvp:
            reasons.append("MVP - extreme danger")
        elif is_boss:
            reasons.append("Boss - high danger")
        
        if not reasons:
            reasons.append("Standard combat encounter")
        
        return reasons
    
    def _probability_to_threat_level(self, win_prob: float) -> ThreatLevel:
        """Convert win probability to threat level"""
        if win_prob >= 0.90:
            return ThreatLevel.TRIVIAL
        elif win_prob >= 0.70:
            return ThreatLevel.MANAGEABLE
        elif win_prob >= 0.50:
            return ThreatLevel.CHALLENGING
        elif win_prob >= 0.30:
            return ThreatLevel.DANGEROUS
        else:
            return ThreatLevel.DEADLY
