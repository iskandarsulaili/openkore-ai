"""
Training Data Collection for ML Models
Extracts features from game state and decision history
"""

from typing import List, Dict, Any, Tuple
import numpy as np
from loguru import logger
import json
from datetime import datetime

class FeatureExtractor:
    """Extracts 28 features from game state for ML model"""
    
    FEATURE_NAMES = [
        # Character features (8)
        'char_level', 'char_hp_ratio', 'char_sp_ratio', 'char_weight_ratio',
        'char_zeny', 'char_base_exp', 'char_job_exp', 'char_status_count',
        
        # Combat features (8)
        'monster_count', 'monster_avg_distance', 'monster_aggressive_count',
        'monster_min_hp_ratio', 'monster_max_distance', 'monster_in_range_count',
        'monster_weakest_hp', 'monster_closest_distance',
        
        # Inventory features (6)
        'inventory_count', 'inventory_healing_count', 'inventory_attack_count',
        'inventory_misc_count', 'inventory_value_estimate', 'inventory_slots_free',
        
        # Social features (4)
        'player_count', 'party_member_count', 'guild_member_count', 'player_avg_distance',
        
        # Temporal features (2)
        'time_of_day', 'session_duration_minutes'
    ]
    
    @staticmethod
    def extract_features(game_state: Dict[str, Any], session_start: int) -> np.ndarray:
        """Extract feature vector from game state"""
        features = np.zeros(28)
        
        char = game_state.get('character', {})
        
        # Character features
        features[0] = char.get('level', 1)
        features[1] = char.get('hp', 0) / max(char.get('max_hp', 1), 1)
        features[2] = char.get('sp', 0) / max(char.get('max_sp', 1), 1)
        features[3] = char.get('weight', 0) / max(char.get('max_weight', 1), 1)
        features[4] = min(char.get('zeny', 0) / 1000000.0, 10.0)  # Normalize to 0-10
        features[5] = min(char.get('base_exp', 0) / 10000000.0, 10.0)
        features[6] = min(char.get('job_exp', 0) / 1000000.0, 10.0)
        features[7] = len(char.get('status_effects', []))
        
        # Combat features
        monsters = game_state.get('monsters', [])
        features[8] = min(len(monsters), 20)  # Cap at 20
        
        if monsters:
            distances = [m.get('distance', 999) for m in monsters]
            features[9] = np.mean(distances) if distances else 0
            features[10] = sum(1 for m in monsters if m.get('is_aggressive', False))
            
            hp_ratios = [m.get('hp', 0) / max(m.get('max_hp', 1), 1) for m in monsters]
            features[11] = min(hp_ratios) if hp_ratios else 1.0
            features[12] = max(distances) if distances else 0
            features[13] = sum(1 for d in distances if d <= 10)
            features[14] = min([m.get('hp', 999) for m in monsters])
            features[15] = min(distances) if distances else 999
        
        # Inventory features
        inventory = game_state.get('inventory', [])
        features[16] = len(inventory)
        features[17] = sum(1 for i in inventory if 'Potion' in i.get('name', ''))
        features[18] = sum(1 for i in inventory if i.get('type', '') in ['weapon', 'armor'])
        features[19] = len(inventory) - features[17] - features[18]
        features[20] = sum(i.get('amount', 1) * 100 for i in inventory[:10])  # Rough value
        features[21] = max(100 - len(inventory), 0)
        
        # Social features
        players = game_state.get('nearby_players', [])
        features[22] = len(players)
        features[23] = sum(1 for p in players if p.get('is_party_member', False))
        features[24] = sum(1 for p in players if p.get('guild', ''))
        features[25] = np.mean([p.get('distance', 999) for p in players]) if players else 999
        
        # Temporal features
        import time
        current_hour = datetime.now().hour
        features[26] = current_hour / 24.0  # Normalize to 0-1
        features[27] = (time.time() - session_start) / 3600.0  # Hours
        
        return features

class DataCollector:
    """Collects and prepares training data from game sessions"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        self.feature_extractor = FeatureExtractor()
        logger.info("Data Collector initialized")
        
    async def collect_training_dataset(self, session_id: str, min_samples: int = 100) -> Tuple[np.ndarray, np.ndarray]:
        """Collect training dataset from database"""
        logger.info(f"Collecting training dataset (minimum {min_samples} samples)...")
        
        # Query decisions from database
        async with self.db.conn.execute(
            "SELECT game_state, action_type, outcome, confidence FROM decisions WHERE session_id = ? AND tier_used = 'llm_training' LIMIT ?",
            (session_id, min_samples * 2)  # Get more than needed
        ) as cursor:
            rows = await cursor.fetchall()
            
        if len(rows) < min_samples:
            logger.warning(f"Only {len(rows)} samples available, need {min_samples}")
            return None, None
            
        # Extract features and labels
        X = []
        y = []
        
        for row in rows:
            game_state_json, action_type, outcome, confidence = row
            
            try:
                game_state = json.loads(game_state_json)
                features = self.feature_extractor.extract_features(game_state, 0)
                X.append(features)
                
                # Label encoding: attack=0, skill=1, move=2, item=3, none=4
                label_map = {'attack': 0, 'skill': 1, 'move': 2, 'item': 3, 'none': 4}
                y.append(label_map.get(action_type, 4))
            except Exception as e:
                logger.error(f"Failed to process training sample: {e}")
                continue
                
        X = np.array(X)
        y = np.array(y)
        
        logger.success(f"Collected {len(X)} training samples with {X.shape[1]} features")
        return X, y

data_collector = None  # Initialized in main.py
