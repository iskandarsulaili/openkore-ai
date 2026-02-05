"""
Social Interaction Handler
Manages all 7 categories of player interactions
"""

from typing import Dict, Any, Optional
from loguru import logger

class InteractionHandler:
    """Handles all types of social interactions"""
    
    def __init__(self, personality_engine_instance, reputation_manager_instance, chat_generator_instance):
        self.personality = personality_engine_instance
        self.reputation = reputation_manager_instance
        self.chat = chat_generator_instance
        logger.info("Interaction Handler initialized with 7 categories")
        
    async def handle_chat(self, character_name: str, player_name: str, 
                         message: str, message_type: str, context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Category 1: Chat interactions"""
        
        # Check if should respond
        reputation = await self.reputation.get_reputation(character_name, player_name)
        
        # Blocked players get no response
        if reputation <= -100:
            logger.debug(f"Ignoring chat from blocked player: {player_name}")
            return None
            
        # Check personality-based response chance
        context['reputation_tier'] = self.reputation.get_tier_name(reputation)
        if not self.personality.should_respond_to_chat(context):
            logger.debug(f"Personality check: Not responding to {player_name}")
            return None
            
        # Generate response
        response = await self.chat.generate_response(message, context)
        
        if response:
            # Update reputation (positive for chat)
            await self.reputation.update_reputation(character_name, player_name, 1, "friendly chat")
            
            return {
                "action": "chat_response",
                "response_text": response,
                "target": player_name,
                "message_type": message_type
            }
            
        return None
        
    async def handle_buff_request(self, character_name: str, player_name: str, 
                                  context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Category 2: Buff interactions"""
        reputation = await self.reputation.get_reputation(character_name, player_name)
        
        # Check if should help
        if not self.personality.should_help_player(reputation):
            return None
            
        # Determine which buff to give (based on job class)
        my_job = context.get('my_job', 'Novice')
        buffs_available = self._get_available_buffs(my_job)
        
        if not buffs_available:
            return None
            
        # Give buff
        await self.reputation.update_reputation(character_name, player_name, 2, "gave buff")
        
        return {
            "action": "give_buff",
            "skill": buffs_available[0],
            "target": player_name
        }
        
    async def handle_trade_request(self, character_name: str, player_name: str, 
                                   trade_offer: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Category 3: Trade interactions"""
        reputation = await self.reputation.get_reputation(character_name, player_name)
        
        # Suspicious/blocked players - decline trade
        if reputation < 0:
            logger.warning(f"Declining trade from suspicious player: {player_name}")
            return {"action": "decline_trade", "reason": "Low reputation"}
            
        # Evaluate trade offer (simplified)
        my_zeny = trade_offer.get('my_zeny_offer', 0)
        their_zeny = trade_offer.get('their_zeny_offer', 0)
        
        # Simple fairness check
        if my_zeny > 0 and their_zeny == 0:
            # They want my items for free - decline
            await self.reputation.update_reputation(character_name, player_name, -5, "unfair trade attempt")
            return {"action": "decline_trade", "reason": "Unfair trade"}
            
        # Accept reasonable trades
        if reputation >= 25 or (my_zeny == 0 and their_zeny > 0):
            await self.reputation.update_reputation(character_name, player_name, 3, "completed trade")
            return {"action": "accept_trade"}
            
        return {"action": "decline_trade", "reason": "Uncertain trade value"}
        
    async def handle_party_invite(self, character_name: str, player_name: str, 
                                  context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Category 5: Party interactions"""
        reputation = await self.reputation.get_reputation(character_name, player_name)
        
        # Check caution level
        if self.personality.traits['caution'] > 0.7 and reputation < 25:
            logger.info(f"Declining party invite from unknown player (cautious personality)")
            return {"action": "decline_party"}
            
        # Accept from friendly+ players
        if reputation >= 50:
            await self.reputation.update_reputation(character_name, player_name, 5, "joined party")
            return {"action": "accept_party", "message": "Thanks for the invite!"}
            
        # Accept from acquaintances if not too cautious
        if reputation >= 25 and self.personality.traits['friendliness'] > 0.5:
            await self.reputation.update_reputation(character_name, player_name, 3, "joined party")
            return {"action": "accept_party"}
            
        return {"action": "decline_party", "reason": "Prefer to solo for now"}
        
    async def handle_duel_request(self, character_name: str, player_name: str, 
                                  context: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Category 4: Duel interactions"""
        reputation = await self.reputation.get_reputation(character_name, player_name)
        my_level = context.get('my_level', 1)
        their_level = context.get('their_level', 1)
        
        # Check caution - cautious personalities avoid PvP
        if self.personality.traits['caution'] > 0.7:
            return {"action": "decline_duel", "reason": "Not interested in PvP"}
            
        # Level difference check
        if abs(my_level - their_level) > 10:
            return {"action": "decline_duel", "reason": "Level difference too large"}
            
        # Only duel friendly+ players
        if reputation >= 50:
            return {"action": "accept_duel", "message": "Let's do this!"}
            
        return {"action": "decline_duel", "reason": "Only duel friends"}
        
    def _get_available_buffs(self, job_class: str) -> list:
        """Get buffs available for job class"""
        buff_map = {
            "Acolyte": ["Blessing", "Increase AGI"],
            "Priest": ["Blessing", "Increase AGI", "Kyrie Eleison"],
            "Sage": ["Endow"],
            "Wizard": ["Magic Strings"]
        }
        return buff_map.get(job_class, [])

interaction_handler = None  # Initialized in main.py
