"""
Inventory Organizer
Automatically organizes inventory and manages storage
"""

import asyncio
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import threading


class InventoryOrganizer:
    """
    Manages inventory organization and storage operations
    - Auto-store valuable items when inventory full
    - Organize by category
    - Weight management
    - Reserve slots for critical items
    """
    
    def __init__(self, data_dir: Path, openkore_client):
        """
        Initialize inventory organizer
        
        Args:
            data_dir: Directory containing inventory_rules.json
            openkore_client: OpenKore IPC client
        """
        self.data_dir = data_dir
        self.openkore = openkore_client
        self.inventory_rules: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self.organization_history: List[Dict] = []
        self._load_inventory_rules()
        
        logger.info("InventoryOrganizer initialized")
    
    def _load_inventory_rules(self):
        """Load inventory management rules"""
        try:
            rules_file = self.data_dir / "inventory_rules.json"
            
            if rules_file.exists():
                with open(rules_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.inventory_rules = data.get('rules', {})
                logger.success(f"Loaded inventory rules")
            else:
                logger.warning("Inventory rules file not found, using defaults")
                self._create_default_rules()
                
        except Exception as e:
            logger.error(f"Failed to load inventory rules: {e}")
            self._create_default_rules()
    
    def _create_default_rules(self):
        """Create default inventory rules"""
        self.inventory_rules = {
            "storage_priority": ["equipment", "cards", "rare_items", "consumables"],
            "keep_in_inventory": ["healing_items", "teleport_items", "return_items"],
            "auto_sell": ["junk_items", "low_value_drops"],
            "weight_threshold": 80,
            "slot_threshold": 90,
            "reserved_slots": 10
        }
    
    async def organize_inventory(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Organize inventory and store items as needed
        
        Args:
            game_state: Current game state
            
        Returns:
            Dictionary with organization result
        """
        with self._lock:
            try:
                inventory = game_state.get('inventory', {})
                items = inventory.get('items', [])
                usage_percent = inventory.get('usage_percent', 0)
                weight_percent = game_state.get('character', {}).get('weight_percent', 0)
                
                logger.info(f"Organizing inventory (Usage: {usage_percent}%, Weight: {weight_percent}%)")
                
                actions_taken = []
                
                # Check if organization needed
                if usage_percent < 70 and weight_percent < 70:
                    return {
                        'success': True,
                        'actions': [],
                        'message': 'Inventory within acceptable limits'
                    }
                
                # Categorize items
                categorized = self._categorize_items(items)
                
                # Determine what to store
                items_to_store = self._select_items_for_storage(categorized, usage_percent, weight_percent)
                
                if items_to_store:
                    # Navigate to storage
                    logger.info(f"Storing {len(items_to_store)} items")
                    storage_success = await self._store_items(items_to_store)
                    
                    if storage_success:
                        actions_taken.append({
                            'action': 'storage',
                            'items_stored': len(items_to_store)
                        })
                
                # Record organization
                self.organization_history.append({
                    'timestamp': datetime.now(),
                    'usage_before': usage_percent,
                    'weight_before': weight_percent,
                    'actions': actions_taken
                })
                
                return {
                    'success': True,
                    'actions': actions_taken,
                    'items_stored': len(items_to_store)
                }
                
            except Exception as e:
                logger.error(f"Inventory organization error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def _categorize_items(self, items: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Categorize items by type
        
        Args:
            items: List of inventory items
            
        Returns:
            Dictionary of categorized items
        """
        categories = {
            'equipment': [],
            'cards': [],
            'consumables': [],
            'materials': [],
            'quest_items': [],
            'valuable': [],
            'junk': []
        }
        
        for item in items:
            item_type = item.get('type', 'unknown')
            item_value = item.get('value', 0)
            item_name = item.get('name', '')
            
            # Categorize based on type and value
            if item_type in ['weapon', 'armor', 'shield', 'accessory']:
                categories['equipment'].append(item)
            elif 'Card' in item_name:
                categories['cards'].append(item)
            elif item_type in ['potion', 'food']:
                categories['consumables'].append(item)
            elif item_type == 'quest':
                categories['quest_items'].append(item)
            elif item_value > 10000:
                categories['valuable'].append(item)
            elif item_value < 100:
                categories['junk'].append(item)
            else:
                categories['materials'].append(item)
        
        return categories
    
    def _select_items_for_storage(
        self,
        categorized: Dict[str, List[Dict]],
        usage_percent: float,
        weight_percent: float
    ) -> List[str]:
        """
        Select which items to store
        
        Args:
            categorized: Categorized items
            usage_percent: Inventory usage percentage
            weight_percent: Weight percentage
            
        Returns:
            List of item names to store
        """
        to_store = []
        storage_priority = self.inventory_rules.get('storage_priority', [])
        
        # Store based on priority
        for category in storage_priority:
            if category in categorized:
                for item in categorized[category]:
                    # Don't store equipped items
                    if not item.get('equipped', False):
                        to_store.append(item.get('name'))
        
        # If weight is issue, prioritize heavy items
        if weight_percent > 70:
            heavy_items = sorted(
                [item for cat in categorized.values() for item in cat],
                key=lambda x: x.get('weight', 0),
                reverse=True
            )
            for item in heavy_items[:10]:
                if item.get('name') not in to_store and not item.get('equipped'):
                    to_store.append(item.get('name'))
        
        return to_store
    
    async def _store_items(self, item_names: List[str]) -> bool:
        """
        Store items in Kafra storage
        
        Args:
            item_names: List of item names to store
            
        Returns:
            True if storage successful
        """
        try:
            # Navigate to Kafra
            await self.openkore.send_command("talknpc kafra")
            await asyncio.sleep(2)
            
            # Select storage option
            await self.openkore.send_command("talk resp 0")
            await asyncio.sleep(1)
            
            # Store each item
            for item_name in item_names:
                await self.openkore.send_command(f"storage add {item_name}")
                await asyncio.sleep(0.3)
            
            # Close storage
            await self.openkore.send_command("storage close")
            
            logger.success(f"Stored {len(item_names)} items")
            return True
            
        except Exception as e:
            logger.error(f"Storage error: {e}")
            return False
    
    async def retrieve_items(
        self,
        item_names: List[str],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Retrieve items from storage
        
        Args:
            item_names: List of items to retrieve
            game_state: Current game state
            
        Returns:
            Retrieval result
        """
        with self._lock:
            try:
                logger.info(f"Retrieving {len(item_names)} items from storage")
                
                # Navigate to Kafra
                await self.openkore.send_command("talknpc kafra")
                await asyncio.sleep(2)
                
                # Select storage option
                await self.openkore.send_command("talk resp 0")
                await asyncio.sleep(1)
                
                # Retrieve each item
                retrieved = []
                for item_name in item_names:
                    await self.openkore.send_command(f"storage get {item_name}")
                    await asyncio.sleep(0.3)
                    retrieved.append(item_name)
                
                # Close storage
                await self.openkore.send_command("storage close")
                
                return {
                    'success': True,
                    'items_retrieved': len(retrieved),
                    'items': retrieved
                }
                
            except Exception as e:
                logger.error(f"Retrieval error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def get_organization_statistics(self) -> Dict:
        """Get inventory organization statistics"""
        with self._lock:
            if not self.organization_history:
                return {
                    'total_organizations': 0
                }
            
            total_stored = sum(
                sum(a.get('items_stored', 0) for a in record['actions'])
                for record in self.organization_history
            )
            
            return {
                'total_organizations': len(self.organization_history),
                'total_items_stored': total_stored,
                'recent_organizations': self.organization_history[-5:]
            }
