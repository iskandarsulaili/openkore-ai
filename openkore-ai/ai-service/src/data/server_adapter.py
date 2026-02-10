"""
Dynamic Server Content Adapter

Handles server-specific custom content detection and adaptation.
Enables AI to work on any server without hardcoded logic.
"""

import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class ServerContentAdapter:
    """
    Dynamic Server Content Adapter
    
    Features:
    - Auto-detect server type from patterns
    - Register custom content dynamically
    - Adapt decision logic for custom content
    - Learn from encounters
    - Persist learned patterns
    """
    
    def __init__(self, monster_db: 'MonsterDatabase', item_db: 'ItemDatabase'):
        """
        Initialize server content adapter.
        
        Args:
            monster_db: MonsterDatabase instance
            item_db: ItemDatabase instance
        """
        self.monster_db = monster_db
        self.item_db = item_db
        
        # Learned custom content
        self.custom_monsters: Dict[int, Dict] = {}
        self.custom_items: Dict[int, Dict] = {}
        
        # Server detection
        self.detected_server_type = "unknown"
        self.server_features: List[str] = []
        
        # Learning metrics
        self.encounter_history: List[Dict] = []
        self.learning_enabled = True
        
        logger.info("ServerContentAdapter initialized")
    
    def detect_server_type(self, game_state: Dict) -> str:
        """
        Auto-detect server type from network packets and game state.
        
        Detects based on patterns, not hardcoded server names:
        - Custom item/monster ID ranges
        - Unique features (custom stats, mechanics)
        - Network packet patterns
        
        Args:
            game_state: Current game state with network info
        
        Returns:
            Detected server type (generic identifier)
        """
        # Check for custom content indicators
        monsters = game_state.get('monsters', [])
        items = game_state.get('items', [])
        
        custom_monster_count = 0
        custom_item_count = 0
        
        for monster in monsters:
            if self.monster_db.detect_custom_monster(monster):
                custom_monster_count += 1
        
        for item in items:
            if self.item_db.detect_custom_item(item):
                custom_item_count += 1
        
        # Classify server based on custom content ratio
        total_monsters = len(monsters) or 1
        total_items = len(items) or 1
        
        custom_ratio = (custom_monster_count / total_monsters + custom_item_count / total_items) / 2
        
        if custom_ratio > 0.3:
            server_type = "high_custom"
            self.server_features.append("extensive_custom_content")
        elif custom_ratio > 0.1:
            server_type = "moderate_custom"
            self.server_features.append("some_custom_content")
        else:
            server_type = "standard"
        
        if server_type != self.detected_server_type:
            logger.info(f"Server type detected: {server_type} (custom ratio: {custom_ratio:.2%})")
            self.detected_server_type = server_type
        
        return server_type
    
    def register_custom_content(self, content_type: str, data: Dict):
        """
        Register newly discovered custom content.
        
        Args:
            content_type: "monster" or "item"
            data: Content data dict
        """
        if content_type == "monster":
            monster_id = data.get('id')
            if monster_id and monster_id not in self.custom_monsters:
                # Adapt monster data
                adapted = self.monster_db.adapt_to_custom_content(data)
                self.custom_monsters[monster_id] = adapted
                logger.info(f"Registered custom monster: {monster_id} - {data.get('name')}")
        
        elif content_type == "item":
            item_id = data.get('id')
            if item_id and item_id not in self.custom_items:
                # Adapt item data
                adapted = self.item_db.adapt_to_custom_content(data)
                self.custom_items[item_id] = adapted
                logger.info(f"Registered custom item: {item_id} - {data.get('name')}")
        
        else:
            logger.warning(f"Unknown content type: {content_type}")
    
    def adapt_decision_logic(self, content_data: Dict) -> Dict:
        """
        Modify AI decisions for custom content.
        
        Returns adapted priorities and strategies:
        - Unknown items get medium priority until learned
        - Unknown monsters get cautious approach
        - Learned patterns get applied
        
        Args:
            content_data: Custom content data
        
        Returns:
            Decision modifications dict
        """
        content_type = content_data.get('type', 'unknown')
        content_id = content_data.get('id', 0)
        
        adaptations = {
            'priority': 50,  # Default medium priority
            'strategy': 'cautious',
            'learning_mode': True
        }
        
        if content_type == 'monster':
            # Check if we've learned about this monster
            if content_id in self.custom_monsters:
                learned = self.custom_monsters[content_id]
                encounters = learned.get('encounter_count', 0)
                
                if encounters > 10:
                    # Enough data, use learned strategy
                    adaptations['strategy'] = 'normal'
                    adaptations['learning_mode'] = False
                    
                    # Adjust priority based on learned outcomes
                    avg_reward = learned.get('avg_reward', 0)
                    if avg_reward > 1000:
                        adaptations['priority'] = 30  # High priority
                    elif avg_reward > 500:
                        adaptations['priority'] = 40
                else:
                    # Still learning
                    adaptations['strategy'] = 'cautious'
                    adaptations['priority'] = 50
        
        elif content_type == 'item':
            # Check if we've learned about this item
            if content_id in self.custom_items:
                learned = self.custom_items[content_id]
                
                # Use adapted properties
                item_type = learned.get('type', 'etc')
                if item_type == 'card':
                    adaptations['priority'] = 10  # Very high priority
                elif item_type in ['weapon', 'armor']:
                    adaptations['priority'] = 30
                else:
                    adaptations['priority'] = 50
        
        return adaptations
    
    def learn_from_encounters(self, encounter_data: Dict):
        """
        Learn patterns from custom quest/NPC interactions.
        
        Updates knowledge about:
        - Monster difficulty and rewards
        - Item actual values
        - Quest patterns
        - NPC behavior
        
        Args:
            encounter_data: Data from game encounter
        """
        if not self.learning_enabled:
            return
        
        encounter_type = encounter_data.get('type', 'unknown')
        timestamp = datetime.now().isoformat()
        
        # Store encounter
        self.encounter_history.append({
            **encounter_data,
            'timestamp': timestamp
        })
        
        # Limit history size
        if len(self.encounter_history) > 1000:
            self.encounter_history = self.encounter_history[-1000:]
        
        # Learn from monster encounters
        if encounter_type == 'monster_kill':
            monster_id = encounter_data.get('monster_id')
            if monster_id and monster_id in self.custom_monsters:
                monster = self.custom_monsters[monster_id]
                
                # Update statistics
                monster['encounter_count'] = monster.get('encounter_count', 0) + 1
                
                # Update reward tracking
                rewards = encounter_data.get('rewards', {})
                exp_gained = rewards.get('exp', 0)
                items_dropped = rewards.get('items', [])
                
                # Calculate average reward
                current_avg = monster.get('avg_reward', 0)
                encounter_count = monster['encounter_count']
                
                # Estimate value of drops (simplified)
                drop_value = len(items_dropped) * 100
                total_reward = exp_gained + drop_value
                
                # Update moving average
                monster['avg_reward'] = ((current_avg * (encounter_count - 1)) + total_reward) / encounter_count
                
                logger.debug(f"Updated monster {monster_id} stats: {encounter_count} encounters, avg reward: {monster['avg_reward']:.0f}")
        
        # Learn from item acquisitions
        elif encounter_type == 'item_acquired':
            item_id = encounter_data.get('item_id')
            if item_id and item_id in self.custom_items:
                item = self.custom_items[item_id]
                
                # Track how often we acquire this item
                item['acquisition_count'] = item.get('acquisition_count', 0) + 1
                
                # Update priority based on frequency
                acq_count = item['acquisition_count']
                if acq_count > 20:
                    # Common item, lower priority
                    item['priority'] = min(item.get('priority', 50) + 10, 70)
                
                logger.debug(f"Updated item {item_id} stats: {acq_count} acquisitions")
    
    def sync_custom_content_to_openmemory(self, openmemory_service):
        """
        Store custom content in OpenMemory semantic sector.
        
        This enables persistent learning across bot restarts.
        
        Args:
            openmemory_service: OpenMemory service instance
        """
        try:
            # Prepare custom content summary
            custom_content_summary = {
                'server_type': self.detected_server_type,
                'server_features': self.server_features,
                'custom_monsters': {
                    str(mid): {
                        'name': m.get('name'),
                        'level': m.get('level'),
                        'encounter_count': m.get('encounter_count', 0),
                        'avg_reward': m.get('avg_reward', 0)
                    }
                    for mid, m in self.custom_monsters.items()
                },
                'custom_items': {
                    str(iid): {
                        'name': i.get('name'),
                        'type': i.get('type'),
                        'priority': i.get('priority'),
                        'acquisition_count': i.get('acquisition_count', 0)
                    }
                    for iid, i in self.custom_items.items()
                },
                'total_encounters': len(self.encounter_history)
            }
            
            # Store in semantic memory
            openmemory_service.store_semantic_knowledge(
                category='server_custom_content',
                knowledge=custom_content_summary
            )
            
            logger.info(f"Synced custom content to OpenMemory: {len(self.custom_monsters)} monsters, {len(self.custom_items)} items")
            
        except Exception as e:
            logger.error(f"Failed to sync custom content to OpenMemory: {e}")
    
    def load_custom_content_from_openmemory(self, openmemory_service):
        """
        Load previously learned custom content from OpenMemory.
        
        Args:
            openmemory_service: OpenMemory service instance
        """
        try:
            # Retrieve from semantic memory
            knowledge = openmemory_service.retrieve_semantic_knowledge(
                category='server_custom_content'
            )
            
            if knowledge:
                self.detected_server_type = knowledge.get('server_type', 'unknown')
                self.server_features = knowledge.get('server_features', [])
                
                # Restore custom monsters
                for mid_str, monster_data in knowledge.get('custom_monsters', {}).items():
                    monster_id = int(mid_str)
                    self.custom_monsters[monster_id] = monster_data
                
                # Restore custom items
                for iid_str, item_data in knowledge.get('custom_items', {}).items():
                    item_id = int(iid_str)
                    self.custom_items[item_id] = item_data
                
                logger.info(f"Loaded custom content from OpenMemory: {len(self.custom_monsters)} monsters, {len(self.custom_items)} items")
        
        except Exception as e:
            logger.error(f"Failed to load custom content from OpenMemory: {e}")
    
    def export_learned_content(self, output_path: str):
        """
        Export learned content to JSON file for backup/analysis.
        
        Args:
            output_path: Path to output file
        """
        try:
            export_data = {
                'server_type': self.detected_server_type,
                'server_features': self.server_features,
                'custom_monsters': self.custom_monsters,
                'custom_items': self.custom_items,
                'encounter_history': self.encounter_history[-100:],  # Last 100 encounters
                'export_timestamp': datetime.now().isoformat()
            }
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2)
            
            logger.info(f"Exported learned content to {output_path}")
            
        except Exception as e:
            logger.error(f"Failed to export learned content: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get adapter statistics."""
        return {
            'server_type': self.detected_server_type,
            'server_features': self.server_features,
            'custom_monsters_count': len(self.custom_monsters),
            'custom_items_count': len(self.custom_items),
            'total_encounters': len(self.encounter_history),
            'learning_enabled': self.learning_enabled
        }
