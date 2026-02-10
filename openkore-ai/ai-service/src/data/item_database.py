"""
Item Database Manager

Handles item data loading, querying, and dynamic server adaptation.
Provides fast lookup and intelligent item analysis for loot prioritization.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class ItemDatabase:
    """
    Item Database Manager
    
    Features:
    - Fast lookup by ID and name (<5ms)
    - Fuzzy name matching for custom content
    - Category-based queries
    - Equipment requirement checking
    - Context-based value calculation
    - Custom content detection
    - Priority database integration
    """
    
    def __init__(self, db_path: str, priority_db_path: str = None):
        """
        Load item database with optional priority database merge.
        
        Args:
            db_path: Path to item_db.json file
            priority_db_path: Path to loot_priority_database.json (optional)
        """
        self.db_path = Path(db_path)
        self.priority_db_path = Path(priority_db_path) if priority_db_path else None
        
        self.items = []
        self.metadata = {}
        self.priority_items = []
        
        # Fast lookup indices
        self.items_by_id: Dict[int, Dict] = {}
        self.items_by_name: Dict[str, Dict] = {}
        self.items_by_category: Dict[str, List[Dict]] = {}
        
        # Performance tracking
        self.load_time = 0
        self.query_count = 0
        
        # Load databases
        self._load_database()
        if self.priority_db_path and self.priority_db_path.exists():
            self._load_priority_database()
        self._build_indices()
        
        logger.info(f"ItemDatabase initialized: {len(self.items)} items loaded in {self.load_time:.3f}s")
    
    def _load_database(self):
        """Load item database from JSON file."""
        start_time = time.time()
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get('metadata', {})
            self.items = data.get('items', [])
            
            self.load_time = time.time() - start_time
            
            logger.info(f"Loaded {len(self.items)} items from {self.db_path}")
            
        except FileNotFoundError:
            logger.error(f"Item database not found: {self.db_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in item database: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load item database: {e}")
            raise
    
    def _load_priority_database(self):
        """Load and merge priority database."""
        try:
            with open(self.priority_db_path, 'r', encoding='utf-8') as f:
                priority_data = json.load(f)
            
            self.priority_items = priority_data.get('items', [])
            
            # Merge priorities into main database
            priority_map = {item.get('id'): item for item in self.priority_items}
            
            for item in self.items:
                item_id = item.get('id')
                if item_id in priority_map:
                    priority_info = priority_map[item_id]
                    item['priority'] = priority_info.get('priority', 50)
                    item['category_tags'] = priority_info.get('tags', [])
                    item['loot_decision'] = priority_info.get('decision', 'evaluate')
            
            logger.info(f"Merged {len(self.priority_items)} priority items")
            
        except Exception as e:
            logger.warning(f"Failed to load priority database: {e}")
    
    def _build_indices(self):
        """Build lookup indices for fast access."""
        logger.info("Building item indices...")
        
        for item in self.items:
            item_id = item.get('id')
            item_name = item.get('name', '').lower()
            item_type = item.get('type', 'unknown').lower()
            
            # Index by ID
            if item_id:
                self.items_by_id[item_id] = item
            
            # Index by name
            if item_name:
                self.items_by_name[item_name] = item
            
            # Index by category/type
            if item_type not in self.items_by_category:
                self.items_by_category[item_type] = []
            self.items_by_category[item_type].append(item)
        
        logger.info(f"Indices built: {len(self.items_by_id)} by ID, {len(self.items_by_name)} by name, {len(self.items_by_category)} categories")
    
    @lru_cache(maxsize=2000)
    def get_item_by_id(self, item_id: int) -> Optional[Dict]:
        """
        Fast lookup by item ID (<5ms).
        
        Args:
            item_id: Item ID
        
        Returns:
            Item data dict or None if not found
        """
        self.query_count += 1
        
        # Track query for integration verification
        logger.debug(f"[ITEM-DB] Query: get_item_by_id({item_id})")
        
        result = self.items_by_id.get(item_id)
        
        # Log result for integration verification
        if result:
            logger.debug(f"[ITEM-DB] Found: {result.get('name')} (Type: {result.get('type')}, Price: {result.get('buy_price', 0)}z)")
        else:
            logger.warning(f"[ITEM-DB] Not found: ID {item_id}")
        
        return result
    
    def get_item_by_name(self, name: str, fuzzy: bool = True) -> Optional[Dict]:
        """
        Lookup by item name with optional fuzzy matching.
        
        Args:
            name: Item name
            fuzzy: Enable fuzzy matching for custom content
        
        Returns:
            Item data dict or None if not found
        """
        self.query_count += 1
        logger.debug(f"[ITEM-DB] Query: get_item_by_name('{name}', fuzzy={fuzzy})")
        
        name_lower = name.lower()
        
        # Exact match first
        if name_lower in self.items_by_name:
            result = self.items_by_name[name_lower]
            logger.debug(f"[ITEM-DB] Exact match found: {result.get('name')} (ID {result.get('id')})")
            return result
        
        # Fuzzy matching for custom content
        if fuzzy:
            best_match = None
            best_ratio = 0.0
            
            for item_name, item in self.items_by_name.items():
                ratio = SequenceMatcher(None, name_lower, item_name).ratio()
                if ratio > best_ratio and ratio > 0.8:  # 80% similarity threshold
                    best_ratio = ratio
                    best_match = item
            
            if best_match:
                logger.debug(f"Fuzzy match for '{name}': '{best_match.get('name')}' (ratio: {best_ratio:.2f})")
                return best_match
        
        return None
    
    def get_items_by_category(self, category: str) -> List[Dict]:
        """
        Get all items in a category.
        
        Args:
            category: Item category (weapon, armor, card, etc.)
        
        Returns:
            List of item dicts in category
        """
        self.query_count += 1
        category_lower = category.lower()
        
        logger.debug(f"[ITEM-DB] Query: get_items_by_category('{category}')")
        
        results = self.items_by_category.get(category_lower, [])
        logger.debug(f"[ITEM-DB] Found {len(results)} items in category '{category}'")
        
        return results
    
    def get_equipment_requirements(self, item_id: int) -> Dict:
        """
        Get job/level requirements for equipment.
        
        Args:
            item_id: Item ID
        
        Returns:
            Dict with job, level, and other requirements
        """
        self.query_count += 1
        
        item = self.get_item_by_id(item_id)
        if not item:
            return {}
        
        # Extract requirement info
        requirements = {
            'level': item.get('required_level', 0),
            'jobs': item.get('jobs', []),
            'gender': item.get('gender', 'both'),
            'classes': item.get('applicable_jobs', [])
        }
        
        return requirements
    
    def calculate_item_value(self, item_id: int, context: Dict = None) -> float:
        """
        Calculate actual value based on context.
        
        Considers:
        - Base NPC price
        - Item type (cards are valuable)
        - Rarity (if from drop data)
        - Player needs (equipment upgrades)
        - Market value (if available)
        
        Args:
            item_id: Item ID
            context: Optional context with player info, market prices, etc.
        
        Returns:
            Calculated value score (0-100)
        """
        self.query_count += 1
        logger.debug(f"[ITEM-DB] Calculating value for item ID {item_id}")
        
        item = self.get_item_by_id(item_id)
        if not item:
            logger.warning(f"[ITEM-DB] Cannot calculate value - item {item_id} not found")
            return 0.0
        
        context = context or {}
        
        # Start with priority if available
        base_value = 100 - item.get('priority', 50)  # Convert priority to value (lower priority = higher value)
        
        # Item type multipliers
        item_type = item.get('type', '').lower()
        type_multipliers = {
            'card': 2.0,
            'weapon': 1.5,
            'armor': 1.3,
            'shadowgear': 1.4,
            'cash': 1.2,
            'healing': 0.8,
            'etc': 0.5
        }
        multiplier = type_multipliers.get(item_type, 1.0)
        
        # NPC price influence
        npc_price = item.get('buy_price', 0)
        if npc_price > 100000:
            multiplier *= 1.5
        elif npc_price > 10000:
            multiplier *= 1.2
        
        # Weight penalty (heavy items less valuable unless valuable)
        weight = item.get('weight', 0)
        if weight > 1000 and npc_price < 10000:
            multiplier *= 0.7
        
        # Context-based adjustments
        if context:
            player_level = context.get('player_level', 1)
            player_job = context.get('player_job', '')
            
            # Check if item is equipment upgrade
            if item_type in ['weapon', 'armor']:
                req_level = item.get('required_level', 0)
                if req_level <= player_level <= req_level + 10:
                    multiplier *= 1.3  # Potential upgrade
        
        final_value = min(base_value * multiplier, 100.0)
        return final_value
    
    def detect_custom_item(self, item_data: Dict) -> bool:
        """
        Detect server-specific custom items.
        
        Custom items typically have:
        - ID > 50000
        - Non-standard types
        - Unusual properties
        
        Args:
            item_data: Item data dict
        
        Returns:
            True if likely custom content
        """
        item_id = item_data.get('id', 0)
        
        # Check if ID is in custom range
        if item_id > 50000:
            return True
        
        # Check if item exists in database
        if item_id not in self.items_by_id:
            return True
        
        return False
    
    def adapt_to_custom_content(self, item_data: Dict) -> Dict:
        """
        Dynamically adapt to unknown items.
        
        Creates estimated properties based on similar items.
        
        Args:
            item_data: Partial item data from game
        
        Returns:
            Enriched item data with estimates
        """
        item_id = item_data.get('id', 0)
        item_name = item_data.get('name', 'Unknown Item')
        
        logger.info(f"Adapting to custom item: ID={item_id}, Name={item_name}")
        
        # Try to infer type from name
        name_lower = item_name.lower()
        inferred_type = 'etc'
        
        if 'card' in name_lower:
            inferred_type = 'card'
        elif any(weapon in name_lower for weapon in ['sword', 'bow', 'staff', 'dagger', 'spear']):
            inferred_type = 'weapon'
        elif any(armor in name_lower for armor in ['armor', 'shield', 'helm', 'boots', 'garment']):
            inferred_type = 'armor'
        
        # Get similar items for reference
        similar_items = self.get_items_by_category(inferred_type)
        
        # Calculate average properties
        avg_price = 0
        avg_weight = 0
        if similar_items:
            prices = [item.get('buy_price', 0) for item in similar_items[:100]]
            weights = [item.get('weight', 0) for item in similar_items[:100]]
            avg_price = sum(prices) / len(prices) if prices else 0
            avg_weight = sum(weights) / len(weights) if weights else 0
        
        # Enrich item data
        enriched = item_data.copy()
        enriched['type'] = inferred_type
        enriched.setdefault('buy_price', int(avg_price))
        enriched.setdefault('weight', int(avg_weight))
        enriched['custom_content'] = True
        enriched['estimated_properties'] = True
        enriched['priority'] = 30  # Default medium-high priority for unknown items
        
        return enriched
    
    def get_cards(self) -> List[Dict]:
        """Get all card items."""
        return self.get_items_by_category('card')
    
    def get_equipment_by_slot(self, slot: str) -> List[Dict]:
        """
        Get equipment for specific slot.
        
        Args:
            slot: Equipment slot (headgear, armor, weapon, etc.)
        
        Returns:
            List of items for that slot
        """
        self.query_count += 1
        
        slot_types = {
            'weapon': ['weapon'],
            'armor': ['armor'],
            'headgear': ['armor'],  # Need to filter by location
            'accessory': ['armor'],
            'garment': ['armor'],
            'shield': ['armor']
        }
        
        relevant_types = slot_types.get(slot.lower(), [])
        results = []
        
        for item_type in relevant_types:
            items = self.get_items_by_category(item_type)
            # Additional filtering would go here based on equipment location
            results.extend(items)
        
        return results
    
    def search_items(self, query: str, limit: int = 50) -> List[Dict]:
        """
        Search items by name or description.
        
        Args:
            query: Search query
            limit: Maximum results
        
        Returns:
            List of matching items
        """
        self.query_count += 1
        query_lower = query.lower()
        
        results = []
        for item in self.items:
            item_name = item.get('name', '').lower()
            if query_lower in item_name:
                results.append(item)
                if len(results) >= limit:
                    break
        
        return results
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            'total_items': len(self.items),
            'priority_items': len(self.priority_items),
            'load_time_seconds': self.load_time,
            'query_count': self.query_count,
            'metadata': self.metadata,
            'categories': {cat: len(items) for cat, items in self.items_by_category.items()}
        }
