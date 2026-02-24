"""
Refinement Safety Net
Prevents catastrophic losses from failed refinements
"""

from typing import Dict, Any
from loguru import logger
import threading


class RefinementSafetyNet:
    """
    Safety checks for refinement operations
    Prevents expensive mistakes
    """
    
    def __init__(self):
        """Initialize safety net"""
        self._lock = threading.RLock()
        self.value_threshold = 100000  # 100k zeny
        self.max_safe_refine = 7
        
        logger.info("RefinementSafetyNet initialized")
    
    def check_refinement_safety(
        self,
        item_name: str,
        target_refine: int,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Check if refinement is safe
        
        Args:
            item_name: Item to refine
            target_refine: Target refine level
            game_state: Current game state
            
        Returns:
            Safety check result
        """
        with self._lock:
            # Check refine level
            if target_refine > self.max_safe_refine:
                return {
                    'safe': False,
                    'reason': f'Refine level {target_refine} exceeds safe limit {self.max_safe_refine}'
                }
            
            # Check item value
            item_value = self._get_item_value(item_name, game_state)
            if item_value > self.value_threshold:
                return {
                    'safe': False,
                    'reason': f'Item value {item_value}z exceeds threshold {self.value_threshold}z',
                    'requires_confirmation': True
                }
            
            # Check zeny availability
            character_zeny = game_state.get('character', {}).get('zeny', 0)
            if character_zeny < 10000:
                return {
                    'safe': False,
                    'reason': 'Insufficient zeny for safe refinement'
                }
            
            return {
                'safe': True,
                'item_value': item_value,
                'refine_cost_estimate': target_refine * 2000
            }
    
    def check_card_slotting_safety(
        self,
        equipment: str,
        card: str,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Check if card slotting is safe"""
        with self._lock:
            card_value = self._get_item_value(card, game_state)
            equipment_value = self._get_item_value(equipment, game_state)
            
            total_value = card_value + equipment_value
            
            if total_value > self.value_threshold:
                return {
                    'safe': False,
                    'reason': f'Combined value {total_value}z too high',
                    'requires_confirmation': True
                }
            
            return {
                'safe': True,
                'total_value': total_value
            }
    
    def _get_item_value(self, item_name: str, game_state: Dict[str, Any]) -> int:
        """Get item value from game state"""
        inventory = game_state.get('inventory', {}).get('items', [])
        
        for item in inventory:
            if item.get('name') == item_name:
                return item.get('value', 0)
        
        return 0
