"""
Muscle Memory Executor - Layer 4: Instant Actions (Pre-learned Sequences)

Pre-cached action sequences for zero-think instant responses.
Response time: <10ms
"""

from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)


class MuscleMemoryExecutor:
    """
    Pre-learned action sequences with redundancy
    
    Characteristics:
    - Instant execution (<10ms)
    - No computation overhead
    - Always have redundant fallbacks
    - Most common actions cached
    """
    
    def __init__(self):
        """Initialize muscle memory with pre-learned sequences"""
        self.enabled = True
        self.sequences = self._initialize_sequences()
        self.execution_count = 0
    
    def _initialize_sequences(self) -> Dict[str, Dict[str, List[str]]]:
        """Initialize all pre-learned sequences"""
        
        return {
            'basic_attack': {
                'primary': ['target_monster', 'approach', 'attack', 'loot'],
                'fallback_1': ['target_monster', 'ranged_attack', 'loot'],
                'fallback_2': ['target_monster', 'skill_attack', 'loot'],
                'description': 'Basic monster attack and loot'
            },
            
            'heal_self': {
                'primary': ['use_red_potion'],
                'fallback_1': ['use_orange_potion'],
                'fallback_2': ['use_white_potion'],
                'fallback_3': ['sit_and_recover'],
                'description': 'Quick self-healing'
            },
            
            'pickup_loot': {
                'primary': ['move_to_item', 'pickup'],
                'fallback_1': ['teleport_closer', 'pickup'],
                'fallback_2': ['abandon_item'],
                'description': 'Pick up dropped items'
            },
            
            'avoid_danger': {
                'primary': ['stop', 'assess', 'retreat'],
                'fallback_1': ['teleport_away'],
                'fallback_2': ['emergency_logout'],
                'description': 'Quick danger avoidance'
            },
            
            'quick_teleport': {
                'primary': ['use_fly_wing'],
                'fallback_1': ['use_teleport_skill'],
                'fallback_2': ['run_to_portal'],
                'description': 'Fast map teleportation'
            },
            
            'recover_sp': {
                'primary': ['use_blue_potion'],
                'fallback_1': ['use_sp_item'],
                'fallback_2': ['sit_for_sp'],
                'description': 'Quick SP recovery'
            },
            
            'storage_deposit': {
                'primary': ['open_storage', 'deposit_all_except_essentials'],
                'fallback_1': ['open_storage', 'deposit_heavy_items'],
                'fallback_2': ['drop_low_value_items'],
                'description': 'Quick storage deposit'
            },
            
            'emergency_escape': {
                'primary': ['fly_wing'],
                'fallback_1': ['teleport_skill'],
                'fallback_2': ['butterfly_wing_to_save'],
                'fallback_3': ['disconnect'],
                'description': 'Emergency escape sequence'
            },
            
            'buff_self': {
                'primary': ['cast_all_buffs'],
                'fallback_1': ['cast_essential_buffs'],
                'fallback_2': ['skip_buffs'],
                'description': 'Quick self-buffing'
            },
            
            'buy_supplies': {
                'primary': ['open_shop', 'buy_preset_items', 'close_shop'],
                'fallback_1': ['open_shop', 'buy_essentials_only', 'close_shop'],
                'fallback_2': ['skip_shopping'],
                'description': 'Quick supply purchase'
            }
        }
    
    def try_execute(
        self,
        goal,  # TemporalGoal
        game_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Try to execute goal using muscle memory
        
        Only handles basic, known patterns that have cached sequences.
        
        Args:
            goal: Goal to execute
            game_state: Current game state
        
        Returns:
            Execution result if muscle memory handles it, None otherwise
        """
        
        # Check if this goal matches a known pattern
        sequence_id = self._match_goal_to_sequence(goal)
        
        if sequence_id:
            logger.debug(f"Muscle memory executing: {sequence_id}")
            return self._execute_sequence(sequence_id, game_state)
        
        return None
    
    def has_cached_sequence(self, goal) -> bool:
        """Check if goal has a cached sequence"""
        sequence_id = self._match_goal_to_sequence(goal)
        return sequence_id is not None
    
    def _match_goal_to_sequence(self, goal) -> Optional[str]:
        """Match goal to a pre-learned sequence"""
        
        goal_name = goal.name.lower()
        goal_type = goal.goal_type.lower()
        
        # Direct name matches
        if 'attack' in goal_name or goal_name == 'kill_monster':
            return 'basic_attack'
        
        if 'heal' in goal_name and goal_type == 'survival':
            return 'heal_self'
        
        if 'loot' in goal_name or 'pickup' in goal_name:
            return 'pickup_loot'
        
        if 'escape' in goal_name or 'flee' in goal_name:
            return 'emergency_escape'
        
        if 'teleport' in goal_name:
            return 'quick_teleport'
        
        if 'storage' in goal_name or 'store' in goal_name:
            return 'storage_deposit'
        
        if 'buff' in goal_name:
            return 'buff_self'
        
        if 'buy' in goal_name or 'shop' in goal_name:
            return 'buy_supplies'
        
        if 'recover_sp' in goal_name or 'sp' in goal_name:
            return 'recover_sp'
        
        return None
    
    async def _execute_sequence(
        self,
        sequence_id: str,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute pre-learned sequence with automatic fallback
        
        Args:
            sequence_id: ID of sequence to execute
            game_state: Current game state
        
        Returns:
            Execution result
        """
        
        sequence = self.sequences.get(sequence_id)
        if not sequence:
            return {'success': False, 'reason': 'Sequence not found'}
        
        self.execution_count += 1
        
        # Try primary sequence
        result = await self._try_action_sequence(
            sequence['primary'],
            'primary',
            game_state
        )
        
        if result['success']:
            logger.debug(f"[SUCCESS] Muscle memory succeeded: {sequence_id} (primary)")
            return result
        
        # Try fallbacks
        fallback_num = 1
        while f'fallback_{fallback_num}' in sequence:
            fallback_key = f'fallback_{fallback_num}'
            fallback_actions = sequence[fallback_key]
            
            logger.debug(f"Trying {fallback_key} for {sequence_id}")
            
            result = await self._try_action_sequence(
                fallback_actions,
                fallback_key,
                game_state
            )
            
            if result['success']:
                logger.debug(f"[SUCCESS] Muscle memory succeeded: {sequence_id} ({fallback_key})")
                return result
            
            fallback_num += 1
        
        # All sequences failed
        logger.warning(f"[ERROR] All muscle memory sequences failed for: {sequence_id}")
        return {
            'success': False,
            'reason': 'All sequences exhausted',
            'sequence_id': sequence_id
        }
    
    async def _try_action_sequence(
        self,
        actions: List[str],
        plan_name: str,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Try to execute a sequence of actions"""
        
        for action in actions:
            # Simulate action execution
            # In production, this would call actual game actions
            action_result = await self._execute_action(action, game_state)
            
            if not action_result.get('success'):
                return {
                    'success': False,
                    'reason': f"Action '{action}' failed in {plan_name}",
                    'failed_action': action
                }
        
        return {
            'success': True,
            'plan_used': plan_name,
            'actions_executed': len(actions)
        }
    
    async def _execute_action(
        self,
        action: str,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single action (simulated)"""
        
        # Simulate instant action execution
        # In production, this would interface with game client
        
        # Mock high success rate for muscle memory (pre-learned)
        import random
        success = random.random() < 0.95  # 95% success rate
        
        return {
            'success': success,
            'action': action
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get muscle memory execution statistics"""
        
        return {
            'total_executions': self.execution_count,
            'cached_sequences': len(self.sequences),
            'enabled': self.enabled
        }
    
    def add_sequence(
        self,
        sequence_id: str,
        primary: List[str],
        fallbacks: List[List[str]],
        description: str
    ) -> None:
        """
        Add a new learned sequence to muscle memory
        
        Args:
            sequence_id: Unique identifier for sequence
            primary: Primary action sequence
            fallbacks: List of fallback sequences
            description: Human-readable description
        """
        
        sequence = {
            'primary': primary,
            'description': description
        }
        
        for i, fallback in enumerate(fallbacks, 1):
            sequence[f'fallback_{i}'] = fallback
        
        self.sequences[sequence_id] = sequence
        
        logger.info(f"Added muscle memory sequence: {sequence_id}")
