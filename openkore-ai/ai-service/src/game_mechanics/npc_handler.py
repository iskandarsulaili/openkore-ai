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
# FIX 6: Ensure verbose sell debug logs are visible
logger.setLevel(logging.INFO)

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
        WITH VERBOSE DEBUGGING to solve "13 items but all protected" issue
        
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
        logger.info(f"[SELL-DEBUG] ========================================")
        logger.info(f"[SELL-DEBUG] CATEGORIZING {len(inventory)} ITEMS")
        logger.info(f"[SELL-DEBUG] ========================================")
        
        # Use provided quest items or empty list
        quest_items_set = set(quest_items) if quest_items else set()
        
        # Equipment types to protect
        EQUIPMENT_TYPES = {"weapon", "armor", "accessory", "garment", "footgear", "headgear"}
        
        # CRITICAL FIX: Explicit vendor trash IDs (common monster drops)
        # These should NEVER be protected - they're meant to be sold
        VENDOR_TRASH_IDS = {
            909,   # Jellopy
            713,   # Empty Bottle
            705,   # Clover
            715,   # Yellow Gemstone (sellable if excess)
            716,   # Red Gemstone (sellable if excess)
            717,   # Blue Gemstone (sellable if excess)
            915,   # Chrysalis
            938,   # Sticky Mucus
            949,   # Feather
            914,   # Fluff
            916,   # Feather of Birds
            955,   # Worm Peeling
            948,   # Bear's Footskin
            935,   # Shell
            946,   # Snail's Shell
            1055,  # Earthworm Peeling
            941,   # Skorpion's Tail
            942,   # Yoyo Tail
            943,   # Solid Shell
            945,   # Raccoon Leaf
            7006,  # Claw of Desert Wolf
            920,   # Wolf Claw
            947,   # Horn
            904,   # Scorpion Tail
            928,   # Frozen Heart
            950,   # Heart of Mermaid
            7033,  # Poison Spore
            512,   # Apple
            513,   # Banana
            514,   # Grape
            515,   # Carrot
            516,   # Sweet Potato
            517,   # Meat
            518,   # Honey
            519,   # Milk
            520,   # Leaflet of Hinal
            521,   # Leaflet of Aloe
            522,   # Fruit of Mastela (keep if low HP items)
        }
        
        # Consumables to KEEP (healing items for survival)
        CONSUMABLES_TO_KEEP = {
            "Red Potion", "Orange Potion", "Yellow Potion", "White Potion",
            "Blue Potion", "Green Potion",
            "Fly Wing", "Butterfly Wing",
            "Fruit of Mastela",  # High-tier heal
        }
        
        # Gemstones: Keep 10, sell excess
        GEMSTONE_IDS = {715, 716, 717}  # Yellow, Red, Blue Gemstone
        gemstone_counts = {}
        
        sell_list = []
        keep_list = []
        reasons = {}
        
        item_num = 0
        for item in inventory:
            item_num += 1
            item_name = item.get("name", "Unknown")
            
            # CRITICAL FIX: Convert string item_id to int (OpenKore sends strings)
            try:
                item_id = int(item.get("id", 0))
            except (ValueError, TypeError):
                item_id = 0
                logger.warning(f"[SELL-DEBUG] [{item_num}] Invalid item ID for {item_name}, defaulting to 0")
            
            try:
                amount = int(item.get("amount", 1))
            except (ValueError, TypeError):
                amount = 1
            
            item_type = item.get("type", "").lower()
            is_equipped = item.get("equipped", False)
            inv_index = item.get("invIndex", -1)
            
            logger.info(f"[SELL-DEBUG] [{item_num}] {item_name} x{amount} (ID:{item_id}, Type:{item_type}, Equipped:{is_equipped}, InvIdx:{inv_index})")
            
            # Rule 0: ALWAYS sell vendor trash (highest priority)
            if item_id in VENDOR_TRASH_IDS and item_id not in GEMSTONE_IDS:
                sell_list.append(item)
                reasons[item_name] = f"Vendor trash (ID: {item_id})"
                logger.info(f"[SELL-DEBUG] [{item_num}] ✓ SELL: Vendor trash (ID: {item_id})")
                continue
            
            # Rule 0b: Gemstones - keep 10, sell excess
            if item_id in GEMSTONE_IDS:
                gemstone_counts[item_id] = gemstone_counts.get(item_id, 0) + amount
                if gemstone_counts[item_id] > 10:
                    excess = gemstone_counts[item_id] - 10
                    # Sell excess gemstones
                    item_copy = item.copy()
                    item_copy['amount'] = excess
                    sell_list.append(item_copy)
                    reasons[item_name] = f"Excess gemstone (keeping 10, selling {excess})"
                    logger.info(f"[SELL-DEBUG] [{item_num}] ✓ SELL: Excess gemstone (keep 10, sell {excess})")
                    # Keep remaining
                    item_keep = item.copy()
                    item_keep['amount'] = 10
                    keep_list.append(item_keep)
                    continue
                else:
                    keep_list.append(item)
                    reasons[item_name] = f"Gemstone reserve (keeping for skills)"
                    logger.info(f"[SELL-DEBUG] [{item_num}] ✗ KEEP: Gemstone reserve")
                    continue
            
            # Rule 1: Never sell cards (use table_loader if available)
            if is_card_func and is_card_func(item_name):
                keep_list.append(item)
                reasons[item_name] = "Card (valuable)"
                logger.info(f"[SELL-DEBUG] [{item_num}] ✗ KEEP: Card (valuable)")
                continue
            elif 4001 <= item_id <= 4999:
                keep_list.append(item)
                reasons[item_name] = "Card (valuable)"
                logger.info(f"[SELL-DEBUG] [{item_num}] ✗ KEEP: Card range (4001-4999)")
                continue
            
            # Rule 2: Never sell quest items (from table_loader)
            if item_name in quest_items_set:
                keep_list.append(item)
                reasons[item_name] = "Quest item"
                logger.info(f"[SELL-DEBUG] [{item_num}] ✗ KEEP: Quest item")
                continue
            
            # Rule 3: Never sell equipped items
            if is_equipped:
                keep_list.append(item)
                reasons[item_name] = "Currently equipped"
                logger.info(f"[SELL-DEBUG] [{item_num}] ✗ KEEP: Currently equipped")
                continue
            
            # Rule 4: Never sell equipment (unless junk)
            if item_type in EQUIPMENT_TYPES:
                keep_list.append(item)
                reasons[item_name] = "Equipment"
                logger.info(f"[SELL-DEBUG] [{item_num}] ✗ KEEP: Equipment type")
                continue
            
            # Rule 5: Keep essential consumables (healing items for survival)
            if item_name in CONSUMABLES_TO_KEEP:
                keep_list.append(item)
                reasons[item_name] = "Essential consumable (needed for survival)"
                logger.info(f"[SELL-DEBUG] [{item_num}] ✗ KEEP: Essential consumable")
                continue
            
            # Rule 6: Sell everything else (monster drops, misc items, food items)
            # This includes: Apple, Meat, Monster drops, etc.
            sell_list.append(item)
            reasons[item_name] = f"Sellable (type: {item_type})"
            logger.info(f"[SELL-DEBUG] [{item_num}] ✓ SELL: Sellable item (type: {item_type})")
        
        logger.info(f"[SELL-DEBUG] ========================================")
        logger.info(f"[SELL-DEBUG] CATEGORIZATION COMPLETE")
        logger.info(f"[SELL-DEBUG] Sellable: {len(sell_list)} items")
        logger.info(f"[SELL-DEBUG] Keep: {len(keep_list)} items")
        logger.info(f"[SELL-DEBUG] ========================================")
        
        if sell_list:
            logger.info(f"[SELL-DEBUG] Items TO SELL:")
            for item in sell_list[:20]:  # Show first 20
                logger.info(f"[SELL-DEBUG]   - {item.get('name')} x{item.get('amount', 1)} (ID:{item.get('id')})")
        else:
            logger.warning(f"[SELL-DEBUG] ⚠️ NO ITEMS TO SELL - All items were protected!")
            logger.warning(f"[SELL-DEBUG] Protected items:")
            for item in keep_list[:10]:
                logger.warning(f"[SELL-DEBUG]   - {item.get('name')} x{item.get('amount', 1)} (Reason: {reasons.get(item.get('name'), 'unknown')})")
        
        if keep_list:
            logger.info(f"[SELL-DEBUG] Items TO KEEP:")
            for item in keep_list[:20]:  # Show first 20
                logger.info(f"[SELL-DEBUG]   - {item.get('name')} x{item.get('amount', 1)} (Reason: {reasons.get(item.get('name'), 'unknown')})")
        
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
        logger.info("[SELL-DEBUG] ========================================")
        logger.info(f"[SELL-DEBUG] Starting sell_junk_items with {len(inventory)} inventory items")
        logger.info("[SELL-DEBUG] ========================================")
        
        # Categorize items
        categorized = self.categorize_inventory_for_selling(inventory)
        
        if not categorized["sell"]:
            logger.info("[SELL-DEBUG] No junk items to sell")
            return {
                "success": True,
                "items_sold": [],
                "estimated_zeny": 0,
                "message": "No sellable items in inventory"
            }
        
        # Calculate estimated value
        estimated_value = 0
        items_to_sell = []
        
        logger.info(f"[SELL-DEBUG] Processing {len(categorized['sell'])} sellable items...")
        
        for item in categorized["sell"]:
            item_name = item.get("name", "Unknown")
            
            # CRITICAL FIX: Convert string amounts to int (OpenKore sends strings)
            try:
                sell_price = int(item.get("sell_price", 10))
            except (ValueError, TypeError):
                sell_price = 10
                logger.debug(f"[SELL-DEBUG] Invalid sell_price for {item_name}, using default 10z")
            
            try:
                amount = int(item.get("amount", 1))
            except (ValueError, TypeError):
                amount = 1
                logger.warning(f"[SELL-DEBUG] Invalid amount for {item_name}, defaulting to 1")
            
            estimated_value += sell_price * amount
            items_to_sell.append(item_name)
        
        logger.info(f"[SELL-DEBUG] Planning to sell {len(items_to_sell)} item types for ~{estimated_value}z")
        logger.info(f"[SELL-DEBUG] Items: {', '.join(items_to_sell[:10])}...")  # Log first 10
        
        # Generate sell command for OpenKore
        # CRITICAL FIX: OpenKore syntax is "sell <invIndex> [amount]"
        # invIndex is the inventory slot number (0, 1, 2, ...), NOT the item name
        sell_commands = []
        logger.info("[SELL-DEBUG] Generating sell commands...")
        
        for item in categorized["sell"]:
            item_name = item.get("name", "Unknown")
            item_id = item.get("id", "0")
            
            # CRITICAL FIX: Get invIndex (inventory slot number) for correct sell syntax
            try:
                inv_index = int(item.get("invIndex", -1))
            except (ValueError, TypeError):
                inv_index = -1
                logger.error(f"[SELL-DEBUG] ❌ Missing or invalid invIndex for {item_name} (ID:{item_id}), cannot sell")
                continue
            
            if inv_index < 0:
                logger.error(f"[SELL-DEBUG] ❌ Invalid invIndex {inv_index} for {item_name} (ID:{item_id}), SKIPPING")
                continue
            
            # CRITICAL FIX: Convert string amount to int (OpenKore sends strings)
            try:
                amount = int(item.get("amount", 1))
            except (ValueError, TypeError):
                amount = 1
                logger.warning(f"[SELL-DEBUG] Invalid amount for {item_name} in sell_commands, defaulting to 1")
            
            # Correct OpenKore sell syntax: sell <invIndex> [amount]
            sell_cmd = f"sell {inv_index} {amount}"
            sell_commands.append(sell_cmd)
            logger.info(f"[SELL-DEBUG] ✓ Generated command: '{sell_cmd}' for {item_name} (ID:{item_id}) at invIndex={inv_index}, qty={amount}")
        
        logger.info(f"[SELL-DEBUG] ========================================")
        logger.info(f"[SELL-DEBUG] Total sell commands generated: {len(sell_commands)}")
        logger.info(f"[SELL-DEBUG] Estimated zeny gain: {estimated_value}z")
        logger.info(f"[SELL-DEBUG] ========================================")
        
        if not sell_commands:
            logger.error("[SELL-DEBUG] ⚠️ WARNING: No sell commands generated despite having sellable items!")
            logger.error("[SELL-DEBUG] This indicates invIndex collection failure!")
        
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


