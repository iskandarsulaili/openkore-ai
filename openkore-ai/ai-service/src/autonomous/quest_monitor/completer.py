"""
Quest Completer
Executes quest completion (turn-in) process
Handles navigation and NPC interaction
"""

import asyncio
from pathlib import Path
from typing import Dict, Optional, Any
from loguru import logger
import threading


class QuestCompleter:
    """
    Executes quest completion process
    Navigates to turn-in NPC and completes dialogue
    """
    
    def __init__(self, openkore_client):
        """
        Initialize quest completer
        
        Args:
            openkore_client: OpenKore HTTP client (REST API) for commands
        """
        self.openkore = openkore_client
        self._lock = threading.RLock()
        self.completion_history: List[Dict] = []
        
        logger.info("QuestCompleter initialized")
    
    async def complete_quest(
        self,
        quest_info: Dict[str, Any],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete a quest by turning it in
        
        Args:
            quest_info: Quest information including turn-in details
            game_state: Current game state
            
        Returns:
            Dictionary with completion result
        """
        with self._lock:
            quest_id = quest_info.get('quest_id')
            quest_name = quest_info.get('name', 'Unknown Quest')
            
            logger.info(f"Starting quest completion: {quest_name}")
            
            try:
                # Step 1: Navigate to turn-in location
                turn_in_map = quest_info.get('turn_in_map')
                turn_in_npc = quest_info.get('turn_in_npc')
                
                if not turn_in_npc:
                    logger.warning(f"No turn-in NPC specified for quest: {quest_name}")
                    return {
                        'success': False,
                        'error': "Missing turn-in NPC information"
                    }
                
                logger.info(f"Step 1: Navigating to {turn_in_npc}")
                nav_success = await self._navigate_to_npc(turn_in_map, turn_in_npc)
                
                if not nav_success:
                    return {
                        'success': False,
                        'error': "Navigation to NPC failed",
                        'step': 'navigation'
                    }
                
                # Step 2: Talk to NPC
                logger.info(f"Step 2: Talking to {turn_in_npc}")
                talk_success = await self._talk_to_npc(turn_in_npc)
                
                if not talk_success:
                    return {
                        'success': False,
                        'error': "Failed to initiate NPC dialogue",
                        'step': 'dialogue_start'
                    }
                
                # Step 3: Complete quest dialogue
                logger.info("Step 3: Completing quest dialogue")
                dialogue_success = await self._complete_quest_dialogue(quest_info)
                
                if not dialogue_success:
                    return {
                        'success': False,
                        'error': "Quest dialogue completion failed",
                        'step': 'dialogue_completion'
                    }
                
                # Step 4: Verify quest completion
                await asyncio.sleep(2)
                verify_success = await self._verify_quest_completion(quest_id)
                
                if verify_success:
                    logger.success(f"Quest completed successfully: {quest_name}")
                    
                    # Record completion
                    self.completion_history.append({
                        'quest_id': quest_id,
                        'quest_name': quest_name,
                        'completed_at': datetime.now(),
                        'quest_type': quest_info.get('type')
                    })
                    
                    return {
                        'success': True,
                        'quest_id': quest_id,
                        'quest_name': quest_name
                    }
                else:
                    return {
                        'success': False,
                        'error': "Quest completion verification failed",
                        'step': 'verification'
                    }
                
            except Exception as e:
                logger.error(f"Quest completion error: {e}")
                return {
                    'success': False,
                    'error': str(e),
                    'step': 'exception'
                }
    
    async def _navigate_to_npc(self, map_name: Optional[str], npc_name: str) -> bool:
        """
        Navigate to NPC location
        
        Args:
            map_name: Target map (optional if NPC is on current map)
            npc_name: NPC name or pattern
            
        Returns:
            True if navigation successful
        """
        try:
            if map_name:
                # Get current map
                current_state = await self.openkore.get_game_state()
                current_map = current_state.get('character', {}).get('map', '')
                
                # Navigate to map if different
                if current_map != map_name:
                    logger.info(f"Navigating to map: {map_name}")
                    await self.openkore.send_command(f"move {map_name}")
                    
                    # Wait for map change
                    for i in range(30):
                        await asyncio.sleep(1)
                        current_state = await self.openkore.get_game_state()
                        if current_state.get('character', {}).get('map') == map_name:
                            break
            
            # Navigate to NPC on current map
            logger.info(f"Moving to NPC: {npc_name}")
            await self.openkore.send_command(f"move {npc_name}")
            await asyncio.sleep(2)
            
            return True
            
        except Exception as e:
            logger.error(f"Navigation error: {e}")
            return False
    
    async def _talk_to_npc(self, npc_name: str) -> bool:
        """
        Initiate dialogue with NPC
        
        Args:
            npc_name: NPC name or pattern
            
        Returns:
            True if dialogue initiated
        """
        try:
            # Send talk command
            await self.openkore.send_command(f"talk {npc_name}")
            await asyncio.sleep(1.5)
            
            return True
            
        except Exception as e:
            logger.error(f"Talk command error: {e}")
            return False
    
    async def _complete_quest_dialogue(self, quest_info: Dict) -> bool:
        """
        Complete quest turn-in dialogue
        
        Args:
            quest_info: Quest information
            
        Returns:
            True if dialogue completed
        """
        try:
            quest_type = quest_info.get('type', 'unknown')
            
            # Standard quest completion dialogue pattern:
            # 1. Select "Complete quest" / "Turn in"
            # 2. Confirm completion
            # 3. Receive rewards
            
            responses = [
                "talk resp 0",  # Select quest completion option
                "talk resp 0",  # Confirm
                "talk cont"     # Continue through reward dialogue
            ]
            
            for response in responses:
                await self.openkore.send_command(response)
                await asyncio.sleep(1)
            
            logger.info("Quest dialogue sequence completed")
            return True
            
        except Exception as e:
            logger.error(f"Dialogue completion error: {e}")
            return False
    
    async def _verify_quest_completion(self, quest_id: str) -> bool:
        """
        Verify quest was completed successfully
        
        Args:
            quest_id: Quest identifier
            
        Returns:
            True if quest no longer in active list
        """
        try:
            current_state = await self.openkore.get_game_state()
            
            if current_state:
                active_quests = current_state.get('quests', {}).get('active', [])
                
                # Check if quest is no longer in active list
                for quest in active_quests:
                    if quest.get('quest_id') == quest_id:
                        logger.warning(f"Quest {quest_id} still in active list")
                        return False
                
                logger.success(f"Quest {quest_id} verified as completed")
                return True
            
            logger.warning("Could not get game state for verification")
            return False
            
        except Exception as e:
            logger.error(f"Verification error: {e}")
            return False
    
    async def complete_quest_chain(
        self,
        quest_chain: List[Dict],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Complete multiple quests in sequence (quest chain)
        
        Args:
            quest_chain: List of quests to complete in order
            game_state: Current game state
            
        Returns:
            Dictionary with chain completion results
        """
        results = []
        total_success = 0
        
        for quest_info in quest_chain:
            result = await self.complete_quest(quest_info, game_state)
            results.append(result)
            
            if result.get('success'):
                total_success += 1
            else:
                # Stop chain on first failure
                logger.warning(f"Quest chain broken at: {quest_info.get('name')}")
                break
            
            # Delay between quests
            await asyncio.sleep(3)
        
        return {
            'total_quests': len(quest_chain),
            'completed': total_success,
            'success_rate': (total_success / len(quest_chain)) * 100 if quest_chain else 0,
            'results': results
        }
    
    def get_completion_statistics(self) -> Dict:
        """Get quest completion statistics"""
        with self._lock:
            if not self.completion_history:
                return {
                    'total_completed': 0,
                    'by_type': {}
                }
            
            by_type = {}
            for completion in self.completion_history:
                quest_type = completion.get('quest_type', 'unknown')
                by_type[quest_type] = by_type.get(quest_type, 0) + 1
            
            return {
                'total_completed': len(self.completion_history),
                'by_type': by_type,
                'recent_completions': self.completion_history[-10:]
            }
