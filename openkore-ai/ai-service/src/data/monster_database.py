"""
Monster Database Manager

Handles monster data loading, querying, and dynamic server adaptation.
Provides fast lookup and intelligent monster analysis for targeting decisions.
"""

import json
import logging
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from functools import lru_cache
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class MonsterDatabase:
    """
    Monster Database Manager
    
    Features:
    - Fast lookup by ID and name (<5ms)
    - Fuzzy name matching for custom content
    - Optimal target selection based on context
    - Drop table analysis
    - Farming value calculation
    - Custom content detection
    """
    
    def __init__(self, db_path: str):
        """
        Load monster database with caching.
        
        Args:
            db_path: Path to monster_db.json file
        """
        self.db_path = Path(db_path)
        self.monsters = []
        self.metadata = {}
        
        # Fast lookup indices
        self.monsters_by_id: Dict[int, Dict] = {}
        self.monsters_by_name: Dict[str, Dict] = {}
        self.monsters_by_level: Dict[int, List[Dict]] = {}
        
        # Performance tracking
        self.load_time = 0
        self.query_count = 0
        
        # Load database
        self._load_database()
        self._build_indices()
        
        logger.info(f"MonsterDatabase initialized: {len(self.monsters)} monsters loaded in {self.load_time:.3f}s")
    
    def _load_database(self):
        """Load monster database from JSON file."""
        start_time = time.time()
        
        try:
            with open(self.db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            self.metadata = data.get('metadata', {})
            self.monsters = data.get('monsters', [])
            
            self.load_time = time.time() - start_time
            
            logger.info(f"Loaded {len(self.monsters)} monsters from {self.db_path}")
            
        except FileNotFoundError:
            logger.error(f"Monster database not found: {self.db_path}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in monster database: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load monster database: {e}")
            raise
    
    def _build_indices(self):
        """Build lookup indices for fast access."""
        logger.info("Building monster indices...")
        
        for monster in self.monsters:
            monster_id = monster.get('id')
            monster_name = monster.get('name', '').lower()
            monster_level = monster.get('level', 0)
            
            # Index by ID
            if monster_id:
                self.monsters_by_id[monster_id] = monster
            
            # Index by name
            if monster_name:
                self.monsters_by_name[monster_name] = monster
            
            # Index by level
            if monster_level not in self.monsters_by_level:
                self.monsters_by_level[monster_level] = []
            self.monsters_by_level[monster_level].append(monster)
        
        logger.info(f"Indices built: {len(self.monsters_by_id)} by ID, {len(self.monsters_by_name)} by name, {len(self.monsters_by_level)} level ranges")
    
    @lru_cache(maxsize=1000)
    def get_monster_by_id(self, monster_id: int) -> Optional[Dict]:
        """
        Fast lookup by monster ID (<5ms).
        
        Args:
            monster_id: Monster ID
        
        Returns:
            Monster data dict or None if not found
        """
        self.query_count += 1
        
        # Track query for integration verification
        logger.debug(f"[MONSTER-DB] Query: get_monster_by_id({monster_id})")
        
        result = self.monsters_by_id.get(monster_id)
        
        # Log result for integration verification
        if result:
            logger.debug(f"[MONSTER-DB] Found: {result.get('name')} (Level {result.get('level')}, HP {result.get('hp')})")
        else:
            logger.warning(f"[MONSTER-DB] Not found: ID {monster_id}")
        
        return result
    
    def get_monster_by_name(self, name: str, fuzzy: bool = True) -> Optional[Dict]:
        """
        Lookup by monster name with optional fuzzy matching.
        
        Args:
            name: Monster name
            fuzzy: Enable fuzzy matching for custom content
        
        Returns:
            Monster data dict or None if not found
        """
        self.query_count += 1
        logger.debug(f"[MONSTER-DB] Query: get_monster_by_name('{name}', fuzzy={fuzzy})")
        
        name_lower = name.lower()
        
        # Exact match first
        if name_lower in self.monsters_by_name:
            result = self.monsters_by_name[name_lower]
            logger.debug(f"[MONSTER-DB] Exact match found: {result.get('name')} (ID {result.get('id')})")
            return result
        
        # Fuzzy matching for custom content
        if fuzzy:
            best_match = None
            best_ratio = 0.0
            
            for monster_name, monster in self.monsters_by_name.items():
                ratio = SequenceMatcher(None, name_lower, monster_name).ratio()
                if ratio > best_ratio and ratio > 0.8:  # 80% similarity threshold
                    best_ratio = ratio
                    best_match = monster
            
            if best_match:
                logger.debug(f"Fuzzy match for '{name}': '{best_match.get('name')}' (ratio: {best_ratio:.2f})")
                return best_match
        
        return None
    
    def find_optimal_targets(self, context: Dict) -> List[Dict]:
        """
        Find best monsters based on level, exp, location, and available monsters.
        
        Args:
            context: Dict containing:
                - level: Player level
                - location: Current map
                - monsters: List of available monster IDs
                - goal: "exp" or "loot" (optional)
        
        Returns:
            List of monster dicts sorted by suitability
        """
        self.query_count += 1
        
        player_level = context.get('level', 1)
        available_ids = context.get('monsters', [])
        goal = context.get('goal', 'exp')
        
        logger.info(f"[MONSTER-DB] Finding optimal targets: Level {player_level}, Goal '{goal}', Available IDs: {available_ids}")
        
        if not available_ids:
            # Return level-appropriate monsters if no specific list provided
            return self._get_level_appropriate_monsters(player_level)
        
        # Get monster data for available IDs
        available_monsters = []
        for monster_id in available_ids:
            monster = self.get_monster_by_id(monster_id)
            if monster:
                available_monsters.append(monster)
        
        # Score and sort monsters
        scored_monsters = []
        for monster in available_monsters:
            score = self._calculate_target_score(monster, player_level, goal)
            scored_monsters.append({
                'monster': monster,
                'score': score
            })
        
        # Sort by score (highest first)
        scored_monsters.sort(key=lambda x: x['score'], reverse=True)
        
        return [item['monster'] for item in scored_monsters]
    
    def _get_level_appropriate_monsters(self, player_level: int) -> List[Dict]:
        """Get monsters appropriate for player level."""
        min_level = max(1, player_level - 10)
        max_level = player_level + 10
        
        appropriate = []
        for level in range(min_level, max_level + 1):
            if level in self.monsters_by_level:
                appropriate.extend(self.monsters_by_level[level])
        
        return appropriate[:50]  # Limit to 50 results
    
    def _calculate_target_score(self, monster: Dict, player_level: int, goal: str) -> float:
        """
        Calculate target priority score.
        
        Factors:
        - Level difference (prefer ±5 levels)
        - Experience gain
        - Drop value
        - Monster difficulty
        """
        monster_level = monster.get('level', 1)
        base_exp = monster.get('base_exp', 0)
        job_exp = monster.get('job_exp', 0)
        hp = monster.get('hp', 1)
        
        # Level difference penalty
        level_diff = abs(monster_level - player_level)
        if level_diff > 10:
            level_penalty = 0.5
        elif level_diff > 5:
            level_penalty = 0.7
        else:
            level_penalty = 1.0
        
        # Experience efficiency (exp per HP)
        exp_efficiency = (base_exp + job_exp) / max(hp, 1)
        
        # Goal-based weighting
        if goal == 'exp':
            score = exp_efficiency * level_penalty * 100
        else:  # loot
            drop_value = self._estimate_drop_value(monster)
            score = (exp_efficiency * 0.3 + drop_value * 0.7) * level_penalty * 100
        
        return score
    
    def _estimate_drop_value(self, monster: Dict) -> float:
        """Estimate total drop value (simplified)."""
        drops = monster.get('drops', [])
        if not drops:
            return 0.0
        
        # Count valuable drops (rate < 1000 = rare)
        valuable_drops = sum(1 for drop in drops if drop.get('rate', 10000) < 1000)
        
        return valuable_drops * 10.0
    
    def get_drop_table(self, monster_id: int) -> List[Dict]:
        """
        Get all drops with rates for a monster.
        
        Args:
            monster_id: Monster ID
        
        Returns:
            List of drop dicts with item name and rate
        """
        self.query_count += 1
        
        monster = self.get_monster_by_id(monster_id)
        if not monster:
            return []
        
        return monster.get('drops', [])
    
    def estimate_farming_value(self, monster_id: int, item_prices: Dict[str, float] = None) -> float:
        """
        Calculate estimated zeny/hour for farming this monster.
        
        Args:
            monster_id: Monster ID
            item_prices: Dict of item_name -> price (optional)
        
        Returns:
            Estimated zeny per kill
        """
        self.query_count += 1
        
        monster = self.get_monster_by_id(monster_id)
        if not monster:
            return 0.0
        
        drops = monster.get('drops', [])
        if not drops or not item_prices:
            return 0.0
        
        total_value = 0.0
        for drop in drops:
            item_name = drop.get('item', '')
            rate = drop.get('rate', 10000)  # Default 0.01% (10000 = 100%)
            
            # Convert rate to probability (rate / 10000)
            probability = rate / 10000.0
            
            # Get item price
            price = item_prices.get(item_name, 0)
            
            # Expected value = probability * price
            total_value += probability * price
        
        return total_value
    
    def detect_custom_monster(self, monster_data: Dict) -> bool:
        """
        Detect if monster is server-specific custom content.
        
        Custom content typically has:
        - ID > 50000
        - Unusual stat ratios
        - Non-standard drops
        
        Args:
            monster_data: Monster data dict (can be from game or database)
        
        Returns:
            True if likely custom content
        """
        monster_id = monster_data.get('id', 0)
        
        # Check if ID is in custom range
        if monster_id > 50000:
            return True
        
        # Check if monster exists in database
        if monster_id not in self.monsters_by_id:
            return True
        
        return False
    
    def adapt_to_custom_content(self, monster_data: Dict) -> Dict:
        """
        Dynamically adapt to unknown monsters.
        
        Creates estimated stats based on similar monsters.
        
        Args:
            monster_data: Partial monster data from game
        
        Returns:
            Enriched monster data with estimates
        """
        monster_id = monster_data.get('id', 0)
        monster_level = monster_data.get('level', 1)
        
        logger.info(f"Adapting to custom monster: ID={monster_id}, Level={monster_level}")
        
        # Find similar monsters by level
        similar = self.monsters_by_level.get(monster_level, [])
        
        if not similar:
            # Find nearest level
            for offset in range(1, 11):
                if monster_level + offset in self.monsters_by_level:
                    similar = self.monsters_by_level[monster_level + offset]
                    break
                if monster_level - offset in self.monsters_by_level:
                    similar = self.monsters_by_level[monster_level - offset]
                    break
        
        if similar:
            # Use average stats from similar monsters
            avg_hp = sum(m.get('hp', 0) for m in similar) / len(similar)
            avg_attack = sum(m.get('attack', 0) for m in similar) / len(similar)
            avg_defense = sum(m.get('defense', 0) for m in similar) / len(similar)
            avg_exp = sum(m.get('base_exp', 0) for m in similar) / len(similar)
            
            # Enrich monster data with estimates
            enriched = monster_data.copy()
            enriched.setdefault('hp', int(avg_hp))
            enriched.setdefault('attack', int(avg_attack))
            enriched.setdefault('defense', int(avg_defense))
            enriched.setdefault('base_exp', int(avg_exp))
            enriched['custom_content'] = True
            enriched['estimated_stats'] = True
            
            return enriched
        
        # Fallback: basic estimates
        enriched = monster_data.copy()
        enriched['custom_content'] = True
        enriched['estimated_stats'] = True
        return enriched
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get database statistics."""
        return {
            'total_monsters': len(self.monsters),
            'load_time_seconds': self.load_time,
            'query_count': self.query_count,
            'metadata': self.metadata,
            'level_range': {
                'min': min(self.monsters_by_level.keys()) if self.monsters_by_level else 0,
                'max': max(self.monsters_by_level.keys()) if self.monsters_by_level else 0
            }
        }
