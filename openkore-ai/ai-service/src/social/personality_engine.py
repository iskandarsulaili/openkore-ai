"""
Personality Engine
Manages 8 personality traits to create human-like behavior
"""

from typing import Dict, Any
from loguru import logger
import yaml
from pathlib import Path

class PersonalityEngine:
    """Manages AI personality traits"""
    
    DEFAULT_TRAITS = {
        'chattiness': 0.5,
        'friendliness': 0.7,
        'helpfulness': 0.6,
        'curiosity': 0.5,
        'caution': 0.6,
        'formality': 0.4,
        'humor': 0.5,
        'patience': 0.7
    }
    
    def __init__(self, config_path: str = "../../../config/plugin.yaml"):
        self.traits = self.DEFAULT_TRAITS.copy()
        self._load_config(config_path)
        logger.info(f"Personality Engine initialized with traits: {self.traits}")
        
    def _load_config(self, config_path: str):
        """Load personality traits from config"""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config = yaml.safe_load(f)
                    if 'personality' in config:
                        self.traits.update(config['personality'])
                        logger.success("Loaded personality traits from config")
        except Exception as e:
            logger.warning(f"Could not load config, using defaults: {e}")
            
    def should_respond_to_chat(self, context: Dict[str, Any]) -> bool:
        """Determine if AI should respond to chat message"""
        import random
        
        # Chattiness determines response rate
        base_chance = self.traits['chattiness']
        
        # Adjust based on context
        if context.get('is_party_member', False):
            base_chance += 0.2  # More chatty with party
        if context.get('is_guild_member', False):
            base_chance += 0.1  # Slightly more chatty with guild
        if context.get('is_whisper', False):
            base_chance += 0.3  # Much more likely to respond to direct messages
            
        return random.random() < min(base_chance, 1.0)
        
    def should_help_player(self, player_reputation: int) -> bool:
        """Determine if AI should help based on reputation and helpfulness"""
        import random
        
        # Base helpfulness
        help_chance = self.traits['helpfulness']
        
        # Adjust based on reputation
        if player_reputation >= 50:  # Friendly
            help_chance += 0.3
        elif player_reputation >= 25:  # Acquaintance
            help_chance += 0.1
        elif player_reputation < 0:  # Suspicious/Blocked
            help_chance = 0.0
            
        return random.random() < min(help_chance, 1.0)
        
    def get_conversation_style(self) -> str:
        """Get conversation style based on formality and humor"""
        if self.traits['formality'] > 0.7:
            return "formal"
        elif self.traits['formality'] < 0.3:
            if self.traits['humor'] > 0.6:
                return "casual_humorous"
            else:
                return "casual"
        else:
            return "neutral"
            
    def get_emoji_usage_rate(self) -> float:
        """How often to use emojis (based on formality and humor)"""
        # Less formal + more humor = more emojis
        return (1.0 - self.traits['formality']) * self.traits['humor']

personality_engine = PersonalityEngine()
