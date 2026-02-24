"""
Loot Prioritization Engine

Handles item priority lookup, pattern matching, and ground item sorting.
"""

import json
import re
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class LootPrioritizer:
    """
    Intelligent loot prioritization system that:
    - Loads item database with priorities
    - Matches items by ID, name, and patterns
    - Detects slotted equipment dynamically
    - Applies user customizations
    - Sorts ground items by priority
    """
    
    def __init__(self, database_path: str, config_path: str):
        """
        Initialize the loot prioritizer.
        
        Args:
            database_path: Path to loot_priority_database.json
            config_path: Path to loot_config.json
        """
        self.database_path = Path(database_path)
        self.config_path = Path(config_path)
        
        # Load database and config
        self.item_db = self._load_item_database()
        self.config = self._load_loot_config()
        
        # Full item database (integration with Phase 1)
        self.full_item_db = None
        
        # Build lookup indices for fast access
        self._build_indices()
        
        logger.info(f"LootPrioritizer initialized with {len(self.items_by_id)} items")
    
    def _load_item_database(self) -> Dict[str, Any]:
        """Load the item priority database."""
        try:
            with open(self.database_path, 'r', encoding='utf-8') as f:
                db = json.load(f)
            logger.info(f"Loaded item database: {db['metadata']['total_items']} items")
            return db
        except Exception as e:
            logger.error(f"Failed to load item database: {e}")
            return {"items": [], "categories": {}, "patterns": {}}
    
    def _load_loot_config(self) -> Dict[str, Any]:
        """Load the loot configuration."""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Load user customizations if available
            user_config_path = self.config_path.parent / "loot_config_user.json"
            if user_config_path.exists():
                with open(user_config_path, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                # Merge user config
                config = self._merge_configs(config, user_config)
                logger.info("User customizations loaded")
            
            return config
        except Exception as e:
            logger.error(f"Failed to load loot config: {e}")
            return {}
    
    def _merge_configs(self, base: Dict, user: Dict) -> Dict:
        """Merge user config into base config."""
        merged = base.copy()
        
        # Merge custom priorities
        if "custom_priorities" in user:
            for item_id_str, custom in user["custom_priorities"].items():
                item_id = int(item_id_str)
                # Find and update item in database
                for item in merged.get("custom_items", []):
                    if item.get("item_id") == item_id:
                        item.update(custom)
                        break
                else:
                    # Add new custom item
                    if "custom_items" not in merged:
                        merged["custom_items"] = []
                    merged["custom_items"].append({
                        "item_id": item_id,
                        **custom
                    })
        
        # Merge preferences
        if "risk_preferences" in user:
            merged.setdefault("risk_tolerance", {}).update(user["risk_preferences"])
        
        if "tactic_preferences" in user:
            merged.setdefault("tactical_preferences", {}).update(user["tactic_preferences"])
        
        return merged
    
    def _build_indices(self):
        """Build lookup indices for fast item retrieval."""
        self.items_by_id = {}
        self.items_by_name = {}
        
        # Index database items
        for item in self.item_db.get("items", []):
            item_id = item.get("item_id")
            item_name = item.get("item_name", "").lower()
            
            if item_id:
                self.items_by_id[item_id] = item
            if item_name:
                self.items_by_name[item_name] = item
        
        # Index custom items from config
        for item in self.config.get("custom_items", []):
            item_id = item.get("item_id")
            item_name = item.get("item_name", "").lower()
            
            if item_id:
                self.items_by_id[item_id] = item
            if item_name:
                self.items_by_name[item_name] = item
        
        logger.debug(f"Built indices: {len(self.items_by_id)} by ID, {len(self.items_by_name)} by name")
    
    def get_item_priority(self, item_id: Optional[int] = None, item_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get priority information for an item.
        
        Args:
            item_id: Item ID (nameID)
            item_name: Item name
        
        Returns:
            Dict with priority_level, category, estimated_value, etc.
        """
        # Try exact ID match first
        if item_id and item_id in self.items_by_id:
            item_data = self.items_by_id[item_id].copy()
            logger.debug(f"Found item by ID {item_id}: {item_data.get('item_name')}")
            return item_data
        
        # Try exact name match
        if item_name:
            item_name_lower = item_name.lower()
            if item_name_lower in self.items_by_name:
                item_data = self.items_by_name[item_name_lower].copy()
                logger.debug(f"Found item by name '{item_name}': {item_data.get('item_id')}")
                return item_data
            
            # Try pattern matching for slotted equipment
            slot_match = self._detect_slotted_equipment(item_name)
            if slot_match:
                return slot_match
            
            # Try partial name match
            partial_match = self._partial_name_match(item_name)
            if partial_match:
                return partial_match
        
        # Default: unknown item with low priority
        return self._default_item_priority(item_id, item_name)
    
    def _detect_slotted_equipment(self, item_name: str) -> Optional[Dict[str, Any]]:
        """
        Detect slotted equipment by pattern matching [1], [2], [3], [4].
        
        Args:
            item_name: Item name to check
        
        Returns:
            Item data if slotted equipment detected, None otherwise
        """
        slot_pattern = self.item_db.get("patterns", {}).get("slot_detection", {})
        pattern_str = slot_pattern.get("pattern", r"\[(\d+)\]")
        
        match = re.search(pattern_str, item_name)
        if match:
            slot_count = int(match.group(1))
            priority_modifier = slot_pattern.get("priority_modifier", {}).get(str(slot_count), 0)
            
            # Base name without slot indicator
            base_name = re.sub(pattern_str, "", item_name).strip()
            
            # Check if we have the base item
            base_item = self.items_by_name.get(base_name.lower())
            if base_item:
                item_data = base_item.copy()
                item_data["item_name"] = item_name  # Keep full name with slots
                item_data["priority_level"] = max(1, item_data.get("priority_level", 20) + priority_modifier)
                item_data["slot_count"] = slot_count
                logger.debug(f"Detected slotted equipment: {item_name} [{slot_count}] - Priority: {item_data['priority_level']}")
                return item_data
            
            # Generic slotted equipment
            base_priority = 25
            final_priority = max(1, base_priority + priority_modifier)
            
            return {
                "item_id": None,
                "item_name": item_name,
                "priority_level": final_priority,
                "category": "slotted_equipment",
                "estimated_value": 100000 * slot_count,
                "user_notes": f"{slot_count}-slot equipment detected",
                "slot_count": slot_count
            }
        
        return None
    
    def _partial_name_match(self, item_name: str) -> Optional[Dict[str, Any]]:
        """
        Try to find item by partial name matching.
        
        Args:
            item_name: Item name to match
        
        Returns:
            Best matching item data or None
        """
        item_name_lower = item_name.lower()
        
        # Find items with matching substrings
        matches = []
        for db_name, item_data in self.items_by_name.items():
            if db_name in item_name_lower or item_name_lower in db_name:
                matches.append((item_data, len(db_name)))
        
        if matches:
            # Return the match with longest matching name (most specific)
            best_match = max(matches, key=lambda x: x[1])
            item_data = best_match[0].copy()
            logger.debug(f"Partial name match for '{item_name}': {item_data.get('item_name')}")
            return item_data
        
        return None
    
    def _default_item_priority(self, item_id: Optional[int], item_name: Optional[str]) -> Dict[str, Any]:
        """
        Return default priority for unknown items.
        
        Args:
            item_id: Item ID
            item_name: Item name
        
        Returns:
            Default item data
        """
        # Check if name suggests card
        if item_name and "card" in item_name.lower():
            category = "rare_card"
            priority = 10
            value = 100000
        else:
            category = "unknown"
            priority = 60
            value = 1000
        
        return {
            "item_id": item_id,
            "item_name": item_name or "Unknown Item",
            "priority_level": priority,
            "category": category,
            "estimated_value": value,
            "user_notes": "Unknown item - default priority"
        }
    
    def prioritize_visible_loot(self, ground_items: List[Dict[str, Any]], game_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Sort ground items by pickup priority.
        
        Args:
            ground_items: List of items on ground with item_id, item_name, position, binID
            game_state: Current game state for context
        
        Returns:
            Sorted list of items with priority metadata
        """
        if not ground_items:
            return []
        
        prioritized_items = []
        
        for item in ground_items:
            item_id = item.get("item_id") or item.get("nameID")
            item_name = item.get("item_name") or item.get("name")
            
            # Get priority data
            priority_data = self.get_item_priority(item_id, item_name)
            
            # Build enriched item data
            enriched = {
                **item,  # Original item data
                **priority_data,  # Priority metadata
                "distance": self._calculate_distance(
                    game_state.get("character", {}).get("position", {}),
                    item.get("position", {})
                )
            }
            
            prioritized_items.append(enriched)
        
        # Sort by priority (lower number = higher priority)
        prioritized_items.sort(key=lambda x: (
            x.get("priority_level", 100),  # Primary: priority
            -x.get("estimated_value", 0),   # Secondary: value (descending)
            x.get("distance", 999)          # Tertiary: distance (ascending)
        ))
        
        logger.info(f"Prioritized {len(prioritized_items)} ground items")
        if prioritized_items:
            top_item = prioritized_items[0]
            logger.info(f"Top priority: {top_item.get('item_name')} (Priority: {top_item.get('priority_level')}, Value: {top_item.get('estimated_value')})")
        
        return prioritized_items
    
    def _calculate_distance(self, pos1: Dict[str, int], pos2: Dict[str, int]) -> float:
        """Calculate Manhattan distance between two positions."""
        if not pos1 or not pos2:
            return 999.0
        
        x1, y1 = pos1.get("x", 0), pos1.get("y", 0)
        x2, y2 = pos2.get("x", 0), pos2.get("y", 0)
        
        return abs(x2 - x1) + abs(y2 - y1)
    
    def is_sacrifice_worthy(self, item_data: Dict[str, Any]) -> bool:
        """
        Determine if an item is worth dying for.
        
        Args:
            item_data: Item priority data
        
        Returns:
            True if sacrifice is allowed for this item
        """
        # Check category rules
        category = item_data.get("category")
        category_info = self.item_db.get("categories", {}).get(category, {})
        sacrifice_allowed = category_info.get("sacrifice_allowed", False)
        
        # Check specific rules
        priority = item_data.get("priority_level", 100)
        sacrifice_config = self.config.get("sacrifice_rules", {})
        
        # MVP cards always worth it
        if category == "mvp_card" and sacrifice_config.get("mvp_card_always_worth", True):
            return True
        
        # High priority items
        if sacrifice_allowed and priority <= sacrifice_config.get("min_priority_for_sacrifice", 10):
            return True
        
        # High value items
        value = item_data.get("estimated_value", 0)
        min_value = sacrifice_config.get("min_value_multiplier", 5.0) * 100000  # Assuming 100k base respawn cost
        if sacrifice_allowed and value >= min_value:
            return True
        
        return False
    
    def get_category_info(self, category: str) -> Dict[str, Any]:
        """Get category information."""
        return self.item_db.get("categories", {}).get(category, {})
    
    def set_item_database(self, item_db: 'ItemDatabase'):
        """
        Replace hardcoded 350 items with full 29,056 item database.
        Maintains priority system but expands coverage.
        
        Args:
            item_db: ItemDatabase instance from Phase 1
        """
        self.full_item_db = item_db
        
        # Rebuild priority mappings with full database
        self._rebuild_priority_mappings()
        
        logger.info(f"Integrated full item database: {len(item_db.items)} items available")
    
    def _rebuild_priority_mappings(self):
        """
        Rebuild priority system using full item database:
        1. Keep existing priority assignments (350 items)
        2. Auto-assign priorities to remaining items based on:
           - Item type (cards highest, etc)
           - Item rarity (based on drop rates)
           - Item value (from NPC prices)
           - Equipment power (attack/defense)
        3. Mark unknown items for learning
        """
        if not self.full_item_db:
            logger.warning("Full item database not set, skipping priority rebuild")
            return
        
        logger.info("Rebuilding priority mappings with full database...")
        
        # Priority assignments by item type
        type_priorities = {
            'card': 10,
            'weapon': 30,
            'armor': 35,
            'shadowgear': 32,
            'cash': 40,
            'healing': 50,
            'usable': 55,
            'etc': 60,
            'ammo': 65
        }
        
        new_items_added = 0
        
        # Add items from full database that aren't in priority database
        for item in self.full_item_db.items:
            item_id = item.get('id')
            
            # Skip if already in our priority database
            if item_id and item_id in self.items_by_id:
                continue
            
            # Auto-assign priority based on type
            item_type = item.get('type', '').lower()
            base_priority = type_priorities.get(item_type, 60)
            
            # Adjust priority based on NPC price
            npc_price = item.get('buy_price', 0)
            if npc_price > 100000:
                base_priority = max(10, base_priority - 20)
            elif npc_price > 10000:
                base_priority = max(20, base_priority - 10)
            
            # Create priority entry
            priority_entry = {
                'item_id': item_id,
                'item_name': item.get('name', 'Unknown'),
                'priority_level': base_priority,
                'category': item_type,
                'estimated_value': npc_price or 1000,
                'user_notes': 'Auto-assigned from full database',
                'auto_generated': True
            }
            
            # Add to indices
            if item_id:
                self.items_by_id[item_id] = priority_entry
            
            item_name = item.get('name', '').lower()
            if item_name:
                self.items_by_name[item_name] = priority_entry
            
            new_items_added += 1
        
        logger.info(f"Priority rebuild complete: Added {new_items_added} items from full database")
        logger.info(f"Total items in prioritizer: {len(self.items_by_id)}")
    
    def reload_database(self):
        """Reload item database (for hot-reloading)."""
        logger.info("Reloading item database...")
        self.item_db = self._load_item_database()
        self.config = self._load_loot_config()
        self._build_indices()
        logger.info("Item database reloaded successfully")
