"""
Auto Equip Manager
Automatically equips best available gear based on character progression
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import threading


class AutoEquipManager:
    """
    Manages automatic equipment selection based on character level and job
    Progressive gear upgrades as character advances
    """
    
    def __init__(self, data_dir: Path, openkore_client):
        """
        Initialize auto equip manager
        
        Args:
            data_dir: Directory containing equipment_loadouts.json
            openkore_client: OpenKore HTTP client (REST API)
        """
        self.data_dir = data_dir
        self.openkore = openkore_client
        self.equipment_rules: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._load_equipment_rules()
        
        logger.info("AutoEquipManager initialized")
    
    def _load_equipment_rules(self):
        """Load equipment rules from configuration"""
        try:
            rules_file = self.data_dir / "equipment_loadouts.json"
            
            if rules_file.exists():
                with open(rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.equipment_rules = data.get('loadouts', {})
                logger.success(f"Loaded equipment rules for {len(self.equipment_rules)} job classes")
            else:
                logger.warning("Equipment loadouts file not found, using defaults")
                self._create_default_rules()
                
        except Exception as e:
            logger.error(f"Failed to load equipment rules: {e}")
            self._create_default_rules()
    
    def _create_default_rules(self):
        """Create default equipment rules"""
        self.equipment_rules = {
            "default": {
                "weapon_priority": ["two_handed", "one_handed", "dagger"],
                "armor_priority": ["defense", "mdef", "element_resist"],
                "accessory_priority": ["stats", "special_effects"]
            }
        }
    
    async def auto_equip_best_gear(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically equip best available gear
        
        Args:
            game_state: Current game state with character and inventory
            
        Returns:
            Dictionary with equipment changes made
        """
        with self._lock:
            try:
                character = game_state.get('character', {})
                inventory = game_state.get('inventory', {}).get('items', [])
                
                job_class = character.get('job_class', 'Novice')
                level = character.get('level', 1)
                
                logger.info(f"Auto-equipping for {job_class} level {level}")
                
                # Get current equipment
                current_equipment = character.get('equipment', {})
                
                # Find best equipment for each slot
                equipment_changes = {}
                
                # Weapon slot
                best_weapon = self._find_best_weapon(inventory, job_class, level)
                if best_weapon and best_weapon != current_equipment.get('weapon'):
                    equipment_changes['weapon'] = best_weapon
                
                # Armor slot
                best_armor = self._find_best_armor(inventory, job_class, level)
                if best_armor and best_armor != current_equipment.get('armor'):
                    equipment_changes['armor'] = best_armor
                
                # Shield slot
                best_shield = self._find_best_shield(inventory, job_class, level)
                if best_shield and best_shield != current_equipment.get('shield'):
                    equipment_changes['shield'] = best_shield
                
                # Accessory slots
                best_accessories = self._find_best_accessories(inventory, job_class, level)
                for slot, accessory in best_accessories.items():
                    if accessory != current_equipment.get(slot):
                        equipment_changes[slot] = accessory
                
                # Execute equipment changes
                if equipment_changes:
                    logger.info(f"Equipping {len(equipment_changes)} items")
                    await self._execute_equipment_changes(equipment_changes)
                    
                    return {
                        'success': True,
                        'changes_made': len(equipment_changes),
                        'equipment': equipment_changes
                    }
                else:
                    logger.debug("No better equipment found")
                    return {
                        'success': True,
                        'changes_made': 0,
                        'message': 'Already wearing optimal gear'
                    }
                
            except Exception as e:
                logger.error(f"Auto-equip error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def _find_best_weapon(self, inventory: List[Dict], job_class: str, level: int) -> Optional[str]:
        """Find best weapon in inventory"""
        weapons = [item for item in inventory if item.get('type') == 'weapon']
        
        if not weapons:
            return None
        
        # Filter by job class compatibility
        compatible_weapons = [
            w for w in weapons
            if self._is_compatible_with_job(w, job_class)
        ]
        
        if not compatible_weapons:
            return None
        
        # Score weapons
        scored_weapons = [
            (weapon, self._score_weapon(weapon, job_class, level))
            for weapon in compatible_weapons
        ]
        
        # Return highest scoring weapon
        best = max(scored_weapons, key=lambda x: x[1])
        return best[0].get('name')
    
    def _score_weapon(self, weapon: Dict, job_class: str, level: int) -> float:
        """Calculate weapon score based on stats and job compatibility"""
        score = 0.0
        
        # Base attack
        score += weapon.get('attack', 0) * 2
        
        # Level requirement (prefer closer to character level)
        req_level = weapon.get('required_level', 1)
        if req_level <= level:
            score += (100 - abs(level - req_level))
        
        # Job-specific bonuses
        if job_class.lower() in str(weapon.get('description', '')).lower():
            score += 50
        
        # Slots (for cards)
        score += weapon.get('slots', 0) * 10
        
        # Refinement
        score += weapon.get('refine', 0) * 5
        
        return score
    
    def _find_best_armor(self, inventory: List[Dict], job_class: str, level: int) -> Optional[str]:
        """Find best armor in inventory"""
        armors = [item for item in inventory if item.get('type') == 'armor']
        
        if not armors:
            return None
        
        compatible_armors = [
            a for a in armors
            if self._is_compatible_with_job(a, job_class)
        ]
        
        if not compatible_armors:
            return None
        
        # Score armors by defense
        best = max(compatible_armors, key=lambda x: (
            x.get('defense', 0) * 2 +
            x.get('mdef', 0) +
            x.get('slots', 0) * 5
        ))
        
        return best.get('name')
    
    def _find_best_shield(self, inventory: List[Dict], job_class: str, level: int) -> Optional[str]:
        """Find best shield in inventory"""
        shields = [item for item in inventory if item.get('type') == 'shield']
        
        if not shields:
            return None
        
        compatible = [s for s in shields if self._is_compatible_with_job(s, job_class)]
        
        if not compatible:
            return None
        
        best = max(compatible, key=lambda x: x.get('defense', 0))
        return best.get('name')
    
    def _find_best_accessories(self, inventory: List[Dict], job_class: str, level: int) -> Dict[str, str]:
        """Find best accessories in inventory"""
        accessories = [item for item in inventory if item.get('type') == 'accessory']
        
        if not accessories:
            return {}
        
        compatible = [a for a in accessories if self._is_compatible_with_job(a, job_class)]
        
        if not compatible:
            return {}
        
        # Sort by usefulness
        sorted_accessories = sorted(
            compatible,
            key=lambda x: (
                sum(x.get('stats', {}).values()) +
                x.get('special_effect_value', 0)
            ),
            reverse=True
        )
        
        # Take top 2 for accessory slots
        result = {}
        if len(sorted_accessories) >= 1:
            result['accessory_1'] = sorted_accessories[0].get('name')
        if len(sorted_accessories) >= 2:
            result['accessory_2'] = sorted_accessories[1].get('name')
        
        return result
    
    def _is_compatible_with_job(self, item: Dict, job_class: str) -> bool:
        """Check if item is compatible with job class"""
        # Check job restrictions
        allowed_jobs = item.get('allowed_jobs', [])
        
        if not allowed_jobs:
            return True  # No restrictions
        
        return job_class in allowed_jobs or 'All' in allowed_jobs
    
    async def _execute_equipment_changes(self, changes: Dict[str, str]) -> bool:
        """
        Execute equipment changes via OpenKore
        
        Args:
            changes: Dictionary of slot -> item_name mappings
            
        Returns:
            True if all changes executed successfully
        """
        try:
            for slot, item_name in changes.items():
                command = f"eq {item_name}"
                await self.openkore.send_command(command)
                await asyncio.sleep(0.5)  # Delay between equips
            
            logger.success(f"Equipped {len(changes)} items")
            return True
            
        except Exception as e:
            logger.error(f"Equipment change execution error: {e}")
            return False
    
    def get_equipment_recommendations(
        self,
        game_state: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Get equipment recommendations without equipping
        
        Args:
            game_state: Current game state
            
        Returns:
            List of equipment recommendations
        """
        with self._lock:
            character = game_state.get('character', {})
            inventory = game_state.get('inventory', {}).get('items', [])
            current_equipment = character.get('equipment', {})
            
            recommendations = []
            
            # Check each slot
            slots = ['weapon', 'armor', 'shield', 'accessory_1', 'accessory_2']
            
            for slot in slots:
                current = current_equipment.get(slot)
                
                # Find better options
                better_options = self._find_better_options(
                    slot,
                    current,
                    inventory,
                    character
                )
                
                if better_options:
                    recommendations.append({
                        'slot': slot,
                        'current': current,
                        'recommended': better_options[0],
                        'improvement': better_options[0].get('score', 0)
                    })
            
            return recommendations
    
    def _find_better_options(
        self,
        slot: str,
        current: Optional[str],
        inventory: List[Dict],
        character: Dict
    ) -> List[Dict]:
        """Find better equipment options for a slot"""
        # Implementation depends on slot type
        # Returns list of items that are better than current
        return []
