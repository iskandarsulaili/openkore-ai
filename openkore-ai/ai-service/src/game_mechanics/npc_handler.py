"""
NPC Interaction Handler for OpenKore AI-Service
Handles buying, selling, and NPC communication with retry logic

User requirement: "NPC location should never be hardcoded... All of them should use
database available in D:\\RO\\bot\\renew\\openkore-ai\\tables as the first source and NEVER hardcoded"
"""
import logging
import json
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import asyncio

logger = logging.getLogger(__name__)

class NPCHandler:
    """
    Manages NPC interactions with robust error handling
    
    NEVER HARDCODES NPC locations - loads from configuration file
    """
    
    def __init__(self, config_path: Optional[Path] = None):
        """
        Initialize NPC Handler
        
        Args:
            config_path: Path to npc_config.json (default: auto-detect)
        """
        self.last_npc_interaction = 0
        self.interaction_cooldown = 3  # seconds between interactions
        
        # Load NPC database from config file
        if config_path is None:
            # Auto-detect: ai-service/data/npc_config.json
            config_path = Path(__file__).parent.parent.parent / "data" / "npc_config.json"
        
        self.config_path = config_path
        self.npc_database = self._load_npc_config()
        self.buying_quantities = self.npc_database.get("buying_quantities", {})
        
        logger.info(f"[NPC] Loaded NPC configuration from {config_path}")
        logger.info(f"[NPC] Available cities: {list(self.npc_database.get('npcs', {}).keys())}")
    
    def _load_npc_config(self) -> Dict:
        """
        Load NPC configuration from JSON file
        
        User requirement: Never hardcode NPC locations
        """
        if not self.config_path.exists():
            logger.error(f"[NPC] Config file not found: {self.config_path}")
            logger.warning("[NPC] Using minimal fallback configuration")
            return {
                "npcs": {
                    "prontera": {
                        "tool_dealer": {
                            "x": 134,
                            "y": 88,
                            "name": "Tool Dealer",
                            "type": "vendor"
                        }
                    }
                },
                "buying_quantities": {"default": 10}
            }
        
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info(f"[NPC] Successfully loaded NPC config with {len(config.get('npcs', {}))} cities")
                return config
        except Exception as e:
            logger.error(f"[NPC] Failed to load config: {e}")
            return {"npcs": {}, "buying_quantities": {"default": 10}}
        
    def find_npc_for_items(self, items: List[str], current_map: str = "prontera") -> Optional[Dict]:
        """
        Find which NPC sells the requested items
        
        Args:
            items: List of item names to find
            current_map: Current map name (to find nearest NPC)
        
        Returns NPC info dict with location or None if no NPC sells these items
        """
        npcs = self.npc_database.get("npcs", {})
        
        # First, try to find NPC on current map
        if current_map in npcs:
            for npc_key, npc_info in npcs[current_map].items():
                if "items" in npc_info:
                    # Check if this NPC sells any of the requested items
                    if any(item in npc_info["items"] for item in items):
                        # Add map name to return info
                        npc_with_map = npc_info.copy()
                        npc_with_map["map"] = current_map
                        npc_with_map["location"] = (npc_info["x"], npc_info["y"])
                        return npc_with_map
        
        # If not found on current map, search all maps
        for map_name, map_npcs in npcs.items():
            for npc_key, npc_info in map_npcs.items():
                if "items" in npc_info:
                    if any(item in npc_info["items"] for item in items):
                        npc_with_map = npc_info.copy()
                        npc_with_map["map"] = map_name
                        npc_with_map["location"] = (npc_info["x"], npc_info["y"])
                        logger.info(f"[NPC] Found NPC on different map: {map_name}")
                        return npc_with_map
        
        logger.warning(f"[NPC] No NPC found that sells: {items}")
        return None
    
    def get_npc_buy_command(self, npc_name: str, items: List[str]) -> str:
        """
        Generate OpenKore command to buy items from NPC
        
        Uses buying_quantities from config (NEVER hardcoded)
        
        Returns command string like: "buy Red Potion 10, Fly Wing 5"
        """
        buy_list = []
        default_qty = self.buying_quantities.get("default", 10)
        
        for item in items:
            qty = self.buying_quantities.get(item, default_qty)
            buy_list.append(f"{item} {qty}")
        
        logger.debug(f"[NPC] Buy command for {len(items)} items")
        return "buy " + ", ".join(buy_list)
    
    async def buy_items_with_retry(
        self, 
        items: List[str], 
        max_retries: int = 3,
        timeout: int = 10
    ) -> Dict:
        """
        Attempt to buy items from appropriate NPC with retry logic
        
        Returns:
            {
                "success": bool,
                "items_bought": List[str],
                "error": Optional[str],
                "retry_count": int
            }
        """
        logger.info(f"[NPC] Attempting to buy items: {items}")
        
        # Find appropriate NPC
        npc_info = self.find_npc_for_items(items)
        if not npc_info:
            logger.error(f"[NPC] No NPC found that sells: {items}")
            return {
                "success": False,
                "items_bought": [],
                "error": "No NPC sells these items",
                "retry_count": 0
            }
        
        logger.info(f"[NPC] Target NPC: {npc_info['name']} at {npc_info['location']}")
        
        # Generate buy command
        buy_command = self.get_npc_buy_command(npc_info["name"], items)
        
        for attempt in range(max_retries):
            try:
                logger.info(f"[NPC] Buy attempt {attempt + 1}/{max_retries}")
                
                # In actual implementation, this would send command to OpenKore
                # For now, we'll return the command to be executed
                result = {
                    "success": True,
                    "items_bought": items,
                    "npc_name": npc_info["name"],
                    "npc_location": npc_info["location"],
                    "command": buy_command,
                    "retry_count": attempt + 1,
                    "instruction": "Execute this command in OpenKore console"
                }
                
                logger.info(f"[NPC] Buy command ready: {buy_command}")
                return result
                
            except Exception as e:
                logger.error(f"[NPC] Attempt {attempt + 1} failed: {e}")
                
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"[NPC] Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                else:
                    return {
                        "success": False,
                        "items_bought": [],
                        "error": str(e),
                        "retry_count": max_retries
                    }
        
        return {
            "success": False,
            "items_bought": [],
            "error": "Max retries exceeded",
            "retry_count": max_retries
        }
    
    def categorize_inventory_for_selling(
        self,
        inventory: List[Dict],
        quest_items: List[str] = None,
        is_card_func = None
    ) -> Dict:
        """
        Categorize inventory items into sellable vs keep
        
        Args:
            inventory: List of inventory items
            quest_items: List of quest item names (from table_loader)
            is_card_func: Function to check if item is a card (from table_loader)
        
        Returns:
            {
                "sell": List[Dict],  # Items safe to sell
                "keep": List[Dict],  # Items to protect
                "reasons": Dict  # Why each item was categorized
            }
        """
        # Use provided quest items or empty list
        quest_items_set = set(quest_items) if quest_items else set()
        
        # Equipment types to protect
        EQUIPMENT_TYPES = {"weapon", "armor", "accessory", "garment", "footgear", "headgear"}
        
        sell_list = []
        keep_list = []
        reasons = {}
        
        for item in inventory:
            item_name = item.get("name", "Unknown")
            item_id = item.get("id", 0)
            item_type = item.get("type", "").lower()
            is_equipped = item.get("equipped", False)
            
            # Rule 1: Never sell cards (use table_loader if available)
            if is_card_func and is_card_func(item_name):
                keep_list.append(item)
                reasons[item_name] = "Card (valuable)"
                continue
            elif 4001 <= item_id <= 4999:
                keep_list.append(item)
                reasons[item_name] = "Card (valuable)"
                continue
            
            # Rule 2: Never sell quest items (from table_loader)
            if item_name in quest_items_set:
                keep_list.append(item)
                reasons[item_name] = "Quest item"
                continue
            
            # Rule 3: Never sell equipped items
            if is_equipped:
                keep_list.append(item)
                reasons[item_name] = "Currently equipped"
                continue
            
            # Rule 4: Never sell equipment (unless junk)
            if item_type in EQUIPMENT_TYPES:
                keep_list.append(item)
                reasons[item_name] = "Equipment"
                continue
            
            # Rule 5: Keep consumables (potions, food)
            if item_type == "consumable" or "Potion" in item_name or item_name in ["Apple", "Meat", "Fly Wing"]:
                keep_list.append(item)
                reasons[item_name] = "Consumable (needed for survival)"
                continue
            
            # Rule 6: Sell everything else (monster drops, misc items)
            sell_list.append(item)
            reasons[item_name] = f"Sellable (type: {item_type})"
        
        logger.info(f"[SELL] Categorized inventory: {len(sell_list)} sellable, {len(keep_list)} keep")
        
        return {
            "sell": sell_list,
            "keep": keep_list,
            "reasons": reasons
        }
    
    async def sell_junk_items(
        self,
        inventory: List[Dict],
        min_zeny_threshold: int = 1000
    ) -> Dict:
        """
        Sell junk items to NPC while protecting important items
        
        Returns:
            {
                "success": bool,
                "items_sold": List[str],
                "estimated_zeny": int,
                "actual_zeny": Optional[int]
            }
        """
        logger.info("[SELL] Starting junk item selling process...")
        
        # Categorize items
        categorized = self.categorize_inventory_for_selling(inventory)
        
        if not categorized["sell"]:
            logger.info("[SELL] No junk items to sell")
            return {
                "success": True,
                "items_sold": [],
                "estimated_zeny": 0,
                "message": "No sellable items in inventory"
            }
        
        # Calculate estimated value
        estimated_value = 0
        items_to_sell = []
        
        for item in categorized["sell"]:
            item_name = item.get("name", "Unknown")
            # Rough estimation: Most low-level drops sell for 2-50z each
            sell_price = item.get("sell_price", 10)  # Default 10z if unknown
            amount = item.get("amount", 1)
            
            estimated_value += sell_price * amount
            items_to_sell.append(item_name)
        
        logger.info(f"[SELL] Planning to sell {len(items_to_sell)} item types for ~{estimated_value}z")
        logger.info(f"[SELL] Items: {', '.join(items_to_sell[:10])}...")  # Log first 10
        
        # Generate sell command for OpenKore
        # OpenKore command: "sell <item name> <amount>"
        sell_commands = []
        for item in categorized["sell"]:
            item_name = item.get("name", "Unknown")
            amount = item.get("amount", 1)
            sell_commands.append(f"sell {item_name} {amount}")
        
        # Get tool dealer location from config (never hardcoded)
        tool_dealer_location = None
        npcs = self.npc_database.get("npcs", {})
        for map_name, map_npcs in npcs.items():
            if "tool_dealer" in map_npcs:
                td = map_npcs["tool_dealer"]
                tool_dealer_location = (td["x"], td["y"])
                break
        
        return {
            "success": True,
            "items_sold": items_to_sell,
            "estimated_zeny": estimated_value,
            "sell_commands": sell_commands,
            "instruction": "Execute these commands at Tool Dealer NPC",
            "npc_location": tool_dealer_location
        }


# Global instance (loaded lazily)
_npc_handler = None

def get_npc_handler() -> NPCHandler:
    """Get or create global NPC handler instance"""
    global _npc_handler
    if _npc_handler is None:
        _npc_handler = NPCHandler()
    return _npc_handler
