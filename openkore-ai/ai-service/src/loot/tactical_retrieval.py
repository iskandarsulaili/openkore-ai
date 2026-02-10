"""
Tactical Loot Retrieval System

Implements different tactical approaches for loot retrieval based on risk level.
"""

import logging
from typing import Dict, List, Any, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class LootTactic(Enum):
    """Available loot retrieval tactics."""
    SYSTEMATIC_COLLECTION = "systematic_collection"
    KITING_RETRIEVAL = "kiting"
    HIT_AND_RUN = "hit_and_run"
    TERRAIN_EXPLOITATION = "terrain"
    AGGRO_MANIPULATION = "aggro_manipulation"
    PET_TANKING = "pet_tanking"
    EMERGENCY_GRAB = "emergency_grab"
    SACRIFICE_DECISION = "sacrifice"


class TacticalLootRetrieval:
    """
    Implements tactical loot retrieval strategies for different risk levels.
    
    Risk Levels:
    - Safe (0-30): Systematic collection
    - Moderate (31-60): Tactical approaches (kiting, hit-and-run, etc.)
    - High (61-100): Sacrifice calculation and emergency grab
    """
    
    def __init__(self):
        """Initialize tactical retrieval system."""
        self.monster_db = None  # Monster database for enhanced risk calculation
        logger.info("TacticalLootRetrieval initialized")
    
    def set_monster_database(self, monster_db: 'MonsterDatabase'):
        """
        Set monster database for enhanced risk calculation.
        
        Uses monster database to:
        - Calculate threat level based on monster stats
        - Estimate danger from nearby monsters
        - Factor in monster special abilities
        
        Args:
            monster_db: MonsterDatabase instance from Phase 1
        """
        self.monster_db = monster_db
        logger.info("Integrated monster database for enhanced risk calculation")
    
    def calculate_retrieval_risk(self, item_id: int, context: Dict) -> float:
        """
        Enhanced risk calculation using monster database.
        
        Steps:
        1. Identify monsters near item drop
        2. Get monster stats from database
        3. Calculate threat level based on:
           - Monster level vs player level
           - Monster attack power
           - Monster special abilities
           - Number of monsters
        4. Factor in item value from database
        5. Return risk score (0-100)
        
        Args:
            item_id: Item ID
            context: Context dict with monsters, character, item position
        
        Returns:
            Risk score (0-100)
        """
        if not self.monster_db:
            # Fallback to basic risk calculation
            return self._basic_risk_calculation(context)
        
        # Extract context
        monsters_near_item = context.get('monsters_near_item', [])
        character = context.get('character', {})
        item_position = context.get('item_position', {})
        
        if not monsters_near_item:
            return 0.0  # No monsters = no risk
        
        player_level = character.get('level', 1)
        player_hp = character.get('hp', 0)
        player_max_hp = character.get('max_hp', 1)
        hp_percentage = (player_hp / player_max_hp) * 100
        
        # Analyze each monster
        total_threat = 0.0
        for monster_data in monsters_near_item:
            monster_id = monster_data.get('id')
            monster_distance = monster_data.get('distance', 10)
            
            # Get full monster data from database
            db_monster = self.monster_db.get_monster_by_id(monster_id)
            if not db_monster:
                # Unknown monster, use estimated threat
                total_threat += 20.0
                continue
            
            # Calculate individual monster threat
            monster_level = db_monster.get('level', 1)
            monster_attack = db_monster.get('attack', 0)
            monster_hp = db_monster.get('hp', 0)
            
            # Level difference factor
            level_diff = monster_level - player_level
            if level_diff > 10:
                level_factor = 2.0
            elif level_diff > 5:
                level_factor = 1.5
            elif level_diff > 0:
                level_factor = 1.2
            elif level_diff > -5:
                level_factor = 1.0
            else:
                level_factor = 0.7
            
            # Attack power factor
            # Estimate: can this monster kill player in few hits?
            estimated_damage = monster_attack * 2  # Rough estimate
            hits_to_kill = player_hp / max(estimated_damage, 1)
            if hits_to_kill < 3:
                attack_factor = 2.0
            elif hits_to_kill < 5:
                attack_factor = 1.5
            else:
                attack_factor = 1.0
            
            # Distance factor (closer = more dangerous)
            if monster_distance < 2:
                distance_factor = 2.0
            elif monster_distance < 5:
                distance_factor = 1.5
            elif monster_distance < 10:
                distance_factor = 1.0
            else:
                distance_factor = 0.5
            
            # Monster durability (high HP monsters are obstacles)
            if monster_hp > 10000:
                durability_factor = 1.3
            elif monster_hp > 5000:
                durability_factor = 1.1
            else:
                durability_factor = 1.0
            
            # Calculate monster threat score
            monster_threat = (
                level_factor * 10 +
                attack_factor * 15 +
                distance_factor * 10 +
                durability_factor * 5
            )
            
            total_threat += monster_threat
        
        # Adjust for number of monsters
        monster_count = len(monsters_near_item)
        if monster_count > 5:
            multiplier = 1.5
        elif monster_count > 3:
            multiplier = 1.3
        elif monster_count > 1:
            multiplier = 1.1
        else:
            multiplier = 1.0
        
        total_threat *= multiplier
        
        # Adjust for player HP
        if hp_percentage < 30:
            total_threat *= 1.5
        elif hp_percentage < 50:
            total_threat *= 1.2
        
        # Cap at 100
        final_risk = min(total_threat, 100.0)
        
        logger.debug(f"Risk calculation: {len(monsters_near_item)} monsters, threat={total_threat:.1f}, final_risk={final_risk:.1f}")
        
        return final_risk
    
    def _basic_risk_calculation(self, context: Dict) -> float:
        """Basic risk calculation without monster database."""
        monsters_near_item = context.get('monsters_near_item', [])
        character = context.get('character', {})
        
        monster_count = len(monsters_near_item)
        player_hp_pct = (character.get('hp', 0) / max(character.get('max_hp', 1), 1)) * 100
        
        # Simple formula
        base_risk = monster_count * 15
        hp_factor = (100 - player_hp_pct) * 0.3
        
        return min(base_risk + hp_factor, 100.0)
    
    def execute_tactic(
        self,
        tactic: str,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a specific loot retrieval tactic.
        
        Args:
            tactic: Tactic name (from LootTactic enum)
            target_item: Primary target item
            all_items: All available items sorted by priority
            game_state: Current game state
        
        Returns:
            Action dict for OpenKore execution
        """
        tactic_map = {
            LootTactic.SYSTEMATIC_COLLECTION.value: self.systematic_collection,
            LootTactic.KITING_RETRIEVAL.value: self.kiting_retrieval,
            LootTactic.HIT_AND_RUN.value: self.hit_and_run_grab,
            LootTactic.TERRAIN_EXPLOITATION.value: self.terrain_exploitation,
            LootTactic.AGGRO_MANIPULATION.value: self.aggro_manipulation,
            LootTactic.PET_TANKING.value: self.pet_tanking,
            LootTactic.EMERGENCY_GRAB.value: self.emergency_grab,
            LootTactic.SACRIFICE_DECISION.value: self.sacrifice_decision
        }
        
        handler = tactic_map.get(tactic)
        if not handler:
            logger.error(f"Unknown tactic: {tactic}, falling back to systematic_collection")
            handler = self.systematic_collection
        
        try:
            action = handler(target_item, all_items, game_state)
            logger.info(f"Executing tactic: {tactic} for item: {target_item.get('item_name')}")
            return action
        except Exception as e:
            logger.error(f"Error executing tactic {tactic}: {e}", exc_info=True)
            return self._create_fallback_action(target_item)
    
    # ===== SAFE SITUATION TACTICS (Risk 0-30) =====
    
    def systematic_collection(
        self,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Systematically collect all valuable items in priority order.
        
        Used when situation is safe.
        """
        character_pos = game_state.get("character", {}).get("position", {})
        
        # Filter items worth collecting
        config_priority_threshold = 70  # Don't collect items with priority > 70
        valuable_items = [
            item for item in all_items
            if item.get("priority_level", 100) <= config_priority_threshold
        ]
        
        # Sort by distance for efficient pathing
        valuable_items.sort(key=lambda x: x.get("distance", 999))
        
        # Collect all items in order
        items_to_grab = [item.get("binID") for item in valuable_items if item.get("binID")]
        
        return {
            "action": "loot_tactical",
            "params": {
                "tactic": "systematic_collection",
                "target_item": {
                    "binID": target_item.get("binID"),
                    "item_id": target_item.get("item_id"),
                    "item_name": target_item.get("item_name"),
                    "priority": target_item.get("priority_level")
                },
                "items_to_grab": items_to_grab,
                "accept_death": False,
                "strategy": "collect_all_valuable",
                "movement": "direct_path"
            },
            "reasoning": (
                f"Safe situation: Systematically collecting {len(items_to_grab)} valuable items. "
                f"Top priority: {target_item.get('item_name')} (Priority: {target_item.get('priority_level')})"
            )
        }
    
    # ===== MODERATE RISK TACTICS (Risk 31-60) =====
    
    def kiting_retrieval(
        self,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Kite enemies away, then circle back to grab loot.
        
        Strategy:
        1. Move away from loot to pull enemies
        2. Create distance/lose aggro
        3. Circle back to loot position
        4. Grab item quickly
        """
        character_pos = game_state.get("character", {}).get("position", {})
        item_pos = target_item.get("position", {})
        
        # Calculate kiting direction (opposite of item)
        kite_direction = self._calculate_opposite_direction(character_pos, item_pos)
        
        # Only grab highest priority items (time limited)
        priority_items = [
            item for item in all_items[:5]  # Top 5 items
            if item.get("priority_level", 100) <= 50
        ]
        items_to_grab = [item.get("binID") for item in priority_items if item.get("binID")]
        
        return {
            "action": "loot_tactical",
            "params": {
                "tactic": "kiting",
                "target_item": {
                    "binID": target_item.get("binID"),
                    "item_id": target_item.get("item_id"),
                    "item_name": target_item.get("item_name"),
                    "priority": target_item.get("priority_level")
                },
                "items_to_grab": items_to_grab,
                "accept_death": False,
                "strategy": "kite_and_return",
                "kite_direction": kite_direction,
                "kite_distance": 15,
                "movement": "kiting_pattern"
            },
            "reasoning": (
                f"Moderate risk: Using kiting tactic to retrieve {target_item.get('item_name')}. "
                f"Will kite enemies {kite_direction} direction, then circle back to grab {len(items_to_grab)} items."
            )
        }
    
    def hit_and_run_grab(
        self,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Quick dash in, grab item, escape immediately.
        
        Strategy:
        1. Use speed buff if available
        2. Dash to item
        3. Grab quickly
        4. Use escape skill (Fly Wing, Teleport, etc.)
        """
        character = game_state.get("character", {})
        
        # Check for speed buffs
        has_speed_buff = self._check_speed_buff(character)
        
        # Check for escape options
        escape_options = self._get_escape_options(game_state)
        
        # Only grab top priority items (limited time window)
        urgent_items = [
            item for item in all_items[:3]  # Top 3 items
            if item.get("priority_level", 100) <= 40
        ]
        items_to_grab = [item.get("binID") for item in urgent_items if item.get("binID")]
        
        return {
            "action": "loot_tactical",
            "params": {
                "tactic": "hit_and_run",
                "target_item": {
                    "binID": target_item.get("binID"),
                    "item_id": target_item.get("item_id"),
                    "item_name": target_item.get("item_name"),
                    "priority": target_item.get("priority_level")
                },
                "items_to_grab": items_to_grab,
                "accept_death": False,
                "strategy": "dash_grab_escape",
                "use_speed_buff": not has_speed_buff,
                "escape_method": escape_options[0] if escape_options else "fly_wing",
                "movement": "sprint"
            },
            "reasoning": (
                f"Moderate risk: Hit-and-run tactic for {target_item.get('item_name')}. "
                f"Will dash in, grab {len(items_to_grab)} items, then escape using {escape_options[0] if escape_options else 'fly_wing'}."
            )
        }
    
    def terrain_exploitation(
        self,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use walls, obstacles, or terrain to block enemies while looting.
        
        Strategy:
        1. Identify terrain features
        2. Position to block enemy path
        3. Grab loot from safe side
        """
        character_pos = game_state.get("character", {}).get("position", {})
        item_pos = target_item.get("position", {})
        
        # Find terrain features (walls, obstacles)
        blocking_positions = self._find_blocking_positions(game_state, character_pos, item_pos)
        
        # Grab multiple items if safe
        nearby_items = [
            item for item in all_items[:7]
            if item.get("distance", 999) < 5 and item.get("priority_level", 100) <= 60
        ]
        items_to_grab = [item.get("binID") for item in nearby_items if item.get("binID")]
        
        return {
            "action": "loot_tactical",
            "params": {
                "tactic": "terrain",
                "target_item": {
                    "binID": target_item.get("binID"),
                    "item_id": target_item.get("item_id"),
                    "item_name": target_item.get("item_name"),
                    "priority": target_item.get("priority_level")
                },
                "items_to_grab": items_to_grab,
                "accept_death": False,
                "strategy": "use_terrain_blocking",
                "blocking_positions": blocking_positions,
                "movement": "terrain_aware"
            },
            "reasoning": (
                f"Moderate risk: Using terrain exploitation for {target_item.get('item_name')}. "
                f"Will use obstacles to block enemies and grab {len(items_to_grab)} nearby items."
            )
        }
    
    def aggro_manipulation(
        self,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Temporarily shift enemy aggro away from loot area.
        
        Strategy:
        1. Attack enemy to get aggro
        2. Run in opposite direction
        3. Enemy chases, creating opening
        4. Grab loot while enemy is distracted
        """
        monsters = game_state.get("monsters", [])
        item_pos = target_item.get("position", {})
        
        # Find nearest enemy to manipulate
        nearest_enemy = self._find_nearest_enemy(monsters, item_pos)
        
        # Select high-priority items only
        priority_items = [
            item for item in all_items[:4]
            if item.get("priority_level", 100) <= 45
        ]
        items_to_grab = [item.get("binID") for item in priority_items if item.get("binID")]
        
        return {
            "action": "loot_tactical",
            "params": {
                "tactic": "aggro_manipulation",
                "target_item": {
                    "binID": target_item.get("binID"),
                    "item_id": target_item.get("item_id"),
                    "item_name": target_item.get("item_name"),
                    "priority": target_item.get("priority_level")
                },
                "items_to_grab": items_to_grab,
                "accept_death": False,
                "strategy": "distract_and_grab",
                "aggro_target": nearest_enemy.get("binID") if nearest_enemy else None,
                "distraction_distance": 10,
                "movement": "aggro_kiting"
            },
            "reasoning": (
                f"Moderate risk: Using aggro manipulation for {target_item.get('item_name')}. "
                f"Will distract nearest enemy and grab {len(items_to_grab)} items during opening."
            )
        }
    
    def pet_tanking(
        self,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Use pet or mercenary to tank enemies while looting.
        
        Strategy:
        1. Command pet/mercenary to attack
        2. Pet draws aggro
        3. Grab loot while enemies focus on pet
        """
        character = game_state.get("character", {})
        has_pet = character.get("pet") is not None
        has_homunculus = character.get("homunculus") is not None
        has_mercenary = character.get("mercenary") is not None
        
        # Select items to grab while pet tanks
        tank_window_items = [
            item for item in all_items[:6]
            if item.get("priority_level", 100) <= 55
        ]
        items_to_grab = [item.get("binID") for item in tank_window_items if item.get("binID")]
        
        return {
            "action": "loot_tactical",
            "params": {
                "tactic": "pet_tanking",
                "target_item": {
                    "binID": target_item.get("binID"),
                    "item_id": target_item.get("item_id"),
                    "item_name": target_item.get("item_name"),
                    "priority": target_item.get("priority_level")
                },
                "items_to_grab": items_to_grab,
                "accept_death": False,
                "strategy": "pet_distraction",
                "use_pet": has_pet,
                "use_homunculus": has_homunculus,
                "use_mercenary": has_mercenary,
                "movement": "behind_tank"
            },
            "reasoning": (
                f"Moderate risk: Using pet tanking for {target_item.get('item_name')}. "
                f"Pet/homunculus/mercenary will distract enemies while grabbing {len(items_to_grab)} items."
            )
        }
    
    # ===== HIGH RISK TACTICS (Risk 61-100) =====
    
    def emergency_grab(
        self,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Emergency grab of top 1-3 items before death.
        
        Used when death is imminent but items are worth securing.
        """
        # Only grab absolute highest priority items
        critical_items = [
            item for item in all_items[:3]
            if item.get("priority_level", 100) <= 15  # Only highest priority
        ]
        
        if not critical_items:
            critical_items = [target_item]
        
        items_to_grab = [item.get("binID") for item in critical_items if item.get("binID")]
        
        return {
            "action": "loot_tactical",
            "params": {
                "tactic": "emergency_grab",
                "target_item": {
                    "binID": target_item.get("binID"),
                    "item_id": target_item.get("item_id"),
                    "item_name": target_item.get("item_name"),
                    "priority": target_item.get("priority_level")
                },
                "items_to_grab": items_to_grab,
                "accept_death": True,
                "strategy": "suicide_grab",
                "movement": "desperate_dash"
            },
            "reasoning": (
                f"HIGH RISK: Emergency grab for {target_item.get('item_name')}. "
                f"Death likely but securing {len(items_to_grab)} critical items worth the sacrifice."
            )
        }
    
    def sacrifice_decision(
        self,
        target_item: Dict[str, Any],
        all_items: List[Dict[str, Any]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Make intelligent sacrifice decision: is death worth securing these items?
        
        Factors:
        - Item value vs respawn cost
        - MVP card exception (always worth it)
        - Multiple high-priority items
        """
        # Calculate total value of grabbable items
        sacrifice_worthy_items = [
            item for item in all_items[:5]
            if item.get("priority_level", 100) <= 20
        ]
        
        total_value = sum(item.get("estimated_value", 0) for item in sacrifice_worthy_items)
        
        # Respawn cost estimation
        character = game_state.get("character", {})
        level = character.get("level", 1)
        respawn_cost = self._estimate_respawn_cost(level)
        
        # Check if MVP card present
        has_mvp_card = any(
            item.get("category") == "mvp_card"
            for item in sacrifice_worthy_items
        )
        
        # Decision logic
        sacrifice_justified = (
            has_mvp_card or  # MVP cards always worth it
            total_value >= 5 * respawn_cost  # Value exceeds cost significantly
        )
        
        if sacrifice_justified:
            items_to_grab = [item.get("binID") for item in sacrifice_worthy_items if item.get("binID")]
            
            return {
                "action": "loot_tactical",
                "params": {
                    "tactic": "sacrifice",
                    "target_item": {
                        "binID": target_item.get("binID"),
                        "item_id": target_item.get("item_id"),
                        "item_name": target_item.get("item_name"),
                        "priority": target_item.get("priority_level")
                    },
                    "items_to_grab": items_to_grab,
                    "accept_death": True,
                    "strategy": "calculated_sacrifice",
                    "movement": "all_out_rush",
                    "value_calculation": {
                        "total_item_value": total_value,
                        "respawn_cost": respawn_cost,
                        "value_multiplier": total_value / respawn_cost if respawn_cost > 0 else 999,
                        "has_mvp_card": has_mvp_card
                    }
                },
                "reasoning": (
                    f"HIGH RISK SACRIFICE: {target_item.get('item_name')} worth dying for. "
                    f"Total value: {total_value} zeny vs respawn cost: {respawn_cost} zeny "
                    f"({total_value/respawn_cost if respawn_cost > 0 else 999:.1f}x). "
                    f"{'MVP CARD DETECTED - ALWAYS WORTH IT!' if has_mvp_card else f'Securing {len(items_to_grab)} valuable items.'}"
                )
            }
        else:
            # Retreat - not worth the sacrifice
            return {
                "action": "retreat",
                "params": {
                    "reason": "loot_not_worth_death",
                    "item_value": total_value,
                    "respawn_cost": respawn_cost
                },
                "reasoning": (
                    f"HIGH RISK: Retreating. Items not worth death. "
                    f"Total value: {total_value} vs respawn cost: {respawn_cost}. "
                    f"Survival prioritized."
                )
            }
    
    # ===== HELPER METHODS =====
    
    def _calculate_opposite_direction(
        self,
        from_pos: Dict[str, int],
        to_pos: Dict[str, int]
    ) -> str:
        """Calculate opposite direction for kiting."""
        if not from_pos or not to_pos:
            return "north"
        
        dx = to_pos.get("x", 0) - from_pos.get("x", 0)
        dy = to_pos.get("y", 0) - from_pos.get("y", 0)
        
        # Determine primary direction
        if abs(dx) > abs(dy):
            return "west" if dx > 0 else "east"
        else:
            return "south" if dy > 0 else "north"
    
    def _check_speed_buff(self, character: Dict[str, Any]) -> bool:
        """Check if character has speed buff active."""
        buffs = character.get("status_effects", [])
        speed_buffs = ["increase_agi", "two_hand_quicken", "adrenaline_rush", "berserk"]
        
        return any(buff in buffs for buff in speed_buffs)
    
    def _get_escape_options(self, game_state: Dict[str, Any]) -> List[str]:
        """Get available escape options."""
        options = []
        
        inventory = game_state.get("inventory", [])
        character = game_state.get("character", {})
        skills = character.get("skills", {})
        
        # Check items
        for item in inventory:
            name = item.get("name", "").lower()
            if "fly wing" in name and item.get("amount", 0) > 0:
                options.append("fly_wing")
            elif "butterfly wing" in name and item.get("amount", 0) > 0:
                options.append("butterfly_wing")
        
        # Check skills
        if skills.get("AL_TELEPORT", {}).get("level", 0) > 0:
            options.append("teleport")
        if skills.get("TF_HIDING", {}).get("level", 0) > 0:
            options.append("hiding")
        if skills.get("TF_BACKSLIDING", {}).get("level", 0) > 0:
            options.append("backslide")
        
        return options or ["run"]
    
    def _find_blocking_positions(
        self,
        game_state: Dict[str, Any],
        char_pos: Dict[str, int],
        item_pos: Dict[str, int]
    ) -> List[Dict[str, int]]:
        """Find positions that can block enemy path."""
        # This would integrate with map data to find walls/obstacles
        # For now, return estimated blocking positions
        
        # Simple heuristic: positions between character and item
        if not char_pos or not item_pos:
            return []
        
        x1, y1 = char_pos.get("x", 0), char_pos.get("y", 0)
        x2, y2 = item_pos.get("x", 0), item_pos.get("y", 0)
        
        # Midpoint could be a blocking position
        mid_x = (x1 + x2) // 2
        mid_y = (y1 + y2) // 2
        
        return [{"x": mid_x, "y": mid_y}]
    
    def _find_nearest_enemy(
        self,
        monsters: List[Dict[str, Any]],
        position: Dict[str, int]
    ) -> Optional[Dict[str, Any]]:
        """Find nearest enemy to a position."""
        if not monsters or not position:
            return None
        
        import math
        
        def distance(m):
            pos = m.get("pos", {})
            if not pos:
                return 999
            dx = pos.get("x", 0) - position.get("x", 0)
            dy = pos.get("y", 0) - position.get("y", 0)
            return math.sqrt(dx**2 + dy**2)
        
        return min(monsters, key=distance, default=None)
    
    def _estimate_respawn_cost(self, level: int) -> int:
        """Estimate respawn cost based on level."""
        # Typical RO respawn cost: 1% of exp to next level or base zeny cost
        base_cost = 1000  # Base zeny
        level_multiplier = level * 100
        
        return base_cost + level_multiplier
    
    def _create_fallback_action(self, target_item: Dict[str, Any]) -> Dict[str, Any]:
        """Create fallback action for error cases."""
        return {
            "action": "loot_tactical",
            "params": {
                "tactic": "systematic_collection",
                "target_item": {
                    "binID": target_item.get("binID"),
                    "item_id": target_item.get("item_id"),
                    "item_name": target_item.get("item_name"),
                    "priority": target_item.get("priority_level")
                },
                "items_to_grab": [target_item.get("binID")],
                "accept_death": False,
                "strategy": "fallback",
                "movement": "direct_path"
            },
            "reasoning": "Fallback: Simple direct approach to loot"
        }
