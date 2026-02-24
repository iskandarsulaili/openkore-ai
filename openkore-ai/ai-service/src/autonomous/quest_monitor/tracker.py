"""
Quest Tracker
Tracks active quests and detects completion opportunities
Pattern-based quest detection (server-agnostic)
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from loguru import logger
import threading
from datetime import datetime, timedelta


class QuestTracker:
    """
    Tracks quest states and detects completion opportunities
    Supports pattern-based quest detection for server-agnostic operation
    """
    
    def __init__(self, data_dir: Path):
        """
        Initialize quest tracker
        
        Args:
            data_dir: Directory containing quest_patterns.json
        """
        self.data_dir = data_dir
        self.active_quests: Dict[str, Dict] = {}
        self.completed_quests: List[str] = []
        self.quest_patterns: Dict[str, Any] = {}
        self._lock = threading.RLock()
        self._load_quest_patterns()
        
        logger.info("QuestTracker initialized")
    
    def _load_quest_patterns(self):
        """Load quest detection patterns from configuration"""
        try:
            pattern_file = self.data_dir / "quest_patterns.json"
            
            if pattern_file.exists():
                with open(pattern_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.quest_patterns = data.get('patterns', {})
                logger.success(f"Loaded {len(self.quest_patterns)} quest patterns")
            else:
                logger.warning("Quest pattern file not found, using defaults")
                self._create_default_patterns()
                
        except Exception as e:
            logger.error(f"Failed to load quest patterns: {e}")
            self._create_default_patterns()
    
    def _create_default_patterns(self):
        """Create default quest patterns"""
        self.quest_patterns = {
            "kill_count": {
                "type": "monster_kill",
                "detection": "inventory_item_increase",
                "completion_check": "item_count_threshold"
            },
            "collection": {
                "type": "item_collection",
                "detection": "quest_log_update",
                "completion_check": "inventory_has_items"
            },
            "delivery": {
                "type": "delivery",
                "detection": "npc_dialogue",
                "completion_check": "target_npc_found"
            },
            "exploration": {
                "type": "location",
                "detection": "map_entry",
                "completion_check": "coordinates_reached"
            }
        }
    
    def update_quest_state(self, game_state: Dict[str, Any]) -> None:
        """
        Update quest state based on game state
        
        Args:
            game_state: Current game state with quest information
        """
        with self._lock:
            try:
                # Extract quest data from game state
                quests = game_state.get('quests', {})
                active = quests.get('active', [])
                
                # Update active quests
                for quest_data in active:
                    quest_id = quest_data.get('quest_id')
                    if quest_id:
                        self._update_active_quest(quest_id, quest_data)
                
                # Check for completed quests
                self._check_quest_completions(game_state)
                
            except Exception as e:
                logger.error(f"Error updating quest state: {e}")
    
    def _update_active_quest(self, quest_id: str, quest_data: Dict) -> None:
        """
        Update or add active quest
        
        Args:
            quest_id: Quest identifier
            quest_data: Quest data from game state
        """
        if quest_id not in self.active_quests:
            logger.info(f"New quest detected: {quest_id}")
            self.active_quests[quest_id] = {
                'quest_id': quest_id,
                'name': quest_data.get('name', 'Unknown Quest'),
                'type': self._detect_quest_type(quest_data),
                'started_at': datetime.now(),
                'progress': quest_data.get('progress', {}),
                'objectives': quest_data.get('objectives', []),
                'turn_in_npc': quest_data.get('turn_in_npc'),
                'turn_in_map': quest_data.get('turn_in_map')
            }
        else:
            # Update existing quest progress
            self.active_quests[quest_id]['progress'] = quest_data.get('progress', {})
    
    def _detect_quest_type(self, quest_data: Dict) -> str:
        """
        Detect quest type from quest data
        
        Args:
            quest_data: Quest information
            
        Returns:
            Quest type string
        """
        objectives = quest_data.get('objectives', [])
        
        # Simple heuristic based on objectives
        for obj in objectives:
            obj_str = str(obj).lower()
            if 'kill' in obj_str or 'defeat' in obj_str:
                return 'kill_count'
            elif 'collect' in obj_str or 'gather' in obj_str:
                return 'collection'
            elif 'deliver' in obj_str or 'bring' in obj_str:
                return 'delivery'
            elif 'go to' in obj_str or 'reach' in obj_str:
                return 'exploration'
        
        return 'unknown'
    
    def _check_quest_completions(self, game_state: Dict[str, Any]) -> None:
        """
        Check which quests are ready for completion
        
        Args:
            game_state: Current game state
        """
        for quest_id, quest_info in list(self.active_quests.items()):
            if self._is_quest_complete(quest_id, quest_info, game_state):
                logger.success(f"Quest ready for completion: {quest_info['name']}")
                quest_info['ready_for_completion'] = True
                quest_info['completed_at'] = datetime.now()
    
    def _is_quest_complete(
        self,
        quest_id: str,
        quest_info: Dict,
        game_state: Dict[str, Any]
    ) -> bool:
        """
        Check if quest objectives are complete
        
        Args:
            quest_id: Quest identifier
            quest_info: Quest information
            game_state: Current game state
            
        Returns:
            True if quest is complete
        """
        quest_type = quest_info.get('type', 'unknown')
        progress = quest_info.get('progress', {})
        
        if quest_type == 'kill_count':
            return self._check_kill_count_complete(progress)
        elif quest_type == 'collection':
            return self._check_collection_complete(progress, game_state)
        elif quest_type == 'delivery':
            return self._check_delivery_complete(progress, game_state)
        elif quest_type == 'exploration':
            return self._check_exploration_complete(progress, game_state)
        
        # If unknown type, check generic progress field
        return progress.get('complete', False) or progress.get('percentage', 0) >= 100
    
    def _check_kill_count_complete(self, progress: Dict) -> bool:
        """Check if kill count quest is complete"""
        current = progress.get('current', 0)
        required = progress.get('required', 1)
        return current >= required
    
    def _check_collection_complete(self, progress: Dict, game_state: Dict) -> bool:
        """Check if collection quest is complete"""
        required_items = progress.get('required_items', [])
        inventory = game_state.get('inventory', {}).get('items', [])
        
        for req_item in required_items:
            item_name = req_item.get('name')
            required_count = req_item.get('count', 1)
            
            # Check if we have enough of this item
            has_count = sum(
                item.get('amount', 0)
                for item in inventory
                if item.get('name') == item_name
            )
            
            if has_count < required_count:
                return False
        
        return len(required_items) > 0
    
    def _check_delivery_complete(self, progress: Dict, game_state: Dict) -> bool:
        """Check if delivery quest is complete"""
        # Delivery is complete when we have the item and haven't delivered yet
        has_item = progress.get('has_delivery_item', False)
        delivered = progress.get('delivered', False)
        return has_item and not delivered
    
    def _check_exploration_complete(self, progress: Dict, game_state: Dict) -> bool:
        """Check if exploration quest is complete"""
        target_map = progress.get('target_map')
        current_map = game_state.get('character', {}).get('map')
        return target_map and current_map == target_map
    
    def get_completable_quests(self) -> List[Dict]:
        """
        Get list of quests ready for completion
        
        Returns:
            List of quests ready to turn in
        """
        with self._lock:
            completable = []
            for quest_id, quest_info in self.active_quests.items():
                if quest_info.get('ready_for_completion', False):
                    completable.append({
                        'quest_id': quest_id,
                        'name': quest_info['name'],
                        'type': quest_info['type'],
                        'turn_in_npc': quest_info.get('turn_in_npc'),
                        'turn_in_map': quest_info.get('turn_in_map'),
                        'duration': (datetime.now() - quest_info['started_at']).total_seconds()
                    })
            
            # Sort by priority (delivery quests first, then by duration)
            completable.sort(key=lambda q: (
                0 if q['type'] == 'delivery' else 1,
                -q['duration']
            ))
            
            return completable
    
    def mark_quest_completed(self, quest_id: str) -> bool:
        """
        Mark quest as completed and remove from active list
        
        Args:
            quest_id: Quest identifier
            
        Returns:
            True if quest was found and marked complete
        """
        with self._lock:
            if quest_id in self.active_quests:
                quest_info = self.active_quests.pop(quest_id)
                self.completed_quests.append(quest_id)
                logger.success(f"Quest completed: {quest_info['name']}")
                return True
            return False
    
    def get_active_quest_count(self) -> int:
        """Get count of active quests"""
        with self._lock:
            return len(self.active_quests)
    
    def get_quest_statistics(self) -> Dict:
        """Get quest tracking statistics"""
        with self._lock:
            completable = sum(
                1 for q in self.active_quests.values()
                if q.get('ready_for_completion', False)
            )
            
            return {
                'active_quests': len(self.active_quests),
                'completable_quests': completable,
                'total_completed': len(self.completed_quests),
                'quest_types': self._get_type_distribution()
            }
    
    def _get_type_distribution(self) -> Dict[str, int]:
        """Get distribution of active quest types"""
        distribution = {}
        for quest_info in self.active_quests.values():
            quest_type = quest_info.get('type', 'unknown')
            distribution[quest_type] = distribution.get(quest_type, 0) + 1
        return distribution
