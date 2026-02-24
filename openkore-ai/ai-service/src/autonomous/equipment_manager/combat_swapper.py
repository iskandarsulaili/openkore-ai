"""
Combat Equipment Swapper
Dynamic equipment switching during combat based on opponent analysis
Element/Size/Race advantage optimization (<1s swap time)
"""

import asyncio
from typing import Dict, Optional, Any, List
from loguru import logger
import threading
from datetime import datetime


class CombatEquipmentSwapper:
    """
    Dynamically swaps equipment during combat for advantage
    - Element advantage (Fire weapon vs Earth enemy)
    - Size advantage (size-specific cards)
    - Race advantage (race-specific damage)
    """
    
    def __init__(self, openkore_client):
        """
        Initialize combat equipment swapper
        
        Args:
            openkore_client: OpenKore HTTP client (REST API)
        """
        self.openkore = openkore_client
        self._lock = threading.RLock()
        self.combat_loadouts: Dict[str, Dict] = {}
        self.swap_history: List[Dict] = []
        self.current_combat_loadout: Optional[str] = None
        self.original_equipment: Optional[Dict] = None
        
        # Element advantage matrix
        self.element_advantages = {
            'Fire': ['Earth', 'Undead', 'Plant'],
            'Water': ['Fire'],
            'Wind': ['Water'],
            'Earth': ['Wind', 'Fire'],
            'Holy': ['Undead', 'Shadow'],
            'Shadow': ['Holy'],
            'Ghost': ['Ghost'],
            'Poison': ['Plant']
        }
        
        logger.info("CombatEquipmentSwapper initialized")
    
    async def analyze_and_swap(
        self,
        opponent: Dict[str, Any],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Analyze opponent and swap equipment for advantage
        
        Args:
            opponent: Opponent/monster information
            game_state: Current game state
            
        Returns:
            Dictionary with swap result
        """
        with self._lock:
            try:
                start_time = datetime.now()
                
                # Extract opponent characteristics
                element = opponent.get('element', 'Neutral')
                size = opponent.get('size', 'Medium')
                race = opponent.get('race', 'Formless')
                
                logger.info(f"Analyzing opponent: Element={element}, Size={size}, Race={race}")
                
                # Save original equipment if not saved
                if not self.original_equipment:
                    self.original_equipment = game_state.get('character', {}).get('equipment', {})
                
                # Find optimal loadout
                optimal_loadout = self._find_optimal_loadout(element, size, race, game_state)
                
                if not optimal_loadout:
                    return {
                        'success': False,
                        'reason': 'No better loadout available'
                    }
                
                # Execute fast swap
                swap_success = await self._execute_fast_swap(optimal_loadout)
                
                swap_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if swap_success:
                    logger.success(f"Combat equipment swapped in {swap_time:.0f}ms")
                    
                    self.current_combat_loadout = optimal_loadout['name']
                    
                    # Record swap
                    self.swap_history.append({
                        'timestamp': datetime.now(),
                        'opponent_element': element,
                        'loadout': optimal_loadout['name'],
                        'swap_time_ms': swap_time
                    })
                    
                    return {
                        'success': True,
                        'loadout': optimal_loadout['name'],
                        'swap_time_ms': swap_time,
                        'advantages': optimal_loadout['advantages']
                    }
                else:
                    return {
                        'success': False,
                        'reason': 'Swap execution failed'
                    }
                
            except Exception as e:
                logger.error(f"Combat swap error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def _find_optimal_loadout(
        self,
        element: str,
        size: str,
        race: str,
        game_state: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        Find optimal equipment loadout for opponent
        
        Args:
            element: Opponent element
            size: Opponent size
            race: Opponent race
            game_state: Current game state
            
        Returns:
            Optimal loadout configuration
        """
        inventory = game_state.get('inventory', {}).get('items', [])
        
        # Find weapons with element advantage
        advantageous_weapons = self._find_advantageous_weapons(element, inventory)
        
        if not advantageous_weapons:
            return None
        
        # Build loadout
        loadout = {
            'name': f'combat_{element}_{size}_{race}',
            'weapon': advantageous_weapons[0],
            'advantages': []
        }
        
        # Check for element advantage
        if self._has_element_advantage(advantageous_weapons[0], element):
            loadout['advantages'].append('element')
        
        # Add size-specific equipment if available
        size_equipment = self._find_size_equipment(size, inventory)
        if size_equipment:
            loadout.update(size_equipment)
            loadout['advantages'].append('size')
        
        # Add race-specific equipment if available
        race_equipment = self._find_race_equipment(race, inventory)
        if race_equipment:
            loadout.update(race_equipment)
            loadout['advantages'].append('race')
        
        return loadout if loadout['advantages'] else None
    
    def _find_advantageous_weapons(self, opponent_element: str, inventory: List[Dict]) -> List[str]:
        """Find weapons with element advantage against opponent"""
        weapons = [item for item in inventory if item.get('type') == 'weapon']
        
        advantageous = []
        
        for weapon in weapons:
            weapon_element = weapon.get('element', 'Neutral')
            
            # Check if weapon element has advantage
            if opponent_element in self.element_advantages.get(weapon_element, []):
                advantageous.append(weapon.get('name'))
        
        return advantageous
    
    def _has_element_advantage(self, weapon_name: str, opponent_element: str) -> bool:
        """Check if weapon has element advantage"""
        # This would need to look up weapon element from database
        # Simplified for now
        return True
    
    def _find_size_equipment(self, size: str, inventory: List[Dict]) -> Dict[str, str]:
        """Find equipment with size-specific bonuses"""
        # Look for cards/equipment with size bonuses
        # Size: Small, Medium, Large
        
        size_bonuses = {}
        
        for item in inventory:
            if f'Size {size}' in item.get('description', ''):
                slot_type = item.get('equip_slot', 'accessory')
                size_bonuses[slot_type] = item.get('name')
        
        return size_bonuses
    
    def _find_race_equipment(self, race: str, inventory: List[Dict]) -> Dict[str, str]:
        """Find equipment with race-specific bonuses"""
        # Look for cards/equipment with race bonuses
        # Race: Demon, Undead, Human, etc.
        
        race_bonuses = {}
        
        for item in inventory:
            if f'Race {race}' in item.get('description', '') or \
               f'{race} ' in item.get('description', ''):
                slot_type = item.get('equip_slot', 'accessory')
                race_bonuses[slot_type] = item.get('name')
        
        return race_bonuses
    
    async def _execute_fast_swap(self, loadout: Dict) -> bool:
        """
        Execute fast equipment swap (<1s)
        
        Args:
            loadout: Loadout configuration
            
        Returns:
            True if swap successful
        """
        try:
            # Batch equipment commands for speed
            commands = []
            
            for slot, item_name in loadout.items():
                if slot not in ['name', 'advantages']:
                    commands.append(f"eq {item_name}")
            
            # Execute all commands rapidly
            for cmd in commands:
                await self.openkore.send_command(cmd)
                await asyncio.sleep(0.1)  # Minimal delay
            
            return True
            
        except Exception as e:
            logger.error(f"Fast swap execution error: {e}")
            return False
    
    async def revert_to_original(self) -> bool:
        """
        Revert to original equipment after combat
        
        Returns:
            True if revert successful
        """
        with self._lock:
            if not self.original_equipment:
                logger.warning("No original equipment saved")
                return False
            
            try:
                logger.info("Reverting to original equipment")
                
                for slot, item_name in self.original_equipment.items():
                    if item_name:
                        await self.openkore.send_command(f"eq {item_name}")
                        await asyncio.sleep(0.1)
                
                self.current_combat_loadout = None
                self.original_equipment = None
                
                logger.success("Reverted to original equipment")
                return True
                
            except Exception as e:
                logger.error(f"Revert error: {e}")
                return False
    
    def get_swap_statistics(self) -> Dict:
        """Get combat swap statistics"""
        with self._lock:
            if not self.swap_history:
                return {
                    'total_swaps': 0,
                    'average_swap_time_ms': 0
                }
            
            avg_time = sum(s['swap_time_ms'] for s in self.swap_history) / len(self.swap_history)
            
            return {
                'total_swaps': len(self.swap_history),
                'average_swap_time_ms': round(avg_time, 2),
                'fastest_swap_ms': min(s['swap_time_ms'] for s in self.swap_history),
                'recent_swaps': self.swap_history[-10:]
            }
