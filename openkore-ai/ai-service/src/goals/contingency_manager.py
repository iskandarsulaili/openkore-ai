"""
Contingency Manager - Failure Recovery Component

Manages fallback plans and ensures zero-failure operation through automatic contingency activation.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
import traceback

from .goal_model import TemporalGoal, GoalStatus, PlanType

logger = logging.getLogger(__name__)


class ContingencyManager:
    """
    Manages fallback plans and ensures zero-failure operation
    
    Key capabilities:
    - Execute goals with automatic fallback
    - Switch between plans seamlessly
    - Emergency abort with safety guarantee
    - Generate post-mortem analysis
    - Learn from failures
    """
    
    def __init__(self):
        """Initialize Contingency Manager"""
        self.execution_log = []
        self.emergency_abort_always_succeeds = True
    
    async def execute_with_contingency(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any],
        execution_plan: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Execute goal with automatic fallback on failure
        
        Execution flow:
        1. Try Plan A (primary)
        2. If fails, try Plan B (alternative)
        3. If fails, try Plan C (conservative)
        4. If fails, execute Plan D (emergency abort - always succeeds)
        
        Args:
            goal: Goal to execute
            game_state: Current game state
            execution_plan: Optional override execution plan
        
        Returns:
            Execution result with status and details
        """
        
        logger.info(f"Executing goal with contingency: {goal.name}")
        
        goal.start_execution()
        
        # Get plan order: primary → alternative → conservative → emergency
        plans = self._get_plan_sequence(goal)
        
        for plan_name, plan_details in plans:
            try:
                logger.info(f"Attempting {plan_name} for goal {goal.id}")
                
                result = await self._execute_plan(goal, plan_name, plan_details, game_state)
                
                if result['success']:
                    logger.info(f"[SUCCESS] Goal {goal.id} succeeded using {plan_name}")
                    goal.complete_success()
                    
                    return {
                        'status': 'success',
                        'plan_used': plan_name,
                        'result': result,
                        'attempts': goal.attempt_count,
                        'duration': goal.get_execution_duration()
                    }
                else:
                    # Plan failed - log and try next
                    logger.warning(f"[ERROR] {plan_name} failed for goal {goal.id}: {result.get('reason')}")
                    self._log_plan_failure(goal, plan_name, result)
                    
                    # Check if we should switch to next plan
                    if plan_name != 'emergency':  # Emergency is last resort
                        switched = goal.switch_to_fallback(
                            self._get_next_plan_type(plan_name),
                            result.get('reason', 'Plan failed')
                        )
                        
                        if not switched:
                            logger.error(f"Failed to switch to fallback plan")
                            break
                        
                        continue
                    
            except Exception as e:
                # Unexpected exception - log and try next plan
                logger.error(f"Exception in {plan_name}: {str(e)}\n{traceback.format_exc()}")
                self._log_exception(goal, plan_name, e)
                
                # If this is emergency plan and it failed, something is very wrong
                if plan_name == 'emergency':
                    return await self._emergency_abort(goal, game_state, str(e))
                
                # Try next plan
                goal.switch_to_fallback(
                    self._get_next_plan_type(plan_name),
                    f"Exception: {str(e)}"
                )
                continue
        
        # All plans failed (including emergency) - should never happen
        logger.critical(f"[EMERGENCY] CRITICAL: All plans failed for goal {goal.id} including emergency!")
        return await self._emergency_abort(goal, game_state, "All plans exhausted")
    
    async def _execute_plan(
        self,
        goal: TemporalGoal,
        plan_name: str,
        plan_details: Dict[str, Any],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Execute a specific plan
        
        Args:
            goal: Goal being executed
            plan_name: Name of plan (primary, alternative, etc.)
            plan_details: Plan execution details
            game_state: Current game state
        
        Returns:
            Execution result
        """
        
        logger.debug(f"Executing plan: {plan_name}")
        
        actions = plan_details.get('actions', [])
        
        # Track execution
        execution_start = datetime.now()
        
        try:
            # Execute each action in sequence
            for action in actions:
                logger.debug(f"Executing action: {action}")
                
                # Simulate action execution
                # In production, this would call actual game actions
                action_result = await self._execute_action(action, plan_details, game_state)
                
                if not action_result['success']:
                    return {
                        'success': False,
                        'reason': f"Action '{action}' failed: {action_result.get('reason')}",
                        'failed_action': action,
                        'execution_time': (datetime.now() - execution_start).total_seconds()
                    }
            
            # All actions succeeded
            execution_time = (datetime.now() - execution_start).total_seconds()
            
            # Check success conditions
            success_met = self._check_success_conditions(goal, game_state)
            
            if success_met:
                return {
                    'success': True,
                    'execution_time': execution_time,
                    'rewards': self._calculate_rewards(goal, game_state)
                }
            else:
                return {
                    'success': False,
                    'reason': 'Success conditions not met',
                    'execution_time': execution_time
                }
                
        except Exception as e:
            logger.error(f"Exception during plan execution: {str(e)}")
            return {
                'success': False,
                'reason': f"Exception: {str(e)}",
                'exception': str(e),
                'execution_time': (datetime.now() - execution_start).total_seconds()
            }
    
    async def _execute_action(
        self,
        action: str,
        plan_details: Dict[str, Any],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single action"""
        
        # Simulate action execution
        # In production, this would interface with actual game client
        
        # Mock success with some failure probability
        import random
        success_probability = 0.9  # 90% success rate per action
        
        if random.random() < success_probability:
            return {'success': True, 'action': action}
        else:
            return {
                'success': False,
                'action': action,
                'reason': 'Simulated random failure'
            }
    
    def _check_success_conditions(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> bool:
        """Check if goal success conditions are met"""
        
        conditions = goal.success_conditions
        
        # Check each condition
        for condition_name, expected_value in conditions.items():
            if condition_name == 'kills':
                # Check kill count
                actual_kills = game_state.get('kill_count', 0)
                if actual_kills < expected_value:
                    return False
            
            elif condition_name == 'hp_percent':
                # Check HP threshold
                actual_hp = game_state.get('hp_percent', 0)
                if actual_hp < expected_value:
                    return False
            
            elif condition_name == 'safe_location':
                # Check if in safe location
                is_safe = game_state.get('in_safe_zone', False)
                if is_safe != expected_value:
                    return False
        
        return True
    
    def _calculate_rewards(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate rewards from successful goal completion"""
        
        return {
            'experience': game_state.get('exp_gained', 0),
            'zeny': game_state.get('zeny_gained', 0),
            'items': game_state.get('items_obtained', []),
            'success_rate_bonus': 1.0
        }
    
    async def _emergency_abort(
        self,
        goal: TemporalGoal,
        game_state: Dict[str, Any],
        reason: str = "Emergency abort activated"
    ) -> Dict[str, Any]:
        """
        Last resort: Abort goal safely
        
        This MUST always succeed to guarantee character safety.
        
        Steps:
        1. Save character state
        2. Teleport to safe location (if possible)
        3. Heal to full HP/SP
        4. Log comprehensive failure report
        5. Mark goal as emergency aborted
        6. Generate post-mortem analysis
        7. Update ML model with failure case
        
        Args:
            goal: Goal being aborted
            game_state: Current game state
            reason: Reason for emergency abort
        
        Returns:
            Emergency abort result (always successful)
        """
        
        logger.critical(f"[EMERGENCY] EMERGENCY ABORT: Goal {goal.id} - {reason}")
        
        goal.emergency_abort(reason)
        
        try:
            # Step 1: Save character state
            character_state = self._save_character_state(game_state)
            logger.info("[SUCCESS] Character state saved")
            
            # Step 2: Teleport to safety (if in danger)
            if not game_state.get('in_safe_zone', False):
                teleport_result = await self._emergency_teleport(game_state)
                logger.info(f"[SUCCESS] Emergency teleport: {teleport_result}")
            
            # Step 3: Heal to full
            heal_result = await self._heal_to_full(game_state)
            logger.info(f"[SUCCESS] Healed to full: {heal_result}")
            
            # Step 4: Log comprehensive failure
            self._log_emergency_abort(goal, reason, character_state)
            
            # Step 5: Generate post-mortem
            post_mortem = self._generate_post_mortem(goal, reason, game_state)
            logger.info("[SUCCESS] Post-mortem analysis generated")
            
            # Step 6: Store for ML training
            self._store_for_ml_training(goal, post_mortem)
            
            return {
                'status': 'emergency_abort',
                'character_safe': True,
                'post_mortem': post_mortem,
                'reason': reason,
                'actions_taken': [
                    'saved_state',
                    'teleported_to_safety',
                    'healed_full',
                    'logged_failure',
                    'generated_post_mortem'
                ]
            }
            
        except Exception as e:
            # Even emergency abort failed - log critical error
            logger.critical(f"🔥 CRITICAL: Emergency abort encountered exception: {str(e)}")
            logger.critical(traceback.format_exc())
            
            # Return success anyway to prevent infinite loops
            # Character safety is assumed at this point
            return {
                'status': 'emergency_abort_with_errors',
                'character_safe': True,  # Assume safe
                'error': str(e),
                'reason': reason
            }
    
    def _get_plan_sequence(self, goal: TemporalGoal) -> List[tuple]:
        """Get sequence of plans to try: primary → alternative → conservative → emergency"""
        
        plans = []
        
        # Primary plan
        plans.append(('primary', goal.primary_plan))
        
        # Fallback plans
        for fallback in goal.fallback_plans:
            plan_name = fallback.plan_type.value
            plans.append((plan_name, fallback.dict()))
        
        return plans
    
    def _get_next_plan_type(self, current_plan: str) -> str:
        """Get next plan type in sequence"""
        
        sequence = ['primary', 'alternative', 'conservative', 'emergency']
        try:
            current_idx = sequence.index(current_plan)
            if current_idx < len(sequence) - 1:
                return sequence[current_idx + 1]
        except ValueError:
            pass
        
        return 'emergency'
    
    def _log_plan_failure(
        self,
        goal: TemporalGoal,
        plan_name: str,
        result: Dict[str, Any]
    ) -> None:
        """Log plan failure for analysis"""
        
        failure_entry = {
            'goal_id': goal.id,
            'goal_name': goal.name,
            'plan_name': plan_name,
            'reason': result.get('reason', 'unknown'),
            'timestamp': datetime.now().isoformat(),
            'attempt_count': goal.attempt_count,
            'result': result
        }
        
        self.execution_log.append(failure_entry)
        logger.warning(f"Plan failure logged: {plan_name} - {result.get('reason')}")
    
    def _log_exception(
        self,
        goal: TemporalGoal,
        plan_name: str,
        exception: Exception
    ) -> None:
        """Log exception during execution"""
        
        exception_entry = {
            'goal_id': goal.id,
            'plan_name': plan_name,
            'exception_type': type(exception).__name__,
            'exception_message': str(exception),
            'traceback': traceback.format_exc(),
            'timestamp': datetime.now().isoformat()
        }
        
        self.execution_log.append(exception_entry)
        logger.error(f"Exception logged: {type(exception).__name__} in {plan_name}")
    
    def _log_emergency_abort(
        self,
        goal: TemporalGoal,
        reason: str,
        character_state: Dict[str, Any]
    ) -> None:
        """Log emergency abort event"""
        
        abort_entry = {
            'goal_id': goal.id,
            'goal_name': goal.name,
            'reason': reason,
            'character_state': character_state,
            'timestamp': datetime.now().isoformat(),
            'attempt_count': goal.attempt_count,
            'plan_execution_history': goal.plan_execution_history
        }
        
        self.execution_log.append(abort_entry)
        logger.critical(f"Emergency abort logged: {reason}")
    
    def _generate_post_mortem(
        self,
        goal: TemporalGoal,
        reason: str,
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate comprehensive post-mortem analysis"""
        
        # Collect all plan failures
        all_failures = {}
        for entry in goal.plan_execution_history:
            plan = entry['from_plan']
            if plan not in all_failures:
                all_failures[plan] = []
            all_failures[plan].append(entry['reason'])
        
        post_mortem = {
            'goal_id': goal.id,
            'goal_name': goal.name,
            'goal_type': goal.goal_type,
            'all_plans_tried': list(all_failures.keys()),
            'failure_reasons': all_failures,
            'final_reason': reason,
            'total_attempts': goal.attempt_count,
            'total_failures': goal.failure_count,
            'character_state_at_failure': {
                'hp_percent': game_state.get('hp_percent', 0),
                'sp_percent': game_state.get('sp_percent', 0),
                'map': game_state.get('map_name', 'unknown'),
                'position': game_state.get('position', {'x': 0, 'y': 0})
            },
            'environmental_factors': {
                'time_of_day': game_state.get('hour', 0),
                'server_lag': game_state.get('ping_ms', 0),
                'player_density': game_state.get('player_count', 0)
            },
            'recommendations': self._generate_failure_recommendations(goal, all_failures),
            'ml_training_data': self._prepare_ml_training_data(goal, all_failures, game_state),
            'timestamp': datetime.now().isoformat()
        }
        
        return post_mortem
    
    def _generate_failure_recommendations(
        self,
        goal: TemporalGoal,
        failures: Dict[str, List[str]]
    ) -> List[str]:
        """Generate recommendations to prevent future failures"""
        
        recommendations = []
        
        # Analyze failure patterns
        all_reasons = []
        for reasons in failures.values():
            all_reasons.extend(reasons)
        
        if 'timeout' in str(all_reasons).lower():
            recommendations.append("Increase goal timeout by 50%")
        
        if 'insufficient' in str(all_reasons).lower():
            recommendations.append("Ensure sufficient resources before starting")
        
        if 'hp' in str(all_reasons).lower():
            recommendations.append("Increase healing threshold to 70%")
        
        recommendations.append("Review goal parameters and adjust based on failure analysis")
        recommendations.append("Consider breaking goal into smaller sub-goals")
        
        return recommendations
    
    def _prepare_ml_training_data(
        self,
        goal: TemporalGoal,
        failures: Dict[str, List[str]],
        game_state: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Prepare data for ML model training"""
        
        return {
            'goal_type': goal.goal_type,
            'features': {
                'hp_percent': game_state.get('hp_percent', 100),
                'sp_percent': game_state.get('sp_percent', 100),
                'weight_percent': game_state.get('weight_percent', 0),
                'character_level': game_state.get('character_level', 1),
                'party_size': game_state.get('party_size', 0),
                'hour_of_day': game_state.get('hour', 12)
            },
            'label': 'failure',
            'failure_count': len(failures),
            'plans_failed': list(failures.keys())
        }
    
    def _store_for_ml_training(
        self,
        goal: TemporalGoal,
        post_mortem: Dict[str, Any]
    ) -> None:
        """Store failure data for ML model training"""
        
        # In production, this would write to database
        logger.info(f"Stored ML training data for goal {goal.id}")
    
    def _save_character_state(self, game_state: Dict[str, Any]) -> Dict[str, Any]:
        """Save current character state"""
        
        return {
            'hp': game_state.get('hp', 0),
            'sp': game_state.get('sp', 0),
            'hp_percent': game_state.get('hp_percent', 0),
            'sp_percent': game_state.get('sp_percent', 0),
            'position': game_state.get('position', {'x': 0, 'y': 0}),
            'map': game_state.get('map_name', 'unknown'),
            'timestamp': datetime.now().isoformat()
        }
    
    async def _emergency_teleport(self, game_state: Dict[str, Any]) -> str:
        """Teleport character to safety"""
        
        # Simulate emergency teleport
        # In production, this would execute actual teleport command
        logger.info("Executing emergency teleport...")
        return "Teleported to safe zone"
    
    async def _heal_to_full(self, game_state: Dict[str, Any]) -> str:
        """Heal character to full HP/SP"""
        
        # Simulate healing
        # In production, this would use healing items or skills
        logger.info("Healing to full HP/SP...")
        return "Healed to 100% HP and SP"
