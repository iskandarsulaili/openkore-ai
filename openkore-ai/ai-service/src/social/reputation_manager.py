"""
Player Reputation Manager
Tracks and manages relationships with other players
"""

from typing import Dict, Any, Optional
from loguru import logger
import time
import json

class ReputationTier:
    """Reputation tier thresholds"""
    BLOCKED = -100
    SUSPICIOUS = -50
    NEUTRAL = 0
    ACQUAINTANCE = 25
    FRIENDLY = 50
    TRUSTED = 75
    WHITELISTED = 100

class ReputationManager:
    """Manages player reputation tracking"""
    
    def __init__(self, db_instance):
        self.db = db_instance
        logger.info("Reputation Manager initialized")
        
    async def get_reputation(self, character_name: str, player_name: str) -> int:
        """Get reputation score for a player"""
        async with self.db.conn.execute(
            "SELECT reputation_score FROM player_reputation WHERE character_name = ? AND player_name = ?",
            (character_name, player_name)
        ) as cursor:
            row = await cursor.fetchone()
            
        return row[0] if row else ReputationTier.NEUTRAL
        
    async def update_reputation(self, character_name: str, player_name: str, 
                               change: int, reason: str):
        """Update player reputation"""
        current_rep = await self.get_reputation(character_name, player_name)
        new_rep = max(min(current_rep + change, 100), -100)  # Clamp to [-100, 100]
        
        # Get current notes or create new
        async with self.db.conn.execute(
            "SELECT notes, interaction_count FROM player_reputation WHERE character_name = ? AND player_name = ?",
            (character_name, player_name)
        ) as cursor:
            row = await cursor.fetchone()
            
        if row:
            notes_str, interaction_count = row
            notes = json.loads(notes_str) if notes_str else []
            interaction_count += 1
        else:
            notes = []
            interaction_count = 1
            
        # Add new note
        notes.append({
            'timestamp': int(time.time()),
            'change': change,
            'reason': reason,
            'new_reputation': new_rep
        })
        
        # Keep only last 50 notes
        notes = notes[-50:]
        
        # Upsert reputation
        async with self.db.conn.execute(
            """INSERT INTO player_reputation (character_name, player_name, reputation_score, interaction_count, last_interaction, notes)
               VALUES (?, ?, ?, ?, ?, ?)
               ON CONFLICT(character_name, player_name) DO UPDATE SET
               reputation_score = ?, interaction_count = ?, last_interaction = ?, notes = ?""",
            (character_name, player_name, new_rep, interaction_count, int(time.time()), json.dumps(notes),
             new_rep, interaction_count, int(time.time()), json.dumps(notes))
        ) as cursor:
            await self.db.conn.commit()
            
        logger.info(f"Updated reputation for {player_name}: {current_rep} -> {new_rep} ({reason})")
        return new_rep
        
    def get_tier_name(self, reputation: int) -> str:
        """Get tier name from reputation score"""
        if reputation >= ReputationTier.WHITELISTED:
            return "Whitelisted"
        elif reputation >= ReputationTier.TRUSTED:
            return "Trusted"
        elif reputation >= ReputationTier.FRIENDLY:
            return "Friendly"
        elif reputation >= ReputationTier.ACQUAINTANCE:
            return "Acquaintance"
        elif reputation >= ReputationTier.NEUTRAL:
            return "Neutral"
        elif reputation >= ReputationTier.SUSPICIOUS:
            return "Suspicious"
        else:
            return "Blocked"
            
    async def should_interact(self, character_name: str, player_name: str, 
                            interaction_type: str) -> bool:
        """Determine if AI should interact with player"""
        reputation = await self.get_reputation(character_name, player_name)
        
        # Blocked players - no interaction
        if reputation <= ReputationTier.BLOCKED:
            return False
            
        # Suspicious players - limited interaction
        if reputation <= ReputationTier.SUSPICIOUS:
            return interaction_type in ['chat']  # Only allow chat
            
        # All other tiers - allow all interactions
        return True

reputation_manager = None  # Initialized in main.py
