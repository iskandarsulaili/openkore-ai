"""
Reflex Goal Trigger - Layer 3: Emergency Response (Rule-Based)

Rule-based emergency goal triggers with built-in fallbacks for survival-critical situations.
Response time: 10-100ms
"""

from typing import Dict, List, Optional, Any, Callable
import logging

from .goal_model import TemporalGoal, GoalPriority, create_emergency_heal_goal

logger = logging.getLogger(__name__)


class ReflexGoalTrigger:
    """
    Rule-based emergency goal triggers with built-in fallbacks
    
    Each reflex has:
    - Trigger condition (when to activate)
    - Primary action (Plan A)
    - 2+ fallback actions (Plans B, C)
    
    Response time: <100ms
    """
    
    def __init__(self):
        """Initialize reflex triggers"""
        self.enabled = True
        self.reflexes = self._initialize_reflexes()
    
    def _initialize_reflexes(self) -> Dict[str, Dict[str, Any]]:
        """Initialize all reflex responses"""
        
        return {
            'emergency_heal': {
                'name': 'Emergency Healing',
                'trigger': lambda state: state.get('hp_percent', 100) < 15,
                'priority': GoalPriority.CRITICAL,
                'plans': [
                    {
                        'name': 'Plan A: Best Healing Item',
                        'action': self._use_best_healing_item,
                        'description': 'Use most effective healing item'
                    },
                    {
                        'name': 'Plan B: Sit and Recover',
                        'action': self._sit_and_recover,
                        'description': 'Sit down to recover HP naturally'
                    },
                    {
                        'name': 'Plan C: Emergency Teleport',
                        'action': self._teleport_to_safety,
                        'description': 'Teleport to safe location immediately'
                    }
                ]
            },
            
            'critical_escape': {
                'name': 'Critical Escape',
                'trigger': lambda state: state.get('aggressive_monster_count', 0) > 10,
                'priority': GoalPriority.CRITICAL,
                'plans': [
                    {
                        'name': 'Plan A: Fly Wing',
                        'action': self._use_fly_wing,
                        'description': 'Use Fly Wing to teleport randomly'
                    },
                    {
                        'name': 'Plan B: Teleport Skill',
                        'action': self._use_teleport_skill,
                        'description': 'Use Teleport skill if available'
                    },
                    {
                        'name': 'Plan C: Run to Safe Zone',
                        'action': self._run_to_nearest_safe_zone,
                        'description': 'Run to nearest safe zone'
                    }
                ]
            },
            
            'overweight': {
                'name': 'Overweight Management',
                'trigger': lambda state: state.get('weight_percent', 0) > 90,
                'priority': GoalPriority.HIGH,
                'plans': [
                    {
                        'name': 'Plan A: Store Items',
                        'action': self._store_items,
                        'description': 'Store items in Kafra storage'
                    },
                    {
                        'name': 'Plan B: Drop Low Value Items',
                        'action': self._drop_low_value_items,
                        'description': 'Drop items worth less than 100z'
                    },
                    {
                        'name': 'Plan C: Emergency Drop',
                        'action': self._emergency_drop,
                        'description': 'Drop items to reduce weight immediately'
                    }
                ]
            },
            
            'low_sp': {
                'name': 'Low SP Recovery',
                'trigger': lambda state: state.get('sp_percent', 100) < 10,
                'priority': GoalPriority.HIGH,
                'plans': [
                    {
                        'name': 'Plan A: SP Items',
                        'action': self._use_sp_items,
                        'description': 'Use SP recovery items'
                    },
                    {
                        'name': 'Plan B: Return to Town',
                        'action': self._return_to_town,
                        'description': 'Return to town for full recovery'
                    },
                    {
                        'name': 'Plan C: Sit Until Full',
                        'action': self._sit_until_full_sp,
                        'description': 'Sit and wait for natural SP recovery'
                    }
                ]
            },
            
            'equipment_broken': {
                'name': 'Equipment Repair',
                'trigger': lambda state: state.get('equipment_broken', False),
                'priority': GoalPriority.HIGH,
                'plans': [
                    {
                        'name': 'Plan A: Visit Repair NPC',
                        'action': self._repair_equipment,
                        'description': 'Go to repair NPC'
                    },
                    {
                        'name': 'Plan B: Switch Equipment',
                        'action': self._switch_to_backup_equipment,
                        'description': 'Use backup equipment set'
                    },
                    {
                        'name': 'Plan C: Return to Town',
                        'action': self._return_to_town,
                        'description': 'Return to town for repairs'
                    }
                ]
            },
            
            'status_ailment': {
                'name': 'Status Ailment Recovery',
                'trigger': lambda state: len(state.get('debuffs', [])) > 0,
                'priority': GoalPriority.HIGH,
                'plans': [
                    {
                        'name': 'Plan A: Use Status Recovery',
                        'action': self._use_status_recovery,
                        'description': 'Use appropriate status recovery item'
                    },
                    {
                        'name': 'Plan B: Wait It Out',
                        'action': self._wait_for_status_end,
                        'description': 'Wait safely for status to expire'
                    },
                    {
                        'name': 'Plan C: Return to Town',
                        'action': self._return_to_town,
                        'description': 'Return to town for healing'
                    }
                ]
            }
        }
    
    def check_and_trigger(self, game_state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check all reflex triggers and activate if needed
        
        Args:
            game_state: Current game state
        
        Returns:
            Reflex action to execute, or None if no reflex triggered
        """
        
        # Check all reflexes in priority order
        for reflex_id, reflex in sorted(
            self.reflexes.items(),
            key=lambda x: x[1]['priority'].value,
            reverse=True
        ):
            if reflex['trigger'](game_state):
                logger.warning(f"🚨 REFLEX TRIGGERED: {reflex['name']}")
                return {
                    'reflex_id': reflex_id,
                    'reflex_name': reflex['name'],
                    'priority': reflex['priority'],
                    'plans': reflex['plans']
                }
        
        return None
    
    async def execute_reflex(
        self,
        reflex_action: Dict[str, Any],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute reflex with automatic fallback
        
        Args:
            reflex_action: Reflex to execute
            game_state: Current game state
        
        Returns:
            Execution result
        """
        
        logger.info(f"Executing reflex: {reflex_action['reflex_name']}")
        
        plans = reflex_action['plans']
        
        # Try each plan in sequence
        for i, plan in enumerate(plans):
            plan_letter = chr(65 + i)  # A, B, C...
            logger.info(f"Trying Plan {plan_letter}: {plan['name']}")
            
            try:
                result = await plan['action'](game_state)
                
                if result.get('success'):
                    logger.info(f"✅ Reflex succeeded with Plan {plan_letter}")
                    return {
                        'success': True,
                        'plan_used': plan['name'],
                        'result': result
                    }
                else:
                    logger.warning(f"❌ Plan {plan_letter} failed: {result.get('reason')}")
                    continue
                    
            except Exception as e:
                logger.error(f"Exception in Plan {plan_letter}: {str(e)}")
                continue
        
        # All plans failed
        logger.error(f"All reflex plans failed for: {reflex_action['reflex_name']}")
        return {
            'success': False,
            'reason': 'All reflex plans exhausted'
        }
    
    async def try_execute(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Try to execute goal using reflex layer
        
        Only handles emergency/survival goals that match reflex triggers.
        
        Args:
            goal: Goal to execute
            game_state: Current game state
        
        Returns:
            Execution result if reflex handles it, None otherwise
        """
        
        # Check if this is an emergency that reflexes can handle
        reflex_action = self.check_and_trigger(game_state)
        
        if reflex_action and goal.priority == GoalPriority.CRITICAL:
            return await self.execute_reflex(reflex_action, game_state)
        
        return None
    
    # ===== Reflex Actions =====
    
    async def _use_best_healing_item(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Use best available healing item"""
        logger.info("Using best healing item")
        # Simulate healing item use
        return {'success': True, 'hp_restored': 50}
    
    async def _sit_and_recover(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Sit down to recover HP naturally"""
        logger.info("Sitting to recover HP")
        return {'success': True, 'action': 'sit'}
    
    async def _teleport_to_safety(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Emergency teleport to safe location"""
        logger.info("Emergency teleporting to safety")
        return {'success': True, 'destination': 'safe_zone'}
    
    async def _use_fly_wing(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Use Fly Wing item"""
        logger.info("Using Fly Wing")
        has_fly_wing = game_state.get('inventory', {}).get('fly_wing', 0) > 0
        if has_fly_wing:
            return {'success': True, 'teleported': True}
        return {'success': False, 'reason': 'No Fly Wing available'}
    
    async def _use_teleport_skill(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Use Teleport skill"""
        logger.info("Using Teleport skill")
        has_skill = 'teleport' in game_state.get('skills', [])
        if has_skill:
            return {'success': True, 'teleported': True}
        return {'success': False, 'reason': 'Teleport skill not available'}
    
    async def _run_to_nearest_safe_zone(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Run to nearest safe zone"""
        logger.info("Running to safe zone")
        return {'success': True, 'action': 'run_to_safe_zone'}
    
    async def _store_items(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Store items in Kafra storage"""
        logger.info("Storing items")
        return {'success': True, 'items_stored': 20}
    
    async def _drop_low_value_items(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Drop items worth less than 100z"""
        logger.info("Dropping low value items")
        return {'success': True, 'items_dropped': 10}
    
    async def _emergency_drop(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Emergency drop to reduce weight"""
        logger.info("Emergency dropping items")
        return {'success': True, 'weight_reduced': 30}
    
    async def _use_sp_items(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Use SP recovery items"""
        logger.info("Using SP items")
        return {'success': True, 'sp_restored': 40}
    
    async def _return_to_town(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Return to town"""
        logger.info("Returning to town")
        return {'success': True, 'location': 'town'}
    
    async def _sit_until_full_sp(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Sit until SP is full"""
        logger.info("Sitting until SP is full")
        return {'success': True, 'action': 'sit_for_sp'}
    
    async def _repair_equipment(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Repair equipment at NPC"""
        logger.info("Repairing equipment")
        return {'success': True, 'repaired': True}
    
    async def _switch_to_backup_equipment(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Switch to backup equipment"""
        logger.info("Switching to backup equipment")
        return {'success': True, 'equipment_switched': True}
    
    async def _use_status_recovery(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Use status recovery item"""
        logger.info("Using status recovery")
        return {'success': True, 'status_cleared': True}
    
    async def _wait_for_status_end(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Wait for status ailment to expire"""
        logger.info("Waiting for status to end")
        return {'success': True, 'action': 'wait'}
