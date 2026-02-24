"""
Resource Prioritizer
Prioritizes resource gathering based on current needs
"""

import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from loguru import logger
import threading


class ResourcePrioritizer:
    """
    Prioritizes which resources to gather based on needs
    - Consumable restocking
    - Material collection for crafting
    - Zeny farming
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize resource prioritizer
        
        Args:
            data_dir: Directory containing resources.json
        """
        self.data_dir = data_dir
        self.resource_needs: Dict[str, int] = {}
        self.resource_sources: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._load_resource_data()
        
        logger.info("ResourcePrioritizer initialized")
    
    def _load_resource_data(self):
        """Load resource data"""
        try:
            resource_file = self.data_dir / "resources.json"
            
            if resource_file.exists():
                with open(resource_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.resource_sources = data.get('sources', {})
                logger.success("Loaded resource data")
            else:
                logger.warning("Resource file not found, using defaults")
                self._create_default_resources()
                
        except Exception as e:
            logger.error(f"Failed to load resource data: {e}")
            self._create_default_resources()
    
    def _create_default_resources(self):
        """Create default resource sources"""
        self.resource_sources = {
            "healing_potions": {
                "source_type": "purchase",
                "locations": ["Prontera Item Shop", "Geffen Item Shop"],
                "cost_per_unit": 500
            },
            "blue_potions": {
                "source_type": "purchase",
                "locations": ["Magic Shop"],
                "cost_per_unit": 5000
            }
        }
    
    def analyze_resource_needs(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze what resources are needed
        
        Args:
            game_state: Current game state
            
        Returns:
            Dictionary of resource needs with priorities
        """
        with self._lock:
            needs = {}
            
            inventory = game_state.get('inventory', {}).get('items', [])
            character = game_state.get('character', {})
            
            # Check consumable levels
            healing_items = self._count_items(inventory, ['White Potion', 'Yellow Potion'])
            if healing_items < 50:
                needs['healing_potions'] = {
                    'current': healing_items,
                    'target': 100,
                    'priority': 'high' if healing_items < 20 else 'medium'
                }
            
            blue_potions = self._count_items(inventory, ['Blue Potion'])
            if blue_potions < 30 and character.get('job_class') in ['Mage', 'Wizard', 'Sage', 'Acolyte', 'Priest']:
                needs['blue_potions'] = {
                    'current': blue_potions,
                    'target': 50,
                    'priority': 'medium'
                }
            
            # Check fly wings
            fly_wings = self._count_items(inventory, ['Fly Wing'])
            if fly_wings < 100:
                needs['fly_wings'] = {
                    'current': fly_wings,
                    'target': 200,
                    'priority': 'medium'
                }
            
            return needs
    
    def _count_items(self, inventory: List[Dict], item_names: List[str]) -> int:
        """Count total amount of specified items"""
        total = 0
        for item in inventory:
            if item.get('name') in item_names:
                total += item.get('amount', 0)
        return total
    
    def get_optimal_gathering_plan(self, needs: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create optimal plan for gathering needed resources
        
        Args:
            needs: Dictionary of resource needs
            
        Returns:
            Gathering plan with route and actions
        """
        with self._lock:
            # Sort needs by priority
            sorted_needs = sorted(
                needs.items(),
                key=lambda x: {'high': 3, 'medium': 2, 'low': 1}.get(x[1].get('priority', 'low'), 0),
                reverse=True
            )
            
            plan = {
                'actions': [],
                'estimated_cost': 0,
                'estimated_time_minutes': 0
            }
            
            for resource_name, need_info in sorted_needs:
                source = self.resource_sources.get(resource_name, {})
                source_type = source.get('source_type')
                
                quantity_needed = need_info['target'] - need_info['current']
                
                if source_type == 'purchase':
                    plan['actions'].append({
                        'type': 'purchase',
                        'resource': resource_name,
                        'quantity': quantity_needed,
                        'location': source.get('locations', [])[0] if source.get('locations') else 'Unknown',
                        'cost': quantity_needed * source.get('cost_per_unit', 0)
                    })
                    plan['estimated_cost'] += quantity_needed * source.get('cost_per_unit', 0)
                    plan['estimated_time_minutes'] += 5
                
                elif source_type == 'farm':
                    plan['actions'].append({
                        'type': 'farm',
                        'resource': resource_name,
                        'quantity': quantity_needed,
                        'location': source.get('farming_location'),
                        'monster': source.get('monster')
                    })
                    plan['estimated_time_minutes'] += 15
            
            return plan
