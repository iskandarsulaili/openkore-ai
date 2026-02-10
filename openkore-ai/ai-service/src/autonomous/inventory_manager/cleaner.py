"""
Inventory Cleaner
Automatically sells junk items and manages inventory cleanup
"""

import asyncio
from typing import Dict, List, Any
from loguru import logger
import threading
from datetime import datetime


class InventoryCleaner:
    """
    Manages inventory cleanup through selling junk items
    Identifies and sells low-value items automatically
    """
    
    def __init__(self, openkore_client):
        """
        Initialize inventory cleaner
        
        Args:
            openkore_client: OpenKore HTTP client (REST API)
        """
        self.openkore = openkore_client
        self._lock = threading.RLock()
        self.cleanup_history: List[Dict] = []
        self.junk_item_patterns = [
            'Jellopy', 'Fluff', 'Clover', 'Feather', 'Sticky Mucus',
            'Shell', 'Worm Peeling', 'Chrysalis', 'Cobweb'
        ]
        
        logger.info("InventoryCleaner initialized")
    
    async def auto_sell_junk(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Automatically sell junk items at nearest NPC
        
        Args:
            game_state: Current game state
            
        Returns:
            Dictionary with cleanup result
        """
        with self._lock:
            try:
                inventory = game_state.get('inventory', {}).get('items', [])
                
                # Identify junk items
                junk_items = self._identify_junk_items(inventory)
                
                if not junk_items:
                    return {
                        'success': True,
                        'items_sold': 0,
                        'message': 'No junk items to sell'
                    }
                
                logger.info(f"Selling {len(junk_items)} junk items")
                
                # Navigate to merchant NPC
                await self._navigate_to_merchant()
                
                # Sell items
                total_zeny = await self._sell_items(junk_items)
                
                # Record cleanup
                self.cleanup_history.append({
                    'timestamp': datetime.now(),
                    'items_sold': len(junk_items),
                    'zeny_earned': total_zeny
                })
                
                return {
                    'success': True,
                    'items_sold': len(junk_items),
                    'zeny_earned': total_zeny,
                    'items': [item.get('name') for item in junk_items]
                }
                
            except Exception as e:
                logger.error(f"Auto-sell error: {e}")
                return {
                    'success': False,
                    'error': str(e)
                }
    
    def _identify_junk_items(self, inventory: List[Dict]) -> List[Dict]:
        """
        Identify junk items in inventory
        
        Args:
            inventory: List of inventory items
            
        Returns:
            List of junk items
        """
        junk = []
        
        for item in inventory:
            item_name = item.get('name', '')
            item_value = item.get('value', 0)
            
            # Check if item matches junk patterns
            if any(pattern in item_name for pattern in self.junk_item_patterns):
                junk.append(item)
            # Or if item has very low value
            elif item_value < 50 and item.get('type') not in ['quest', 'equipment']:
                junk.append(item)
        
        return junk
    
    async def _navigate_to_merchant(self) -> bool:
        """Navigate to nearest merchant NPC"""
        try:
            # Find nearest tool dealer or merchant
            await self.openkore.send_command("move tool dealer")
            await asyncio.sleep(3)
            
            # Talk to merchant
            await self.openkore.send_command("talk tool dealer")
            await asyncio.sleep(1.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation to merchant error: {e}")
            return False
    
    async def _sell_items(self, items: List[Dict]) -> int:
        """
        Sell items to merchant
        
        Args:
            items: List of items to sell
            
        Returns:
            Total zeny earned
        """
        total_zeny = 0
        
        try:
            for item in items:
                item_name = item.get('name')
                item_value = item.get('value', 0)
                amount = item.get('amount', 1)
                
                # Sell item
                await self.openkore.send_command(f"sell {item_name} {amount}")
                await asyncio.sleep(0.3)
                
                total_zeny += item_value * amount
            
            # Close shop
            await self.openkore.send_command("talk close")
            
            logger.success(f"Sold items for {total_zeny} zeny")
            return total_zeny
            
        except Exception as e:
            logger.error(f"Sell items error: {e}")
            return total_zeny
    
    def get_cleanup_statistics(self) -> Dict:
        """Get cleanup statistics"""
        with self._lock:
            if not self.cleanup_history:
                return {
                    'total_cleanups': 0,
                    'total_items_sold': 0,
                    'total_zeny_earned': 0
                }
            
            total_items = sum(r['items_sold'] for r in self.cleanup_history)
            total_zeny = sum(r['zeny_earned'] for r in self.cleanup_history)
            
            return {
                'total_cleanups': len(self.cleanup_history),
                'total_items_sold': total_items,
                'total_zeny_earned': total_zeny,
                'average_zeny_per_cleanup': round(total_zeny / len(self.cleanup_history), 2) if self.cleanup_history else 0
            }