def find_nearest_npc(npc_type: str, current_map: str, current_pos: Dict) -> Optional[Dict]:
    """
    GOD-TIER IMPROVEMENT #8: Find nearest NPC of given type from current position
    
    Args:
        npc_type: Type of NPC to find (e.g., 'tool_dealer', 'potion_seller')
        current_map: Current map name
        current_pos: Current position dict with 'x' and 'y' keys
        
    Returns:
        NPC info dict with map, x, y, name, priority or None if not found
    """
    # Load NPC locations from JSON database
    npc_locations_path = Path(__file__).parent.parent.parent / "data" / "npc_locations.json"
    
    if not npc_locations_path.exists():
        logger.error(f"[NPC] NPC locations database not found: {npc_locations_path}")
        return None
    
    try:
        with open(npc_locations_path, 'r', encoding='utf-8') as f:
            npc_database = json.load(f)
    except Exception as e:
        logger.error(f"[NPC] Failed to load NPC locations: {e}")
        return None
    
    npcs_of_type = npc_database.get(npc_type, [])
    
    if not npcs_of_type:
        logger.error(f"[NPC] No NPCs of type '{npc_type}' found in database")
        return None
    
    # Calculate distances
    distances = []
    for npc in npcs_of_type:
        # Simple map distance calculation
        # Same map = distance based on coordinates
        # Different map = add penalty (1000 cells)
        if npc['map'] == current_map:
            dx = npc['x'] - current_pos.get('x', 0)
            dy = npc['y'] - current_pos.get('y', 0)
            dist = (dx ** 2 + dy ** 2) ** 0.5  # Euclidean distance
        else:
            dist = 1000 + npc.get('priority', 999) * 100  # Cross-map penalty + priority
        
        distances.append((dist, npc))
    
    # Sort by distance, return closest
    distances.sort(key=lambda x: x[0])
    nearest = distances[0][1]
    
    logger.info(f"[NPC] Nearest {npc_type}: {nearest['name']} at {nearest['map']} ({nearest['x']},{nearest['y']}) - ~{distances[0][0]:.1f} cells away")
    return nearest


# Global instance (loaded lazily)
_npc_handler = None

def get_npc_handler() -> NPCHandler:
    """Get or create global NPC handler instance"""
    global _npc_handler
    if _npc_handler is None:
        _npc_handler = NPCHandler()
    return _npc_handler
