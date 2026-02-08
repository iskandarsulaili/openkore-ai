"""
Adaptive Equipment Management System
Auto-swaps equipment based on enemy type, map, and combat situation
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from loguru import logger


class EquipmentManager:
    """
    Autonomous equipment management based on combat situation.
    Generates equipment switching commands for OpenKore.
    """
    
    # Element effectiveness matrix (attacker element vs defender element)
    ELEMENT_ADVANTAGE = {
        'neutral': {},
        'water': {'fire': 2.0, 'earth': 0.5},
        'earth': {'fire': 2.0, 'wind': 0.5},
        'fire': {'earth': 2.0, 'water': 0.5, 'wind': 2.0},
        'wind': {'water': 2.0, 'earth': 0.5},
        'poison': {'neutral': 1.25},
        'holy': {'shadow': 2.0, 'undead': 2.0},
        'shadow': {'holy': 2.0},
        'ghost': {'ghost': 2.0},
        'undead': {'holy': 0.5}
    }
    
    # Race/size/type specific equipment bonuses
    EQUIPMENT_MODIFIERS = {
        'race': ['demi_human', 'brute', 'plant', 'insect', 'fish', 'demon', 'undead', 'angel', 'dragon'],
        'size': ['small', 'medium', 'large'],
        'element': list(ELEMENT_ADVANTAGE.keys())
    }
    
    def __init__(self, user_intent_path: str, inventory_state: Optional[Dict] = None):
        """Initialize with user intent and current inventory"""
        self.user_intent_path = Path(user_intent_path)
        self.user_intent = self._load_user_intent()
        
        # Current equipment state
        self.current_equipment = {}
        self.inventory = inventory_state or {}
        
        # Map-specific equipment profiles
        self.map_profiles = {}
        
        # Performance tracking
        self.damage_taken_by_element = {}
        self.damage_dealt_by_weapon = {}
        
        logger.info("EquipmentManager initialized")
    
    def _load_user_intent(self) -> Dict[str, Any]:
        """Load user intent from JSON"""
        if not self.user_intent_path.exists():
            logger.warning(f"User intent file not found: {self.user_intent_path}")
            return {}
        
        with open(self.user_intent_path, 'r', encoding='utf-8-sig') as f:
            return json.load(f)
    
    def on_map_change(self, new_map: str, enemies: List[Dict]) -> Dict[str, Any]:
        """
        Called when entering a new map.
        Analyzes dominant enemy types and recommends equipment setup.
        """
        logger.info(f"Analyzing equipment for map: {new_map}")
        
        # Analyze enemy composition
        analysis = self._analyze_enemy_composition(enemies)
        
        # Get optimal equipment set
        equipment_set = self._get_optimal_equipment_set(analysis)
        
        # Generate equipment commands
        commands = self._generate_equipment_commands(equipment_set)
        
        # Store profile for this map
        self.map_profiles[new_map] = {
            'analysis': analysis,
            'equipment': equipment_set,
            'commands': commands
        }
        
        return {
            'map': new_map,
            'analysis': analysis,
            'recommended_equipment': equipment_set,
            'commands': commands,
            'reason': self._explain_equipment_choice(analysis, equipment_set)
        }
    
    def on_combat_start(self, enemy: Dict) -> Dict[str, Any]:
        """
        Called when engaging an enemy.
        May switch equipment for specific enemy matchups.
        """
        enemy_name = enemy.get('name', 'Unknown')
        enemy_element = enemy.get('element', 'neutral')
        enemy_race = enemy.get('race', 'unknown')
        enemy_size = enemy.get('size', 'medium')
        
        # Check if we need to switch equipment for this specific enemy
        optimal_weapon = self._get_optimal_weapon_for_enemy(enemy)
        optimal_armor = self._get_optimal_armor_for_enemy(enemy)
        
        commands = []
        
        # Only switch if significantly better
        if optimal_weapon and optimal_weapon != self.current_equipment.get('weapon'):
            commands.append(f"eq {optimal_weapon}")
            logger.info(f"Switching to {optimal_weapon} for {enemy_name}")
        
        if optimal_armor and optimal_armor != self.current_equipment.get('armor'):
            commands.append(f"eq {optimal_armor}")
            logger.info(f"Switching to {optimal_armor} for {enemy_name}")
        
        return {
            'enemy': enemy_name,
            'equipment_changes': len(commands),
            'commands': commands,
            'reason': f"Optimizing for {enemy_element} {enemy_race} {enemy_size}"
        }
    
    def on_taking_damage(self, damage_type: str, damage_amount: int, enemy: Dict) -> Dict[str, Any]:
        """
        Called when taking damage.
        May switch to defensive equipment if taking heavy damage.
        """
        enemy_element = enemy.get('element', 'neutral')
        
        # Track damage by element
        if enemy_element not in self.damage_taken_by_element:
            self.damage_taken_by_element[enemy_element] = []
        self.damage_taken_by_element[enemy_element].append(damage_amount)
        
        # Calculate average damage
        avg_damage = sum(self.damage_taken_by_element[enemy_element]) / len(self.damage_taken_by_element[enemy_element])
        
        commands = []
        
        # If taking heavy damage (>30% HP), switch to defensive gear
        if damage_amount > 0 and avg_damage > 0:  # Placeholder for HP percentage check
            defensive_armor = self._get_defensive_armor(enemy_element)
            
            if defensive_armor and defensive_armor != self.current_equipment.get('armor'):
                commands.append(f"eq {defensive_armor}")
                logger.warning(f"Switching to defensive armor due to heavy {enemy_element} damage")
        
        return {
            'damage_taken': damage_amount,
            'damage_type': damage_type,
            'element': enemy_element,
            'equipment_changes': len(commands),
            'commands': commands
        }
    
    def _analyze_enemy_composition(self, enemies: List[Dict]) -> Dict[str, Any]:
        """Analyze enemy types in current area"""
        if not enemies:
            return {
                'dominant_element': 'neutral',
                'dominant_race': 'unknown',
                'dominant_size': 'medium',
                'element_distribution': {},
                'total_enemies': 0
            }
        
        element_count = {}
        race_count = {}
        size_count = {}
        
        for enemy in enemies:
            # Count elements
            element = enemy.get('element', 'neutral')
            element_count[element] = element_count.get(element, 0) + 1
            
            # Count races
            race = enemy.get('race', 'unknown')
            race_count[race] = race_count.get(race, 0) + 1
            
            # Count sizes
            size = enemy.get('size', 'medium')
            size_count[size] = size_count.get(size, 0) + 1
        
        # Find dominant types
        dominant_element = max(element_count, key=element_count.get) if element_count else 'neutral'
        dominant_race = max(race_count, key=race_count.get) if race_count else 'unknown'
        dominant_size = max(size_count, key=size_count.get) if size_count else 'medium'
        
        return {
            'dominant_element': dominant_element,
            'dominant_race': dominant_race,
            'dominant_size': dominant_size,
            'element_distribution': element_count,
            'race_distribution': race_count,
            'size_distribution': size_count,
            'total_enemies': len(enemies)
        }
    
    def _get_optimal_equipment_set(self, analysis: Dict) -> Dict[str, str]:
        """
        Determine optimal equipment set based on enemy analysis.
        Returns dict with equipment slot recommendations.
        """
        dominant_element = analysis.get('dominant_element', 'neutral')
        dominant_race = analysis.get('dominant_race', 'unknown')
        dominant_size = analysis.get('dominant_size', 'medium')
        
        equipment_set = {
            'weapon': None,
            'armor': None,
            'shield': None,
            'accessory1': None,
            'accessory2': None
        }
        
        # Choose weapon based on enemy element (counter element)
        counter_element = self._get_counter_element(dominant_element)
        equipment_set['weapon'] = f"{counter_element}_weapon"  # Placeholder
        
        # Choose armor for resistance
        if dominant_element != 'neutral':
            equipment_set['armor'] = f"{dominant_element}_resistance_armor"
        else:
            equipment_set['armor'] = "high_def_armor"
        
        # Choose accessories for race/size bonuses
        if dominant_race in self.EQUIPMENT_MODIFIERS['race']:
            equipment_set['accessory1'] = f"{dominant_race}_damage_accessory"
        
        return equipment_set
    
    def _get_counter_element(self, enemy_element: str) -> str:
        """Get the element that is strong against enemy element"""
        # Simplified counter-element logic
        counter_map = {
            'water': 'wind',
            'wind': 'earth',
            'earth': 'fire',
            'fire': 'water',
            'holy': 'shadow',
            'shadow': 'holy',
            'undead': 'holy',
            'neutral': 'neutral'
        }
        
        return counter_map.get(enemy_element, 'neutral')
    
    def _get_optimal_weapon_for_enemy(self, enemy: Dict) -> Optional[str]:
        """Get best weapon for specific enemy"""
        enemy_element = enemy.get('element', 'neutral')
        enemy_race = enemy.get('race', 'unknown')
        
        # Priority 1: Element advantage
        if enemy_element in ['undead', 'shadow']:
            return 'holy_weapon'
        
        # Priority 2: Race-specific weapons
        if enemy_race == 'undead':
            return 'holy_weapon'
        elif enemy_race == 'demi_human':
            return 'demi_human_weapon'
        
        # Default: best general weapon
        return None
    
    def _get_optimal_armor_for_enemy(self, enemy: Dict) -> Optional[str]:
        """Get best armor for specific enemy"""
        enemy_element = enemy.get('element', 'neutral')
        
        # Choose armor with resistance to enemy's element
        if enemy_element in ['fire', 'water', 'wind', 'earth']:
            return f"{enemy_element}_resistance_armor"
        
        return None
    
    def _get_defensive_armor(self, element: str) -> Optional[str]:
        """Get defensive armor for specific element damage"""
        resistance_armor_map = {
            'fire': 'fire_resistance_armor',
            'water': 'water_resistance_armor',
            'wind': 'wind_resistance_armor',
            'earth': 'earth_resistance_armor',
            'holy': 'shadow_resistance_armor',
            'shadow': 'holy_resistance_armor',
            'neutral': 'high_def_armor'
        }
        
        return resistance_armor_map.get(element, 'high_def_armor')
    
    def _generate_equipment_commands(self, equipment_set: Dict[str, str]) -> List[str]:
        """Generate OpenKore commands to equip items"""
        commands = []
        
        for slot, item in equipment_set.items():
            if item:
                commands.append(f"eq {item}")
        
        return commands
    
    def _explain_equipment_choice(self, analysis: Dict, equipment_set: Dict) -> str:
        """Generate human-readable explanation"""
        dominant_element = analysis.get('dominant_element', 'neutral')
        dominant_race = analysis.get('dominant_race', 'unknown')
        total_enemies = analysis.get('total_enemies', 0)
        
        explanation = f"Map has {total_enemies} enemies\n"
        explanation += f"Dominant: {dominant_element} element, {dominant_race} race\n"
        explanation += f"Recommended setup:\n"
        
        for slot, item in equipment_set.items():
            if item:
                explanation += f"  - {slot}: {item}\n"
        
        return explanation
    
    def get_equipment_for_situation(self, situation: str) -> Dict[str, Any]:
        """
        Get equipment recommendations for specific situations.
        Situations: 'boss', 'mvp', 'farming', 'pvp', 'defense'
        """
        equipment_profiles = {
            'boss': {
                'weapon': 'high_damage_weapon',
                'armor': 'high_def_armor',
                'shield': 'damage_reduction_shield',
                'accessory1': 'boss_damage_accessory',
                'accessory2': 'hp_boost_accessory'
            },
            'mvp': {
                'weapon': 'maximum_damage_weapon',
                'armor': 'elemental_resistance_armor',
                'shield': 'reflect_shield',
                'accessory1': 'mvp_damage_accessory',
                'accessory2': 'survival_accessory'
            },
            'farming': {
                'weapon': 'aoe_weapon',
                'armor': 'light_armor',
                'shield': 'drop_rate_shield',
                'accessory1': 'drop_rate_accessory',
                'accessory2': 'exp_boost_accessory'
            },
            'pvp': {
                'weapon': 'burst_damage_weapon',
                'armor': 'demi_human_resistance',
                'shield': 'reflect_shield',
                'accessory1': 'pvp_accessory',
                'accessory2': 'anti_stun_accessory'
            },
            'defense': {
                'weapon': 'defensive_weapon',
                'armor': 'maximum_def_armor',
                'shield': 'high_def_shield',
                'accessory1': 'hp_accessory',
                'accessory2': 'damage_reduction_accessory'
            }
        }
        
        profile = equipment_profiles.get(situation, equipment_profiles['farming'])
        
        return {
            'situation': situation,
            'equipment': profile,
            'commands': self._generate_equipment_commands(profile)
        }
    
    def update_inventory(self, inventory: Dict[str, Any]):
        """Update current inventory state"""
        self.inventory = inventory
        logger.debug(f"Inventory updated: {len(inventory)} items")
    
    def update_current_equipment(self, equipment: Dict[str, str]):
        """Update currently equipped items"""
        self.current_equipment = equipment
        logger.debug(f"Current equipment updated: {equipment}")
    
    def export_equipment_config(self, output_path: str) -> bool:
        """
        Export equipment switching rules to config file.
        Can be used to create equipAuto.txt for OpenKore.
        """
        try:
            config_lines = [
                "# Auto-generated equipment switching rules",
                "# Format: equipAuto <item> {conditions}",
                ""
            ]
            
            # Add map-based rules
            for map_name, profile in self.map_profiles.items():
                equipment_set = profile.get('equipment', {})
                config_lines.append(f"# Rules for {map_name}")
                
                for slot, item in equipment_set.items():
                    if item:
                        config_lines.append(f"equipAuto {item} {{")
                        config_lines.append(f"    map {map_name}")
                        config_lines.append(f"}}")
                        config_lines.append("")
            
            output_path_obj = Path(output_path)
            with open(output_path_obj, 'w', encoding='utf-8') as f:
                f.write('\n'.join(config_lines))
            
            logger.success(f"Exported equipment config to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export equipment config: {e}")
            return False
